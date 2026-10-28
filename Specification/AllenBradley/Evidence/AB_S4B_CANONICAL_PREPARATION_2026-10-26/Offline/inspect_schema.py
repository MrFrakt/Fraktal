from collections import Counter
from pathlib import Path
import gzip,json
R=Path('C:/Users/SoftIndVM/Fraktal')
v=json.loads(gzip.decompress((R/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz').read_bytes()))['vectors'][-1]
paths=list(v['expected']['values']);roots=Counter(p.split('/')[1] for p in paths)
print(json.dumps(dict(rootChildren=roots,configPaths=[p for p in paths if any(k in p.lower() for k in ('cfg','configpage','parcfg','configpersist'))][:45]),indent=2))
