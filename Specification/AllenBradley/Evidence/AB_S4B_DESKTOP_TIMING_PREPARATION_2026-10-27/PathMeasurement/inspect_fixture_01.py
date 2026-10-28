from pathlib import Path
import gzip,json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
for filename in ('cip_publication_goldens.json.gz','cip_read_view_goldens.json.gz'):
    doc=json.loads(gzip.decompress((R/'FraktalCore/HMI/test/fixtures'/filename).read_bytes()))
    vector=doc['vectors'][-1];capture=vector['capture']
    print(json.dumps(dict(file=filename,vector=vector['name'],keys=list(capture),
      manifestNames=[r for r in capture['symbols'] if 'manifest' in r['name'].lower()],
      recordTags=[r['tag'] for r in capture['records']],
      firstTemplateKeys=list(capture['templates'][0]))))
