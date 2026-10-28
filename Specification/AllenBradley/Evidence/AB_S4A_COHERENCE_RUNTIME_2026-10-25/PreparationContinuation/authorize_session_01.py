"""Record the owner's current, exact-image S4a session approval."""
from pathlib import Path
import datetime,gzip,hashlib,json,sys
W=Path(__file__).parent;D=W.parent/'session_01'
R=Path('C:/Users/SoftIndVM/Fraktal')
P=R/'Specification/AllenBradley/Evidence/AB_S4A_COHERENCE_PREPARATION_2026-10-25/manifest.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (D/'authorization.json').exists() and not (D/'session_started.json').exists()
m=json.loads(P.read_bytes())
assert sha(P)=='78637cff0f3473fd536770616bf622722a9c3de8dab90b74ddaa20b9e5bdb9cd'
assert sha(P.parent.parent/m['report'])==m['reportSha256']
for row in m['artifacts']:
    path=P.parent/row['path'];assert sha(path)==row['sha256']
b=json.loads((D/'source_bindings.json').read_bytes())
assert all(sha(Path(name)).upper()==value for name,value in b['sha256'].items())
sys.path.insert(0,str(D))
import qualification_session as session
approval=json.loads((D/'authorization.template.json').read_bytes())
approval.update(CurrentOwnerApproved=True,OwnerInstruction='Approve guarded S4a qualification',
    ApprovalQuestion='call_0aa6207bba714a73bb1e80ee242d1981:0',
    RecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    PreparationManifestSha256=sha(P))
approval.update({flag:True for flag in session.FLAGS})
session.authorize(approval)
with (D/'authorization.json').open('x',encoding='utf-8') as stream:json.dump(approval,stream,indent=2);stream.write('\n')
print(json.dumps(dict(recorded=True,serial=approval['Serial'],acdSha256=approval['CanonicalSha256'],
    checkedSourceBindings=len(b['sha256']),preparationArtifacts=len(m['artifacts']),
    faultClearAuthorized=False,clockChangeAuthorized=False,powerOperationsAuthorized=False)))
