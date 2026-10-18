"""Both clone sources, BUSY isolation, immutable indices and actual restart/loss."""
import json
import os
from pathlib import Path
import sys
import time
from target import TARGET,WORK,original
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from fraktal_tia_binding import Catalog
from tia_mailbox import Mailbox
from tia_webapi import WebApi,leaf_var


def probe(output):
    if output.resolve().parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    facts=Catalog.read();before=original();checks=[];api=box=None
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Operations_20261016.webapi.pin'
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=240):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def connect():
            nonlocal api,box
            api=WebApi(TARGET.profile['address'],pin,not pin.exists());api.login('fraktal')
            box=Mailbox(api,TARGET.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring') and box.read('StationA.ModelCapacity')==3,'model restore barrier')
        def login(root='StationA',user='admin'):
            check('login '+root+' '+user,box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda:not box.read(root+'.Access.LoginBusy'),'login completion')
            check('authenticated '+root+' '+user,box.read(root+'.Access.CurrentLevel'),4 if user=='admin' else 1)
        def durable():
            wait(lambda:all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB')),'verified durable checkpoint')
        def control(key,value):
            TARGET.guard();api.call('PlcProgram.Write',dict(var=leaf_var(key.split('.')),value=value))
        def policy(action,level,root='StationA'):
            return box.request('SET_ACCESS_LEVEL',root,IntValue=facts.enums['E_GatedAction'][action],TextValue=str(level))
        def edit(key,value,root='StationA',model=0):
            return box.request('WRITE_CONFIG',root,NameValue=key,IntValue=2 if key=='preset' else 1,TextValue=str(value),DurationMs=model)
        def create(code,root='StationA',source=0,set_name=None):
            return box.request('CREATE_MODEL',root,NameValue=code,IntValue=source,BoolValue=set_name is not None,TextValue=set_name or '')
        def cycle():
            api.conn.close();emit(dict(event='restart',status=TARGET.action('restart')));connect()
        def export(name,root):
            check('begin set export '+root,box.request('EXPORT_CONFIG_SET',root,TextValue=name))
            rows=[json.loads(box.read(root+'.ConfigSetDocument'))]
            for index in range(1,box.read(root+'.ConfigSetDocumentLines')+1):
                if not box.request('EXPORT_CONFIG_SET',root,TextValue=name,IntValue=index):raise AssertionError('set export continuation')
                rows.append(json.loads(box.read(root+'.ConfigSetDocument')))
            return rows
        def import_rows(rows,root):
            for index,row in enumerate(rows):
                text=json.dumps(row,separators=(',',':'))
                # One request holds a 255-WCHAR piece. Longer records use the
                # existing exact chunk protocol, never a truncated JSON line.
                while len(text)>240:
                    if not box.request('IMPORT_CONFIG_SET',root,TextValue=text[:240],IntValue=1):return False
                    text=text[240:]
                if not box.request('IMPORT_CONFIG_SET',root,TextValue=text,BoolValue=index==len(rows)-1):return False
            return True
        try:
            connect();login();login('StationB');durable()
            wait(lambda:box.read('GDB_ModelTest.Done'),'native model assertions')
            check('native assertion count',box.read('GDB_ModelTest.Checks'),15)
            check('native assertion failures',box.read('GDB_ModelTest.Failures'),0)
            check('inherited class assertion count',box.read('GDB_ClassPolicyTest.Checks'),16)
            check('inherited class assertion failures',box.read('GDB_ClassPolicyTest.Failures'),0)
            check('seed count A',box.read('StationA.AvailableModelCount'),2)
            check('seed count B',box.read('StationB.AvailableModelCount'),2)
            denied=api.bulk([('PlcProgram.Write',dict(var=leaf_var(['StationA',member]),value=1)) for member in ('ModelCapacity','AvailableModelCount')])
            check('catalog dimensions externally read only',all(error is not None for value,error in denied))
            check('cursor fixture selects B',box.request('SET_MODEL',TextValue='MODEL_B'))
            check('save unchanged B model set',box.request('SAVE_CONFIG_SET',TextValue='cursor-B',IntValue=0))
            check('cursor fixture returns to A',box.request('SET_MODEL',TextValue='MODEL_A'));durable()
            check('load B set with unchanged B values',box.request('LOAD_CONFIG_SET',TextValue='cursor-B'));durable()
            cycle();check('model-set load persists its active cursor',box.read('StationA.Model.ModelCode'),'MODEL_B')
            login();login('StationB')
            check('return to seed A',box.request('SET_MODEL',TextValue='MODEL_A'))
            durable();control('GDB_ModelTest.DropCachePulse',True)
            wait(lambda:box.read('GDB_ModelTest.CacheDropped'),'seed cache row deliberately removed')
            check('complete model-set load repairs missing cache row',box.request('LOAD_CONFIG_SET',TextValue='cursor-B'))
            check('repaired model is active',box.read('StationA.Model.ModelCode'),'MODEL_B')
            check('return to A after repair',box.request('SET_MODEL',TextValue='MODEL_A'))
            for code,source in [('',0),('MODEL_A',0),('X'*65,0),('bad-source',3),('negative-source',-1)]:
                check('invalid create '+repr(code),create(code,source=source),False)
            check('CONFIG_SET may be offered to operator',policy('CONFIG_SET',1))
            check('restrict model read',policy('DATA_READ',4));check('allow blanket model write',policy('DATA_WRITE',0))
            login(user='operator')
            check('read permission rechecked on creation',create('READ_DENIED'),False)
            check('read refusal exact key',box.read('StationA.ConfigPersist.LastRejectKey'),'timeout')
            check('read refusal is access diagnostic',box.read('StationA.HmiResponse.Diagnostic'),'std.error.accessDenied')
            login();check('allow blanket read',policy('DATA_READ',0))
            check('allow commissioning source reads independently',box.request('SET_CLASS_LEVEL',NameValue='commissioning',IntValue=0,BoolValue=False))
            check('restrict blanket write',policy('DATA_WRITE',4))
            login(user='operator');check('write permission independently rechecked',create('WRITE_DENIED'),False)
            check('write refusal exact key',box.read('StationA.ConfigPersist.LastRejectKey'),'timeout')
            login();check('save station set',box.request('SAVE_CONFIG_SET',TextValue='station-source',IntValue=1))
            check('station set is never a model source',create('WRONG_KIND',set_name='station-source'),False)
            check('inactive source edited',edit('preset',222,model=2))
            check('source A running recipe remains',box.read('StationA.Model.ModelCode'),'MODEL_A')
            preset=box.read('StationA.ParCfg.Preset');stage=box.read('GDB_ModelTest.StagedPreset')
            check('select AUTO',box.request('SET_MODE',IntValue=facts.enums['E_Mode']['AUTO']))
            check('start root for BUSY clone',box.request('START'))
            wait(lambda:box.read('StationA.Status.State')==facts.enums['E_ExecState']['BUSY'],'root BUSY')
            check('clone inactive model while BUSY',create('MODEL_NEW',source=2))
            check('accepted creation clears prior unsupported-request report',box.read('StationA.HmiResponse.Report.Count'),0)
            check('accepted creation release report is clear',box.read('StationA.HmiResponse.Report.Released'))
            wait(lambda:box.read('StationA.AvailableModelCount')==3,'new catalog durable publication')
            check('creation stayed BUSY',box.read('StationA.Status.State'),facts.enums['E_ExecState']['BUSY'])
            check('running model unchanged',box.read('StationA.Model.ModelCode'),'MODEL_A')
            check('running values unchanged',box.read('StationA.ParCfg.Preset'),preset)
            check('project prepared recipe untouched',box.read('GDB_ModelTest.StagedPreset'),stage)
            check('append keeps seed index1',box.read('StationA.AvailableModels[1].ModelCode'),'MODEL_A')
            check('append keeps seed index2',box.read('StationA.AvailableModels[2].ModelCode'),'MODEL_B')
            check('new entry index3',box.read('StationA.AvailableModels[3].ModelCode'),'MODEL_NEW')
            check('creation checkpoint observed pending',box.read('GDB_ModelTest.PendingSeen'))
            check('catalog never published ahead of readback',box.read('GDB_ModelTest.PrematurePublication'),False)
            check('capacity refusal changes nothing',create('OVER_CAPACITY'),False)
            check('ordinary changeover still refuses BUSY',box.request('SET_MODEL',TextValue='MODEL_NEW'),False)
            check('abort for changeover',box.request('OPERATOR_RESET'))
            wait(lambda:box.read('StationA.Status.State')==facts.enums['E_ExecState']['READY'],'reset READY')
            check('ordinary changeover activates clone',box.request('SET_MODEL',TextValue='MODEL_NEW'))
            check('cloned inactive values applied',box.read('StationA.ParCfg.Preset'),222)
            check('dynamic model accepts typed edit',edit('preset',333))
            check('peer has independent spare slot',box.read('StationB.AvailableModelCount'),2)
            login('StationB')
            check('prepare peer set',edit('preset',444,'StationB'))
            check('save peer complete model set',box.request('SAVE_CONFIG_SET','StationB',TextValue='peer-model',IntValue=0))
            control('GDB_ModelTest.DamageSetPulse',True)
            wait(lambda:box.read('GDB_ModelTest.SetDamaged'),'last source record deliberately damaged')
            check('source revision mismatch refuses entire creation',create('BAD_SCHEMA','StationB',set_name='peer-model'),False)
            check('source rejection leaves peer catalog untouched',box.read('StationB.AvailableModelCount'),2)
            check('source rejection names its record',bool(box.read('StationB.ConfigPersist.LastRejectKey')))
            control('GDB_ModelTest.RepairSetPulse',True)
            wait(lambda:box.read('GDB_ModelTest.SetRepaired'),'source record restored')
            rows=export('peer-model','StationB');rows[0]['set']='recovery-model';rows[0]['model']='OLD_CATALOG_CODE'
            check('import typed recovery model with absent catalog code',import_rows(rows,'StationB'))
            check('unknown-code set cannot activate',box.request('LOAD_CONFIG_SET','StationB',TextValue='recovery-model'),False)
            check('edit peer after saved snapshot',edit('preset',555,'StationB'))
            check('clone complete recovery set',create('SET_CLONE','StationB',set_name='recovery-model'))
            wait(lambda:box.read('StationB.AvailableModelCount')==3,'peer catalog publication')
            check('set clone leaves peer live recipe',box.read('StationB.ParCfg.Preset'),555)
            check('activate set clone',box.request('SET_MODEL','StationB',TextValue='SET_CLONE'))
            check('set source value copied',box.read('StationB.ParCfg.Preset'),444)
            durable();control('GDB_ModelTest.PoisonPulse',True)
            wait(lambda:box.read('GDB_ModelTest.Poisoned'),'retained catalog cache poisoned')
            cycle()
            check('LOAD_DB repairs poisoned catalog cache',box.read('StationA.AvailableModels[3].ModelCode'),'MODEL_NEW')
            check('restart restores created active model',box.read('StationA.Model.ModelCode'),'MODEL_NEW')
            check('restart restores edited dynamic data',box.read('StationA.ParCfg.Preset'),333)
            check('peer created model survives',box.read('StationB.Model.ModelCode'),'SET_CLONE')
            check('peer typed data survives',box.read('StationB.ParCfg.Preset'),444)
            login();login('StationB');durable();control('GDB_ModelTest.DamagePulse',True)
            wait(lambda:box.read('GDB_ModelTest.Damaged'),'model anchors damaged')
            cycle()
            check('corrupt catalog domain falls back to seeds',box.read('StationA.AvailableModelCount'),2)
            check('lost active model falls back to initial',box.read('StationA.Model.ModelCode'),'MODEL_A')
            check('loss requires explicit acknowledgment',box.read('StationA.ConfigPersist.RestoreLost'))
            check('peer catalog remains complete',box.read('StationB.AvailableModelCount'),3)
            check('peer active model preserved',box.read('StationB.Model.ModelCode'),'SET_CLONE')
            check('class policy survives model domain loss',box.read('StationA.Access.Classes[1].WriteLevel'),1)
            check('action policy survives model domain loss',box.read('StationA.Access.Policy.Required[1]'),4)
            login();check('unacknowledged loss blocks creation',create('RECOVERED'),False)
            check('acknowledge lost model domain',box.request('ACK_CONFIG_RESTORE'));durable()
            check('acknowledged seed catalog can create again',create('RECOVERED'))
            wait(lambda:box.read('StationA.AvailableModelCount')==3,'repaired catalog creation')
            durable();check('original Fraktal preserved',original(),before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not c for c in checks)))
        finally:
            if api and api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
