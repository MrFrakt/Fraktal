"""Append S3g runtime evidence with exact bytes, source closure and prior seals."""
from pathlib import Path
import datetime,gzip,hashlib,json,re
ROOT=Path('C:/Users/SoftIndVM/Fraktal');R=Path(__file__).parent;P=R.parent/'prepare_feb76c7a0968442293ee0d20b812eb17'
AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence';NAME='AB_S3G_CANONICAL_RUNTIME_2026-10-23'
D=E/NAME;REPORT=E/(NAME+'.md');sha=lambda raw:hashlib.sha256(raw).hexdigest()
v=json.loads((R/'runtime_verification_01.json').read_text());assert v['passed'] and v['acceptedTotalChecks']==83
for label in v['requiredSuccessfulRuns']+['runtime_verification_01','finish_documents_01','spec_closing_01','contracts_closing_01',
    'consistency_closing_01','root_tests_closing_01','capacity_calibration_01','whitespace_closing_01']:
    assert json.loads((R/(label+'_exit.json')).read_text())['exitCode']==0,label
sources=json.loads((R/'source_verification_01.json').read_text())['sha256']
for name,pin in sources.items():assert sha((ROOT/name).read_bytes())==pin,name
assert re.search(r'Ran 74 tests in [\d.]+s\s+OK',(R/'root_tests_closing_01.log').read_text())
assert json.loads((R/'authorization_consumed.json').read_text())['consumed']
assert not D.exists();D.mkdir()
def put(name,raw):
    path=D/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as file:file.write(raw)
for path in sorted(R.rglob('*')):
    if not path.is_file() or any(part in ('bin','obj','__pycache__') for part in path.parts):continue
    if path.name.startswith(('package_01','seal_verification_')):continue
    assert path.suffix.lower()!='.acd' and 'credential' not in path.name.lower(),path
    name='Runtime/'+path.relative_to(R).as_posix();raw=path.read_bytes()
    if path.suffix.lower()=='.l5x':name+='.gz';raw=gzip.compress(raw,mtime=0)
    put(name,raw)
for name in ('echo_before_s3g.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','backup.sha256','canonical.sha256','deploy_attempt.json'):
    path=P/name;raw=path.read_bytes();archive='Controller/'+name
    if path.suffix.lower()=='.l5x':archive+='.gz';raw=gzip.compress(raw,mtime=0)
    put(archive,raw)
for name in sources:put('Source/'+name,(ROOT/name).read_bytes())
for name in ('AB_CANONICAL_PUBLICATION_S3G_NOTES_2026-10-23.md','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
    'AB_FROZEN_CONTRACTS_V2.json','AB_CAPACITY_OBSERVATIONS_2026-10-21.json'):
    put('Target/'+name,(AB/name).read_bytes())
artifacts=[]
for path in sorted(D.rglob('*')):
    if not path.is_file():continue
    raw=path.read_bytes();row=dict(path=path.relative_to(D).as_posix(),bytes=len(raw),sha256=sha(raw))
    if path.name.lower().endswith('.l5x.gz'):row['expandedSha256']=sha(gzip.decompress(raw))
    artifacts.append(row)
m=dict(schema='fraktal.ab.s3g-canonical-runtime-evidence',schemaVersion=1,date='2026-10-23',timeZone='America/Mexico_City',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT.read_bytes()),
    status='S3g-Echo-exit-passed-genealogy-restored',runtimeAccepted=True,authorizationConsumed=True,
    approvalQuestion='call_5e5f359334b94e09adf9531a212f0d9c:0',acceptedCandidateRows=41,acceptedNativeVectorResults=11,
    acceptedBaselineRows=31,acceptedTotalChecks=83,actualRecordedChecks=83,pairedCaptures=88,
    expectedPagePaths=[3672,3622,3272],canonicalAddedPaths=1055,abSourceBindings=151,allPreparedSourcesUnchanged=True,
    abTests=2127,abTestsSource='identical-source preparation seal',rootTests=74,capacityUnit='Blocks',
    capacityBlocks=2407200,availableBlocks=738528,totalBlocks=3145728,deltaFromAcceptedS3fBlocks=108752,
    nativePayloadBytes=145084,nativeRecordBytes=[121160,7308,16616],timing=v['timing'],attempts=v['attempts'],
    preparedAcdSha256=v['preparedAcdSha256'],sourceSha256=v['sourceSha256'],sdkSavedAcdSha256=v['sdkSavedAcdSha256'],
    backupAcdSha256=v['backupAcdSha256'],finalGenealogyReady=True,failedRunsRetained=[],
    nativeAcdFilesArchived=False,credentialFilesArchived=False,priorSeals=v['priorSeals'],
    artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(row['bytes'] for row in artifacts))
put('manifest.json',json.dumps(m,indent=2).encode())
for row in artifacts:
    raw=(D/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
    if row.get('expandedSha256'):assert sha(gzip.decompress(raw))==row['expandedSha256']
assert sha(REPORT.read_bytes())==m['reportSha256']
result=dict(passed=True,artifacts=len(artifacts),bytes=m['totalBytes'],reportSha256=m['reportSha256'],
    manifestSha256=sha((D/'manifest.json').read_bytes()),predecessorRecords=25,predecessorArtifacts=5689,
    currentRecords=26,currentArtifacts=5689+len(artifacts),acceptedChecks=83,authorizationConsumed=True)
with (R/'seal_verification_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
