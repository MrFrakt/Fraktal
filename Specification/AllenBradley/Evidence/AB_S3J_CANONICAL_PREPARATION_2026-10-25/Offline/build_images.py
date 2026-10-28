from pathlib import Path
import json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
exe=R/'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
for target in ('EchoController','PhysicalController'):
 name='native_'+target+'_01';cmd=[str(exe),'--build-readback',str(W/'s3j_02.L5X'),str(W/(name+'.L5X')),target]
 start=time.time()
 with (W/(name+'.log')).open('xb') as f:done=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 result=dict(name=name,exitCode=done.returncode,seconds=time.time()-start)
 with (W/(name+'_exit.json')).open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
 if done.returncode:sys.exit(done.returncode)
