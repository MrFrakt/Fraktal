from pathlib import Path
import json,subprocess,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
receipt=W/'ab_suite_01_exit.json'
while not receipt.exists():time.sleep(15)
assert json.loads(receipt.read_bytes())['exitCode']==0

def run(label,*command):subprocess.run([sys.executable,str(W/'run_logged.py'),label,str(R),*map(str,command)],check=True)
run('finish_docs_02',sys.executable,W/'finish_docs_02.py')
run('ab_spec_01',sys.executable,'tools/check_ab_spec.py')
run('ab_contracts_01',sys.executable,'tools/check_ab_contracts.py')
run('consistency_01',sys.executable,'tools/check_consistency.py','--strict')
run('seal_02',sys.executable,W/'seal_02.py')
print('Evidence sealed; ready for final review and commit')
