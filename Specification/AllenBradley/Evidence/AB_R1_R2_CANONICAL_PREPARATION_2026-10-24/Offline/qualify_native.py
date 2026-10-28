from pathlib import Path
import json,subprocess,sys,shutil
O=Path('C:/work/fraktal-ab-s3j-20261024/r1_01');W=Path(json.loads((O/'native_preparation_location_01.json').read_bytes())['workspace']);R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools'
def run(name,cmd):
 with (W/(name+'.log')).open('xb') as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 with (W/(name+'_exit.json')).open('x') as f:json.dump(dict(exitCode=r.returncode,command=cmd),f,indent=2)
 print(name,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('prepared_readback_01',[sys.executable,str(T/'fraktal_ab_readback.py'),str(W/'s3i_r1_r2.L5X'),str(O/'prepared_readback_01.L5X')])
shutil.copyfile(W/'prepared_readback_01.log',W/'canonical_prepared_compare.json')
run('session_build_01',['dotnet','build',str(W/'session/S3iLifetimeSession.csproj'),'--nologo'])
run('gate_dry_check_01',[sys.executable,str(W/'gate_dry_check.py'),str(W/'gate_dry_check_01.json')])
run('authorization_negative_01',[sys.executable,str(W/'test_authorization.py')])
