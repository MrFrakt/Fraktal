"""Verify the empty-controller recovery, then re-enter the unchanged S3h gates."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,subprocess,sys
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OLD=Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P=OLD.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
PY=sys.executable
assert json.loads((R/'recovery_download_02_exit.json').read_text())['exitCode']==0
assert (R/'recovery_attempt.json').exists()
reference=ROOT/'Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Reference/genealogy_current.L5X.gz'
raw=gzip.decompress(reference.read_bytes())
assert hashlib.sha256(raw).hexdigest()=='91bf67c9101eae863cf29c1a9df6413d7256ab056d985394587f0183aa525714'
with (R/'genealogy_reference.L5X').open('xb') as f:f.write(raw)
stages=[];error=None
def run(label,*args):
    print(json.dumps(dict(stage=label,status='started')),flush=True)
    stages.append(label)
    subprocess.run([PY,str(R/'run_logged.py'),label,*map(str,args)],cwd=ROOT,check=True)
    print(json.dumps(dict(stage=label,status='finished')),flush=True)
try:
    run('recovery_log_audit_01',PY,T/'fraktal_ab_sdk_log_gate.py',R/'recovery_download_02.log',
        '--require','Open project','--require','Download','--require','Save','--require','Save As')
    run('recovery_readback_01',PY,T/'fraktal_ab_readback.py',R/'genealogy_reference.L5X',R/'genealogy_recovered.L5X')
    run('recovery_access_01',PY,P/'audit_baseline_access.py',R/'genealogy_recovered.L5X','--output',R/'recovery_access_01.json')
    run('recovery_guard_01',PY,P/'scripts/guard_echo.py')
    run('recovery_baseline_01',PY,T/'fraktal_ab_genealogy_execute.py','--execute-fixture',
        '--expect-serial','601FC87B','--credential-file','C:/work/fraktal_echo38_access_fixture.json',
        '--output',R/'recovery_baseline_01.json')
    rows=json.loads((R/'recovery_baseline_01.json').read_text())
    assert len(rows['rows'])==31 and rows['restored'] and all(row['passed'] for row in rows['rows'])
    run('recovery_manual_01',PY,P/'ensure_manual.py','--output',R/'recovery_manual_01.json')
    run('recovery_final_checks_01',PY,P/'final_checks.py',R/'recovery_final_checks_01.json')
    run('recovery_preflight_01',PY,P/'scripts/preflight.py','--verify-only')
    # The diagnostic workflow is unchanged. It still requires fresh backup,
    # audit, source/image pins, idle/logout/documents and exact target guards.
    run('diagnostic_resumption_01',PY,OLD/'run_logged.py','resumption_02',PY,OLD/'resume_guarded_session.py')
except Exception as caught:
    error=f'{type(caught).__name__}: {caught}'
    print(error,file=sys.stderr,flush=True)
finally:
    with (R/'recovery_and_diagnostic_execution_01.json').open('x') as f:
        json.dump(dict(passed=error is None,error=error,stagesStarted=stages,
                       diagnosticDeploymentAttempted=(P/'deploy_attempt.json').exists(),
                       capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
raise SystemExit(0 if error is None else 1)
