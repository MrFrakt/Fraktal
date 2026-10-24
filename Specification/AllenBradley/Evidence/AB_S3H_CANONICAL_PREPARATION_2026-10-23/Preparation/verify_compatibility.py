"""Preserve every accepted prior image and sealed generic snapshot."""
from pathlib import Path
import ast,gzip,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_s3g_native_checks as native
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s3h_demo as demo
PRIOR=Path('C:/work/fraktal-ab-s3g-20261023/prepare_feb76c7a0968442293ee0d20b812eb17')
tree=ast.parse((PRIOR/'verify_s3g_compatibility.py').read_text())
script=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/compatibility.py').read_text()
tree=ast.parse(script)
stages=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stages' for t in n.targets)))
stages.append(('s3f','B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3','fraktal_ab_genealogy_s3f_demo','idle_equivalence_01',2617))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
checks=[]
for stage,pin,declaration,filename,count in stages:
    output=P/('compatibility_'+stage+'.L5X');assert not output.exists()
    with (P/('compatibility_'+stage+'.log')).open('xb') as log:
        subprocess.run([sys.executable,str(T/'fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(output),'--declaration',declaration],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
    assert sha(output)==pin,(stage,sha(output))
    name='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23' if stage=='s3f' else f'AB_{stage.upper()}_CANONICAL_RUNTIME_'+('2026-10-21' if stage in ('s2','s3a','s3b') else '2026-10-22')
    path=ROOT/f'Specification/AllenBradley/Evidence/{name}/Runtime/{filename}.json.gz'
    evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair'];replay=reader.snapshot(pair['capture'])
    assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==count
    checks.append(dict(stage=stage,outputSha256=pin,paths=count,sealedPairSha256=sha(path)))
output=P/'compatibility_s3g_bench.L5X';assert not output.exists();native.generate(Path('C:/work/echo38_5580_seed.L5X'),output)
assert sha(output)=='50E0F8977D975A14C5CD6F86A42AE56B8D4F995CD6A2AA52E071C252104DAE91'
path=ROOT/'Specification/AllenBradley/Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23/Runtime/idle_equivalence_01.json.gz'
evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair'];replay=reader.snapshot(pair['capture'])
assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==3672
checks.append(dict(stage='s3g',outputSha256=sha(output),paths=3672,sealedPairSha256=sha(path)))
current=P/'s3h_regenerated_01.L5X';assert not current.exists();gen.generate(demo.application(),Path('C:/work/echo38_5580_seed.L5X'),current)
assert sha(current)==sha(P/'s3h_candidate_03.L5X')
report=dict(passed=True,priorStages=checks,currentSourceSha256=sha(current),unchangedGenericReader=True)
with (P/'compatibility_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,priorStages=len(checks),currentSourceSha256=sha(current))))
