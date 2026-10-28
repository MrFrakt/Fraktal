from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
PY=sys.executable;log=W/'run_logged.py';source=W/'s3k_read_surface_02.L5X'
def run(label,*command):
 p=subprocess.run([PY,str(log),label,*map(str,command)],cwd=ROOT)
 if p.returncode:raise SystemExit(p.returncode)
run('readback_EchoController_03',PY,T/'fraktal_ab_readback.py',source,W/'native_EchoController_02.L5X')
exe=T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
assert not (W/'native_PhysicalController_02.L5X').exists()
run('native_PhysicalController_02',exe,'--build-readback',source,W/'native_PhysicalController_02.L5X','PhysicalController')
run('readback_PhysicalController_03',PY,T/'fraktal_ab_readback.py',source,W/'native_PhysicalController_02.L5X')
