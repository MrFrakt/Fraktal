"""Credential-wrapper entry point for the isolated production gateway."""
import os
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
if __name__=='__main__':
    log=Path(sys.argv[1]);stop=log.with_suffix('.stop')
    assert not stop.exists()
    certificate=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Config_Transactions_20261011/gateway.certificate.der'
    dart=Path('C:/Users/Siemens/Documents/FlutterSdk/flutter/bin/cache/dart-sdk/bin/dart.exe')
    packages=REPO/'FraktalCore/HMI/gateway/.dart_tool/package_config.json'
    script=HERE.parent/'Manifest/run_gateway.dart'
    simulator=HERE.parents[1]/'Spikes/S12_TypeMap/simulator.ps1'
    with log.open('xb') as stream:
        result=subprocess.run([str(dart),'--packages='+str(packages),str(script),str(certificate),str(simulator),str(stop)],stdout=stream,stderr=subprocess.STDOUT)
    raise SystemExit(result.returncode)
