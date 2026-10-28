"""S3k request cases on the downloaded image; needs request_authorization.json set by a current owner approval.

Stops at the first failed gate. The fixture owns cleanup of everything it changes.
Afterwards only read-only checks run. No download, restore, fault clear or clock change.
"""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
S3J = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
PY = sys.executable
CREDENTIAL = 'C:/work/fraktal_echo38_access_fixture.json'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
# The accepted procedure's oracle selects its station at import time.
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_s3k_demo'

approval = json.loads((D/'request_authorization.json').read_text())
pin = (D/'canonical.sha256').read_text().strip()
assert approval['CurrentOwnerApproved'] and approval['MailboxOrTagWritesAuthorized'] and approval['CanonicalSha256'] == pin
assert json.loads((D/'deploy_attempt.json').read_text())['CanonicalSha256'] == pin
for label in ('deploy_01', 'deploy_readback_01', 'deploy_access_01', 'generic_acquire_02', 'idle_equivalence_02',
              'dry_run_typed_03', 'ab_suite_request_cases_02'):
    assert json.loads((D/(label+'_exit.json')).read_text())['exitCode'] == 0, label
stages, error = [], None


def run(label, *args):
    print(json.dumps(dict(stage=label, status='started')), flush=True)
    stages.append(label)
    subprocess.run([PY, str(D/'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)


def dumps():
    return [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size) for p in sorted(DUMPS.rglob('*.dmp'))]


try:
    run('guard_requests_02', PY, S3J/'scripts/guard_echo.py')
    if dumps(): raise RuntimeError('existing controller dump files; inspect before any write')
    run('request_cases_02', PY, T/'fraktal_ab_s3k_fixture_execute.py', '--authorization-file', D/'request_authorization.json',
        '--expect-acd-sha256', pin, '--execute-fixture', '--expect-serial', '601FC87B',
        '--credential-file', CREDENTIAL, '--output', D/'request_cases_02.json')
    run('guard_after_requests_02', PY, S3J/'scripts/guard_echo.py')
    run('idle_equivalence_03', PY, T/'fraktal_ab_s3k_equivalence.py', '--expect-serial', '601FC87B', '--output', D/'idle_equivalence_03.json.gz')
    run('generic_acquire_03', PY, T/'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',
        '--output', D/'generic_snapshot_03.json.gz', '--capture-output', D/'generic_capture_03.json.gz')
    run('candidate_timing_02', PY, S3J/'measure_timing.py', D/'candidate_timing_02.json', '--candidate')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
    print(json.dumps(dict(error=error)), flush=True)
finally:
    after = dumps()
    with (D/'request_session_02.json').open('x') as out:
        json.dump(dict(passed=error is None and not after, error=error, stagesStarted=stages, dumpFiles=after,
                       capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
raise SystemExit(0 if error is None else 1)
