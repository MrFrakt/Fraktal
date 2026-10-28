from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-timing-20261027/offline_01/seal_preparation_01.py').read_text(encoding='utf-8')
def change(before,after):
    global source
    assert source.count(before)==1,(before,source.count(before))
    source=source.replace(before,after)
change("OLD=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-timing-20261027/session_01')")
change("P=E/'AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27'","P=E/'AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27'")
change("O=E/'AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27'","O=E/'AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27'")
start=source.index("for label in ('prepare_session_01'");end=source.index("assert b'Ran 2339 tests'",start)
source=source[:start]+"""for label in ('prepare_session_01','array_part_trace_tests_01','array_sdk_build_01','array_authorization_checks_01',
 'array_workflow_checks_01','array_readiness_checks_01','array_readonly_refusals_01','update_status_01',
 'array_spec_01','array_contracts_01','array_consistency_01','array_root_tests_01','array_whitespace_01',
 'array_pub_01','array_flutter_01','array_analyze_01','array_windows_01','array_focused_01','refresh_mirror_01',
 'materialize_test_01','array_tiers_after_03','wire_before_01','wire_after_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert load(W/'cli_refusal_01_exit.json')['exitCode']==255
assert load(W/'array_tiers_before_04_exit.json')['exitCode']==1
assert b'+1 -4: Some tests failed!' in (W/'array_tiers_before_04.log').read_bytes()
assert b'Ran 6 tests' in (W/'array_part_trace_tests_01.log').read_bytes()
assert b'Ran 74 tests' in (W/'array_root_tests_01.log').read_bytes()
assert b'665 ~12: All tests passed!' in (W/'array_flutter_01.log').read_bytes()
assert b'No issues found!' in (W/'array_analyze_01.log').read_bytes()
before_replay=load(W/'wire_before_01.json');after_replay=load(W/'wire_after_01.json')
assert before_replay['values']==after_replay['values'] and before_replay['types']==after_replay['types']
assert (before_replay['wireReads'],after_replay['wireReads'])==(990,810)
assert (before_replay['groups'],after_replay['groups'])==(297,237)
assert (before_replay['hiddenByClassReads'],after_replay['hiddenByClassReads'])==(60,0)
assert before_replay['consumedValues']==after_replay['consumedValues']==976
"""+source[end:]
for before,after in (
 ("previous['observerSamples']==1991 and previous['allGoodSamples']==1991","previous['observerSamples']==2035 and previous['allGoodSamples']==2033 and previous['samplesWithUncertainRows']==2"),
 ("W/'isolated_hmi_sources_02.json'","W/'isolated_hmi_sources_01.json'"),
 ("assert len(mirror['files'])==318","assert len(mirror['files'])==319 and len(mirror['added'])==1"),
 ("names.update(('AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27','AB_S4B_PART_READ_DIAGNOSTIC_ATTEMPT_2026-10-27'))",
  "names.update(('AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27','AB_S4B_DESKTOP_TIMING_ATTEMPT_2026-10-27'))"),
 ('assert len(names)==98','assert len(names)==100'),
 ('fraktal.ab.s4b-desktop-timing-source-bindings','fraktal.ab.s4b-tier-queue-source-bindings'),
 ("changedHmiFiles=mirror['changed'],hmiMirrorInputs=318","changedHmiFiles=mirror['changed'],addedHmiFiles=mirror['added'],hmiMirrorInputs=319"),
 ('timing_preparation_report_01.md','array_preparation_report_01.md'),
 ('fraktal.ab.s4b-desktop-timing-preparation','fraktal.ab.s4b-tier-queue-preparation'),
 ('flutterTests=660','flutterTests=665'),
 ('unchangedPlcBoundFiles=373,changedHmiFiles=3,sessionOnlyPartTracing=True','unchangedPlcBoundFiles=373,changedHmiFiles=3,addedHmiFiles=1,arrayTierTests=5,sessionOnlyPartTracing=True')):
    change(before,after)
start=source.index("text=(OLD/'candidate_regressions_v2.py')");end=source.index("package=Path(",start)
source=source[:start]+"""for name in ('candidate_regressions_v2.py','desktop_readonly.py','qualification_session_v2.py',
 'task_monitor.py','session/Program.cs','desktop_diagnostic_qualification_test.dart'):
    assert (S/name).read_text(encoding='utf-8')==(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix()),name
"""+source[end:]
start=source.index("B=Path('C:/work/fraktal-ab-s4b-paths-");end=source.index("for label in ('ab_suite_01'",start)
source=source[:start]+source[end:]
compile(source,str(W/'seal_preparation_01.py'),'exec')
with (W/'seal_preparation_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Materialized append-only tier/queue retry sealer; no controller access.')
