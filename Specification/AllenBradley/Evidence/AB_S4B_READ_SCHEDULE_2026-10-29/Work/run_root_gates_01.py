from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
commands=[('root_01',[sys.executable,'-m','unittest','tools.test_check_ab_spec',
 'tools.test_check_ab_contracts','tools.test_check_consistency']),
 ('ab_spec_01',[sys.executable,'tools/check_ab_spec.py']),
 ('ab_contracts_01',[sys.executable,'tools/check_ab_contracts.py']),
 ('consistency_01',[sys.executable,'tools/check_consistency.py','--strict']),
 ('whitespace_01',['git','-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--check']),
 ('final_guard_01',[sys.executable,'C:/work/fraktal-ab-s4b-q-20261029/session_01/scripts/guard_echo.py']),
 ('final_inspect_01',['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect']),
 ('final_preflight_01',[sys.executable,'C:/work/fraktal-ab-s4b-msp-20261027/session_01/scripts/preflight.py','--verify-only'])]
for label,command in commands:
 result=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*command],cwd=R)
 if result.returncode:raise SystemExit(result.returncode)
