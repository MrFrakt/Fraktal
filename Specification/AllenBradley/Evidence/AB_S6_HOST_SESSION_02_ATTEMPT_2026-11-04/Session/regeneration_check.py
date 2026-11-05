"""HEAD must regenerate the pinned candidate L5X byte for byte; also build the adapter at HEAD."""
from pathlib import Path
import hashlib, json, subprocess, sys, tempfile

D = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
SOURCE = '5ADEF279CB93BE1D53ED067915C8F7C21434658DD32C633E7DC3176D1BEDE2FA'
DART = 'C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
assert not dirty, 'working tree must be clean'
with tempfile.TemporaryDirectory() as folder:
    output = Path(folder) / 'regenerated.L5X'
    subprocess.run([sys.executable, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_generate.py'),
                    'C:/work/echo38_5580_seed.L5X', str(output), '--declaration', 'fraktal_ab_genealogy_s6_host_demo'],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    regenerated = hashlib.sha256(output.read_bytes()).hexdigest().upper()
(D / 'bin').mkdir()
subprocess.run([DART, 'compile', 'exe', 'bin/fraktal_host_adapter.dart', '-o', str(D / 'bin/fraktal_host_adapter.exe')],
               cwd=ROOT / 'FraktalCore/HMI/gateway', check=True)
result = dict(repositoryHead=head, regeneratedSha256=regenerated, pinnedSourceSha256=SOURCE,
              identical=regenerated == SOURCE,
              adapterSha256=hashlib.sha256((D / 'bin/fraktal_host_adapter.exe').read_bytes()).hexdigest().upper())
with (D / 'regeneration_check.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
raise SystemExit(0 if result['identical'] else 1)
