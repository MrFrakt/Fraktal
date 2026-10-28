from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/seal_preparation_01.py')
source=original.read_text(encoding='utf-8')
def replace(before,after,count=1):
    global source
    assert source.count(before)==count,(before,source.count(before))
    source=source.replace(before,after)
replace("OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-status-20261027/session_01')")
replace("G=OLD.parent/'offline_01'","G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")
replace("P=E/'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26'","P=E/'AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27'")
replace("O=E/'AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27'","O=E/'AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27'")
start=source.index('labels=(');end=source.index('\nfor label in labels:',start)
source=source[:start]+"""labels=('prepare_session_01','startup_freshness_test_01','startup_pub_01','startup_flutter_01',
    'startup_analyze_01','startup_windows_01','record_hmi_sources_01','desktop_positive_01',
    'startup_sdk_build_01','startup_authorization_checks_01','startup_workflow_checks_01',
    'startup_readiness_checks_01','startup_readonly_refusals_01','update_status_01',
    'startup_spec_01','startup_contracts_01','startup_consistency_01','startup_root_tests_01','startup_whitespace_01')"""+source[end:]
start=source.index("for label in ('status_order_before_01'");end=source.index("\nassert load(W/'cli_refusal_01_exit.json')",start)
source=source[:start]+"""for label in ('desktop_startup_refused_01','desktop_stale_refused_01'):
    assert load(W/(label+'_exit.json'))['exitCode']==1,label
startup=load(W.parent/'desktop_diagnostic_fixture_02/failure.json')
assert startup['error']=='FormatException: Injected startup fixture refusal'
assert not startup['desktopLiveAccepted'] and not startup['shots']
assert b'Null check operator' not in (W/'desktop_startup_refused_01.log').read_bytes()
assert not (W.parent/'desktop_diagnostic_fixture_02/result.json').exists()
stale=load(W.parent/'desktop_diagnostic_fixture_03/failure.json')
assert stale['link']=='stale' and not stale['desktopLiveAccepted']
positive=load(W.parent/'desktop_diagnostic_fixture_01/result.json')
assert positive['passed'] and positive['coverageValidated'] and len(positive['shots'])==31
assert not positive['live']
"""+source[end:]
for before,after in (('status_flutter_01.log','startup_flutter_01.log'),('status_analyze_01.log','startup_analyze_01.log'),
    ('status_root_tests_01.log','startup_root_tests_01.log'),("['observerSamples']==68","['observerSamples']==910"),
    ('packages/fraktal_opcua_client/lib/src/cip_read_plan.dart','lib/data/opcua_repository.dart'),
    ('test/cip_read_plan_test.dart','test/opcua_freshness_test.dart'),
    ("names.update(('AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26','AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27'))",
     "names.update(('AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27','AB_S4B_STATUS_ORDER_ATTEMPT_2026-10-27'))"),
    ('assert len(names)==90','assert len(names)==92'),
    ('status_preparation_report_01.md','startup_preparation_report_01.md'),
    ('fraktal.ab.s4b-status-order-source-bindings','fraktal.ab.s4b-startup-diagnostic-source-bindings'),
    ('fraktal.ab.s4b-status-order-preparation','fraktal.ab.s4b-startup-diagnostic-preparation')):
    replace(before,after)
replace('files.add(package)',"""files.add(package)
helper=package.parent.parent/'tool/desktop_startup_diagnostic_test.dart'
assert helper.read_bytes()==(S/'desktop_diagnostic_qualification_test.dart').read_bytes()
files.add(helper)""")
before="for name in ('ab_suite_01','build_EchoController_01'"
assert source.count(before)==1
source=source.replace(before,"""for folder in sorted(W.parent.glob('desktop_diagnostic_fixture_*')):
    for path in sorted(folder.rglob('*')):
        if path.is_file():archive(path,'Desktop/'+folder.name+'/'+path.relative_to(folder).as_posix())
for name in ('ab_suite_01','build_EchoController_01'""")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
