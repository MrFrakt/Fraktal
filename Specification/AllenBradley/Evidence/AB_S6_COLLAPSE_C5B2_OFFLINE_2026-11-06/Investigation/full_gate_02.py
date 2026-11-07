from pathlib import Path
import hashlib,json,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
for label in ('clients_07','native_replay_01','token_proof_02','predicate_accounting_01'):
 assert json.loads((W/(label+'_exit.json')).read_bytes())['exitCode']==0,label
assert json.loads((W/'schema_press_01.json').read_bytes())['passed']
assert json.loads((W/'prepare_press_02.json').read_bytes())['passed']
prefix='FraktalCore/PLC/Allen-Bradley/tools'
paths=[]
for args in (['ls-files','-z','--',prefix],['ls-files','--others','--exclude-standard','-z','--',prefix]):
 paths+=subprocess.check_output(['git',*args],cwd=R).decode().split('\0')
files=[dict(path=p,sha256=hashlib.sha256((R/p).read_bytes()).hexdigest().upper()) for p in sorted(set(paths)-{''})]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
with (W/'tools_freeze_02.json').open('x',encoding='utf-8') as f:json.dump(dict(head=head,files=files),f,indent=2)
print('Frozen',len(files),'source files',flush=True)
code=subprocess.run([sys.executable,str(W/'run_logged.py'),'ab_suite_02',str(T),sys.executable,'-m','unittest','discover','-s','.','-t','.','-v']).returncode
assert all(hashlib.sha256((R/e['path']).read_bytes()).hexdigest().upper()==e['sha256'] for e in files)
raise SystemExit(code)
