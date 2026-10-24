from pathlib import Path
import collections,gzip,json,statistics
R=Path(__file__).parent;rows=[]
for path in sorted(R.glob('*.json.gz')):
    data=json.loads(gzip.decompress(path.read_bytes()));pair=data.get('pair',{})
    attempts=pair.get('stateEvidence',{}).get('attempts',data.get('attempts',[]))
    trailing=[(r['after']-r['before'])//2 for r in attempts if 'after' in r]
    row=dict(file=path.name,passed=data.get('passed'),error=data.get('error'),attempts=len(attempts),
        initialOdd=sum(r['before']%2!=0 for r in attempts),completeReadWindows=len(trailing),
        windowScanDeltas=dict(sorted(collections.Counter(trailing).items())))
    if pair:
        plans=pair.get('readPlan',[])
        row.update(connections=pair.get('readConnections'),requests=len(plans),
            liveRecordSizes={r['tag']:len(bytes.fromhex(r['rawHex'])) for r in pair['rawReads'] if r['rawHex']},
            packetKinds=dict(collections.Counter(p['kind'] for p in plans)))
    rows.append(row)
with (R/'acquisition_inspection_01.json').open('x') as f:json.dump(dict(rows=rows),f,indent=2)
print(json.dumps(rows,indent=2))
