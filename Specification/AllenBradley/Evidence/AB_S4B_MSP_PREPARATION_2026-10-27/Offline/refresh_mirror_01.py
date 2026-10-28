"""Freeze all current HMI inputs and the explicit MSP changes over refill."""
from pathlib import Path
import hashlib
import json
import shutil

R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s4b-refill-20261027/offline_01/isolated_hmi_sources_01.json')
changed={H/p for p in ('packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
    'packages/fraktal_opcua_client/lib/src/cip_transport.dart',
    'packages/fraktal_opcua_client/lib/src/cip_read_pool.dart','test/cip_read_pool_test.dart')}
added={H/'test/cip_read_batch_test.dart'}
rows=[];seen=set()
for row in json.loads(old.read_bytes())['files']:
    path=Path(row['source']);copy=Path(row['copy']);digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=row['sha256']:
        assert path in changed,path
        seen.add(path)
    shutil.copyfile(path,copy)
    rows.append(dict(source=path.as_posix(),copy=copy.as_posix(),sha256=digest,bytes=path.stat().st_size))
assert seen==changed
for path in added:
    copy=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01')/path.relative_to(H)
    shutil.copyfile(path,copy)
    rows.append(dict(source=path.as_posix(),copy=copy.as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,files=rows,changed=[p.as_posix() for p in sorted(changed)],added=[p.as_posix() for p in sorted(added)]),f,indent=2)
print(json.dumps(dict(files=len(rows),changed=len(changed),added=len(added))))
