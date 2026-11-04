from pathlib import Path
import gzip,json
R=Path('C:/Users/SoftIndVM/Fraktal')
for name in ('cip_owner_apparatus_v610.json.gz','cip_publication_goldens.json.gz'):
    path=R/'FraktalCore/HMI/test/fixtures'/name
    value=json.loads(gzip.decompress(path.read_bytes()))
    print(json.dumps(dict(file=name,keys=list(value),schema=value.get('schema'),
        provenance=value.get('provenance'),synthetic=value.get('synthetic'),
        vectors=[dict(name=r.get('name'),keys=list(r)) for r in value.get('vectors',[])],
        manifestMinor=value.get('manifest',{}).get('schemaMinor'))))
