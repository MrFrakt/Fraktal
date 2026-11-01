import sys
sys.path.pop(0)
from pathlib import Path
import datetime,hashlib,json,shutil
W=Path('C:/work/fraktal-ab-s5-20261029');D=W/'session_19'
sys.path.insert(0,str(D))
from s5_session import FLAGS,authorize
from artifact_readiness import validate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
assert not (D/'session_started.json').exists()
binding=json.loads((D/'source_bindings.json').read_bytes())
original=dict(binding['sha256'])
authKey=str(D/'authorization.json')
assert authKey in original
auth=json.loads((D/'authorization.json').read_bytes())
assert auth['CurrentOwnerApproved'] is False
assert all(sha(path)==pin for path,pin in original.items())
auth.update(CurrentOwnerApproved=True,
    OwnerInstruction='Standing owner O3, AGENTS.md 3a and canonical publication plan 6.3: guarded dedicated Echo 601FC87B sessions require no per-session approval. Qualify the timing-layout/detail-refresh correction, unchanged command vectors, read-only detail stability and owner C12, then pinned genealogy rollback.',
    Scope='Unchanged S5 write vectors; read-only timing/history stability observations; fresh owner C12; mandatory pinned genealogy/five-document restore/31 baseline cases. No clears, clocks, power or vendor-state edits.',
    ApprovedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
auth.update({flag:True for flag in FLAGS})
authorize(auth)
with (D/'authorization_granted_01.json').open('x',encoding='utf-8') as f:json.dump(auth,f,indent=2)
authBefore=sha(D/'authorization.json');bindingBefore=sha(D/'source_bindings.json')
(D/'authorization.json').rename(D/'authorization_preparation_unarmed_01.json')
shutil.copyfile(D/'authorization_granted_01.json',D/'authorization.json')
# Authorization has its own strict validator and immutable session-start hash.
# Match the preceding accepted preparation: template remains source-bound;
# actual authorization is armed only after the preparation has been sealed.
binding['sha256'].pop(authKey)
assert binding['sha256']=={k:v for k,v in original.items() if k!=authKey}
(D/'source_bindings.json').rename(D/'source_bindings_preparation_unarmed_01.json')
with (D/'source_bindings.json').open('x',encoding='utf-8') as f:json.dump(binding,f,indent=2)
assert all(sha(path)==pin for path,pin in binding['sha256'].items())
assert validate(D)['passed']
record=dict(passed=True,controllerAccess=False,authorizationSeparatedOnly=True,
    beforeBindingSha256=bindingBefore,afterBindingSha256=sha(D/'source_bindings.json'),
    beforeAuthorizationSha256=authBefore,armedAuthorizationSha256=sha(D/'authorization.json'),
    removedBindingPath=authKey,unchangedOtherBindings=len(binding['sha256']),
    reason='Preparation included the unarmed approval file among frozen source inputs. Preserve it and separate only that actual approval, matching session18. authorize() and session_started approval hashing remain required. No other binding/guard changes.',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D/'preparation_authorization_separation.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
E=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
name='AB_S5_GATEWAY_DETAIL_REFRESH_PREPARATION_CLOSURE_2026-10-31';P=E/name
assert not P.exists() and not (E/(name+'.md')).exists();P.mkdir();hashes={}
for source in [W/'arm_session19.py',D/'preparation_authorization_separation.json',D/'source_bindings.json',D/'authorization_granted_01.json']:
    shutil.copyfile(source,P/source.name);hashes[source.name]=sha(P/source.name)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2,sort_keys=True)
with (E/(name+'.md')).open('x',encoding='utf-8') as f:f.write(f'''# S5 detail-refresh preparation: authorization separation

The [preparation](AB_S5_GATEWAY_DETAIL_REFRESH_PREPARATION_2026-10-31.md)
accidentally bound the unarmed authorization as a frozen source input. No
controller access or session start occurred. Its original payload and runtime
files are preserved. This closure separates only the actual authorization,
matching session18: the template and all other {len(binding['sha256'])} bindings
remain unchanged. The strict exact-image/scope authorize() validator and the
session-start approval hash remain required. No controller guard is relaxed.

Standing O3 arms this exact existing image/session. No new write vector is
added. Every freshness, proof, retry and rollback rule is unchanged. The
attached final binding and approval hashes govern the session. All original
gate results remain applicable. Payload hash: {sha(P/'payload_hashes.json')}.
''')
print(json.dumps(record))
