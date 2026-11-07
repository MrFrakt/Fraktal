from pathlib import Path
import json,subprocess,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
receipt=W/'ab_suite_01_exit.json'
while not receipt.exists():time.sleep(15)
assert json.loads(receipt.read_bytes())['exitCode']==0
def run(label,*command):subprocess.run([sys.executable,str(W/'run_logged.py'),label,str(R),*map(str,command)],check=True)
run('finish_docs_01',sys.executable,W/'finish_docs_01.py')
run('consistency_01',sys.executable,'tools/check_consistency.py','--strict')
run('seal_01',sys.executable,W/'seal_01.py')
print('Offline gates and evidence complete; ready for review and commit')
