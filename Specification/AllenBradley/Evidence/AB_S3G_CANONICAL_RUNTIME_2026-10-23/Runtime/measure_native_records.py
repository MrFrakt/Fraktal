"""Offline measurement from the generic acquisition's actual Template sizes."""
from pathlib import Path
import gzip,hashlib,json
R=Path(__file__).parent;path=R/'generic_capture_01.json.gz'
capture=json.loads(gzip.decompress(path.read_bytes()))
templates={t['handle']:t for t in capture['templates']};symbols={s['name']:s for s in capture['symbols']}
rows=[]
for record in capture['records']:
    template=templates[symbols[record['tag']]['handle']];raw=bytes.fromhex(record['rawHex'])
    assert len(raw)==template['byteSize']
    rows.append(dict(tag=record['tag'],template=template['name'],nativeTemplateBytes=template['byteSize'],
        rawPayloadBytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert len(rows)==3
report=dict(passed=True,readOnly=True,controllerAccess=False,captureSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    records=rows,totalPayloadBytes=sum(row['rawPayloadBytes'] for row in rows),unit='bytes')
with (R/'native_record_sizes_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
