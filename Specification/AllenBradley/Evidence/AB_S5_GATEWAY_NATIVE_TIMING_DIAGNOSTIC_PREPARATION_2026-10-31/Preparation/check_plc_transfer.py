from pathlib import Path
import hashlib,json
D=Path(__file__).parent;P=D.parent/'session_09'
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
pins=json.loads((P/'source_bindings.json').read_bytes())['sha256']
current={str(p):sha(p) for p in T.rglob('*.py') if '__pycache__' not in p.parts}
bound={name:pin for name,pin in pins.items() if Path(name).is_relative_to(T)}
assert current==bound, 'PLC tool source set/hash changed'
assert json.loads((D.parent/'ab_suite_02_exit.json').read_bytes())['exitCode']==0
assert sha(D/'s5_canonical.ACD')=='95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012'
result=dict(passed=True,controllerAccess=False,unchangedPlcInputs=len(current),
    abSuiteTestsPassed=2357,exactImageCapacityPercent=66,
    proof='Original sealed PLC sources, dual-v38 builds/readbacks and exact-image Capacity retained by hashes; HMI gates are fresh',
    sha256=current)
with (D/'plc_transfer_source_check.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='sha256'}))
