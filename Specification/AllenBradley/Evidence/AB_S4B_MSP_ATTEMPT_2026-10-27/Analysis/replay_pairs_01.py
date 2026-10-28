"""Replay every completed capture; retain the full fixture/87-pair gate."""
from pathlib import Path
import gzip,json,sys
W=Path(__file__).parent;D=W.parent/'session_01'
R=Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_canonical_reader import snapshot
from fraktal_ab_canonical_equivalence import compare_live
evidence=json.loads((D/'candidate_regressions.json').read_bytes())
expected={'rows':31,'s4bAccessRows':2,'s4bConfigRows':8}
counts={key:len(evidence.get(key,[])) for key in expected}
assert all(row['passed'] for key in expected for row in evidence.get(key,[]))
assert evidence['restored'] and evidence['policyRestored']
rows=[]
for kind,pairs in evidence.items():
    if not kind.endswith('Pairs'):continue
    for entry in pairs:
        path=Path(entry['output'])
        assert path.parent==D and entry['passed']
        report=json.loads(gzip.decompress(path.read_bytes()));assert report['passed']
        pair=report['pair'];decoded=snapshot(pair['capture'])
        assert decoded['values']==pair['canonical']['values'],path.name
        assert decoded['types']==pair['canonical']['types'],path.name
        compared=compare_live(lambda:dict(pair,canonical=decoded))
        assert compared['equal'] and compared['typeAcceptance'],path.name
        rows.append(dict(kind=kind,output=path.name,paths=len(decoded['values']),modules=decoded['moduleCount'],passed=True))
full=counts==expected and evidence.get('error') is None and evidence.get('s3fSetMediumEmpty') is True and len(rows)==87
result=dict(passed=True,readOnly=True,controllerAccess=False,fullFixturePassed=full,
 expectedRegressions=41,regressions=sum(counts.values()),caseCounts=counts,expectedCaseCounts=expected,
 pairs=len(rows),minimumPaths=min((r['paths'] for r in rows),default=0),
 maximumPaths=max((r['paths'] for r in rows),default=0),rows=rows)
with (D/'paired_replay_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
