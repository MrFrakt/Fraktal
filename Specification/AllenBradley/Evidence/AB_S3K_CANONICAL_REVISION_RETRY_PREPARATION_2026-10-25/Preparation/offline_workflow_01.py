from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
def run(label,*args):
    result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,args)],cwd=R)
    if result.returncode:raise SystemExit(result.returncode)
run('compile_01',sys.executable,W/'compile_01.py')
for target,label in [('EchoController','Echo'),('PhysicalController','Physical')]:
    run('access_'+label+'_01',sys.executable,W/'audit_access.py',W/('native_'+target+'_01.L5X'),W/('access_'+label+'_01.json'))
run('prepare_capacity_01',sys.executable,W/'prepare_capacity_01.py')
