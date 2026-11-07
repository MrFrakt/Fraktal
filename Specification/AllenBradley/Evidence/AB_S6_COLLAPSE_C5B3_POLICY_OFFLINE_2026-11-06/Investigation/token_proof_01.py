from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
from fraktal_ab_st_format import tokens
import fraktal_ab_fixture_observation as fixture
import fraktal_ab_press_s6_collapse_echo38 as profile
E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06'
old=Path('C:/work/fraktal-ab-c5b2-control-20261106/prepare_01/press.L5X');new=W/'press_01.L5X'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
pins=json.loads((E/'Preparation/artifact_bindings.json').read_bytes())['artifacts'];assert any(Path(r['path'])==old and r['sha256']==sha(old) for r in pins)
def routines(p):
 root=ET.parse(p).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for r in owner.findall('./Routines/Routine'):
   out[owner.get('Name')+'/'+r.get('Name')]=(r.get('Type'),list(tokens('\n'.join(n.text or '' for n in r.iter() if n.tag in ('Line','Text')))) if r.get('Type')=='ST' else ET.tostring(r))
 return root,out
root,a=routines(old);_,b=routines(new);assert set(a)==set(b)
type_name=next(t.get('DataType') for t in root.iter('Tag') if t.get('Name')==fixture.tag(profile.application()))
prior={m.get('Name') for t in root.iter('DataType') if t.get('Name')==type_name for m in t.findall('./Members/Member')}
body=list(b['FRK_PressProgram/FRK_Press_CopyFixtureObservation'][1]);deltas=[]
expected={x['surface']+'.'+x['member']:x for x in json.loads((W/'policy_fact_accounting_01.json').read_bytes())['facts']}
for surface,m,name,source in fixture.facts(profile.application()):
 if name in prior:continue
 held=expected.pop(surface+'.'+m.name);assert source==held['source'] and m.dimension==held['dimension']
 if m.dimension:
  code=f'FOR FRK_Press_FixtureIndex := 0 TO {m.dimension-1} DO FRK_Press_FixtureObservation.{name}[FRK_Press_FixtureIndex] := {source}.{m.name}[FRK_Press_FixtureIndex]; END_FOR;'
 else:code=f'FRK_Press_FixtureObservation.{name} := {source}.{m.name};'
 wanted=list(tokens(code));hits=[i for i in range(len(body)-len(wanted)+1) if body[i:i+len(wanted)]==wanted];assert len(hits)==1,(surface,m.name)
 at=hits[0];del body[at:at+len(wanted)];deltas.append(dict(surface=surface,member=m.name,dimension=m.dimension,source=source,tokens=wanted))
assert not expected and len(deltas)==27
key='FRK_PressProgram/FRK_Press_CopyFixtureObservation';assert ('ST',body)==a[key]
assert all(a[k]==b[k] for k in a if k!=key)
result=dict(passed=True,referenceCommit='f68314e3b2d46d4497be5e204818ae5df5bd26f0',referenceSha256=sha(old),sourceSha256=sha(new),unchangedRoutines=len(a)-1,addedFacts=deltas,tokenCounts=dict(before=sum(len(v[1]) for v in a.values() if v[0]=='ST'),after=sum(len(v[1]) for v in b.values() if v[0]=='ST')),controllerAccess=False)
with (W/'token_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,unchangedRoutines=len(a)-1,addedFacts=len(deltas),tokenCounts=result['tokenCounts'])))
