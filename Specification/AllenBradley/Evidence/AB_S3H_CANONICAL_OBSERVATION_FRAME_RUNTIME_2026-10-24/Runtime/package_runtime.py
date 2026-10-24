"""Seal the S3h observation-frame runtime: sources, predecessors, payload."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, shutil

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3h-20261024/frame_b7a501a104b448438e1e3566840fa12f')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24'
PREP = 'AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24'
OUT = EV/NAME
ACD = 'E07C419651A2C6A785D150CAA0BB1894A57CB4453036A0CC2EF2FA8413649745'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'
pins = json.loads((R/'initial_source_verification.json').read_text())
for name, pin in pins['sha256'].items():
    assert sha(ROOT/name) == pin, name
# Download saves into the project it opens, so the probe's own hash moves after
# the download; the download-time binding and the untouched review copy hold.
assert json.loads((W/'deploy_attempt.json').read_text())['CanonicalSha256'] == ACD == sha(W/'capacity_review.ACD').upper()
saved_after_download = sha(W/'s3h_frame_canonical.ACD').upper()
session =json.loads((R/'session_execution_01.json').read_text())
start = json.loads((R/'start_execution_01.json').read_text())
assert session['passed'] and start['passed'] and all(s['exitCode'] == 0 for s in session['steps'])
fixture = json.loads((R/'candidate_regressions_01.json').read_text())
assert len(fixture['rows']) == 31 and all(r['passed'] for r in fixture['rows'])
assert len(fixture['s3hAccessRows']) == 2 and all(r['passed'] for r in fixture['s3hAccessRows'])
assert len(fixture['s3hConfigRows']) == 8 and all(r['passed'] for r in fixture['s3hConfigRows'])
baseline = json.loads((R/'baseline_regressions_01.json').read_text())
assert len(baseline['rows']) == 31 and all(r['passed'] for r in baseline['rows'])
replay = json.loads((R/'replay_01.json').read_text())
assert replay['passed'] and replay['captures'] == 88
assert json.loads((R/'final_checks_01.json').read_text())['passed']
assert json.loads((R/'dumps_before_session_01.json').read_text())['dumpFiles'] == []
assert json.loads((R/'dumps_after_session_01.json').read_text())['dumpFiles'] == []

# Every canonical predecessor, now including the observation-frame preparation.
prep = json.loads((EV/PREP/'manifest.json').read_text())
names = [s['name'] for s in prep['priorSeals']] + [PREP]
seals, total = [], 0
for name in names:
    manifest = json.loads((EV/name/'manifest.json').read_text())
    for artifact in manifest['artifacts']:
        raw = (EV/name/artifact['path']).read_bytes()
        assert len(raw) == artifact['bytes'] and hashlib.sha256(raw).hexdigest() == artifact['sha256'].lower(), \
            (name, artifact['path'])
        if artifact.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(raw)).hexdigest() == artifact['expandedSha256'].lower()
    if manifest.get('report') and manifest.get('reportSha256'):
        assert sha(EV/manifest['report']) == manifest['reportSha256'].lower(), (name, manifest['report'])
    seals.append(dict(name=name, artifacts=len(manifest['artifacts']), manifestSha256=sha(EV/name/'manifest.json')))
    total += len(manifest['artifacts'])
assert len(seals) == 40


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), target
    shutil.copyfile(source, target)


def pack(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), target
    with open(source, 'rb') as src, open(target, 'wb') as raw, \
            gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed:
        shutil.copyfileobj(src, packed)


for path in sorted(R.rglob('*')):
    if path.is_file():
        assert path.suffix.upper() not in ('.ACD', '.BAK'), path
        copy(path, OUT/'Runtime'/path.relative_to(R))
session_files = ['authorization.json', 'backup.sha256', 'baseline_capacity.json', 'baseline_reference.json', 'canonical.sha256',
                 'canonical_prepared_compare.json', 'capacity_review.json', 'deploy_attempt.json', 'preflight.json',
                 'scripts/guard_echo.py', 'scripts/preflight.py', 'ensure_manual.py', 'final_checks.py', 'measure_timing.py',
                 'audit_baseline_access.py', 'session/Program.cs', 'session/FrameSession.csproj', 'session/NuGet.Config',
                 'session_build_01.log', 'package_01.log', 'package_02.log', 'package_03.log']
for name in session_files:
    copy(W/name, OUT/'Session'/name)
for name in ('echo_before_s3h.L5X', 'canonical_downloaded.L5X', 'genealogy_restored.L5X'):
    pack(W/name, OUT/'Session'/(name + '.gz'))
assert sha(OUT/'Session/capacity_review.json') == sha(W/'capacity_review.json')

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file()]
assert not any(a['path'].upper().endswith(('.ACD', '.BAK')) for a in artifacts)
report = NAME + '.md'
timing = json.loads((R/'candidate_timing_01.json').read_text())['samples']
manifest = dict(
    schema='fraktal.ab.s3h-canonical-observation-frame-runtime-evidence', schemaVersion=1, date='2026-10-24',
    timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report), status='s3h-exit-passed-genealogy-restored',
    stageAccepted=True, acceptedScope='Local Echo 601FC87B genealogy fixture through the observation frame',
    sessionApprovalConsumed=True, approvalSource=json.loads((R/'owner_session_approval.json').read_text())['ApprovalSource'],
    preparedAcdSha256=ACD, downloadedAcdSha256=ACD, postDownloadSavedAcdSha256=saved_after_download,
    sourceSha256=prep['sourceSha256'], backupSha256=(W/'backup.sha256').read_text().strip(),
    candidateChecks=41, baselineChecks=31, recordedChecks=72, pairedCaptures=88, independentReplays=88,
    proofAttempts=dict(minimum=replay['attempts']['minimum'], maximum=replay['attempts']['maximum']),
    nativeRecordBytes=[133744, 7308, 16616], observationFrameBytes=172088,
    candidateTaskSamples=len(timing), capacityBlocks=2680132, capacityPercent=85,
    heldOutForecastBlocks=2720877, sourceBindings=len(pins['sha256']), failedOrExtraRuns=0,
    newNativeDumpsObserved=False, faultClears=0, clockChanges=0, hardKills=0,
    credentialFilesArchived=False, nativeAcdFilesArchived=False, priorSeals=seals, artifacts=artifacts,
    artifactCount=len(artifacts), totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), bytes=manifest['totalBytes'],
                      predecessors=len(seals), predecessorArtifacts=total)))
