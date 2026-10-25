"""Seal the completed authorized session and verify every predecessor again."""
from datetime import datetime,timezone
from pathlib import Path
import gzip,hashlib,json,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');EV=ROOT/'Specification/AllenBradley/Evidence'
R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3i-20261024/prepare_d6df75f72d02435aab2ef3fbd7ea986d')
NAME='AB_S3I_CANONICAL_RUNTIME_2026-10-24';OUT=EV/NAME;REPORT=EV/(NAME+'.md')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
assert not OUT.exists(),'append-only runtime record already exists'
prep_name='AB_S3I_CANONICAL_PREPARATION_2026-10-24';prep=load(EV/prep_name/'manifest.json')
names=[row['name'] for row in prep['priorSeals']]+[prep_name]
seals=[];total=0
assert len(names)==len(set(names))==43
for name in names:
    p=EV/name/'manifest.json';d=load(p)
    for row in d['artifacts']:
        raw=(EV/name/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'].lower(),(name,row['path'])
        if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256'].lower()
    if d.get('reportSha256'):assert sha(EV/d['report'])==d['reportSha256'].lower()
    total+=len(d['artifacts']);seals.append(dict(name=name,artifacts=len(d['artifacts']),manifestSha256=sha(p)))
assert total==9800,total
summary=load(R/'runtime_summary_01.json');assert summary['passed'] and not summary['calendarProducerLifetimeAccepted']
assert load(R/'authorization_consumed_01.json')['CurrentOwnerApproved'] is False
assert load(W/'authorization.json')['CurrentOwnerApproved'] is False
assert sha(W/'capacity_review.ACD').upper()==summary['preparedAcdSha256']
assert sha(R/'s3i_regenerated_01.L5X')==summary['sourceSha256']==prep['sourceSha256']
bindings=load(R/'initial_source_verification_02.json')['sha256']
assert len(bindings)==170 and all(sha(ROOT/name)==pin for name,pin in bindings.items())
for label in ('ab_suite_01','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_02',
              'start_driver_01','guard_final_01','independent_replay_01','summarize_runtime_01','regenerate_01'):
    assert load(R/(label+'_exit.json'))['exitCode']==0,label
assert b'Ran 2178 tests' in (R/'ab_suite_01.log').read_bytes()
OUT.mkdir()
def copy(source,relative,compress=False):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
    if compress:
        with source.open('rb') as input,target.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as packed:shutil.copyfileobj(input,packed)
    else:shutil.copyfile(source,target)

for source in sorted(R.rglob('*')):
    if not source.is_file():continue
    if source.name.startswith('package_runtime_01'):continue  # current stdout is not finished
    assert not any(s in source.name.lower() for s in ('credential','password','secret','dumpfile'))
    if any(part in ('bin','obj','__pycache__') for part in source.relative_to(R).parts):continue
    if source.suffix.lower() not in ('.json','.gz','.log','.py','.l5x'):continue
    relative=Path('Runtime')/source.relative_to(R)
    copy(source,str(relative)+('.gz' if source.suffix.lower()=='.l5x' else ''),source.suffix.lower()=='.l5x')

session_names=['preflight.json','backup.sha256','canonical.sha256','deploy_attempt.json','authorization.json',
    'canonical_prepared_compare.json','baseline_capacity.json','baseline_reference.json','capacity_review.json',
    'scripts/guard_echo.py','scripts/preflight.py','session/Program.cs','session/S3iSession.csproj','session/NuGet.Config',
    'ensure_manual.py','final_checks.py','measure_timing.py','audit_access.py']
for name in session_names:copy(W/name,str(Path('Session')/name))
for name in ('echo_before_s3i.L5X','canonical_downloaded.L5X','genealogy_restored.L5X','s3i_bench_05.L5X'):
    copy(W/name,str(Path('Session')/(name+'.gz')),True)
for name in sorted(bindings):copy(ROOT/name,str(Path('Source')/name)+'.gz',True)
contracts=['AGENTS.md','Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json']
for name in contracts:copy(ROOT/name,str(Path('Contract')/name))
with (OUT/'contract_bindings.json').open('x') as f:json.dump({name:sha(ROOT/name) for name in contracts},f,indent=2)

artifacts=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();row=dict(path=p.relative_to(OUT).as_posix(),sha256=sha(p),bytes=len(raw))
        if p.suffix=='.gz':row['expandedSha256']=hashlib.sha256(gzip.decompress(raw)).hexdigest()
        artifacts.append(row)
manifest=dict(schema='fraktal.ab.s3i-canonical-runtime-evidence',schemaVersion=1,date='2026-10-24',
    timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    status='publication-native-passed-genealogy-restored-calendar-lifetime-open',publicationAccepted=True,stageAccepted=False,
    sessionApprovalConsumed=True,approvalSource='Owner reply "Approve this guarded S3i session", call_857f749a9e6d4fd6a69515d2b6e226ab:0',
    preparedAcdSha256=summary['preparedAcdSha256'],postDownloadSavedAcdSha256=summary['postDownloadSavedAcdSha256'],
    sourceSha256=summary['sourceSha256'],backupSha256=summary['backupSha256'],sourceBindings=170,readOnlyObserverSourceDeltaFiles=1,
    candidateChecks=41,nativePublicationVectors=8,baselineChecks=31,recordedChecks=80,pairedCaptures=88,independentReplays=88,
    proofAttempts=summary['attempts'],pathCounts=summary['pathCounts'],idlePaths=3968,nativeRecordBytes=[134720,7308,16616],
    observationFrameBytes=173792,frameFragments=44,capacity=summary['capacity'],timing=summary['timing'],
    final=summary['final'],observedLiveShiftHistoryCounts=[0],calendarProducerLifetimeAccepted=False,physicalRetentionAccepted=False,
    abTests=2178,rootTests=74,priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),
    totalBytes=sum(row['bytes'] for row in artifacts))
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,reportSha256=sha(REPORT),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),priorRecords=len(seals),priorArtifacts=total,bytes=manifest['totalBytes'])))
