import sys
sys.path.pop(0)
from pathlib import Path
import hashlib,json

W=Path('C:/work/fraktal-ab-s5-20261029');D=W/'session_17'
H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
bases=[H/name for name in ('lib','packages/fraktal_opcua_client/lib','gateway/lib','gateway/bin','test','integration_test')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
pins=json.loads((W/'session_16/source_bindings.json').read_bytes())['sha256']
current={str(path):sha(path) for base in bases for path in base.rglob('*.dart')}
expected={name:pin for name,pin in pins.items() if Path(name).suffix=='.dart' and any(Path(name).is_relative_to(base) for base in bases)}
assert current==expected,'HMI source set/hash changed since the complete 788-test gate'
for label in ('two_tab_shared_full_hmi_01','two_tab_shared_analyze_01','two_tab_shared_locked_01',
    'two_tab_shared_gateway_tests_01','two_tab_shared_package_01'):
    assert json.loads((W/(label+'_exit.json')).read_bytes())['exitCode']==0,label
with (D/'hmi_source_transfer.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,controllerAccess=False,unchangedInputs=len(current),
        hmiTestsPassed=788,hmiTestsSkipped=12,shippingSourcesUnchanged=True,sha256=current),stream,indent=2)
print(json.dumps(dict(passed=True,unchangedInputs=len(current),hmiTestsPassed=788,hmiTestsSkipped=12,controllerAccess=False)))
