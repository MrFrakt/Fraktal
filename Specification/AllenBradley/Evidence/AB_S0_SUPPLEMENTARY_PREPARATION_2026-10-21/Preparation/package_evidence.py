from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).resolve().parent
REPORT=ROOT/'Specification/AllenBradley/Evidence/AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21.md'
PAYLOAD=REPORT.with_suffix('')
for name in ('native_summary.json','offline_summary.json','closure_checks.json'):
    assert json.loads((WORK/name).read_text(encoding='utf-8'))['passed'],name
assert json.loads((WORK/'probe_prepared_compare.json').read_text(encoding='utf-8'))['Equivalent']
assert json.loads((WORK/'prepare_acd_audit.json').read_text(encoding='utf-8'))['Clean']
assert not PAYLOAD.exists(),'append-only payload exists'
PAYLOAD.mkdir()
artifacts=[]

def add(source, relative):
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
    if path.suffix.lower() in ('.json','.log','.py','.cs','.csproj','.md','.l5x','.sha256'):
        add(path,Path('Preparation')/relative)
tools=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
for name in ('fraktal_ab_s0_supplementary_probe.py','fraktal_ab_s0_supplementary_measure.py',
             'fraktal_ab_s0_supplementary_access.py','test_fraktal_ab_s0_supplementary.py',
             'fraktal_ab_s0_canonical_probe.py','fraktal_ab_s0_canonical_measure.py',
             'fraktal_ab_canonical_reader.py'):
    path=tools/name;add(path,Path('Source')/path.relative_to(ROOT))
for name in ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md','AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
             'AB_FROZEN_CONTRACTS_V2.json'):
    path=ROOT/'Specification/AllenBradley'/name;add(path,Path('Target')/name)
acd=WORK/'s0_probe.ACD';pin=(WORK/'probe.sha256').read_text().strip()
assert hashlib.sha256(acd.read_bytes()).hexdigest().upper()==pin
manifest=dict(schema='fraktal.ab.s0-supplementary-preparation-evidence',schemaVersion=1,
              sealedUtc=datetime.now(timezone.utc).isoformat(),report=REPORT.name,
              reportSha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
              preparedAcd=dict(path=str(acd),bytes=acd.stat().st_size,sha256=pin,archived=False),
              artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(row['bytes'] for row in artifacts),
              credentialsArchived=False,controllerChanges=0,downloadAuthorized=False)
with (PAYLOAD/'manifest.json').open('x',encoding='utf-8') as out:json.dump(manifest,out,indent=2);out.write('\n')
for row in artifacts:
    data=(PAYLOAD/row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    if row.get('compression'):
        assert hashlib.sha256(gzip.decompress(data)).hexdigest()==row['expandedSha256']
print(json.dumps(dict(payload=str(PAYLOAD),artifacts=len(artifacts),bytes=manifest['totalBytes'],allHashesVerified=True)))
