from pathlib import Path
import datetime,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
R=P.parent/'runtime_fd53835fe9684f598bdd829da6d29c8d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((R/'source_verification_failed_01.json').read_text())['sha256']
current={n:sha(ROOT/n) for n in before}
changes={n:dict(previous=pin,current=current[n]) for n,pin in before.items() if pin!=current[n]}
assert {Path(n).name for n in changes}=={'fraktal_ab_canonical_equivalence.py','test_fraktal_ab_canonical_publication.py'}
assert len(current)==159
sys.path.insert(0,str(T));import fraktal_ab_generate as gen;import fraktal_ab_genealogy_s3h_demo as demo
output=P/'s3h_regenerated_paced_01.L5X';assert not output.exists()
gen.generate(demo.application(),Path('C:/work/echo38_5580_seed.L5X'),output)
assert sha(output)==sha(P/'s3h_candidate_03.L5X')=='e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315'
for n in ('s3h_canonical.ACD','capacity_review.ACD'):
 assert sha(P/n).upper()=='C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC'
result=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=current,
 sourceBindings=159,changedFromFailedSession=changes,addedSources=[],generatedSourceUnchanged=True,
 preparedAcdUnchanged=True,readOnlyObserverOnly=True,waitSeconds=.001,connections=4,
 maximumOutstandingPerConnection=1,attemptLimit=100,secondsLimit=5)
with (P/'source_bindings_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('sha256','changedFromFailedSession')}))
