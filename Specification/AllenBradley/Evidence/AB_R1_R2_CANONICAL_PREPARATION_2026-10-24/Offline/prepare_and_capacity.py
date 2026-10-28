from pathlib import Path
import json,subprocess,sys,time,hashlib,shutil
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
jobs=[('readback_Echo_01',[sys.executable,str(T/'fraktal_ab_readback.py'),str(W/'s3i_r1_r2.L5X'),str(W/'native_EchoController_01.L5X')]),('readback_Physical_01',[sys.executable,str(T/'fraktal_ab_readback.py'),str(W/'s3i_r1_r2.L5X'),str(W/'native_PhysicalController_01.L5X')]),('access_Echo_01',[sys.executable,str(W/'audit_access.py'),str(W/'native_EchoController_01.L5X'),str(W/'access_Echo_01.json')]),('access_Physical_01',[sys.executable,str(W/'audit_access.py'),str(W/'native_PhysicalController_01.L5X'),str(W/'access_Physical_01.json')]),('prepare_acd_01',[str(W/'prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'),str(W/'s3i_r1_r2.L5X'),str(W/'s3i_r1_r2.ACD'),str(W/'prepared_readback_01.L5X')])]
for name,cmd in jobs:
 with (W/(name+'.log')).open('xb') as f:done=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 print(json.dumps(dict(name=name,exitCode=done.returncode)),flush=True)
 if done.returncode:sys.exit(done.returncode)
shutil.copyfile(W/'s3i_r1_r2.ACD',W/'capacity_review.ACD')
sha=hashlib.sha256((W/'capacity_review.ACD').read_bytes()).hexdigest().upper()
with (W/'prepared_identity_01.json').open('x') as f:json.dump(dict(acdSha256=sha,sourceSha256=hashlib.sha256((W/'s3i_r1_r2.L5X').read_bytes()).hexdigest().upper()),f,indent=2)
cmd=[sys.executable,str(T/'fraktal_ab_studio_capacity.py'),'--acd',str(W/'capacity_review.ACD'),'--expect-sha256',sha,'--output',str(W/'capacity_auto_01.json'),'--capture-output',str(W/'capacity_capture_01.json')]
with (W/'capacity_01.log').open('xb') as f:done=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
print(json.dumps(dict(name='capacity_01',exitCode=done.returncode)),flush=True)
sys.exit(done.returncode)
