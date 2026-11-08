import hashlib
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, 'FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_generate as gen
from test_fraktal_ab_generate import SEED_38

profiles = [
    'fraktal_ab_genealogy_s6_collapse_demo',
    'fraktal_ab_press_s6_collapse_echo38',
    'fraktal_ab_press_s6_shelving_echo38',
]

results = {}
for name in profiles:
    mod = __import__(name)
    app = mod.application()
    with tempfile.TemporaryDirectory() as folder:
        seed = Path(folder) / 'seed.L5X'
        seed.write_text(SEED_38, encoding='utf-8')
        out = Path(folder) / f'{name}.L5X'
        gen.generate(app, seed, out)
        data = out.read_bytes()
        sha = hashlib.sha256(data).hexdigest().upper()
        text = data.decode('utf-8')
        root = ET.fromstring(data)
        routines = root.findall('.//Routine')
        # ST token count
        tokens = 0
        for r in routines:
            for line in r.findall('.//Line'):
                if line.text:
                    tokens += len(line.text.split())
        results[name] = {
            'sha256': sha,
            'bytes': len(data),
            'routines': len(routines),
            'st_tokens': tokens,
        }
        print(f'{name}:')
        print(f'  SHA256: {sha}')
        print(f'  Bytes: {len(data)}')
        print(f'  Routines: {len(routines)}')
        print(f'  ST Tokens: {tokens}')
