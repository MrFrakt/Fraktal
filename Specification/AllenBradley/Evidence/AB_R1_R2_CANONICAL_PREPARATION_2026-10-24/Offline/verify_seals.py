from pathlib import Path
import json,hashlib,gzip,re,time
R=Path('C:/Users/SoftIndVM/Fraktal');E=R/'Specification/AllenBradley/Evidence';O=Path('C:/work/fraktal-ab-s3j-20261024/r1_01');rows=[];total=0
pattern=re.compile(r'AB_S(0|1|2|3[A-Z]?)_(CANONICAL|SUPPLEMENTARY)_')
for p in sorted(E.glob('AB_*/manifest.json')):
 if not pattern.match(p.parent.name):continue
 m=json.loads(p.read_bytes())
 for a in m['artifacts']:
  raw=(p.parent/a['path']).read_bytes()
  assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256'].lower(),(p,a['path'])
  if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==a['expandedSha256'].lower()
 if m.get('report') and m.get('reportSha256'):assert hashlib.sha256((E/m['report']).read_bytes()).hexdigest()==m['reportSha256'].lower()
 total+=len(m['artifacts']);rows.append(dict(name=p.parent.name,manifestSha256=hashlib.sha256(p.read_bytes()).hexdigest(),artifacts=len(m['artifacts'])))
with (O/'prior_seals_01.json').open('x') as f:json.dump(dict(passed=True,records=len(rows),artifacts=total,rows=rows),f,indent=2)
print(json.dumps(dict(passed=True,records=len(rows),artifacts=total)))
