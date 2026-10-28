"""Current owner approval: prepared request cases, then guarded genealogy rollback."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
W=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
PY=sys.executable;SDK=D/'restore_session/bin/Debug/net8.0/win-x86/S3kRestore.exe'
DUMPS=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
auth=json.loads((D/'restore_authorization.json').read_bytes())
assert auth['CurrentOwnerApproved'] and auth['RestoreGenealogyAuthorized'] and auth['BaselineRegressionWritesAuthorized']
assert auth['Serial']=='601FC87B' and not auth['FaultClearAuthorized'] and not auth['ClockSetAuthorized']
assert json.loads((D/'restore_helper_build_01_exit.json').read_bytes())['exitCode']==0
assert json.loads((D/'current_request_image_01.json').read_bytes())['passed']
steps=[];candidate_error=None;restore_error=None
def run(label,*args):
    print(json.dumps(dict(stage=label,status='started')),flush=True);steps.append(label)
    subprocess.run([PY,str(D/'run_logged.py'),label,*map(str,args)],cwd=R,check=True)
def audit(label,log):
    args=[PY,T/'fraktal_ab_sdk_log_gate.py',D/(log+'.log')]
    for operation in ('Open project','Download','Save','Save As'):args+=['--require',operation]
    run(label,*args)
try:
    run('request_session_01',PY,D/'request_session.py')
except Exception as error:
    candidate_error=f'{type(error).__name__}: {error}'
    print(json.dumps(dict(candidateError=candidate_error)),flush=True)
finally:
    try:
        run('guard_before_restore_01',PY,W/'scripts/guard_echo.py')
        if list(DUMPS.rglob('*.dmp')):raise RuntimeError('controller dump present; no power operation or fault clear authorized')
        run('manual_before_restore_01',PY,D/'ensure_manual_candidate.py','--output',D/'manual_before_restore_01.json')
        run('restore_genealogy_01',SDK,'restore-genealogy')
        audit('restore_log_audit_01','restore_genealogy_01')
        run('restore_access_01',PY,W/'audit_baseline_access.py',D/'genealogy_restored.L5X','--output',D/'restore_access_01.json')
        run('guard_baseline_01',PY,W/'scripts/guard_echo.py')
        run('baseline_regressions_01',PY,T/'fraktal_ab_genealogy_execute.py','--execute-fixture','--expect-serial','601FC87B',
            '--credential-file','C:/work/fraktal_echo38_access_fixture.json','--output',D/'baseline_regressions_01.json')
        run('manual_final_01',PY,D/'ensure_manual_baseline.py','--output',D/'manual_final_01.json')
        run('final_checks_01',PY,W/'final_checks.py',D/'final_checks_01.json')
        run('preflight_final_01',PY,W/'scripts/preflight.py','--verify-only')
        run('baseline_timing_01',PY,W/'measure_timing.py',D/'baseline_timing_01.json')
    except Exception as error:
        restore_error=f'{type(error).__name__}: {error}'
        print(json.dumps(dict(restoreError=restore_error)),flush=True)
    dumps=[dict(path=p.relative_to(DUMPS).as_posix(),bytes=p.stat().st_size) for p in sorted(DUMPS.rglob('*.dmp'))]
    record=dict(passed=candidate_error is None and restore_error is None and not dumps,
        candidateError=candidate_error,restoreError=restore_error,stagesStarted=steps,dumpFiles=dumps,
        authorizationConsumed=True,authorizationInstruction=auth['OwnerInstruction'],
        faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (D/'request_restore_session_01.json').open('x') as out:json.dump(record,out,indent=2)
raise SystemExit(0 if record['passed'] else 1)
