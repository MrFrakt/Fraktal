"""Bind observer-only changes and prove the deployed PLC source is unchanged."""
from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-20261022/prepare_3816927132f14d4998876bc62e22f342')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
before=json.loads((W/'source_bindings_01.json').read_text())
changed={n:dict(before=pin,after=sha((ROOT/n).read_bytes())) for n,pin in before['sha256'].items() if sha((ROOT/n).read_bytes())!=pin}
expected={'fraktal_ab_s2_equivalence.py','fraktal_ab_paired_reads.py','fraktal_ab_s3f_fixture_execute.py','test_fraktal_ab_s3f_fixture.py'}
assert {Path(n).name for n in changed}==expected,changed
paths=set(before['sha256'])|{'FraktalCore/PLC/Allen-Bradley/tools/'+n for n in ('fraktal_ab_paired_fragments.py','test_fraktal_ab_paired_fragments.py')}
current={n:sha((ROOT/n).read_bytes()) for n in sorted(paths)}
output=R/'generation_closing_01.L5X';assert not output.exists()
with (R/'generation_closing_01.log').open('xb') as f:
 subprocess.run([sys.executable,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_generate.py'),
  'C:/work/echo38_5580_seed.L5X',str(output),'--declaration','fraktal_ab_genealogy_s3f_demo'],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
assert sha(output.read_bytes()).upper()=='7BBAD050BFD82D3C76DD84E82644AC1AAE5A772125CC02AAC7DD93FE1F621C28'
for n,pin in current.items():assert sha((ROOT/n).read_bytes())==pin,n
generic=[]
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_canonical_reader import snapshot
for suffix in ('01','02'):
 p=R/f'generic_capture_{suffix}.json.gz';s=R/f'generic_snapshot_{suffix}.json.gz'
 decoded=snapshot(json.loads(gzip.decompress(p.read_bytes())))
 assert decoded==json.loads(gzip.decompress(s.read_bytes())) and decoded['nodeCount']==2617 and decoded['moduleCount']==7
 generic.append(dict(capture=p.name,captureSha256=sha(p.read_bytes()),snapshot=s.name,snapshotSha256=sha(s.read_bytes()),paths=2617))
report=dict(passed=True,controllerAccess=False,readOnly=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 preparedBindings=138,unchangedPreparedBindings=134,changedObserverBindings=changed,currentBindings=140,
 addedObserverFiles=sorted(paths-set(before['sha256'])),generatedPlcSourceUnchanged=True,generatedSourceSha256=sha(output.read_bytes()),
 genericReplays=generic,sha256=current)
with (R/'source_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('sha256','changedObserverBindings','genericReplays')}))
