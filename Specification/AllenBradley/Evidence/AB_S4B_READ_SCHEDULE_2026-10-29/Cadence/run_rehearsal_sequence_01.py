from pathlib import Path
import json,subprocess,sys
W=Path(__file__).parent
for gate in ['locked_dependencies_01','full_hmi_02','analyze_02','windows_profile_02','plc_transfer_01',
 'configuration_stage_tests_01','peer_qualification_02']:
 assert json.loads((W/(gate+'_exit.json')).read_bytes())['exitCode']==0,gate
for label,seed in [('profile_01',8),('profile_02',7),('profile_03',9)]:
 code=subprocess.run([sys.executable,str(W/'run_logged.py'),'rehearsal_'+label,
  sys.executable,str(W/'run_rehearsal_01.py'),'--mode','profile','--label',label,'--seed',str(seed)]).returncode
 if code:raise SystemExit(code)
subprocess.run([sys.executable,str(W/'run_logged.py'),'rehearsal_debug_01',sys.executable,
 str(W/'run_rehearsal_01.py'),'--mode','debug','--label','debug_01','--seed','9'])
raise SystemExit(subprocess.run([sys.executable,str(W/'run_logged.py'),'verify_rehearsals_01',
 sys.executable,str(W/'verify_rehearsals_01.py')]).returncode)
