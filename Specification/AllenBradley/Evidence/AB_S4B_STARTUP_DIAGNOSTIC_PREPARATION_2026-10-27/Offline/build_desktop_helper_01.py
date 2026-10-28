from pathlib import Path
W=Path(__file__).parent
source=Path('C:/work/fraktal-ab-s4b-status-20261027/session_01/desktop_diagnostic_qualification_test.dart').read_text(encoding='utf-8')
def replace(before,after):
    global source
    assert source.count(before)==1,before
    source=source.replace(before,after)
replace('    expect(live && forceStale,false);',"""    expect(live && forceStale,false);
    final forceStartupFailure=Platform.environment['FRAKTAL_AB_DESKTOP_FORCE_STARTUP_FAILURE_FIXTURE']=='1';
    expect(live && forceStartupFailure,false);""")
replace("""    try {
      await tester.runAsync(() async {
        await loadHmiFonts();""","""    try {
      Object? startupError;
      StackTrace? startupStack;
      await tester.runAsync(() async {
        try {
        await loadHmiFonts();
        if(forceStartupFailure) throw const FormatException('Injected startup fixture refusal');""")
replace("""        await until(()=>app!.link==LinkState.live && app!.forest.isNotEmpty,'discovered forest');
      });
      await tester.pumpWidget""","""        await until(()=>app!.link==LinkState.live && app!.forest.isNotEmpty,'discovered forest');
        } on Object catch(error,stack) {
          startupError=error;
          startupStack=stack;
        }
      });
      if(startupError!=null) Error.throwWithStackTrace(startupError!,startupStack!);
      await tester.pumpWidget""")
with (W/'desktop_diagnostic_qualification_test.dart').open('x',encoding='utf-8',newline='') as f:f.write(source)
runner=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/run_desktop_diagnostic_fixture_01.py').read_text(encoding='utf-8')
runner=runner.replace("if '--force-stale'", "if '--force-startup-failure' in sys.argv[2:]:env['FRAKTAL_AB_DESKTOP_FORCE_STARTUP_FAILURE_FIXTURE']='1'\nif '--force-stale'")
with (W/'run_desktop_fixture_01.py').open('x',encoding='utf-8',newline='') as f:f.write(runner)
record=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/record_hmi_sources_01.py').read_text(encoding='utf-8')
before="C:/work/fraktal-ab-s4b-20261025/offline_01/isolated_hmi_sources_07.json"
assert record.count(before)==1
record=record.replace(before,'C:/work/fraktal-ab-s4b-status-20261027/offline_01/isolated_hmi_sources_01.json')
record=record.replace('test/cip_read_plan_test.dart','test/opcua_freshness_test.dart')
record=record.replace('packages/fraktal_opcua_client/lib/src/cip_read_plan.dart','lib/data/opcua_repository.dart')
with (W/'record_hmi_sources_01.py').open('x',encoding='utf-8',newline='') as f:f.write(record)
print('Prepared helper that retains startup exception and stack before any app use.')
