"""Wait for this run's test result; the session itself rechecks all gates."""
from pathlib import Path
import json,subprocess,sys,time
R=Path(__file__).parent
result=R/'ab_suite_01_exit.json'
deadline=time.monotonic()+600
while not result.exists():
    if time.monotonic()>deadline:raise SystemExit('AB gate result did not arrive; no session started')
    time.sleep(2)
assert json.loads(result.read_text())['exitCode']==0,'AB gate failed; no session started'
raise SystemExit(subprocess.run([sys.executable,str(R/'start_session.py')],check=False).returncode)
