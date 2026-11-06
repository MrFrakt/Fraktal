"""Final C4c qualification against the frozen primary sources. Read-only/offline."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');I=Path(__file__).resolve().parent;G=I.parent/'Gates'
W=Path('C:/work/fraktal-ab-s6-host-20261104/prepare');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
C=Path('C:/work/fraktal-ab-c4-control-20261106');PY=sys.executable
for unused in range(1800):
    if (W/'prepare_candidate_17.json').exists():break
    time.sleep(1)
else:raise TimeoutError('source17 preparation did not finish')
assert json.loads((W/'prepare_candidate_17.json').read_bytes())['passed']
exits={}
def run(label,*args):
    exits[label]=subprocess.run([PY,str(I/'run_logged_at.py'),label,str(R),*map(str,args)],cwd=R).returncode
run('token_proof_17_r3',PY,I/'c4c_proof_04.py',G/'token_proof_17_r3.json',
    W/'s6_collapse_13.L5X',W/'s6_collapse_17.L5X',W/'press_collapse_13.L5X',W/'press_collapse_17.L5X')
for target,prefix in (('EchoController',''),('PhysicalController',''),('EchoController','press_')):
    image=W/('press_collapse_17.L5X' if prefix else 's6_collapse_17.L5X')
    run(f'initialization_{prefix}{target}_17_r3',PY,I/'audit_storage_readback_01.py',image,
        W/f'{prefix}{target}_readback_17.L5X',G/f'initialization_{prefix}{target}_17_r3.json')
mirrors=[]
for declaration,prefix,baseline in (('fraktal_ab_genealogy_s6_collapse_demo','s6','fraktal_ab_genealogy_s6_host_demo'),
                                    ('fraktal_ab_press_s6_collapse_echo38','press','fraktal_ab_press_canonical_echo38')):
    mirror=C/f'{prefix}_final_mirror_17_r3.L5X'
    run(f'mirror_{prefix}_17_r3',PY,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',mirror,'--declaration',declaration)
    # The seed is the explicitly pinned Studio export, never a controller upload.
    original=W/f'{prefix}_collapse_17.L5X'
    mirrors.append(dict(declaration=declaration,identical=mirror.read_bytes()==original.read_bytes(),
                        sha256=hashlib.sha256(original.read_bytes()).hexdigest().upper()))
    run(f'schema_{prefix}_17_r3',PY,T/'fraktal_ab_schema_identity.py','--declaration',declaration,
        '--seed','C:/work/echo38_5580_seed.L5X','--check',T/'fixtures/schema_identity'/f'{baseline}.json.gz',
        '--declared',T/'fixtures/schema_identity'/f'{declaration}.declared.json')
source=json.loads((G/'full_ab_source_bindings_before_05.json').read_bytes())['sources']
assert all(hashlib.sha256((T/n).read_bytes()).hexdigest().upper()==v for n,v in source.items())
gateway={}
for relative in subprocess.check_output(['git','ls-files','FraktalCore/HMI/gateway'],cwd=R,text=True).splitlines():
    path=R/relative
    if path.is_file():
        assert subprocess.check_output(['git','show','c1c55a6a5:'+relative],cwd=R)==path.read_bytes(),relative
        gateway[relative]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (G/'gateway_unchanged_17_r3.json').open('x',encoding='utf-8') as out:
    json.dump(dict(baselineCommit='c1c55a6a5',testsBound=44,sources=gateway),out,indent=2)
result=dict(passed=all(v==0 for v in exits.values()) and all(row['identical'] for row in mirrors),
            exits=exits,mirrors=mirrors,primarySourcesMatchFrozenSuite=True,sourceFiles=len(source),controllerAccess=False)
with (G/'qualification_17_r3.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)
