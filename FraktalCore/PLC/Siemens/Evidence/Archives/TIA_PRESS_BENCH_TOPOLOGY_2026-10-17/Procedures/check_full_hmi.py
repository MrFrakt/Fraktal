from pathlib import Path
import subprocess,sys,json
w=Path(__file__).parent;repo=Path('C:/Projects/Fraktal');out=w/'index_projection_final';hmi=out/'FraktalCore/HMI'
flutter='C:/Users/Siemens/Documents/FlutterSdk/flutter/bin/flutter.bat'
files=[p for p in subprocess.check_output(['git','ls-files','-z','FraktalCore/HMI'],cwd=repo).decode().split('\0') if p and not (out/p).exists()]
if files:subprocess.run(['git','checkout-index','--stdin','-z','--prefix='+out.as_posix()+'/'],cwd=repo,input=('\0'.join(files)+'\0').encode(),check=True)
with (w/'final_flutter_version.json').open('xb') as f:subprocess.run([flutter,'--version','--machine'],cwd=hmi,stdout=f,stderr=subprocess.STDOUT,check=True)
lock=subprocess.check_output(['git','show',':FraktalCore/HMI/pubspec.lock'],cwd=repo);assert (hmi/'pubspec.lock').read_bytes()==lock,'Focused test changed dependency lock'
results={}
for label,args in [('hmi_analyze',['analyze','--no-pub']),('hmi_all',['test','--concurrency=2','--reporter','expanded'])]:
    with (w/('final_'+label+'.log')).open('xb') as f:r=subprocess.run([flutter]+args,cwd=hmi,stdout=f,stderr=subprocess.STDOUT)
    results[label]=r.returncode;print({label:r.returncode},flush=True)
    assert (hmi/'pubspec.lock').read_bytes()==lock,'Flutter changed dependency lock'
    if r.returncode:print((w/('final_'+label+'.log')).read_text('utf-8-sig')[-6000:]);raise SystemExit(r.returncode)
(w/'final_hmi_all_checks.json').write_text(json.dumps(results,indent=2)+'\n')
