from pathlib import Path
import datetime,gzip,hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;W=P.parent/'transport_bd2c073c468c443eb19ca12f85d90eda'
AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence';NAME='AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23';D=E/NAME;REPORT=E/(NAME+'.md')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((P/'diagnostic_verification_01.json').read_text());assert v['passed'] and v['controllerChanges']==0 and v['currentOwnerApprovalPending']
assert json.loads((P/'diagnostic_verification_02_exit.json').read_text())['exitCode']==0
for name,pin in v['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
assert not D.exists();D.mkdir()
def put(name,raw):
    p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(raw)
def copy(p,name):
    raw=p.read_bytes()
    if p.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
    put(name,raw)
for directory,prefix in ((P,'Preparation'),(W,'TransportExperiments')):
    for p in sorted(directory.rglob('*')):
        if not p.is_file() or any(part in ('bin','obj','__pycache__') for part in p.parts):continue
        if p.suffix.lower()=='.acd' or 'credential' in p.name.lower() or p.name.startswith(('package_retry_01','diagnostic_seal_verification_')):continue
        copy(p,prefix+'/'+p.relative_to(directory).as_posix())
for name in v['sha256']:copy(ROOT/name,'Source/'+name)
for name in ('AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_FROZEN_CONTRACTS_V2.json'):
    copy(AB/name,'Target/'+name)
artifacts=[]
for p in sorted(D.rglob('*')):
    if not p.is_file():continue
    raw=p.read_bytes();row=dict(path=p.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
    if p.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
    artifacts.append(row)
m=dict(schema='fraktal.ab.s3h-canonical-diagnostic-preparation-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
    status='diagnostic-offline-gates-passed-current-native-authorization-pending',stageAccepted=False,controllerChanges=0,
    preparedAcdSha256=v['preparedAcdSha256'],sourceSha256=v['sourceSha256'],sessionExecutableSha256=v['sessionExecutableSha256'],
    sessionSourceSha256=v['sessionSourceSha256'],sourceBindings=159,abTests=2149,abSeconds=v['abSeconds'],rootTests=74,
    connections=4,maximumOutstandingPerConnection=1,attemptLimit=100,secondsLimit=5,allWaitingPollsCounted=True,
    baselineTransportProxyOnly=True,diagnosticWrapperTests=4,unchangedEvenWaitSeconds=.001,capacityReusedByExactImageHash=True,capacityBlocks=2501720,availableBlocks=644008,totalBlocks=3145728,
    credentialFilesArchived=False,nativeAcdFilesArchived=False,priorSeals=v['priorSeals'],
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
    raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,diagnosticReady=True,currentOwnerApprovalPending=True,artifactCount=len(artifacts),bytes=m['totalBytes'],
    reportSha256=m['reportSha256'],manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=33,predecessorArtifacts=8072,
    currentRecords=34,currentArtifacts=8072+len(artifacts),controllerChanges=0,sourceBindings=159)
with (P/'diagnostic_seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
