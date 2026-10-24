"""Audit the unchanged scan proof and fresh-edge scheduling from saved frames."""
from pathlib import Path
import collections,gzip,json
R=Path(__file__).parent
fixture=json.loads((R/'candidate_regressions_01.json').read_text())
items=[item for key,value in fixture.items() if key.endswith('Pairs') for item in value]
items.append(dict(output=str(R/'idle_equivalence_01.json.gz'),passed=True))
rows=[];waiting=odd=changed=0
for item in items:
    e=json.loads(gzip.decompress(Path(item['output']).read_bytes()))
    assert item['passed'] and e['passed']
    p=e['pair'];proof=p['stateEvidence'];history=proof['attempts']
    assert p['sameStateVerified'] and p['readConnections']==4
    assert p['readTransport']=='one outstanding read per socket; single multiplex owner'
    assert proof['freshStart'] and proof['readOnly'] and proof['kind']=='PLC entire-scan generation'
    assert 1<=len(history)<=100 and proof['generation']>0 and proof['generation']%2==0
    assert history[-1]['before']==history[-1]['after']==proof['generation']
    previous=None
    for h in history:
        before=h['before']
        if before%2:
            assert 'after' not in h
            odd+=1
        elif h.get('waitingFreshScan'):
            assert 'after' not in h and (previous is None or before==previous)
            waiting+=1
        else:
            assert previous is not None and before!=previous and 'after' in h
            changed+=h['after']!=before
        previous=h.get('after',before)
    rows.append(dict(file=Path(item['output']).name,attempts=len(history),generation=proof['generation']))
assert len(rows)==88
report=dict(passed=True,controllerAccess=False,captures=88,attemptLimit=100,secondsLimit=5,
    allWaitingPollsCounted=True,waitingPolls=waiting,oddPolls=odd,changedWindows=changed,
    freshStart=True,connections=4,maximumOutstandingPerConnection=1,
    attemptDistribution=sorted(collections.Counter(r['attempts'] for r in rows).items()),rows=rows)
with (R/'retry_proof_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
