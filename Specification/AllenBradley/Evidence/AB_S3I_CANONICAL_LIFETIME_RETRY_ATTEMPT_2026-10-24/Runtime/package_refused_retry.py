"""Seal the S3i lifetime retry that its helper refused before download."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, re, shutil

R = Path(__file__).parent
W = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/retry_prepare_1225822a67f84efc8efcb1ffeb9fffce')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3I_CANONICAL_LIFETIME_RETRY_ATTEMPT_2026-10-24'
OUT = EV/NAME
CANONICAL = re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'
start = json.loads((R/'start_execution_01.json').read_text())
session = json.loads((R/'session_execution_01.json').read_text())
assert start['passed'] is False and start['deploymentAttempted'] is False
assert session['candidateError'] == 'RuntimeError: deploy_01 failed; logs retained' and session['restoreError'] is None
assert [s['label'] for s in session['steps']] == ['preflight_before_download_01', 'deploy_01']
assert 'Prior-stage Capacity evidence changed' in (R/'deploy_01.log').read_text()
assert not (W/'deploy_attempt.json').exists() and not (W/'canonical_downloaded.L5X').exists()
for label in ('guard_after_refusal_01', 'preflight_after_refusal_01'):
    assert json.loads((R/(label + '_exit.json')).read_text())['exitCode'] == 0, label
assert json.loads((W/'compare_copies_01.json').read_text())['differing']

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


for path in sorted(R.rglob('*')):
    if path.is_file():
        assert path.suffix.upper() not in ('.ACD', '.BAK'), path
        copy(path, OUT/'Runtime'/path.relative_to(R))
for name in ('authorization.json', 'preflight.json', 'backup.sha256', 'baseline_capacity.json', 'baseline_reference.json',
             'compare_copies.py', 'compare_copies_01.json', 'compare_copies_01.log', 'compare_copies_01_exit.json'):
    copy(W/name, OUT/'Session'/name)
target = OUT/'Session/echo_before_s3i.L5X.gz'
with open(W/'echo_before_s3i.L5X', 'rb') as src, open(target, 'wb') as raw, \
        gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed:
    shutil.copyfileobj(src, packed)

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file()]
report = NAME + '.md'
manifest = dict(
    schema='fraktal.ab.s3i-canonical-lifetime-retry-attempt', schemaVersion=1, date='2026-10-24',
    timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report), status='helper-refused-before-download-controller-unchanged',
    stageAccepted=False, sessionApprovalConsumed=True, downloadAttempted=False, controllerChanges=0,
    refusal='Prior-stage Capacity evidence changed', cause='retry setup rewrote CRLF line ends of hash-bound copies',
    retryOf='AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24', faultClears=0, clockChanges=0, hardKills=0,
    credentialFilesArchived=False, nativeAcdFilesArchived=False, priorSeals=seals, priorArtifactCount=total,
    artifacts=artifacts, artifactCount=len(artifacts), totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), predecessors=len(seals), predecessorArtifacts=total)))
