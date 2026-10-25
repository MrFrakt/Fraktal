"""Seal the accepted S3i lifetime runtime: runtime, session files, predecessors."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, re, shutil

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/retry2_prepare_8a934eccd6e548aea4d0c1c5a2e06db7')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3I_CANONICAL_LIFETIME_RUNTIME_2026-10-24'
OUT = EV/NAME
ACD = 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
CANONICAL = re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'
pins = json.loads((R/'initial_source_verification.json').read_text())
for name, pin in pins['sha256'].items():
    assert sha(ROOT/name) == pin, name
start = json.loads((R/'start_execution_01.json').read_text())
session = json.loads((R/'session_execution_01.json').read_text())
assert start['passed'] and session['passed'] and all(s['exitCode'] == 0 for s in session['steps'])
assert json.loads((W/'deploy_attempt.json').read_text())['CanonicalSha256'] == ACD == sha(W/'capacity_review.ACD').upper()
assert sha(W/'retention_control.ACD').upper() == ACD
fixture = json.loads((R/'candidate_regressions_01.json').read_text())
assert len(fixture['rows']) == 31 and all(r['passed'] for r in fixture['rows'])
assert all(r['passed'] for k in ('s3iAccessRows', 's3iConfigRows') for r in fixture[k])
calendar = json.loads((R/'calendar_01.json').read_text())
assert calendar['passed'] and len(calendar['rows']) == 7 and calendar['calendarWriteCount'] == 38
assert calendar['configurationRestored'] and 'cleanupError' not in calendar
retained = json.loads((W/'retained_cycle.json').read_text())
assert retained['Passed'] and not retained['DownloadPerformed'] and retained['SourceAcdUnchanged']
assert json.loads((R/'retention_01.json').read_text())['passed']
assert len(json.loads((R/'baseline_regressions_01.json').read_text())['rows']) == 31
replay = json.loads((R/'replay_01.json').read_text())
assert replay['passed'] and replay['captures'] == 97
assert json.loads((R/'final_checks_01.json').read_text())['passed']
assert json.loads((R/'dumps_before_session_01.json').read_text())['dumpFiles'] == []
assert json.loads((R/'dumps_after_session_01.json').read_text())['dumpFiles'] == []

seals, total = [], 0
for path in sorted(EV.glob('AB_*/manifest.json')):
    name = path.parent.name
    if not CANONICAL.match(name) or name == NAME:
        continue
    manifest = json.loads(path.read_text())
    for artifact in manifest['artifacts']:
        raw = (path.parent/artifact['path']).read_bytes()
        assert len(raw) == artifact['bytes'] and hashlib.sha256(raw).hexdigest() == artifact['sha256'].lower(), \
            (name, artifact['path'])
        if artifact.get('expandedSha256'):
            assert hashlib.sha256(gzip.decompress(raw)).hexdigest() == artifact['expandedSha256'].lower()
    if manifest.get('report') and manifest.get('reportSha256'):
        assert sha(EV/manifest['report']) == manifest['reportSha256'].lower(), (name, manifest['report'])
    seals.append(dict(name=name, artifacts=len(manifest['artifacts']), manifestSha256=sha(path)))
    total += len(manifest['artifacts'])


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
for name in ('authorization.json', 'preflight.json', 'deploy_attempt.json', 'backup.sha256', 'retained_cycle.json'):
    copy(W/name, OUT/'Session'/name)
for name in ('echo_before_s3i.L5X', 'canonical_downloaded.L5X', 'genealogy_restored.L5X'):
    pack(W/name, OUT/'Session'/(name + '.gz'))

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file()]
assert not any(a['path'].upper().endswith(('.ACD', '.BAK')) for a in artifacts)
report = NAME + '.md'
timing = json.loads((R/'candidate_timing_01.json').read_text())['samples']
manifest = dict(
    schema='fraktal.ab.s3i-canonical-lifetime-runtime', schemaVersion=1, date='2026-10-24',
    timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report), status='s3i-exit-passed-genealogy-restored',
    stageAccepted=True, calendarLifetimeAccepted=True, retentionAccepted=True,
    acceptedScope='Local Echo 601FC87B genealogy fixture through the migration frame',
    sessionApprovalConsumed=True,
    approvalSource=json.loads((R/'owner_session_approval.json').read_text())['ApprovalSource'],
    downloadedAcdSha256=ACD, sourceSha256=pins['sourceSha256'], backupSha256=(W/'backup.sha256').read_text().strip(),
    candidateChecks=41, calendarRows=7, calendarCommits=38, retentionRows=1, nativeFirstScanVectors=8,
    baselineChecks=31, pairedCapturesReplayed=97, proofAttempts=dict(minimum=replay['attempts']['minimum'],
    maximum=replay['attempts']['maximum']), retainedProgramRunCycles=1, downloadInCycle=False,
    candidateTaskSamples=len(timing), candidateCumulativeMaxScanUs=9206, idlePaths=4010,
    sourceBindings=len(pins['sha256']), failedOrExtraRuns=0, newNativeDumpsObserved=False, faultClears=0,
    clockChanges=0, hardKills=0, credentialFilesArchived=False, nativeAcdFilesArchived=False,
    priorSeals=seals, priorArtifactCount=total, artifacts=artifacts, artifactCount=len(artifacts),
    totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), bytes=manifest['totalBytes'],
                      predecessors=len(seals), predecessorArtifacts=total)))
