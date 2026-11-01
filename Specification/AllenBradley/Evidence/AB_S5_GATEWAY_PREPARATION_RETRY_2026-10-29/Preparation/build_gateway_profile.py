"""Compile the native HMI gateway cases; never run the resulting application."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
D=Path(__file__).parent
H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
command=[str(SDK/'bin/cache/dart-sdk/bin/dart.exe'),str(SDK/'bin/cache/flutter_tools.snapshot'),
    'build','windows','--profile','--no-pub','--target=integration_test/ab_gateway_acceptance_test.dart',
    '--dart-define=fraktal.ab.gateway.fixture='+str(D/'gateway_fixture.json')]
subprocess.run(command,cwd=H,env=dict(os.environ,FLUTTER_ROOT=str(SDK)),check=True,
    creationflags=subprocess.CREATE_NO_WINDOW)
source=H/'build/windows/x64/runner/Profile';target=D/'qualification_app'
assert not target.exists()
shutil.copytree(source,target)
hashes={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper()
    for p in target.rglob('*') if p.is_file()}
with (D/'qualification_app_hashes.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(profile=True,controllerAccess=False,sha256=hashes),stream,indent=2)
print(json.dumps(dict(prebuilt=True,files=len(hashes),controllerAccess=False)))
