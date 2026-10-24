from pathlib import Path
import datetime,gzip,hashlib,json,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
BASE=ROOT/'Specification/AllenBradley/Evidence'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
rows=[]
for path in sorted(BASE.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL')):continue
 m=json.loads(path.read_text())
 for a in m['artifacts']:
  raw=(path.parent/a['path']).read_bytes()
  assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower(),str(path.parent/a['path'])
  if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower()
 if m.get('report'):assert sha((BASE/m['report']).read_bytes())==m['reportSha256'].lower()
 rows.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(rows)==21 and sum(row['artifacts'] for row in rows)==4328,rows
prep=BASE/'AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23'
m=json.loads((prep/'manifest.json').read_text());bound=[]
for a in m['artifacts']:
 if a['path'].startswith('Preparation/'):
  relative=a['path'][len('Preparation/'):]
  path=W/(relative[:-3] if a.get('expandedSha256') and relative.endswith('.gz') else relative)
  raw=path.read_bytes()
  if a.get('expandedSha256'):assert sha(raw)==a['expandedSha256'].lower(),str(path)
  else:assert sha(raw)==a['sha256'].lower(),str(path)
  bound.append(relative)
sources=json.loads((W/'source_bindings_01.json').read_text())['sha256']
assert len(sources)==142
for path,pin in sources.items():assert sha((ROOT/path).read_bytes())==pin.lower(),path
pin='BD030AEB01D58469D452D877A9CFF2868B79DE45055A3795D1D1479BB2771183'
for path in (W/'s3f_canonical.ACD',W/'capacity_review.ACD'):assert sha(path.read_bytes()).upper()==pin
assert (W/'canonical.sha256').read_text().strip()==pin
assert sha((W/'genealogy_s3f_revision_01.L5X').read_bytes()).upper()=='B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3'
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seals=rows,sealCount=len(rows),artifacts=4328,sourceBindings=142,preparationFilesChecked=bound,preparedAcdSha256=pin,sha256=sources)
with (R/'opening_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
approval=json.loads((W/'authorization.template.json').read_text())
for key in ('CurrentOwnerApproved','ManualNormalizationAuthorized','AccessVectorsAuthorized','ConfigurationVectorsAuthorized','RevisionVectorsAuthorized','RetainedRestartAuthorized'):approval[key]=True
approval.update(OwnerAnswer='Approve the follow-up session',QuestionId='call_b8e9e258f03f4b089d447c3e1e056603:0',CapturedUtc=report['capturedUtc'],RuntimeFolder=str(R),ScopeSource='Specification/AllenBradley/Evidence/AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23.md')
assert approval['FaultClearAuthorized'] is False and approval['ClockSetAuthorized'] is False
with (W/'authorization.json').open('x') as f:json.dump(approval,f,indent=2)
shutil.copyfile(W/'authorization.json',R/'authorization.json')
shutil.copyfile(W/'run_logged.py',R/'run_logged.py')
print(json.dumps(dict(passed=True,seals=len(rows),artifacts=4328,sourceBindings=142,authorized=True)))
