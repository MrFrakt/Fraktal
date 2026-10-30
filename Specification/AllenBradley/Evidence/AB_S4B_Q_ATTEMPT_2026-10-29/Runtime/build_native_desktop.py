"""Prebuild native-endpoint acceptance before candidate download; no controller I/O."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
D=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
env=dict(os.environ,FLUTTER_ROOT=str(SDK))
command=[str(SDK/'bin/cache/dart-sdk/bin/dart.exe'),str(SDK/'bin/cache/flutter_tools.snapshot'),
 'build','windows','--profile','--no-pub','--target=integration_test/ab_desktop_acceptance_test.dart',
 '--dart-define=fraktal.cip.trace=true',
 '--dart-define=fraktal.ab.desktop.endpoint=cip://127.0.0.1?slot=0&serial=601FC87B',
 '--dart-define=fraktal.ab.desktop.output='+str(D/'desktop_profile')]
subprocess.run(command,cwd=H,env=env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
source=H/'build/windows/x64/runner/Profile';target=D/'desktop_app'
assert not target.exists();shutil.copytree(source,target)
hashes={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in target.rglob('*') if p.is_file()}
with (D/'desktop_app_hashes.json').open('x',encoding='utf-8') as f:
    json.dump(dict(profile=True,rehearsal=False,endpoint='cip://127.0.0.1?slot=0&serial=601FC87B',
                  controllerAccess=False,sha256=hashes),f,indent=2)
print(json.dumps(dict(prebuilt=True,files=len(hashes),controllerAccess=False)))
