"""Negative authorization checks only: no controller or credential access."""
from pathlib import Path
import json,os,subprocess,sys
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
assert json.loads((W/'authorization.json').read_bytes())['CurrentOwnerApproved'] is False
exe=W/'session/bin/Debug/net8.0/win-x86/S3jSession.exe';rows=[]
for mode in ('backup','deploy-canonical','restore-genealogy'):
 result=subprocess.run([str(exe),mode],capture_output=True);raw=result.stdout+result.stderr
 with (W/('refused_'+mode.replace('-','_')+'_01.log')).open('xb') as f:f.write(raw)
 assert result.returncode!=0 and b'Current target/artifact owner authorization missing' in raw
 assert not any(x in raw for x in (b'Open project started',b'Download started',b'"address"'))
 rows.append(dict(command=mode,refusedBeforeSdkAndGuard=True,exitCode=result.returncode))
output=W/'must_not_exist_io.json'
cmd=[sys.executable,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s3j_io_execute.py'),'--execute-fixture',
 '--expect-serial','601FC87B','--expect-acd-sha256',(W/'canonical.sha256').read_text().strip(),
 '--authorization-file',str(W/'authorization.json'),'--output',str(output)]
result=subprocess.run(cmd,env=dict(os.environ,FRAKTAL_AB_DECLARATION='fraktal_ab_genealogy_demo'),capture_output=True);raw=result.stdout+result.stderr
with (W/'refused_io_vectors_01.log').open('xb') as f:f.write(raw)
assert result.returncode!=0 and b'current exact-image S3j word-vector authorization required' in raw and not output.exists()
rows.append(dict(command='io-vectors',refusedBeforeConnection=True,exitCode=result.returncode))
source=(W/'session/Program.cs').read_bytes()
assert b'if (args[0]=="cycle-retained")' not in source
assert b'ChangeControllerModeAsync' in source and b'DownloadAsync' in source
assert not any(token in source for token in (b'ClearControllerFault',b'SetClock',b'IsEnabled'))
with (W/'authorization_negative_01.json').open('x') as f:json.dump(dict(passed=True,cases=rows,controllerAccess=False),f,indent=2)
print(json.dumps(dict(passed=True,negativeCases=len(rows),controllerAccess=False)))
