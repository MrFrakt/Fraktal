"""Native active-latch recovery, timing, startup fence and close-journal checks."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[1]/'tools'),str(HERE.parent/'ConfigSets')]
from tia_webapi import WebApi,leaf_var
from native_mailbox import Mailbox
from fraktal_tia_binding import Catalog
from fraktal_tia_alarms import RECOVERY_POLICY
spec=importlib.util.spec_from_file_location('guard',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)
SELECTED=('StationA','StationA.Satellite')
def probe(out, *, expect_medium=False):
    checks=[];complete=False;c=Catalog.read();lost=json.loads(RECOVERY_POLICY.read_bytes())['reason']
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api=WebApi('169.254.212.49',pin,False)
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(r):stream.write(json.dumps(r,ensure_ascii=True)+'\n');stream.flush()
        def guard():
            for attempt in range(3):
                try:return UNIT.guard()
                except RuntimeError as error:
                    if str(error)!='simulator identity unavailable' or attempt==2:raise
                    time.sleep(.2*(attempt+1))
        def check(label,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append((label,ok));emit(dict(event='check',label=label,actual=actual,expected=expected,passed=ok));assert ok,label
        def until(f,label):
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if f():return
                time.sleep(.02)
            raise AssertionError(label)
        def writes(fields):
            emit(dict(event='fixture-guard',targets=list(fields),status=guard()))
            r=api.bulk([('PlcProgram.Write',dict(var=leaf_var(p.split('.')),value=v)) for p,v in fields.items()]);assert not any(e for v,e in r)
        def stimulus(op,scope='StationA',event_slot=1,reason=15300,text='test.alarm.recovery',reset=1,automatic=False):
            writes({'GDB_AlarmRecoveryTest.'+n:v for n,v in dict(Scope=scope,EventSlot=event_slot,Reason=reason,Text=text,ResetClass=reset,Automatic=automatic).items()})
            writes({'GDB_AlarmRecoveryTest.Operation':op});until(lambda:box.read('GDB_AlarmRecoveryTest.Operation')==0,'fixture consumed')
            return box.read('GDB_AlarmRecoveryTest.ReturnSlot')
        def clear_all():
            writes({'GDB_AlarmRecoveryTest.StickyCause':False,'GDB_StateAlarmTest.CauseLive':False})
            for scope in (*SELECTED,'StationB'):stimulus(3,scope)
        def record(scope,slot=1,ring=False):
            fields=[f['member'] for f in c.resolve(['ST_AlarmEvent'])['ST_AlarmEvent']]
            prefix=scope+'.AlarmLog.'+('Ring' if ring else 'Active')+'['+str(slot)+'].'
            r=api.bulk([('PlcProgram.Read',dict(var=leaf_var((prefix+n).split('.')))) for n in fields]);assert not any(e for v,e in r)
            return dict(zip(fields,(v for v,e in r)))
        def login():
            assert box.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            until(lambda:not box.read('StationA.Access.LoginBusy'),'login');check('admin login',box.read('StationA.Access.CurrentLevel'),4)
            assert box.request('SET_SESSION_TIMEOUT',DurationMs=0)
        def mode(value):
            assert box.request('SET_MODE',IntValue=c.enums['E_Mode'][value])
            until(lambda:box.read('StationA.ModeActivePublished')==c.enums['E_Mode'][value],'mode settled')
        def cycle(power=False):
            nonlocal api,box
            before=box.read('GDB_AccessPersistTest.StartupCount')
            if power:api.conn.close()
            commands=[(HERE.parent/'Config/cycle_simulator.ps1',None)] if power else [(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1',a) for a in ('halt','run')]
            for script,action in commands:
                emit(dict(event='restart-guard',power=power,action=action,status=guard()))
                cmd=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)]
                if action:cmd+=['-Action',action]
                r=subprocess.run(cmd,capture_output=True);emit(dict(event='restart-result',exit_code=r.returncode,output=r.stdout.decode('utf-8-sig').strip()));assert r.returncode==0
            if power:api=WebApi('169.254.212.49',pin,False);api.login('fraktal');box=Mailbox(api,guard,emit)
            until(lambda:box.read('GDB_AccessPersistTest.StartupCount')>before,'complete forest startup')
            if expect_medium:
                until(lambda:not box.read('FRK_PersistStatus.Restoring'),'document restore barrier')
            check('restart session cleared',box.read('StationA.Access.CurrentLevel'),0)
            check('restart Unit not running',box.read('StationA.RunningPublished'),False)
            check('restart child execute low',box.read('StationA.Cell.Gate.Execute'),False)
            check('restart child output low',box.read('StationA.Cell.Gate.OutImm.Output'),False)
        def denied_start(label):
            check(label,box.request('START'),False)
            count=box.read('StationA.HmiResponse.Report.Count')
            reasons=[box.read('StationA.HmiResponse.Report.Reasons['+str(i)+'].Description') for i in range(1,count+1)]
            check(label+' names manual latch','std.release.manualReset' in reasons,True)
        try:
            api.login('fraktal');box=Mailbox(api,guard,emit)
            clear_all();cycle();login();mode('AUTO');clear_all()
            # Explicit ACTIVE and WAIT_RESET survive; unselected Unit stays volatile.
            originals={}
            for scope in (*SELECTED,'StationB'):
                slot=stimulus(1,scope);check('initial slot '+scope,slot,1)
                originals[scope]=record(scope)
            time.sleep(.12)
            stimulus(2,'StationA.Satellite');waiting=record('StationA.Satellite')
            check('manual gone waits',waiting['State'],2)
            writes({'GDB_AlarmRecoveryTest.Scope':'StationA','GDB_AlarmRecoveryTest.EventSlot':1})
            saved=box.read('GDB_AlarmRecoveryTest.Elapsed');check('elapsed checkpoint positive',saved>0,True)
            cycle()
            check('ACTIVE record restored',record('StationA'),originals['StationA'])
            check('WAIT_RESET record restored',record('StationA.Satellite'),waiting)
            check('unselected active volatile',box.read('StationB.AlarmLog.NActive'),0)
            check('restore callback not replayed',box.read('GDB_StateAlarmTest.SinkCome'),0)
            check('restore latches block',box.read('StationA.AlarmLog.Blocking'),True)
            login();mode('AUTO');denied_start('restored latches refuse start')
            cycle(True);check('power ACTIVE record restored',record('StationA'),originals['StationA'])
            check('power WAIT_RESET record restored',record('StationA.Satellite'),waiting)
            login();mode('AUTO');denied_start('power latches refuse start')
            check('one operator reset accepted',box.request('OPERATOR_RESET'),True)
            until(lambda:not box.read('StationA.AlarmLog.Blocking') and not box.read('StationA.Satellite.AlarmLog.Blocking'),'cascade reset')
            check('reset child execute stays low',box.read('StationA.Cell.Gate.Execute'),False)
            check('reset child output stays low',box.read('StationA.Cell.Gate.OutImm.Output'),False)
            check('restartable after reset',box.request('START'),True)
            until(lambda:box.read('StationA.RunningPublished'),'running after reset')
            assert box.request('STOP');writes({'GDB_UnitTest.FinishCycle':True});until(lambda:not box.read('StationA.RunningPublished'),'stop complete');writes({'GDB_UnitTest.FinishCycle':False})
            # Controller-running duration accumulates without outage or unsigned epoch jump.
            clear_all();slot=stimulus(1);time.sleep(.15)
            writes({'GDB_AlarmRecoveryTest.Scope':'StationA','GDB_AlarmRecoveryTest.EventSlot':slot});first=box.read('GDB_AlarmRecoveryTest.Elapsed')
            cycle(True);time.sleep(.15)
            stimulus(2,event_slot=slot);duration=int(record('StationA',slot)['Duration'])
            check('duration includes pre-restart observation',duration>=first,True)
            check('duration bounded after clock rebasing',duration<30000,True)
            frozen=record('StationA',slot);cycle();check('WAIT_RESET duration frozen',record('StationA',slot),frozen)
            stimulus(4);cycle();check('closed latch does not return',box.read('StationA.AlarmLog.NActive'),0)
            # Runtime ownership is re-evaluated; automatic faults gone become WAIT_RESET.
            clear_all();slot=stimulus(1,automatic=True,reason=15301)
            cycle();check('captured fault re-evaluated gone',record('StationA',slot)['State'],2)
            check('captured fault stays blocking',box.read('StationA.AlarmLog.Blocking'),True)
            stimulus(4);clear_all()
            slot=stimulus(1,reset=0,reason=15302);cycle();check('AUTO_RESET never retained',box.read('StationA.AlarmLog.NActive'),0)
            # Actual fault capture retains the first-out and releases commands on reboot.
            login();mode('MANUAL');clear_all()
            check('actual child fault command accepted',box.request('MANUAL_COMMAND',TargetPath='StationA.Cell.Gate',IntValue=4),True)
            until(lambda:box.read('StationA.AlarmLog.NActive')==1,'captured child fault')
            until(lambda:record('StationA')['State']==2,'child fault gone')
            fault=record('StationA');cycle(True);check('actual first-out restored',record('StationA'),fault)
            login();check('actual fault one reset',box.request('OPERATOR_RESET'),True)
            until(lambda:not box.read('StationA.AlarmLog.Blocking'),'actual fault reset')
            # A live owner reclaims its occurrence; deliberate reset never clears its condition.
            clear_all();writes({'GDB_AlarmRecoveryTest.StickyCause':True})
            until(lambda:box.read('GDB_AlarmRecoveryTest.CauseSlot')>0,'sticky cause raised')
            original=record('StationA');cycle();check('live cause restores same occurrence',record('StationA'),original)
            check('live cause not duplicated',box.read('StationA.AlarmLog.NActive'),1)
            login();check('live cause deliberate reset',box.request('OPERATOR_RESET'),True)
            until(lambda:box.read('StationA.AlarmLog.NActive')==1,'cause re-raised')
            check('reset preserves live condition',box.read('GDB_AlarmRecoveryTest.StickyCause'),True)
            check('reset re-raises new occurrence',record('StationA')['ComeAt']!=original['ComeAt'],True)
            writes({'GDB_AlarmRecoveryTest.StickyCause':False});until(lambda:record('StationA')['State']==2,'sticky cause gone')
            assert box.request('OPERATOR_RESET');clear_all()
            # Parent must be blocked before a selected descendant has finished startup.
            mode('AUTO');stimulus(6)
            check('startup fence sees pending descendant',box.read('GDB_AlarmRecoveryTest.StartupBlocked'),True)
            denied_start('unfinished descendant refuses start');stimulus(7)
            check('startup fence released',box.read('GDB_AlarmRecoveryTest.StartupBlocked'),False)
            # Both journal interruption points close exactly once without callback replay.
            for phase in (40,41):
                clear_all();slot=stimulus(1,reason=15340+phase);stimulus(2,event_slot=slot)
                stimulus(phase,event_slot=slot);head=box.read('StationA.AlarmLog.RingHead')
                cycle(True)
                check('journal active cleared '+str(phase),box.read('StationA.AlarmLog.NActive'),0)
                check('journal closes exactly once '+str(phase),box.read('StationA.AlarmLog.RingHead'),head+(phase==40))
                item=record('StationA',box.read('StationA.AlarmLog.RingHead'),True)
                check('journal closed correct occurrence '+str(phase),item['ReasonCode'],15340+phase)
                check('journal no close callback replay '+str(phase),box.read('GDB_StateAlarmTest.SinkClose'),0)
                cycle();check('journal not repeated '+str(phase),box.read('StationA.AlarmLog.RingHead'),head+(phase==40))
            # Whole-image rejection is blocking, visible and independent of closed history/peers.
            for damage in range(1,11):
                clear_all();stimulus(1,reason=15400+damage);stimulus(1,'StationA.Satellite',reason=15500+damage)
                stimulus(2,'StationA.Satellite');peer=record('StationA.Satellite')
                writes({'GDB_AlarmRecoveryTest.Scope':'StationA','GDB_AlarmRecoveryTest.Damage':damage})
                cycle()
                item=record('StationA');check('corrupt image loss reason '+str(damage),item['ReasonCode'],lost['code'])
                check('corrupt image description '+str(damage),item['Description'],lost['description'])
                check('corrupt image manual latch '+str(damage),item['ResetClass'],1)
                check('corrupt image blocks '+str(damage),box.read('StationA.AlarmLog.Blocking'),True)
                check('corrupt image no false prefix '+str(damage),box.read('StationA.AlarmLog.NActive'),1)
                check('corrupt image preserves peer '+str(damage),record('StationA.Satellite'),peer)
                cycle();check('loss latch persists '+str(damage),record('StationA')['ReasonCode'],lost['code'])
                login();check('loss acknowledged by reset '+str(damage),box.request('OPERATOR_RESET'),True)
                until(lambda:not box.read('StationA.AlarmLog.Blocking'),'loss reset')
                cycle();check('loss reset retained '+str(damage),box.read('StationA.AlarmLog.NActive'),0)
            # Private images/timing, and published readonly alarm fields keep their boundaries.
            for path in ('FRK_AlarmRecovery.Rows[1].SchemaVersion','FRK_AlarmRecoveryRuntime.Ready[1]','StationA.AlarmLog.ElapsedBefore[1]','StationA.AlarmLog.Recovering[1]'):
                r=api.bulk([('PlcProgram.Read',dict(var=leaf_var(path.split('.'))))])[0];check('private read '+path,r[1]['code'],200)
            for path,value in (('FRK_AlarmRecovery.Rows[1].SchemaVersion',0),('StationA.AlarmLog.Active[1].State',0)):
                emit(dict(event='write-refusal-guard',target=path,status=guard()))
                r=api.bulk([('PlcProgram.Write',dict(var=leaf_var(path.split('.')),value=value))])[0];check('write refusal '+path,r[1]['code'],200 if path.startswith('FRK') else 205)
            clear_all();cycle(True);complete=True
        finally:
            api.conn.close()
            if not complete:checks.append(('probe completed',False))
            emit(dict(event='summary',checks=len(checks),failures=sum(not ok for n,ok in checks),completed=complete))
            suite=ET.Element('testsuite',name='Fraktal.TIA.AlarmRecovery',tests=str(len(checks)),failures=str(sum(not ok for n,ok in checks)))
            for name,ok in checks:
                case=ET.SubElement(suite,'testcase',name=name)
                if not ok:ET.SubElement(case,'failure',message=name)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)
if __name__=='__main__':probe(Path(sys.argv[1]))
