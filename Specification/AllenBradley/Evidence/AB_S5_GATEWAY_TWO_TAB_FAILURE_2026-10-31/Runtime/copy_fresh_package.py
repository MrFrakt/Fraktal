from pathlib import Path
import hashlib,json,shutil
D=Path(__file__).parent
assert json.loads((D.parent/'idle_connection_package_01_exit.json').read_bytes())['exitCode']==0
source=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/build/gateway/windows-x64')
target=D/'gateway_package'
assert not target.exists()
shutil.copytree(source,target)
hashes={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in target.rglob('*') if p.is_file()}
with (D/'gateway_package_hashes.json').open('x',encoding='utf-8') as stream:json.dump(dict(controllerAccess=False,sha256=hashes),stream,indent=2)
print(json.dumps(dict(passed=True,files=len(hashes),controllerAccess=False)))
