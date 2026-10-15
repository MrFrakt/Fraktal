"""Native frontier/history/annotation checks with synthetic sequence events."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from fraktal_tia_binding import Catalog
from tia_webapi import WebApi,leaf_var
from tia_mailbox import Mailbox
from tia_target_guard import guard


def probe(out, *, expect_medium=False):
    checks=[];complete=False
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    c='GDB_SequenceViewTest.'
    with out.open('x',encoding='ascii',newline='\n') as f:
        def emit(value):f.write(json.dumps(value,ensure_ascii=True)+'\n');f.flush()
        def read(path):return api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
        def check(label,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append(ok);emit(dict(event='check',label=label,actual=actual,expected=expected,passed=ok))
            if not ok:raise AssertionError(label)
        def wait(pred,label,seconds=8):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if pred():return
                time.sleep(.02)
            raise AssertionError(label)
        def write(values):
            emit({'event':'mutation-guard','targets':list(values),'status':guard()})
            replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
            if any(e for v,e in replies):
                emit({'event':'write-errors','errors':[{'path':p,'error':e} for p,(v,e) in zip(values,replies) if e]})
                raise AssertionError('native write refused')
        def controls(**values):
            # Native batch writes may span scans. Commit a complete structural
            # record by enabling it last; intermediate shapes are not visits.
            structural={'Enabled','Owner','StepNo','StepName','Branch','Depth','Visit','Parent','UseHelper','HelperOffset'}
            if structural.intersection(values):
                enabled=values.pop('Enabled',read(c+'Enabled'))
                write({c+'Enabled':False})
                if values:write({c+n:v for n,v in values.items()})
                if enabled:write({c+'Enabled':True})
            else:
                write({c+n:v for n,v in values.items()})
            time.sleep(.03)
        def query():
            entries=[];page=0
            while True:
                check('manifest page acknowledged',mail.request('QUERY_CONFIG',IntValue=page),True)
                base='StationA.HmiResponse.ConfigPage';count=read(base+'.EntryCount');pages=read(base+'.PageCount')
                fields=('Scope','Item','ValueText','Writable','WriteKey')
                paths=[base+'.Entries[%d].%s'%(slot,n) for slot in range(1,count+1) for n in fields]
                replies=api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
                assert not any(e for v,e in replies)
                values=[v for v,e in replies];entries += [dict(zip(fields,values[i:i+len(fields)])) for i in range(0,len(values),len(fields))]
                if page+1>=pages:return entries
                page+=1
        def row(i,n):return read('StationA.SequenceSteps[%d].%s'%(i,n))
        def cursor(b,n):return read('StationA.ActiveSteps[%d].%s'%(b,n))
        def mode(mode):
            check('mode '+mode+' acknowledged',mail.request('SET_MODE',IntValue=Catalog.read().enums['E_Mode'][mode]),True)
            wait(lambda:read('StationA.ModeActivePublished')==Catalog.read().enums['E_Mode'][mode],'mode committed')
        try:
            api.login('fraktal');mail=Mailbox(api,guard,emit)
            if expect_medium:
                wait(lambda:not read('FRK_PersistStatus.Restoring') and all(not read(r+'.ConfigPersist.Pending') for r in ('StationA','StationB')),'selected medium ready',seconds=65)
            emit({'event':'connection','status':guard(),'pin':api.fingerprint})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            check('admin login consumed',mail.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN']),True)
            wait(lambda:not read('StationA.Access.LoginBusy') and read('StationA.Access.CurrentLevel')==4,'admin authenticated')
            controls(Enabled=False,Annotate=False,AwaitEnabled=False,Parent=False,Owner=1,UseHelper=False)
            if read('StationA.SequenceStepCount'):
                mode('AUTO');mode('MANUAL')
            check('view selected',read('StationA.SequenceViewEnabled'),True)
            check('initial rows',read('StationA.SequenceStepCount'),0)
            check('initial annotations',read('StationA.SequenceAnnotationCount'),0)
            for path in ('StationA.SequenceStepDef[1].StepNo','StationA.SequenceViewBook.Overflow','FRK_ViewScratch.Step.StepNo'):
                replies=api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])
                check('private definition/storage '+path,replies[0][1]['code'],200)
            for path,value in [('StationA.SequenceStepCount',9),('StationA.SequenceSteps[1].Visited',True),('StationA.ActiveSteps[0].RowIdx',1),('StationA.SequenceAnnotations[1].Key','bad'),('StationA.CurrentStep.StepNo',99)]:
                emit({'event':'mutation-guard','target':path,'status':guard()})
                reply=api.bulk([('PlcProgram.Write',{'var':leaf_var(path.split('.')),'value':value})])[0]
                check('readonly '+path,reply[1]['code'],205)
            revision=read('StationA.ConfigRev')
            controls(StepNo=10,StepName='test.main',Branch=0,Depth=0,Visit=1,Elapsed=50,ExpectedTime=40,Enabled=True,FastPulse=True)
            wait(lambda:read('StationA.SequenceStepCount')==2 and not read(c+'FastPulse'),'fast visit recorded')
            check('fast row retained',row(2,'Visited'),True)
            check('fast duration retained',row(2,'LastDuration'),2)
            check('main cursor restored on following scan',cursor(0,'RowIdx'),1)
            check('main elapsed',cursor(0,'Elapsed'),50)
            check('main timeout',cursor(0,'TimedOut'),True)
            check('main-only elapsed',read('StationA.CurrentStepElapsed'),50)
            check('main-only guard',read('StationA.CurrentStepTimedOut'),True)
            check('current step title',read('StationA.CurrentStep.StepName'),'test.main')
            check('root B isolation',read('StationB.SequenceStepCount'),0)
            check('nested Unit isolation',read('StationA.Satellite.SequenceStepCount'),0)
            controls(AwaitEnabled=True,AwaitLabel='test.restoreCondition',AwaitOk=False)
            check('main condition label',read('StationA.CurrentStep.Conds[1].Label'),'test.restoreCondition')
            check('main condition false',read('StationA.CurrentStep.Conds[1].Ok'),False)
            controls(AwaitOk=True)
            check('main condition true',read('StationA.CurrentStep.Conds[1].Ok'),True)
            controls(ExpectedTime=100)
            check('recipe guard update changes cursor',cursor(0,'TimedOut'),False)
            revision=read('StationA.ConfigRev')
            controls(ExpectedTime=40)
            wait(lambda:read('StationA.ConfigRev')!=revision,'chart manifest revision settled')
            stable=read('StationA.ConfigRev');time.sleep(1.2)
            check('no per-scan manifest churn',read('StationA.ConfigRev'),stable)
            entries=query();defs=[r for r in entries if r['Scope']=='StationA' and r['Item'].startswith('SequenceSteps/')]
            check('static facets seven per discovered row',len(defs),14)
            check('static facets read only',all(not r['Writable'] and r['WriteKey']=='' for r in defs),True)
            lookup={r['Item']:r['ValueText'] for r in defs}
            check('manifest title',lookup['SequenceSteps/SequenceSteps[1]/StepName'],'test.main')
            check('manifest fast step',int(lookup['SequenceSteps/SequenceSteps[2]/StepNo']),11)
            check('manifest milliseconds guard',int(lookup['SequenceSteps/SequenceSteps[1]/ExpectedTime']),40)
            controls(AwaitEnabled=False,Annotate=True,IsError=False,Key='test.warning',SourcePath='StationA.Cell.Clamp')
            check('warning row flag',row(1,'WarningActive'),True)
            check('warning sparse kind',read('StationA.SequenceAnnotations[1].IsError'),False)
            check('warning sparse key',read('StationA.SequenceAnnotations[1].Key'),'test.warning')
            controls(IsError=True,Key='test.error')
            check('error row flag',row(1,'ErrorActive'),True)
            check('separate sparse kinds',read('StationA.SequenceAnnotationCount'),2)
            controls(Annotate=False,Visit=2)
            check('revisit clears warning',row(1,'WarningActive'),False)
            check('revisit preserves error until reset',row(1,'ErrorActive'),True)
            check('freed warning slot',read('StationA.SequenceAnnotations[1].RowIdx'),0)
            controls(StepNo=30,StepName='test.leg',Branch=1,Depth=1,Visit=1,Elapsed=75,ExpectedTime=60,Parent=True)
            wait(lambda:read('StationA.SequenceStepCount')==4,'child and parent rows recorded')
            check('sub-chain cursor wins over later parent',cursor(1,'RowIdx'),3)
            check('parallel leg elapsed',cursor(1,'Elapsed'),75)
            check('parallel leg guard',cursor(1,'TimedOut'),True)
            check('untouched main cursor cleared',cursor(0,'RowIdx'),0)
            check('parallel is not main clock',read('StationA.CurrentStepElapsed'),0)
            controls(Annotate=True,IsError=False,Key='test.leg.warning')
            check('freed note reused',read('StationA.SequenceAnnotationCount'),2)
            check('leg warning survives full note table',row(3,'WarningActive'),True)
            controls(IsError=True,Key='test.leg.error')
            check('full note table preserves row error',row(3,'ErrorActive'),True)
            check('full note table remains bounded',read('StationA.SequenceAnnotationCount'),2)
            controls(Annotate=False,Parent=False,StepNo=40,StepName='test.overflow',Branch=2,Depth=0)
            check('row capacity bounded',read('StationA.SequenceStepCount'),4)
            check('overflow detected',read(c+'Overflow'),True)
            check('overflow creates no false cursor',cursor(2,'RowIdx'),0)
            controls(Enabled=False)
            check('idle cursor cleared',cursor(1,'RowIdx'),0)
            check('idle history remains PLC-owned',row(2,'Visited'),True)
            # The shared reset gate requires a real blocking occurrence. Chart
            # marks alone are presentation data and must not weaken that gate.
            write({'GDB_StateAlarmTest.Diag.ReasonCode':10021,
                   'GDB_StateAlarmTest.Diag.Description':'test.chart.resetOccurrence',
                   'GDB_StateAlarmTest.Diag.SourcePath':'StationA',
                   'GDB_StateAlarmTest.Diag.Severity':1,
                   'GDB_StateAlarmTest.ResetClass':Catalog.read().enums['E_ResetClass']['MANUAL_RESET'],
                   'GDB_StateAlarmTest.RaisePulse':True})
            wait(lambda:not read('GDB_StateAlarmTest.RaisePulse') and read('StationA.AlarmLog.Blocking'),'blocking reset occurrence')
            check('operator reset acknowledged',mail.request('OPERATOR_RESET'),True)
            check('operator reset error cleared',row(1,'ErrorActive'),False)
            check('operator reset leg error cleared',row(3,'ErrorActive'),False)
            check('operator reset warning remains',row(3,'WarningActive'),True)
            mode('AUTO')
            check('committed mode clears rows',read('StationA.SequenceStepCount'),0)
            check('committed mode clears annotations',read('StationA.SequenceAnnotationCount'),0)
            check('committed mode clears overflow',read(c+'Overflow'),False)
            check('new mode empty manifest',any(r['Item'].startswith('SequenceSteps/') for r in query()),False)
            controls(StepNo=10,StepName='test.newMode',Branch=0,Depth=0,Visit=3,Elapsed=0,ExpectedTime=0,Enabled=True)
            check('same number allowed in new mode',read('StationA.SequenceStepCount'),1)
            check('new mode new title',read('StationA.CurrentStep.StepName'),'test.newMode')
            controls(Enabled=False);mode('MANUAL')
            controls(UseHelper=True,HelperReset=True,HelperOffset=360,StepNo=240,StepName='test.helper.step',Branch=0,Depth=1,ExpectedTime=0,AwaitLabel='test.helper.restore',AwaitOk=False,Enabled=True)
            wait(lambda:read('StationA.SequenceStepCount')==1,'real shared sequence helper recorded')
            check('real helper local step',read('GDB_SequenceHelperTest.Seq.Step'),240)
            check('real helper projected step',read('StationA.CurrentStep.StepNo'),600)
            check('real helper pending flag',read('GDB_SequenceHelperTest.Seq.Pending'),True)
            check('real helper condition',read('StationA.CurrentStep.Conds[1].Label'),'test.helper.restore')
            write({'GDB_SequenceHelperTest.Diag.ReasonCode':10020,'GDB_SequenceHelperTest.Diag.Description':'test.helper.message','GDB_SequenceHelperTest.Diag.SourcePath':'StationA.Cell.Clamp'})
            controls(Annotate=True)
            check('real helper warning row',row(1,'WarningActive'),True)
            check('real helper message text',read('StationA.SequenceAnnotations[1].Key'),'test.helper.message')
            check('real helper message once per visit',read('StationA.SequenceAnnotationCount'),1)
            controls(Annotate=False,StepNo=260,StepName='test.helper.next',AwaitOk=True)
            wait(lambda:read('StationA.SequenceStepCount')==2,'real helper next step')
            check('real helper next projection',read('StationA.CurrentStep.StepNo'),620)
            check('real helper next wait true',read('StationA.CurrentStep.Conds[1].Ok'),True)
            check('real helper prior history',row(1,'Visited'),True)
            controls(Enabled=False)
            check('real helper run-drop clears cursor',cursor(0,'RowIdx'),0)
            controls(UseHelper=False)
            # Restart clears the non-retained chart while retained configuration remains.
            api.conn.close()
            for action in ('halt','run'):
                emit({'event':'restart-guard','action':action,'status':guard()})
                result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit({'event':'restart-result','action':action,'exit':result.returncode,'output':result.stdout.decode('utf-8-sig')});assert result.returncode==0
            api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False);api.login('fraktal')
            if expect_medium:wait(lambda:not read('FRK_PersistStatus.Restoring'),'selected medium after restart',seconds=65)
            wait(lambda:read('StationA.SequenceViewEnabled'),'chart startup')
            check('restart clears discovery',read('StationA.SequenceStepCount'),0)
            check('restart clears annotations',read('StationA.SequenceAnnotationCount'),0)
            check('restart clears cursor',cursor(0,'RowIdx'),0)
            check('root A idle',read('StationA.RunningPublished'),False)
            check('root B idle',read('StationB.RunningPublished'),False)
            mail=Mailbox(api,guard,emit)
            check('final logout',mail.request('LOGOUT'),True)
            complete=True
        finally:
            emit({'event':'summary','checks':len(checks),'passed':sum(checks),'complete':complete})
            api.conn.close()
    assert complete and all(checks)
    return len(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    print(json.dumps({'checks':probe(p.parse_args().out)}))
