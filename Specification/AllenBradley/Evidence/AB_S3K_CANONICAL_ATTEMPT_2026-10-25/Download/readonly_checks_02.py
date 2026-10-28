"""Resume only the read-only checks after the reader fix; no controller change."""
from pathlib import Path
import datetime, json, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
S3J = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
PY = sys.executable
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
first = json.loads((D/'session_execution_01.json').read_text())
# Download, read-back, access and the candidate guard passed; only acquisition failed.
assert first['deploymentAttempted'] and first['stagesStarted'][-1] == 'generic_acquire_01'
for label in ('deploy_01', 'deploy_log_audit_01', 'deploy_readback_01', 'deploy_access_01', 'guard_candidate_01'):
    assert json.loads((D/(label+'_exit.json')).read_text())['exitCode'] == 0, label
stages, error = [], None


def run(label, *args):
    print(json.dumps(dict(stage=label, status='started')), flush=True)
    stages.append(label)
    subprocess.run([PY, str(D/'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)


try:
    run('guard_candidate_02', PY, S3J/'scripts/guard_echo.py')
    run('generic_acquire_02', PY, T/'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',
        '--output', D/'generic_snapshot_02.json.gz', '--capture-output', D/'generic_capture_02.json.gz')
    run('idle_equivalence_01', PY, T/'fraktal_ab_s3k_equivalence.py', '--expect-serial', '601FC87B', '--output', D/'idle_equivalence_01.json.gz')
    run('candidate_timing_01', PY, S3J/'measure_timing.py', D/'candidate_timing_01.json', '--candidate')
    run('guard_final_01', PY, S3J/'scripts/guard_echo.py')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
    print(json.dumps(dict(error=error)), flush=True)
finally:
    rows = [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size) for p in sorted(DUMPS.rglob('*.dmp'))]
    with (D/'readonly_checks_02.json').open('x') as out:
        json.dump(dict(passed=error is None and not rows, error=error, stagesStarted=stages, readOnly=True, dumpFiles=rows,
                       capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
raise SystemExit(0 if error is None else 1)
