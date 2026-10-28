from pathlib import Path
import json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
jobs=[('ab_suite_02',[sys.executable,'-m','unittest','discover','-s','FraktalCore/PLC/Allen-Bradley/tools','-t','FraktalCore/PLC/Allen-Bradley/tools']),('root_tests_02',[sys.executable,'-m','unittest','tools.test_check_consistency','tools.test_check_ab_spec','tools.test_check_ab_contracts']),('ab_spec_02',[sys.executable,'tools/check_ab_spec.py']),('ab_contracts_02',[sys.executable,'tools/check_ab_contracts.py']),('consistency_02',[sys.executable,'tools/check_consistency.py','--strict'])]
for name,cmd in jobs:
 start=time.time()
 with (W/(name+'.log')).open('xb') as f:done=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 result=dict(name=name,exitCode=done.returncode,seconds=time.time()-start,command=cmd)
 with (W/(name+'_exit.json')).open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
 if done.returncode:sys.exit(done.returncode)
