from pathlib import Path
import os,subprocess,sys
root=Path('C:/Projects/Fraktal')
work=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Config_Transactions_20261011'
dart=Path('C:/Users/Siemens/Documents/FlutterSdk/flutter/bin/cache/dart-sdk/bin/dart.exe')
command=[str(dart),'--packages='+str(root/'FraktalCore/HMI/gateway/.dart_tool/package_config.json'),str(root/'FraktalCore/PLC/Siemens/Tests/Manifest/run_gateway.dart'),str(work/'gateway.certificate.der'),str(root/'FraktalCore/PLC/Siemens/Spikes/S12_TypeMap/simulator.ps1'),str(work/'gateway_final.stop')]
with Path(sys.argv[1]).open('xb') as stream:
    result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,cwd=root/'FraktalCore/HMI/gateway')
raise SystemExit(result.returncode)
