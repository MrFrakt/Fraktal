"""Only negative invocations; no fixture credential or controller is read."""
from pathlib import Path
import json,os,subprocess,sys
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
app=json.loads((W/'authorization.json').read_text());assert app['CurrentOwnerApproved'] is False
exe=W/'session/bin/Debug/net8.0/win-x86/S3iLifetimeSession.exe'
rows=[]
for mode in ('backup','deploy-canonical','restore-genealogy','cycle-retained'):
    result=subprocess.run([str(exe),mode],capture_output=True)
    raw=result.stdout+result.stderr
    with (W/('refused_'+mode.replace('-','_')+'_01.log')).open('xb') as f:f.write(raw)
    assert result.returncode!=0 and b'Current target/artifact owner authorization missing' in raw
    assert not any(s in raw for s in (b'Open project started',b'Download started',b'"address"'))
    rows.append(dict(command=mode,refusedBeforeSdkAndGuard=True,exitCode=result.returncode))
env=dict(os.environ,FRAKTAL_AB_DECLARATION='fraktal_ab_genealogy_demo')
for phase in ('calendar','retention'):
    output=W/('must_not_exist_'+phase+'.json')
    args=[sys.executable,str(W/'run_candidate.py'),'lifetime',
        '--phase',phase,'--execute-fixture','--expect-serial','601FC87B','--authorization-file',str(W/'authorization.json'),
        '--output',str(output)]
    args += (['--credential-file',str(W/'unread_fixture_file.json')] if phase=='calendar' else ['--before',str(W/'unread_before.json')])
    result=subprocess.run(args,env=env,capture_output=True);raw=result.stdout+result.stderr
    with (W/('refused_fixture_'+phase+'_01.log')).open('xb') as f:f.write(raw)
    assert result.returncode!=0 and b'current exact-image calendar/lifetime authorization required' in raw
    assert not output.exists()
    rows.append(dict(command=phase,refusedBeforeControllerAndCredential=True,exitCode=result.returncode))
source=(W/'session/Program.cs').read_text(encoding='utf-8')
cycle=source.split('if (args[0]=="cycle-retained") {',1)[1].split('if (args[0]=="backup") {',1)[0]
assert cycle.count('ChangeControllerModeAsync')==2 and 'RequestedControllerMode.Program' in cycle and 'RequestedControllerMode.Run' in cycle
assert not any(token in cycle for token in ('DownloadAsync','SaveAsync','SaveAsAsync','ClearFault','SetClock'))
assert cycle.index('retention_readiness.py')<cycle.index('RequestedControllerMode.Program')
with (W/'authorization_negative_01.json').open('x') as f:json.dump(dict(passed=True,cases=rows,cycleHasNoDownloadOrSave=True,controllerAccess=False),f,indent=2)
print(json.dumps(dict(passed=True,negativeCases=len(rows),cycleHasNoDownloadOrSave=True,controllerAccess=False)))
