"""Authorized S3k option A download on Echo 601FC87B; read-only checks only after it.

Stops at the first failed gate. No mailbox/tag write, restore, fault clear or
clock change is attempted: those need their own current authorization.
"""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
S3J = Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
A = Path('C:/work/fraktal-ab-s3k-20261025/command_a_02')
PY = sys.executable
SDK = D/'session/bin/Debug/net8.0/win-x86/S3kSession.exe'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()

approval = json.loads((D/'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['DownloadAuthorized'] and approval['Serial'] == '601FC87B'
assert not any(approval[k] for k in ('MailboxOrTagWritesAuthorized', 'RestoreGenealogyAuthorized', 'FaultClearAuthorized', 'ClockSetAuthorized'))
assert sha(D/'s3k_command_a.ACD') == approval['CanonicalSha256'] == (D/'canonical.sha256').read_text().strip()
assert sha(D/'s3k_command_a.L5X') == approval['SourceSha256']
# The offline gates of this exact image must still be green.
assert json.loads((A/'sealed_01.json').read_text())['passed']
stages, error = [], None


def dumps(label):
    rows = [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size) for p in sorted(DUMPS.rglob('*.dmp'))]
    with (D/(label+'.json')).open('x') as out:
        json.dump(dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), readOnly=True, dumpFiles=rows), out, indent=2)
    return rows


def run(label, *args):
    print(json.dumps(dict(stage=label, status='started')), flush=True)
    stages.append(label)
    subprocess.run([PY, str(D/'run_logged.py'), label, *map(str, args)], cwd=ROOT, check=True)


def audit(label, log, *operations):
    args = [PY, T/'fraktal_ab_sdk_log_gate.py', D/(log+'.log')]
    for operation in operations: args += ['--require', operation]
    run(label, *args)


try:
    run('guard_initial_01', PY, S3J/'scripts/guard_echo.py')
    if dumps('dumps_before_01'): raise RuntimeError('existing controller dump files; inspect before any controller change')
    run('preflight_initial_01', PY, S3J/'scripts/preflight.py', '--verify-only')
    run('backup_01', SDK, 'backup')
    audit('backup_log_audit_01', 'backup_01', 'Save As')
    run('backup_access_01', PY, S3J/'audit_baseline_access.py', D/'echo_before_s3k.L5X', '--output', D/'backup_access_01.json')
    run('deploy_01', SDK, 'deploy-canonical')
    audit('deploy_log_audit_01', 'deploy_01', 'Open project', 'Download', 'Save', 'Save As')
    run('deploy_readback_01', PY, T/'fraktal_ab_readback.py', D/'s3k_command_a.L5X', D/'canonical_downloaded.L5X')
    run('deploy_access_01', PY, A/'audit_access.py', D/'canonical_downloaded.L5X', D/'deploy_access_01.json')
    run('guard_candidate_01', PY, S3J/'scripts/guard_echo.py')
    # Read-only from here: discovery/acquisition, idle equivalence, TASK timing.
    run('generic_acquire_01', PY, T/'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',
        '--output', D/'generic_snapshot_01.json.gz', '--capture-output', D/'generic_capture_01.json.gz')
    run('idle_equivalence_01', PY, T/'fraktal_ab_s3k_equivalence.py', '--expect-serial', '601FC87B', '--output', D/'idle_equivalence_01.json.gz')
    run('candidate_timing_01', PY, S3J/'measure_timing.py', D/'candidate_timing_01.json', '--candidate')
    run('guard_final_01', PY, S3J/'scripts/guard_echo.py')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
    print(json.dumps(dict(error=error)), flush=True)
finally:
    after = dumps('dumps_after_01')
    with (D/'session_execution_01.json').open('x') as out:
        json.dump(dict(passed=error is None and not after, error=error, stagesStarted=stages,
                       deploymentAttempted=(D/'deploy_attempt.json').exists(), restoreAttempted=False,
                       controllerWritesOtherThanDownload=0,
                       capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
raise SystemExit(0 if error is None else 1)
