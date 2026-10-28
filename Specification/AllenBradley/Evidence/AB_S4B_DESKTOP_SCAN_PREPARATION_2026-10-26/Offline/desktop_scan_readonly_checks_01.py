from pathlib import Path
import json
import subprocess
import sys

W=Path(__file__).parent
D=W.parent/'desktop_scan_01'
rows=[]
for name in ('task_monitor.py','desktop_readonly.py'):
    assert not (D/'authorization.json').exists()
    with (W/('missing_approval_'+name.removesuffix('.py')+'_01.log')).open('x',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,str(D/name)],stdout=stream,stderr=subprocess.STDOUT)
    assert result.returncode!=0
    assert not (D/'task_monitor_ready.json').exists() and not (D/'desktop_live').exists()
    rows.append(dict(helper=name,missingApprovalRefused=True,exitCode=result.returncode))
for path in D.glob('*.py'):
    compile(path.read_text(encoding='utf-8'),str(path),'exec')
result=dict(passed=True,controllerAccess=False,controllerChanges=0,helpers=rows,syntaxPassed=True)
with (W/'desktop_scan_readonly_checks_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(result))
