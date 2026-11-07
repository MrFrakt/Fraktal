from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
W=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal')
E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06'
old=Path('C:/work/fraktal-ab-c5b3-control-20261106/prepare_01/press.L5X')
press=W/'press_01.L5X'
shelving=W/'shelving_01.L5X'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
pins=json.loads((E/'Preparation/artifact_bindings.json').read_bytes())['artifacts']
assert any(Path(r['path'])==old and r['sha256']==sha(old) for r in pins)
def fields(path):
 root=ET.parse(path).getroot();kind=next(t.get('DataType') for t in root.iter('Tag') if t.get('Name')=='FRK_Press_FixtureObservation')
 return kind,next(t for t in root.iter('DataType') if t.get('Name')==kind).findall('./Members/Member')
old_kind,a=fields(old)
press_kind,b=fields(press)
shelving_kind,c=fields(shelving)
assert old_kind=='FRK_T_PressFixtureV2_AF73C3A5' and press_kind==shelving_kind=='FRK_T_PressFixtureV2_2A276D94'
assert len(a)==102 and len(b)==len(c)==141
assert [ET.tostring(x) for x in b]==[ET.tostring(x) for x in c]
by_b={x.get('Name'):ET.tostring(x) for x in b}
assert [by_b[x.get('Name')] for x in a]==[ET.tostring(x) for x in a]
added=json.loads((W/'phase5_fact_accounting_01.json').read_bytes())['facts']
prior_names=[x.get('Name') for x in a]
new_names=[r['observedName'] for r in added]
assert [x.get('Name') for x in b if x.get('Name') not in set(new_names)]==prior_names
assert {x.get('Name') for x in b}-set(prior_names)==set(new_names)
result=dict(
 passed=True,
 oldUdtName=old_kind,
 newUdtName=press_kind,
 oldMembers=len(a),
 newMembers=len(b),
 priorMembersByteIdenticalAndOrderPreserved=True,
 shelvingLayoutIdenticalToPress=True,
 appendedMembers=len(added),
 referenceSha256=sha(old),
 pressSha256=sha(press),
 shelvingSha256=sha(shelving),
 controllerAccess=False,
)
with (W/'layout_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
