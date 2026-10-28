"""Hash-verified native captures and independent logical/header decoder goldens."""
from pathlib import Path
import gzip,hashlib,json,struct,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_reader as reader
E=R/'Specification/AllenBradley/Evidence';vectors=[]
for name in ('AB_S3K_CANONICAL_RUNTIME_2026-10-25','AB_PRESS_S3_EXIT_RUNTIME_2026-10-25','AB_S4A_COHERENCE_RUNTIME_2026-10-25'):
    folder=E/name;seal=json.loads((folder/'manifest.json').read_bytes())
    item=next(r for r in seal['artifacts'] if r['path'].endswith('generic_capture.json.gz'))
    raw=(folder/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
    capture=json.loads(gzip.decompress(raw));expected=reader.snapshot(capture)
    objects,sizes=reader.template_objects(capture['templates']);m=capture['manifest']
    header={'Magic':0x46524b36,'SchemaMajor':6,'SchemaMinor':m['schemaMinor'],'PublicationStage':m['publicationStage'],
        'Valid':True,'Truncated':False,'ContentHash':m['contentHash'],'ConfigRevision':m['configRevision'],
        'LegacyContentHash':m['legacyContentHash'],'FragmentRevision':m['fragmentRevision']}
    for physical,normalized in [('TypeAnnotations','typeAnnotations'),('PathExceptions','pathExceptions'),
        ('Bindings','bindings'),('Services','services'),('DataProducts','dataProducts'),
        ('CommandBindings','commandBindings'),('CommandOperations','commandOperations'),('ReadCoherenceBindings','readCoherenceBindings')]:
        if normalized not in m:continue
        rows=m[normalized];header[physical+'Count']=header[physical+'Capacity']=len(rows)
        if rows:header[physical]=rows
    handle=next(t['handle'] for t in capture['templates'] if {'Magic','TypeAnnotations','ContentHash'}<={r['name'] for r in t['members']})
    def encode(value,handle):
        out=bytearray(sizes[handle]);members=reader.member_table(objects[handle]);width=reader.is_string(members)
        if width is not None:
            raw=value.encode();assert len(raw)<=width
            struct.pack_into('<i',out,next(r['offset'] for r in members if r['name']=='LEN'),len(raw))
            at=next(r['offset'] for r in members if r['name']=='DATA');out[at:at+len(raw)]=raw;return out
        for row in members:
            if row['name'].startswith('ZZZZZZZZZZ'):continue
            child=value[row['name']];at=row['offset'];items=child if row['array'] else [child]
            if row['struct']:
                assert len(items)==(row['info'] if row['array'] else 1)
                for index,item in enumerate(items):
                    data=encode(item,row['handle']);start=at+index*len(data);out[start:start+len(data)]=data
            elif row['atomic']==0xc1:
                assert not row['array']
                if child:out[at+row['info']//8]|=1<<(row['info']%8)
            else:
                assert row['atomic']==0xc4 and not row['array'];struct.pack_into('<i',out,at,child)
        return out
    physical=encode(header,handle)
    import fraktal_ab_canonical_manifest as wire
    assert wire.normalize(reader.decode_record(physical,handle,capture['templates']))==m
    vectors.append(dict(name=name,capture=capture,expected=expected,
        sourceSha256=item['sha256'],source=(folder/item['path']).relative_to(R).as_posix(),
        physicalManifest=dict(handle=handle,rawHex=physical.hex(),
            provenance='Reconstructed test input from accepted Template offsets and normalized manifest; not captured native header bytes')))
path=R/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz'
raw=json.dumps(dict(schema='fraktal.cip.publication-goldens.v1',vectors=vectors),separators=(',',':'),allow_nan=False).encode()
with path.open('xb') as stream:stream.write(gzip.compress(raw,mtime=0))
report=dict(passed=True,vectors=len(vectors),paths=[len(v['expected']['values']) for v in vectors],
    fixtureSha256=hashlib.sha256(path.read_bytes()).hexdigest(),controllerAccess=False)
with (W/'goldens_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
print(json.dumps(dict(configPaths=[p for p in vectors[-1]['expected']['values'] if any(k in p for k in ('CfgManifest','ConfigDescription','ConfigItems','ParCfg'))][:32])))
