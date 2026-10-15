"""Native derived-state, event lifecycle, reset, overflow and sink checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from fraktal_tia_binding import Catalog
spec=importlib.util.spec_from_file_location('unit_guard',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)


def probe(out):
    catalog=Catalog.read();kinds=catalog.enums['E_HmiRequestKind'];modes=catalog.enums['E_Mode']
    checks=[];complete=False
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        def check(label,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append((label,ok));emit({'event':'check','label':label,'actual':actual,'expected':expected,'passed':ok})
            if not ok:raise AssertionError(label)
        def read(path):return api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
        def wait(predicate,label):
            until=time.monotonic()+8
            while time.monotonic()<until:
                if predicate():return
                time.sleep(.02)
            raise AssertionError(label)
        def write(values):
            emit({'event':'mutation-guard','status':UNIT.guard(),'targets':list(values)})
            results=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
            if any(e for v,e in results):raise AssertionError('native write refused')
        def test(**values):write({'GDB_StateAlarmTest.'+n:v for n,v in values.items()})
        def pulse(name):test(**{name:True});wait(lambda:not read('GDB_StateAlarmTest.'+name),name+' consumed')
        def request(kind,root='StationA',**fields):
            seq=(read(root+'.HmiRequest.Sequence')+1)&0xffffffff or 1
            args={'Kind':kinds[kind],'IntValue':0,'TextValue':'','User':'','Secret':'','TargetPath':'','DurationMs':0};args.update(fields)
            write({root+'.HmiRequest.'+n:v for n,v in args.items()});write({root+'.HmiRequest.Sequence':seq})
            wait(lambda:read(root+'.HmiResponse.AckSequence')==seq,'acknowledgement')
            return seq,read(root+'.HmiResponse.Accepted')
        def login():
            seq,ok=request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            check('login consumed',ok,True)
            wait(lambda:read('StationA.Access.LoginResultSequence')==seq and not read('StationA.Access.LoginBusy'),'login result')
            check('admin session',read('StationA.Access.CurrentLevel'),4)
        def record(prefix):
            fields=[f['member'] for f in catalog.resolve(['ST_AlarmEvent'])['ST_AlarmEvent']]
            rows=api.bulk([('PlcProgram.Read',{'var':leaf_var((prefix+'.'+f).split('.'))}) for f in fields])
            if any(e for v,e in rows):raise AssertionError('event witness unavailable')
            return dict(zip(fields,(v for v,e in rows)))
        def diag(text='test.alarm.native',reason=15001,severity=2,category=0):
            values={'ReasonCode':reason,'Description':text,'SourcePath':'StationA.Cell.Gate','IoTag':'-B101','IoAddress':'DI0.1','Severity':severity,'Category':category}
            write({'GDB_StateAlarmTest.Diag.'+n:v for n,v in values.items()})
        def clear():pulse('ClearLog')
        def mode(value):
            check('mode '+value,request('SET_MODE',IntValue=modes[value])[1],True)
            wait(lambda:read('StationA.ModeActivePublished')==modes[value],'mode result')
        try:
            api.login('fraktal');emit({'event':'connection','version':api.call('Api.Version'),'pin':api.fingerprint,'permissions':api.call('Api.GetPermissions')})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            check('state count',read('StationA.StateFlagCount'),1)
            check('state key',read('StationA.StateFlags[1].Key'),'project.state.atHome')
            check('initial derived state',read('StationA.StateFlags[1].Value'),True)
            check('initial freshness',read('StationA.StateFlags[1].Stale'),False)
            previous=read('StationA.StateFlags[1].Since');peer=read('StationB.StateFlags[1].Since')
            test(Position=7);wait(lambda:not read('StationA.StateFlags[1].Value'),'derived change')
            check('derived OutImm changes without command',read('StationA.OutImm.AtHome'),False)
            changed=read('StationA.StateFlags[1].Since');check('change timestamp updated',changed!=previous,True)
            time.sleep(.1);check('unchanged state preserves timestamp',read('StationA.StateFlags[1].Since'),changed)
            check('peer state remains true',read('StationB.StateFlags[1].Value'),True)
            check('peer timestamp isolated',read('StationB.StateFlags[1].Since'),peer)
            test(Position=0);wait(lambda:read('StationA.OutImm.AtHome'),'derived restoration')
            for index in (0,catalog.capacities['MAX_STATE_FLAGS']+1):
                test(StateIndex=index,StateValue=True,PublishState=True)
                check('invalid state index returns predicate %d'%index,read('GDB_StateAlarmTest.StandaloneReturn'),True)
                check('invalid state index does not publish %d'%index,read('GDB_StateAlarmTest.StandaloneCount'),0)
            last=catalog.capacities['MAX_STATE_FLAGS'];base='GDB_StateAlarmTest.StandaloneFlags[%d]'%last
            test(StateIndex=last);wait(lambda:read('GDB_StateAlarmTest.StandaloneCount')==last,'last state slot')
            check('last slot published',read(base+'.Value'),True)
            check('sparse gap remains unnamed',read('GDB_StateAlarmTest.StandaloneFlags[1].Key'),'')
            stamp=read(base+'.Since');test(PublishState=False);wait(lambda:read(base+'.Stale'),'lost publisher')
            check('missing publisher forces false',read(base+'.Value'),False)
            check('staleness preserves last timestamp',read(base+'.Since'),stamp)
            test(StateValue=False,PublishState=True);wait(lambda:not read(base+'.Stale'),'publication resumed')
            check('republication returns current false',read('GDB_StateAlarmTest.StandaloneReturn'),False)
            check('republication refreshes timestamp',read(base+'.Since')!=stamp,True)
            login();clear()
            wide='x'*255;diag(wide);test(ResetClass=0);pulse('RaisePulse');slot=read('GDB_StateAlarmTest.Slot')
            check('first AUTO slot',slot,1);event=record('StationA.AlarmLog.Active[%d]'%slot)
            check('full width event description',event['Description'],wide)
            check('I/O tag preserved',event['IoTag'],'-B101');check('I/O address preserved',event['IoAddress'],'DI0.1')
            check('project severity retained',event['Severity'],2);check('AUTO nonblocking',read('StationA.AlarmLog.Blocking'),False)
            check('AUTO active count',read('StationA.AlarmLog.NActive'),1)
            check('come callback',read('GDB_StateAlarmTest.SinkCome'),1)
            time.sleep(.1);pulse('GonePulse');closed=record('StationA.AlarmLog.Ring[1]')
            check('AUTO closes',closed['State'],0);check('AUTO active count clears',read('StationA.AlarmLog.NActive'),0)
            check('monotonic duration positive',int(closed['Duration'])>0,True)
            check('gone time exists',int(closed['GoneAt'])>0,True)
            check('unproven UTC quality remains false',not closed['ComeTimeSynchronized'] and not closed['GoneTimeSynchronized'],True)
            check('close callback',read('GDB_StateAlarmTest.SinkClose'),1)
            check('sink receives exact closed event',record('GDB_StateAlarmTest.SinkLast'),closed)
            pulse('GonePulse');check('second gone refused',read('GDB_StateAlarmTest.GoneAccepted'),False)
            clear();diag(reason=catalog.enums['E_Reason']['PERMISSIVE_NOT_MET'],severity=2,category=2);pulse('RaisePulse')
            event=record('StationA.AlarmLog.Active[1]');check('registered priority wins',event['Severity'],0);check('registered category wins',event['Category'],0)
            pulse('GonePulse');clear();diag('test.alarm.manual');test(ResetClass=1);pulse('RaisePulse')
            check('MANUAL blocks',read('StationA.AlarmLog.Blocking'),True);pulse('GonePulse')
            waiting=record('StationA.AlarmLog.Active[1]');check('MANUAL waits for reset',waiting['State'],2)
            check('WAIT_RESET still blocks',read('StationA.AlarmLog.Blocking'),True)
            check('WAIT_RESET has no close callback',read('GDB_StateAlarmTest.SinkClose'),0)
            check('operator reset accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:not read('StationA.AlarmLog.Blocking'),'reset closes waiting event')
            reset=record('StationA.AlarmLog.Ring[1]');check('reset event closed',reset['State'],0)
            check('reset time exists',int(reset['ResetAt'])>0,True)
            check('reset preserves come-gone duration',reset['Duration'],waiting['Duration'])
            check('reset closes active list',read('StationA.AlarmLog.NActive'),0)
            clear();diag('test.alarm.activeReset');pulse('RaisePulse')
            check('ACTIVE reset accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:not read('StationA.AlarmLog.Blocking'),'ACTIVE reset result')
            closed=record('StationA.AlarmLog.Ring[1]');check('ACTIVE reset stamps gone',int(closed['GoneAt'])>0,True)
            check('ACTIVE reset duration positive',int(closed['Duration'])>0,True)
            clear();diag('test.alarm.live');test(CauseLive=True);wait(lambda:read('StationA.AlarmLog.Blocking'),'live cause')
            mode('AUTO');check('blocking alarm denies start',request('START')[1],False)
            count=read('StationA.HmiResponse.Report.Count')
            descriptions=[read('StationA.HmiResponse.Report.Reasons[%d].Description'%i) for i in range(1,count+1)]
            check('release explains manual reset', 'std.release.manualReset' in descriptions,True)
            check('live reset accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:read('StationA.AlarmLog.Blocking'),'live condition re-raised')
            check('reset does not erase condition',read('GDB_StateAlarmTest.CauseLive'),True)
            check('live condition still denies start',request('START')[1],False)
            check('peer log remains nonblocking',read('StationB.AlarmLog.Blocking'),False)
            test(CauseLive=False);wait(lambda:read('StationA.AlarmLog.Active[1].State')==2,'condition gone')
            check('one reset after restore accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:not read('StationA.AlarmLog.Blocking'),'restored reset')
            check('start is restartable',request('START')[1],True);wait(lambda:read('StationA.RunningPublished'),'run starts')
            diag('test.alarm.running');pulse('RaisePulse')
            check('reset with running command accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:not read('StationA.RunningPublished') and read('StationA.Status.State')==0,'running reset')
            check('child command withdrawn',read('GDB_UnitTest.ChildExecute'),False)
            mode('MANUAL');clear()
            check('manual fault accepted',request('MANUAL_COMMAND',TargetPath='StationA.Cell.Gate',IntValue=4)[1],True)
            wait(lambda:read('StationA.AlarmLog.NActive')==1,'automatic descendant fault capture')
            fault=record('StationA.AlarmLog.Active[1]');check('fault source canonical',fault['SourcePath'],'StationA.Cell.Gate')
            check('fault first-out retained',fault['Description'],'test.first')
            check('fault is manual reset',fault['ResetClass'],1)
            wait(lambda:read('StationA.AlarmLog.Active[1].State')==2,'automatic gone')
            check('descendant fault remains blocking',read('StationA.AlarmLog.Blocking'),True)
            check('descendant reset accepted',request('OPERATOR_RESET')[1],True)
            wait(lambda:not read('StationA.AlarmLog.Blocking'),'descendant reset done')
            clear()
            check('hold command accepted',request('MANUAL_COMMAND',TargetPath='StationA.Cell.Gate',IntValue=3)[1],True)
            write({'GDB_RoutingTest.PermitOne':False})
            wait(lambda:read('StationA.Cell.Gate.Held'),'manual hold')
            check('HELD withdraws output',read('StationA.Cell.Gate.OutImm.Output'),False)
            check('HELD has no fault event',read('StationA.AlarmLog.NActive'),0)
            check('HELD does not block as an alarm',read('StationA.AlarmLog.Blocking'),False)
            write({'GDB_RoutingTest.PermitOne':True})
            wait(lambda:not read('StationA.Cell.Gate.Held'),'hold restoration')
            check('reset releases held command',request('OPERATOR_RESET')[1],True)
            wait(lambda:read('StationA.Cell.Gate.Status.State')==0,'held command released')
            clear();diag('test.alarm.capacity');test(ResetClass=0,FillCount=catalog.capacities['MAX_ALARM_RING']+1);pulse('FillPulse')
            check('closed ring wraps',read('StationA.AlarmLog.RingHead'),1)
            check('ring overwrite reported',read('StationA.AlarmLog.Truncated'),True)
            check('ring events do not block',read('StationA.AlarmLog.Blocking'),False)
            check('ring callback comes',read('GDB_StateAlarmTest.SinkCome'),catalog.capacities['MAX_ALARM_RING']+1)
            check('ring callback closes',read('GDB_StateAlarmTest.SinkClose'),catalog.capacities['MAX_ALARM_RING']+1)
            clear();test(ResetClass=1,FillCount=catalog.capacities['MAX_ALARM_ACTIVE']+1);pulse('FillPulse')
            check('active capacity bounded',read('StationA.AlarmLog.NActive'),catalog.capacities['MAX_ALARM_ACTIVE'])
            check('active overflow reported',read('StationA.AlarmLog.Truncated'),True)
            check('overflow callback not fabricated',read('GDB_StateAlarmTest.SinkCome'),catalog.capacities['MAX_ALARM_ACTIVE'])
            check('all active events reset',request('OPERATOR_RESET')[1],True)
            wait(lambda:read('StationA.AlarmLog.NActive')==0,'capacity reset')
            clear();test(ResetClass=2);pulse('RaisePulse');check('invalid reset class rejected',read('GDB_StateAlarmTest.Slot'),0)
            for path in ('StationA.AlarmLog.ComeMs[1]','StationA.AlarmLog.Touched[1]','StationA.AlarmLog.SinkEnabled','StationA.StateTouched[1]'):
                rows=api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})]);check('private read '+path,rows[0][1]['code'],200)
            for path,value in (('StationA.AlarmLog.Blocking',False),('StationA.AlarmLog.Active[1].State',0),('StationA.StateFlags[1].Value',False)):
                emit({'event':'mutation-guard','status':UNIT.guard(),'targets':[path]})
                rows=api.bulk([('PlcProgram.Write',{'var':leaf_var(path.split('.')),'value':value})]);check('authority write '+path,rows[0][1]['code'],205)
            diag('test.alarm.restart');test(ResetClass=1);pulse('RaisePulse')
            for action in ('halt','run'):
                emit({'event':'mode-guard','status':UNIT.guard(),'action':action})
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                if result.returncode:raise AssertionError('native mode failed')
                emit({'event':'mode-result','output':result.stdout.decode('utf-8-sig')})
            check('restart active list clear',read('StationA.AlarmLog.NActive'),0)
            check('restart ring clear',read('StationA.AlarmLog.RingHead'),0)
            check('restart does not claim retained alarms',read('StationA.AlarmLog.Blocking'),False)
            check('restart derived state recomputed',read('StationA.StateFlags[1].Value'),True)
            check('restart session cleared',read('StationA.Access.CurrentLevel'),0)
            complete=True
        finally:
            api.conn.close()
            if not complete:checks.append(('probe completed',False))
            emit({'event':'summary','checks':len(checks),'failures':sum(not ok for n,ok in checks),'completed':complete})
            suite=ET.Element('testsuite',name='Fraktal.TIA.StateAlarm',tests=str(len(checks)),failures=str(sum(not ok for n,ok in checks)))
            for name,ok in checks:
                case=ET.SubElement(suite,'testcase',name=name)
                if not ok:ET.SubElement(case,'failure',message=name)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)


if __name__=='__main__':probe(Path(sys.argv[1]))
