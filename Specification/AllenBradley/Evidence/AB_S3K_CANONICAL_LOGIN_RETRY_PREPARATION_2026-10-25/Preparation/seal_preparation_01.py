"""Append-only corrected-image preparation; verify every prior seal first."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
R = W.parent / 'retry_login_01'
E = ROOT / 'Specification/AllenBradley/Evidence'
NAME = 'AB_S3K_CANONICAL_LOGIN_RETRY_PREPARATION_2026-10-25'
OUT = E / NAME
load = lambda p: json.loads(p.read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def save(path, value):
    write(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


assert not OUT.exists()
assert load(W / 'final_preparation_checks_01.json')['passed']
assert not (R / 'authorization.json').exists() and not (R / 'session_started.json').exists()
previous = E / 'AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25/manifest.json'
prior = load(previous)
names = {row['name'] for row in prior['priorSeals']} | {previous.parent.name}
seals, total = [], 0
for index, name in enumerate(sorted(names)):
    manifest = E / name / 'manifest.json'
    old = load(manifest)
    for row in old['artifacts']:
        data = (manifest.parent / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'].lower(), (name, row['path'])
        if row.get('expandedSha256'):
            assert sha(gzip.decompress(data)) == row['expandedSha256'].lower()
    if old.get('reportSha256'):
        assert sha((E / old['report']).read_bytes()) == old['reportSha256'].lower()
    seals.append(dict(name=name, manifestSha256=sha(manifest.read_bytes()), artifacts=len(old['artifacts'])))
    total += len(old['artifacts'])
    if index % 10 == 0:
        print(json.dumps(dict(priorSealsVerified=index + 1)), flush=True)
assert len(seals) == 61
save(W / 'prior_seals_preparation_01.json', dict(passed=True, records=len(seals), artifacts=total, rows=seals))

bindings = load(R / 'source_bindings.json')
for path, expected in bindings['sha256'].items():
    assert sha(Path(path).read_bytes()).upper() == expected.upper(), path
artifacts = []


def archive(source, relative, compress=False):
    raw = source.read_bytes()
    data = gzip.compress(raw, mtime=0) if compress else raw
    name = relative + ('.gz' if compress else '')
    write(OUT / name, data)
    row = dict(path=name, bytes=len(data), sha256=sha(data))
    if compress:
        row['expandedSha256'] = sha(raw)
    artifacts.append(row)


for folder, prefix in ((W, 'Preparation'), (R, 'Retry')):
    for source in sorted(folder.rglob('*')):
        if not source.is_file() or any(part in ('bin', 'obj', '__pycache__') for part in source.relative_to(folder).parts):
            continue
        if source.suffix.lower() not in ('.py', '.json', '.gz', '.log', '.l5x', '.cs', '.csproj', '.txt', '.sha256'):
            continue
        assert 'credential' not in source.name.lower(), source
        archive(source, prefix + '/' + source.relative_to(folder).as_posix(), source.suffix.lower() == '.l5x')
source_count = 0
for name in bindings['sha256']:
    source = Path(name)
    if source.is_relative_to(ROOT):
        archive(source, 'Source/' + source.relative_to(ROOT).as_posix(), True)
        source_count += 1
report = E / (NAME + '.md')
manifest = dict(schema='fraktal.ab.s3k-login-retry-preparation', schemaVersion=1,
                date='2026-10-25', timeZone='America/Mexico_City',
                sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                report=report.name, reportSha256=sha(report.read_bytes()),
                status='offline-passed-native-retry-needs-current-authorization', nativeAccepted=False,
                correctedImageDownloaded=False, currentControllerChangesAuthorized=False,
                genealogyRestored=True, rollbackRestoresOriginalHostDocuments=True, abTests=2295, rootTests=74, priorImages=12, priorCaptures=1431,
                preparedAcdSha256=sha((R / 's3k_command_a.ACD').read_bytes()).upper(),
                generatedSourceSha256=sha((R / 's3k_command_a.L5X').read_bytes()).upper(),
                capacity=load(W / 'capacity_auto_02.json'), sourceBindings=source_count,
                priorSeals=seals, priorArtifacts=total, artifactCount=len(artifacts), artifacts=artifacts,
                credentialFilesArchived=False, nativeAcdFilesArchived=False, committed=False, pushed=False)
save(OUT / 'manifest.json', manifest)
for row in artifacts:
    data = (OUT / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    if row.get('expandedSha256'):
        assert sha(gzip.decompress(data)) == row['expandedSha256']
result = dict(passed=True, manifest=(OUT / 'manifest.json').as_posix(),
              manifestSha256=sha((OUT / 'manifest.json').read_bytes()), artifacts=len(artifacts),
              sourceBindings=source_count, priorSeals=len(seals), priorArtifacts=total,
              retryApproved=False, correctedImageDownloaded=False, genealogyRestored=True)
save(W / 'sealed_preparation_01.json', result)
print(json.dumps(result), flush=True)
