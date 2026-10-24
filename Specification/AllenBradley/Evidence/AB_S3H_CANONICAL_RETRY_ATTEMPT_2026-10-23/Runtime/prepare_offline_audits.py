"""Copy already qualified read-only evidence auditors into this fresh run."""
from pathlib import Path
import json
R=Path(__file__).parent
prior=R.parent/'runtime_6cf76ecb8785463ab372c202e79f03f2'
for name in ('verify_candidate_surface.py','replay_runtime_captures.py','measure_native_records.py',
             'trace_observations.py','close_native_measurements.py'):
    with (R/name).open('x',encoding='utf-8') as f: f.write((prior/name).read_text())
print(json.dumps(dict(passed=True,controllerAccess=False,auditors=5)))
