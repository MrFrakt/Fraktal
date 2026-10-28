from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
source=R/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DeviceCMs'
target=W.parent/'PLC/TwinCAT/Framework/Fraktal_Core/DeviceCMs';assert not target.exists()
rows=[]
for name in subprocess.check_output(['git','ls-files','-z','--',source.relative_to(R).as_posix()],cwd=R).decode().split('\0'):
    if not name:continue
    p=R/name
    if not p.is_file():continue
    out=target/p.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
    assert out.read_bytes()==p.read_bytes();rows.append(dict(source=str(p),copy=str(out),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
with (W/'isolated_core_dependencies_01.json').open('x',encoding='utf-8') as stream:json.dump(dict(passed=True,files=rows),stream,indent=2)
print(json.dumps(dict(passed=True,files=len(rows))))
