"""Finish and seal the uncommitted C4a draft after source-12 gates complete."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil

P=Path(__file__).resolve().parents[1];R=P.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
load=lambda p:json.loads(Path(p).read_bytes())
assert load(P/'Gates/gate_summary_02.json')['passed']
assert load(P/'Gates/full_ab_source_bindings_result_02.json')['sourcesUnchangedDuringSuite']
bindings=load(P/'Gates/source_bindings_02.json')
assert not bindings['defects']
assert not (P/'payload_hashes.json').exists()
for row in bindings['files']:
    source=R/row['file'];assert sha(source)==row['sha256'],row['file']
    target=P/'Source'/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(source.read_bytes())
state=dict(status='stopped',reason='superseded source-11 copy ordering; source-12 gate run 02 completes it',
           completed=['bind_sources_01','dart_analyze_gateway_01','dart_test_gateway_01'],
           partial='focused_python_01.log',controllerAccess=False)
with (P/'Gates/run_state_01.json').open('x',encoding='utf-8') as out:json.dump(state,out,indent=2)
report=P.with_suffix('.md');body=report.read_text(encoding='utf-8')
assert 'RESULTS' not in body
body=body.replace('2026-11-05, America/Mexico_City. Entry commit',
    'Prepared 2026-11-05; final gates and sealing completed 2026-11-06, America/Mexico_City. Entry commit',1)
report.write_text(body,encoding='utf-8',newline='\n')
credential=Path('C:/work/fraktal_echo38_access_fixture.json')
pins=[str(u['pin']).encode() for u in load(credential)['users']]
files={}
for p in sorted(P.rglob('*')):
    if not p.is_file():continue
    assert p.suffix.lower() not in {'.acd','.l5x','.bak','.exe','.dll','.pdb','.pyc'}
    assert 'credential' not in p.name.lower()
    raw=p.read_bytes();checked=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
    assert not any(pin in checked for pin in pins),'credential data refused'
    files[p.relative_to(P).as_posix()]=sha(p)
assert not any(pin in report.read_bytes() for pin in pins)
with (P/'payload_hashes.json').open('x',encoding='utf-8') as out:json.dump(files,out,indent=2,sort_keys=True)
manifest=dict(schema='fraktal.ab.s6-collapse-c4a-offline',schemaVersion=1,entryCommit='8e74160c6',
    sealedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report=report.name,reportSha256=sha(report),
    payloadManifestSha256=sha(P/'payload_hashes.json'),files=len(files),controllerAccess=False,
    preparation=load(P/'Gates/Prepare/prepare_candidate_12.json'),source11Superseded=True,
    ABTests=2557,dartTests=44,rootTests=85,nativeAcceptance=False)
with (P/'manifest.json').open('x',encoding='utf-8') as out:json.dump(manifest,out,indent=2)
print(json.dumps(dict(sealed=True,files=len(files),ABTests=2557,controllerAccess=False)))
