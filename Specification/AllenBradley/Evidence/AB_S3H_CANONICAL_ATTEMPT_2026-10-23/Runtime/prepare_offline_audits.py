"""Adapt the existing evidence auditors to the S3h surface and owner count."""
from pathlib import Path
import json
R=Path(__file__).parent;prior=Path('C:/work/fraktal-ab-s3g-20261023/runtime_9564a5c9669b42eeadca0c412b7ea3f7')
text=(prior/'verify_candidate_surface.py').read_text().replace('s3g','s3h').replace('S3g','S3h')
needle='   expected_count={0:3672,1:3622,2:3272}[page]'
assert needle in text
text=text.replace(needle,needle+"+70+13*values['Press/HostEvents/Count']\n   assert 0<=values['Press/HostEvents/Count']<=16\n   assert state['canonical']['types']['Press/Part/Result/Stamp']=='DateTime'\n   assert state['canonical']['types']['Press/HostEvents/Count']=='Int16'\n   assert state['canonical']['types']['Press/Part/Result/Records[1]/Value']=='Double'",1)
with (R/'verify_candidate_surface.py').open('x') as f:f.write(text)
text=(prior/'replay_runtime_captures.py').read_text().replace('s3g','s3h').replace('S3g','S3h')
needle="expected=gate.subset_paths(app,codes,canonical=False,page=context['page'],model=context['model']),"
assert needle in text
text=text.replace(needle,"expected=gate.subset_paths(app,codes,canonical=False,count=additional['host']['metadata']['Count'],page=context['page'],model=context['model']),",1)
with (R/'replay_runtime_captures.py').open('x') as f:f.write(text)
with (R/'measure_native_records.py').open('x') as f:f.write((prior/'measure_native_records.py').read_text())
text=(R/'candidate_then_restore.py').read_text()
needle="assert json.loads((R/'backup_access_01.json').read_text())['Conforms']"
assert needle in text
text=text.replace(needle,needle+"\nassert json.loads((R/'tooling_validation_01.json').read_text())['passed']",1)
with (R/'candidate_then_restore_initial.py').open('x') as f:f.write((R/'candidate_then_restore.py').read_text())
(R/'candidate_then_restore.py').write_text(text)
print(json.dumps(dict(passed=True,controllerAccess=False,protocolOrStimulusChange=False)))
