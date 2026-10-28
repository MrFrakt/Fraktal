"""Record the owner's current exact-image approval after immutable verification."""
from pathlib import Path
import datetime
import gzip
import hashlib
import importlib.util
import json
import sys

R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
S=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence'
P=E/'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
pin='5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26'
assert sha(P/'manifest.json')==pin
m=load(P/'manifest.json')
assert sha(E/m['report'])==m['reportSha256']
assert sha(S/'source_bindings.json')==m['sourceBindingsSha256']
for row in m['artifacts']:
    p=P/row['path']
    assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],str(p)
    if row.get('expandedSha256'):
        assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==row['expandedSha256']
for row in m['priorSeals']:
    assert sha(E/row['name']/'manifest.json')==row['manifestSha256']
b=load(S/'source_bindings.json')
assert b['gatesPassed']
for name,expected in b['sha256'].items():
    assert sha(name).upper()==expected.upper(),'bound input changed: '+name
for name in ('authorization.json','session_started.json','deploy_attempt.json','echo_before_s4b.ACD'):
    assert not (S/name).exists(),name
assert load(W/'echo_guard_approved_01_exit.json')['exitCode']==0
sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('approved_cold_session',S/'qualification_session_v2.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
approval=load(S/'authorization.template.json')
approval.update(CurrentOwnerApproved=True,
    OwnerInstruction='Approve guarded S4b cold-start/desktop session',
    ApprovalQuestion='call_297cd0f6497b4493909e0f524643c7c9:0',
    ApprovedPreparationManifestSha256=pin,
    ApprovedPreparation='Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md',
    AuthorizationRecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    ReadOnlyGuardLogSha256=sha(W/'echo_guard_approved_01.log'),
    TaskCounterClearAuthorized=False)
for flag in module.FLAGS:
    approval[flag]=True
module.authorize(approval)
with (S/'authorization.json').open('x',encoding='utf-8',newline='') as f:
    json.dump(approval,f,indent=2,ensure_ascii=False)
    f.write('\n')
print(json.dumps(dict(currentOwnerApproved=True,serial=approval['Serial'],
    canonicalSha256=module.PIN,sourceBindingsVerified=len(b['sha256']),
    preparationArtifactsVerified=len(m['artifacts']),priorSealsVerified=len(m['priorSeals']),
    controllerChanges=0,authorizationSha256=sha(S/'authorization.json'))))
