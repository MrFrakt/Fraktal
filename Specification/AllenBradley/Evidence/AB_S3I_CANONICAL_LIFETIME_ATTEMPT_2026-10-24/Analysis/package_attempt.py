"""Seal the failed S3i lifetime attempt: runtime, session files, analysis, predecessors."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, re, shutil

A = Path(__file__).parent
R = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/runtime_9fe4b2baee484ed2bb9b25b66cd32168')
P = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/prepare_9af0ac9f71534d89b5be9645bdc6575f')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24'
OUT = EV/NAME
ACD = 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
CANONICAL = re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'
session = json.loads((R/'session_execution_01.json').read_text())
assert session['passed'] is False and session['candidateError'] == 'RuntimeError: calendar_01 failed; logs retained'
assert session['restoreError'] is None
failed_at = [s['label'] for s in session['steps'] if s['exitCode']]
assert failed_at == ['calendar_01'], failed_at
assert json.loads((P/'deploy_attempt.json').read_text())['CanonicalSha256'] == ACD
assert json.loads((A/'replay_attempt_01.json').read_text())['captures'] == 87
assert json.loads((R/'final_checks_01.json').read_text())['passed']

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
for name in ('authorization.json', 'preflight.json', 'deploy_attempt.json', 'backup.sha256'):
    copy(P/name, OUT/'Session'/name)
for name in ('echo_before_s3i.L5X', 'canonical_downloaded.L5X', 'genealogy_restored.L5X'):
    pack(P/name, OUT/'Session'/(name + '.gz'))
for path in sorted(A.iterdir()):
    if path.is_file():
        copy(path, OUT/'Analysis'/path.name)

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file()]
assert not any(a['path'].upper().endswith(('.ACD', '.BAK')) for a in artifacts)
report = NAME + '.md'
manifest = dict(
    schema='fraktal.ab.s3i-canonical-lifetime-attempt', schemaVersion=1, date='2026-10-24',
    timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report), status='calendar-capture-failed-genealogy-restored',
    stageAccepted=False, calendarLifetimeAccepted=False, retentionAccepted=False, sessionApprovalConsumed=True,
    approvalQuestion='call_cc943a76fb914520bb418dda6ea4beaf:0', downloadedAcdSha256=ACD,
    failedStage='calendar_01', failedPhase='original_empty_profile', calendarWrites=0,
    candidateChecksPassed=41, baselineChecksPassed=31, acceptedFixturePairsReplayed=87,
    notReached=['retained_cycle_01', 'manual_retained_01', 'retention_01', 'idle_equivalence_01',
                'generic_acquire_01', 'candidate_timing_01'],
    cause='mailbox writer at 500 bytes passed to the frame oracle', newNativeDumpsObserved=False,
    faultClears=0, clockChanges=0, hardKills=0, credentialFilesArchived=False, nativeAcdFilesArchived=False,
    priorSeals=seals, priorArtifactCount=total, artifacts=artifacts, artifactCount=len(artifacts),
    totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), bytes=manifest['totalBytes'],
                      predecessors=len(seals), predecessorArtifacts=total)))
