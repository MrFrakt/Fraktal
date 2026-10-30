from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
D='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
F='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/flutter_tools.snapshot'
for label,args in [('locked_dependencies_02',['pub','get','--enforce-lockfile']),
 ('analyze_02',['analyze','--no-pub']),('windows_profile_02',['build','windows','--profile','--no-pub'])]:
    result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,D,F,*args],cwd=H)
    if result.returncode:raise SystemExit(result.returncode)
