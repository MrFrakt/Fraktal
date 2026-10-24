from pathlib import Path
import datetime,gzip,hashlib,json
R=Path(__file__).parent;BASE=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence');sha=lambda raw:hashlib.sha256(raw).hexdigest()
opening=json.loads((R/'opening_verification_01.json').read_text());rows=[]
for before in opening['seals']:
 path=BASE/before['name']/'manifest.json';assert sha(path.read_bytes())==before['manifestSha256']
 m=json.loads(path.read_text())
 for a in m['artifacts']:
  raw=(path.parent/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower()
  if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower()
 if m.get('report'):assert sha((BASE/m['report']).read_bytes())==m['reportSha256'].lower()
 rows.append(before)
assert len(rows)==21 and sum(row['artifacts'] for row in rows)==4328
report=dict(passed=True,readOnly=True,controllerAccess=False,records=21,artifacts=4328,rows=rows,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (R/'prior_seals_closing_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
