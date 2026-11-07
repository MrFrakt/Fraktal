from pathlib import Path
import json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');PY=sys.executable
while not (W/'ab_suite_03_exit.json').exists():time.sleep(15)
assert json.loads((W/'ab_suite_03_exit.json').read_bytes())['exitCode']==0,'AB suite failed'
def run(label,*cmd):subprocess.run([PY,str(W/'run_logged.py'),label,str(R),*map(str,cmd)],check=True)
run('finish_docs_03',PY,W/'finish_docs_03.py')
run('consistency_01',PY,R/'tools/check_consistency.py','--strict')
run('seal_03',PY,W/'seal_03.py')
