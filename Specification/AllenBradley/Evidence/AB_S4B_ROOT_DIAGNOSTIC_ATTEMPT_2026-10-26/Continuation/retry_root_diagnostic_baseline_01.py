"""One unchanged retry to complete the current session's approved rollback.

The failed 22-row run and its residual cleanup remain separate evidence.
This starts no download or candidate image session and adds no write vectors.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys

D = Path('C:/work/fraktal-ab-s4b-20261025/retry_root_diagnostic_01')
R = Path('C:/Users/SoftIndVM/Fraktal')
approval = json.loads((D / 'authorization.json').read_bytes())
assert approval['OwnerInstruction'] == 'Approve guarded S4b root diagnostic session'
assert approval['ApprovalQuestion'] == 'call_0c97c2f8c5c84620bbb108165c7177cd:0'
assert approval['BaselineRegressionWritesAuthorized'] is True
assert json.loads((D / 'rollback_cleanup_01.json').read_bytes())['passed']
assert json.loads((D / 'final_checks_cleanup_01.json').read_bytes())['passed']
assert json.loads((D / 'preflight_cleanup_01_exit.json').read_bytes())['exitCode'] == 0
assert not (D / 'baseline_regressions_retry_01.json').exists()
old = json.loads((D / 'baseline_regressions.json').read_bytes())
assert len(old['rows']) == 22 and old['error'] == 'ready mode 2 timed out: step=0, error=0'
record = dict(scope='Complete the current approved rollback with one unchanged 31-case baseline retry',
    ownerInstruction=approval['OwnerInstruction'], approvalQuestion=approval['ApprovalQuestion'],
    authorizationSha256=hashlib.sha256((D / 'authorization.json').read_bytes()).hexdigest(),
    previousFailureRetained=True, originalBaselineCasesPassed=22, newWriteVectors=0,
    newDownloadSession=False, clockChanges=0, faultClears=0, powerOperations=0,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D / 'rollback_continuation_01.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], cwd=R, check=True)
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
command = [sys.executable, str(R / 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_genealogy_execute.py'),
    '--execute-fixture', '--expect-serial', '601FC87B',
    '--credential-file', 'C:/work/fraktal_echo38_access_fixture.json',
    '--output', str(D / 'baseline_regressions_retry_01.json')]
raise SystemExit(subprocess.run(command, cwd=R).returncode)
