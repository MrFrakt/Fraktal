"""Append-only follow-up record, exact-image gate transfer and source binding."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,shutil
ROOT=Path('C:/Users/SoftIndVM/Fraktal');EV=ROOT/'Specification/AllenBradley/Evidence';W=Path(__file__).parent
NAME='AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24';OUT=EV/NAME;REPORT=EV/(NAME+'.md')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
assert not OUT.exists(),'append-only evidence already exists'
prior_name='AB_S3I_CANONICAL_RUNTIME_2026-10-24';prior=load(EV/prior_name/'manifest.json')
names=[row['name'] for row in prior['priorSeals']]+[prior_name]
assert len(names)==len(set(names))==44
seals=[];total=0
for name in names:
    p=EV/name/'manifest.json';d=load(p)
    for row in d['artifacts']:
        raw=(EV/name/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'].lower(),(name,row['path'])
        if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256'].lower()
    if d.get('reportSha256'):assert sha(EV/d['report'])==d['reportSha256'].lower()
    total+=len(d['artifacts']);seals.append(dict(name=name,artifacts=len(d['artifacts']),manifestSha256=sha(p)))
assert total==10219,total
bindings=load(W/'source_bindings_01.json')['sha256'];assert len(bindings)==172
assert all(sha(ROOT/name)==pin for name,pin in bindings.items())
assert load(W/'unchanged_verification_01.json')['acceptedPairsReplayed']==88
pin='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
for name in ('s3i_canonical.ACD','capacity_review.ACD','retention_control.ACD'):assert sha(W/name).upper()==pin
assert sha(W/'s3i_regenerated_01.L5X')==sha(W/'s3i_bench_05.L5X')==prior['sourceSha256']
assert load(W/'authorization.json')['CurrentOwnerApproved'] is False
for label in ('focused_05','ab_suite_01','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_02',
              'session_build_01','authorization_negative_01','unchanged_verification_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert b'Ran 2189 tests' in (W/'ab_suite_01.log').read_bytes()
assert load(W/'authorization_negative_01.json')['controllerAccess'] is False
OUT.mkdir()
def copy(source,relative,compress=False):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
    if compress:
        with source.open('rb') as input,target.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as packed:shutil.copyfileobj(input,packed)
    else:shutil.copyfile(source,target)
for source in sorted(W.rglob('*')):
    if not source.is_file() or any(part in ('bin','obj','__pycache__') for part in source.relative_to(W).parts):continue
    if source.name.startswith('package_preparation_01'):continue
    if source.suffix.lower() not in ('.json','.py','.cs','.csproj','.config','.log','.sha256','.l5x'):continue
    assert not any(token in source.name.lower() for token in ('credential','password','secret','dump'))
    copy(source,str(Path('Preparation')/source.relative_to(W))+('.gz' if source.suffix.lower()=='.l5x' else ''),source.suffix.lower()=='.l5x')
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
manifest=dict(schema='fraktal.ab.s3i-canonical-lifetime-preparation',schemaVersion=1,date='2026-10-24',
    timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    currentNativeSessionApproved=False,controllerAccess=False,controllerOperations=0,plcChanged=False,
    preparedAcdSha256=pin,sourceSha256=prior['sourceSha256'],sourceBindings=172,unchangedInheritedBindings=170,
    addedBindings=2,abTests=2189,rootTests=74,focusedTests=11,negativeCases=6,priorNativePairsReplayed=88,
    maxCalendarCommits=64,normalCalendarCommits=38,retainedProgramRunCycles=1,
    calendarRowsPrepared=7,retentionRowsPrepared=1,candidateRowsPrepared=41,baselineRowsPrepared=31,
    nativePublicationVectorsPerFirstScan=8,firstScanExecutionsPrepared=2,
    reusedExactImageCompileReadback=True,capacity=load(W/'capacity_review.json'),
    calendarLifetimeAccepted=False,retentionAccepted=False,stageAccepted=False,
    priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,artifactCount=len(artifacts),
    totalBytes=sum(row['bytes'] for row in artifacts))
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,reportSha256=sha(REPORT),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),priorRecords=len(seals),priorArtifacts=total,bytes=manifest['totalBytes'])))
