from pathlib import Path
import gzip
import json

D = Path('C:/work/fraktal-ab-s4b-20261025/retry_lookup_01')
paths = sorted(D.glob('candidate_regressions_configuration_*.json.gz'), key=lambda p: p.stat().st_mtime)
report = json.loads(gzip.decompress(paths[-1].read_bytes()))
print(json.dumps(dict(latestCapture=paths[-1].name, keys=list(report),
    phase=report.get('phase'), metadata=report.get('metadata'), passed=report.get('passed'))))
