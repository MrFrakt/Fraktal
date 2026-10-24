from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((R/'restart_preparation_01.json').read_text());assert v['passed'] and v['controllerChanges']==0
assert sha(R/'EchoRestart/Program.cs')==v['helperSourceSha256']
assert sha(R/'EchoRestart/bin/Debug/net10.0-windows/EchoRestart.exe')==v['helperSha256']
for label in ('echo_restart_build_02','echo_restart_selftest_02','record_restart_preparation_01',
 'root_restart_prep_01','spec_restart_prep_01','contracts_restart_prep_01','consistency_restart_prep_01','whitespace_restart_prep_01'):
 assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
assert not (R/'restart_authorization.json').exists() and not (R/'restart_attempt.json').exists()
prior=[]
for path in sorted(E.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL',
 'AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
 m=json.loads(path.read_text())
 for row in m['artifacts']:
  p=path.parent/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'].lower()
 if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
 prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(prior)==35 and sum(p['artifacts'] for p in prior)==8351
assert not D.exists();D.mkdir()
def copy(path,name):
 dest=D/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(path.read_bytes())
for p in sorted(R.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
 if p.name.startswith(('package_restart_preparation_01','restart_preparation_seal_')):continue
 assert p.suffix.lower()!='.acd' and 'credential' not in p.name.lower(),p
 copy(p,'Preparation/'+p.relative_to(R).as_posix())
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_FROZEN_CONTRACTS_V2.json'):
 copy(AB/name,'Target/'+name)
rows=[dict(path=p.relative_to(D).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(D.rglob('*')) if p.is_file()]
m=dict(schema='fraktal.ab.s3h-echo-restart-preparation-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
 status='ClosedExternally-restart-prepared-current-authorization-pending',controllerChanges=0,
 helperSha256=v['helperSha256'],helperSourceSha256=v['helperSourceSha256'],authorizationTests=6,
 originalDiagnosticApprovalConsumed=False,currentRestartApprovalPending=True,sourceBindingsUnchanged=159,
 credentialFilesArchived=False,nativeAcdFilesArchived=False,priorSeals=prior,artifacts=rows,
 artifactCount=len(rows),totalBytes=sum(r['bytes'] for r in rows))
with (D/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
for row in rows:assert sha(D/row['path'])==row['sha256']
result=dict(passed=True,artifactCount=len(rows),manifestSha256=sha(D/'manifest.json'),reportSha256=sha(REPORT),
 predecessorRecords=35,predecessorArtifacts=8351,currentRecords=36,currentArtifacts=8351+len(rows),controllerChanges=0,
 currentRestartApprovalPending=True,originalDiagnosticApprovalConsumed=False)
with (R/'restart_preparation_seal_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
