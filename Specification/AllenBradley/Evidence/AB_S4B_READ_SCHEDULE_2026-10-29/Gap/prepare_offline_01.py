from pathlib import Path
W=Path(__file__).parent;H=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI')
F=Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')
for name in ['packages/fraktal_opcua_client/lib/src/cip_read_plan.dart',
 'packages/fraktal_opcua_client/lib/src/cip_session_client.dart','test/cip_coalesced_read_test.dart']:
 (H/name).write_bytes((F/'profile_04/Sources'/name).read_bytes())
for name in ['run_logged.py','run_rehearsal_01.py','debug_rehearsal_test.dart','verify_plc_bindings_01.py',
 'configuration_comparison.py','test_configuration_stage_01.py','prepare_peer_qualification_01.py']:
 raw=(F/name).read_text(encoding='utf-8').replace(F.as_posix(),W.as_posix())
 with (W/name).open('x',encoding='utf-8') as f:f.write(raw)
