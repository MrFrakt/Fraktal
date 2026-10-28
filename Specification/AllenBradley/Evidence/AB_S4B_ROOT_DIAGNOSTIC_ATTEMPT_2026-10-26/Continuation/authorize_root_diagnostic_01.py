from pathlib import Path
import datetime
import gzip
import hashlib
import importlib.util
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
D = Path('C:/work/fraktal-ab-s4b-20261025/retry_root_diagnostic_01')
E = R / 'Specification/AllenBradley/Evidence'
P = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path = P / 'manifest.json'
assert digest(manifest_path) == '225a80bc2d5840504de9f9fee4b2185184f86755254dd40030d7064f5dd32384'
manifest = json.loads(manifest_path.read_bytes())
assert digest(E / manifest['report']) == manifest['reportSha256']
assert digest(D / 'source_bindings.json') == manifest['sourceBindingsSha256']
for row in manifest['artifacts']:
    path = P / row['path']
    assert digest(path) == row['sha256'] and path.stat().st_size == row['bytes'], row['path']
    if row.get('expandedSha256'):
        assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == row['expandedSha256']
bindings = json.loads((D / 'source_bindings.json').read_bytes())
assert bindings['gatesPassed'] is True
for path, expected in bindings['sha256'].items():
    assert digest(Path(path)).upper() == expected.upper(), path
for name in ('authorization.json', 'session_started.json', 'deploy_attempt.json', 'echo_before_s4b.ACD'):
    assert not (D / name).exists(), name
spec = importlib.util.spec_from_file_location('qualification_root_diagnostic', D / 'qualification_session_v2.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
approval = json.loads((D / 'authorization.template.json').read_bytes())
approval.update(CurrentOwnerApproved=True, OwnerInstruction='Approve guarded S4b root diagnostic session',
                ApprovalQuestion='call_0c97c2f8c5c84620bbb108165c7177cd:0',
                ApprovalRecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ApprovedPreparationManifestSha256=digest(manifest_path))
for flag in module.FLAGS:
    approval[flag] = True
module.authorize(approval)
assert digest(D / 's4b_read_view.ACD').upper() == module.PIN
assert digest(D / 's4b_read_view.L5X').upper() == module.SOURCE
with (D / 'authorization.json').open('x', encoding='utf-8') as stream:
    json.dump(approval, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(authorized=True, sourceBindingsVerified=len(bindings['sha256']),
                     artifactsVerified=len(manifest['artifacts']), controllerChanges=0,
                     ownerInstruction=approval['OwnerInstruction'])))
