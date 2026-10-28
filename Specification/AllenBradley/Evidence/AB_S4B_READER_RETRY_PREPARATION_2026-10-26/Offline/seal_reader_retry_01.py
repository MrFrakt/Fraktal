"""Seal the measured retry-effort and conservative-age corrections."""
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

replace("\nD = W.parent / 'retry_root_diagnostic_01'", "\nD = W.parent / 'retry_reader_01'")
replace("\nOLD = W.parent / 'retry_template_01'", "\nOLD = W.parent / 'retry_freshness_01'")
replace("OUT = E / 'AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26'", "OUT = E / 'AB_S4B_READER_RETRY_PREPARATION_2026-10-26'")
start = source.index('labels = (')
end = source.index('\nfor label in labels:', start)
source = source[:start] + """labels = ('seal_freshness_attempt_01', 'prepare_reader_retry_01', 'reader_sdk_build_01',
          'reader_authorization_checks_01', 'refresh_reader_hmi_01', 'reader_lockfile_01',
          'reader_windows_01', 'reader_flutter_01', 'reader_analyze_01', 'reader_status_01',
          'reader_spec_01', 'reader_contracts_01', 'reader_consistency_01', 'reader_tests_01',
          'reader_whitespace_02', 'reader_after_01')""" + source[end:]
replace("'637 ~12: All tests passed!' in (L / 'diagnostic_flutter_01.log')", "'647 ~12: All tests passed!' in (L / 'reader_flutter_01.log')")
replace("(L / 'diagnostic_analyze_01.log')", "(L / 'reader_analyze_01.log')")
replace("""    if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
        assert sha(path).upper() == expected.upper(), name
        unchanged_hmi_production += 1""", """    if '/FraktalCore/HMI/lib/' in name or '/FraktalCore/HMI/packages/' in name:
        if path.name in ('cip_read_plan.dart', 'cip_session_client.dart'):
            assert sha(path).upper() != expected.upper(), 'correction missing: ' + name
        else:
            assert sha(path).upper() == expected.upper(), name
            unchanged_hmi_production += 1""")
replace("mirror = load(W / 'isolated_hmi_sources_03.json')", "mirror = load(W / 'isolated_hmi_sources_07.json')")
replace("schema='fraktal.ab.s4b-root-diagnostic-source-bindings'", "schema='fraktal.ab.s4b-reader-retry-source-bindings'")
replace("previous_prep = E / 'AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26/manifest.json'",
        "previous_prep = E / 'AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26/manifest.json'")
replace("names.update(('AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26', 'AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26'))",
        "names.update(('AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26', 'AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26'))")
start = source.index("report = f'''")
end = source.index('\nwith REPORT.open', start)
source = source[:start] + (W / 'reader_preparation_report.txt').read_text(encoding='utf-8') + source[end:]
start = source.index("for path in (W / 'prepare_root_diagnostic_01.py'")
end = source.index("\nfor name in ('missing_approval_cli_root_diagnostic_01.log'", start)
source = source[:start] + """for path in (W / 'prepare_reader_retry_01.py', W / 'prepare_root_diagnostic_01.py',
             W / 'reader_authorization_checks.py', W / 'refresh_reader_hmi_01.py', W / 'isolated_hmi_sources_07.json',
             W / 'reader_authorization_checks_01.json', W / 'seal_reader_retry_01.py', W / 'reader_preparation_report.txt',
             W / 'update_reader_status_01.py'):
    archive(path, 'Offline/' + path.name)
assert load(L / 'reader_before_01_exit.json')['exitCode'] == 1
for suffix in ('.log', '_exit.json'):
    archive(L / ('reader_before_01' + suffix), 'Offline/reader_before_01' + suffix)
    archive(L / ('reader_whitespace_01' + suffix), 'Offline/reader_whitespace_01' + suffix)
""" + source[end:]
replace("('missing_approval_cli_root_diagnostic_01.log', 'missing_approval_sdk_root_diagnostic_01.log')",
        "('missing_approval_cli_reader_01.log', 'missing_approval_sdk_reader_01.log')")
replace("schema='fraktal.ab.s4b-root-diagnostic-preparation'", "schema='fraktal.ab.s4b-reader-retry-preparation'")
replace('rootTests=74, flutterTests=637, flutterSkipped=12', 'rootTests=74, flutterTests=647, flutterSkipped=12')
replace("W / 'sealed_root_diagnostic_01.json'", "W / 'sealed_reader_retry_01.json'")
exec(compile(source, str(original), 'exec'), {'__file__': __file__})
