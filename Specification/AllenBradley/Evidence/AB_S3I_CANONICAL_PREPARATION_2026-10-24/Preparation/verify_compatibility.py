"""Every accepted prior image, the prior S3h source with the frame off, and the frame candidate."""
from pathlib import Path
import ast,gzip,hashlib,json,os,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_s3g_native_checks as native
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s3h_demo as demo
from dataclasses import replace
SEED=Path('C:/work/echo38_5580_seed.L5X')
script=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/compatibility.py').read_text()
tree=ast.parse(script)
stages=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stages' for t in n.targets)))
stages.append(('s3f','B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3','fraktal_ab_genealogy_s3f_demo','idle_equivalence_01',2617))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
checks=[]
for stage,pin,declaration,filename,count in stages:
    output=P/('compatibility_'+stage+'.L5X');assert not output.exists()
    with (P/('compatibility_'+stage+'.log')).open('xb') as log:
        subprocess.run([sys.executable,str(T/'fraktal_ab_generate.py'),str(SEED),str(output),'--declaration',declaration],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
    assert sha(output)==pin,(stage,sha(output))
    name='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23' if stage=='s3f' else f'AB_{stage.upper()}_CANONICAL_RUNTIME_'+('2026-10-21' if stage in ('s2','s3a','s3b') else '2026-10-22')
    path=ROOT/f'Specification/AllenBradley/Evidence/{name}/Runtime/{filename}.json.gz'
    evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair'];replay=reader.snapshot(pair['capture'])
    assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==count
    checks.append(dict(stage=stage,outputSha256=pin,paths=count,sealedPairSha256=sha(path)))
output=P/'compatibility_s3g_bench.L5X';assert not output.exists();native.generate(SEED,output)
assert sha(output)=='50E0F8977D975A14C5CD6F86A42AE56B8D4F995CD6A2AA52E071C252104DAE91'
path=ROOT/'Specification/AllenBradley/Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23/Runtime/idle_equivalence_01.json.gz'
evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair'];replay=reader.snapshot(pair['capture'])
assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==3672
checks.append(dict(stage='s3g',outputSha256=sha(output),paths=3672,sealedPairSha256=sha(path)))
off=P/'compatibility_s3h_frame_off.L5X';assert not off.exists()
gen.generate(replace(demo.application(),canonical_observation_period_ms=0),SEED,off)
assert sha(off)=='E83B9A2CD9593718026528CCDBD83A1EAD6C8A52948FC6616006DAFFB0567315',sha(off)
current=P/'s3h_frame_regenerated_01.L5X';assert not current.exists();gen.generate(demo.application(),SEED,current)
assert sha(current)=='BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2'=='BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2'
report=dict(passed=True,priorStages=checks,s3hFrameOffSha256=sha(off),currentSourceSha256=sha(current),unchangedGenericReader=True)
with (P/'compatibility_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,priorStages=len(checks),frameOff=sha(off),currentSourceSha256=sha(current))))
