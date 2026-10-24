from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
BASE=ROOT/'Specification/AllenBradley/Evidence';NAME='AB_S3E_CANONICAL_PREPARATION_2026-10-22'
DEST=BASE/NAME;REPORT=BASE/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((W/'preparation_verification_01.json').read_text());assert v['passed'] and v['controllerChanges']==0 and not v['runtimeAccepted']
for name in v['requiredSuccessfulRuns']:assert json.loads((W/(name+'_exit.json')).read_text())['exitCode']==0,name
bindings=json.loads((W/'source_bindings_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
assert not DEST.exists();DEST.mkdir()
def put(relative,raw):
 p=DEST/relative;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
def archive(relative,p):
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():raise ValueError('forbidden evidence filename')
 raw=p.read_bytes()
 if p.suffix.lower()=='.l5x':relative+='.gz';raw=gzip.compress(raw,mtime=0)
 put(relative,raw)
for p in sorted(W.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
 if p.name.startswith('package_01') or p.name.startswith('seal_verification_'):continue
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():continue
 if p.suffix.lower() not in {'.py','.ps1','.cs','.csproj','.config','.json','.sha256','.md','.log','.gz','.l5x','.txt'}:continue
 archive('Preparation/'+p.relative_to(W).as_posix(),p)
for name in bindings['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
docs=('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json','AB_CANONICAL_PUBLICATION_S3E_NOTES_2026-10-22.md','AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json','AB_CAPACITY_FORECAST_METHOD_2026-10-21.md','AB_CAPACITY_OBSERVATIONS_2026-10-21.json')
for name in docs:put('Target/'+name,(BASE.parent/name).read_bytes())
artifacts=[]
for p in sorted(DEST.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();a=dict(path=p.relative_to(DEST).as_posix(),bytes=len(raw),sha256=sha(raw))
 if p.name.lower().endswith('.l5x.gz'):a['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(a)
prior=json.loads((W/'prior_seals_verification_01.json').read_text());assert prior['records']==15 and prior['artifacts']==2628
cap=json.loads((W/'capacity_review.json').read_text())
m=dict(schema='fraktal.ab.s3e-canonical-preparation-evidence',schemaVersion=1,date='2026-10-22',timeZone='America/Mexico_City',sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),sourceCommit=bindings['sourceCommit'],publicationStage='S3e',offlineGatesPassed=True,runtimeAccepted=False,controllerChanges=0,currentAuthorizationPending=True,preflightRecorded=True,manualOrdinal=1,preparedAcdSha256=v['preparedAcdSha256'],generatedSourceSha256=v['sourceSha256'],expectedPaths=2154,fixtureEquipmentModules=0,fixtureConcurrentLegs=0,sourceBindings=76,abTests=2078,rootTests=74,plannedCandidateRegressionRows=31,plannedAdditionalAccessRows=2,plannedBaselineRegressionRows=31,plannedRegressionRows=64,capacityMeasured=True,capacityProvider=cap['Provider'],usedStandardBlocks=cap['UsedStandardBlocks'],availableBlocks=cap['AvailableBlocks'],totalBlocks=cap['TotalBlocks'],forecastHoldout=v['forecastHoldout'],nativeAcdFilesArchived=False,credentialFilesArchived=False,artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),priorSeals=prior['rows'])
put('manifest.json',json.dumps(m,indent=2).encode())
for a in artifacts:
 raw=(DEST/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'],a['path']
 if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'],a['path']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((DEST/'manifest.json').read_bytes()),predecessorRecords=15,predecessorArtifacts=2628,controllerChanges=0,runtimeAccepted=False,currentAuthorizationPending=True)
with (W/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
