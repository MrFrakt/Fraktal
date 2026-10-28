"""Replay accepted generators in a fresh directory; call the press library API."""
from pathlib import Path
W = Path(__file__).parent
original = Path('C:/work/fraktal-ab-s4b-20261025/offline_01/compatibility_generated_01.py')
source = original.read_text(encoding='utf-8')
before = "subprocess.run([sys.executable,str(T/'fraktal_ab_press_canonical_echo38.py'),str(SEED),str(output)],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)"
assert source.count(before) == 1
source = source.replace(before, "import fraktal_ab_press_canonical_echo38 as press\npress.generate(SEED, output)")
output = W / 'compatibility_retry_01'
output.mkdir()
exec(compile(source, str(original), 'exec'), {'__file__': str(output / 'replay.py')})
