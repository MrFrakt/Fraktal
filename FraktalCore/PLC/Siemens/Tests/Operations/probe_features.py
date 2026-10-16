"""Real mailbox checks for identity, health, gates, tower and teach capture."""
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
    facts=Catalog.read();before=original();TARGET.guard();checks=[]
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Operations_20261016.webapi.pin'
    api=WebApi(TARGET.profile['address'],pin,not pin.exists())
    with output.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row)+'\n');stream.flush()
        def check(label,value,expected=True):
            passed=type(value) is type(expected) and value==expected
            emit(dict(event='check',label=label,value=value,expected=expected,passed=passed));checks.append(passed)
            if not passed:raise AssertionError(label)
        def wait(predicate,label,seconds=90):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.1)
            raise TimeoutError(label)
        def control(name,value):
            path=name if '.' in name else 'GDB_UnitTest.'+name
            TARGET.guard();api.call('PlcProgram.Write',dict(var=leaf_var(path.split('.')),value=value))
        def login(user='admin'):
            check('login '+user,box.request('LOGIN',User=user,Secret=os.environ['FRAKTAL_TIA_'+user.upper()+'_PIN']))
            wait(lambda:not box.read('StationA.Access.LoginBusy'),'login result')
            check('authenticated '+user,box.read('StationA.Access.CurrentLevel'),4 if user=='admin' else 1)
        def active():
            values=api.bulk([('PlcProgram.Read',dict(var=leaf_var(('StationA.AlarmLog.Active[%d].%s'%(i,n)).split('.')))) for i in range(1,facts.capacities['MAX_ALARM_ACTIVE']+1) for n in ('State','ReasonCode')])
            if any(error for value,error in values):raise RuntimeError('active alarm read refused')
            return {values[i+1][0]:i//2+1 for i in range(0,len(values),2) if values[i][0]!=facts.enums['E_AlarmState']['CLOSED']}
        def capture(**fields):return box.request('CAPTURE_CONFIG',NameValue='capturedCycles',IntValue=1,**fields)
        try:
            api.login('fraktal');box=Mailbox(api,TARGET.guard,emit)
            wait(lambda:not box.read('FRK_PersistStatus.Restoring'),'LOAD_DB restore')
            login()
            if box.read('StationA.ConfigPersist.RestoreLost') and not box.read('StationA.ConfigPersist.RestoreAcknowledged'):
                check('explicitly acknowledge isolated fixture schema change',box.request('ACK_CONFIG_RESTORE'))
            check('root nameplate has exact unique identity',box.read('StationA.Nameplate.ProductUri'),'urn:fraktal:tia:operations:station-a')
            check('unassigned peer nameplate stays empty',box.read('StationB.Nameplate.ProductUri'),'')
            check('health evaluator present',box.read('StationA.SystemHealth.Present'))
            wait(lambda:box.read('StationA.SystemHealth.TaskAvailable'),'native RT_INFO measurement')
            check('native task measurement positive',box.read('StationA.SystemHealth.TaskCycleUs')>0)
            check('native wall clock available',box.read('StationA.SystemHealth.TimeQuality.Available'))
            check('unqualified synchronization remains false',box.read('StationA.SystemHealth.TimeQuality.Synchronized'),False)
            check('unqualified CPU and memory metrics remain unavailable',box.read('StationA.SystemHealth.ControllerAvailable'),False)
            check('incomplete target health never invented healthy',box.read('StationA.SystemHealth.Healthy'),False)
            gate=facts.enums['E_Reason']['COMMISSIONING_GATE_ACTIVE'];slots=active()
            check('simulation gate standard event present',gate in slots)
            check('commissioning gate cannot be shelved',box.request('SHELVE_ALARM',IntValue=slots[gate],DurationMs=1000),False)
            box.request('OPERATOR_RESET')
            check('operator reset cannot conceal build gate',gate in active())
            wait(lambda:box.read('StationA.Status.State')==facts.enums['E_ExecState']['READY'],'ready after reset')
            modes=facts.enums['E_Mode'];check('select MANUAL',box.request('SET_MODE',IntValue=modes['MANUAL']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['MANUAL'],'manual')
            check('lamp test accepted',box.request('LAMP_TEST'))
            check('all lamps and horn during test',all(box.read('StationA.SignalTower.'+n) for n in ('Red','Amber','Green','Blue','White','Horn','TestActive')))
            wait(lambda:not box.read('StationA.SignalTower.TestActive'),'lamp test automatic expiry',seconds=8)
            check('lamp test self clears',box.read('StationA.SignalTower.TestActive'),False)
            policy=facts.enums['E_GatedAction']['DATA_WRITE'];prior=box.read('StationA.Access.Policy.Required[%d]'%policy)
            check('protect capture with DATA_WRITE',box.request('SET_ACCESS_LEVEL',IntValue=policy,TextValue='2'))
            login('operator');check('capture access refusal',capture(),False)
            check('capture reports access denial',box.read('StationA.HmiResponse.Diagnostic'),'std.error.accessDenied');login()
            count=box.read('StationA.OutImm.Cycles');check('initial fixture count inside capture band',0<=count<=10)
            check('capture ignores client-supplied number',capture(TextValue='999'))
            check('captured actual published value',box.read('StationA.StationCfg.CapturedCycles'),count)
            check('uncaptured field refused',box.request('CAPTURE_CONFIG',NameValue='preset',IntValue=2,TextValue='99'),False)
            check('wrong capture revision refused',box.request('CAPTURE_CONFIG',NameValue='capturedCycles',IntValue=2),False)
            check('wrong revision gives RECIPE_INVALID',box.read('StationA.HmiResponse.Report.Reasons[1].ReasonCode'),facts.enums['E_Reason']['RECIPE_INVALID'])
            check('foreign root capture refused',capture(TargetPath='StationB'),False)
            check('select AUTO',box.request('SET_MODE',IntValue=modes['AUTO']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['AUTO'],'auto')
            check('capture needs setup mode',capture(),False)
            check('start fixture production',box.request('START'))
            wait(lambda:box.read('StationA.RunningPublished'),'running')
            check('lamp test refused during production',box.request('LAMP_TEST'),False)
            check('capture refused during production',capture(),False)
            control('FinishCycle',True)
            control('GDB_RoutingTest.NestedFinish',True)
            control('GDB_RoutingTest.InnerFinish',True)
            wait(lambda:box.read('StationA.OutImm.Cycles')>10,'published measurement outside teach band')
            check('graceful stop',box.request('STOP'))
            wait(lambda:not box.read('StationA.RunningPublished'),'stopped')
            wait(lambda:all(box.read(path+'.Status.State')==facts.enums['E_ExecState']['READY'] for path in ('StationA.Satellite','StationA.Satellite.Inner')),'all synthetic descendant cycles stopped')
            check('capture range test begins with every descendant READY',all(box.read(path+'.Status.State')==facts.enums['E_ExecState']['READY'] for path in ('StationA.Satellite','StationA.Satellite.Inner')))
            control('FinishCycle',False)
            control('GDB_RoutingTest.NestedFinish',False)
            control('GDB_RoutingTest.InnerFinish',False)
            check('release completed command',box.request('STOP'))
            wait(lambda:box.read('StationA.Status.State')==facts.enums['E_ExecState']['READY'],'ready after command release')
            check('return MANUAL',box.request('SET_MODE',IntValue=modes['MANUAL']))
            wait(lambda:box.read('StationA.ModeActivePublished')==modes['MANUAL'],'manual after run')
            check('machine value obeys same range validation',capture(),False)
            check('out of range capture gives RECIPE_INVALID',box.read('StationA.HmiResponse.Report.Reasons[1].ReasonCode'),facts.enums['E_Reason']['RECIPE_INVALID'])
            check('rejected capture leaves configuration intact',box.read('StationA.StationCfg.CapturedCycles'),count)
            check('restore DATA_WRITE policy',box.request('SET_ACCESS_LEVEL',IntValue=policy,TextValue=str(prior)))
            wait(lambda:not box.read('StationA.ConfigPersist.Pending') and not box.read('StationA.ConfigPersist.Failed'),'verified durable writes')
            check('logout',box.request('LOGOUT'))
            after=original();check('original keeper unchanged',after,before)
            emit(dict(result='PASS',checks=len(checks),failures=sum(not p for p in checks),original_before=before,original_after=after))
        except BaseException:
            emit(dict(result='FAIL',checks=len(checks),failures=sum(not p for p in checks),original_before=before,original_after=original()));raise
        finally:
            if api.conn:api.conn.close()


if __name__=='__main__':probe(Path(sys.argv[1]))
