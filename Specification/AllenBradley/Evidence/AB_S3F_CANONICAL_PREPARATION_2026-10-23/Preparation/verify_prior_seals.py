"""Read-only verification of all eighteen predecessor canonical evidence seals."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence');W=Path(__file__).parent
rows=[];sha=lambda raw:hashlib.sha256(raw).hexdigest()
for path in sorted(ROOT.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL_INVENTORY')):continue
 manifest=json.loads(path.read_text());artifacts=manifest['artifacts']
 for entry in artifacts:
  p=path.parent/entry['path'];raw=p.read_bytes()
  assert sha(raw)==entry['sha256'].lower() and len(raw)==entry['bytes'],str(p)
  if entry.get('expandedSha256'):assert sha(gzip.decompress(raw))==entry['expandedSha256'].lower(),str(p)
 if manifest.get('report'):assert sha((ROOT/manifest['report']).read_bytes())==manifest['reportSha256'].lower(),str(path)
 rows.append(dict(name=path.parent.name,artifacts=len(artifacts),manifestSha256=sha(path.read_bytes()),passed=True))
assert len(rows)==18,len(rows)
report=dict(passed=True,readOnly=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=len(rows),artifacts=sum(r['artifacts'] for r in rows),rows=rows)
assert report['artifacts']==3207,report['artifacts']
with (W/'prior_seals_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
