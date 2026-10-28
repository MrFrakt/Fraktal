"""With canonical_table_driven off, every accepted stage image regenerates byte-identically."""
from pathlib import Path
import ast, hashlib, json, os, subprocess, sys

ROOT = Path('C:/Users/SoftIndVM/Fraktal')
T = ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
C = Path(__file__).parent
SEED = Path('C:/work/echo38_5580_seed.L5X')
sys.path.insert(0, str(T))
os.environ['FRAKTAL_AB_DECLARATION'] = 'fraktal_ab_genealogy_demo'
import fraktal_ab_generate as gen
import fraktal_ab_s3g_native_checks as s3g_native
import fraktal_ab_s3i_native_checks as s3i_native
import fraktal_ab_genealogy_s3h_demo as s3h
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
script = Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009/compatibility.py').read_text()
tree = ast.parse(script)
stages = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
                               and any(isinstance(t, ast.Name) and t.id == 'stages' for t in n.targets)))
stages.append(('s3f', 'B71E30ABBE8221AAA39A0DF8EEB934897FE0A4B0711047EFDC7D653A20AE7CF3', 'fraktal_ab_genealogy_s3f_demo', None, None))
rows = []
for stage, pin, declaration, *unused in stages:
    output = C/f'compat2_{stage}.L5X'
    subprocess.run([sys.executable, str(T/'fraktal_ab_generate.py'), str(SEED), str(output), '--declaration', declaration],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    rows.append(dict(stage=stage, pin=pin, actual=sha(output)))
output = C/'compat2_s3g.L5X'; s3g_native.generate(SEED, output)
rows.append(dict(stage='s3g', pin='50E0F8977D975A14C5CD6F86A42AE56B8D4F995CD6A2AA52E071C252104DAE91', actual=sha(output)))
output = C/'compat2_s3h.L5X'; gen.generate(s3h.application(), SEED, output)
rows.append(dict(stage='s3h', pin='BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2', actual=sha(output)))
output = C/'compat2_s3i.L5X'; s3i_native.generate(SEED, output)
rows.append(dict(stage='s3i', pin='0F3A5F6DD762BED3819404025DAF6D5703511807B440C4988EACF5E494EC72C3', actual=sha(output)))
report = dict(passed=all(r['pin'] == r['actual'] for r in rows), stages=rows)
with (C/'compatibility_02.json').open('x') as out:
    json.dump(report, out, indent=2)
print(json.dumps(dict(passed=report['passed'], stages=len(rows),
                      mismatched=[r['stage'] for r in rows if r['pin'] != r['actual']])))
raise SystemExit(0 if report['passed'] else 1)
