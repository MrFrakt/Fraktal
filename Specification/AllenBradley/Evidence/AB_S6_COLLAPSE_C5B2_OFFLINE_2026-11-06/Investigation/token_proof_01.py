from pathlib import Path
import ast,hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T));import fraktal_ab_schema_identity as si
from fraktal_ab_st_format import tokens
import fraktal_ab_press_s6_collapse_echo38 as profile
import fraktal_ab_fixture_observation as fixture
W=Path(__file__).parent;new=W/'prepare_01/press.L5X';old=W/'reference_press_01.L5X';app=profile.application()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def routines(p):
 root=ET.parse(p).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for r in owner.findall('./Routines/Routine'):
   key=owner.get('Name')+'/'+r.get('Name');out[key]=(r.get('Type'),tokens('\n'.join(n.text or '' for n in r.iter() if n.tag in ('Line','Text'))) if r.get('Type')=='ST' else ET.tostring(r))
 return out
refsource=(W/'reference/FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_press_s6_collapse_echo38.py').read_text(encoding='utf-8');node=next(n for n in ast.parse(refsource).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FIXTURE' for t in n.targets));prior={(surface,name) for surface,names in ast.literal_eval(node.value) for name in names}
a,b=routines(old),routines(new);assert set(a)==set(b)
key='FRK_PressProgram/FRK_Press_CopyFixtureObservation';body=list(b[key][1]);deltas=[]
for surface,m,name,source in fixture.facts(app):
 if (surface,m.name) in prior:continue
 expected_source=(app.records[int(surface[3:])].name+'Tag' if surface.startswith('Cfg') else {'SetState':'FRK_Press_ConfigSetState','Persist':'FRK_Press_ConfigPersist'}[surface]);assert source==expected_source
 if m.dimension:
  assert surface=='SetState' and m.name=='AuditSequence' and m.dimension==16
  code=f'FOR FRK_Press_FixtureIndex := 0 TO 15 DO FRK_Press_FixtureObservation.{name}[FRK_Press_FixtureIndex] := {source}.{m.name}[FRK_Press_FixtureIndex]; END_FOR;'
 else:code=f'FRK_Press_FixtureObservation.{name} := {source}.{m.name};'
 wanted=list(tokens(code));hits=[i for i in range(len(body)-len(wanted)+1) if body[i:i+len(wanted)]==wanted];assert len(hits)==1,(surface,m.name)
 at=hits[0];del body[at:at+len(wanted)];deltas.append(dict(surface=surface,member=m.name,source=source,elements=m.dimension or 1,tokens=wanted))
assert len(deltas)==35 and len(fixture.facts(app))==75
assert ('ST',tuple(body))==a[key], 'unexpected fixture token delta'
assert all(a[k]==b[k] for k in a if k!=key),'unexpected executable delta'
result=dict(passed=True,referenceCommit='ca786c6c9e549a9ff60287cba4c290afca9ac289',referenceSha256=sha(old),sourceSha256=sha(new),unchangedRoutines=len(a)-1,addedFacts=deltas,controllerAccess=False)
with (W/'token_proof_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,unchangedRoutines=len(a)-1,addedFacts=len(deltas))))
