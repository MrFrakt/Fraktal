"""Append one complete preparation seal; never archive native ACD/credentials."""
from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
NAME='AB_S3G_CANONICAL_PREPARATION_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((P/'full_preparation_verification_01.json').read_text())
assert v['passed'] and v['controllerChanges']==0 and v['currentAuthorizationPending'] and not v['runtimeAccepted']
for label in v['requiredSuccessfulRuns']+['full_verification_01']:
    assert json.loads((P/(label+'_exit.json')).read_text())['exitCode']==0,label
for name,pin in v['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
assert not D.exists();D.mkdir()
def put(name,raw):
    path=D/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
for path in sorted(P.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.parts):continue
    if path.suffix.lower()=='.acd' or 'credential' in path.name.lower():continue
    if path.name.startswith(('full_package_01','full_seal_verification_')):continue
    name='Preparation/'+path.relative_to(P).as_posix();raw=path.read_bytes()
    if path.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
    put(name,raw)
for name in v['sha256']:put('Source/'+name,(ROOT/name).read_bytes())
inventory=json.loads((AB/'AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json').read_text())
for name,bound in inventory['sourceBindings'].items():
    if name in v['sha256']:continue
    raw=(ROOT/name).read_bytes();assert sha(raw)==bound['sha256'];put('Reference/'+name,raw)
for name in ('AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md','AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md',
    'AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json','AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md',
    'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
    'AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
    put('Target/'+name,(AB/name).read_bytes())
artifacts=[]
for path in sorted(D.rglob('*')):
    if not path.is_file():continue
    raw=path.read_bytes();row=dict(path=path.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
    if path.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
    artifacts.append(row)
helper=P/'session/bin/Debug/net8.0/win-x86/S3gSession.exe'
m=dict(schema='fraktal.ab.s3g-canonical-preparation-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
    status='offline-gates-passed-current-native-authorization-pending',runtimeAccepted=False,controllerAccess='read-only baseline checks',controllerChanges=0,
    sourceSha256=v['sourceSha256'],preparedAcdSha256=v['preparedAcdSha256'],
    sessionExecutableSha256=sha(helper.read_bytes()),sessionSourceSha256=sha((P/'session/Program.cs').read_bytes()),
    canonicalAddedPaths=1055,approvedNumericPaths=200,approvedDependentValuePaths=224,otherAddedPathsExact=631,
    abTests=2127,abSeconds=291.415,rootTests=74,focusedTests=13,abSourceBindings=151,
    nativeOfflineTargets=['EchoController','PhysicalController'],capacityMeasured=True,capacityUnit='Blocks',
    capacityBlocks=2407200,availableBlocks=738528,totalBlocks=3145728,deltaFromAcceptedS3fBlocks=108752,
    scanMeasured=False,plannedCandidateRows=41,plannedNativeVectorResults=11,plannedBaselineRows=31,
    failedRunsRetained=v['failedRunsRetained'],priorSeals=v['priorSeals'],nativeAcdFilesArchived=False,credentialFilesArchived=False,
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
    raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),
    predecessorRecords=24,predecessorArtifacts=5287,currentRecords=25,currentArtifacts=5287+len(artifacts),
    sourceBindings=151,abTests=2127,rootTests=74,controllerChanges=0,currentAuthorizationPending=True)
with (P/'full_seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
