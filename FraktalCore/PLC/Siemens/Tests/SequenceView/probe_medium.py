"""Native shared-view withdrawal during a selected LOAD_DB restore barrier."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'tools'))
from tia_webapi import WebApi,leaf_var
from tia_mailbox import Mailbox
from tia_target_guard import guard


def probe(out):
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    checks=[];complete=False;c='GDB_SequenceViewTest.'
    with out.open('x',encoding='ascii',newline='\n') as f:
        def emit(r):f.write(json.dumps(r,ensure_ascii=True)+'\n');f.flush()
        def read(path):return api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
        def wait(pred,label,seconds=65):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if pred():return
                time.sleep(.04)
            raise AssertionError(label)
        def check(label,actual,expected):
            ok=type(actual) is type(expected) and actual==expected
            checks.append(ok);emit(dict(event='check',label=label,actual=actual,expected=expected,passed=ok))
            if not ok:raise AssertionError(label)
        def write(values):
            emit({'event':'mutation-guard','status':guard(),'targets':list(values)})
            replies=api.bulk([('PlcProgram.Write',{'var':leaf_var(p.split('.')),'value':v}) for p,v in values.items()])
            assert not any(e for v,e in replies),[(p,e) for p,(v,e) in zip(values,replies) if e]
        def ready():
            return not read('FRK_PersistStatus.Restoring') and all(not read(r+'.ConfigPersist.Pending') and not read(r+'.ConfigPersist.Failed') for r in ('StationA','StationB'))
        try:
            api.login('fraktal');emit({'event':'connection','pin':api.fingerprint,'owner':guard()})
            out.with_suffix('.certificate.der').write_bytes(api.conn.sock.getpeercert(binary_form=True))
            wait(ready,'selected storage ready and durable')
            check('selected medium',read('FRK_PersistStatus.Medium'),'LOAD_DB')
            check('selected documents',read('FRK_PersistStatus.DocumentCount'),17)
            write({c+'Owner':1,c+'UseHelper':False,c+'StepNo':42,c+'StepName':'test.integration.main',
                   c+'Branch':0,c+'Depth':0,c+'Visit':1,c+'ExpectedTime':50,c+'Elapsed':75,
                   c+'Parent':False,c+'Annotate':False,c+'AwaitEnabled':False,c+'Enabled':True})
            wait(lambda:read('StationA.ActiveSteps[0].RowIdx')>0,'main cursor active')
            check('view title before restart',read('StationA.CurrentStep.StepName'),'test.integration.main')
            check('view guard before restart',read('StationA.CurrentStepTimedOut'),True)
            check('history before restart',read('StationA.SequenceSteps[1].Visited'),True)
            write({'GDB_SequenceQuiesceTest.Enabled':True})
            wait(lambda:read('GDB_SequenceQuiesceTest.BeforeActive') and not read('GDB_SequenceQuiesceTest.AfterActive'),'running-state quiescence')
            check('quiesce saw a live cursor',read('GDB_SequenceQuiesceTest.BeforeActive'),True)
            check('quiesce withdrew the live cursor',read('GDB_SequenceQuiesceTest.AfterActive'),False)
            check('quiesce preserves visited history',read('GDB_SequenceQuiesceTest.HistorySurvived'),True)
            check('quiesce publishes no current step',read('GDB_SequenceQuiesceTest.CurrentCleared'),True)
            write({'GDB_SequenceQuiesceTest.Enabled':False})
            wait(lambda:read('StationA.ActiveSteps[0].RowIdx')>0,'normal frame re-publishes cursor')
            mail=Mailbox(api,guard,emit)
            check('login consumed',mail.request('LOGIN',User='admin',Secret=os.environ['FRAKTAL_TIA_ADMIN_PIN']),True)
            wait(lambda:read('StationA.Access.CurrentLevel')==4 and not read('StationA.Access.LoginBusy'),'admin authenticated')
            write({'GDB_PersistenceTest.Unavailable':True})
            api.conn.close()
            for action in ('halt','run'):
                emit({'event':'restart-guard','action':action,'owner':guard()})
                r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'),'-Action',action],capture_output=True)
                emit({'event':'restart-result','action':action,'exit':r.returncode,'output':r.stdout.decode('utf-8-sig')});assert r.returncode==0
            api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False);api.login('fraktal')
            wait(lambda:read('FRK_PersistStatus.Restoring'),'restore barrier entered')
            for root in ('StationA','StationB'):
                check(root+' boot withdraws run',read(root+'.RunningPublished'),False)
                check(root+' boot drops session',read(root+'.Access.CurrentLevel'),0)
                for branch in range(3):
                    check(root+' boot cursor %d'%branch,read(root+'.ActiveSteps[%d].RowIdx'%branch),0)
                check(root+' boot current step cleared',read(root+'.CurrentStep.StepName'),'')
                check(root+' boot elapsed cleared',read(root+'.CurrentStepElapsed'),0)
                check(root+' boot timeout cleared',read(root+'.CurrentStepTimedOut'),False)
            check('cold boot history is volatile',read('StationA.SequenceSteps[1].Visited'),False)
            check('cold boot publishes empty row inventory',read('StationA.SequenceStepCount'),0)
            write({c+'Enabled':False,'GDB_PersistenceTest.Unavailable':False})
            wait(ready,'restore barrier exits and documents durable')
            for root in ('StationA','StationB'):
                check(root+' fresh startup clears chart',read(root+'.SequenceStepCount'),0)
                check(root+' no revived cursor',read(root+'.ActiveSteps[0].RowIdx'),0)
                check(root+' no revived session',read(root+'.Access.CurrentLevel'),0)
                check(root+' no revived command',read(root+'.RunningPublished'),False)
            check('selected storage after retry',read('FRK_PersistStatus.Medium'),'LOAD_DB')
            complete=True
        finally:
            emit({'event':'summary','checks':len(checks),'passed':sum(checks),'complete':complete})
            api.conn.close()
    assert complete and all(checks)
    return len(checks)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    print(json.dumps({'checks':probe(p.parse_args().out)}))
