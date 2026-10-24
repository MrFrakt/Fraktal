"""Append S3h native runtime evidence; no credentials or ACD binaries."""
from pathlib import Path
import datetime,gzip,hashlib,json,re
R=Path(__file__).parent;P=R.parent/'retry_fc306d330cc642499a52abbb53bae945'
ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3H_CANONICAL_RUNTIME_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['acceptedTotalChecks']==72
for label in v['requiredSuccessfulRuns']+['runtime_verification_01','finish_documents_01','spec_closing_01',
 'contracts_closing_01','consistency_closing_01','root_tests_closing_01','capacity_calibration_01','whitespace_closing_01']:
 assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
sources=json.loads((R/'source_verification_01.json').read_text())['sha256']
for name,pin in sources.items():assert sha((ROOT/name).read_bytes())==pin,name
assert re.search(r'Ran 74 tests in [\d.]+s\s+OK',(R/'root_tests_closing_01.log').read_text())
for seal in v['priorSeals']:
 path=E/seal['name']/'manifest.json';assert sha(path.read_bytes())==seal['manifestSha256']
 m=json.loads(path.read_text())
 for item in m['artifacts']:
  raw=(path.parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256'].lower()
 assert sha((E/m['report']).read_bytes())==m['reportSha256'].lower()
assert not D.exists();D.mkdir()
def put(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def copy(path,name):
 raw=path.read_bytes()
 if path.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
 put(name,raw)
for path in sorted(R.rglob('*')):
 if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.parts):continue
 if path.name.startswith(('package_01','seal_verification_')):continue
 assert path.suffix.lower()!='.acd' and 'credential' not in path.name.lower(),path
 copy(path,'Runtime/'+path.relative_to(R).as_posix())
for name in ('echo_before_s3h.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','backup.sha256',
 'canonical.sha256','deploy_attempt.json','authorization.json','session/Program.cs','prepared_image_reference.json'):
 copy(P/name,'Controller/'+name)
for name in sources:copy(ROOT/name,'Source/'+name)
for name in ('AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
 'AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
 copy(AB/name,'Target/'+name)
artifacts=[]
for path in sorted(D.rglob('*')):
 if not path.is_file():continue
 raw=path.read_bytes();row=dict(path=path.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
 if path.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(row)
m=dict(schema='fraktal.ab.s3h-canonical-runtime-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
 status='S3h-Echo-exit-passed-genealogy-restored',runtimeAccepted=True,authorizationConsumed=True,
 approvalQuestion='call_9b203bdff24848999469abe17a76ee4f:0',acceptedCandidateRows=41,acceptedBaselineRows=31,
 acceptedTotalChecks=72,actualRecordedChecks=72,pairedCaptures=88,fullRingExpectedPagePaths=[3950,3900,3550],
 canonicalAddedPaths=278,approvedTypePaths=36,abSourceBindings=159,allPreparedSourcesUnchanged=True,
 abTests=2149,abTestsSource='identical-source paced preparation seal',rootTests=74,capacityUnit='Blocks',
 capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,deltaFromAcceptedS3gBlocks=94520,
 nativePayloadBytes=v['nativePayloadBytes'],nativeRecordBytes=v['nativeRecordBytes'],timing=v['timing'],attempts=v['attempts'],
 traceObservations=v['traceObservations'],connections=4,maximumOutstandingPerConnection=1,unchangedEvenWaitSeconds=.001,
 preparedAcdSha256=v['preparedAcdSha256'],sourceSha256=v['sourceSha256'],sdkSavedAcdSha256=v['sdkSavedAcdSha256'],
 backupAcdSha256=v['backupAcdSha256'],finalGenealogyReady=True,failedRunsRetained=v['failedRunsRetained'],
 nativeAcdFilesArchived=False,credentialFilesArchived=False,priorSeals=v['priorSeals'],
 artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(r['bytes'] for r in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
 raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
 if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],
 manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=32,predecessorArtifacts=7749,
 currentRecords=33,currentArtifacts=7749+len(artifacts),acceptedChecks=72,authorizationConsumed=True)
with (R/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
