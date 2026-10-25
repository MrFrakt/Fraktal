"""Bind the owner's retry approval to the sealed retry preparation and unchanged image."""
from pathlib import Path
import datetime, gzip, hashlib, json, shutil

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/retry_prepare_1225822a67f84efc8efcb1ffeb9fffce')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
E = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3I_CANONICAL_LIFETIME_RETRY_PREPARATION_2026-10-24'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert sha(E/NAME/'manifest.json') == '186e32ffb08ffeaa42c4cea750369c9b268b223b142aae0608d9d5f64add4288'
manifest = json.loads((E/NAME/'manifest.json').read_text(encoding='utf-8'))
assert sha(E/manifest['report']) == manifest['reportSha256']
for row in manifest['artifacts']:
    raw = (E/NAME/row['path']).read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
bindings = json.loads((E/NAME/'Preparation/source_bindings_01.json').read_text())['sha256']
assert len(bindings) == 172 and all(sha(ROOT/name) == pin for name, pin in bindings.items())
pin = manifest['preparedAcdSha256']
assert pin == 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
for name in ('s3i_canonical.ACD', 'capacity_review.ACD', 'retention_control.ACD'):
    assert sha(W/name).upper() == pin, name
assert sha(W/'s3i_bench_05.L5X') == manifest['sourceSha256']
for name in ('preflight.json', 'deploy_attempt.json', 'backup.sha256', 'echo_before_s3i.ACD', 'canonical_downloaded.L5X',
             'genealogy_restored.L5X', 'retained_cycle.json'):
    assert not (W/name).exists(), name
for name in ('session/Program.cs', 'scripts/guard_echo.py', 'scripts/preflight.py', 'scripts/retention_preflight.py',
             'scripts/retention_readiness.py', 'ensure_manual.py', 'final_checks.py', 'measure_timing.py', 'audit_access.py',
             'audit_baseline_access.py', 'runtime_template/start_session.py', 'runtime_template/candidate_then_restore.py'):
    assert sha(W/name) == sha(E/NAME/'Preparation'/name), name
sdk = W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
assert sha(sdk) == manifest['sessionExecutableSha256'] and sha(sdk.with_suffix('.dll')) == manifest['sessionAssemblySha256']
prior = json.loads((E/'AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24/Session/authorization.json').read_text())
approval = dict(
    CurrentOwnerApproved=True, ManualNormalizationAuthorized=True, AccessVectorsAuthorized=True,
    ConfigurationVectorsAuthorized=True, NativeLineVectorsAuthorized=True, CalendarLifetimeVectorsAuthorized=True,
    RetainedCycleAuthorized=True, FaultClearAuthorized=False, ClockSetAuthorized=False, Serial='601FC87B',
    CanonicalSha256=pin, SourceSha256=manifest['sourceSha256'], RuntimeDirectory=R.as_posix(),
    MaxCalendarCommits=64, NormalCalendarCommits=38, RetainedProgramRunCycles=1,
    NativeFirstScanVectors=8, NativeFirstScanExecutions=2, CandidateRows=41, BaselineRows=31,
    Scope=prior['Scope'], Excluded=prior['Excluded'],
    ApprovalSource=('Owner chat reply 2026-10-24 "yes" to: approve the S3i lifetime rerun on Echo 601FC87B for ACD '
                    'A5FAFA46...7E36C42 - same scope as before from the new workspace; fault clears, clock changes, '
                    'firmware/network changes, power operations, hard kills and vendor-state edits excluded'),
    RetryOf='Evidence/AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24.md',
    ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    PreparationManifestSha256=sha(E/NAME/'manifest.json'), PreparationReportSha256=manifest['reportSha256'],
    SessionExecutableSha256=sha(sdk), SessionAssemblySha256=sha(sdk.with_suffix('.dll')),
    SessionSourceSha256=sha(W/'session/Program.cs'))
assert json.loads((W/'authorization.json').read_text())['CurrentOwnerApproved'] is False
(W/'authorization.json').rename(R/'preapproval_working_authorization.json')
for path in (W/'authorization.json', R/'owner_session_approval.json'):
    with path.open('x', encoding='utf-8') as out:
        json.dump(approval, out, indent=2)
with (R/'initial_source_verification.json').open('x') as out:
    json.dump(dict(passed=True, sourceBindings=len(bindings), sha256=bindings, preparedAcdSha256=pin,
                   sourceSha256=manifest['sourceSha256'], sessionExecutableSha256=sha(sdk),
                   sessionAssemblySha256=sha(sdk.with_suffix('.dll'))), out, indent=2)
for name in ('start_session.py', 'candidate_then_restore.py'):
    shutil.copyfile(W/'runtime_template'/name, R/name)
for name in ('run_logged.py', 'audit_baseline_access.py'):
    shutil.copyfile(W/name, R/name)
print(json.dumps(dict(passed=True, sourceBindings=len(bindings), canonicalSha256=pin, controllerOperations=0)))
