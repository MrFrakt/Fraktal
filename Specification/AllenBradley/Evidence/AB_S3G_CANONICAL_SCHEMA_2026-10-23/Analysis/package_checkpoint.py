from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3G_CANONICAL_SCHEMA_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((P/'checkpoint_verification_01.json').read_text());assert v['passed'] and v['controllerChanges']==0 and not v['fullS3gCandidate'] and not v['dependentValuesApproved']
for label in v['requiredSuccessfulRuns']+['checkpoint_verification_01','spec_gate_01','contracts_gate_01','consistency_gate_01','root_tests_01','whitespace_gate_01']:
 assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
for name,pin in v['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
assert not D.exists();D.mkdir()
def put(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
for p in sorted(P.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
 if p.name.startswith(('package_01','seal_verification_')):continue
 assert '.acd' not in p.name.lower() and 'credential' not in p.name.lower()
 name='Analysis/'+p.relative_to(P).as_posix();raw=p.read_bytes()
 if p.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
 put(name,raw)
for name in v['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
inventory=json.loads((AB/'AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
for name,bound in inventory['sourceBindings'].items():
 if name in v['sha256']:continue
 raw=(ROOT/name).read_bytes();assert sha(raw)==bound['sha256'];put('Reference/'+name,raw)
for name in ('AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md','AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md','AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json','AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
 put('Target/'+name,(AB/name).read_bytes())
artifacts=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();row=dict(path=p.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
 if p.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(row)
m=dict(schema='fraktal.ab.s3g-schema-checkpoint-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),status='partial-offline-qualification-dependent-value-decision-pending',runtimeAccepted=False,fullS3gCandidate=False,controllerAccess=False,controllerChanges=0,typePathsApproved=200,pendingDependentValuePaths=224,canonicalPathsAdded=1055,abTests=2118,rootTests=74,abSourceBindings=145,nativeTypeHealthTargets=['EchoController','PhysicalController'],sourceSha256=v['sourceSha256'],capacityMeasured=False,scanMeasured=False,failedRunsRetained=v['failedRunsRetained'],priorSeals=v['priorSeals'],nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for a in artifacts:
 raw=(D/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256']
 if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=23,predecessorArtifacts=5032,controllerChanges=0,fullS3gCandidate=False,dependentValueDecisionPending=True)
with (P/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
