from pathlib import Path
import hashlib,json,subprocess,sys
from gateway_stage import gateway_arguments,ready
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
package=D/'gateway_package';exe=package/'fraktal_gateway.exe'
for name,pin in json.loads((D/'gateway_package_hashes.json').read_bytes())['sha256'].items():assert hashlib.sha256((package/name).read_bytes()).hexdigest().upper()==pin
subprocess.run([sys.executable,str(D/'scripts/guard_echo.py')],check=True)
args=gateway_arguments(exe,package,'echo-read-overlap',18080,False)
args[args.index('--commissioning-ttl-minutes')+1]='5'
log=(D/'read_overlap_gateway_02.log').open('x',encoding='utf-8')
process=subprocess.Popen(args,cwd=package,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    ready(process,18080,False)
    result=subprocess.run(['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',
        '--packages='+str(D/'dart_package_config.json'),str(D/'read_client_overlap_02.dart')],cwd=R,timeout=120)
    raise SystemExit(result.returncode)
finally:
    if process.poll() is None:process.terminate();process.wait(timeout=15)
    log.close()
