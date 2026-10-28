from pathlib import Path
import hashlib
import json
import shutil

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
H = R / 'FraktalCore/HMI'
OUT = W.parent / 'hmi_verify_01'
previous = json.loads((W / 'isolated_hmi_sources_03.json').read_bytes())
changed = [row['source'] for row in previous['files']
    if hashlib.sha256(Path(row['source']).read_bytes()).hexdigest() != row['sha256']]
assert set(changed) == {(H / 'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart').as_posix(),
                        (H / 'test/cip_read_plan_test.dart').as_posix()}, changed
rows = []
for row in previous['files']:
    source, target = Path(row['source']), Path(row['copy'])
    shutil.copyfile(source, target)
    assert source.read_bytes() == target.read_bytes()
    rows.append(dict(source=source.as_posix(), copy=target.as_posix(),
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(), bytes=source.stat().st_size))
probe = OUT / 'test/cip_schedule_profile_probe.dart'
destination = W / 'cip_schedule_profile_probe.dart'
assert probe.is_file() and not destination.exists()
shutil.copyfile(probe, destination)
assert probe.read_bytes() == destination.read_bytes()
probe.unlink()
with (W / 'isolated_hmi_sources_04.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(passed=True, files=rows, changes=changed, testProbeArchived=destination.as_posix()), stream, indent=2)
print(json.dumps(dict(passed=True, files=len(rows), changedInputs=changed, ownerGeneratedMapTouched=False)))
