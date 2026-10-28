"""Seal the failed typed-login retry and successful completion of its rollback."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
R = Path(__file__).parent
E = ROOT / 'Specification/AllenBradley/Evidence'
NAME = 'AB_S3K_CANONICAL_RUNTIME_2026-10-25'
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
assert load(R / 'session_result.json')['passed']
assert load(R / 'pair_replay_01.json')['captures'] == 91
assert load(R / 'native_acceptance_01.json')['passed']
assert len(load(R / 'baseline_regressions.json')['rows']) == 31
assert load(R / 'final_checks.json')['passed']
for label in ('post_runtime_root_tests_01', 'post_runtime_spec_01', 'post_runtime_contracts_01',
              'post_runtime_consistency_01', 'post_runtime_whitespace_01', 'backup_audit', 'deploy_audit',
              'deploy_readback', 'deploy_access', 'restore_genealogy_audit', 'restore_access',
              'baseline_regressions', 'preflight_final', 'baseline_timing'):
    assert load(R / (label + '_exit.json'))['exitCode'] == 0, label
previous = E / 'AB_S3K_CANONICAL_LOGIN_RETRY_PREPARATION_2026-10-25/manifest.json'
old = load(previous)
names = {row['name'] for row in old['priorSeals']} | {previous.parent.name}
seals, total = [], 0
for name in sorted(names):
    path = E / name / 'manifest.json'
    held = load(path)
    for row in held['artifacts']:
        raw = (path.parent / row['path']).read_bytes()
        assert sha(raw) == row['sha256'].lower() and len(raw) == row['bytes'], (name, row['path'])
        if row.get('expandedSha256'):
            assert sha(gzip.decompress(raw)) == row['expandedSha256'].lower()
    if held.get('reportSha256'):
        assert sha((E / held['report']).read_bytes()) == held['reportSha256'].lower()
    seals.append(dict(name=name, manifestSha256=sha(path.read_bytes()), artifacts=len(held['artifacts'])))
    total += len(held['artifacts'])
assert len(seals) == 62
save(R / 'prior_seals_runtime_01.json', dict(passed=True, records=len(seals), artifacts=total, rows=seals))
bindings = load(R / 'source_bindings.json')['sha256']
for name, expected in bindings.items():
    source = Path(name)
    if source.is_relative_to(ROOT):
        frozen = R / 'NativeSource' / source.relative_to(ROOT)
        frozen = frozen.with_name(frozen.name + '.gz')
        assert sha(gzip.decompress(frozen.read_bytes())).upper() == expected.upper()
        if source.parent == ROOT / 'FraktalCore/PLC/Allen-Bradley/tools':
            assert sha(source.read_bytes()).upper() == expected.upper()
artifacts = []


def archive(source, relative, compress=False):
    raw = source.read_bytes()
    data = gzip.compress(raw, mtime=0) if compress else raw
    name = relative + ('.gz' if compress else '')
    write(OUT / name, data)
    row = dict(path=name, bytes=len(data), sha256=sha(data))
    if compress:
        row['expandedSha256'] = sha(raw)
    elif source.is_relative_to(R / 'NativeSource'):
        row['expandedSha256'] = sha(gzip.decompress(raw))
    artifacts.append(row)


for source in sorted(R.rglob('*')):
    if not source.is_file() or any(part in ('bin', 'obj', '__pycache__') for part in source.relative_to(R).parts):
        continue
    if source.suffix.lower() not in ('.py', '.json', '.jsonl', '.gz', '.log', '.l5x', '.cs', '.csproj', '.txt', '.sha256'):
        continue
    assert 'credential' not in source.name.lower()
    archive(source, 'Runtime/' + source.relative_to(R).as_posix(), source.suffix.lower() == '.l5x')
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md', 'AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md', 'AB_FROZEN_CONTRACTS_V2.json'):
    archive(ROOT / 'Specification/AllenBradley' / name, 'CurrentDocs/' + name)
report = E / (NAME + '.md')
manifest = dict(schema='fraktal.ab.s3k-runtime-acceptance', schemaVersion=1,
                date='2026-10-25', timeZone='America/Mexico_City',
                sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), report=report.name,
                reportSha256=sha(report.read_bytes()), nativeAccepted=True, typedLoginCompleted=True,
                mainCandidateRows=31, candidateCheckRows=55, typedInterleavingCheckRows=14, accessCases=2, configurationCases=8, typedAckAndWipeRows=12,
                pairedCapturesReplayed=91, genealogyRestored=True, originalHostDocumentsRestored=5,
                baselineChecks=31, finalChecksPassed=True, authorizationConsumed=True,
                currentControllerChangesAuthorized=False,
                downloadedAcdSha256='AA4239C636647527CC37F3B3F18206821FBEE108D3315C5087DC0DCD1653BBDF',
                sourceSha256='B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A',
                abTests=2295, rootTests=74, nativeSourceBindings=load(R / 'native_source_verified_01.json')['frozenRepoSources'],
                measurements=load(R / 'measurements_01.json'), nativeAssertions=load(R / 'native_acceptance_01.json'), timing=load(R / 'runtime_summary_01.json')['timing'],
                priorSeals=seals, priorArtifacts=total, artifactCount=len(artifacts), artifacts=artifacts,
                credentialFilesArchived=False, nativeAcdFilesArchived=False, committed=False, pushed=False)
save(OUT / 'manifest.json', manifest)
for row in artifacts:
    raw = (OUT / row['path']).read_bytes()
    assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
    if row.get('expandedSha256'):
        assert sha(gzip.decompress(raw)) == row['expandedSha256']
result = dict(passed=True, manifest=(OUT / 'manifest.json').as_posix(),
              manifestSha256=sha((OUT / 'manifest.json').read_bytes()), artifacts=len(artifacts),
              priorSeals=len(seals), priorArtifacts=total, candidateAccepted=True, genealogyRestored=True)
save(R / 'sealed_runtime_01.json', result)
print(json.dumps(result), flush=True)
