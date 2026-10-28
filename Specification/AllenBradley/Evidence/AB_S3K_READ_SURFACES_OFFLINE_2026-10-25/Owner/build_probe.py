from pathlib import Path
import json,subprocess,sys
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal')
exe=ROOT/'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
for target in ('EchoController','PhysicalController'):
 label='native_'+target+'_01'
 command=[sys.executable,str(W/'run_logged.py'),label,str(exe),'--build-readback',str(W/'release_owner_probe_01.L5X'),str(W/(label+'.L5X')),target]
 result=subprocess.run(command,cwd=ROOT)
 if result.returncode:raise SystemExit(result.returncode)
 label='readback_'+target+'_01'
 result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,sys.executable,str(ROOT/'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_readback.py'),str(W/'release_owner_probe_01.L5X'),str(W/('native_'+target+'_01.L5X'))],cwd=ROOT)
 if result.returncode:raise SystemExit(result.returncode)
