from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_generate as gen
import fraktal_ab_press_s6_shelving_echo38 as profile
import fraktal_ab_schema_identity as si
from fraktal_ab_st_format import tokens
from test_fraktal_ab_schema_identity import DECLARATIONS
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
old=Path('C:/work/fraktal-ab-c5b3-control-20261106/prepare_01/press.L5X');new=W/'shelving_01.L5X'
E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06'
bound=json.loads((E/'Preparation/artifact_bindings.json').read_bytes())['artifacts']
assert any(Path(row['path'])==old and row['sha256']==sha(old) for row in bound)
def routines(path):
 root=ET.parse(path).getroot();out={}
 for owner in [*root.iter('AddOnInstructionDefinition'),*root.iter('Program')]:
  for routine in owner.findall('./Routines/Routine'):
   key=owner.get('Name')+'/'+routine.get('Name')
   out[key]=(routine.get('Type'),list(tokens('\n'.join(n.text or '' for n in routine.iter() if n.tag in ('Line','Text')))) if routine.get('Type')=='ST' else ET.tostring(routine))
 return out
a,b=routines(old),routines(new);assert set(a)==set(b)
changed=[key for key in a if a[key]!=b[key]]
assert changed==['FRK_PressProgram/FRK_Press_ScanHealth'],changed
key=changed[0];before=list(a[key][1]);after=list(b[key][1])
index=gen.HEALTH_EVENTS.index('CONTROLLER_METRICS_UNAVAILABLE')
expected=list(tokens(f'{gen.system_health_tag(profile.application())}.Bad[{index}] := 1;'))
at=[i for i in range(len(after)-len(expected)+1) if after[i:i+len(expected)]==expected]
assert len(at)==1;del after[at[0]:at[0]+len(expected)];assert after==before
surface=si.surface(new);same=si.compare(si.surface(old),surface);assert same['passed'],same
baseline=si.read(T/'fixtures/schema_identity/fraktal_ab_press_canonical_echo38.json.gz')
declarations=json.loads((T/'fixtures/schema_identity'/f'{DECLARATIONS["fraktal_ab_press_s6_shelving_echo38"]}.declared.json').read_bytes())
schema=si.compare(baseline,surface,[si.Declared(**row) for row in declarations]);assert schema['passed'],schema
result=dict(passed=True,parentCommit='8f87f0ab5f4e1c9fb007a23e1b0f51847d2ae3a0',referenceSha256=sha(old),sourceSha256=sha(new),changedRoutines=changed,unchangedRoutines=len(a)-1,onlyAddedTokens=expected,tokenCounts=dict(before=sum(len(v[1]) for v in a.values() if v[0]=='ST'),after=sum(len(v[1]) for v in b.values() if v[0]=='ST')),surfaceVsBase=same,schemaVsPrecollapse=schema,baseUnchanged=True,controllerAccess=False)
with (W/'image_proof_02.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(dict(passed=True,unchangedRoutines=len(a)-1,addedTokens=len(expected),surfaceDifferences=len(same['covered']))))
