"""Complete the owner's current rollback instruction after the failed request walk."""
from pathlib import Path
import datetime,json,os,subprocess,sys
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
W=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
PY=sys.executable;SDK=D/'restore_session/bin/Debug/net8.0/win-x86/S3kRestore.exe'
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
a=json.loads((D/'restore_authorization.json').read_bytes())
assert a['CurrentOwnerApproved'] and a['RestoreGenealogyAuthorized'] and a['BaselineRegressionWritesAuthorized']
assert a['Serial']=='601FC87B' and not a['FaultClearAuthorized'] and not a['ClockSetAuthorized']
assert json.loads((D/'manual_rollback_03.json').read_bytes())['passed']
assert json.loads((D/'restore_helper_build_03_exit.json').read_bytes())['exitCode']==0
steps=[];error=None
def run(label,*args):
    print(json.dumps(dict(stage=label,status='started')),flush=True);steps.append(label)
    subprocess.run([PY,str(D/'run_logged.py'),label,*map(str,args)],cwd=R,check=True)
try:
    run('guard_rollback_03',PY,W/'scripts/guard_echo.py')
    run('restore_genealogy_01',SDK,'restore-genealogy')
    run('restore_log_audit_01',PY,T/'fraktal_ab_sdk_log_gate.py',D/'restore_genealogy_01.log',
        '--require','Open project','--require','Download','--require','Save','--require','Save As')
    run('restore_access_01',PY,W/'audit_baseline_access.py',D/'genealogy_restored.L5X','--output',D/'restore_access_01.json')
    run('guard_baseline_01',PY,W/'scripts/guard_echo.py')
    run('baseline_regressions_01',PY,T/'fraktal_ab_genealogy_execute.py','--execute-fixture','--expect-serial','601FC87B',
        '--credential-file','C:/work/fraktal_echo38_access_fixture.json','--output',D/'baseline_regressions_01.json')
    run('manual_final_01',PY,D/'ensure_manual_baseline.py','--output',D/'manual_final_01.json')
    run('final_checks_01',PY,W/'final_checks.py',D/'final_checks_01.json')
    run('preflight_final_01',PY,W/'scripts/preflight.py','--verify-only')
    run('baseline_timing_01',PY,W/'measure_timing.py',D/'baseline_timing_01.json')
except Exception as caught:
    error=f'{type(caught).__name__}: {caught}';print(json.dumps(dict(error=error)),flush=True)
finally:
    dump_root=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
    dumps=[dict(path=p.relative_to(dump_root).as_posix(),bytes=p.stat().st_size) for p in sorted(dump_root.rglob('*.dmp'))]
    record=dict(passed=error is None and not dumps,error=error,steps=steps,dumpFiles=dumps,
        candidateAccepted=False,authorizationConsumed=True,ownerInstruction=a['OwnerInstruction'],
        faultClears=0,clockChanges=0,powerOperations=0,hardKills=0,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with (D/'restore_verify_session_03.json').open('x') as out:json.dump(record,out,indent=2)
raise SystemExit(0 if record['passed'] else 1)
