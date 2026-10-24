from datetime import datetime,timezone
import gzip,hashlib,json
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal');WORK=Path(__file__).parent
REPORT=ROOT/'Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md'
PAYLOAD=REPORT.with_suffix('')
closure=json.loads((WORK/'closure_checks_final.json').read_text());assert closure['passed'] and all(closure['checks'].values())
assert not PAYLOAD.exists();PAYLOAD.mkdir()
artifacts=[]
def add(source,relative):
    assert source.suffix.lower()!='.acd'
    raw=source.read_bytes();compress=source.suffix.lower()=='.l5x' and len(raw)>200000
    stored=gzip.compress(raw,compresslevel=9,mtime=0) if compress else raw
    destination=PAYLOAD/(str(relative)+'.gz' if compress else relative);destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as out:out.write(stored)
    row=dict(path=destination.relative_to(PAYLOAD).as_posix(),bytes=len(stored),sha256=hashlib.sha256(stored).hexdigest())
    if compress:row.update(expandedBytes=len(raw),expandedSha256=hashlib.sha256(raw).hexdigest(),compression='gzip mtime 0')
    artifacts.append(row)
for source in sorted(WORK.rglob('*')):
    relative=source.relative_to(WORK)
    if not source.is_file() or any(p in ('bin','obj','__pycache__') for p in relative.parts):continue
    if source.suffix.lower() in ('.json','.log','.py','.cs','.csproj','.md','.l5x','.sha256','.gz'):
        add(source,Path('Preparation')/relative)
tools=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
for name in ['fraktal_ab_declaration.py','fraktal_ab_generate.py','fraktal_ab_canonical_manifest.py','fraktal_ab_canonical_reader.py','fraktal_ab_canonical_publication.py','fraktal_ab_canonical_unit_core.py','fraktal_ab_canonical_equivalence.py','fraktal_ab_canonical_acquire.py','fraktal_ab_genealogy_canonical_demo.py','fraktal_ab_genealogy_s3a_demo.py','fraktal_ab_s2_equivalence.py','fraktal_ab_s3a_equivalence.py','fraktal_ab_s3a_fixture_execute.py','fraktal_ab_genealogy_execute.py','fraktal_ab_part_execute.py','fraktal_ab_tower_execute.py','fraktal_ab_models.py','fraktal_ab_access_audit.py','fraktal_ab_readback.py','fraktal_ab_sdk_log_gate.py','test_fraktal_ab_canonical_array_views.py','test_fraktal_ab_canonical_unit_core.py','test_fraktal_ab_canonical_publication.py','test_fraktal_ab_canonical_reader.py','test_fraktal_ab_s3a_fixture.py']:
    add(tools/name,Path('Source')/name)
add(ROOT/closure['coreCapacitySource']['path'],Path('Engineering')/'PL_Fraktal.TcGVL')
for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md','AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md','AB_CANONICAL_PUBLICATION_S3A_NOTES_2026-10-21.md','AB_CANONICAL_PUBLICATION_S3A_INVENTORY_2026-10-21.json','AB_FROZEN_CONTRACTS_V2.json']:
    add(ROOT/'Specification/AllenBradley'/name,Path('Target')/name)
references=[]
for name in ['s3a_canonical.ACD','capacity_review.ACD']:
    p=WORK/name;references.append(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
m=dict(schema='fraktal.ab.s3a-canonical-preparation-evidence',schemaVersion=1,date='2026-10-21',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,reportSha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),sourceCommit='a1163c7c7bec21988167bc971145b1366206e9ce',artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),nativeAcdFilesArchived=False,credentialFilesArchived=False,nativeArtifactReferences=references,controllerChanges=0,runtimeAccepted=False,currentAuthorizationPending=True,capacityPending=True,expectedCurrentPaths=94,proposedRegressionRows=62,proposedAdditionalReadOnlyDecisionPairs=4,priorSeals=closure['priorSeals'])
with (PAYLOAD/'manifest.json').open('x',encoding='utf-8') as out:json.dump(m,out,indent=2)
for a in artifacts:
    raw=(PAYLOAD/a['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['sha256']
    if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==a['expandedSha256']
assert hashlib.sha256(REPORT.read_bytes()).hexdigest()==m['reportSha256']
print(json.dumps(dict(payload=str(PAYLOAD),artifacts=len(artifacts),bytes=m['totalBytes'],allHashesVerified=True,preparedAcdSha256=closure['preparedAcdSha256'])))
