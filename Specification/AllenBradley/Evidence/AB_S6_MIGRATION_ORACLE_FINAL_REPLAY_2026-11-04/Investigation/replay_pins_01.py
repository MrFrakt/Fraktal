"""WP6.3: every current accepted image pin regenerates byte-identically.

1. The latest all-stage compatibility script (2026-10-26, 15 images) runs from
   its evidence-sealed copy, which must equal the workspace original, with the
   press-API substitution its own retry used, into a fresh folder.
2. S4b V6.8 and S5 each regenerate in a fresh process on the same seed, so the
   R1/R2 profile that script applies part-way through cannot leak into them.

Superseded or never-regenerated pins are recorded, not replayed. No bytecode
is written, so imports from original session folders leave nothing behind.
Generated L5X files stay under the work folder; only hashes enter evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
R = Path('C:/Users/SoftIndVM/Fraktal')
T = R / 'FraktalCore/PLC/Allen-Bradley/tools'
E = R / 'Specification/AllenBradley/Evidence'
G = Path(__file__).resolve().parents[1] / 'Gates'
WORK = Path(sys.argv[1])
SEED = Path('C:/work/echo38_5580_seed.L5X')
SEALED = E / 'AB_S4B_CANONICAL_PREPARATION_2026-10-26/Offline/compatibility_generated_01.py'
ORIGINAL = Path('C:/work/fraktal-ab-s4b-20261025/offline_01/compatibility_generated_01.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


assert sha(SEALED) == sha(ORIGINAL), 'sealed compatibility script differs from its workspace original'
source = SEALED.read_text(encoding='utf-8')
before = ("subprocess.run([sys.executable,str(T/'fraktal_ab_press_canonical_echo38.py'),str(SEED),"
          "str(output)],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)")
assert source.count(before) == 1
source = source.replace(before, 'import fraktal_ab_press_canonical_echo38 as press\npress.generate(SEED, output)')
staged = WORK / 'stages'
staged.mkdir(parents=True)
substituted = WORK / 'compatibility_source.py'
substituted.write_text(source, encoding='utf-8')
# The script writes beside its __file__; point that at the fresh folder.
child = subprocess.run([sys.executable, '-B', '-c',
                        'import sys; source=open(sys.argv[1],encoding="utf-8").read(); '
                        'exec(compile(source, sys.argv[2], "exec"), {"__file__": sys.argv[3], "__name__": "__main__"})',
                        str(substituted), str(ORIGINAL), str(staged / 'replay.py')],
                       cwd=R, capture_output=True, text=True)
stages = json.loads((staged / 'accepted_images_01.json').read_text(encoding='utf-8')) \
    if (staged / 'accepted_images_01.json').exists() else dict(passed=False, stages=[])
rows = [dict(r, source='2026-10-26 compatibility script') for r in stages['stages']]
for stage, declaration, pin in (
        ('s4b-v6.8', 'fraktal_ab_genealogy_s4b_demo',
         '60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E'),
        ('s5', 'fraktal_ab_genealogy_s4b_owner_demo',
         '979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162')):
    output = WORK / f'{stage}.L5X'
    run = subprocess.run([sys.executable, '-B', str(T / 'fraktal_ab_generate.py'), str(SEED), str(output),
                          '--declaration', declaration], cwd=R, capture_output=True, text=True)
    rows.append(dict(stage=stage, pin=pin, actual=sha(output) if output.exists() else None,
                     declaration=declaration, exitCode=run.returncode, source='fresh process'))
result = dict(schema='fraktal.ab.s6-wp63-pin-replay', schemaVersion=1,
              compatibilityScript=dict(sealed=SEALED.relative_to(R).as_posix(), sha256=sha(SEALED),
                                       exitCode=child.returncode, stdout=child.stdout[-2000:],
                                       stderr=child.stderr[-4000:]),
              seed=dict(path=str(SEED).replace('\\', '/'), sha256=sha(SEED)),
              images=len(rows), passed=bool(rows) and child.returncode == 0
              and all(r['pin'] == r['actual'] for r in rows),
              mismatched=[r['stage'] for r in rows if r['pin'] != r['actual']], stages=rows,
              notReplayed=[
                  dict(pin='22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06',
                       reason='S4b owner image superseded inside S5 by the recorded write-revision '
                              'correction (two generated assignments); its declaration now yields S5',
                       record='Evidence/AB_S5_GATEWAY_WRITE_REVISION_PREPARATION_2026-10-30.md'),
                  dict(pin='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084',
                       reason='legacy genealogy rollback ACD; plan section 4 downloads a hash-checked '
                              'copy and never regenerates it')],
              generatedFilesOutsideEvidence=str(WORK).replace('\\', '/'), controllerAccess=False)
with (G / 'pin_replay_01.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps({k: result[k] for k in ('images', 'passed', 'mismatched')}))
raise SystemExit(0 if result['passed'] else 1)
