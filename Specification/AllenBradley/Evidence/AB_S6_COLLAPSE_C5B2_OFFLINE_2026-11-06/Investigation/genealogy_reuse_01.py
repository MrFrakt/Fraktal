from pathlib import Path
import hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T));import fraktal_ab_schema_identity as si
W=Path(__file__).parent;P=W/'prepare_01';OLD=Path('C:/work/fraktal-ab-c5-control-20261106');E=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
source=P/'genealogy.L5X';assert sha(source)==sha(OLD/'prepare_03/genealogy.L5X')
entries=json.loads((E/'Preparation/artifact_bindings.json').read_bytes())['artifacts']
paths=[OLD/'prepare_03/genealogy.L5X',OLD/'prepare_03/genealogy.ACD',*(OLD/'prepare_02'/('genealogy_'+target+'_readback.L5X') for target in ('EchoController','PhysicalController'))]
rows=[]
for path in paths:
 found=[row for row in entries if Path(row['path'])==path];assert len(found)==1 and sha(path)==found[0]['sha256'],str(path)
 rows.append(dict(path=str(path),sha256=sha(path)))
capacity=json.loads((OLD/'prepare_03/genealogy_capacity.json').read_bytes());assert capacity['VerifiedFit'] and capacity['CanonicalSha256']==sha(OLD/'prepare_03/genealogy.ACD')
before=si.read(T/'fixtures/schema_identity/fraktal_ab_genealogy_s6_host_demo.json.gz');declared=[si.Declared(**d) for d in json.loads((T/'fixtures/schema_identity/fraktal_ab_genealogy_s6_collapse_demo.declared.json').read_bytes())]
check=si.compare(before,si.surface(source),declared);assert check['passed'],check
with (W/'schema_genealogy_01.json').open('x',encoding='utf-8') as f:json.dump(check,f,indent=2)
result=dict(passed=True,sourceByteIdentical=True,priorEvidence=str(E.relative_to(R)),buildTargets=['EchoController','PhysicalController'],readbackAccessDefaultChecks='hash-bound C5a qualification reused; no changed genealogy bytes',artifacts=rows,capacity=capacity,controllerAccess=False)
with (W/'genealogy_reuse_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=True,sourceSha256=sha(source),artifacts=len(rows))))
