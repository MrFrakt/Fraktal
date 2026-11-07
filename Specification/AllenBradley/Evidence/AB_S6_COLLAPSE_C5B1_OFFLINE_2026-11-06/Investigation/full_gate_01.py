from pathlib import Path
import hashlib,json,subprocess,sys,time
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';PY=sys.executable
for unused in range(2400):
 if (W/'focused_02_exit.json').exists():break
 time.sleep(1)
else:raise TimeoutError('focused tests did not finish')
assert json.loads((W/'focused_02_exit.json').read_bytes())['exitCode']==0,'focused tests failed; full suite not started'
for name in ('schema_press_01.json','token_proof_01.json'):assert json.loads((W/name).read_bytes())['passed']
prefix='FraktalCore/PLC/Allen-Bradley/tools'
tracked=subprocess.check_output(['git','ls-files','-z','--',prefix],cwd=R).decode().split('\0')
extra=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','--',prefix],cwd=R).decode().split('\0')
files=[dict(path=p,sha256=hashlib.sha256((R/p).read_bytes()).hexdigest().upper()) for p in sorted(set(tracked+extra)-{''})]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
with (W/'tools_freeze_01.json').open('x',encoding='utf-8') as f:json.dump(dict(head=head,files=files),f,indent=2)
print('Frozen',len(files),'source files',flush=True)
result=subprocess.run([PY,str(W/'run_logged.py'),'ab_suite_01',str(T),PY,'-m','unittest','discover','-s','.','-t','.','-q'])
assert all(hashlib.sha256((R/e['path']).read_bytes()).hexdigest().upper()==e['sha256'] for e in files),'sources changed during suite'
raise SystemExit(result.returncode)
