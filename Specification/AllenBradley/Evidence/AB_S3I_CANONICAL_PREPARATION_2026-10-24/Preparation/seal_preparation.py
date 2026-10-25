"""Append-only S3i preparation payload; verify the complete predecessor chain."""
from datetime import datetime,timezone
from pathlib import Path
import gzip
import hashlib
import json
import shutil

ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;EV=ROOT/'Specification/AllenBradley/Evidence'
NAME='AB_S3I_CANONICAL_PREPARATION_2026-10-24';OUT=EV/NAME;REPORT=EV/(NAME+'.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists(),'append-only: preparation already sealed'
prior_name='AB_S3I_CANONICAL_INVENTORY_2026-10-24'
inventory=json.loads((EV/prior_name/'manifest.json').read_text(encoding='utf-8'))
names=[s['name'] for s in inventory['priorSeals']]+[prior_name]
assert len(names)==len(set(names))==42
seals=[];total=0
for name in names:
    p=EV/name/'manifest.json';d=json.loads(p.read_text(encoding='utf-8'))
    for row in d['artifacts']:
        artifact=EV/name/row['path'];raw=artifact.read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'].lower(),(name,row['path'])
        if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==row['expandedSha256'].lower()
    if d.get('reportSha256'):assert sha(EV/d['report'])==d['reportSha256'].lower(),name
    total+=len(d['artifacts']);seals.append(dict(name=name,artifacts=len(d['artifacts']),manifestSha256=sha(p)))
assert total==9415,total

bindings=json.loads((W/'source_bindings_01.json').read_text())['sha256']
assert len(bindings)==170 and all(sha(ROOT/name)==pin.lower() for name,pin in bindings.items())
required=('ab_suite_02','root_tests_02','ab_spec_02','ab_contracts_02','consistency_02','whitespace_02',
    'native_bench_echo_05','native_physical_05','echo_readback_05','physical_readback_05','prepared_readback_01',
    'prepared_access_01','echo_access_05','physical_access_05','helper_build_03','session_build_01','prepare_acd_01',
    'source_compatibility_01','compatibility_01','prepared_audits_02','capacity_auto_01','authorization_negative_01')
for label in required:assert json.loads((W/(label+'_exit.json')).read_text())['exitCode']==0,label
assert b'Ran 2178 tests' in (W/'ab_suite_02.log').read_bytes()
pin=(W/'canonical.sha256').read_text().strip()
assert sha(W/'s3i_canonical.ACD').upper()==sha(W/'capacity_review.ACD').upper()==pin=='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42'
assert sha(W/'s3i_bench_05.L5X').upper()=='0F3A5F6DD762BED3819404025DAF6D5703511807B440C4988EACF5E494EC72C3'
auth=json.loads((W/'authorization.json').read_text());assert auth['CurrentOwnerApproved'] is False and auth['NativeLineVectorsAuthorized'] is False
capacity=json.loads((W/'capacity_review.json').read_text());assert capacity['VerifiedFit'] and capacity['UsedStandardBlocks']==2763512

OUT.mkdir()
def copy(source,relative,compress=False):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
    if compress:
        with source.open('rb') as input,target.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as packed:shutil.copyfileobj(input,packed)
    else:shutil.copyfile(source,target)

# All small work artifacts and every failed/generated L5X; no vendor images,
# binary dependencies, credentials, persistence medium or dumps.
for source in sorted(W.rglob('*')):
    if not source.is_file() or any(part in ('bin','obj','__pycache__') for part in source.relative_to(W).parts):continue
    if source.name.startswith('seal_preparation_02'):continue  # active seal stdout is not yet complete
    if source.suffix.lower() not in ('.py','.cs','.csproj','.config','.json','.log','.sha256','.l5x'):continue
    assert not any(token in source.name.lower() for token in ('credential','password','secret','dump'))
    relative=Path('Preparation')/source.relative_to(W)
    copy(source,str(relative)+('.gz' if source.suffix.lower()=='.l5x' else ''),source.suffix.lower()=='.l5x')
for name in sorted(bindings):copy(ROOT/name,str(Path('Source')/name)+'.gz',True)

contract_names=['AGENTS.md','Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md',
    'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md',
    'Specification/AllenBradley/AB_CAPACITY_OBSERVATIONS_2026-10-21.json',
    'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/ST_LineStatus.TcDUT',
    'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/ST_ShiftRecordV3.TcDUT',
    'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL']
for name in contract_names:copy(ROOT/name,str(Path('Contract')/name))
with (OUT/'contract_bindings.json').open('x') as f:json.dump({name:sha(ROOT/name) for name in contract_names},f,indent=2)

artifacts=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();row=dict(path=p.relative_to(OUT).as_posix(),sha256=sha(p),bytes=len(raw))
        if p.suffix=='.gz':row['expandedSha256']=hashlib.sha256(gzip.decompress(raw)).hexdigest()
        artifacts.append(row)
manifest=dict(schema='fraktal.ab.s3i-canonical-preparation-evidence',schemaVersion=1,date='2026-10-24',
    sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,reportSha256=sha(REPORT),
    ownerContractApproved=True,currentNativeSessionApproved=False,controllerAccess=False,controllerOperations=0,
    runtimeAccepted=False,sourceSha256=sha(W/'s3i_bench_05.L5X'),preparedAcdSha256=pin,sourceBindings=170,
    abTests=2178,rootTests=74,readbackBodies=58,readbackInitialValues=43648,nativeVectorsPrepared=8,
    candidateCasesPrepared=41,baselineCasesPrepared=31,calendarProducerLifetimeAccepted=False,
    capacity=capacity,priorSeals=seals,priorArtifactCount=total,artifacts=artifacts,
    artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts))
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,reportSha256=sha(REPORT),manifestSha256=sha(OUT/'manifest.json'),
    artifacts=len(artifacts),priorRecords=len(seals),priorArtifacts=total,bytes=manifest['totalBytes'])))
