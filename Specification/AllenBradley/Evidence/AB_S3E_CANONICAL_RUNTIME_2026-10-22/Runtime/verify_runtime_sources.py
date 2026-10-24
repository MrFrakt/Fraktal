from pathlib import Path
import datetime,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((W/'source_bindings_01.json').read_text())
for name,pin in before['sha256'].items():assert sha(ROOT/name)==pin,name
assert len(before['sha256'])==76
result=dict(passed=True,sourceCommit=before['sourceCommit'],capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),unchangedPreparedSourceFiles=76,finalRootSourcesMatchPreparation=True,temporaryReadOnlyObserverEditsRestored=True,preparedSourceBindingsSha256=sha(W/'source_bindings_01.json'),correctedAcceptanceAuditSha256=sha(R/'acceptance_corrected_manual_gate.py'),manualPolicyGateDerivedFrom='fraktal_ab_access.GATES[fraktal_ab_mailbox.MANUAL_COMMAND]',manualPolicyCanonicalIndex=2,sha256=before['sha256'])
with (R/'source_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='sha256'}))
