"""C5a offline qualification of exact prepared sources and preserved defaults."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';P=W/'prepare_03';PY=sys.executable
sys.path.insert(0,str(T));import fraktal_ab_schema_identity as si
exits={};mirrors=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(label,*args):
 code=subprocess.run([PY,str(W/'run_logged_02.py'),label,str(R),*map(str,args)],cwd=R).returncode
 exits[label]=code
 if code:raise RuntimeError(label+' failed')
for i in range(3600):
 if (W/'prepare_c5a_04.json').exists():break
 time.sleep(1)
else:raise TimeoutError('preparation has not completed')
prep=json.loads((W/'prepare_c5a_04.json').read_bytes());assert prep['passed'],prep.get('error')
run('token_proof_04',PY,W/'token_proof_c5a_03.py',W/'token_proof_04.json')
audit=R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06/Investigation/audit_storage_readback_01.py'
for name,decl,baseline in [('genealogy','fraktal_ab_genealogy_s6_collapse_demo','fraktal_ab_genealogy_s6_host_demo'),('press','fraktal_ab_press_s6_collapse_echo38','fraktal_ab_press_canonical_echo38')]:
 source=P/(name+'.L5X')
 for target in ('EchoController','PhysicalController'):
  back=(W/'prepare_02' if name=='genealogy' else W/'prepare_04' if target=='PhysicalController' else P)/(name+'_'+target+'_readback.L5X')
  run('initialization_'+name+'_'+target+'_04',PY,audit,source,back,W/('initialization_'+name+'_'+target+'_04.json'))
 mirror=P/(name+'_mirror_04.L5X')
 run('mirror_'+name+'_04',PY,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',mirror,'--declaration',decl)
 mirrors.append(dict(profile=name,sha256=sha(source),identical=sha(source)==sha(mirror)))
 before=si.read(T/'fixtures/schema_identity'/(baseline+'.json.gz'))
 declarations=[si.Declared(**d) for d in json.loads((T/'fixtures/schema_identity'/(decl+'.declared.json')).read_bytes())]
 result=si.compare(before,si.surface(source),declarations)
 with (W/('schema_'+name+'_04.json')).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 assert result['passed'],{k:result[k] for k in ('uncovered','unusedDeclarations')}
result=dict(passed=all(row['identical'] for row in mirrors),exits=exits,mirrors=mirrors,controllerAccess=False)
with (W/'qualification_04.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)
