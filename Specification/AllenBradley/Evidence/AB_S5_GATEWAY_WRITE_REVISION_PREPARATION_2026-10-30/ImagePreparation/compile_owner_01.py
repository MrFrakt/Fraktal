from pathlib import Path
import subprocess
import sys
R=Path('C:/Users/SoftIndVM/Fraktal')
W=Path(__file__).parent
T=R/'FraktalCore/PLC/Allen-Bradley/tools'
source=W/'canonical_owner_01.L5X'
def run(label,*args):
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,args)],cwd=R,check=True)
run('generate_01',sys.executable,T/'fraktal_ab_generate.py','C:/work/echo38_5580_seed.L5X',source,
    '--declaration','fraktal_ab_genealogy_s4b_owner_demo')
sdk=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
for target in ('EchoController','PhysicalController'):
    output=W/(target+'_owner_readback_01.L5X')
    run('build_'+target+'_01',sdk,'--build-readback',source,output,target)
    run('readback_'+target+'_01',sys.executable,T/'fraktal_ab_readback.py',source,output)
