from pathlib import Path
import subprocess,sys
W=Path(__file__).parent
old=Path('C:/work/fraktal-ab-s4-20261025/offline_01/verify_compatibility_final.py').read_text()
old=old[:old.index("report = dict(")]+old[old.index('from dataclasses import replace'):]
old=old[:old.index("result=dict(")]+'''
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
'''
script=W/'compatibility_generated_01.py'
with script.open('x') as stream:stream.write(old)
raise SystemExit(subprocess.run([sys.executable,str(script)]).returncode)
