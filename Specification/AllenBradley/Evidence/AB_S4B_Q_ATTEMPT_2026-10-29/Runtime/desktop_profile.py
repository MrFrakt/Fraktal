"""Guarded strict LIVE profile desktop from a prebuilt, hash-bound binary."""
from pathlib import Path
import json,os,subprocess,sys
from qualification_session_v2 import authorize
from desktop_coverage import validate_coverage
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
SDK=Path('C:/work/fraktal-toolchains/flutter-3.47.5')
def main():
    authorize(json.loads((D/'authorization.json').read_bytes()))
    assert not (D/'desktop_profile').exists()
    env=dict(os.environ,FLUTTER_ROOT=str(SDK),FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY=str(D/'desktop_expected_inventory.json'))
    for name in ['FRAKTAL_AB_DESKTOP_FIXTURE','FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE','FRAKTAL_AB_DESKTOP_FORCE_STARTUP_FAILURE_FIXTURE']:
        env.pop(name,None)
    command=[str(SDK/'bin/cache/dart-sdk/bin/dart.exe'),str(SDK/'bin/cache/flutter_tools.snapshot'),
      'drive','--profile','--no-pub','-d','windows','--driver=test_driver/integration_test.dart',
      '--target=integration_test/ab_desktop_acceptance_test.dart',
      '--use-application-binary='+str(D/'desktop_app/fraktal_hmi.exe')]
    subprocess.run(command,cwd=H,env=env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    value=json.loads((D/'desktop_profile/result.json').read_bytes())
    validate_coverage(value,json.loads((D/'desktop_expected_inventory.json').read_bytes()),require_live=True)
    assert value['desktopLiveAccepted'] and value['nativeFreshnessClaim'] and not value['rehearsal']
    with (D/'desktop_semantic_acceptance.json').open('x',encoding='utf-8') as f:
        json.dump(dict(passed=True,live=True,profile=True,modules=len(value['modules']),views=len(value['shots']),readOnly=True),f,indent=2)
if __name__=='__main__':main()
