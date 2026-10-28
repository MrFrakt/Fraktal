from pathlib import Path

W=Path(__file__).parent
original=W/'seal_root_diagnostic_01.py'
archived=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26/Offline/seal_root_diagnostic_01.py')
assert original.read_bytes()==archived.read_bytes()
source=original.read_text(encoding='utf-8')
def replace(before,after):
    global source
    assert source.count(before)==1,before
    source=source.replace(before,after)
replace("L = W.parent / 'session_01'","L = W.parent / 'retry_reader_01'\nG = W.parent / 'session_01'")
replace("\nD = W.parent / 'retry_root_diagnostic_01'","\nD = W.parent / 'desktop_scan_01'")
replace("\nOLD = W.parent / 'retry_template_01'","\nOLD = W.parent / 'retry_reader_01'")
replace("OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'","OUT = E / 'AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26'")
start=source.index('labels = (')
end=source.index('\nfor label in labels:',start)
source=source[:start]+"""labels = ('seal_reader_runtime_01','runtime_status_01','postrun_spec_01','postrun_contracts_01',
          'postrun_consistency_01','postrun_tests_01','prepare_desktop_scan_01','desktop_scan_sdk_build_01',
          'desktop_scan_flow_tests_01','desktop_scan_flow_tests_02','desktop_scan_authorization_checks_01',
          'desktop_scan_readonly_checks_01','desktop_fixture_04','desktop_fixture_05','desktop_fixture_06',
          'desktop_scan_analyze_02','desktop_scan_status_01','desktop_scan_spec_01',
          'desktop_scan_contracts_01','desktop_scan_consistency_01','desktop_scan_whitespace_01')"""+source[end:]
replace("'637 ~12: All tests passed!' in (L / 'diagnostic_flutter_01.log')","'647 ~12: All tests passed!' in (G / 'reader_flutter_01.log')")
replace("(L / 'diagnostic_analyze_01.log')","(G / 'reader_analyze_01.log')")
replace("mirror = load(W / 'isolated_hmi_sources_03.json')","""mirror = load(W / 'isolated_hmi_sources_07.json')
for row in mirror['files']:
    files.add(Path(row['copy']))
files.add(W.parent/'hmi_verify_01/.dart_tool/package_config.json')
files.add(W.parent/'hmi_verify_01/tool/desktop_scan_qualification_test.dart')
files.add(D/'desktop_readonly_qualification_test.dart')
assert (D/'desktop_readonly_qualification_test.dart').read_bytes()==(W/'desktop_readonly_qualification_test.dart').read_bytes()==(W.parent/'hmi_verify_01/tool/desktop_scan_qualification_test.dart').read_bytes()
ui=load(W.parent/'desktop_fixture_06/result.json')
assert ui['passed'] and not ui['live'] and not ui['desktopLiveAccepted'] and ui['fixtureClientWriteCalls']==0
assert len(ui['modules'])==7 and len(ui['fieldbusNodes'])==3 and len(ui['shots'])==31
assert 'Warning: A call to tap()' not in (L/'desktop_fixture_06.log').read_text(encoding='utf-8')
assert 'No issues found!' in (L/'desktop_scan_analyze_02.log').read_text(encoding='utf-8')
assert 'Ran 7 tests' in (L/'desktop_scan_flow_tests_02.log').read_text(encoding='utf-8')""")
replace("schema='fraktal.ab.s4b-root-diagnostic-source-bindings'","schema='fraktal.ab.s4b-desktop-scan-source-bindings'")
replace("previous_prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'","previous_prep = E / 'AB_S4B_READER_RETRY_PREPARATION_2026-10-26/manifest.json'")
replace("names.update(('AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26', 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'))","names.update(('AB_S4B_READER_RETRY_PREPARATION_2026-10-26', 'AB_S4B_READER_RUNTIME_2026-10-26'))")
start=source.index("report = f'''")
end=source.index('\nwith REPORT.open',start)
source=source[:start]+(W/'desktop_scan_preparation_report.txt').read_text(encoding='utf-8')+source[end:]
start=source.index("for path in (W / 'prepare_root_diagnostic_01.py'")
end=source.index("\nfor name in ('missing_approval_cli_root_diagnostic_01.log'",start)
source=source[:start]+"""for path in (W/'prepare_desktop_scan_01.py',W/'prepare_root_diagnostic_01.py',
             W/'task_monitor_template.py',W/'desktop_launcher_template.py',W/'desktop_readonly_qualification_test.dart',
             W/'run_desktop_fixture_01.py',W/'test_desktop_scan_workflow_01.py',W/'desktop_scan_authorization_checks.py',
             W/'desktop_scan_authorization_checks_01.json',W/'desktop_scan_readonly_checks_01.py',
             W/'desktop_scan_readonly_checks_01.json',W/'isolated_hmi_sources_07.json',
             W/'update_reader_runtime_status_01.py',W/'update_desktop_scan_status_01.py',
             W/'seal_desktop_scan_01.py',W/'desktop_scan_preparation_report.txt',
             W/'desktop_fixture_failed_source_01.dart',W/'desktop_fixture_unproved_navigation_02.dart',
             W/'desktop_fixture_stale_finder_03.dart',W/'desktop_analyzer_source_01.dart'):
    archive(path,'Offline/'+path.name)
for label in ('desktop_fixture_01','desktop_fixture_02','desktop_fixture_03','desktop_scan_analyze_01'):
    assert load(L/(label+'_exit.json'))['exitCode']==1
    for suffix in ('.log','_exit.json'):
        archive(L/(label+suffix),'Offline/'+label+suffix)
for folder in ('desktop_fixture_02','desktop_fixture_03','desktop_fixture_04','desktop_fixture_05','desktop_fixture_06'):
    for path in sorted((W.parent/folder).glob('*')):
        if path.is_file():
            archive(path,'Rendering/'+folder+'/'+path.name)
for name in ('missing_approval_task_monitor_01.log','missing_approval_desktop_readonly_01.log'):
    archive(W/name,'Offline/'+name)
for label in ('reader_flutter_01','reader_windows_01','reader_analyze_01','reader_lockfile_01'):
    assert load(G/(label+'_exit.json'))['exitCode']==0
    for suffix in ('.log','_exit.json'):
        archive(G/(label+suffix),'Offline/retained_'+label+suffix)
"""+source[end:]
replace("('missing_approval_cli_root_diagnostic_01.log', 'missing_approval_sdk_root_diagnostic_01.log')","('missing_approval_cli_desktop_scan_01.log', 'missing_approval_sdk_desktop_scan_01.log')")
replace("schema='fraktal.ab.s4b-root-diagnostic-preparation'","schema='fraktal.ab.s4b-desktop-scan-preparation'")
replace('rootTests=74, flutterTests=637, flutterSkipped=12','rootTests=74, flutterTests=647, flutterSkipped=12')
replace("W / 'sealed_root_diagnostic_01.json'","W / 'sealed_desktop_scan_01.json'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
