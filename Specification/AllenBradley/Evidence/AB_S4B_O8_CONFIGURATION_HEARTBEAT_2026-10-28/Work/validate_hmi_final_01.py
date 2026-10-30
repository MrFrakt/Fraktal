"""Current-source HMI gates, serialized; no controller I/O."""
from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
F='C:/work/fraktal-toolchains/flutter-3.47.5/bin/flutter.bat'
for label,args in [
 ('locked_dependencies_01',['pub','get','--enforce-lockfile']),
 ('analyze_01',['analyze','--no-pub']),
 ('full_hmi_01',['test','--no-pub','--reporter','expanded']),
 ('profile_build_01',['build','windows','--profile','--no-pub']),
]:
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,F,*args],cwd=H,check=True)
