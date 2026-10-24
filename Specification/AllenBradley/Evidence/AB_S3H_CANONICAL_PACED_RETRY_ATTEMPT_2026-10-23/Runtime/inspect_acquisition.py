from pathlib import Path
import collections,gzip,json,sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from fraktal_ab_canonical_equivalence import compare_documents
from fraktal_ab_canonical_reader import snapshot
R=Path(__file__).parent;rows=[]
for p in sorted(R.glob('candidate_regressions_01_*.json.gz')):
 d=json.loads(gzip.decompress(p.read_bytes()));pair=d.get('pair',{})
 history=pair.get('stateEvidence',{}).get('attempts',d.get('attempts',[]))
 windows=[(h['after']-h['before'])//2 for h in history if 'after' in h]
 row=dict(file=p.name,passed=d['passed'],error=d.get('error'),attempts=len(history),
  waitingFreshScan=sum(bool(h.get('waitingFreshScan')) for h in history),initialOdd=sum(h['before']%2!=0 for h in history),
  completeReadWindows=len(windows),windowScanDeltas=sorted(collections.Counter(windows).items()))
 if pair:
  assert snapshot(pair['capture'])==pair['canonical']
  comparison=compare_documents(pair['projection'],pair['canonical']);assert comparison['equal'] and comparison['typeAcceptance']
  row.update(freshStart=pair['stateEvidence']['freshStart'],connections=pair['readConnections'],requests=len(pair['readPlan']),
   paths=len(pair['canonical']['values']),packetKinds=dict(collections.Counter(p['kind'] for p in pair['readPlan'])))
 rows.append(row)
failed=[r for r in rows if not r['passed']]
assert len(rows)==40 and len(failed)==1 and sum(r['passed'] for r in rows)==39
assert (failed[0]['attempts'],failed[0]['waitingFreshScan'],failed[0]['initialOdd'],failed[0]['completeReadWindows'])==(100,77,6,17)
assert failed[0]['windowScanDeltas']==[(1,17)]
with (R/'acquisition_inspection_01.json').open('x') as f:json.dump(dict(passed=True,controllerAccess=False,rows=rows),f,indent=2)
print(json.dumps(dict(passed=True,passing=39,failed=failed)))
