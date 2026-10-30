"""Preserve the unqualified experiment and restore the qualified desktop reader."""
from pathlib import Path
import hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
C=R/'Specification/AllenBradley/Evidence/AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28'
manifest=json.loads((C/'artifact_manifest.json').read_bytes())
restored={}
for relative in ['packages/fraktal_opcua_client/lib/src/cip_read_plan.dart','test/cip_coalesced_read_test.dart']:
    current=H/relative;previous=W/'profile_04/Sources'/relative
    assert current.read_bytes()==previous.read_bytes(),'concurrent edit: '+relative
    kept=W/'UnqualifiedAdaptiveExperiment'/relative;kept.parent.mkdir(parents=True,exist_ok=True)
    with kept.open('xb') as f:f.write(current.read_bytes())
    path='FraktalCore/HMI/'+relative;original=C/'Current'/path
    expected=manifest['sourceSha256'][path]
    assert hashlib.sha256(original.read_bytes()).hexdigest()==expected
    current.write_bytes(original.read_bytes());restored[relative]=expected
with (W/'adaptive_experiment_reverted_01.json').open('x') as f:
    json.dump(dict(reverted=True,reason='Failed consecutive profile gate; native body service cost not isolated',
        restoredSha256=restored,experimentalProfileLabels=['profile_01','profile_02','profile_03','profile_04'],
        nativeUse=False,controllerChanges=0),f,indent=2)
print(json.dumps(dict(reverted=True,files=len(restored),controllerChanges=0)))
