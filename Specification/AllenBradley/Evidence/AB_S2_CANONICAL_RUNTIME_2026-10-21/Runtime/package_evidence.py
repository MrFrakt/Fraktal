from datetime import datetime,timezone
import json,gzip,hashlib
from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal');RUNTIME=Path(__file__).parent
WORK=Path('C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5')
REPORT=ROOT/'Specification/AllenBradley/Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md'
PAYLOAD=REPORT.with_suffix('')
closure=json.loads((RUNTIME/'runtime_closure.json').read_text());assert closure['passed']
checks={name:json.loads((RUNTIME/(name+'_exit.json')).read_text())['exitCode']==0 for name in ['spec_01','contracts_01','consistency_01','root_suite_01','diff_01']};assert all(checks.values())
prior=[]
for name in ['AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20','AB_S0_CANONICAL_TYPES_2026-10-20','AB_S1_CANONICAL_READER_2026-10-20','AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21','AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21','AB_S2_CANONICAL_PREPARATION_2026-10-21']:
    folder=REPORT.parent/name;m=json.loads((folder/'manifest.json').read_text())
    if m.get('reportSha256'):assert hashlib.sha256((folder.parent/m['report']).read_bytes()).hexdigest().lower()==m['reportSha256'].lower()
    for a in m['artifacts']:
        b=(folder/a['path']).read_bytes();assert hashlib.sha256(b).hexdigest().lower()==a['sha256'].lower()
        if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(b)).hexdigest().lower()==a['expandedSha256'].lower()
    prior.append(dict(record=name,artifacts=len(m['artifacts']),verified=True))
assert not PAYLOAD.exists();PAYLOAD.mkdir()
artifacts=[]
def add(p,relative):
    assert p.suffix.lower()!='.acd'
    raw=p.read_bytes();compressed=p.suffix.lower()=='.l5x' and len(raw)>200000
    stored=gzip.compress(raw,compresslevel=9,mtime=0) if compressed else raw
    destination=PAYLOAD/(str(relative)+'.gz' if compressed else relative);destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as f:f.write(stored)
    a=dict(path=destination.relative_to(PAYLOAD).as_posix(),bytes=len(stored),sha256=hashlib.sha256(stored).hexdigest())
    if compressed:a.update(expandedBytes=len(raw),expandedSha256=hashlib.sha256(raw).hexdigest(),compression='gzip mtime 0')
    artifacts.append(a)
for p in sorted(RUNTIME.rglob('*')):
    rel=p.relative_to(RUNTIME)
    if not p.is_file() or any(x in ('bin','obj','__pycache__') for x in rel.parts):continue
    if p.suffix.lower() in ('.py','.cs','.csproj','.json','.log','.md','.l5x','.sha256','.gz'):add(p,Path('Runtime')/rel)
for name in ['authorization.json','capacity_review.json','backup.sha256','canonical.sha256','deploy_attempt.json','echo_before_s2.L5X','canonical_downloaded.L5X','genealogy_restored.L5X']:
    add(WORK/name,Path('Session')/name)
tools=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
for name in ['fraktal_ab_declaration.py','fraktal_ab_generate.py','fraktal_ab_canonical_publication.py','fraktal_ab_canonical_manifest.py','fraktal_ab_canonical_reader.py','fraktal_ab_canonical_equivalence.py','fraktal_ab_canonical_acquire.py','fraktal_ab_genealogy_canonical_demo.py','fraktal_ab_s2_equivalence.py','test_fraktal_ab_canonical_publication.py','fraktal_ab_access_audit.py','fraktal_ab_readback.py','fraktal_ab_sdk_log_gate.py','fraktal_ab_genealogy_execute.py','fraktal_ab_part_execute.py','fraktal_ab_tower_execute.py']:
    add(tools/name,Path('Source')/name)
for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md','AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md','AB_FROZEN_CONTRACTS_V2.json']:
    add(ROOT/'Specification/AllenBradley'/name,Path('Target')/name)
m=dict(schema='fraktal.ab.s2-canonical-runtime-evidence',schemaVersion=1,date='2026-10-21',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,reportSha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(a['bytes'] for a in artifacts),runtimeAccepted=True,publicationStage=2,acceptedPaths=46,regressionRows=62,extraRecoveryRegressionRows=0,recordedDownloads=3,recordedModeChanges=5,faultClears=0,priorSeals=prior,statusDocumentGates=checks,nativeAcdFilesArchived=False,credentialFilesArchived=False)
with (PAYLOAD/'manifest.json').open('x',encoding='utf-8') as f:json.dump(m,f,indent=2)
for a in artifacts:
    data=(PAYLOAD/a['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==a['sha256']
    if a.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(data)).hexdigest()==a['expandedSha256']
print(json.dumps(dict(payload=str(PAYLOAD),artifacts=len(artifacts),bytes=m['totalBytes'],priorSealsVerified=len(prior),priorArtifactsVerified=sum(p['artifacts'] for p in prior),allHashesVerified=True)))
