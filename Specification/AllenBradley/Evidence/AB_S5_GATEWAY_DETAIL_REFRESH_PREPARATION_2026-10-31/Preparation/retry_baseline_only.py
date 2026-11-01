"""One unchanged 31-case retry, new outputs; original failure is preserved."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
from s5_session import authorize
D=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PRIOR=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
PY=sys.executable
authorize(json.loads((D/'authorization.json').read_bytes()))
assert json.loads((D/'manual_after_failed_baseline_01.json').read_bytes())['passed']
assert hashlib.sha256(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).hexdigest().upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
def save(name,value):
    with (D/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def run(label,*args):
    print(json.dumps(dict(stage=label,status='started')),flush=True)
    subprocess.run([PY,str(D/'run_logged.py'),label,*map(str,args)],cwd=ROOT,check=True)
save('baseline_retry_authorization.json',dict(standingDecision='O3',serial='601FC87B',
    scope='One unchanged baseline fixture retry and MANUAL/final/preflight/timing cleanup; read-only state witness; no download or new write vector',
    sourceFailure='baseline_regressions.json: HOME timed out at step0/error0 after ST and two SFC cases; restored=true',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
watch=None;log=None
try:
    run('guard_baseline_retry_01',PY,D/'scripts/guard_echo.py')
    log=(D/'baseline_retry_watch.log').open('x',encoding='utf-8')
    watch=subprocess.Popen([PY,str(D/'baseline_retry_watch.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+15
    while not (D/'baseline_retry_watch_ready.json').exists():
        if watch.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Read-only retry witness did not become ready')
        time.sleep(.1)
    try:
        run('baseline_regressions_02',PY,T/'fraktal_ab_genealogy_execute.py','--execute-fixture',
            '--expect-serial','601FC87B','--credential-file','C:/work/fraktal_echo38_access_fixture.json',
            '--output',D/'baseline_regressions_02.json')
    finally:
        save('baseline_retry_watch_stop.json',dict(stop=True))
        assert watch.wait(timeout=15)==0
        log.close();log=None
    value=json.loads((D/'baseline_regressions_02.json').read_bytes())
    assert value['restored'] and 'error' not in value and len(value['rows'])==31
    run('manual_final_02',PY,D/'ensure_manual_baseline.py','--output',D/'manual_final_02.json')
    run('final_checks_02',PY,PRIOR/'final_checks.py',D/'final_checks_02.json')
    run('preflight_final_02',PY,D/'scripts/preflight.py','--verify-only')
    run('baseline_timing_02',PY,PRIOR/'measure_timing.py',D/'baseline_timing_02.json')
    save('baseline_recovery_result.json',dict(passed=True,baselineCases=31,genealogyRestored=True,
        originalFailedBaselinePreserved=True,originalFailedSessionPreserved=True,
        S5Acceptance=False,browserAcknowledgementProgressUnproven=True,
        faultClears=0,clockChanges=0,powerOperations=0,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
except BaseException as error:
    save('baseline_recovery_result.json',dict(passed=False,error=f'{type(error).__name__}: {error}'))
    raise
finally:
    if watch is not None and watch.poll() is None:
        if not (D/'baseline_retry_watch_stop.json').exists():save('baseline_retry_watch_stop.json',dict(stop=True))
        watch.wait(timeout=15)
    if log is not None:log.close()
