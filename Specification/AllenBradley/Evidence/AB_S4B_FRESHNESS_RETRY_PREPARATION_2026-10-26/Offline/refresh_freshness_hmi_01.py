from pathlib import Path
import hashlib
import json
import shutil

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
H = R / 'FraktalCore/HMI'
previous = json.loads((W / 'isolated_hmi_sources_05.json').read_bytes())
changed = [row['source'] for row in previous['files']
    if hashlib.sha256(Path(row['source']).read_bytes()).hexdigest() != row['sha256']]
expected = {'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
            'packages/fraktal_opcua_client/lib/src/cip_session_client.dart',
            'test/cip_read_plan_test.dart', 'test/cip_qualification_test.dart',
            'tool/qualify_cip_canonical.dart'}
assert set(changed) == {(H / name).as_posix() for name in expected}, changed
rows = []
for row in previous['files']:
    source, target = Path(row['source']), Path(row['copy'])
    shutil.copyfile(source, target)
    assert source.read_bytes() == target.read_bytes()
    rows.append(dict(source=source.as_posix(), copy=target.as_posix(),
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(), bytes=source.stat().st_size))
with (W / 'isolated_hmi_sources_06.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(passed=True, files=rows, changes=changed, ownerGeneratedMapTouched=False), stream, indent=2)
print(json.dumps(dict(passed=True, files=len(rows), changedInputs=changed)))
