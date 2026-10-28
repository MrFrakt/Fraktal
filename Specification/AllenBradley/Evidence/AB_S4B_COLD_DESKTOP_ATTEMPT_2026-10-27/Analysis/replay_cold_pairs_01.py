from pathlib import Path
import gzip
import json
import sys

R = Path('C:/Users/SoftIndVM/Fraktal')
D = Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')
sys.path.insert(0, str(R / 'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_canonical_reader import snapshot
from fraktal_ab_canonical_equivalence import compare_live

evidence = json.loads((D / 'candidate_regressions.json').read_bytes())
assert len(evidence['rows']) == 31 and all(row['passed'] for row in evidence['rows'])
assert len(evidence['s4bAccessRows']) == 2 and all(row['passed'] for row in evidence['s4bAccessRows'])
assert len(evidence['s4bConfigRows']) == 8 and all(row['passed'] for row in evidence['s4bConfigRows'])
assert evidence['restored'] and evidence['policyRestored'] and evidence['s3fSetMediumEmpty']
rows = []
for key, pairs in evidence.items():
    if not key.endswith('Pairs'):
        continue
    for entry in pairs:
        path = Path(entry['output'])
        assert path.parent == D and entry['passed']
        report = json.loads(gzip.decompress(path.read_bytes()))
        assert report['passed']
        pair = report['pair']
        decoded = snapshot(pair['capture'])
        assert decoded['values'] == pair['canonical']['values'], path.name
        assert decoded['types'] == pair['canonical']['types'], path.name
        result = compare_live(lambda: dict(pair, canonical=decoded))
        assert result['equal'] and result['typeAcceptance'], path.name
        rows.append(dict(kind=key, output=path.name, paths=len(decoded['values']),
                         modules=decoded['moduleCount'], passed=True))
result = dict(passed=True, readOnly=True, controllerAccess=False, regressions=41,
    pairs=len(rows), minimumPaths=min(row['paths'] for row in rows), maximumPaths=max(row['paths'] for row in rows),
    rows=rows)
with (D / 'paired_replay_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({key: value for key, value in result.items() if key != 'rows'}))
