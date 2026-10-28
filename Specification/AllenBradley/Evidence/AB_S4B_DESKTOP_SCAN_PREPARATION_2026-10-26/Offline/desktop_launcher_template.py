"""Launch only the sealed read-only desktop acceptance helper."""
from pathlib import Path
import os
import subprocess
from qualification_session_v2 import authorize
import json

D=Path(__file__).parent
authorize(json.loads((D/'authorization.json').read_bytes()))
assert not (D/'desktop_live').exists()
env=dict(os.environ,FLUTTER_ROOT='C:/work/fraktal-toolchains/flutter-3.47.5',
    FRAKTAL_AB_DESKTOP_LIVE='1',FRAKTAL_AB_DESKTOP_OUTPUT=str(D/'desktop_live'),
    FRAKTAL_AB_DESKTOP_ENDPOINT='cip://127.0.0.1?slot=0&serial=601FC87B')
env.pop('FRAKTAL_AB_DESKTOP_FIXTURE',None)
command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat','test',
    '--no-pub','--concurrency=1','--reporter','expanded',str(D/'desktop_readonly_qualification_test.dart')]
process=subprocess.Popen(command,cwd=D.parent/'hmi_verify_01',env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    code=process.wait(timeout=240)
except subprocess.TimeoutExpired:
    # Only this newly spawned read-only Flutter process tree; never Echo.
    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],check=True)
    raise
raise SystemExit(code)
