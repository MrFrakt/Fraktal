from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent;D=W/'session_10'
E=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
NAME='AB_S5_GATEWAY_IDLE_CONNECTION_SEAL_CORRECTION_2026-10-30';P=E/NAME
assert not P.exists() and not (E/(NAME+'.md')).exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
source=D/'source_bindings.json';value=json.loads(source.read_bytes())
assert value['sha256'].pop(str(D/'authorization.json'))
assert not (D/'deploy_attempt.json').exists() and not (D/'session_started.json').exists()
for name,pin in value['sha256'].items():assert sha(name)==pin,name
source.rename(D/'source_bindings_superseded_01.json')
with source.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
P.mkdir();artifacts={}
for path in [source,D/'source_bindings_superseded_01.json',Path(__file__)]:
    target=P/path.name;shutil.copyfile(path,target);artifacts[target.name]=sha(target)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as stream:json.dump(artifacts,stream,indent=2)
report=f'''# S5 idle-connection preparation: authorization seal correction

Before any session/controller access, review of the
[preparation](AB_S5_GATEWAY_IDLE_CONNECTION_PREPARATION_2026-10-30.md)
found that its generic JSON inventory also froze the intentionally unarmed
authorization.json. Arming standing O3 would therefore fail the source gate.
The standard protocol freezes authorization.template.json; the actual grant
is recorded after sealing and checked by the existing authorization validator.

Only the actual authorization.json pin is removed. The superseded binding is
preserved under a new filename and in this payload; the original preparation
payload is unchanged. Every other source/package/gate/image pin is rechecked.
The SDK, runner, validation rules, command vectors and rollback guards are
unchanged. No controller operation occurred. This corrected source_bindings.json
is the binding used by session_10. The preparation's other scopes/proofs apply.

Corrected binding SHA-256: {sha(source)}.
Payload manifest SHA-256: {sha(P/'payload_hashes.json')}.
'''
with (E/(NAME+'.md')).open('x',encoding='utf-8') as stream:stream.write(report)
print(json.dumps(dict(passed=True,controllerAccess=False,inputs=len(value['sha256']),bindingSha256=sha(source))))
