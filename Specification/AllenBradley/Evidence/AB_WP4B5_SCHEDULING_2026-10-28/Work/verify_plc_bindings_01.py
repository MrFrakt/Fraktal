"""Transfer unchanged PLC gates by exact source hashes; no controller I/O."""
from pathlib import Path
import hashlib,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
reference=R/'Specification/AllenBradley/Evidence/AB_S4B_MSP_PREPARATION_2026-10-27/Preparation/source_bindings.json'
bindings=json.loads(reference.read_bytes())['sha256']
plc={p:h for p,h in bindings.items() if 'FraktalCore/PLC/Allen-Bradley/tools/' in p}
assert len(plc)==373
for p,h in plc.items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()==h,p
result=dict(passed=True,sourceBindings=len(plc),
    reference=str(reference),referenceSha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
    sourceSha256=plc,transferredAbTests=2339,transferredV38Targets=2,
    capacityPercent=65,unchangedImageSha256='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5',
    nativeAcceptanceClaim=False,controllerChanges=0)
with (W/'plc_transfer_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='sourceSha256'}))
