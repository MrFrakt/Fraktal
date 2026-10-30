from pathlib import Path
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-wp4b5-20261028/offline_01')
source=(OLD/'run_rehearsal_01.py').read_text(encoding='utf-8')
needle="'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart','pubspec.yaml','pubspec.lock'"
assert source.count(needle)==1
source=source.replace(needle,"'packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',\n    'packages/fraktal_opcua_client/lib/src/cip_read_pool.dart',\n    'test/cip_coalesced_read_test.dart','test/cip_session_client_test.dart',\n    'test/opcua_freshness_test.dart','pubspec.yaml','pubspec.lock'")
for name,value in [('run_rehearsal_01.py',source),('debug_rehearsal_test.dart',(OLD/'debug_rehearsal_test.dart').read_text())]:
    with (W/name).open('x',encoding='utf-8',newline='') as f:f.write(value)
print('Prepared labelled runner with all changed reader inputs; Echo read-only checks retained.')
