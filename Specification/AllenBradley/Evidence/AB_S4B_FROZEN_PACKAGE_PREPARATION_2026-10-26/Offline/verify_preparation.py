from pathlib import Path
import gzip,hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
P=R/'Specification/AllenBradley/Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'manifest.json').read_bytes())
assert manifest['reportSha256']==sha(P.parent/manifest['report'])
assert manifest['sourceBindingsSha256']==sha(D/'source_bindings.json')
for row in manifest['artifacts']:
    path=P/row['path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes'],row['path']
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==row['expandedSha256']
bindings=json.loads((D/'source_bindings.json').read_bytes())
for path,pin in bindings['sha256'].items():assert sha(Path(path)).upper()==pin,path
assert not (D/'authorization.json').exists() and not (D/'session_started.json').exists()
assert not (D/'deploy_attempt.json').exists() and not (D/'echo_before_s4b.ACD').exists()
result=dict(passed=True,artifacts=len(manifest['artifacts']),sourceBindings=len(bindings['sha256']),priorSeals=len(manifest['priorSeals']),
    nativeSessionAuthorized=False,controllerChanges=0,manifestSha256=sha(P/'manifest.json'))
with (W/'verified_preparation_01.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
