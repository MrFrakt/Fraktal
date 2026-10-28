from pathlib import Path
import hashlib,json
W=Path(__file__).parent
old=json.loads((W/'isolated_hmi_sources_01.json').read_bytes())
allowed={'cip_read_pool.dart','cip_read_pool_test.dart'}
for row in old['files']:
    source,copy=Path(row['source']),Path(row['copy'])
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=row['sha256']:assert source.name in allowed,source
    assert source.read_bytes()==copy.read_bytes(),source
    row.update(sha256=digest,bytes=source.stat().st_size)
with (W/'isolated_hmi_sources_02.json').open('x',encoding='utf-8') as f:json.dump(old,f,indent=2)
print(json.dumps(dict(passed=True,files=len(old['files']),changed=4,added=2)))
