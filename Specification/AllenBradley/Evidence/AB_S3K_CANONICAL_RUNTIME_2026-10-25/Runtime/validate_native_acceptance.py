"""Assert the bounded S3k genealogy acceptance from sealed-session outputs."""
from pathlib import Path
import gzip
import hashlib
import json
import sys

R = Path(__file__).parent
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
sys.path.insert(0, str(ROOT / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_command_binding as binding
import fraktal_ab_s3k_fixture_execute as fixture
import fraktal_ab_mailbox as mailbox

load = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
session = load(R / 'session_result.json')
summary = load(R / 'runtime_summary_01.json')
cases = load(R / 'request_cases.json')
baseline = load(R / 'baseline_regressions.json')
assert session['passed'] and summary['passed'] and session['genealogyRestored']
expected = {'rows': 31, 's3kAccessRows': 2, 's3kConfigRows': 8, 's3kTypedRows': 14}
for key, count in expected.items():
    assert len(cases[key]) == count and all(row['passed'] for row in cases[key]), key
assert cases['restored'] and cases['policyRestored'] and cases['s3fSetMediumEmpty']
typed = {row['case']: row for row in cases['s3kTypedRows']}
assert summary['typedLoginCompleted'] and typed['collision_observed']['outcome'] == 'collision_refused'
assert sum(row.get('wiped') is True for row in typed.values()) == 12
assert len(baseline['rows']) == 31 and all(row['passed'] for row in baseline['rows']) and not baseline.get('error')
assert load(R / 'pair_replay_01.json')['captures'] == 91
assert load(R / 'restore_original_medium.json')['passed'] if (R/'restore_original_medium.json').exists() else load(R/'medium_restored_01.json')['passed']
assert all(load(R / 'final_checks.json')['checks'].values())
timing = summary['timing']
for key in ('candidate_timing', 'baseline_timing'):
    fields = timing[key]['fields']
    assert fields['FRK_Press_HealthProbe.TaskMaxScanUs']['maximum'] < 10000
    assert fields['FRK_Press_HealthProbe.TaskOverlapCount']['maximum'] == 0

capture = load(R / 'generic_capture.json.gz')
descriptor = capture['manifest']['commandBindings'][0]
plan = binding.write_plan(capture, descriptor, fixture.arguments(Kind=mailbox.QUERY_CONFIG), 100,
                          connection_bytes=descriptor['ConnectionBytes'])
symbol = next(s for s in capture['symbols'] if s['name'] == descriptor['PayloadSymbol'])
template = next(t for t in capture['templates'] if t['handle'] == symbol['handle'])
assert descriptor['ConnectionBytes'] == 4000 and plan.payload_bytes == 784
assert hashlib.sha256(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD').read_bytes()).hexdigest().upper() == 'D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
result = dict(passed=True, scope='Echo 601FC87B genealogy S3k image AA4239C6...1653BBDF and fixed authorized cases',
              candidateCheckRows=55, inheritedCheckRows=41, typedInterleavingCheckRows=14, baselineChecks=31,
              pairedCaptures=91, typedLoginCompleted=True, collisionOutcome='collision_refused',
              typedPayloadBytes=plan.payload_bytes, templateStructureHandle=template['structureHandle'],
              typedConnectionBytes=descriptor['ConnectionBytes'], cumulativeCandidateMaxScanUs=8969,
              candidateOverlapCount=0, genealogyRestored=True, originalDocumentsRestored=True,
              finalChecksPassed=True, currentControllerChangesAuthorized=False,
              excludedAcceptance=['press ST/SFC/LD declaration proof', 'physical I/O module proof', 'S4-S7'])
with (R / 'native_acceptance_01.json').open('x') as out:
    json.dump(result, out, indent=2)
print(json.dumps(result))
