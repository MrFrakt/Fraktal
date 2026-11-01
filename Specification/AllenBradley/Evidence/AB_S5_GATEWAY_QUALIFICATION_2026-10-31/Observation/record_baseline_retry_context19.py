import sys
sys.path.pop(0)
from pathlib import Path
import datetime,json
D=Path('C:/work/fraktal-ab-s5-20261029/session_19')
failed=json.loads((D/'baseline_regressions.json').read_bytes())
record=dict(controllerAccess=False,originalError=failed['error'],originalCompletedRows=len(failed['rows']),
    originalInputAndPolicyRestorationPassed=failed['restored'] and failed['policyRestored'],
    actualScope='One unchanged baseline fixture retry, MANUAL/final/preflight/timing cleanup and read-only state witness. No download or new write vector.',
    correction='The inherited recovery wrapper retains a descriptive HOME-timeout string and browser-unproven flags from session11. They do not describe this run. The actual failure is START refused; current native/C12 gates passed. The original files and flags remain immutable; a separate stage-exit result evaluates current evidence after recovery.',
    preparationAttempt='Attempted exclusive-copy preparation stopped before any write because the already inherited recovery helper existed. The existing helper then ran unchanged under its exact-image authorization and guards.',
    originalFailurePreserved=True,standingAuthority='O3',utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D/'baseline_retry_context_correction.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps({k:v for k,v in record.items() if k not in ('correction','preparationAttempt')}))
