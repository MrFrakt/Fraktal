from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
D='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
F='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/flutter_tools.snapshot'
for label,arguments in [('full_hmi_02',['test','--no-pub','--reporter','expanded']),
 ('analyze_02',['analyze','--no-pub']),('windows_profile_02',['build','windows','--profile','--no-pub'])]:
 print(label,flush=True)
 result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,D,F,*arguments],cwd=H)
 if result.returncode:raise SystemExit(result.returncode)
raise SystemExit(subprocess.run([sys.executable,str(W/'run_rehearsal_sequence_01.py')]).returncode)
