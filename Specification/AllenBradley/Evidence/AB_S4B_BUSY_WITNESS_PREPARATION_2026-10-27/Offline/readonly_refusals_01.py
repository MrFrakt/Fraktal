from pathlib import Path
import json
import subprocess
import sys
W = Path(__file__).parent
S = W.parent / 'session_01'
rows = []
for name in ('task_monitor.py', 'desktop_readonly.py'):
    result = subprocess.run([sys.executable, str(S / name)], capture_output=True, text=True)
    output = result.stdout + result.stderr
    with (W / (name + '.missing_authorization.log')).open('x', encoding='utf-8') as stream:
        stream.write(output)
    assert result.returncode != 0 and 'authorization.json' in output
    rows.append(dict(helper=name, refused=True, exitCode=result.returncode))
assert not any((S / name).exists() for name in ('authorization.json', 'session_started.json',
    'task_monitor_ready.json', 'desktop_live', 'echo_before_s4b.ACD', 'deploy_attempt.json'))
with (W / 'readonly_refusals_01.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(passed=True,controllerAccess=False,helpers=rows),stream,indent=2)
print(json.dumps(dict(passed=True,readonlyHelpersRefused=len(rows),controllerAccess=False)))
