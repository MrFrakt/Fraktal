from pathlib import Path

W=Path(__file__).parent
original=W/'seal_root_diagnostic_01.py'
source=original.read_text(encoding='utf-8')
assert original.read_bytes()==Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26/Offline/seal_root_diagnostic_01.py').read_bytes()
def replace(before,after):
    global source
    assert source.count(before)==1,before
    source=source.replace(before,after)
replace("L = W.parent / 'session_01'","L = W.parent / 'desktop_scan_01'\nG = W.parent / 'session_01'")
replace("\nD = W.parent / 'retry_root_diagnostic_01'","\nD = W.parent / 'desktop_scan_continue_01'")
replace("\nOLD = W.parent / 'retry_template_01'","\nOLD = W.parent / 'desktop_scan_01'")
replace("OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'","OUT = E / 'AB_S4B_DESKTOP_SCAN_CONTINUATION_2026-10-26'")
start=source.index('labels = (');end=source.index('\nfor label in labels:',start)
source=source[:start]+"""labels = ('guard_unchanged_01','preflight_unchanged_01','prepare_continuation_01',
    'ready_after_01','ready_protocol_tests_01','continuation_sdk_build_01',
    'seal_preflight_attempt_01','continuation_auth_checks_02')"""+source[end:]
replace("'637 ~12: All tests passed!' in (L / 'diagnostic_flutter_01.log')","'647 ~12: All tests passed!' in (G / 'reader_flutter_01.log')")
replace("(L / 'diagnostic_analyze_01.log')","(G / 'reader_analyze_01.log')")
replace("assert result['genealogyRestored'] and result['authorizationConsumed'] and result['rollbackError'] is None\nassert load(OLD / 'final_checks.json')['passed']","""assert not result['passed'] and result['authorizationConsumed'] and result['rollbackError'] is None
assert result['candidateError'].startswith('JSONDecodeError:')
assert not (OLD/'deploy_attempt.json').exists()
assert load(OLD/'manual_initial.json')['controllerWrites']==0
assert load(OLD/'guard_unchanged_01_exit.json')['exitCode']==0
assert load(OLD/'preflight_unchanged_01_exit.json')['exitCode']==0""")
replace("    path = Path(name)\n    if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:","    path = Path(name)\n    if not path.is_relative_to(OLD):\n        assert sha(path).upper()==expected.upper(), name\n    if 'FraktalCore/PLC/Allen-Bradley/tools/' in name:")
replace("mirror = load(W / 'isolated_hmi_sources_03.json')","mirror = load(W / 'isolated_hmi_sources_07.json')\nfiles.add(D/'desktop_readonly_qualification_test.dart')")
replace("schema='fraktal.ab.s4b-root-diagnostic-source-bindings'","schema='fraktal.ab.s4b-desktop-scan-continuation-source-bindings'")
replace("previous_prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'","previous_prep = E / 'AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26/manifest.json'")
replace("names.update(('AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26', 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'))","names.update(('AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26','AB_S4B_DESKTOP_SCAN_PREFLIGHT_ATTEMPT_2026-10-26'))")
start=source.index("report = f'''");end=source.index('\nwith REPORT.open',start)
source=source[:start]+(W/'desktop_continuation_report.txt').read_text(encoding='utf-8')+source[end:]
start=source.index("for path in (W / 'prepare_root_diagnostic_01.py'");end=source.index("\nfor name in ('missing_approval_cli_root_diagnostic_01.log'",start)
source=source[:start]+"""for name in ('prepare_root_diagnostic_01.py','prepare_desktop_continuation_01.py',
    'session_ready_template.py','test_ready_workflow_01.py','test_desktop_scan_workflow_01.py',
    'test_session_ready_01.py','desktop_continue_authorization_checks.py',
    'desktop_continue_authorization_checks_01.json','seal_desktop_continuation_01.py','desktop_continuation_report.txt'):
    archive(W/name,'Offline/'+name)
for label in ('ready_before_01','continuation_auth_checks_01'):
    assert load(L/(label+'_exit.json'))['exitCode']==1
    for suffix in ('.log','_exit.json'):
        archive(L/(label+suffix),'Offline/'+label+suffix)
"""+source[end:]
replace("('missing_approval_cli_root_diagnostic_01.log', 'missing_approval_sdk_root_diagnostic_01.log')","('missing_approval_cli_desktop_continue_01.log','missing_approval_sdk_desktop_continue_01.log')")
replace("schema='fraktal.ab.s4b-root-diagnostic-preparation'","schema='fraktal.ab.s4b-desktop-scan-continuation-preparation'")
replace('rootTests=74, flutterTests=637, flutterSkipped=12','rootTests=74, flutterTests=647, flutterSkipped=12')
replace("W / 'sealed_root_diagnostic_01.json'","W / 'sealed_desktop_continuation_01.json'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
