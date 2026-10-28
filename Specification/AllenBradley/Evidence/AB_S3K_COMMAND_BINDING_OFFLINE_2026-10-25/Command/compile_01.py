"""Generate the option A image and build/read it back on both v38 targets."""
from pathlib import Path
import subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
exe=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
source=W/'s3k_command_a_01.L5X'
def run(label,*command):
 r=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,command)],cwd=R)
 if r.returncode:raise SystemExit(r.returncode)
run('generation_01',sys.executable,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',source,'--declaration','fraktal_ab_genealogy_s3k_demo')
for target in ('EchoController','PhysicalController'):
 run('native_'+target+'_01',exe,'--build-readback',source,W/('native_'+target+'_01.L5X'),target)
 run('readback_'+target+'_01',sys.executable,T/'fraktal_ab_readback.py',source,W/('native_'+target+'_01.L5X'))
