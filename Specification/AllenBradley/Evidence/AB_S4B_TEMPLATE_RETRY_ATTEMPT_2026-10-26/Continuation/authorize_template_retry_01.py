from pathlib import Path
import datetime
import gzip
import hashlib
import importlib.util
import json

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
D = Path('C:/work/fraktal-ab-s4b-20261025/retry_template_01')
E = ROOT / 'Specification/AllenBradley/Evidence'
P = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path = P / 'manifest.json'
assert digest(manifest_path) == '2ddcea618d2a1f5b12f457707b2bd93115236c1808031d488a65d5fc0faeb6c2'
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
spec = importlib.util.spec_from_file_location('qualification_retry', D / 'qualification_session_v2.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
approval = json.loads((D / 'authorization.template.json').read_bytes())
approval.update(CurrentOwnerApproved=True, OwnerInstruction='Approve guarded S4b Template retry',
                ApprovalQuestion='call_378e7db52cb749e49ad59c696606376a:0',
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
