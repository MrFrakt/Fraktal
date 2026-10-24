from pathlib import Path
import gzip,hashlib,json
R=Path(__file__).parent;p=R/'generic_capture_01.json.gz'
c=json.loads(gzip.decompress(p.read_bytes()))
templates={t['handle']:t for t in c['templates']};symbols={s['name']:s for s in c['symbols']};rows=[]
for record in c['records']:
 t=templates[symbols[record['tag']]['handle']];raw=bytes.fromhex(record['rawHex']);assert len(raw)==t['byteSize']
 rows.append(dict(tag=record['tag'],template=t['name'],nativeTemplateBytes=t['byteSize'],rawPayloadBytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert len(rows)==3
report=dict(passed=True,readOnly=True,controllerAccess=False,captureSha256=hashlib.sha256(p.read_bytes()).hexdigest(),records=rows,totalPayloadBytes=sum(row['rawPayloadBytes'] for row in rows),unit='bytes')
assert report['totalPayloadBytes']==133156
with (R/'native_record_sizes_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
