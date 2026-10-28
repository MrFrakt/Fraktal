from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/offline_01/seal_preparation_01.py').read_text(encoding='utf-8')
def change(before,after):
    global source
    assert source.count(before)==1,(before,source.count(before))
    source=source.replace(before,after)
change("OLD=Path('C:/work/fraktal-ab-s4b-pool-20261027/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/session_01')")
change("P=E/'AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27'","P=E/'AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27'")
change("O=E/'AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27'","O=E/'AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27'")
start=source.index("for label in ('prepare_session_01'");end=source.index("assert b'Ran 2339 tests'",start)
source=source[:start]+"""for label in ('prepare_session_01','timing_part_trace_tests_01','timing_sdk_build_01','timing_authorization_checks_02',
 'timing_workflow_checks_01','timing_readiness_checks_01','timing_readonly_refusals_01','update_status_01',
 'timing_spec_01','timing_contracts_01','timing_consistency_01','timing_root_tests_01','timing_whitespace_01',
 'timing_pub_01','timing_flutter_02','timing_analyze_02','timing_windows_01','timing_focused_02','trace_define_01','refresh_mirror_02'):
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert load(W/'cli_refusal_02_exit.json')['exitCode']==255
assert load(W/'cli_refusal_01_exit.json')['exitCode']==64
assert load(W/'timing_authorization_checks_01_exit.json')['exitCode']==1
assert load(W/'timing_analyze_01_exit.json')['exitCode']==1
assert b'Ran 6 tests' in (W/'timing_part_trace_tests_01.log').read_bytes()
assert b'Ran 74 tests' in (W/'timing_root_tests_01.log').read_bytes()
assert b'660 ~12: All tests passed!' in (W/'timing_flutter_02.log').read_bytes()
assert b'No issues found!' in (W/'timing_analyze_02.log').read_bytes()
"""+source[end:]
for before,after in (
 ("previous['candidateCases']==25 and previous['pairedCapturesReplayed']==53","previous['candidateCases']==41 and previous['pairedCapturesReplayed']==87"),
 ("previous['observerSamples']==1288 and previous['allGoodSamples']==1288","previous['observerSamples']==1991 and previous['allGoodSamples']==1991"),
 ("allowed={R/'Specification/AllenBradley'","allowed_docs={R/'Specification/AllenBradley'"),
 ("files=set();changed=[];plc_count=0","""mirror=load(W/'isolated_hmi_sources_02.json')
allowed_hmi={Path(p) for p in mirror['changed']}
assert len(allowed_hmi)==3
allowed_copies={Path(row['copy']) for row in mirror['files'] if Path(row['source']) in allowed_hmi}
package=Path('C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/.dart_tool/package_config.json')
allowed=allowed_docs|allowed_hmi|allowed_copies|{package}
files=set();changed=[];plc_count=0"""),
 ("assert set(changed)==allowed and plc_count==373","assert set(changed)-{package}==allowed_docs|allowed_hmi|allowed_copies and plc_count==373"),
 ("mirror=load(W/'isolated_hmi_sources_01.json');assert len(mirror['files'])==318","assert len(mirror['files'])==318"),
 ("files.update(allowed)","files.update(allowed_docs|allowed_hmi|allowed_copies)"),
 ("names.update(('AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27','AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27'))",
  "names.update(('AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27','AB_S4B_PART_READ_DIAGNOSTIC_ATTEMPT_2026-10-27'))"),
 ('assert len(names)==96','assert len(names)==98'),
 ('fraktal.ab.s4b-part-read-diagnostic-source-bindings','fraktal.ab.s4b-desktop-timing-source-bindings'),
 ('changedHmiFiles=[],hmiMirrorInputs=318','changedHmiFiles=mirror[\'changed\'],hmiMirrorInputs=318'),
 ('partdiag_preparation_report_01.md','timing_preparation_report_01.md'),
 ('fraktal.ab.s4b-part-read-diagnostic-preparation','fraktal.ab.s4b-desktop-timing-preparation'),
 ('unchangedPlcBoundFiles=373,changedHmiFiles=0','unchangedPlcBoundFiles=373,changedHmiFiles=3'),
 ('unchangedPlcBoundFiles=373,changedHmiFiles=0,','unchangedPlcBoundFiles=373,changedHmiFiles=3,'),
 ('changedShippingFiles=0','changedShippingFiles=3')):
    # The previous count replacement also covers the later summary occurrence.
    count=source.count(before)
    if count==0 and before=='unchangedPlcBoundFiles=373,changedHmiFiles=0,':continue
    assert count>=1,(before,count)
    source=source.replace(before,after)
start=source.index("text=(OLD/'candidate_regressions_v2.py')");end=source.index("package=Path(",start)
source=source[:start]+"""text=(OLD/'candidate_regressions_v2.py').read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
before="command=['C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe',"
assert text.count(before)==1
assert text.replace(before,before+"'-Dfraktal.cip.trace=true',")==(S/'candidate_regressions_v2.py').read_text(encoding='utf-8')
text=(OLD/'desktop_readonly.py').read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix())
assert text.count("'test','--no-pub',")==1
assert text.replace("'test','--no-pub',","'test','--dart-define=fraktal.cip.trace=true','--no-pub',")==(S/'desktop_readonly.py').read_text(encoding='utf-8')
for name in ('qualification_session_v2.py','task_monitor.py','session/Program.cs'):
    assert (S/name).read_text(encoding='utf-8')==(OLD/name).read_text(encoding='utf-8').replace(OLD.as_posix(),S.as_posix()),name
"""+source[end:]
start=source.index("for label in ('pool_pub_01'");end=source.index("for label in ('ab_suite_01'",start)
source=source[:start]+"""B=Path('C:/work/fraktal-ab-s4b-paths-20261027/offline_01')
assert load(B/'paths_before_01_exit.json')['exitCode']==0
for path in sorted(B.iterdir()):
    if path.is_file() and path.suffix in ('.py','.dart','.json','.log'):archive(path,'PathMeasurement/'+path.name)
"""+source[end:]
compile(source,str(W/'seal_preparation_01.py'),'exec')
with (W/'seal_preparation_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
print('Materialized strict timing sealer; no controller access.')
