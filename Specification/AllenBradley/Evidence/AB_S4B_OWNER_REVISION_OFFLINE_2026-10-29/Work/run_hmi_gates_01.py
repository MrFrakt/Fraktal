from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
D='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
F='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/flutter_tools.snapshot'
for label,command in [('locked_dependencies_01',[D,F,'pub','get','--enforce-lockfile']),
 ('full_hmi_01',[D,F,'test','--no-pub','--reporter','expanded']),
 ('analyze_01',[D,F,'analyze','--no-pub']),
 ('windows_profile_01',[D,F,'build','windows','--profile','--no-pub'])]:
    print(label,flush=True)
    result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*command],cwd=H)
    if result.returncode:raise SystemExit(result.returncode)
