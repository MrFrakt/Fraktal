"""Native closed-history restart, corruption, isolation and privacy qualification."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[1]/'tools'),str(HERE.parent/'ConfigSets')]
from tia_webapi import WebApi,leaf_var
from native_mailbox import Mailbox
from fraktal_tia_binding import Catalog
spec=importlib.util.spec_from_file_location('guard',HERE.parent/'Unit/probe_web.py')
UNIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(UNIT)
SCOPES=('StationA','StationA.Satellite','StationB')
def probe(out, *, expect_recovery=False):
    checks=[];complete=False
    pin=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin'
    api=WebApi('169.254.212.49',pin,False)
    with out.open('x',encoding='ascii',newline='\n') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        def guard():
            for attempt in range(3):
                try:return UNIT.guard()
                except RuntimeError as error:
                    if str(error)!='simulator identity unavailable' or attempt==2:raise
                    emit(dict(event='identity-read-retry',attempt=attempt+1));time.sleep(.2*(attempt+1))
        def check(name,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append((name,ok));emit(dict(event='check',label=name,actual=actual,expected=expected,passed=ok))
            assert ok,name
        def until(predicate,label):
            end=time.monotonic()+10
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.02)
            raise AssertionError(label)
        def writes(fields):
            emit(dict(event='fixture-guard',targets=list(fields),status=guard()))
            rows=api.bulk([('PlcProgram.Write',dict(var=leaf_var(p.split('.')),value=v)) for p,v in fields.items()])
            errors=[dict(path=p,error=e) for p,(v,e) in zip(fields,rows) if e]
            if errors:emit(dict(event='fixture-write-errors',errors=errors))
            assert not errors
        def stimulus(operation,scope='StationA',text='test.alarm.retained',reason=15011,unicode=0):
            writes({'GDB_AlarmPersistTest.Scope':scope,'GDB_AlarmPersistTest.Text':text,'GDB_AlarmPersistTest.Reason':reason,'GDB_AlarmPersistTest.UnicodeMode':unicode})
            writes({'GDB_AlarmPersistTest.Operation':operation})
            until(lambda:box.read('GDB_AlarmPersistTest.Operation')==0,'fixture consumed')
        def event(scope,index):
            fields=[f['member'] for f in Catalog.read().resolve(['ST_AlarmEvent'])['ST_AlarmEvent']]
            rows=api.bulk([('PlcProgram.Read',dict(var=leaf_var((scope+'.AlarmLog.Ring['+str(index)+'].'+f).split('.')))) for f in fields])
            assert not any(e for v,e in rows)
            return dict(zip(fields,(v for v,e in rows)))
        def cycle(power=False):
            nonlocal api,box
            before=box.read('GDB_AccessPersistTest.StartupCount')
            if power:api.conn.close()
            commands=[(HERE.parent/'Config/cycle_simulator.ps1',None)] if power else [(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1',a) for a in ('halt','run')]
            for script,action in commands:
                emit(dict(event='restart-guard',power=power,action=action,status=guard()))
                command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)]
                if action:command+=['-Action',action]
                r=subprocess.run(command,capture_output=True)
                emit(dict(event='restart-result',exit_code=r.returncode,output=r.stdout.decode('utf-8-sig').strip()))
                assert r.returncode==0
            if power:
                api=WebApi('169.254.212.49',pin,False);api.login('fraktal');box=Mailbox(api,guard,emit)
            until(lambda:box.read('GDB_AccessPersistTest.StartupCount')>before,'complete startup')
            for root in ('StationA','StationB'):check('restart session '+root,box.read(root+'.Access.CurrentLevel'),0)
        try:
            api.login('fraktal');box=Mailbox(api,guard,emit)
            for scope in SCOPES:stimulus(2,scope)
            texts={s:'history '+s+' '+chr(0x03bb)+' '+chr(0x4e2d) for s in SCOPES}
            for scope in SCOPES:
                stimulus(1,scope,'history '+scope+' ',unicode=1);check('seed ring '+scope,box.read(scope+'.AlarmLog.RingHead'),1)
                check('seed complete '+scope,box.read(scope+'.AlarmLog.Truncated'),False)
                check('seed Unicode '+scope,event(scope,1)['Description'],texts[scope])
            before={s:event(s,1) for s in SCOPES}
            cycle()
            for scope in SCOPES:
                check('STOP/RUN record '+scope,event(scope,1),before[scope])
                check('STOP/RUN head '+scope,box.read(scope+'.AlarmLog.RingHead'),1)
                check('STOP/RUN closed history nonblocking '+scope,box.read(scope+'.AlarmLog.Blocking'),False)
            check('restore does not replay sink comes',box.read('GDB_StateAlarmTest.SinkCome'),0)
            check('restore does not replay sink closes',box.read('GDB_StateAlarmTest.SinkClose'),0)
            cycle(True)
            for scope in SCOPES:check('power record '+scope,event(scope,1),before[scope])
            # Long, wide text and all timestamp/duration/quality fields participate.
            stimulus(2);long_text=(chr(0x03bb)+chr(0x4e2d)+'x')*85
            stimulus(1,text='',unicode=2);long_event=event('StationA',1)
            check('255-character Unicode',long_event['Description'],long_text)
            cycle(True);check('long full record restored',event('StationA',1),long_event)
            # Explicit manual close records a real monotonic duration and reset stamp.
            writes({'GDB_StateAlarmTest.Diag.ReasonCode':15012,'GDB_StateAlarmTest.Diag.Description':'test.alarm.duration',
                'GDB_StateAlarmTest.Diag.SourcePath':'StationA.Cell.Gate','GDB_StateAlarmTest.Diag.IoTag':'-B101',
                'GDB_StateAlarmTest.Diag.IoAddress':'DI0.1','GDB_StateAlarmTest.Diag.Severity':2,'GDB_StateAlarmTest.Diag.Category':0,
                'GDB_StateAlarmTest.ResetClass':1,'GDB_StateAlarmTest.RaisePulse':True})
            until(lambda:not box.read('GDB_StateAlarmTest.RaisePulse'),'raised')
            time.sleep(.12)
            writes({'GDB_StateAlarmTest.GonePulse':True});until(lambda:not box.read('GDB_StateAlarmTest.GonePulse'),'gone')
            assert box.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
            until(lambda:not box.read('StationA.Access.LoginBusy'),'login');check('reset admin',box.read('StationA.Access.CurrentLevel'),4)
            check('manual event reset accepted',box.request('OPERATOR_RESET'),True)
            head=box.read('StationA.AlarmLog.RingHead');records=[event('StationA',i) for i in range(1,head+1)]
            closed=next(e for e in records if e['ReasonCode']==15012)
            check('manual record reason',closed['ReasonCode'],15012)
            check('manual duration positive',int(closed['Duration'])>0,True)
            check('manual reset timestamp exists',bool(closed['ResetAt']),True)
            # Logout produces an audit event; snapshot after that final mutation.
            assert box.request('LOGOUT');head=box.read('StationA.AlarmLog.RingHead')
            snapshot=[event('StationA',i) for i in range(1,head+1)]
            cycle();check('manual and audit records retained',[event('StationA',i) for i in range(1,head+1)],snapshot)
            # Full-ring wrap and overflow survive restart in chronological positions.
            stimulus(2)
            for i in range(65):stimulus(1,text='retained ordinal '+str(i),reason=15020+i)
            check('ring wraps',box.read('StationA.AlarmLog.RingHead'),1)
            check('overflow visible',box.read('StationA.AlarmLog.Truncated'),True)
            wrap=[event('StationA',i) for i in range(1,65)]
            cycle(True)
            check('full wrapped records retained',[event('StationA',i) for i in range(1,65)],wrap)
            check('wrapped newest',event('StationA',1)['Description'],'retained ordinal 64')
            check('overflow retained',box.read('StationA.AlarmLog.Truncated'),True)
            # Worst supported text occupancy exercises bounded startup validation.
            stimulus(2)
            for i in range(64):stimulus(1,text='',unicode=2,reason=15100+i)
            cycle(True)
            check('full Unicode ring head',box.read('StationA.AlarmLog.RingHead'),64)
            check('full Unicode oldest',event('StationA',1)['Description'],long_text)
            check('full Unicode newest',event('StationA',64)['Description'],long_text)
            check('full Unicode ring complete',box.read('StationA.AlarmLog.Truncated'),False)
            # A full active list must not rewrite the same retained overflow flag.
            stimulus(2)
            writes({'GDB_StateAlarmTest.Diag.ReasonCode':15080,'GDB_StateAlarmTest.Diag.Description':'test.alarm.capacity',
                'GDB_StateAlarmTest.Diag.SourcePath':'StationA.Cell.Gate','GDB_StateAlarmTest.Diag.Severity':2,
                'GDB_StateAlarmTest.Diag.Category':0,'GDB_StateAlarmTest.ResetClass':1,'GDB_StateAlarmTest.FillCount':17,
                'GDB_StateAlarmTest.FillPulse':True,'GDB_AlarmPersistTest.Scope':'StationA'})
            until(lambda:not box.read('GDB_StateAlarmTest.FillPulse'),'active capacity filled')
            check('full active count',box.read('StationA.AlarmLog.NActive'),16)
            check('full active loss visible',box.read('StationA.AlarmLog.Truncated'),True)
            generation=box.read('GDB_AlarmPersistTest.Generation')
            for i in range(3):
                writes({'GDB_StateAlarmTest.RaisePulse':True})
                until(lambda:not box.read('GDB_StateAlarmTest.RaisePulse'),'capacity raise consumed')
                check('repeated full raise refused '+str(i),box.read('GDB_StateAlarmTest.Slot'),0)
                check('full-table generation stable '+str(i),box.read('GDB_AlarmPersistTest.Generation'),generation)
            cycle()
            check('active-overflow history marker retained',box.read('StationA.AlarmLog.Truncated'),True)
            check('active recovery profile',box.read('StationA.AlarmLog.NActive'),Catalog.read().capacities['MAX_ALARM_ACTIVE'] if expect_recovery else 0)
            if expect_recovery:stimulus(2)
            # No per-scan image rewrite for an idle log.
            writes({'GDB_AlarmPersistTest.Scope':'StationA'})
            generation=box.read('GDB_AlarmPersistTest.Generation');time.sleep(.15)
            check('idle image generation stable',box.read('GDB_AlarmPersistTest.Generation'),generation)
            for path in ('FRK_AlarmHistory.Rows[1].Scope','FRK_AlarmHistory.Commissioned[1]','StationA.AlarmLog.HistorySlot'):
                result=api.bulk([('PlcProgram.Read',dict(var=leaf_var(path.split('.'))))])[0]
                check('private read '+path,result[1]['code'],200)
            for path,value in (('FRK_AlarmHistory.Rows[1].SchemaVersion',1),('StationA.AlarmLog.Ring[1].Description','tamper')):
                emit(dict(event='write-refusal-guard',target=path,status=guard()))
                result=api.bulk([('PlcProgram.Write',dict(var=leaf_var(path.split('.')),value=value))])[0]
                check('private/authority write '+path,result[1]['code'],200 if path.startswith('FRK_') else 205)
            # Whole-image failure: no accepted prefix, peer and nested Unit unchanged.
            witnesses={s:event(s,1) for s in SCOPES[1:]}
            for operation in range(10,18):
                stimulus(2);stimulus(1,text='first '+str(operation));stimulus(1,text='second '+str(operation))
                stimulus(operation);cycle()
                check('reject head '+str(operation),box.read('StationA.AlarmLog.RingHead'),0)
                check('reject first row '+str(operation),event('StationA',1)['ReasonCode'],0)
                check('reject visible '+str(operation),box.read('StationA.AlarmLog.Truncated'),True)
                check('reject not blocking '+str(operation),box.read('StationA.AlarmLog.Blocking'),False)
                for scope,witness in witnesses.items():check('reject isolation '+str(operation)+' '+scope,event(scope,1),witness)
                # Loss witness persists after reinitialization and new events.
                stimulus(1,text='after rejection '+str(operation));cycle()
                check('loss witness retained '+str(operation),box.read('StationA.AlarmLog.Truncated'),True)
                check('new history retained '+str(operation),event('StationA',1)['Description'],'after rejection '+str(operation))
            # Deliberately clear the test histories, then prove the empty image is valid.
            for scope in SCOPES:stimulus(2,scope)
            cycle(True)
            for scope in SCOPES:
                check('explicit clear retained '+scope,box.read(scope+'.AlarmLog.RingHead'),0)
                check('explicit clear complete '+scope,box.read(scope+'.AlarmLog.Truncated'),False)
            complete=True
        finally:
            api.conn.close()
            if not complete:checks.append(('probe completed',False))
            emit(dict(event='summary',checks=len(checks),failures=sum(not ok for n,ok in checks),completed=complete))
            suite=ET.Element('testsuite',name='Fraktal.TIA.AlarmPersistence',tests=str(len(checks)),failures=str(sum(not ok for n,ok in checks)))
            for name,ok in checks:
                case=ET.SubElement(suite,'testcase',name=name)
                if not ok:ET.SubElement(case,'failure',message=name)
            ET.ElementTree(suite).write(out.with_suffix('.junit.xml'),encoding='utf-8',xml_declaration=True)
if __name__=='__main__':probe(Path(sys.argv[1]))
