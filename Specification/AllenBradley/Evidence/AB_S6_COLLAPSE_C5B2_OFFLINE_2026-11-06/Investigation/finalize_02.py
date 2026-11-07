from pathlib import Path
import json,subprocess,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
for label in ('ab_suite_02','dart_tests_01'):
 receipt=W/(label+'_exit.json')
 while not receipt.exists():time.sleep(15)
 assert json.loads(receipt.read_bytes())['exitCode']==0,label

def run(label,cwd,*command):
 subprocess.run([sys.executable,str(W/'run_logged.py'),label,str(cwd),*map(str,command)],check=True)
run('finish_docs_03',R,sys.executable,W/'finish_docs_03.py')
run('ab_spec_02',R,sys.executable,'tools/check_ab_spec.py')
run('ab_contracts_02',R,sys.executable,'tools/check_ab_contracts.py')
run('consistency_02',R,sys.executable,'tools/check_consistency.py','--strict')
run('seal_03',R,sys.executable,W/'seal_03.py')
print('Documentation and evidence sealed; awaiting final review before commit',flush=True)
