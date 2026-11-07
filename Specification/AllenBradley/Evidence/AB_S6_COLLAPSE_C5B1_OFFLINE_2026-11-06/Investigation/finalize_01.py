from pathlib import Path
import json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');PY=sys.executable
for unused in range(7200):
 if (W/'ab_suite_01_exit.json').exists():break
 time.sleep(1)
else:raise TimeoutError('full AB suite has not finished')
assert json.loads((W/'ab_suite_01_exit.json').read_bytes())['exitCode']==0,'AB suite failed: no docs, seal or commit'
def run(label,*args):
 done=subprocess.run([PY,str(W/'run_logged.py'),label,str(R),*[str(a) for a in args]])
 assert done.returncode==0,label
run('finish_docs_01',PY,W/'finish_docs_01.py')
for label,args in [('ab_spec_02',['tools/check_ab_spec.py']),('ab_contracts_02',['tools/check_ab_contracts.py']),('consistency_02',['tools/check_consistency.py','--strict'])]:run(label,PY,*args)
run('seal_01',PY,W/'seal_01.py')
print('C5b1 sealed and ready for final commit review',flush=True)
