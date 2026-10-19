"""Compare full native outputs using committed versus current host adapter."""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
TOOLS = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
OUT = Path(__file__).parent
sys.path.insert(0, str(TOOLS))
import fraktal_ab_generate as gen
import fraktal_ab_host_events as current
import fraktal_ab_tower_demo as fixture

blob = subprocess.run(['git', 'show', 'HEAD:FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_host_events.py'],
                      cwd=ROOT, check=True, capture_output=True).stdout
old = types.ModuleType('committed_host_adapter')
exec(compile(blob, '<committed host adapter>', 'exec'), old.__dict__)
seed = Path('C:/work/echo38_5580_seed.L5X')
rows = []
try:
    for name, module in [('committed', old), ('current', current)]:
        gen.host = module
        path = OUT/(name+'_tower.L5X')
        gen.generate(fixture.application(), seed, path)
        rows.append(dict(name=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                         bytes=path.stat().st_size))
finally:
    gen.host = current
result = dict(seedSha256=hashlib.sha256(seed.read_bytes()).hexdigest().upper(), outputs=rows,
              byteIdentical=rows[0]['sha256'] == rows[1]['sha256'])
with (OUT/'generation.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
if not result['byteIdentical']:
    raise SystemExit(1)
