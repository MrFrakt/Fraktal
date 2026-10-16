"""Guarded live production/weekly-calendar requests on the isolated .55 CPU."""
import copy
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
    if output.resolve().parent!=WORK.resolve():raise ValueError('fixed private test workspace required')
    facts=Catalog.read();before=original();TARGET.guard()
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Operations_20261016.webapi.pin'
    api=WebApi(TARGET.profile['address'],pin,not pin.exists());checks=[]
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=120):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def login(root='StationA',user='admin'):
            check('login '+root+' '+user,box.request('LOGIN',root,User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda:not box.read(root+'.Access.LoginBusy'),'application authentication')
            check('level '+root+' '+user,box.read(root+'.Access.CurrentLevel'),4 if user=='admin' else 1)
        def durable():
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'restore barrier')
            wait(lambda:all(not box.read(r+'.ConfigPersist.Pending') and not box.read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB')),'verified document writes')
        def edit(key,value,root='StationA',model=0):
            return box.request('WRITE_CONFIG',root,TargetPath=root,NameValue=key,TextValue=str(value),IntValue=1,DurationMs=model)
        def rows(root):
            assert box.request('QUERY_CONFIG',root,IntValue=0)
            count=box.read(root+'.HmiResponse.ConfigPage.PageCount');result=[]
            for page in range(max(0,count-3),count):
                assert box.request('QUERY_CONFIG',root,IntValue=page)
                base=root+'.HmiResponse.ConfigPage';n=box.read(base+'.EntryCount');names=('WriteKey','ValueText','ConfigKind','Readable','Writable')
                values=api.bulk([('PlcProgram.Read',{'var':leaf_var((base+'.Entries[%d].%s'%(i,key)).split('.'))}) for i in range(1,n+1) for key in names])
                if any(error for value,error in values):raise RuntimeError('manifest page refused')
                for start in range(0,len(values),len(names)):
                    row=dict(zip(names,[v[0] for v in values[start:start+len(names)]]))
                    if row['ConfigKind']==facts.enums['E_ConfigKind']['LINE_CFG']:result.append(row)
            return result
        def export(name,kind=None):
            args=dict(TextValue=name,IntValue=0)
            if kind is not None:args.update(IntValue=kind,NameValue='0123456789abcdef0123456789abcdef')
            if not box.request('EXPORT_CURRENT_CONFIG' if kind is not None else 'EXPORT_CONFIG_SET',**args):return None
            count=box.read('StationA.ConfigSetDocumentLines');result=[json.loads(box.read('StationA.ConfigSetDocument'))]
            for i in range(1,count+1):
                if not box.request('EXPORT_CONFIG_SET',TextValue=name,IntValue=i,NameValue=args.get('NameValue','')):return None
                result.append(json.loads(box.read('StationA.ConfigSetDocument')))
            return result
        def importing(document):
            for i,row in enumerate(document):
                value=json.dumps(row,separators=(',',':'))
                pieces=[value[n:n+255] for n in range(0,len(value),255)]
                for j,piece in enumerate(pieces):
                    last=j==len(pieces)-1
                    if not box.request('IMPORT_CONFIG_SET',TextValue=piece,IntValue=0 if last else 1,BoolValue=last and i==len(document)-1):return False
            return True
        try:
            api.login('fraktal');box=Mailbox(api,TARGET.guard,emit);durable()
            emit(dict(event='connection',status=TARGET.guard(),fingerprint=api.fingerprint))
            for root in ('StationA','StationB'):
                check('initial IDLE '+root,box.read(root+'.MachineState'),facts.enums['E_MachineState']['IDLE'])
                check('idle has no invented availability '+root,box.read(root+'.Oee.AvailValid'),False)
                check('empty calendar is unscheduled '+root,box.read(root+'.CurrentShift'),0)
                check('no unconfigured production goal '+root,box.read(root+'.ShiftProductionTarget'),0)
                login(root)
                calendar=rows(root);check('complete29-field line manifest '+root,len(calendar),29)
                check('owner calendar advertised writable '+root,all(r['Readable'] and r['Writable'] for r in calendar))
                check('default row duration from Core '+root,int(next(r['ValueText'] for r in calendar if r['WriteKey']=='line.shift.1.durationMin')),1440)
                check('new row starts unused '+root,int(next(r['ValueText'] for r in calendar if r['WriteKey']=='line.shift.1.startMin')),-1)
            gate=facts.enums['E_GatedAction']['DATA_WRITE']
            prior_gate=box.read('StationA.Access.Policy.Required[%d]'%gate)
            check('set OEE reset gate to technician',box.request('SET_ACCESS_LEVEL',IntValue=gate,TextValue='2'))
            login(user='operator')
            check('operator cannot reset OEE under technician policy',box.request('RESET_OEE'),False)
            login();check('administrator resets OEE',box.request('RESET_OEE'))
            check('reset trend head',box.read('StationA.OeeTrendHead'),0)
            check('per-model ideal cycle write',edit('idealCycleMs',1250))
            check('working ideal cycle follows model config',box.read('StationA.Oee.IdealCycleMs'),1250)
            modes=facts.enums['E_Mode']
            check('select AUTO',box.request('SET_MODE',IntValue=modes['AUTO']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['AUTO'],'AUTO selection')
            check('start Unit',box.request('START'))
            wait(lambda:box.read('StationA.RunningPublished'),'running')
            check('classified producing',box.read('StationA.MachineState'),facts.enums['E_MachineState']['PRODUCING'])
            wait(lambda:box.read('StationA.Oee.RunMs')>0,'measured run bucket')
            check('production makes availability valid',box.read('StationA.Oee.AvailValid'))
            check('peer calendar edit respects shared readiness',edit('line.shift.utcOffsetMin',1,'StationB'),False)
            check('operator reset stops synthetic Unit',box.request('OPERATOR_RESET'))
            wait(lambda:not box.read('StationA.RunningPublished') and box.read('StationA.Status.State')==facts.enums['E_ExecState']['READY'],'ready')
            check('return MANUAL',box.request('SET_MODE',IntValue=modes['MANUAL']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['MANUAL'],'MANUAL')
            check('empty calendar row start edit',edit('line.shift.1.startMin',0))
            check('target configured before enabling row',edit('line.shift.1.target',500))
            check('enable full-day weekly row',edit('line.shift.1.activeDays',127))
            for root in ('StationA','StationB'):
                wait(lambda:box.read(root+'.CurrentShift')==1,'scheduled interval '+root)
                check('latched target '+root,box.read(root+'.ShiftProductionTarget'),500)
                check('unscheduled interval closed '+root,box.read(root+'.ShiftHistoryCount'),1)
                check('closed record V3 '+root,box.read(root+'.ShiftHistory[1].SchemaVersion'),3)
                check('closed off interval target0 '+root,box.read(root+'.ShiftHistory[1].ProductionTarget'),0)
                check('native unqualified clock remains explicit '+root,box.read(root+'.ShiftHistory[1].TimeSynchronized'),False)
            check('target edit accepted',edit('line.shift.1.target',900))
            for root in ('StationA','StationB'):check('open target not rewritten '+root,box.read(root+'.ShiftProductionTarget'),500)
            revision=box.read('StationA.Line.Revision')
            check('second row start while disabled',edit('line.shift.2.startMin',0))
            revision=box.read('StationA.Line.Revision')
            check('individual overlap refused whole',edit('line.shift.2.activeDays',127),False)
            check('overlap refusal keeps revision',box.read('StationA.Line.Revision'),revision)
            check('save complete calendar set',box.request('SAVE_CONFIG_SET',TextValue='operations-calendar',IntValue=facts.enums['E_ConfigKind']['LINE_CFG']))
            document=export('operations-calendar');check('saved29-record calendar',len(document),30)
            invalid=copy.deepcopy(document)
            next(row for row in invalid[1:] if row['key']=='line.shift.2.activeDays')['value']='127'
            check('import overlapping calendar refused atomically',importing(invalid),False)
            check('whole refusal keeps owner revision',box.read('StationA.Line.Revision'),revision)
            original_set=export('operations-calendar')
            check('failed import preserves stored calendar',int(next(r['value'] for r in original_set[1:] if r['key']=='line.shift.2.activeDays')),0)
            check('saved valid calendar loads',box.request('LOAD_CONFIG_SET',TextValue='operations-calendar'))
            check('whole load advances revision once',box.read('StationA.Line.Revision'),revision+1)
            for root in ('StationA','StationB'):check('set load cannot rewrite latched target '+root,box.read(root+'.ShiftProductionTarget'),500)
            check('delete test calendar set',box.request('DELETE_CONFIG_SET',TextValue='operations-calendar'))
            # Preserve a reusable empty-calendar test image after this run.
            check('disable calendar for next boot',edit('line.shift.1.activeDays',0))
            check('normalize target',edit('line.shift.1.target',0))
            check('normalize ideal cycle',edit('idealCycleMs',1000))
            check('restore data-write policy',box.request('SET_ACCESS_LEVEL',IntValue=gate,TextValue=str(prior_gate)))
            durable()
            for root in ('StationA','StationB'):check('logout '+root,box.request('LOGOUT',root))
            after=original();check('original Fraktal unchanged',after,before)
            emit(dict(event='complete',checks=len(checks),failures=sum(not c for c in checks)))
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
