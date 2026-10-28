"""Read-only postprocessing of the completed exact-image session."""
from pathlib import Path
import gzip
import hashlib
import json
import statistics
import sys

R = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_canonical_reader as reader

load = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
result = load(R / 'session_result.json')
fixture = load(R / 'request_cases.json')
completion = result
baseline = load(R / 'baseline_regressions.json')
final = load(R / 'final_checks.json')
assert completion['passed'] and not baseline.get('error') and baseline['restored'] and len(baseline['rows']) == 31 and all(r['passed'] for r in baseline['rows']) and final['passed']
rows = {key: dict(count=len(value), passed=sum(row.get('passed') is True for row in value))
        for key, value in fixture.items() if isinstance(value, list) and (key == 'rows' or key.endswith('Rows') or key.endswith('Pairs'))}
timing = {}
for name in ('candidate_timing', 'baseline_timing'):
    path = R / (name + '.json')
    if not path.exists():
        timing[name] = dict(measured=False)
        continue
    samples = [row['values'] for row in load(path)['samples']]
    details = {}
    for key in samples[0]:
        values = [row[key] for row in samples]
        details[key] = dict(minimum=min(values), median=statistics.median(values), maximum=max(values))
    timing[name] = dict(measured=True, unit='microseconds', samples=len(samples), fields=details)

generic_replay = False
if (R / 'generic_capture.json.gz').exists():
    snapshot = reader.snapshot(load(R / 'generic_capture.json.gz'))
    assert snapshot == load(R / 'generic_snapshot.json.gz')
    generic_replay = True
    generic = dict(values=snapshot['nodeCount'], modules=snapshot['moduleCount'], replayPassed=True)
else:
    generic = dict(replayPassed=False, reason='candidate stopped before generic acquisition')

bindings = load(R / 'source_bindings.json')
for name, expected in bindings['sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest().upper() == expected.upper(), name
out = dict(passed=result['passed'], candidatePassed=not bool(fixture.get('error')), candidateError=fixture.get('error'),
           caseGroups=rows, typedCases=fixture.get('s3kTypedRows', []), typedLoginCompleted=any(row['case']=='legacy_after_typed' for row in fixture.get('s3kTypedRows', [])), generic=generic,
           timing=timing, genealogyRestored=True, baselineChecks=31, finalChecks=final['checks'],
           nativeSourcesUnchanged=True, boundFiles=len(bindings['sha256']), authorizationConsumed=True,
           exactAcdSha256=load(R / 'deploy_attempt.json')['CanonicalSha256'],
           baselineAcdSha256='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084')
with (R / 'runtime_summary_01.json').open('x') as stream:
    json.dump(out, stream, indent=2)
print(json.dumps({key: value for key, value in out.items() if key not in ('timing', 'typedCases')}))
