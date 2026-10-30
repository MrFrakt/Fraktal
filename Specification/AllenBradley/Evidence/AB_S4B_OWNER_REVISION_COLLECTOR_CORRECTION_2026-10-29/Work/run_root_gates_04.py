from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
commands=[('root_04',[sys.executable,'-m','unittest','tools.test_check_ab_spec',
 'tools.test_check_ab_contracts','tools.test_check_consistency']),
 ('ab_spec_04',[sys.executable,'tools/check_ab_spec.py']),
 ('ab_contracts_04',[sys.executable,'tools/check_ab_contracts.py']),
 ('consistency_04',[sys.executable,'tools/check_consistency.py','--strict'])]
for label,command in commands:
 result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*command],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
