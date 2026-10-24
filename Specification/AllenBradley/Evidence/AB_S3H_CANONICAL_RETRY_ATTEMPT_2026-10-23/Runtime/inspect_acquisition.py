from pathlib import Path
import collections,gzip,json
R=Path(__file__).parent;rows=[]
for path in sorted(R.glob('candidate_regressions_01_*.json.gz')):
    d=json.loads(gzip.decompress(path.read_bytes()));pair=d.get('pair',{})
    attempts=pair.get('stateEvidence',{}).get('attempts',d.get('attempts',[]))
    windows=[(h['after']-h['before'])//2 for h in attempts if 'after' in h]
    row=dict(file=path.name,passed=d['passed'],error=d.get('error'),attempts=len(attempts),
        waitingFreshScan=sum(bool(h.get('waitingFreshScan')) for h in attempts),
        initialOdd=sum(h['before']%2!=0 for h in attempts),completeReadWindows=len(windows),
        windowScanDeltas=sorted(collections.Counter(windows).items()))
    if pair:
        from sys import path as imports
        imports.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
        import fraktal_ab_canonical_reader as reader
        assert reader.snapshot(pair['capture'])==pair['canonical']
        from fraktal_ab_canonical_equivalence import compare_documents
        comparison=compare_documents(pair['projection'],pair['canonical'])
        assert comparison['equal'] and comparison['typeAcceptance'] and not comparison['differences']
        row.update(freshStart=pair['stateEvidence']['freshStart'],connections=pair['readConnections'],
            requests=len(pair['readPlan']),packetKinds=dict(collections.Counter(p['kind'] for p in pair['readPlan'])),
            readTransport=pair['readTransport'],paths=len(pair['canonical']['values']))
    rows.append(row)
assert len(rows)==4 and sum(r['passed'] for r in rows)==3
assert rows[-1]['attempts']==100 and rows[-1]['waitingFreshScan']==93 and rows[-1]['initialOdd']==3
assert rows[-1]['completeReadWindows']==4 and rows[-1]['windowScanDeltas']==[(1,4)]
with (R/'acquisition_inspection_01.json').open('x') as f:json.dump(dict(passed=True,controllerAccess=False,rows=rows),f,indent=2)
print(json.dumps(rows,indent=2))
