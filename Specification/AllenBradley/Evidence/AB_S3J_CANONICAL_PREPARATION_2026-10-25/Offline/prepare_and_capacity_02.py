from pathlib import Path
import json,subprocess,sys
W=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01');R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
def run(name,cmd):
 with (W/(name+'.log')).open('xb') as f:p=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 with (W/(name+'_exit.json')).open('x') as f:json.dump(dict(exitCode=p.returncode,command=cmd),f,indent=2)
 print(name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
for short,target in [('Echo','EchoController'),('Physical','PhysicalController')]:
 run('readback_'+short+'_04',[sys.executable,str(T/'fraktal_ab_readback.py'),str(W/'s3j_06.L5X'),str(W/('native_'+target+'_04.L5X'))])
run('prepare_acd_02',[str(W/'prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'),str(W/'s3j_06.L5X'),str(W/'s3j_final.ACD'),str(W/'prepared_readback_02.L5X')])
import shutil,hashlib
shutil.copyfile(W/'s3j_final.ACD',W/'capacity_final_review.ACD');pin=hashlib.sha256((W/'s3j_final.ACD').read_bytes()).hexdigest().upper()
with (W/'prepared_identity_02.json').open('x') as f:json.dump(dict(acdSha256=pin,sourceSha256=hashlib.sha256((W/'s3j_06.L5X').read_bytes()).hexdigest().upper()),f,indent=2)
run('capacity_02',[sys.executable,str(T/'fraktal_ab_studio_capacity.py'),'--acd',str(W/'capacity_final_review.ACD'),'--expect-sha256',pin,'--output',str(W/'capacity_auto_02.json'),'--capture-output',str(W/'capacity_capture_02.json')])
