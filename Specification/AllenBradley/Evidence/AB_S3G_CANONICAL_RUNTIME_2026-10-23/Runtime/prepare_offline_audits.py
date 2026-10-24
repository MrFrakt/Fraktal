"""Adapt the accepted audit apparatus to the explicit added S3g path set."""
from pathlib import Path
R=Path(__file__).parent
W=Path('C:/work/fraktal-ab-s3f-revision-20261023/prepare_c66f76a368304f6981b436dbf651e009')
O=Path('C:/work/fraktal-ab-s3f-revision-20261023/runtime_9b86612c2f174292a2773260021df32d')
text=(W/'verify_base_acceptance.py').read_text()
for name in ('DecisionPairs','ConditionPairs','SequencePairs','ResetPairs','AccessPairs','AccessRows','ConfigPairs','ConfigRows'):
    needle='s3f'+name;assert needle in text;text=text.replace(needle,'s3g'+name)
for before,after in (('2617','3672'),('2567','3622'),('2217','3272')):
    assert text.count(before)==1;text=text.replace(before,after)
with (R/'verify_candidate_surface.py').open('x') as f:f.write(text)
text=(O/'replay_runtime_captures.py').read_text()
text=text.replace('import fraktal_ab_genealogy_s3f_demo as demo','import fraktal_ab_genealogy_s3g_demo as demo')
text=text.replace('import fraktal_ab_s3f_equivalence as gate','import fraktal_ab_s3g_equivalence as gate')
text=text.replace("fixture['s3fConfigPairs']","fixture['s3gConfigPairs']")
text=text.replace('independently replay S3f reference contexts','independently replay S3g reference contexts')
with (R/'replay_runtime_captures.py').open('x') as f:f.write(text)
print('Prepared read-only candidate coverage and independent native-byte replay audits.')
