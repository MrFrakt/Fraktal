from pathlib import Path
import datetime, hashlib, json, shutil, gzip
ROOT=Path('C:/Users/SoftIndVM/Fraktal')
W=Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea');R=Path(__file__).parent
E=ROOT/'Specification/AllenBradley/Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'manifest.json').read_text())
assert sha(E/'manifest.json')=='b2fa5b8cadf14a39dcaa324c251e9c2497a527d2a0c4d573c17d97ad68803621'
assert sha(E.with_suffix('.md'))==m['reportSha256']=='86936ea92f20aa1ea78a5d5be574b44ad2078001709e90e4ed2c466b8f2e7e33'
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
assert sha(W/'s3e_canonical.ACD').upper()==sha(W/'capacity_review.ACD').upper()==pin
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
for p in ('authorization.json','deploy_attempt.json','backup.sha256','echo_before_s3e.ACD','canonical_downloaded.L5X','genealogy_restored.L5X'):assert not (W/p).exists(),p
report=dict(passed=True,preparationArtifacts=len(m['artifacts']),sourceBindings=len(bindings['sha256']),preparedAcdSha256=pin,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'initial_artifact_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
a=json.loads((W/'authorization.template.json').read_text())
a.update(CurrentOwnerApproved=True,ManualNormalizationAuthorized=True,AccessVectorsAuthorized=True,OwnerResponse='Approve this guarded S3e session',QuestionId='call_b9ffdb91b99f4a60a0318f472d0a6254:0',RecordedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),RuntimeDirectory=R.as_posix())
for p in (W/'authorization.json',R/'authorization.json'):
 with p.open('x') as f:json.dump(a,f,indent=2)
print(json.dumps(report))
