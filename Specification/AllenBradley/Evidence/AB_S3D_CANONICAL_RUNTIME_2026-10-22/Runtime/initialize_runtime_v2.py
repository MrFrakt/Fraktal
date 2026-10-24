from pathlib import Path
import datetime, hashlib, json, shutil, gzip
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
W=Path('C:/work/fraktal-ab-s3d-20261022/prepare_f1995b2579fe4f7a9d15d02dd8ed53e9');R=Path(__file__).parent
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3D_CANONICAL_PREPARATION_2026-10-22'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text())
assert sha(E/'manifest.json')=='1491d2605b3cbb682c65857a4dd39e3693ad8c42f4eb17ceb648a561ab1cf935'
assert sha(E.with_suffix('.md'))==m['reportSha256']=='31d232ad1c6393fb1e535e17ef0e5f611f7fd1f1e077770a558b76b84cff0c04'
for a in m['artifacts']:
 p=E/a['path'];assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'],a['path']
 if a['path'].startswith('Preparation/'):
  working=W/a['path'][len('Preparation/'):]
  if working.suffix=='.gz' and not working.exists():
   assert working.with_suffix('').read_bytes()==gzip.decompress(p.read_bytes()),str(working)
  else:
   assert working.is_file() and sha(working)==a['sha256'],str(working)
bindings=json.loads((W/'source_bindings_01.json').read_text())
for p,h in bindings['sha256'].items():assert sha(ROOT/p)==h,p
pin=(W/'canonical.sha256').read_text().strip()
assert sha(W/'s3d_canonical.ACD').upper()==sha(W/'capacity_review.ACD').upper()==pin
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
for p in ('authorization.json','deploy_attempt.json','backup.sha256','echo_before_s3d.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (W/p).exists(),p
report=dict(passed=True,preparationArtifacts=len(m['artifacts']),sourceBindings=len(bindings['sha256']),preparedAcdSha256=pin,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'initial_artifact_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
a=json.loads((W/'authorization.template.json').read_text())
a.update(CurrentOwnerApproved=True,ManualNormalizationAuthorized=True,OwnerResponse='Approve this guarded S3d session',QuestionId='call_71ac973170694f23b7a5f4248c9b1c99:0',RecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),RuntimeDirectory=R.as_posix())
for p in (W/'authorization.json',R/'authorization.json'):
 with p.open('x') as f:json.dump(a,f,indent=2)
print(json.dumps(report))
