from pathlib import Path
import subprocess,os,sys
work=Path(__file__).parent;repo=work/'index_projection'
live=os.environ.copy();live.update(FRAKTAL_TIA_BRIDGE_LIVE='1',FRAKTAL_TIA_BRIDGE_EXPECT_CONNECTED='1',
    FRAKTAL_TIA_BRIDGE_CERT=str(work/'bench.der'),FRAKTAL_TIA_BRIDGE_OUTPUT=str(work/'hmi_recovered01.json'))
with (work/'hmi_recovered01.log').open('xb') as log:
    r=subprocess.run(['C:/Users/Siemens/Documents/FlutterSdk/flutter/bin/flutter.bat','test','--run-skipped','--concurrency=1','test/live_tia_press_bridge_test.dart','--reporter','expanded'],cwd=repo/'FraktalCore/HMI',env=live,stdout=log,stderr=subprocess.STDOUT)
print(dict(hmi_exit=r.returncode));
if r.returncode:print((work/'hmi_recovered01.log').read_text('utf-8-sig')[-5000:])
raise SystemExit(r.returncode)

