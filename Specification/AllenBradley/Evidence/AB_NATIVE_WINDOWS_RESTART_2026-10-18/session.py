import json
import subprocess
import sys
from pathlib import Path

root=Path(__file__).parent
mode=sys.argv[1]
if mode not in ('prepare','backup','deploy-authorized'):
    raise SystemExit('invalid session mode')
with (root/(mode+'.log')).open('xb') as log:
    result=subprocess.run([str(root/'bin/Debug/net8.0/win-x86/WindowSession.exe'),mode],
                          stdout=log,stderr=subprocess.STDOUT,timeout=360)
print(json.dumps(dict(mode=mode,exitCode=result.returncode)))
raise SystemExit(result.returncode)
