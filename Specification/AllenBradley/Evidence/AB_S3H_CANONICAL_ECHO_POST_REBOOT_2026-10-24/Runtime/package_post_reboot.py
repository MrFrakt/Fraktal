"""Append a new evidence record; verify every predecessor without modifying it."""
from pathlib import Path
import datetime
import hashlib
import json

R = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
AB = ROOT / 'Specification/AllenBradley'
E = AB / 'Evidence'
NAME = 'AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24'
D = E / NAME
REPORT = E / (NAME + '.md')
PREVIOUS = Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P = PREVIOUS.parent / 'diagnostic_0b74f072e0d74c7c97531e07dec70898'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

v = json.loads((R / 'post_reboot_observation_01.json').read_text())
assert not v['controllerReady'] and not v['diagnosticApprovalConsumed']
assert v['controllerChangingOperations'] == 0
for label in ('echo_inspect_post_windows_reboot_01', 'emulator_dump_metadata_01',
              'emulator_stack_01', 'capture_post_reboot_01', 'record_post_reboot_01',
              'root_post_reboot_01', 'spec_post_reboot_01', 'contracts_post_reboot_01',
              'consistency_post_reboot_01', 'whitespace_post_reboot_01'):
    assert json.loads((R / (label + '_exit.json')).read_text())['exitCode'] == 0, label
bindings = json.loads((PREVIOUS / 'initial_source_verification.json').read_text())
for relative, expected in bindings['sha256'].items():
    assert sha(ROOT / relative) == expected, relative
for relative, expected in bindings['diagnosticBindings'].items():
    assert sha(P / relative) == expected, relative
assert sha(P / 's3h_canonical.ACD').upper() == bindings['preparedAcdSha256']

prior = []
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(prefix in path.parent.name for prefix in (
        'AB_S0_CANONICAL', 'AB_S0_SUPPLEMENTARY', 'AB_S1_CANONICAL', 'AB_S2_CANONICAL',
        'AB_S3A_CANONICAL', 'AB_S3B_CANONICAL', 'AB_S3C_CANONICAL', 'AB_S3D_CANONICAL',
        'AB_S3E_CANONICAL', 'AB_S3F_CANONICAL', 'AB_S3G_CANONICAL', 'AB_S3H_CANONICAL')):
        continue
    manifest = json.loads(path.read_text())
    for row in manifest['artifacts']:
        artifact = path.parent / row['path']
        assert artifact.stat().st_size == row['bytes'] and sha(artifact) == row['sha256'].lower(), artifact
    if manifest.get('report'):
        assert sha(E / manifest['report']) == manifest['reportSha256'].lower()
    prior.append(dict(name=path.parent.name, artifacts=len(manifest['artifacts']), manifestSha256=sha(path)))
assert len(prior) == 37 and sum(row['artifacts'] for row in prior) == 8576
assert not D.exists()
D.mkdir()

def copy(path, name):
    target = D / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as out:
        out.write(path.read_bytes())

for path in sorted(R.iterdir()):
    if not path.is_file() or path.name.startswith(('package_post_reboot_01', 'post_reboot_seal_')):
        continue
    assert path.suffix.lower() not in ('.acd', '.dmp', '.dat', '.sqlite', '.bin')
    assert 'credential' not in path.name.lower()
    copy(path, 'Runtime/' + path.name)
copy(PREVIOUS / 'initial_source_verification.json', 'Reference/initial_source_verification.json')
for filename in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
                 'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
                 'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md', 'AB_FROZEN_CONTRACTS_V2.json'):
    copy(AB / filename, 'Target/' + filename)
rows = [dict(path=path.relative_to(D).as_posix(), bytes=path.stat().st_size, sha256=sha(path))
        for path in sorted(D.rglob('*')) if path.is_file()]
manifest = dict(schema='fraktal.ab.s3h-echo-post-reboot-evidence', schemaVersion=1,
                date='2026-10-24', timeZone='America/Mexico_City',
                sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                report=REPORT.name, reportSha256=sha(REPORT),
                status='host-reboot-completed-emulator-startup-crash-persists-diagnostics-not-started',
                controllerReady=False, diagnosticApprovalConsumed=False,
                diagnosticApprovalQuestion=v['diagnosticApprovalQuestion'],
                controllerChangingOperations=0, nativeMemoryDumpArchived=False,
                credentialFilesArchived=False, controllerDefinitionsModified=False,
                startupException=v['startupException'], underlyingCauseConfirmed=False,
                priorSeals=prior, artifacts=rows, artifactCount=len(rows),
                totalBytes=sum(row['bytes'] for row in rows))
with (D / 'manifest.json').open('x', encoding='utf-8') as out:
    json.dump(manifest, out, indent=2)
for row in rows:
    assert sha(D / row['path']) == row['sha256']
result = dict(passed=True, artifactCount=len(rows), reportSha256=sha(REPORT),
              manifestSha256=sha(D / 'manifest.json'),
              predecessorRecords=len(prior), predecessorArtifacts=8576,
              currentRecords=len(prior) + 1, currentArtifacts=8576 + len(rows),
              controllerReady=False, diagnosticApprovalConsumed=False)
with (R / 'post_reboot_seal_01.json').open('x') as out:
    json.dump(result, out, indent=2)
print(json.dumps(result))
