import subprocess,sys
from pathlib import Path
w=Path(__file__).resolve().parent
p=subprocess.run([sys.executable,'-m','unittest','discover','-s','FraktalCore/PLC/Siemens/tools','-t','FraktalCore/PLC/Siemens/tools'],cwd=r'C:\Projects\Fraktal',capture_output=True)
with (w/'33_tools_final.log').open('xb') as f:f.write(p.stdout);f.write(p.stderr)
print(p.stderr.decode('utf-8',errors='replace')[-500:]);sys.exit(p.returncode)
