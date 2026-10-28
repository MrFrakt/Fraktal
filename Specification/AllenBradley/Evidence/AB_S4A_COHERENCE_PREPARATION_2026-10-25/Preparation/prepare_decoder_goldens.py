"""Physical Dart decoder vectors from two hash-verified native acceptance captures."""
from pathlib import Path
import gzip,hashlib,json,sys

ROOT=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_reader as reader

E=ROOT/'Specification/AllenBradley/Evidence'
vectors=[]
for name in ('AB_S3K_CANONICAL_RUNTIME_2026-10-25','AB_PRESS_S3_EXIT_RUNTIME_2026-10-25'):
    folder=E/name
    manifest=json.loads((folder/'manifest.json').read_bytes())
    artifacts=[a for a in manifest['artifacts'] if 'generic_capture' in a['path'] and a['path'].endswith('.json.gz')]
    assert len(artifacts)==1,(name,[a['path'] for a in artifacts])
    artifact=artifacts[0];path=folder/artifact['path'];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==artifact['sha256'].lower()
    capture=json.loads(gzip.decompress(raw));objects,sizes=reader.template_objects(capture['templates'])
    symbols={s['name']:s for s in capture['symbols']}
    def normalize(value,handle):
        rows=reader.member_table(objects[handle])
        if reader.is_string(rows) is not None:return bytes.fromhex(value['bytes']).decode('utf-8')
        output={}
        for row in rows:
            key=row['name']
            if key.startswith('ZZZZZZZZZZ'):continue
            item=value[key]
            if row['struct']:
                output[key]=[normalize(x,row['handle']) for x in item] if row['array'] else normalize(item,row['handle'])
            elif row['atomic']==0xc1 and row['array']:
                output[key]=[i in item for i in range(row['info'])]
            elif row['atomic'] in (0xc5,0xc9,0xc0,0xcc,0xd7,0xdf):
                output[key]=[str(x) for x in item] if row['array'] else str(item)
            else:output[key]=item
        return output
    records=[]
    for row in capture['records']:
        handle=symbols[row['tag']]['handle']
        decoded=reader.decode_record(bytes.fromhex(row['rawHex']),handle,capture['templates'])
        records.append(dict(tag=row['tag'],handle=handle,rawHex=row['rawHex'],expected=normalize(decoded,handle)))
    vectors.append(dict(name=name,source=path.relative_to(ROOT).as_posix(),sourceSha256=artifact['sha256'],
                        templates=capture['templates'],records=records))
output=ROOT/'FraktalCore/HMI/test/fixtures/cip_template_goldens.json.gz'
data=json.dumps(dict(schema='fraktal.cip.template-goldens.v1',vectors=vectors),separators=(',',':'),allow_nan=False).encode()
with output.open('xb') as stream:stream.write(gzip.compress(data,mtime=0))
result=dict(passed=True,sources=2,records=sum(len(v['records']) for v in vectors),expandedBytes=len(data),
            fixtureSha256=hashlib.sha256(output.read_bytes()).hexdigest(),controllerAccess=False)
with (Path(__file__).parent/'decoder_goldens_01.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
