from pathlib import Path
import json,shutil,subprocess,sys,time
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
while not (W/'generate_press_01_exit.json').exists():time.sleep(5)
assert json.loads((W/'generate_press_01_exit.json').read_bytes())['exitCode']==0
P=W/'prepare_01';P.mkdir(exist_ok=False);shutil.copyfile(W/'press_01.L5X',P/'press.L5X')
subprocess.run([sys.executable,str(W/'prepare_press_01.py')],check=True)
