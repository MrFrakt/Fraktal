from pathlib import Path
import hashlib,json,shutil,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
source=W/'s6_host_02.L5X';acd=W/'s6_host_02.ACD';review=W/'capacity_review_02.ACD'
assert not acd.exists() and not review.exists()
def run(label,*command):
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,command)],cwd=R,check=True)
run('prepare_acd_02','C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe',source,acd,W/'prepared_readback_02.L5X')
run('prepared_compare_02',sys.executable,T/'fraktal_ab_readback.py',source,W/'prepared_readback_02.L5X')
pin=hashlib.sha256(acd.read_bytes()).hexdigest().upper();shutil.copyfile(acd,review)
run('capacity_02',sys.executable,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',pin,
    '--output',W/'capacity_auto_02.json','--capture-output',W/'capacity_capture_02.json')
assert hashlib.sha256(acd.read_bytes()).hexdigest().upper()==pin
with (W/'prepared_pins_02.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(acdSha256=pin,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest().upper()),stream,indent=2)
