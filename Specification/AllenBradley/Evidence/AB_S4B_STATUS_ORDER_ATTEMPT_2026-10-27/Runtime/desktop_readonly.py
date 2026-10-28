from pathlib import Path
import json
import os
import subprocess
import sys
from qualification_session_v2 import authorize
from desktop_coverage import validate_coverage

D=Path(__file__).parent
authorize(json.loads((D/'authorization.json').read_bytes()))
assert not (D/'desktop_live').exists()
env=dict(os.environ,FLUTTER_ROOT='C:/work/fraktal-toolchains/flutter-3.47.5',
    FRAKTAL_AB_DESKTOP_LIVE='1',FRAKTAL_AB_DESKTOP_OUTPUT=str(D/'desktop_live'),
    FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY=str(D/'desktop_expected_inventory.json'),
    FRAKTAL_AB_DESKTOP_ENDPOINT='cip://127.0.0.1?slot=0&serial=601FC87B')
env.pop('FRAKTAL_AB_DESKTOP_FIXTURE',None)
env.pop('FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE',None)
command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat','test','--no-pub',
    '--concurrency=1','--reporter','expanded',str(D/'desktop_diagnostic_qualification_test.dart')]
process=subprocess.Popen(command,cwd=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01'),env=env,
    creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
    output=process.communicate(timeout=240)[0]
except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],check=True)
    output=process.communicate(timeout=10)[0]
    sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
    raise
sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
if process.returncode:raise SystemExit(process.returncode)
value=json.loads((D/'desktop_live/result.json').read_bytes())
expected=json.loads((D/'desktop_expected_inventory.json').read_bytes())
validate_coverage(value,expected,require_live=True)
with (D/'desktop_semantic_acceptance.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,live=True,modules=len(value['modules']),views=len(value['shots']),readOnly=True),stream,indent=2)
