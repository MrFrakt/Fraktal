from pathlib import Path
import hashlib,json,shutil,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
source=W/'canonical_owner_01.L5X';acd=W/'canonical_owner_01.ACD';review=W/'capacity_review_01.ACD'
assert not acd.exists() and not review.exists()
def run(label,*command):
    subprocess.run([sys.executable,str(W/'run_logged.py'),label,*map(str,command)],cwd=R,check=True)
run('prepare_acd_01','C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe',source,acd,W/'prepared_readback_01.L5X')
run('prepared_compare_01',sys.executable,T/'fraktal_ab_readback.py',source,W/'prepared_readback_01.L5X')
pin=hashlib.sha256(acd.read_bytes()).hexdigest().upper();shutil.copyfile(acd,review)
run('capacity_01',sys.executable,T/'fraktal_ab_studio_capacity.py','--acd',review,'--expect-sha256',pin,
    '--output',W/'capacity_auto_01.json','--capture-output',W/'capacity_capture_01.json')
assert hashlib.sha256(acd.read_bytes()).hexdigest().upper()==pin
with (W/'prepared_pins_01.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(acdSha256=pin,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest().upper()),stream,indent=2)
