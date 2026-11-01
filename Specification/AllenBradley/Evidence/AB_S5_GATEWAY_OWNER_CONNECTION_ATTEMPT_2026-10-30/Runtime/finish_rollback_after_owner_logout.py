"""Finish only the interrupted session09 rollback; retain the failed session result."""
import sys
from pathlib import Path
import datetime, hashlib, json, os, subprocess, time

D = Path(__file__).parent
W = D.parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PRIOR = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
SDK = D/'session/bin/Debug/net8.0/win-x86/S5Session.exe'
PY = sys.executable
from s5_session import authorize, dumps

def save(name, value):
    with (D/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)

def run(label, *args):
    print(json.dumps(dict(stage=label,status='started')),flush=True)
    subprocess.run([PY,str(D/'run_logged.py'),label,*map(str,args)],cwd=ROOT,check=True)

def main():
    authorize(json.loads((D/'authorization.json').read_bytes()))
    assert not dumps(), 'controller dump present'
    assert not (D/'genealogy_restored.L5X').exists()
    assert json.loads((W/'idle_cip_pool_probe_01_exit.json').read_bytes())['exitCode']==0
    bindings=json.loads((D/'source_bindings.json').read_bytes())['sha256']
    checked=[]
    for name,pin in bindings.items():
        path=Path(name)
        # This continuation executes PLC guards/fixtures and the sealed SDK only.
        # Changed HMI inputs are not run and do not qualify the failed candidate.
        if '/FraktalCore/HMI/' in path.as_posix(): continue
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==pin.upper(),name
        checked.append(name)
    save('rollback_continuation_started.json',dict(
        ownerWords='MANUAL and logged out now',
        purpose='Complete interrupted mandatory rollback only',
        originalFailedSessionPreserved=True, restorationInputsVerified=checked,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
    run('guard_rollback_02',PY,D/'scripts/guard_echo.py')
    run('manual_rollback_02',PY,D/'ensure_manual_candidate.py','--output',D/'manual_rollback_02.json')
    run('restore_genealogy',SDK,'restore-genealogy')
    args=[PY,T/'fraktal_ab_sdk_log_gate.py',D/'restore_genealogy.log']
    for operation in ('Open project','Download','Save','Save As'):args.extend(['--require',operation])
    run('restore_genealogy_audit',*args)
    run('restore_access',PY,PRIOR/'audit_baseline_access.py',D/'genealogy_restored.L5X','--output',D/'restore_access.json')
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
    run('guard_baseline',PY,D/'scripts/guard_echo.py')
    run('restore_original_medium',PY,D/'restore_original_medium.py')
    run('baseline_regressions',PY,T/'fraktal_ab_genealogy_execute.py','--execute-fixture',
        '--expect-serial','601FC87B','--credential-file','C:/work/fraktal_echo38_access_fixture.json',
        '--output',D/'baseline_regressions.json')
    run('manual_final',PY,D/'ensure_manual_baseline.py','--output',D/'manual_final.json')
    run('final_checks',PY,PRIOR/'final_checks.py',D/'final_checks.json')
    run('preflight_final',PY,D/'scripts/preflight.py','--verify-only')
    gate=W/'idle_connection_full_hmi_01_exit.json'
    while not gate.exists():
        print('Waiting for HMI tests to end before baseline timing',flush=True)
        time.sleep(5)
    run('baseline_timing',PY,PRIOR/'measure_timing.py',D/'baseline_timing.json')
    assert not dumps()
    save('rollback_continuation_result.json',dict(passed=True,genealogyRestored=True,
        candidateAccepted=False, originalFailedSessionPreserved=True,
        ownerConnectionIssuesRemainUnderInvestigation=True,
        faultClears=0,clockChanges=0,powerOperations=0,echoHardKills=0,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if not (D/'rollback_continuation_result.json').exists():
            save('rollback_continuation_result.json',dict(passed=False,error=f'{type(error).__name__}: {error}'))
        raise
