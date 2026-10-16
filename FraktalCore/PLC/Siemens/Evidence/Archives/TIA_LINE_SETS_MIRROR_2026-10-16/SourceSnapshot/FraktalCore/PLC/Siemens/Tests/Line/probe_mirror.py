"""Guarded source/mirror checks; synthetic provider, no cross-controller claim."""
import json
import os
from pathlib import Path
import sys
import time

from mirror_target import WORK, PROFILE, TIA, action, guard, original
sys.path.insert(0,str(TIA/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi, leaf_var


def probe(output):
    if output.resolve().parent != WORK.resolve():raise ValueError('fixed private workspace required')
    before=original();guard()
    facts=Catalog.read();line_kind=facts.enums['E_ConfigKind']['LINE_CFG']
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/LineMirror_20261016.webapi.pin'
    api=WebApi(PROFILE['address'],pin,not pin.exists());checks=[]
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            checks.append(passed);emit(dict(event='check',label=label,value=value,expected=expected,passed=passed))
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=120):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def connect():api.login('fraktal');return Mailbox(api,guard,emit)
        def ready():
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'restore barrier')
            wait(lambda:all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB')),'verified writes')
        def login(root):
            check('login '+root,box.request('LOGIN',root,User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN']))
            wait(lambda:not box.read(root+'.Access.LoginBusy'),'login')
            check('admin '+root,box.read(root+'.Access.CurrentLevel'),4)
        def controls(**values):
            emit(dict(event='provider-control-guard',status=guard(),fields=list(values)))
            rows=api.bulk([('PlcProgram.Write',{'var':leaf_var(['GDB_LineMirrorTest',name]),'value':value}) for name,value in values.items()])
            if any(error for value,error in rows):raise RuntimeError('provider control refused')
        def publish(revision,value,mode=0,error=0,synchronized=True):
            controls(Enabled=True,IncomingRevision=revision,TaktMs=value,ImageMode=mode,SourceError=error,Synchronized=synchronized)
            emit(dict(event='provider-pulse-guard',status=guard()))
            api.call('PlcProgram.Write',{'var':leaf_var(['GDB_LineMirrorTest','PublishPulse']),'value':True})
            wait(lambda:not box.read('GDB_LineMirrorTest.PublishPulse'),'provider accepted pulse')
            # Available is private; observe the owner-facing result instead.
            time.sleep(.1)
        def line_rows(root):
            assert box.request('QUERY_CONFIG',root,IntValue=0)
            total=box.read(root+'.HmiResponse.ConfigPage.PageCount');found=[]
            for page in range(max(0,total-2),total):
                assert box.request('QUERY_CONFIG',root,IntValue=page)
                base=root+'.HmiResponse.ConfigPage';count=box.read(base+'.EntryCount')
                names=('ConfigKind','WriteKey','ValueText','Readable','Writable','Scope')
                requests=[('PlcProgram.Read',{'var':leaf_var((base+'.Entries[%d].%s'%(slot,name)).split('.'))}) for slot in range(1,count+1) for name in names]
                rows=api.bulk(requests)
                if any(error for value,error in rows):raise RuntimeError('manifest read refused')
                for start in range(0,len(rows),len(names)):
                    row=dict(zip(names,[v[0] for v in rows[start:start+len(names)]]))
                    if row['ConfigKind']==line_kind:found.append(row)
            return found
        def stale_slots():
            count=facts.capacities['MAX_ALARM_ACTIVE']
            rows=api.bulk([('PlcProgram.Read',{'var':leaf_var(['StationA','AlarmLog','Active[%d]'%slot,name])})
                           for slot in range(1,count+1) for name in ('Description','State')])
            if any(error for value,error in rows):raise RuntimeError('event read failed')
            return [slot for slot in range(1,count+1)
                    if rows[(slot-1)*2][0]=='std.error.lineDataStale'
                    and rows[(slot-1)*2+1][0]!=facts.enums['E_AlarmState']['CLOSED']]
        try:
            box=connect();ready();emit(dict(event='connection',status=guard(),fingerprint=api.fingerprint))
            check('no virgin-image persistence failure',box.read('StationA.ConfigPersist.Failed'),False)
            initial=box.read('StationA.Line.Revision'); first=initial+10
            emit(dict(event='initial-revision',revision=initial,cold=initial==0))
            for root in ('StationA','StationB'):
                login(root)
                rows=line_rows(root)
                check('eight mirror capabilities '+root,len(rows),8)
                check('initial mirror capabilities '+root,all(not r['Writable'] and r['Readable']==(initial>0)
                      and (initial>0 or r['ValueText']=='') and r['Scope']==root for r in rows))
                check('mirror role '+root,box.read(root+'.Line.Role'),facts.enums['E_LineRole']['MIRROR'])
            check('provider scheduled once per scan',box.read('GDB_LineMirrorTest.SourceOncePerScan'))
            publish(first,1500)
            wait(lambda:box.read('StationA.Line.Revision')==first,'first source revision')
            check('first image typed value',box.read('GDB_LineMirrorTest.WorkingTaktMs'),1500)
            check('source clock quality propagated',box.read('StationA.Line.TimeSynchronized'))
            check('valid source clears staleness',box.read('StationA.Line.Stale'),False)
            wait(lambda:box.read('StationA.Line.Stale'),'source expiry',10)
            for mode,label in ((1,'wrong identity'),(2,'partial image'),(3,'invalid last record')):
                publish(first+1,2500,mode)
                check('reject '+label,box.read('StationA.Line.Revision'),first)
                check('whole rejection preserves first field '+label,box.read('GDB_LineMirrorTest.WorkingTaktMs'),1500)
                check('bad image does not renew freshness '+label,box.read('StationA.Line.Stale'))
            publish(first+1,2500,synchronized=False)
            wait(lambda:box.read('StationA.Line.Revision')==first+1,'new complete source revision')
            check('new source value committed',box.read('GDB_LineMirrorTest.WorkingTaktMs'),2500)
            check('unsynchronized source is explicit',box.read('StationA.Line.TimeSynchronized'),False)
            publish(first+1,2600)
            check('changed same revision refused',box.read('GDB_LineMirrorTest.WorkingTaktMs'),2500)
            wait(lambda:box.read('StationA.Line.Stale'),'invalid heartbeat cannot renew source',10)
            publish(first+2,3500,error=77)
            check('provider error published',box.read('StationA.Line.SourceError'),77)
            check('provider error keeps previous image',box.read('GDB_LineMirrorTest.WorkingTaktMs'),2500)
            publish(first+2,3500)
            wait(lambda:box.read('StationA.Line.Revision')==first+2,'recovered source revision')
            check('provider error clears',box.read('StationA.Line.SourceError'),0)
            check('recovered complete value',box.read('GDB_LineMirrorTest.WorkingTaktMs'),3500)
            for root in ('StationA','StationB'):
                rows=line_rows(root)
                check('mirror remains read-only '+root,all(not r['Writable'] and r['Readable'] for r in rows))
                check('mirror value served under peer scope '+root,int(next(r['ValueText'] for r in rows if r['WriteKey']=='line.taktMs')),3500)
            for kind,fields in (
                ('WRITE_CONFIG',dict(TargetPath='StationA',NameValue='line.taktMs',TextValue='4000',IntValue=1)),
                ('SAVE_CONFIG_SET',dict(TextValue='mirror-refused',IntValue=line_kind)),
                ('EXPORT_CURRENT_CONFIG',dict(TextValue='mirror-refused',IntValue=line_kind,NameValue='f'*32))):
                check('mirror refuses '+kind,box.request(kind,**fields),False)
                check('refusal names owner '+kind,box.read('StationA.ConfigPersist.LastRejectScope'),'BenchLineOwner')
            header=dict(set='mirror-refused',root='StationA',schema=1,configRev=box.read('StationA.ConfigRev'),kind=line_kind,model='',records=8,created=0,clock=0)
            check('mirror refuses line import header',box.request('IMPORT_CONFIG_SET',TextValue=json.dumps(header,separators=(',',':'))),False)
            check('import refusal names owner',box.read('StationA.ConfigPersist.LastRejectScope'),'BenchLineOwner')
            check('refusals keep revision',box.read('StationA.Line.Revision'),first+2)
            controls(Enabled=False,SourceError=0);ready()
            wait(lambda:box.read('StationA.Line.Stale'),'offline mirror expiry',10)
            slots=stale_slots();check('one stale event',len(slots),1)
            event='StationA.AlarmLog.Active[%d]'%slots[0]
            for name,wanted in (('Severity',facts.enums['E_Severity']['LOW']),('Category',facts.enums['E_Category']['SYSTEM']),('ResetClass',facts.enums['E_ResetClass']['AUTO_RESET'])):
                check('stale event '+name,box.read(event+'.'+name),wanted)
            check('stale event nonblocking',box.read('StationA.AlarmLog.Blocking'),False)
            time.sleep(.2);check('stale event deduplicates',len(stale_slots()),1)
            controls(PoisonPulse=True)
            wait(lambda:box.read('GDB_LineMirrorTest.WorkingTaktMs')==99999,'poison working mirror')
            api.conn.close();emit(dict(event='power-cycle',status=action('restart')))
            api=WebApi(PROFILE['address'],pin,False);box=connect();ready()
            check('offline restart restores mirrored value',box.read('GDB_LineMirrorTest.WorkingTaktMs'),3500)
            check('offline restart restores revision',box.read('StationA.Line.Revision'),first+2)
            check('boot observed defaults before mirror restore',box.read('GDB_LineMirrorTest.BootDefaultValue'),1000)
            check('restore does not invent synchronized source time',box.read('StationA.Line.TimeSynchronized'),False)
            wait(lambda:box.read('StationA.Line.Stale'),'restored mirror still needs source observation',10)
            login('StationA');modes=facts.enums['E_Mode']
            check('stale mirror AUTO selection',box.request('SET_MODE',IntValue=modes['AUTO']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['AUTO'],'AUTO')
            check('staleness alone permits production start',box.request('START'))
            wait(lambda:box.read('StationA.RunningPublished'),'running despite stale source')
            check('reset running synthetic Unit',box.request('OPERATOR_RESET'))
            wait(lambda:box.read('StationA.Status.State')==0 and not box.read('StationA.RunningPublished'),'ready after reset')
            check('MANUAL restored',box.request('SET_MODE',IntValue=modes['MANUAL']))
            publish(first+2,3500)
            wait(lambda:not box.read('StationA.Line.Stale'),'same-revision heartbeat after restore')
            check('same revision reapplied after restore',box.read('StationA.Line.Revision'),first+2)
            wait(lambda:not stale_slots(),'stale event closed',3)
            check('stale event closes automatically',len(stale_slots()),0)
            check('provider still scheduled once',box.read('GDB_LineMirrorTest.SourceOncePerScan'))
            ready();assert box.request('LOGOUT')
            after=original();check('original Fraktal unchanged',after,before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not c for c in checks)))
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
