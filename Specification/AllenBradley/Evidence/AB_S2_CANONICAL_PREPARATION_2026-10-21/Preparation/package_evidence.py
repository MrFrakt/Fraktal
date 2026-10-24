from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).resolve().parent
REPORT=ROOT/'Specification/AllenBradley/Evidence/AB_S2_CANONICAL_PREPARATION_2026-10-21.md'
PAYLOAD=REPORT.with_suffix('')
assert json.loads((WORK/'closure_checks.json').read_text())['passed']
assert not PAYLOAD.exists(), 'Append-only payload exists'
PAYLOAD.mkdir()
artifacts=[]


def add(source, relative):
    assert source.suffix.lower()!='.acd'
    raw=source.read_bytes()
    compress=source.suffix.lower()=='.l5x' and len(raw)>200000
    stored=gzip.compress(raw,compresslevel=9,mtime=0) if compress else raw
    destination=PAYLOAD/(str(relative)+'.gz' if compress else relative)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as out:out.write(stored)
    row=dict(path=destination.relative_to(PAYLOAD).as_posix(),bytes=len(stored),sha256=hashlib.sha256(stored).hexdigest())
    if compress:row.update(expandedBytes=len(raw),expandedSha256=hashlib.sha256(raw).hexdigest(),compression='gzip mtime 0')
    artifacts.append(row)


for path in sorted(WORK.rglob('*')):
    relative=path.relative_to(WORK)
    if not path.is_file() or any(segment in ('bin','obj','__pycache__') for segment in relative.parts):continue
    if path.suffix.lower() in ('.json','.log','.py','.cs','.csproj','.md','.l5x','.sha256','.gz'):
        add(path,Path('Preparation')/relative)
tools=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
for name in ('fraktal_ab_declaration.py','fraktal_ab_generate.py','fraktal_ab_canonical_publication.py',
             'fraktal_ab_canonical_manifest.py','fraktal_ab_canonical_reader.py','fraktal_ab_canonical_equivalence.py',
             'fraktal_ab_canonical_acquire.py','fraktal_ab_genealogy_canonical_demo.py','fraktal_ab_s2_equivalence.py',
             'test_fraktal_ab_canonical_publication.py','fraktal_ab_access_audit.py','fraktal_ab_readback.py',
             'fraktal_ab_sdk_log_gate.py'):
    add(tools/name,Path('Source')/name)
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md','AB_FROZEN_CONTRACTS_V2.json'):
    add(ROOT/'Specification/AllenBradley'/name,Path('Target')/name)
manifest=dict(schema='fraktal.ab.s2-canonical-preparation-evidence',schemaVersion=1,
              date='2026-10-21',timeZone='America/Mexico_City',sealedUtc=datetime.now(timezone.utc).isoformat(),
              report=REPORT.name,reportSha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
              artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(row['bytes'] for row in artifacts),
              nativeAcdFilesArchived=False,credentialFilesArchived=False,controllerChanges=0,
              currentS2Authorization=False,capacityPending=True,runtimeAccepted=False)
with (PAYLOAD/'manifest.json').open('x',encoding='utf-8') as out:json.dump(manifest,out,indent=2);out.write('\n')
for row in artifacts:
    data=(PAYLOAD/row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    if row.get('expandedSha256'):assert hashlib.sha256(gzip.decompress(data)).hexdigest()==row['expandedSha256']
print(json.dumps(dict(payload=str(PAYLOAD),artifacts=len(artifacts),bytes=manifest['totalBytes'],allHashesVerified=True)))
