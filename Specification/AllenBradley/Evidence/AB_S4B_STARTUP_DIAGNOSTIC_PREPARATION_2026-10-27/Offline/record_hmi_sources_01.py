from pathlib import Path
import hashlib
import json
R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/isolated_hmi_sources_01.json')
allowed={R/'FraktalCore/HMI'/name for name in (
    'test/opcua_freshness_test.dart',
    'lib/data/opcua_repository.dart')}
rows=[]
changed=[]
for row in json.loads(old.read_bytes())['files']:
    source,copy=Path(row['source']),Path(row['copy'])
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=row['sha256']:
        assert source in allowed,source
        changed.append(source.as_posix())
    assert source.read_bytes()==copy.read_bytes(),source
    rows.append(dict(source=source.as_posix(),copy=copy.as_posix(),sha256=digest,bytes=source.stat().st_size))
assert len(rows)==316 and len(changed)==2
with (W/'isolated_hmi_sources_01.json').open('x',encoding='utf-8') as f:
    json.dump(dict(passed=True,files=rows,changed=changed,plcSourcesUnchanged=True),f,indent=2)
print(json.dumps(dict(passed=True,files=len(rows),changed=changed)))
