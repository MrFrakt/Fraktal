"""Negative invocation only: every authorization flag remains false."""
from pathlib import Path
import json
import subprocess

W=Path(__file__).parent
authorization=json.loads((W/'authorization.json').read_text())
assert all(authorization[k] is False for k in ('CurrentOwnerApproved','AccessVectorsAuthorized',
    'ConfigurationVectorsAuthorized','NativeLineVectorsAuthorized'))
program=(W/'session/Program.cs').read_text()
guard=program.index('using (var authorization=')
assert guard<program.index('if (args[0]=="backup")')
assert '!approved.GetProperty("NativeLineVectorsAuthorized").GetBoolean()' in program
rows=[]
for mode in ('backup','deploy-canonical','restore-genealogy'):
    result=subprocess.run([str(W/'session/bin/Debug/net8.0/win-x86/S3iSession.exe'),mode],capture_output=True,text=True)
    output=result.stdout+result.stderr
    with (W/('authorization_refused_'+mode.replace('-','_')+'_01.log')).open('x') as f:f.write(output)
    assert result.returncode!=0 and 'Current target/artifact owner authorization missing' in output
    assert not any(token in output for token in ('Open project started','Open Project From Controller','"address"','Download started'))
    rows.append(dict(mode=mode,refusedBeforeGuardAndSdk=True,exitCode=result.returncode))
with (W/'authorization_negative_01.json').open('x') as f:json.dump(dict(passed=True,controllerAccess=False,cases=rows),f,indent=2)
print(json.dumps(dict(passed=True,cases=len(rows),controllerAccess=False)))
