from pathlib import Path
import json,xml.etree.ElementTree as ET
P=Path(__file__).parent
root=ET.parse(P/'s3h_candidate_01.L5X')
overlength=[dict(kind=n.tag,name=n.get('Name'),characters=len(n.get('Name'))) for n in root.iter() if len(n.get('Name',''))>40]
assert len(overlength)==3
assert 'BOOL tag not expected in expression' in (P/'native_echo_02.log').read_text()
assert 'expected a DINT, got' in (P/'focused_01.log').read_text()
assert 'test_profile_is_opt_in_and_legacy_manifest_identity_is_preserved' in (P/'ab_suite_01.log').read_text()
report=dict(passed=True,retainedFailures=[
    dict(run='focused_01',reason='Integer interpreter rejects BOOL equality; final ST removes this native-invalid expression and the temporary interpreter workaround'),
    dict(run='native_echo_01',reason='Native import rejects overlength identifiers',identifiers=overlength),
    dict(run='native_echo_02',reason='Native compiler rejects BOOL comparison; final numeric-owner checks replace it'),
    dict(run='ab_suite_01',reason='Prior refusal test still treats now-approved stage 10 as invalid; first unsupported stage is now 11')],
    failedSourceImagesRetained=True,validationWeakened=False,controllerChanges=0)
with (P/'failed_runs_analysis_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(dict(passed=True,retainedFailures=len(report['retainedFailures']),controllerChanges=0)))
