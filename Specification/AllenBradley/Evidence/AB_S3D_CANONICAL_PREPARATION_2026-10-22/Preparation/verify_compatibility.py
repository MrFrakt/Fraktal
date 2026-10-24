from pathlib import Path
import gzip,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_reader as reader
checks=[]
for stage,expected in [('s2','9398A04EE4ABECF74C006CF0BD2AB516D8EA3AE5607D37041AB8AE0CD0FE725E'),('s3a','83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095'),('s3b','72B9FAA0ECA228FEBAD8D19B5628A09DC06B87E739AAB3473C63E1E891CEF589'),('s3c','E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2')]:
 actual=hashlib.sha256((W/('compatibility_'+stage+'.L5X')).read_bytes()).hexdigest().upper()
 assert actual==expected,(stage,actual)
 checks.append(dict(kind='unchangedStageOutput',stage=stage,sha256=actual))
for stage,filename,count in [('S2','equivalence_01',46),('S3A','idle_equivalence_02',94),('S3B','idle_equivalence_01',304),('S3C','idle_equivalence_01',647)]:
 path=ROOT/('Specification/AllenBradley/Evidence/AB_'+stage+'_CANONICAL_RUNTIME_'+('2026-10-22' if stage=='S3C' else '2026-10-21')+'/Runtime')/(filename+'.json.gz')
 raw=path.read_bytes();evidence=json.loads(gzip.decompress(raw));pair=evidence['pair']
 replay=reader.snapshot(pair['capture'])
 assert replay==pair['canonical'],stage+' snapshot changed'
 assert evidence['passed'] and replay['nodeCount']==count
 checks.append(dict(kind='sealedPairReplay',stage=stage,paths=count,sourceSha256=hashlib.sha256(raw).hexdigest()))
with (W/'compatibility_verification_01.json').open('x') as stream:json.dump(dict(passed=True,checks=checks),stream,indent=2)
print(json.dumps(dict(passed=True,checks=len(checks))))
