from pathlib import Path
import json,shutil,sys,subprocess
O=Path('C:/work/fraktal-ab-s3j-20261024/s3j_01');W=Path(json.loads((O/'native_preparation_location_02.json').read_bytes())['workspace']);ROOT=Path('C:/Users/SoftIndVM/Fraktal');T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
shutil.copyfile(O.parent/'prepare_bbed9750802a4d19976a31bef8d90123/test_authorization.py',W/'test_authorization.py')
p=W/'session/Program.cs';b=p.read_bytes().replace(b'S3i lifetime',b'S3j fieldbus').replace(b'S3i scope',b'S3j scope');p.write_bytes(b)
def run(name,args):
 with (W/(name+'.log')).open('xb') as f:p=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 with (W/(name+'_exit.json')).open('x') as f:json.dump(dict(exitCode=p.returncode,command=args),f,indent=2)
 print(name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
run('prepared_compare_01',[sys.executable,str(T/'fraktal_ab_readback.py'),str(W/'s3j.L5X'),str(O/'prepared_readback_02.L5X')])
shutil.copyfile(W/'prepared_compare_01.log',W/'canonical_prepared_compare.json')
run('session_build_01',['dotnet','build',str(W/'session/S3jSession.csproj'),'--nologo'])
run('download_gate_dry_check_01',[sys.executable,str(W/'gate_dry_check.py'),str(W/'download_gate_dry_check_01.json')])
run('authorization_negative_01',[sys.executable,str(W/'test_authorization.py')])
