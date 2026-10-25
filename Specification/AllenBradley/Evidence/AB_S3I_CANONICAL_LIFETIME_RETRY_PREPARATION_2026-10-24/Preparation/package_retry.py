"""Seal the S3i lifetime retry preparation: workspace, changed sources, predecessors."""
from datetime import datetime, timezone
from pathlib import Path
import gzip, hashlib, json, re, shutil

W = Path(__file__).parent
L = Path('C:/work/fraktal-ab-s3i-lifetime-20261024/retry_fix_01')
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
EV = ROOT/'Specification/AllenBradley/Evidence'
NAME = 'AB_S3I_CANONICAL_LIFETIME_RETRY_PREPARATION_2026-10-24'
OUT = EV/NAME
ACD = 'A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
CANONICAL = re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert not (OUT/'manifest.json').exists(), 'append-only: already sealed'
bindings = json.loads((W/'source_bindings_01.json').read_text())
for name, pin in bindings['sha256'].items():
    assert sha(ROOT/name) == pin, name
assert json.loads((W/'authorization.json').read_text())['CurrentOwnerApproved'] is False
for label in ('ab_suite_01', 'root_tests_02', 'ab_spec_02', 'ab_contracts_02', 'consistency_02', 'whitespace_02',
              'session_build_01', 'authorization_negative_01', 'unchanged_verification_01', 'guard_readonly_01'):
    assert json.loads((W/(label + '_exit.json')).read_text())['exitCode'] == 0, label
for name in ('s3i_canonical.ACD', 'capacity_review.ACD', 'retention_control.ACD'):
    assert sha(W/name).upper() == ACD, name

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


for path in sorted(W.rglob('*')):
    relative = path.relative_to(W)
    if not path.is_file() or relative.parts[0] == 'session' and relative.parts[1] in ('bin', 'obj'):
        continue
    if path.suffix.upper() in ('.ACD', '.BAK'):
        continue
    if path.suffix.upper() == '.L5X':
        pack(path, OUT/'Preparation'/(relative.as_posix() + '.gz'))
    else:
        copy(path, OUT/'Preparation'/relative)
for path in sorted(L.iterdir()):
    if path.is_file():
        copy(path, OUT/'Fix'/path.name)
for name in bindings['changed']:
    pack(ROOT/name, OUT/'Source'/(name + '.gz'))

artifacts = [dict(path=p.relative_to(OUT).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(OUT.rglob('*')) if p.is_file()]
assert not any(a['path'].upper().endswith(('.ACD', '.BAK')) for a in artifacts)
report = NAME + '.md'
sdk = W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
manifest = dict(
    schema='fraktal.ab.s3i-canonical-lifetime-retry-preparation', schemaVersion=1, date='2026-10-24',
    timeZone='America/Mexico_City', sealedUtc=datetime.now(timezone.utc).isoformat(),
    report=report, reportSha256=sha(EV/report), currentNativeSessionApproved=False, controllerAccess='read-only guard',
    controllerOperations=0, plcChanged=False, preparedAcdSha256=ACD,
    sourceSha256='0f3a5f6dd762bed3819404025daf6d5703511807b440c4988eacf5e494ec72c3',
    retryOf='AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24', sourceBindings=len(bindings['sha256']),
    changedBindings=len(bindings['changed']), abTests=2191, rootTests=74, focusedTests=22, negativeCases=6,
    sessionExecutableSha256=sha(sdk), sessionAssemblySha256=sha(sdk.with_suffix('.dll')),
    sessionSourceSha256=sha(W/'session/Program.cs'), stageAccepted=False, calendarLifetimeAccepted=False,
    retentionAccepted=False, credentialFilesArchived=False, nativeAcdFilesArchived=False,
    priorSeals=seals, priorArtifactCount=total, artifacts=artifacts, artifactCount=len(artifacts),
    totalBytes=sum(a['bytes'] for a in artifacts))
(OUT/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(sealed=True, artifacts=len(artifacts), bytes=manifest['totalBytes'],
                      predecessors=len(seals), predecessorArtifacts=total)))
