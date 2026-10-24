from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
WORK=Path(__file__).resolve().parent
REPORT=ROOT/'Specification/AllenBradley/Evidence/AB_S1_CANONICAL_READER_2026-10-20.md'
PAYLOAD=REPORT.with_suffix('')

for path in (WORK/'Final/offline_summary.json',WORK/'native_summary.json',
             WORK/'Final/final_summary.json',WORK/'post_docs_summary.json',
             WORK/'replay_summary.json',WORK/'source_checks.json'):
    if not json.loads(path.read_text(encoding='utf-8'))['passed']:
        raise SystemExit(f'gate failed: {path}')
if PAYLOAD.exists():
    raise SystemExit('append-only payload exists')
PAYLOAD.mkdir()

def copy(source, relative):
    destination=PAYLOAD/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())

for path in sorted(WORK.rglob('*')):
    if path.is_file() and path.suffix.lower() in ('.json','.log','.py','.l5x'):
        copy(path,Path('Run')/path.relative_to(WORK))
tools=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
for name in ('fraktal_ab_canonical_reader.py','fraktal_ab_canonical_equivalence.py',
             'fraktal_ab_projection_replay.py','fraktal_ab_s0_canonical_measure.py',
             'fraktal_ab_s0_canonical_probe.py','test_fraktal_ab_canonical_reader.py',
             'test_fraktal_ab_s0_canonical_probe.py'):
    copy(tools/name,Path('Source')/(tools/name).relative_to(ROOT))
for path in (tools/'fixtures/canonical').iterdir():
    if path.is_file():copy(path,Path('Source')/path.relative_to(ROOT))
for name in ('AB_FROZEN_CONTRACTS_V2.json',
             'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md',
             'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
             'AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md'):
    path=ROOT/'Specification/AllenBradley'/name
    copy(path,Path('ApprovedTarget')/name)

artifacts=[]
for path in sorted(PAYLOAD.rglob('*')):
    if path.is_file():
        data=path.read_bytes()
        artifacts.append(dict(path=path.relative_to(PAYLOAD).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(schema='fraktal.ab.s1-evidence',schemaVersion=1,
              sealedUtc=datetime.now(timezone.utc).isoformat(),
              report=REPORT.name,reportSha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),
              artifacts=artifacts,artifactCount=len(artifacts),totalBytes=sum(r['bytes'] for r in artifacts),
              credentialsArchived=False,controllerChanges=0)
with (PAYLOAD/'manifest.json').open('x',encoding='utf-8') as stream:
    json.dump(manifest,stream,indent=2)
    stream.write('\n')
for row in artifacts:
    assert hashlib.sha256((PAYLOAD/row['path']).read_bytes()).hexdigest()==row['sha256']
print(json.dumps(dict(payload=str(PAYLOAD),artifactCount=len(artifacts),totalBytes=manifest['totalBytes'],hashesVerified=True)))
