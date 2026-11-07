from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-c5b2-control-20261106/prepare_01/press.L5X');new=W/'press_01.L5X'
def fields(path):
 root=ET.parse(path).getroot();kind=next(t.get('DataType') for t in root.iter('Tag') if t.get('Name')=='FRK_Press_FixtureObservation')
 return next(t for t in root.iter('DataType') if t.get('Name')==kind).findall('./Members/Member')
a,b=fields(old),fields(new);assert len(a)==75 and len(b)==102
assert [ET.tostring(x) for x in a]==[ET.tostring(x) for x in b[:len(a)]]
added=json.loads((W/'policy_fact_accounting_01.json').read_bytes())['facts']
assert {x.get('Name') for x in b[len(a):]}=={r['surface']+'_'+r['member'] for r in added}
result=dict(passed=True,oldMembers=len(a),newMembers=len(b),prefixByteIdentical=True,appendedMembers=len(added),sourceSha256=hashlib.sha256(new.read_bytes()).hexdigest().upper(),controllerAccess=False)
with (W/'layout_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
