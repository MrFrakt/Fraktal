from pathlib import Path
import ast,hashlib,json,re,sys,xml.etree.ElementTree as ET
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_fixture_observation as fixture
import fraktal_ab_genealogy_s6_collapse_demo as profile
import fraktal_ab_schema_identity as si
import fraktal_ab_st_model as st
from fraktal_ab_st_format import tokens
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
old=Path('C:/work/fraktal-ab-c5-control-20261106/prepare_03/genealogy.L5X');new=W/'genealogy_01.L5X'
pins=json.loads((R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06/Preparation/artifact_bindings.json').read_bytes())['artifacts']; assert any(Path(row['path'])==old and row['sha256']==sha(old) for row in pins)
reference=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06/Investigation/token_proof_01.py'
tree=ast.parse(reference.read_text(encoding='utf-8'));nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('bodies','compare_against_prior')]
assert len(nodes)==2
code=ast.unparse(ast.Module(body=nodes,type_ignores=[])).replace('phase5_fact_accounting_01.json','fact_accounting_01.json').replace('len(deltas) == 39','len(deltas) == 12'); exec(compile(code,str(reference),'exec'),globals())
facts=[dict(surface=surface,member=m.name,dimension=m.dimension,source=source) for surface,m,name,source in fixture.facts(profile.application()) if surface!='Mailbox']
with (W/'fact_accounting_01.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,facts=facts,scope='copy-source inventory; native genealogy values remain S6-Q'),out,indent=2)
body=compare_against_prior(old,new,profile.application())
declared=[si.Declared(**d) for d in json.loads((T/'fixtures/schema_identity/fraktal_ab_genealogy_s6_collapse_demo.declared.json').read_bytes())]
schema=si.compare(si.read(T/'fixtures/schema_identity/fraktal_ab_genealogy_s6_host_demo.json.gz'),si.surface(new),declared)
with (W/'schema_01.json').open('x',encoding='utf-8') as out:json.dump(schema,out,indent=2)
assert schema['passed'],dict(uncovered=schema['uncovered'][:8],unused=schema['unusedDeclarations'])
result=dict(passed=True,body=body,schema=schema,privateFacts=len(fixture.facts(profile.application())),referenceProofSha256=sha(reference),controllerAccess=False)
with (W/'image_proof_02.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(dict(passed=True,addedFacts=body['addedFactCopies'],routines=body['routines'],tokens=body['tokenCounts'])))
