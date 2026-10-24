from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
prepared=json.loads((W/'source_bindings_01.json').read_text())['sha256'];assert len(prepared)==142
paths=set(prepared)|{'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_part_execute.py'}
sources={n:sha((ROOT/n).read_bytes()) for n in sorted(paths)}
changes={n:dict(before=pin,after=sources[n]) for n,pin in prepared.items() if sources[n]!=pin}
assert {Path(n).name for n in changes}=={'fraktal_ab_s2_equivalence.py','fraktal_ab_paired_fragments.py','test_fraktal_ab_paired_fragments.py','fraktal_ab_part_execute.py'},changes
output=R/'generation_closing_01.L5X';assert not output.exists()
with (R/'generation_closing_01.log').open('xb') as f:
 subprocess.run([sys.executable,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(output),'--declaration','fraktal_ab_genealogy_s3f_demo'],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
assert sha(output.read_bytes()).upper()=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_canonical_reader import snapshot
p=R/'generic_capture_01.json.gz';s=R/'generic_snapshot_01.json.gz'
decoded=snapshot(json.loads(gzip.decompress(p.read_bytes())))
assert decoded==json.loads(gzip.decompress(s.read_bytes())) and decoded['nodeCount']==2617 and decoded['moduleCount']==7
for n,pin in sources.items():assert sha((ROOT/n).read_bytes())==pin,n
report=dict(passed=True,controllerAccess=False,readOnly=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceBindings=len(sources),observerChanges=changes,addedFixtureTest=sorted(paths-set(prepared)),generatedSourceSha256=sha(output.read_bytes()),generatedPlcSourceUnchanged=True,genericReplayPaths=2617,sha256=sources)
with (R/'source_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='sha256'}))
