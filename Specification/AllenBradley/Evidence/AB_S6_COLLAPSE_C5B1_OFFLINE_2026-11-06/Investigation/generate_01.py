from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';P=W/'prepare_01'
results=[]
for name,decl in [('press','fraktal_ab_press_s6_collapse_echo38'),('genealogy','fraktal_ab_genealogy_s6_collapse_demo')]:
 args=[sys.executable,str(T/'fraktal_ab_generate.py'),'C:/work/echo38_5580_seed.L5X',str(P/(name+'.L5X')),'--declaration',decl]
 done=subprocess.run([sys.executable,str(W/'run_logged.py'),'generate_'+name+'_01',str(R),*args]);assert done.returncode==0
 results.append(dict(profile=name,sha256=hashlib.sha256((P/(name+'.L5X')).read_bytes()).hexdigest().upper()))
with (P/'source_pins.json').open('x',encoding='utf-8') as f:json.dump(results,f,indent=2)
