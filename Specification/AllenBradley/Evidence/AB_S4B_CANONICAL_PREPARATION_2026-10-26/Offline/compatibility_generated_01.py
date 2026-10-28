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
    output = C/f'compat_final_{stage}.L5X'
    subprocess.run([sys.executable, str(T/'fraktal_ab_generate.py'), str(SEED), str(output), '--declaration', declaration],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    rows.append(dict(stage=stage, pin=pin, actual=sha(output)))
output = C/'compat_final_s3g.L5X'; s3g_native.generate(SEED, output)
rows.append(dict(stage='s3g', pin='50E0F8977D975A14C5CD6F86A42AE56B8D4F995CD6A2AA52E071C252104DAE91', actual=sha(output)))
output = C/'compat_final_s3h.L5X'; gen.generate(s3h.application(), SEED, output)
rows.append(dict(stage='s3h', pin='BF456BCA68745C39D0903D0DE96B9B8AD4EC9DC502E809F38DA82599D2EFB1F2', actual=sha(output)))
output = C/'compat_final_s3i.L5X'; s3i_native.generate(SEED, output)
rows.append(dict(stage='s3i', pin='0F3A5F6DD762BED3819404025DAF6D5703511807B440C4988EACF5E494EC72C3', actual=sha(output)))
from dataclasses import replace
sys.path.insert(0,'C:/work/fraktal-ab-r1-r2-20261024/prepare_8f74e954758141dd81821a0c1316c2ef')
from candidate_profile import configure
configure()
p=C/'compat_final_r1_r2.L5X';s3i_native.generate(SEED,p)
rows.append(dict(stage='r1_r2',pin='C3E1FA7EEACB927B98AC0177E51D44A2E132BC1C1677ACC07583A46C02021333',actual=sha(p)))
import fraktal_ab_genealogy_s3j_demo as s3j
p=C/'compat_final_s3j.L5X';gen.generate(s3j.application(),SEED,p)
rows.append(dict(stage='s3j',pin='2F0B2CE73C2ECB69B1DD7F32BB1AE1D66550811A0EF49C1D65E9AE2C7A753EEA',actual=sha(p)))

for stage,declaration,pin in (
    ('s3k','fraktal_ab_genealogy_s3k_demo','B543336202821F95BC41A5A51441E86021F1BA9EFF28D42FABCD1AA83D7C782A'),
    ('s4a','fraktal_ab_genealogy_s4_demo','20F27F80CF9D0AEFEFA72EB64848927AE6076CF05CB544073575A55728825996')):
    output=C/f'compat_current_{stage}.L5X'
    subprocess.run([sys.executable,str(T/'fraktal_ab_generate.py'),str(SEED),str(output),'--declaration',declaration],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)
    rows.append(dict(stage=stage,pin=pin,actual=sha(output)))
output=C/'compat_current_press.L5X'
subprocess.run([sys.executable,str(T/'fraktal_ab_press_canonical_echo38.py'),str(SEED),str(output)],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)
rows.append(dict(stage='press',pin='6FD00A4825A2ADFA0BE9E662446905B53461C17CE40A50C1DE02733F530FBB02',actual=sha(output)))
result=dict(passed=all(r['pin']==r['actual'] for r in rows),images=len(rows),stages=rows)
with (C/'accepted_images_01.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(passed=result['passed'],images=len(rows),mismatched=[r['stage'] for r in rows if r['pin']!=r['actual']])))
raise SystemExit(0 if result['passed'] else 1)
