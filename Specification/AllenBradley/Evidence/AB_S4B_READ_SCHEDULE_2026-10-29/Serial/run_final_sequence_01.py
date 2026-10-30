"""One unchanged-source consecutive rehearsal sequence, retaining every outcome."""
from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
for label,seed in [('profile_07',8),('profile_08',7),('profile_09',9)]:
 result=subprocess.run([sys.executable,str(W/'run_logged.py'),'rehearsal_'+label,
  sys.executable,str(W/'run_rehearsal_01.py'),'--mode','profile','--label',label,'--seed',str(seed)])
 if result.returncode:raise SystemExit(result.returncode)
raise SystemExit(subprocess.run([sys.executable,str(W/'run_logged.py'),'rehearsal_debug_01',
 sys.executable,str(W/'run_rehearsal_01.py'),'--mode','debug','--label','debug_01','--seed','9']).returncode)
