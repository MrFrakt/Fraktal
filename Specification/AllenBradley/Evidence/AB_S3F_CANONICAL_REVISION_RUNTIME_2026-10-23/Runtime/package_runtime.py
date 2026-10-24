from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
BASE=ROOT/'Specification/AllenBradley/Evidence';NAME='AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23';D=BASE/NAME;REPORT=BASE/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['authorizationConsumed'] and v['s3fStageComplete']
for n in v['requiredSuccessfulRuns']+['runtime_verification_01','prior_seals_closing_01','spec_closing_01','contracts_closing_01','consistency_closing_01','whitespace_closing_02']:
 assert json.loads((R/(n+'_exit.json')).read_text())['exitCode']==0,n
sources=json.loads((R/'source_verification_02.json').read_text())
for p,pin in sources['sha256'].items():assert sha((ROOT/p).read_bytes())==pin,p
assert not D.exists();D.mkdir()
def put(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def archive(name,p):
 assert '.acd' not in p.name.lower() and 'credential' not in p.name.lower()
 raw=p.read_bytes()
 if p.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
 put(name,raw)
for p in sorted(R.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
 if p.name.startswith('package_01') or p.name.startswith('seal_verification_'):continue
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():continue
 archive('Runtime/'+p.relative_to(R).as_posix(),p)
for name in ('echo_before_s3f.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','backup.sha256','canonical.sha256','deployed.sha256','authorization.json','deploy_attempt.json','restart_before.json','restart_after.json','capacity_review.json','preflight.json'):
 archive('Session/'+name,W/name)
for name in sources['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_S3F_REVISION_FOLLOWUP_2026-10-23.md','AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
 put('Target/'+name,(BASE.parent/name).read_bytes())
artifacts=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();a=dict(path=p.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
 if p.name.lower().endswith('.l5x.gz'):a['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(a)
prior=json.loads((R/'prior_seals_closing_01.json').read_text());assert prior['records']==21 and prior['artifacts']==4328
m=dict(schema='fraktal.ab.s3f-revision-runtime-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),publicationStage='S3f',runtimeAccepted=True,s3fStageComplete=True,acceptedCandidateRows=42,acceptedRetainedRestartRows=1,acceptedBaselineRows=31,acceptedTotalRows=74,actualRecordedRows=v['actualRecordedRows'],extraRecordedRows=v['extraRecordedRows'],pairedCaptures=v['pairedCaptures'],nativePayloadBytes=v['nativePayloadBytes'],timing=v['timing'],sourceBindings=143,abTests=2114,rootTests=74,preparedAcdSha256=v['preparedAcdSha256'],sdkSavedAcdSha256=v['sdkSavedAcdSha256'],finalGenealogyReady=True,authorizationConsumed=True,nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),priorSeals=prior['rows'])
put('manifest.json',json.dumps(m,indent=2).encode())
for a in artifacts:
 raw=(D/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256']
 if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=21,predecessorArtifacts=4328,s3fStageComplete=True,finalGenealogyReady=True,authorizationConsumed=True)
with (R/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
