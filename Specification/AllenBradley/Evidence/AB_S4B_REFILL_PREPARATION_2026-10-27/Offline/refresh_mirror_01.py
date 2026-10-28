"""Verify and refresh the two changed inputs in the pinned HMI mirror."""
from pathlib import Path
import hashlib
import json
import shutil

R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI';W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/offline_01/isolated_hmi_sources_01.json')
changed={H/'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',H/'test/cip_read_pool_test.dart'}
rows=[];seen=set()
for row in json.loads(old.read_bytes())['files']:
    path=Path(row['source']);target=Path(row['copy'])
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=row['sha256']:
        assert path in changed,path
        seen.add(path)
    shutil.copyfile(path,target)
    rows.append(dict(source=path.as_posix(),copy=target.as_posix(),sha256=digest,bytes=path.stat().st_size))
assert seen==changed and len(rows)==319
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,files=rows,changed=[p.as_posix() for p in sorted(changed)],added=[]),stream,indent=2)
print(json.dumps(dict(files=len(rows),changed=len(changed),added=0)))
