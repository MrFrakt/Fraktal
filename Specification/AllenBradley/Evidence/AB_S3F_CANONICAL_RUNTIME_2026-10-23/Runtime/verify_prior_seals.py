"""Verify all nineteen predecessor canonical seals, including S3f preparation."""
from pathlib import Path
import datetime,gzip,hashlib,json
BASE=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence');R=Path(__file__).parent
sha=lambda raw:hashlib.sha256(raw).hexdigest();rows=[]
for path in sorted(BASE.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL_INVENTORY','AB_S3F_CANONICAL_PREPARATION')):continue
 manifest=json.loads(path.read_text())
 for a in manifest['artifacts']:
  p=path.parent/a['path'];raw=p.read_bytes()
  assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower(),str(p)
  if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower(),str(p)
 if manifest.get('report'):assert sha((BASE/manifest['report']).read_bytes())==manifest['reportSha256'].lower()
 rows.append(dict(name=path.parent.name,artifacts=len(manifest['artifacts']),manifestSha256=sha(path.read_bytes()),passed=True))
assert len(rows)==19 and sum(r['artifacts'] for r in rows)==3554
report=dict(passed=True,readOnly=True,records=19,artifacts=3554,rows=rows,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'prior_seals_verification_02.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
