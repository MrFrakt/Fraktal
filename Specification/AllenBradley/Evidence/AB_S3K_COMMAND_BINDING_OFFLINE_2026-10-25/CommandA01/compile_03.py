from pathlib import Path
import subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
exe=R/'FraktalCore/PLC/Allen-Bradley/tools/Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe'
commands=[('generation_03',[sys.executable,'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_generate.py',
 'C:/work/echo38_5580_seed.L5X',str(W/'s3k_command_03.L5X'),'--declaration','fraktal_ab_genealogy_s3k_demo']),
 ('native_EchoController_03',[str(exe),'--build-readback',str(W/'s3k_command_03.L5X'),str(W/'native_EchoController_03.L5X'),'EchoController'])]
for label,command in commands:
 r=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*command],cwd=R)
 if r.returncode:raise SystemExit(r.returncode)
