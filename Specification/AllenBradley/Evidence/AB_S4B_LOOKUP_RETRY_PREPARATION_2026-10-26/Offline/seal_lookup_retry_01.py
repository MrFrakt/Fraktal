"""Apply the sealed preparation workflow to the measured lookup correction."""
from pathlib import Path

W = Path(__file__).parent
original = W / 'seal_root_diagnostic_01.py'
archived = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26/Offline/seal_root_diagnostic_01.py')
assert original.read_bytes() == archived.read_bytes()
source = original.read_text(encoding='utf-8')

def replace(before, after):
    global source
    assert source.count(before) == 1, before
    source = source.replace(before, after)

replace("\nD = W.parent / 'retry_root_diagnostic_01'", "\nD = W.parent / 'retry_lookup_01'")
replace("\nOLD = W.parent / 'retry_template_01'", "\nOLD = W.parent / 'retry_root_diagnostic_01'")
replace("OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'", "OUT = E / 'AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26'")
start = source.index("labels = (")
end = source.index("\nfor label in labels:", start)
source = source[:start] + """labels = ('seal_root_diagnostic_attempt_01', 'prepare_lookup_retry_02', 'lookup_sdk_build_02',
          'lookup_authorization_checks_01', 'refresh_lookup_hmi_01', 'lookup_lockfile_01',
          'lookup_windows_01', 'lookup_flutter_01', 'lookup_analyze_01', 'lookup_status_01',
          'lookup_spec_01', 'lookup_contracts_01', 'lookup_consistency_01', 'lookup_tests_01',
          'lookup_whitespace_01', 'schedule_profile_before_01', 'schedule_profile_after_01')""" + source[end:]
replace("'637 ~12: All tests passed!' in (L / 'diagnostic_flutter_01.log')", "'638 ~12: All tests passed!' in (L / 'lookup_flutter_01.log')")
replace("(L / 'diagnostic_analyze_01.log')", "(L / 'lookup_analyze_01.log')")
replace("result = load(OLD / 'session_result.json')", "result = load(OLD / 'runtime_summary_01.json')")
replace("assert result['genealogyRestored'] and result['authorizationConsumed'] and result['rollbackError'] is None",
        "assert result['continuationGenealogyRestored'] and result['authorizationConsumed'] and result['baselineRetryCasesPassed'] == 31")
replace("assert load(OLD / 'final_checks.json')['passed']", "assert load(OLD / 'final_checks_retry_01.json')['passed']")
replace("""    if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
        assert sha(path).upper() == expected.upper(), name
        unchanged_hmi_production += 1""", """    if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
        if path.name == 'cip_read_plan.dart':
            assert sha(path).upper() != expected.upper(), 'lookup correction missing'
        else:
            assert sha(path).upper() == expected.upper(), name
            unchanged_hmi_production += 1""")
replace("mirror = load(W / 'isolated_hmi_sources_03.json')", "mirror = load(W / 'isolated_hmi_sources_04.json')")
replace("schema='fraktal.ab.s4b-root-diagnostic-source-bindings'", "schema='fraktal.ab.s4b-lookup-retry-source-bindings'")
replace("previous_prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'",
        "previous_prep = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26/manifest.json'")
replace("names.update(('AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26', 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'))",
        "names.update(('AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26', 'AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26'))")
start = source.index("report = f'''")
end = source.index("\nwith REPORT.open", start)
source = source[:start] + (W / 'lookup_preparation_report.txt').read_text(encoding='utf-8') + source[end:]
start = source.index("for path in (W / 'prepare_root_diagnostic_01.py'")
end = source.index("\nfor name in ('missing_approval_cli_root_diagnostic_01.log'", start)
source = source[:start] + """for path in (W / 'prepare_lookup_retry_01.py', W / 'prepare_lookup_retry_02.py', W / 'prepare_root_diagnostic_01.py',
             W / 'lookup_authorization_checks.py', W / 'refresh_lookup_hmi_01.py', W / 'isolated_hmi_sources_04.json',
             W / 'lookup_authorization_checks_01.json', W / 'seal_lookup_retry_01.py', W / 'lookup_preparation_report.txt',
             W / 'update_lookup_status_01.py', W / 'cip_schedule_profile_probe.dart',
             W / 'schedule_profile_before_01.json', W / 'schedule_profile_after_01.json'):
    archive(path, 'Offline/' + path.name)
for label in ('prepare_lookup_retry_01', 'lookup_sdk_build_01'):
    assert load(L / (label + '_exit.json'))['exitCode'] != 0
    for suffix in ('.log', '_exit.json'):
        archive(L / (label + suffix), 'Offline/' + label + suffix)
""" + source[end:]
replace("('missing_approval_cli_root_diagnostic_01.log', 'missing_approval_sdk_root_diagnostic_01.log')",
        "('missing_approval_cli_lookup_01.log', 'missing_approval_sdk_lookup_01.log')")
replace("schema='fraktal.ab.s4b-root-diagnostic-preparation'", "schema='fraktal.ab.s4b-lookup-retry-preparation'")
replace("rootTests=74, flutterTests=637, flutterSkipped=12", "rootTests=74, flutterTests=638, flutterSkipped=12")
replace("W / 'sealed_root_diagnostic_01.json'", "W / 'sealed_lookup_retry_01.json'")
exec(compile(source, str(original), 'exec'), {'__file__': __file__})
