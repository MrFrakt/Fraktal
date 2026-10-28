from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
source=R/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Modules'
target=W.parent/'PLC/TwinCAT/Framework/Fraktal_Modules';assert not target.exists()
files=subprocess.check_output(['git','ls-files','-z','--',source.relative_to(R).as_posix()],cwd=R).decode().split('\0')
rows=[]
for name in files:
    if not name:continue
    p=R/name
    if not p.is_file():continue
    out=target/p.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
    assert out.read_bytes()==p.read_bytes()
    rows.append(dict(source=str(p),copy=str(out),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
with (W/'isolated_test_dependencies_01.json').open('x',encoding='utf-8') as stream:json.dump(dict(passed=True,files=rows),stream,indent=2)
print(json.dumps(dict(passed=True,files=len(rows),purpose='Unchanged sibling PLC module-type inventory for HMI semantic icon gate')))
