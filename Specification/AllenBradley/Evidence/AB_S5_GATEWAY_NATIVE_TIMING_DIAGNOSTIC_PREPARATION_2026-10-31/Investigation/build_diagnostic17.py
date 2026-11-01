import sys
sys.path.pop(0)
from pathlib import Path
import hashlib,json,shutil,subprocess

W=Path('C:/work/fraktal-ab-s5-20261029');D=W/'session_17';P=W/'session_16'
H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
normal=json.loads((P/'gateway_package_hashes.json').read_bytes())['sha256']
target=D/'gateway_package'
assert not target.exists() and not (D/'gateway_trace.exe').exists()
target.mkdir()
for name,pin in normal.items():
    original=P/'gateway_package'/name
    assert sha(original)==pin
    if name=='fraktal_gateway.exe':continue
    destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(original,destination)
command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',
    'compile','exe','-Dfraktal.cip.trace=true','bin/fraktal_gateway.dart','-o',str(D/'gateway_trace.exe')]
subprocess.run(command,cwd=H/'gateway',check=True,creationflags=subprocess.CREATE_NO_WINDOW)
shutil.copyfile(D/'gateway_trace.exe',target/'fraktal_gateway.exe')
hashes={p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file()}
assert hashes.keys()==normal.keys()
assert [name for name in hashes if hashes[name]!=normal[name]]==['fraktal_gateway.exe']
with (D/'gateway_package_hashes.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(controllerAccess=False,diagnosticOnly=True,sha256=hashes),stream,indent=2)
with (D/'diagnostic_package_derivation.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,controllerAccess=False,diagnosticOnly=True,
        define='fraktal.cip.trace=true',changedFiles=['fraktal_gateway.exe'],
        normalManifestSha256=sha(P/'gateway_package_hashes.json'),
        normalWebUnchanged=True,command=command,normalPackage=normal),stream,indent=2)
print(json.dumps(dict(passed=True,diagnosticOnly=True,changedFiles=['fraktal_gateway.exe'],controllerAccess=False)))
