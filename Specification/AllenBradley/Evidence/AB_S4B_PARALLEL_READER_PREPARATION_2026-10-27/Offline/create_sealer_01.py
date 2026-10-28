from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/seal_preparation_01.py').read_text(encoding='utf-8')
def change(before,after):
    global source
    assert source.count(before)==1,(before,source.count(before))
    source=source.replace(before,after)
change('Seal the same-image Status-order retry after all gates','Seal the same-image four-connection reader after all gates')
change("OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')","OLD=Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01')")
change("G=OLD.parent/'offline_01'","G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")
change("P=E/'AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26'","P=E/'AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27'")
change("O=E/'AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27'","O=E/'AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27'")
start=source.index('labels=(');end=source.index('\nfor label in labels:',start)
source=source[:start]+"""labels=('verify_prepared_session_02','pool_tests_06','pool_pub_01','pool_flutter_02',
    'pool_analyze_02','pool_windows_02','record_mirror_03','pool_sdk_build_01',
    'pool_authorization_checks_01','pool_workflow_checks_01','pool_readiness_checks_01',
    'pool_readonly_refusals_01','update_status_01','pool_spec_01','pool_contracts_01',
    'pool_consistency_01','pool_root_tests_01','pool_whitespace_01')"""+source[end:]
start=source.index("for label in ('status_order_before_01'");end=source.index("assert load(W/'cli_refusal_01_exit.json')",start)
source=source[:start]+"""for label in ('pool_tests_04','pool_tests_05'):
    assert load(W/(label+'_exit.json'))['exitCode']==1,label
"""+source[end:]
for before,after in (
 ('648 ~12: All tests passed!','660 ~12: All tests passed!'),
 ('status_flutter_01.log','pool_flutter_02.log'),('status_analyze_01.log','pool_analyze_02.log'),
 ('status_root_tests_01.log','pool_root_tests_01.log'),("['observerSamples']==68","['observerSamples']==906"),
 ("W/'isolated_hmi_sources_01.json'","W/'isolated_hmi_sources_03.json'"),
 ("assert len(mirror['files'])==316 and len(mirror['changed'])==2","assert len(mirror['files'])==318 and len(mirror['changed'])==6 and len(mirror['added'])==2"),
 ("'test/cip_read_plan_test.dart')}","'packages/fraktal_opcua_client/lib/src/cip_transport.dart',\n    'packages/fraktal_opcua_client/lib/src/cip_session_client.dart',\n    'packages/fraktal_opcua_client/lib/src/cip_read_coherence.dart',\n    'test/cip_read_coherence_test.dart','test/cip_transport_test.dart')}"),
 ("assert sum('/FraktalCore/HMI/' in name for name in changed)==2","assert sum('/FraktalCore/HMI/' in name for name in changed)==6"),
 ("names.update(('AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26','AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27'))",
  "names.update(('AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27','AB_S4B_STARTUP_DIAGNOSTIC_ATTEMPT_2026-10-27'))"),
 ('assert len(names)==90','assert len(names)==94'),
 ('fraktal.ab.s4b-status-order-source-bindings','fraktal.ab.s4b-parallel-reader-source-bindings'),
 ("changedHmiFiles=mirror['changed'],hmiMirrorInputs=316","changedHmiFiles=mirror['changed'],addedHmiFiles=mirror['added'],hmiMirrorInputs=318"),
 ('status_preparation_report_01.md','parallel_preparation_report_01.md'),
 ('fraktal.ab.s4b-status-order-preparation','fraktal.ab.s4b-parallel-reader-preparation'),
 ('flutterTests=648','flutterTests=660'),('unchangedPlcBoundFiles=373,changedHmiFiles=2','unchangedPlcBoundFiles=373,changedHmiFiles=6,addedHmiFiles=2,readConnections=4')):
    change(before,after)
change('files.add(package)',"""files.add(package)
helper=package.parent.parent/'tool/desktop_startup_diagnostic_test.dart'
assert helper.read_bytes()==(S/'desktop_diagnostic_qualification_test.dart').read_bytes()
files.add(helper)
# Strict UI helper and fixtures are unchanged; retain the exact earlier proofs.
U=OLD.parent/'offline_01'
positive=load(U.parent/'desktop_diagnostic_fixture_01/result.json')
assert positive['passed'] and positive['coverageValidated'] and len(positive['shots'])==31 and not positive['live']
startup=load(U.parent/'desktop_diagnostic_fixture_02/failure.json')
assert startup['error']=='FormatException: Injected startup fixture refusal' and not startup['desktopLiveAccepted']
assert b'Null check operator' not in (U/'desktop_startup_refused_01.log').read_bytes()
assert load(U.parent/'desktop_diagnostic_fixture_03/failure.json')['link']=='stale'
assert (S/'desktop_diagnostic_qualification_test.dart').read_bytes()==(OLD/'desktop_diagnostic_qualification_test.dart').read_bytes()
assert load(W/'verified_prepared_session_02.json')['preparedInputsVerified']
""")
change("for name in ('ab_suite_01','build_EchoController_01'","""for folder in sorted(U.parent.glob('desktop_diagnostic_fixture_*')):
    for path in sorted(folder.rglob('*')):
        if path.is_file():archive(path,'RetainedDesktop/'+folder.name+'/'+path.relative_to(folder).as_posix())
for label in ('desktop_positive_01','desktop_startup_refused_01','desktop_stale_refused_01'):
    for suffix in ('.log','_exit.json'):archive(U/(label+suffix),'RetainedDesktop/'+label+suffix)
for name in ('ab_suite_01','build_EchoController_01'""")
with (W/'seal_preparation_01.py').open('x',encoding='utf-8',newline='') as f:f.write(source)
compile(source,str(W/'seal_preparation_01.py'),'exec')
print('Materialized strict append-only preparation sealer; no controller access.')
