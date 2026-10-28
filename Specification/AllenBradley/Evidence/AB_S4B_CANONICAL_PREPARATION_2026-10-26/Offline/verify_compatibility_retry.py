from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;destination=W/'compatibility_retry_01';destination.mkdir()
script=(W/'compatibility_generated_01.py').read_text()
before="subprocess.run([sys.executable,str(T/'fraktal_ab_press_canonical_echo38.py'),str(SEED),str(output)],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)"
after="from fraktal_ab_press_canonical_echo38 import generate as generate_press\ngenerate_press(SEED,output)"
assert script.count(before)==1
with (destination/'verify.py').open('x') as stream:stream.write(script.replace(before,after))
raise SystemExit(subprocess.run([sys.executable,str(destination/'verify.py')]).returncode)
