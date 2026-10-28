"""Offline ACD preparation, read-back comparison and Studio Capacity on a pinned copy."""
from pathlib import Path
import hashlib,shutil,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
prepare=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe')
source=W/'s3k_command_a_02.L5X';acd=W/'command_a_02.ACD';review=W/'command_a_capacity_review.ACD'
def run(label,*command):
 r=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,command)],cwd=R)
 if r.returncode:raise SystemExit(r.returncode)
assert not acd.exists() and not review.exists()
run('prepare_acd_02',prepare,source,acd,W/'prepared_readback_02.L5X')
run('prepared_compare_02',sys.executable,T/'fraktal_ab_readback.py',source,W/'prepared_readback_02.L5X')
shutil.copyfile(acd,review)
pin=hashlib.sha256(acd.read_bytes()).hexdigest().upper()
assert hashlib.sha256(review.read_bytes()).hexdigest().upper()==pin
run('capacity_02',sys.executable,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',pin,
    '--output',W/'capacity_auto_02.json','--capture-output',W/'capacity_capture_02.json')
print(pin)
