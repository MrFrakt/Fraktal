"""Native shared first-out walk, named stalls, HELD and handled failure."""
import argparse,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from tia_target_guard import guard
from tia_mailbox import Mailbox
from fraktal_tia_binding import Catalog

def probe(out):
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    checks=[];complete=False;c='GDB_SequenceDiagnosticTest.';root='StationA';target=root+'.Cell.Clamp'
    enum=Catalog.read().enums
    with out.open('x',encoding='ascii') as stream:
        def emit(row):stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
        def read(path):return api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
        def write(values):
            emit({'event':'mutation-guard','status':guard(),'targets':list(values)})
            replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
            if any(e for _,e in replies):emit({'event':'write-errors','errors':[{'path':p,'error':e} for p,(_,e) in zip(values,replies) if e]})
            assert not any(e for _,e in replies),'native control write refused'
        def controls(**values):write({c+n:v for n,v in values.items()})
        def wait(pred,label,seconds=65):
            end=time.monotonic()+seconds
            while not pred():
                assert time.monotonic()<end,label;time.sleep(.03)
        def check(label,value,expected):
            ok=type(value) is type(expected) and value==expected
            emit({'event':'check','label':label,'actual':value,'expected':expected,'passed':ok});checks.append(ok)
            assert ok,label
        def login():
            if read(root+'.Access.CurrentLevel')!=4:
                assert mail.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN'])
                wait(lambda:read(root+'.Access.CurrentLevel')==4 and not read(root+'.Access.LoginBusy'),'admin authenticated')
        def mode(value):
            ordinal=enum['E_Mode'][value]
            assert mail.request('SET_MODE',IntValue=ordinal)
            wait(lambda:read(root+'.ModeActivePublished')==ordinal,'mode committed')
        def idle():
            controls(Enabled=False,Finish=False)
            login()
            if read(root+'.AlarmLog.Blocking'):
                assert mail.request('OPERATOR_RESET')
                wait(lambda:not read(root+'.AlarmLog.Blocking'),'operator reset closes occurrence')
            if read(root+'.Status.State')!=enum['E_ExecState']['READY']:
                assert mail.request('STOP')
                write({'GDB_UnitTest.FinishCycle':True})
                wait(lambda:read(root+'.Status.State')==enum['E_ExecState']['READY'],'graceful stop closes command')
                write({'GDB_UnitTest.FinishCycle':False})
            mode('MANUAL');mode('AUTO')
            wait(lambda:read(target+'.Status.State')==enum['E_ExecState']['READY'],'child ready')
        def start(**values):
            idle()
            settings=dict(Owner=1,Enabled=True,ResetPulse=True,Scenario=0,StepNo=42,Branch=0,
                     Guard=100,Elapsed=0,ConditionOne=False,ConditionTwo=False,CommandValue=2,
                     InvalidTarget=0,Permit=True,Finish=False)
            settings.update(values);controls(**settings)
            check('start accepted',mail.request('START'),True)
            wait(lambda:read(root+'.RunningPublished') or read(root+'.Error'),'Unit running or immediate fault')
        def diag(path):
            fields=('ReasonCode','SourcePath','Description','IoTag','IoAddress','Severity','Category','Since','TimeSynchronized')
            return {n:read(path+'.'+n) for n in fields}
        try:
            api.login('fraktal');mail=Mailbox(api,guard,emit)
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            emit({'event':'connection','status':guard(),'pin':api.fingerprint})
            wait(lambda:not read('FRK_PersistStatus.Restoring') and not read(root+'.ConfigPersist.Pending'),'selected storage ready')
            write({'GDB_SequenceViewTest.Enabled':False,'GDB_SequenceQuiesceTest.Enabled':False})
            for path in ('FRK_Diagnostics.Samples[1].Diagnostic.ReasonCode','FRK_Views.V001.Book.AwaitIndex'):
                reply=api.bulk([('PlcProgram.Read',{'var':leaf_var(path.split('.'))})])[0]
                check('private work '+path,reply[1]['code'],200)
            emit({'event':'mutation-guard','status':guard(),'targets':[root+'.Pending.ReasonCode']})
            reply=api.bulk([('PlcProgram.Write',{'var':leaf_var((root+'.Pending.ReasonCode').split('.')),'value':9})])[0]
            check('pending mirror readonly',reply[1]['code'],205)

            start()
            check('before guard pending empty',read(root+'.Pending.ReasonCode'),0)
            controls(Elapsed=150)
            wait(lambda:read(root+'.Pending.ReasonCode')==enum['E_Reason']['STEP_STALLED'],'named stall published')
            check('first false condition',read(root+'.CurrentStep.AwaitingLabel'),'test.condition.first')
            check('stall severity',read(root+'.Pending.Severity'),enum['E_Severity']['LOW'])
            check('stall is not error',read(root+'.Error'),False)
            check('stall creates no alarm',read(root+'.AlarmLog.Blocking'),False)
            check('stall tile mirror',read(root+'.Status.Diagnostic.ReasonCode'),enum['E_Reason']['STEP_STALLED'])
            stamp=read(root+'.Pending.Since');time.sleep(.1)
            check('same visit since stable',read(root+'.Pending.Since'),stamp)
            controls(ConditionOne=True)
            wait(lambda:read(root+'.CurrentStep.AwaitingLabel')=='test.condition.second','next false condition named')
            check('second condition false',read(root+'.CurrentStep.Conds[2].Ok'),False)
            controls(ConditionTwo=True,StepNo=43,Elapsed=0)
            wait(lambda:read(root+'.Pending.ReasonCode')==0,'step change clears pending')
            check('step change clears tile',read(root+'.Status.Diagnostic.ReasonCode'),0)

            start(Scenario=4,Guard=0)
            wait(lambda:read(target+'.Busy') and read(root+'.Cell.Gate.Busy'),'two real commands busy')
            check('longest default guard',read(root+'.CurrentStep.ExpectedTime'),45000)
            check('qualified awaited command',read(root+'.CurrentStep.AwaitingLabel'),target+'.FIRST')
            revision=read(root+'.ConfigRev');time.sleep(1.3)
            settled=read(root+'.ConfigRev');time.sleep(1.3)
            check('derived guard does not churn manifest',read(root+'.ConfigRev'),settled)
            emit({'event':'revision-before-settle','value':revision})

            description='test.original.'+'x'*200
            injection=dict(ReasonCode=10022,SourcePath=target,Description=description,IoTag='DEV_X9',
                           IoAddress='%I9.0',Severity=enum['E_Severity']['MED'],Category=enum['E_Category']['PROCESS'],
                           Since='1791961200123456789',TimeSynchronized=True)
            write({c+'Diagnostic.'+n:v for n,v in injection.items()})
            start(Scenario=1,CommandValue=5,Guard=100,Elapsed=150)
            wait(lambda:read(root+'.Pending.ReasonCode')==10022,'child first-out named at guard')
            for n in ('ReasonCode','SourcePath','Description','IoTag','IoAddress','Category'):
                check('pending preserves '+n,read(root+'.Pending.'+n),injection[n])
            check('pending forced Low',read(root+'.Pending.Severity'),enum['E_Severity']['LOW'])
            check('root B pending isolated',read('StationB.Pending.ReasonCode'),0)
            check('child pending is not fault',read(root+'.Error'),False)

            start(Scenario=1,CommandValue=3,Guard=100,Elapsed=0)
            wait(lambda:read(target+'.Busy'),'hold command started')
            controls(Permit=False,Elapsed=50000)
            wait(lambda:read(target+'.Held') and read(root+'.Held'),'held child and parent')
            check('held is busy',read(root+'.Busy'),True)
            check('held is not error',read(root+'.Error'),False)
            check('held disarms generic stall',read(root+'.Pending.ReasonCode'),0)
            check('held clears timeout flag',read(root+'.CurrentStepTimedOut'),False)
            check('held source retained',read(root+'.Status.Diagnostic.SourcePath'),target)
            check('held has no reset alarm',read(root+'.AlarmLog.Blocking'),False)
            controls(Permit=True,Finish=True,Elapsed=0)
            wait(lambda:not read(root+'.Held') and read(c+'Completed'),'held restores without reset')
            check('held recovery clears tile',read(root+'.Status.Diagnostic.ReasonCode'),0)

            start(Scenario=2,CommandValue=7,Guard=500000)
            wait(lambda:read(root+'.Error'),'cross-tier fault before guard')
            first=diag(target+'.Status.Diagnostic')
            for n,v in first.items():check('EM preserves '+n,read(root+'.Cell.Status.Diagnostic.'+n),v)
            for n,v in first.items():check('Unit preserves '+n,read(root+'.Status.Diagnostic.'+n),v)
            check('fault did not wait for guard',read(root+'.CurrentStepTimedOut'),False)
            check('fault marks active row',read(root+'.SequenceSteps[1].ErrorActive'),True)
            check('fault annotation source',read(root+'.SequenceAnnotations[1].SourcePath'),target)
            check('root B fault isolated',read('StationB.Error'),False)

            start(Scenario=3,CommandValue=7,Guard=500000)
            wait(lambda:read(root+'.SequenceSteps[1].WarningActive'),'handled failure reported')
            check('handled failure keeps Unit busy',read(root+'.Busy'),True)
            check('handled failure does not error',read(root+'.Error'),False)
            check('handled failure does not block restart',read(root+'.AlarmLog.Blocking'),False)
            check('handled failure links child',read(root+'.SequenceAnnotations[1].SourcePath'),target)

            start(Scenario=1,CommandValue=7,Guard=500000,Branch=1,StepNo=50)
            wait(lambda:read(root+'.Error'),'parallel-leg fault adopted')
            check('parallel error marks its row',read(root+'.SequenceSteps[1].ErrorActive'),True)
            check('parallel leg has no main-line pending',read(root+'.Pending.ReasonCode'),0)

            start(Scenario=1,InvalidTarget=15,Guard=500000)
            wait(lambda:read(root+'.Error'),'foreign-root target fails closed')
            check('foreign target rejected reason',read(root+'.Status.Diagnostic.ReasonCode'),enum['E_Reason']['DEVICE_NOT_READY'])
            check('foreign target does not execute child',read('StationB.Cell.Clamp.Execute'),False)
            idle();mode('MANUAL')
            check('final logout',mail.request('LOGOUT'),True)
            check('final pending empty',read(root+'.Pending.ReasonCode'),0)
            complete=True
        finally:
            emit({'event':'summary','checks':len(checks),'passed':sum(checks),'complete':complete});api.conn.close()
    assert complete and all(checks)
    return len(checks)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    print(json.dumps({'checks':probe(p.parse_args().out)}))
