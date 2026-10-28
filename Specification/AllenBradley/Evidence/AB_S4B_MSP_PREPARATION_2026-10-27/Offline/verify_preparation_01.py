"""Independently verify sealed artifacts and all live runtime bindings, read-only."""
from pathlib import Path
import gzip,hashlib,json
W=Path(__file__).parent;S=W.parent/'session_01'
E=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
O=E/'AB_S4B_MSP_PREPARATION_2026-10-27'
load=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(O/'manifest.json');receipt=load(W/'sealed_preparation_01.json')
assert sha(O/'manifest.json')==receipt['manifestSha256']
assert sha(E/q['report'])==q['reportSha256']
assert sha(S/'source_bindings.json')==q['sourceBindingsSha256']
for row in q['artifacts']:
    raw=(O/row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256']
b=load(S/'source_bindings.json')
for path,expected in b['sha256'].items():assert sha(path).upper()==expected,path
assert q['readOnlyBodyMsp'] and q['separateCompletedCounters'] and not q['intraPacketOrderAssumed']
assert not q['nativeSessionAuthorized'] and not q['nativeAccepted'] and q['controllerChanges']==0
assert not (S/'authorization.json').exists() and not (S/'session_started.json').exists()
for row in q['priorSeals']:assert sha(E/row['name']/'manifest.json')==row['manifestSha256']
print(json.dumps(dict(passed=True,artifacts=len(q['artifacts']),sourceBindings=len(b['sha256']),
    priorSeals=len(q['priorSeals']),nativeAuthorized=False,controllerAccess=False)))
