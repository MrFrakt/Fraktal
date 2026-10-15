"""Isolated native Unit mailbox/control/trace tests; mutations are never replayed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi, leaf_var
from fraktal_tia_binding import Catalog


from tia_target_guard import guard


def probe(out):
    catalog=Catalog.read(); modes=catalog.enums['E_Mode']; kinds=catalog.enums['E_HmiRequestKind']
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    checks=[]
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        api=WebApi('169.254.212.49',pin,False)
        def read(name):return api.call('PlcProgram.Read',{'var':leaf_var(name.split('.'))})
        def check(label,actual,expected):
            passed=type(actual) is type(expected) and actual==expected
            checks.append((label,passed));emit({'event':'check','label':label,'actual':actual,'expected':expected,'passed':passed})
            if not passed:raise AssertionError(label)
        def wait(name,expected):
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                actual=read(name)
                if actual==expected:return actual
                time.sleep(.02)
            check('wait '+name,actual,expected)
        def write_many(values):
            emit({'event':'mutation-guard','status':guard(),'targets':list(values)})
            replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(name.split('.')),'value':value}) for name,value in values.items()])
            if any(error for value,error in replies):raise AssertionError('write refused: '+str(replies))
        def request(root,kind,iv=0,bv=False,secret=False):
            seq=(int(read(root+'.HmiRequest.Sequence'))+1)&0xffffffff
            if seq==0:seq=1
            values={root+'.HmiRequest.Kind':kinds.get(kind,kind),root+'.HmiRequest.IntValue':iv,root+'.HmiRequest.BoolValue':bv}
            if secret:values[root+'.HmiRequest.Secret']='test-only'
            write_many(values)
            write_many({root+'.HmiRequest.Sequence':seq})
            wait(root+'.HmiResponse.AckSequence',seq)
            accepted=read(root+'.HmiResponse.Accepted')
            emit({'event':'ack','root':root,'kind':kind,'sequence':seq,'accepted':accepted,'diagnostic':read(root+'.HmiResponse.Diagnostic')})
            if kind == 'LOGIN':
                if not accepted:raise AssertionError('login attempt was not consumed')
                wait(root+'.Access.LoginResultSequence',seq)
                wait(root+'.Access.LoginBusy',False)
                return not read(root+'.Access.LoginFailed') and read(root+'.Access.CurrentLevel')>0
            return accepted
        def set_input(**values):write_many({'GDB_UnitTest.'+name:value for name,value in values.items()})
        def last_part_event():
            # Operator access traces may follow a part event in the same scan.
            # Inspect the newest canonical part record, rather than assuming the
            # entire history ring contains only part events.
            head=read('StationA.AlarmLog.RingHead')
            reasons={catalog.enums['E_Reason'][name] for name in ('EVENT_PART_RECEIVED','EVENT_PART_PROCESSING_STARTED','EVENT_PART_PROCESSED','EVENT_PART_PROCESSING_ABORTED')}
            for offset in range(catalog.capacities['MAX_ALARM_RING']):
                slot=(head-1-offset)%catalog.capacities['MAX_ALARM_RING']+1
                reason=read('StationA.AlarmLog.Ring[%d].ReasonCode'%slot)
                if reason in reasons:return reason
            return 0
        def reset(ready=True):
            check('reset accepted',request('StationA','OPERATOR_RESET'),True)
            if ready:wait('StationA.Status.State',0);wait('GDB_UnitTest.ChildState',0)
        def mode(name):
            check('mode '+name,request('StationA','SET_MODE',modes[name]),True)
            wait('StationA.ModeActivePublished',modes[name])
        def start():
            check('start accepted',request('StationA','START'),True)
            wait('StationA.RunningPublished',True)
        def stop_cycle():
            check('stop accepted',request('StationA','STOP'),True)
            check('stop awaits cycle',read('StationA.RunningPublished'),True)
            check('stop pending',read('StationA.StopPendingPublished'),True)
            set_input(FinishCycle=True)
            wait('StationA.Status.State',0)
            set_input(FinishCycle=False)
            check('stop no longer pending',read('StationA.StopPendingPublished'),False)
        def mode_action(action):
            emit({'event':'mode-guard','action':action,'status':guard()})
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
            emit({'event':'mode-result','action':action,'exit':result.returncode,'output':result.stdout.decode('utf-8-sig')})
            if result.returncode:raise RuntimeError('simulator mode failed')
        try:
            api.login('fraktal');emit({'event':'connection','pin':api.fingerprint,'version':api.call('Api.Version'),'permissions':api.call('Api.GetPermissions')})
            baseline_good=read('StationA.GoodCount');baseline_writes=read('GDB_UnitTest.CarrierWrites')
            check('initial manual',read('StationA.ModeActivePublished'),modes['MANUAL'])
            check('peer identity',read('StationB.Status.Name'),'StationB')
            check('peer carrier off',read('StationB.Part.Uid'),'')
            check('manual start rejected',request('StationA','START'),False)
            check('manual release reasons',int(read('StationA.HmiResponse.Report.Count'))>0,True)
            check('unsupported mode rejected',request('StationA','SET_MODE',999),False)
            check('unsupported request rejected',request('StationA',999),False)
            check('absent login provider rejected',request('StationA','LOGIN',secret=True),False)
            check('transport secret cleared',read('GDB_UnitTest.SecretCleared'),True)
            check('private copy secret cleared',read('GDB_UnitTest.SnapshotSecretCleared'),True)
            mode('AUTO')
            set_input(LockStart=True)
            check('PLC access blocks mailbox start',request('StationA','START'),False)
            check('access reason published',read('StationA.HmiResponse.Report.Reasons[1].Kind'),catalog.enums['E_ReleaseKind']['ACCESS'])
            set_input(LockStart=False)
            set_input(Permit=False)
            check('live permit blocks start',request('StationA','START'),False)
            check('release query accepted',request('StationA','RELEASE_START'),True)
            check('release false',read('StationA.HmiResponse.Report.Released'),False)
            check('owning permit path',read('StationA.HmiResponse.Report.Reasons[1].SourcePath'),'StationA.Cell.Clamp')
            set_input(Permit=True)
            start();time.sleep(2.2)
            check('continuous run beyond timeout',read('StationA.RunningPublished'),True)
            check('part received present',read('StationA.Part.Present'),True)
            check('canonical started event',last_part_event(),catalog.enums['E_Reason']['EVENT_PART_PROCESSING_STARTED'])
            uid=read('StationA.Part.Uid')
            check('nonempty local uid',len(uid)>0,True)
            sequence=read('StationA.HmiRequest.Sequence')
            write_many({'StationA.HmiRequest.Kind':kinds['STOP'],'StationA.HmiRequest.Sequence':sequence})
            time.sleep(.08);check('same sequence does not replay',read('StationA.StopPendingPublished'),False)
            stop_cycle()
            check('good count once',read('StationA.GoodCount'),baseline_good+1)
            check('result provider uid',read('GDB_UnitTest.WrittenUid'),uid)
            check('result write once',read('GDB_UnitTest.CarrierWrites'),baseline_writes+1)
            check('canonical processed event',last_part_event(),catalog.enums['E_Reason']['EVENT_PART_PROCESSED'])
            check('part no longer present',read('StationA.Part.Present'),False)
            ack=read('StationA.HmiResponse.AckSequence')
            write_many({'StationA.HmiRequest.Kind':kinds['START'],'StationA.HmiRequest.Sequence':0})
            time.sleep(.08)
            check('zero sequence ignored',read('StationA.HmiResponse.AckSequence'),ack)
            check('zero sequence does not start',read('StationA.RunningPublished'),False)
            start()
            check('auto graceful mode request',request('StationA','SET_MODE',modes['HOME']),True)
            check('mode remains auto while stopping',read('StationA.ModeActivePublished'),modes['AUTO'])
            set_input(FinishCycle=True);wait('StationA.ModeActivePublished',modes['HOME']);set_input(FinishCycle=False)
            start();set_input(ExitHold=True)
            check('home request deferred by hook',request('StationA','SET_MODE',modes['AUTO']),True)
            check('home held by exit hook',read('StationA.ModeActivePublished'),modes['HOME'])
            set_input(ExitHold=False);wait('StationA.ModeActivePublished',modes['AUTO'])
            check('immediate cancel releases part',read('StationA.Part.Present'),False)
            check('abort event',last_part_event(),catalog.enums['E_Reason']['EVENT_PART_PROCESSING_ABORTED'])
            mode('CHANGEOVER');start()
            check('blocked while running',request('StationA','SET_MODE',modes['AUTO']),False)
            stop_cycle();mode('AUTO')
            start();set_input(IssueChild=True,ChildCommand=2)
            wait('GDB_UnitTest.ChildState',1)
            reset()
            check('reset releases stranded execute',read('GDB_UnitTest.ChildExecute'),False)
            set_input(FaultRoot=True);wait('StationA.Status.FaultActive',True)
            reset(False);check('reset does not erase live fault',read('StationA.Status.FaultActive'),True)
            set_input(FaultRoot=False);reset()
            set_input(Permit=False)
            check('reset does not bypass permit',request('StationA','START'),False)
            set_input(Permit=True)
            start();set_input(CarrierControl=2)
            stop_cycle_request=request('StationA','STOP')
            check('stop before failed carrier',stop_cycle_request,True)
            writes=read('GDB_UnitTest.CarrierWrites');good=read('StationA.GoodCount')
            set_input(FinishCycle=True);wait('StationA.ErrorID',catalog.enums['E_Reason']['CARRIER_WRITE_FAILED']);set_input(FinishCycle=False)
            check('failed write no good count',read('StationA.GoodCount'),good)
            check('failed write no provider result',read('GDB_UnitTest.CarrierWrites'),writes)
            check('failed write abort event',last_part_event(),catalog.enums['E_Reason']['EVENT_PART_PROCESSING_ABORTED'])
            reset();set_input(CarrierControl=1)
            set_input(CarrierControl=2)
            check('start read-failure attempt accepted',request('StationA','START'),True)
            wait('StationA.ErrorID',catalog.enums['E_Reason']['CARRIER_READ_FAILED'])
            check('read failure does not publish part',read('StationA.Part.Present'),False)
            reset();set_input(CarrierControl=1)
            start();set_input(CarrierControl=3)
            check('stop before mismatch accepted',request('StationA','STOP'),True)
            set_input(FinishCycle=True);wait('StationA.ErrorID',catalog.enums['E_Reason']['PART_ID_MISMATCH']);set_input(FinishCycle=False)
            check('identity mismatch stops result',read('StationA.Part.Present'),False)
            reset()
            start();set_input(Verdict=catalog.enums['E_Verdict']['NOK'],Reason=0)
            check('stop before bad verdict accepted',request('StationA','STOP'),True)
            set_input(FinishCycle=True);wait('StationA.ErrorID',catalog.enums['E_Reason']['RESULT_RECORD_REJECTED']);set_input(FinishCycle=False)
            reset();set_input(Verdict=catalog.enums['E_Verdict']['OK'],Reason=2003)
            mode('HOME');start();set_input(ExitHold=True)
            check('bounded exit request accepted',request('StationA','SET_MODE',modes['AUTO']),True)
            wait('StationA.ErrorID',catalog.enums['E_Reason']['TIMEOUT'])
            check('timed-out exit keeps old mode',read('StationA.ModeActivePublished'),modes['HOME'])
            set_input(ExitHold=False);reset();mode('AUTO')
            start();set_input(IssueChild=True,ChildCommand=2);wait('GDB_UnitTest.ChildState',1)
            seq=read('StationA.HmiRequest.Sequence');boot=read('GDB_UnitTest.BootStamp')
            mode_action('halt');mode_action('run')
            wait('StationA.Status.State',0)
            check('restart defaults to manual',read('StationA.ModeActivePublished'),modes['MANUAL'])
            check('restart did not replay start',read('StationA.RunningPublished'),False)
            check('restart releases child execute',read('GDB_UnitTest.ChildExecute'),False)
            check('restart has a new startup stamp',read('GDB_UnitTest.BootStamp')!=boot,True)
            check('restart acknowledges current boundary',read('StationA.HmiResponse.AckSequence'),read('StationA.HmiRequest.Sequence'))
            check('restart boundary rejected',read('StationA.HmiResponse.Accepted'),False)
            mode('AUTO');start();stop_cycle();mode('MANUAL')
            for path in ('StationA.Unit.RunReq','StationA.Device.Cycles','StationA.Core.Exec','StationA.ModePolicy[0].Style','FRK_Carriers.Slots[1].Serial'):
                value,error=api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])[0]
                check('private '+path,error.get('code') if error else None,200)
            for path,value in [('StationA.ModeActivePublished',0),('StationA.Access.CurrentLevel',4),('StationA.Part.Uid','bad'),('StationA.Cell.Clamp.Execute',True),('StationA.ParCfg.Timeout',1)]:
                emit({'event':'mutation-guard','status':guard(),'target':path})
                reply,error=api.bulk([('PlcProgram.Write',{'var':leaf_var(path.split('.')),'value':value})])[0]
                check('read-only '+path,error.get('code') if error else None,205)
            emit({'event':'summary','checks':len(checks),'failed':sum(not ok for label,ok in checks),'passed':True})
        finally:
            if api.token:api.call('Api.Logout')
            api.conn.close()
            suite=ET.Element('testsuite',name='Fraktal.TIA.Unit.Native',tests=str(len(checks)),failures=str(sum(not ok for label,ok in checks)))
            for label,ok in checks:
                case=ET.SubElement(suite,'testcase',name=label)
                if not ok:ET.SubElement(case,'failure',message=label)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)


if __name__=='__main__':probe(Path(sys.argv[1]))
