"""Complete the same authorized rollback after restoring original host documents."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

R = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'
PRIOR = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
approval = json.loads((R / 'authorization.json').read_bytes())
assert approval['CurrentOwnerApproved'] and approval['RestoreGenealogyAuthorized'] and approval['BaselineRegressionWritesAuthorized']
assert approval['Serial'] == '601FC87B' and not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
assert json.loads((R / 'medium_restored_01.json').read_bytes())['passed']
assert hashlib.sha256(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).hexdigest().upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'


def run(label, *args):
    print(json.dumps(dict(stage=label, status='started')), flush=True)
    subprocess.run([sys.executable, str(R / 'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)


error = None
try:
    run('guard_rollback_completion', sys.executable, R / 'scripts/guard_echo.py')
    run('baseline_regressions_02', sys.executable, T / 'fraktal_ab_genealogy_execute.py', '--execute-fixture',
        '--expect-serial', '601FC87B', '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json',
        '--output', R / 'baseline_regressions_02.json')
    run('manual_final', sys.executable, R / 'ensure_manual_baseline.py', '--output', R / 'manual_final.json')
    run('final_checks', sys.executable, PRIOR / 'final_checks.py', R / 'final_checks.json')
    run('preflight_final', sys.executable, R / 'scripts/preflight.py', '--verify-only')
    run('baseline_timing', sys.executable, PRIOR / 'measure_timing.py', R / 'baseline_timing.json')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
dump_root = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
dumps = [str(path) for path in dump_root.rglob('*.dmp')]
result = dict(passed=error is None and not dumps, error=error, genealogyRestored=error is None,
              candidateAccepted=False, authorizationConsumed=True, dumpFiles=dumps,
              additionalDownloads=0, faultClears=0, clockChanges=0, powerOperations=0, hardKills=0,
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R / 'rollback_completion_01.json').open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result), flush=True)
raise SystemExit(0 if result['passed'] else 1)
