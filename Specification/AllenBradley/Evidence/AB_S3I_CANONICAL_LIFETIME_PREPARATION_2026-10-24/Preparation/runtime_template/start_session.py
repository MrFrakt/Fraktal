"""Stop at the first failed dependency; the candidate driver owns rollback."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PY = sys.executable
SDK = W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dumps(label):
    rows = [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size,
                 modifiedUtc=datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).isoformat())
            for p in sorted(DUMPS.rglob('*.dmp'))]
    with (R/(label + '.json')).open('x') as out:
        json.dump(dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), readOnly=True,
                       dumpFiles=rows), out, indent=2)
    return rows


pins = json.loads((R/'initial_source_verification.json').read_text())
for name, pin in pins['sha256'].items():
    assert sha(ROOT/name) == pin, name
approval = json.loads((W/'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['Serial'] == '601FC87B'
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
assert sha(W/'s3i_canonical.ACD').upper() == pins['preparedAcdSha256'] == approval['CanonicalSha256']
assert sha(SDK) == approval['SessionExecutableSha256']
for label in ('ab_suite_01','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_02'):
    assert json.loads((W/(label+'_exit.json')).read_text())['exitCode'] == 0, label
stages, error = [], None


def run(label, *args):
    print(json.dumps(dict(stage=label, status='started')), flush=True)
    stages.append(label)
    # No later command can run after a refused guard or failed audit.
    subprocess.run([PY, str(R/'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)
    print(json.dumps(dict(stage=label, status='finished')), flush=True)


try:
    run('guard_initial_01', PY, W/'scripts/guard_echo.py')
    if dumps('dumps_before_session_01'):
        raise RuntimeError('existing controller dump files; inspect before any controller change')
    run('manual_initial_01', PY, W/'ensure_manual.py', '--output', R/'manual_initial_01.json')
    run('preflight_initial_01', PY, W/'scripts/preflight.py')
    run('backup_01', SDK, 'backup')
    run('backup_log_audit_01', PY, T/'fraktal_ab_sdk_log_gate.py', R/'backup_01.log', '--require', 'Save As')
    run('backup_access_01', PY, R/'audit_baseline_access.py', W/'echo_before_s3i.L5X', '--output', R/'backup_access_01.json')
    run('session_01', PY, R/'candidate_then_restore.py')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
with (R/'start_execution_01.json').open('x') as out:
    json.dump(dict(passed=error is None, error=error, stagesStarted=stages,
                   deploymentAttempted=(W/'deploy_attempt.json').exists(),
                   capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
if error:
    print(error, file=sys.stderr)
raise SystemExit(0 if error is None else 1)
