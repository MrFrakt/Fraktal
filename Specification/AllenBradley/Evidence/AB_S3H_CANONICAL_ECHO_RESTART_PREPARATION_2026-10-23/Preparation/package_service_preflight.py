from pathlib import Path
import datetime,gzip,hashlib,json
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3H_CANONICAL_DIAGNOSTIC_SERVICE_PREFLIGHT_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((R/'preflight_service_stop_01.json').read_text());assert v['controllerChanges']==0 and not v['authorizationConsumed']
for label in ('prepare_resumption_01','record_service_stop_01','root_service_stop_01','spec_service_stop_01',
 'contracts_service_stop_01','consistency_service_stop_01','whitespace_service_stop_01'):
 assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
prior=[]
for path in sorted(E.glob('AB_*/manifest.json')):
 if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL',
 'AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL','AB_S3H_CANONICAL')):continue
 m=json.loads(path.read_text())
 for row in m['artifacts']:
  p=path.parent/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'].lower()
 if m.get('report'):assert sha(E/m['report'])==m['reportSha256'].lower()
 prior.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path)))
assert len(prior)==34 and sum(p['artifacts'] for p in prior)==8312
assert not D.exists();D.mkdir()
def copy(path,name):
 dest=D/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(path.read_bytes())
for p in sorted(R.iterdir()):
 if not p.is_file() or p.name.startswith(('package_service_preflight_01','service_preflight_seal_')):continue
 assert p.suffix.lower()!='.acd' and 'credential' not in p.name.lower(),p
 copy(p,'Preflight/'+p.name)
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_FROZEN_CONTRACTS_V2.json'):
 copy(AB/name,'Target/'+name)
rows=[dict(path=p.relative_to(D).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(D.rglob('*')) if p.is_file()]
m=dict(schema='fraktal.ab.s3h-diagnostic-service-preflight-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
 status='service-stopped-no-controller-change-current-authorization-unused',controllerChanges=0,authorizationConsumed=False,
 approvalQuestion=v['authorizationQuestion'],runtimeDirectory=R.as_posix(),stageAccepted=False,
 credentialFilesArchived=False,nativeAcdFilesArchived=False,priorSeals=prior,artifacts=rows,
 artifactCount=len(rows),totalBytes=sum(r['bytes'] for r in rows))
with (D/'manifest.json').open('x') as f:json.dump(m,f,indent=2)
for row in rows:assert sha(D/row['path'])==row['sha256']
result=dict(passed=True,artifactCount=len(rows),manifestSha256=sha(D/'manifest.json'),reportSha256=sha(REPORT),
 predecessorRecords=34,predecessorArtifacts=8312,currentRecords=35,currentArtifacts=8312+len(rows),controllerChanges=0,authorizationConsumed=False)
with (R/'service_preflight_seal_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
