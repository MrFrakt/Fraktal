"""Fresh older-stage outputs and immutable runtime bytes with today's reader."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(TOOLS))
import fraktal_ab_canonical_reader as reader
stages=[('s2','9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E','fraktal_ab_genealogy_canonical_demo','equivalence_01',46),
 ('s3a','83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095','fraktal_ab_genealogy_s3a_demo','idle_equivalence_02',94),
 ('s3b','72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589','fraktal_ab_genealogy_s3b_demo','idle_equivalence_01',304),
 ('s3c','E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2','fraktal_ab_genealogy_s3c_demo','idle_equivalence_01',647),
 ('s3d','03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962','fraktal_ab_genealogy_s3d_demo','idle_equivalence_01',2125),
 ('s3e','3BFFCEADB98EC7B7B7AA05550202CC187C736A8C2B22C75B7B7D158BE4F5AD87','fraktal_ab_genealogy_s3e_demo','idle_equivalence_01',2154)]
checks=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
for stage,expected,declaration,filename,count in stages:
 output=W/('compatibility_'+stage+'.L5X')
 assert not output.exists()
 with (W/('compatibility_'+stage+'_generation.log')).open('xb') as f:
  subprocess.run([sys.executable,str(TOOLS/'fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(output),'--declaration',declaration],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
 assert sha(output)==expected,(stage,sha(output))
 checks.append(dict(kind='unchangedStageOutput',stage=stage,sha256=expected))
 date='2026-10-21' if stage in ('s2','s3a','s3b') else '2026-10-22'
 path=ROOT/f'Specification/AllenBradley/Evidence/AB_{stage.upper()}_CANONICAL_RUNTIME_{date}/Runtime/{filename}.json.gz'
 evidence=json.loads(gzip.decompress(path.read_bytes()));pair=evidence['pair']
 replay=reader.snapshot(pair['capture'])
 assert replay==pair['canonical'] and evidence['passed'] and replay['nodeCount']==count
 checks.append(dict(kind='sealedPairReplay',stage=stage,paths=count,sourceSha256=sha(path)))
output=W/'generation_recheck.L5X'
assert not output.exists()
with (W/'generation_recheck.log').open('xb') as f:
 subprocess.run([sys.executable,str(TOOLS/'fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(output),'--declaration','fraktal_ab_genealogy_s3f_demo'],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
assert sha(output)==sha(W/'genealogy_s3f_revision_01.L5X'),'current source differs from compiled candidate'
checks.append(dict(kind='compiledCandidateRegeneration',sha256=sha(output)))
with (W/'compatibility_verification_01.json').open('x') as f:json.dump(dict(passed=True,checks=checks),f,indent=2)
print(json.dumps(dict(passed=True,checks=len(checks))))
