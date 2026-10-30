from pathlib import Path
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s4b-gap-20261029/offline_01')
for name in ['run_logged.py','run_rehearsal_01.py','debug_rehearsal_test.dart','verify_plc_bindings_01.py',
 'configuration_comparison.py','test_configuration_stage_01.py','prepare_peer_qualification_01.py']:
 raw=(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),W.as_posix())
 with (W/name).open('x',encoding='utf-8') as f:f.write(raw)
