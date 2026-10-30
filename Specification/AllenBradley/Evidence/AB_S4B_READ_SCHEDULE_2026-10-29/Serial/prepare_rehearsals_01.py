from pathlib import Path
W=Path(__file__).parent;OLD=Path('C:/work/fraktal-ab-s4b-observer-20261029/offline_01')
raw=(OLD/'run_rehearsal_01.py').read_text(encoding='utf-8')
needle="'tool/qualify_cip_canonical.dart','test/cip_qualification_test.dart',"
assert raw.count(needle)==1
raw=raw.replace(needle,needle+"\n    'tool/qualify_cip_configuration.dart','test/cip_configuration_qualification_test.dart',")
with (W/'run_rehearsal_01.py').open('x') as f:f.write(raw)
raw=(OLD/'verify_rehearsals_01.py').read_text(encoding='utf-8')
raw=raw.replace("labels=['profile_03','profile_04','profile_05']","labels=['profile_01','profile_02','profile_03']")
with (W/'verify_rehearsals_01.py').open('x') as f:f.write(raw)
source=Path('C:/work/fraktal-ab-s4b-o8-20261028/offline_01/debug_rehearsal_test.dart')
with (W/'debug_rehearsal_test.dart').open('xb') as f:f.write(source.read_bytes())
print('Fresh 31-input rehearsal runner; current one-connection source; no controller changes')
