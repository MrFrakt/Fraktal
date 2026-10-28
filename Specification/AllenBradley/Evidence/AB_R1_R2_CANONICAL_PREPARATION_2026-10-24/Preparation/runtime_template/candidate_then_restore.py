"""Execute only the currently authorized S3i scope; rollback in all exit paths."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-r1-r2-20261024/prepare_8f74e954758141dd81821a0c1316c2ef')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
SDK = W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
LOG = R/'run_logged.py'
PY = sys.executable
cred = 'C:/work/fraktal_echo38_access_fixture.json'
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
approval = json.loads((W/'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['CanonicalSha256'] == (W/'canonical.sha256').read_text().strip()
assert not approval['FaultClearAuthorized'] and not approval['ClockSetAuthorized']
assert json.loads((R/'backup_01_exit.json').read_text())['exitCode'] == 0
assert json.loads((R/'backup_log_audit_01.log').read_text())['Clean']
assert json.loads((R/'backup_access_01.json').read_text())['Conforms']
assert json.loads((R/'initial_source_verification.json').read_text())['passed']
steps = []


def run(label, *args):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(json.dumps(dict(stage=label, status='started', utc=started)), flush=True)
    result = subprocess.run([PY, str(LOG), label, *map(str, args)], cwd=ROOT)
    steps.append(dict(label=label, exitCode=result.returncode, startedUtc=started))
    print(json.dumps(dict(stage=label, status='finished', exitCode=result.returncode)), flush=True)
    if result.returncode:
        raise RuntimeError(label + ' failed; logs retained')


def audit(label, log, *operations):
    args = [PY, T/'fraktal_ab_sdk_log_gate.py', R/(log + '.log')]
    for operation in operations:
        args += ['--require', operation]
    run(label, *args)


error = None
restore_error = None
try:
    run('preflight_before_download_01', PY, W/'scripts/preflight.py', '--verify-only')
    run('deploy_01', SDK, 'deploy-canonical')
    audit('deploy_log_audit_01', 'deploy_01', 'Open project', 'Download', 'Save', 'Save As')
    run('deploy_readback_01', PY, T/'fraktal_ab_readback.py', W/'s3i_bench_05.L5X', W/'canonical_downloaded.L5X')
    run('deploy_access_01', PY, W/'audit_access.py', W/'canonical_downloaded.L5X', R/'deploy_access_01.json')
    run('guard_candidate_01', PY, W/'scripts/guard_echo.py')
    run('candidate_regressions_01', PY, W/'run_candidate.py', 'fixture', '--execute-fixture', '--expect-serial', '601FC87B',
        '--credential-file', cred, '--output', R/'candidate_regressions_01.json')
    run('manual_candidate_01', PY, W/'ensure_manual.py', '--output', R/'manual_candidate_01.json')
    run('calendar_01', PY, W/'run_candidate.py', 'lifetime', '--phase', 'calendar',
        '--execute-fixture', '--expect-serial', '601FC87B', '--authorization-file', W/'authorization.json',
        '--credential-file', cred, '--output', R/'calendar_01.json')
    run('retained_cycle_01', SDK, 'cycle-retained')
    audit('retained_cycle_log_audit_01', 'retained_cycle_01', 'Open project')
    retained=json.loads((W/'retained_cycle.json').read_text())
    assert retained['Passed'] and not retained['DownloadPerformed'] and retained['SourceAcdUnchanged']
    run('manual_retained_01', PY, W/'ensure_manual.py', '--output', R/'manual_retained_01.json')
    run('retention_01', PY, W/'run_candidate.py', 'lifetime', '--phase', 'retention',
        '--execute-fixture', '--expect-serial', '601FC87B', '--authorization-file', W/'authorization.json',
        '--before', R/'calendar_01.json', '--output', R/'retention_01.json')
    run('idle_equivalence_01', PY, W/'run_candidate.py', 'equivalence', '--expect-serial', '601FC87B', '--output', R/'idle_equivalence_01.json.gz')
    run('generic_acquire_01', PY, T/'fraktal_ab_canonical_acquire.py', '--expect-serial', '601FC87B',
        '--output', R/'generic_snapshot_01.json.gz', '--capture-output', R/'generic_capture_01.json.gz')
    run('candidate_timing_01', PY, W/'measure_timing.py', R/'candidate_timing_01.json', '--candidate')
except Exception as caught:
    error = f'{type(caught).__name__}: {caught}'
    print(json.dumps(dict(candidateError=error)), flush=True)
finally:
    try:
        if (W/'deploy_attempt.json').exists():
            run('restore_genealogy_01', SDK, 'restore-genealogy')
            audit('restore_log_audit_01', 'restore_genealogy_01', 'Open project', 'Download', 'Save', 'Save As')
            run('restore_access_01', PY, R/'audit_baseline_access.py', W/'genealogy_restored.L5X', '--output', R/'restore_access_01.json')
            run('guard_baseline_01', PY, W/'scripts/guard_echo.py')
            run('baseline_regressions_01', PY, T/'fraktal_ab_genealogy_execute.py', '--execute-fixture', '--expect-serial', '601FC87B',
                '--credential-file', cred, '--output', R/'baseline_regressions_01.json')
            run('manual_final_01', PY, W/'ensure_manual.py', '--output', R/'manual_final_01.json')
            run('final_checks_01', PY, W/'final_checks.py', R/'final_checks_01.json')
            run('preflight_final_01', PY, W/'scripts/preflight.py', '--verify-only')
            run('baseline_timing_01', PY, W/'measure_timing.py', R/'baseline_timing_01.json')
    except Exception as caught:
        restore_error = f'{type(caught).__name__}: {caught}'
        print(json.dumps(dict(restoreError=restore_error)), flush=True)
    rows = [dict(path=p.relative_to(DUMPS).as_posix(), bytes=p.stat().st_size) for p in sorted(DUMPS.rglob('*.dmp'))]
    with (R/'dumps_after_session_01.json').open('x') as out:
        json.dump(dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), readOnly=True, dumpFiles=rows), out, indent=2)
    with (R/'session_execution_01.json').open('x') as out:
        json.dump(dict(passed=error is None and restore_error is None, candidateError=error, restoreError=restore_error,
                       steps=steps, capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat()), out, indent=2)
raise SystemExit(0 if error is None and restore_error is None else 1)
