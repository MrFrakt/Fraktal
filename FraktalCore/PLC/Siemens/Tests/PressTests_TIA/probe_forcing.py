"""Core 10.5.1 forcing on the engineering press image, over the real root mailbox."""
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'));sys.path.insert(0,str(HERE.parent/'Line'))
from fraktal_tia_binding import Catalog
from owner_target import original
from tia_mailbox import Mailbox
from tia_webapi import WebApi,leaf_var

TOPOLOGY='GDB_PressDemoFieldbus.Topology'
CONTROL_COILS=('_000K951','_000K911')


def probe(target,output,pin):
    if output.resolve().parent!=target.work:raise ValueError('fixed isolated workspace required')
    facts=Catalog.read();before=original();target.guard();checks=[]
    definition=json.loads((HERE.parents[1]/'Examples/PressDemo/01_PneumaticPress/press.json').read_bytes())
    api=WebApi(target.profile['address'],pin,not pin.exists())
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=45):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.05)
            emit(dict(event='timeout',label=label,state=read('Status.State'),mode=read('ModeActivePublished')))
            raise TimeoutError(label)
        def read(path):return box.read('PressDemo.'+path)
        def bulk(paths):
            replies=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
            if any(error for value,error in replies):raise RuntimeError('topology read refused')
            return [value for value,error in replies]
        def request(kind,**fields):return box.request(kind,root='PressDemo',**fields)
        def mode(name):
            check('select '+name,request('SET_MODE',IntValue=facts.enums['E_Mode'][name]))
            wait(lambda:read('ModeActivePublished')==facts.enums['E_Mode'][name],'mode '+name)
        def idle():wait(lambda:read('Status.State')==facts.enums['E_ExecState']['READY'],'root READY')
        def audit(prefix,path):
            # Every request is audited, so look back a few records, not only at the head.
            capacity=facts.capacities['MAX_ALARM_RING'];head=read('AlarmLog.RingHead')
            for back in range(8):
                index=(head-1-back)%capacity+1
                text,source=bulk(['PressDemo.AlarmLog.Ring[%d].%s'%(index,f) for f in ('Description','SourcePath')])
                if text.startswith(prefix) and source==path:return text
            return ''
        def channels():
            nodes=box.read(TOPOLOGY+'.NodeCount');rows={}
            for node in range(1,nodes+1):
                base=TOPOLOGY+'.Nodes[%d]'%node
                for channel in range(1,box.read(base+'.ChannelCount')+1):
                    at=base+'.Channels[%d]'%channel
                    # The public surface only: set-points and the permit stay private (Part IV 10.5).
                    path,direction,forceable,forced,owner=bulk([at+'.'+f for f in ('Path','Dir','Forceable','Forced','ModulePath')])
                    rows[path]=dict(at=at,dir=direction,forceable=forceable,forced=forced,owner=owner)
            return rows
        def force(path,on,text='true'):
            accepted=request('FORCE_CHANNEL',TargetPath=path,BoolValue=on,TextValue=text if on else '')
            return accepted,read('HmiResponse.Diagnostic')
        try:
            api.login('fraktal');box=Mailbox(api,target.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'LOAD_DB restore');idle()
            register={};page=0
            while True:
                check('query engineering register page '+str(page),request('QUERY_CONFIG',IntValue=page))
                count=read('HmiResponse.ConfigPage.EntryCount');pages=read('HmiResponse.ConfigPage.PageCount')
                if not 1<=pages<=1024:raise ValueError('unbounded manifest')
                for index in range(1,count+1):
                    item=read('HmiResponse.ConfigPage.Entries[%d].Item'%index)
                    if item.startswith('Engineering/Gates/') and item.endswith('/Name'):
                        register[read('HmiResponse.ConfigPage.Entries[%d].ValueText'%index)]=item
                page+=1
                if page>=pages:break
            check('engineering image declares both build gates',sorted(register),['OUTPUT_FORCING','USE_SIMULATION'])
            rows=channels()
            output_kind,input_kind=facts.enums['E_ChannelDir']['OUTPUT'],facts.enums['E_ChannelDir']['INPUT']
            forceable=sorted(p for p,r in rows.items() if r['forceable'])
            emit(dict(event='topology',channels=len(rows),forceable=forceable))
            check('declared forceable channel count',len(forceable),len(definition['fieldbus']['forceable']))
            check('only outputs are forceable',all(rows[p]['dir']==output_kind for p in forceable))
            check('every forceable output belongs to the press',all(rows[p]['owner'].startswith('PressDemo.') for p in forceable))
            check('control-power coils are never forceable',any(c in p for p in forceable for c in CONTROL_COILS),False)
            check('nothing is forced at boot',any(r['forced'] for r in rows.values()),False)
            valve,second=forceable[0],forceable[1]
            sensor=next(p for p,r in sorted(rows.items()) if r['dir']==input_kind)
            coil=next(p for p,r in sorted(rows.items()) if r['dir']==output_kind and any(c in p for c in CONTROL_COILS))
            def forced():return sorted(p for p,r in channels().items() if r['forced'])
            mode('MANUAL');idle()
            emit(dict(event='access',level=read('Access.CurrentLevel')))
            check('force a declared valve',force(valve,True),(True,''))
            check('forced valve is published forced',box.read(rows[valve]['at']+'.Forced'),True)
            check('force audited against its channel with the value','set=true' in audit('std.audit.channelForced',valve))
            for label,path in (('an input',sensor),('a control-power coil',coil),('an unknown channel','PressIo1214C DQ/_NoSuchTag')):
                check('refuse forcing '+label,force(path,True),(False,'std.error.hmiRequestRejected'))
                check('refusal audited for '+label,audit('std.audit.channelForceRejected',path)!='')
            check('refused requests force nothing else',forced(),[valve])
            # The exact-'true' decoding is a private set-point, proven natively (Operations suite);
            # here the request is accepted and the text it carried is audited verbatim.
            check('force with a non-canonical value',force(second,True,'TRUE'),(True,''))
            check('non-canonical value audited verbatim','set=TRUE' in audit('std.audit.channelForced',second))
            check('clear the valve force',force(valve,False),(True,''))
            check('cleared valve is released',box.read(rows[valve]['at']+'.Forced'),False)
            check('clear audited',audit('std.audit.channelForceCleared',valve)!='')
            check('force the valve again',force(valve,True),(True,''))
            mode('HOME')
            wait(lambda:not forced(),'forces withdrawn outside idle MANUAL')
            check('leaving idle MANUAL withdraws every force',forced(),[])
            check('withdrawal audited once for the root',audit('std.audit.forcesWithdrawn','PressDemo')!='')
            check('force refused outside idle MANUAL',force(valve,True),(False,'std.fieldbus.forceBlocked'))
            check('start HOME after withdrawal',request('START'));wait(lambda:read('RunningPublished'),'HOME running')
            wait(lambda:not read('RunningPublished'),'HOME completed',90);idle()
            mode('MANUAL');idle()
            check('a restored permit resumes no force',forced(),[])
            check('idle MANUAL accepts a new force',force(valve,True),(True,''))
            check('and clears it',force(valve,False),(True,''))
            check('original keeper unchanged',original(),before)
            emit(dict(result='PASS',checks=len(checks),failures=sum(not p for p in checks)))
        except BaseException:
            emit(dict(result='FAIL',checks=len(checks),failures=sum(not p for p in checks),original_before=before,original_after=original()));raise
        finally:
            if api.conn:api.conn.close()
