from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
text=(W/'seal_attempt_01.py').read_text(encoding='utf-8').replace("('qualification_run_01','candidate_regressions'))","('qualification_run_01','candidate_regressions','dart_observer'))")
text=text.replace("W/'seal_attempt_01.py']","W/'seal_attempt_01.py',W/'seal_attempt_v2.py',W/'seal_attempt_01.log',W/'seal_attempt_01_exit.json']")
with (W/'seal_attempt_fixed.py').open('x',encoding='utf-8',newline='') as stream:stream.write(text)
raise SystemExit(subprocess.run([sys.executable,str(W/'seal_attempt_fixed.py')]).returncode)
