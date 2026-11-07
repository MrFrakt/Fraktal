from pathlib import Path
import hashlib,json,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
for label in ('focused_05','predicates_02','schema_02','annotations_replay_01','root_suite_01'):
 assert json.loads((W/(label+'_exit.json')).read_bytes())['exitCode']==0,label
prefix='FraktalCore/PLC/Allen-Bradley/tools';paths=[]
for args in (['ls-files','-z','--',prefix],['ls-files','--others','--exclude-standard','-z','--',prefix]):
 paths+=subprocess.check_output(['git',*args],cwd=R).decode().split('\0')
files=[dict(path=p,sha256=hashlib.sha256((R/p).read_bytes()).hexdigest().upper()) for p in sorted(set(paths)-{''})]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
with (W/'tools_freeze_01.json').open('x',encoding='utf-8') as f:json.dump(dict(head=head,files=files),f,indent=2)
print('Frozen',len(files),'source files',flush=True)
code=subprocess.run([sys.executable,str(W/'run_logged.py'),'ab_suite_01',str(T),sys.executable,'-m','unittest','discover','-s','.','-t','.','-v']).returncode
assert all(hashlib.sha256((R/e['path']).read_bytes()).hexdigest().upper()==e['sha256'] for e in files)
raise SystemExit(code)
