"""Regenerate prior stages, replay sealed frames, bind both S3g variants."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_s3g_native_checks as native
from importlib.machinery import SourceFileLoader
prior_script=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/compatibility.py').read_text()
# Reuse only the recorded immutable stage pins; do not execute the old script.
import ast
tree=ast.parse(prior_script)
stages=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stages' for t in n.targets)))
stages.append(('s3f','B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3','fraktal_ab_genealogy_s3f_demo','idle_equivalence_01',2617))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
checks=[]
for stage,pin,declaration,filename,count in stages:
    output=P/('full_compatibility_'+stage+'.L5X');assert not output.exists()
    with (P/('full_compatibility_'+stage+'.log')).open('xb') as log:
        subprocess.run([sys.executable,str(T/'fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(output),'--declaration',declaration],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
    assert sha(output)==pin,(stage,sha(output))
    name='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23' if stage=='s3f' else f'AB_{stage.upper()}_CANONICAL_RUNTIME_'+('2026-10-21' if stage in ('s2','s3a','s3b') else '2026-10-22')
    path=ROOT/f'Specification/AllenBradley/Evidence/{name}/Runtime/{filename}.json.gz'
    evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair']
    replay=reader.snapshot(pair['capture'])
    assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==count,(stage,replay['nodeCount'])
    checks.append(dict(stage=stage,outputSha256=pin,paths=count,sealedPairSha256=sha(path)))
new=P/'s3g_native_regeneration_01.L5X';assert not new.exists()
native.generate(Path('C:/work/echo38_5580_seed.L5X'),new)
assert sha(new)==sha(P/'s3g_native_candidate_01.L5X')
report=dict(passed=True,priorStages=checks,currentSourceSha256=sha(new))
with (P/'full_compatibility_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,priorStages=len(checks),currentSourceSha256=sha(new))))
