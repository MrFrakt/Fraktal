from pathlib import Path
from collections import Counter
import gzip
import json
import statistics

W = Path(__file__).parent
D = Path('C:/work/fraktal-ab-s4b-pool-20261027/session_01')
load = lambda p: json.loads(gzip.decompress(p.read_bytes())) if p.suffix == '.gz' else json.loads(p.read_bytes())
dart = load(D / 'dart_qualification.json.gz')
samples = dart['samples']
def series(name):
    values = sorted(row[name] for row in samples if isinstance(row.get(name), (int, float)))
    return None if not values else dict(minimum=values[0], median=statistics.median(values),
        p95=values[min(len(values)-1, int(len(values)*.95))], maximum=values[-1])
result = dict(observerPassed=dart['passed'], observerError=dart['error'], elapsedMs=dart['elapsedMs'],
    completedSamples=len(samples), retainedSnapshots=len(dart['snapshots']),
    configurationPages=len(dart['configurationPages']), sampleAgeMs=series('sampleAgeMs'), rpcUs=series('rpcUs'),
    maximumRowAcquisitionUs=series('maximumRowAcquisitionUs'), maximumAcceptedRowWindowUs=series('maximumAcceptedRowWindowUs'),
    statusCounts=dict(Counter((row['bad'], row['uncertain']).__str__() for row in samples)),
    configurationPageSummaries=[dict(root=page['root'], modelOrdinal=page['modelOrdinal'],
        scalars=len(page['page']), entries=page['page']['EntryCount']) for page in dart['configurationPages']],
    rejectedSnapshots=[dict(failure=s.get('rootSampleFailure'), values=len(s.get('values', {})),
        sampleAgeMs=s.get('sampleAgeMs'), responseProcessingMs=s.get('responseProcessingMs'))
        for s in dart['snapshots'] if s.get('qualificationRejectedRootSample')])
for name in ('candidate_regressions.json', 'session_result.json', 'idle_equivalence.json.gz', 'candidate_timing.json', 'baseline_regressions.json', 'final_checks.json'):
    path = D / name
    if not path.exists():
        continue
    value = load(path)
    if name.endswith('regressions.json'):
        result[name] = dict(rows=len(value.get('rows', [])), passedRows=sum(row.get('passed') is True for row in value.get('rows', [])),
            restored=value.get('restored'), error=value.get('error'), policyRestored=value.get('policyRestored'))
    elif name in ('session_result.json', 'final_checks.json'):
        result[name] = value
    else:
        result[name] = dict(keys=list(value), passed=value.get('passed'), differences=value.get('differences'))
with (D / 'runtime_inspection_01.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
