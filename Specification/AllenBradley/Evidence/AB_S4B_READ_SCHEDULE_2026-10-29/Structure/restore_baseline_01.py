from pathlib import Path
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
F=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01/profile_04/Sources')
for name in ['packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
 'packages/fraktal_opcua_client/lib/src/cip_session_client.dart','test/cip_read_plan_test.dart']:
 (H/name).write_bytes((F/name).read_bytes())
source=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')
for name in ['run_logged.py','run_rehearsal_01.py','debug_rehearsal_test.dart','verify_plc_bindings_01.py',
 'configuration_comparison.py','test_configuration_stage_01.py','prepare_peer_qualification_01.py']:
 raw=(source/name).read_text(encoding='utf-8').replace(source.as_posix(),W.as_posix())
 with (W/name).open('x',encoding='utf-8') as f:f.write(raw)
print('Restored the qualified pre-cadence source; failed cadence sources remain captured.')
