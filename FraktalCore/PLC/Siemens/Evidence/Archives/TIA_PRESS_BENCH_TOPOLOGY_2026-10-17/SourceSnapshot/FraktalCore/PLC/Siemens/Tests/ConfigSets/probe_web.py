"""Native mailbox acceptance for retained keyed sets and JSON-lines exchange."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_target_guard import guard


def probe(out):
    c = Catalog.read(); checks = []; complete = False
    pin = Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/FrkS12.webapi.pin'
    api = WebApi('169.254.212.49', pin, False)
    with out.open('x', encoding='ascii', newline='\n') as stream:
        def emit(row):
            stream.write(json.dumps(row, ensure_ascii=True)+'\n'); stream.flush()
        def read(path):
            return api.call('PlcProgram.Read', {'var': leaf_var(path.split('.'))})
        def check(label, actual, expected=True):
            ok = type(actual) is type(expected) and actual == expected
            checks.append((label, ok)); emit(dict(event='check', label=label, actual=actual, expected=expected, passed=ok))
            if not ok: raise AssertionError(label)
        def write(values):
            replies = api.bulk([('PlcProgram.Write', {'var': leaf_var(p.split('.')), 'value': v}) for p,v in values.items()])
            if any(error for value,error in replies): raise AssertionError('native write refused')
        def wait(predicate, seconds=8):
            deadline = time.monotonic()+seconds
            while time.monotonic() < deadline:
                if predicate(): return
                time.sleep(.02)
            raise AssertionError('mailbox/session timeout')
        def request(kind, root='StationA', **fields):
            return Mailbox(api, guard, emit).request(kind, root, **fields)
        def login(root='StationA', user='admin'):
            check(root+' '+user+' login consumed', request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda: not read(root+'.Access.LoginBusy'))
            check(root+' '+user+' authenticated',read(root+'.Access.CurrentLevel'),4 if user=='admin' else 1)
        def edit(scope,key,value,revision=2):
            return request('WRITE_CONFIG',TargetPath=scope,NameValue=key,TextValue=value,IntValue=revision)
        def listing(root='StationA'):
            assert request('LIST_CONFIG_SETS',root)
            return [read(root+'.ConfigSets[%d].SetName'%i) for i in range(1,read(root+'.ConfigSetCount')+1)]
        def station_requires_ready():
            page = 0
            while True:
                assert request('QUERY_CONFIG', IntValue=page)
                base = 'StationA.HmiResponse.ConfigPage'
                for slot in range(1, read(base+'.EntryCount')+1):
                    entry = base+'.Entries[%d]'%slot
                    if read(entry+'.ConfigKind') == c.enums['E_ConfigKind']['STATION_CFG'] and read(entry+'.Writable') and read(entry+'.RequiresReady'):
                        return True
                page += 1
                if page >= read(base+'.PageCount'): return False
        def restore_ready():
            # LOCAL_RETAIN has no document-medium status DB. LOAD_DB restores
            # asynchronously and withholds the operator mailbox until complete.
            value, error = api.bulk([('PlcProgram.Read', {'var':leaf_var(['FRK_PersistStatus','Restoring'])})])[0]
            if error:
                if error['code'] == 200: return True
                raise AssertionError('restore status unavailable')
            return not value and all(not read(root+'.ConfigPersist.Pending') and not read(root+'.ConfigPersist.Failed') for root in ('StationA','StationB'))
        def export(name,root='StationA'):
            lines=[]; count=0; index=0
            while index <= count:
                assert request('EXPORT_CONFIG_SET',root,TextValue=name,IntValue=index)
                check('export line index '+str(index),read(root+'.ConfigSetDocumentLine'),index)
                count=read(root+'.ConfigSetDocumentLines')
                lines.append(read(root+'.ConfigSetDocument'));index+=1
            emit(dict(event='document',root=root,lines=lines))
            return [json.loads(line) for line in lines]
        def importing(document):
            for index,row in enumerate(document):
                line=json.dumps(row,separators=(',',':'),ensure_ascii=True)
                pieces=[line[i:i+255] for i in range(0,len(line),255)]
                for pi,piece in enumerate(pieces):
                    last=pi==len(pieces)-1
                    if not request('IMPORT_CONFIG_SET',TextValue=piece,IntValue=0 if last else 1,BoolValue=last and index==len(document)-1): return False
            return True
        def copy(document,name):
            value=json.loads(json.dumps(document));value[0]['set']=name;return value
        try:
            api.login('fraktal');emit(dict(event='connection',status=guard(),pin=api.fingerprint))
            check('named-set provider advertised',read('StationA.ConfigPersist.StorePresent'))
            check('peer provider advertised',read('StationB.ConfigPersist.StorePresent'))
            # Declare the bench's CONFIG_SET gate through the same authenticated
            # policy handler, including when resuming an earlier candidate.
            login();login('StationB')
            for root in ('StationA','StationB'):
                assert request('SET_ACCESS_LEVEL',root,IntValue=c.enums['E_GatedAction']['CONFIG_SET'],TextValue='3')
                assert request('ACK_CONFIG_RESTORE',root)
                assert request('LOGOUT',root)
            check('anonymous cannot list',request('LIST_CONFIG_SETS'),False)
            check('anonymous cannot save',request('SAVE_CONFIG_SET',TextValue='denied',IntValue=1),False)
            login(user='operator')
            check('operator cannot save',request('SAVE_CONFIG_SET',TextValue='denied',IntValue=1),False)
            login();login('StationB')
            for root in ('StationA','StationB'):
                for existing in listing(root): assert request('DELETE_CONFIG_SET',root,TextValue=existing)
            check('empty own listing',listing(),[])
            check('empty peer listing',listing('StationB'),[])
            check('set release query',request('RELEASE_ACTION',IntValue=c.enums['E_GatedAction']['CONFIG_SET']))
            check('set release allowed',read('StationA.HmiResponse.Report.Released'))
            for name in ('','n'*81): check('invalid name refused '+str(len(name)),request('SAVE_CONFIG_SET',TextValue=name,IntValue=1),False)
            check('line config unsupported',request('SAVE_CONFIG_SET',TextValue='line',IntValue=2),False)
            check('station label write',edit('StationA','siteLabel','saved station',1))
            check('nested station label write',edit('StationA.Satellite','siteLabel','saved nested',1))
            check('save station config',request('SAVE_CONFIG_SET',TextValue='station',IntValue=1))
            check('listing own saved set',listing(),['station'])
            check('peer has no own set',listing('StationB'),[])
            check('peer cannot load own set',request('LOAD_CONFIG_SET','StationB',TextValue='station'),False)
            check('edit root after save',edit('StationA','siteLabel','changed root',1))
            check('edit nested after save',edit('StationA.Satellite','siteLabel','changed nested',1))
            revision=read('StationA.ConfigRev')
            check('atomic station config load',request('LOAD_CONFIG_SET',TextValue='station'))
            check('root restored',read('StationA.StationCfg.SiteLabel'),'saved station')
            check('nested restored',read('StationA.Satellite.StationCfg.SiteLabel'),'saved nested')
            check('load advances config revision',read('StationA.ConfigRev')!=revision)
            check('peer stays at default',read('StationB.StationCfg.SiteLabel'),'bench')
            for field in range(1,8):
                assert request('SAVE_CONFIG_SET',TextValue='station',IntValue=1)
                assert edit('StationA','siteLabel','unchanged on failure',1)
                revision=read('StationA.ConfigRev')
                emit(dict(event='mutation-guard',status=guard(),targets=['GDB_ConfigSetTest']))
                write({'GDB_ConfigSetTest.SetName':'station','GDB_ConfigSetTest.Field':field,
                       'GDB_ConfigSetTest.Text':'invalid-boolean','GDB_ConfigSetTest.Corrupt':True})
                wait(lambda: not read('GDB_ConfigSetTest.Corrupt'))
                check('saved last record corrupted '+str(field),read('GDB_ConfigSetTest.Slot')>0)
                check('late load rejection '+str(field),request('LOAD_CONFIG_SET',TextValue='station'),False)
                check('late rejection leaves first value '+str(field),read('StationA.StationCfg.SiteLabel'),'unchanged on failure')
                check('late rejection leaves config revision '+str(field),read('StationA.ConfigRev'),revision)
                check('late rejection names scope '+str(field),bool(read('StationA.ConfigPersist.LastRejectScope')))
                check('late rejection names key '+str(field),bool(read('StationA.ConfigPersist.LastRejectKey')))
                check('rejected station set is an event '+str(field),read('StationA.Error'),False)
                assert edit('StationA','siteLabel','saved station',1)
            assert request('SAVE_CONFIG_SET',TextValue='station',IntValue=1)
            station=export('station');check('station header identity',station[0]['root'],'StationA')
            check('station has nested records',any(r.get('scope')=='StationA.Satellite' for r in station[1:]))
            check('unsynchronized clock declared',station[0]['clock'],0)
            check('complete header count',station[0]['records'],len(station)-1)
            check('JSON roundtrip imports',importing(copy(station,'imported')))
            check('import does not apply live config',read('StationA.StationCfg.SiteLabel'),'saved station')
            for mode in ('schema','root','revision','kind','type','value','duplicate','missing','unknown','model'):
                bad=copy(station,'bad-'+mode)
                if mode=='schema':bad[0]['schema']=99
                elif mode=='root':bad[0]['root']='StationB'
                elif mode=='revision':bad[-1]['rev']=99
                elif mode=='kind':bad[-1]['kind']=0
                elif mode=='type':bad[-1]['type']=3 if bad[-1]['type']!=3 else 0
                elif mode=='value':bad[-1]['value']='invalid-boolean'
                elif mode=='duplicate':bad[-1]=dict(bad[1])
                elif mode=='missing':bad.pop();bad[0]['records']-=1
                elif mode=='unknown':bad[-1]['key']='unknown'
                else:bad[0]['model']='MODEL_A'
                check('invalid import refused '+mode,importing(bad),False)
                check('invalid import preserves live '+mode,read('StationA.StationCfg.SiteLabel'),'saved station')
            check('failed imports consume no slots',len(listing()),2)
            # A held piece cannot survive another request or session generation.
            header=json.dumps(station[0],separators=(',',':'))
            check('import piece held',request('IMPORT_CONFIG_SET',TextValue=header[:40],IntValue=1))
            assert request('QUERY_CONFIG',IntValue=0)
            check('intervening operation discards piece',request('IMPORT_CONFIG_SET',TextValue=header[40:]),False)
            check('malformed/trailing JSON refused',request('IMPORT_CONFIG_SET',TextValue=header+'x'),False)
            check('duplicate JSON field refused',request('IMPORT_CONFIG_SET',TextValue=header[:-1]+',"schema":1}'),False)
            check('save model config',request('SAVE_CONFIG_SET',TextValue='model',IntValue=0))
            check('root model write',edit('StationA','preset','99'))
            check('late leaf model write',edit('StationA.Satellite.Cell.Gate','preset','77'))
            check('load model config',request('LOAD_CONFIG_SET',TextValue='model'))
            check('root model restored',read('StationA.ParCfg.Preset'),10)
            check('late leaf model restored',read('StationA.Satellite.Cell.Gate.ParCfg.Preset'),10)
            model=export('model');check('model code travels',model[0]['model'],'MODEL_A')
            check('model excludes station config',all(r['kind']==0 for r in model[1:]))
            check('unknown model import refused',importing([dict(model[0],set='unknown-model',model='UNKNOWN')]+model[1:]),False)
            check('fourth slot saves',request('SAVE_CONFIG_SET',TextValue='fourth',IntValue=1))
            check('capacity refusal',request('SAVE_CONFIG_SET',TextValue='overflow',IntValue=1),False)
            check('replacement uses same slot',request('SAVE_CONFIG_SET',TextValue='fourth',IntValue=1))
            check('full store still four',len(listing()),4)
            check('delete frees slot',request('DELETE_CONFIG_SET',TextValue='fourth'))
            check('same name separate peer',request('SAVE_CONFIG_SET','StationB',TextValue='station',IntValue=1))
            # Import a >255-character valid header through normal HMI pieces.
            longdoc=copy(station,'L'*80);longdoc[0]['root']='StationA';
            line=json.dumps(longdoc[0],separators=(',',':'))
            # An 80-character value plus escaping makes a record exceed one request.
            for row in longdoc[1:]:
                if row['key']=='siteLabel' or row['key'].startswith('long.'):row['value']='"\\'*40
            check('long record requires pieces',max(len(json.dumps(r,separators=(',',':'))) for r in longdoc)>255)
            check('long escaped lines import',importing(longdoc))
            roundtrip=export('L'*80)
            check('long escaped value intact',roundtrip[1]['value'],longdoc[1]['value'])
            check('exported line exceeds one request',max(len(json.dumps(r,separators=(',',':'))) for r in roundtrip)>255)
            check('delete long set',request('DELETE_CONFIG_SET',TextValue='L'*80))
            station_ready = station_requires_ready()
            busy_timeout = read('StationA.ParCfg.Timeout')
            # The guarded host performs several round trips while BUSY. Give
            # this fixture phase a declared budget, then restore the old value.
            assert edit('StationA','timeout','60000',1)
            assert request('SET_MODE',IntValue=c.enums['E_Mode']['AUTO']);assert request('START')
            wait(lambda: read('StationA.RunningPublished'))
            check('model load refuses BUSY',request('LOAD_CONFIG_SET',TextValue='model'),False)
            before_busy_load = read('StationA.StationCfg.SiteLabel')
            check('whole station load honors declared READY requirements',request('LOAD_CONFIG_SET',TextValue='station'),not station_ready)
            if station_ready:
                check('BUSY rejection leaves live station value intact',read('StationA.StationCfg.SiteLabel'),before_busy_load)
            check('save remains allowed BUSY',request('SAVE_CONFIG_SET',TextValue='busy',IntValue=1))
            check('list remains allowed BUSY',len(listing()),4)
            assert request('OPERATOR_RESET');wait(lambda: not read('StationA.RunningPublished'))
            assert edit('StationA','timeout',str(busy_timeout),1)
            emit(dict(event='mutation-guard',status=guard(),targets=['GDB_ConfigTest.Unavailable']))
            write({'GDB_ConfigTest.Unavailable':True})
            check('unavailable store refuses save',request('SAVE_CONFIG_SET',TextValue='station',IntValue=1),False)
            check('failure exposed',read('StationA.ConfigPersist.Failed'))
            write({'GDB_ConfigTest.Unavailable':False})
            check('storage recovery saves',request('SAVE_CONFIG_SET',TextValue='station',IntValue=1))
            check('failure clears after success',read('StationA.ConfigPersist.Failed'),False)
            for leaf in ('StationA.ConfigSetDocument','StationA.ConfigSets[1].SetName','FRK_SetStore.SchemaVersion','FRK_SetRuntime.Work[1].Received'):
                value,error=api.bulk([('PlcProgram.Read',{'var':leaf_var(leaf.split('.'))})])[0]
                if leaf.startswith('FRK_'):check('private set state hidden '+leaf,error['code'],200)
                else:
                    value,error=api.bulk([('PlcProgram.Write',{'var':leaf_var(leaf.split('.')),'value':'forbidden'})])[0]
                    check('published set state read-only '+leaf,error['code'],205)
            # STOP/RUN cold-start path preserves named sets without unregistering.
            expected=listing()
            wait(lambda: all(not read(root+'.ConfigPersist.Pending') and not read(root+'.ConfigPersist.Failed') for root in ('StationA','StationB')), seconds=60)
            api.conn.close()
            for action in ('halt','run'):
                emit(dict(event='mode-guard',action=action,status=guard()))
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit(dict(event='mode-result',action=action,exit_code=result.returncode));assert result.returncode==0
            api=WebApi('169.254.212.49',pin,False);api.login('fraktal')
            wait(restore_ready, seconds=60)
            login()
            login('StationB')
            check('named sets survive cold start',listing(),expected)
            check('retained set loads after restart',request('LOAD_CONFIG_SET',TextValue='model'))
            # Leave the downloaded qualification image at its reproducible defaults.
            assert request('LOAD_CONFIG_SET',TextValue='model')
            for name in listing():assert request('DELETE_CONFIG_SET',TextValue=name)
            for name in listing('StationB'):assert request('DELETE_CONFIG_SET','StationB',TextValue=name)
            assert edit('StationA','siteLabel','bench',1);assert edit('StationA.Satellite','siteLabel','bench',1)
            complete = True
            emit(dict(event='complete',checks=len(checks),failed=sum(not ok for _,ok in checks),status=guard()))
        finally:
            api.conn.close()
            suite=ET.Element('testsuite',name='Fraktal.TIA.ConfigSets',tests=str(len(checks)),failures=str(sum(not ok for _,ok in checks)),errors='0' if complete else '1')
            for label,ok in checks:
                case=ET.SubElement(suite,'testcase',name=label)
                if not ok:ET.SubElement(case,'failure',message=label)
            if not complete:ET.SubElement(ET.SubElement(suite,'testcase',name='acceptance completed'),'error',message='Probe stopped before completion; see native log')
            ET.ElementTree(suite).write(out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)


if __name__=='__main__':probe(Path(sys.argv[1]))
