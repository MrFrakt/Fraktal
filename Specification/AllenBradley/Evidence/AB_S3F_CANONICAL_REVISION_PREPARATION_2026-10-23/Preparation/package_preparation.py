"""Append-only seal of the revision-fix preparation; no native authorization."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
BASE=ROOT/'Specification/AllenBradley/Evidence';NAME='AB_S3F_CANONICAL_REVISION_PREPARATION_2026-10-23';D=BASE/NAME;REPORT=BASE/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((W/'preparation_verification_01.json').read_text());assert v['passed'] and v['controllerChanges']==0 and not v['runtimeAccepted']
for n in v['requiredSuccessfulRuns']+['spec_02','contracts_02','consistency_02','whitespace_01','preflight_verify_01']:
 assert json.loads((W/(n+'_exit.json')).read_text())['exitCode']==0,n
bindings=json.loads((W/'source_bindings_01.json').read_text())
for name,pin in bindings['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
for p in W.rglob('*.py'):
 if not any(part in ('bin','obj','__pycache__') for part in p.parts):compile(p.read_bytes(),str(p),'exec')
assert not (W/'authorization.json').exists();assert not D.exists();D.mkdir()
def put(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
for p in sorted(W.rglob('*')):
 if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
 if p.name.startswith('package_01') or p.name.startswith('seal_verification_'):continue
 if '.acd' in p.name.lower() or 'credential' in p.name.lower():continue
 name='Preparation/'+p.relative_to(W).as_posix();raw=p.read_bytes()
 if p.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
 put(name,raw)
for name in bindings['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_S3F_REVISION_FOLLOWUP_2026-10-23.md',
 'AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md','AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
 put('Target/'+name,(BASE.parent/name).read_bytes())
artifacts=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();a=dict(path=p.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
 if p.name.lower().endswith('.l5x.gz'):a['expandedSha256']=sha(gzip.decompress(raw))
 artifacts.append(a)
m=dict(schema='fraktal.ab.s3f-revision-preparation-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
 sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
 publicationStage='S3f-revision-followup',offlineGatesPassed=True,runtimeAccepted=False,controllerChanges=0,currentAuthorizationPending=True,
 preparedAcdSha256=v['preparedAcdSha256'],generatedSourceSha256=v['sourceSha256'],sourceBindings=142,abTests=2111,rootTests=74,
 plannedCandidateRows=42,plannedRetainedRestartRows=1,plannedBaselineRows=31,plannedTotalRows=74,
 usedStandardBlocks=2298448,availableBlocks=847280,totalBlocks=3145728,deltaCapacityBlocks=36,
 failedRunsRetained=v['failedRunsRetained'],priorSeals=v['priorSeals'],nativeAcdFilesArchived=False,credentialFilesArchived=False,
 artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for a in artifacts:
 raw=(D/a['path']).read_bytes();assert len(raw)==a['bytes'] and sha(raw)==a['sha256'],a['path']
 if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'],a['path']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=20,predecessorArtifacts=4032,controllerChanges=0,currentAuthorizationPending=True)
with (W/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
