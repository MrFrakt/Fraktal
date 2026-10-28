from pathlib import Path
import gzip,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
doc=json.loads(gzip.decompress((R/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz').read_bytes()))
fixture=doc['vectors'][-1];values=fixture['expected']['values']
print(json.dumps(dict(vector=fixture['name'],historyByClassLeaves=sum('/Profiler/History[' in p and '/ByClass[' in p for p in values),
 historyCounts={p:v for p,v in values.items() if p.endswith('/Profiler/HistoryCount')})))
