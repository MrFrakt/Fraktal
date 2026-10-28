from pathlib import Path

W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s4b-20261025/offline_01/desktop_readonly_qualification_test.dart')
source=OLD.read_text(encoding='utf-8')
def replace(before,after):
    global source
    assert source.count(before)==1,before
    source=source.replace(before,after)
replace('void main() {',"""List<String> modulePaths(Iterable<ModuleNode> roots) => [
  for(final node in roots) node.path,
  for(final node in roots) ...modulePaths(node.children)
];

void main() {""")
replace("    tester.view.physicalSize = const Size(1600,1000);","    await tester.binding.setSurfaceSize(const Size(1600,1000));\n    addTearDown(()=>tester.binding.setSurfaceSize(null));\n    tester.view.physicalSize = const Size(1600,1000);")
replace('    final boundary = GlobalKey();',"""    final expected=jsonDecode(File(Platform.environment['FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY']!).readAsStringSync()) as Map;
    final forceStale=Platform.environment['FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE']=='1';
    expect(live && forceStale,false);
    final elapsed=Stopwatch()..start();
    final oldDebug=debugPrint;
    debugPrint=(String? message,{int? wrapWidth}) {
      if(message!=null) File('${out.path}/refresh.log').writeAsStringSync(
        '${elapsed.elapsedMicroseconds} $message\\n',mode:FileMode.append);
    };
    addTearDown(()=>debugPrint=oldDebug);
    final boundary = GlobalKey();""")
replace('    _NativeFixtureClient? fixture;',"""    _NativeFixtureClient? fixture;
    var refusedActions=0;
    void record(String stage) {
      File('${out.path}/link_forest.jsonl').writeAsStringSync(jsonEncode({
        'elapsedUs':elapsed.elapsedMicroseconds,'stage':stage,'link':app?.link.name,
        'modules':app==null?[]:modulePaths(app!.forest),
        'selected':app?.selectedPath})+'\\n',mode:FileMode.append);
    }
    void requireLive(String stage) {
      record(stage);
      expect(app!.link,LinkState.live,reason:stage);
      expect(modulePaths(app!.forest).toSet(),List<String>.from(expected['modules'] as List).toSet(),reason:stage);
      expect(app!.forest,isNotEmpty,reason:stage);
    }""")
replace("      await tester.pump(const Duration(milliseconds:150));\n      expect(tester.takeException(),isNull,reason:name);","      requireLive('before-$name');\n      await tester.pump(const Duration(milliseconds:150));\n      requireLive('after-$name');\n      expect(tester.takeException(),isNull,reason:name);")
replace("      shots.add({'file':'$name.png','module':path,'tab':tab});","      shots.add({'file':'$name.png','module':path,'tab':tab,'link':app!.link.name,'rootCount':app!.forest.length});")
replace("        await until(()=>app!.forest.isNotEmpty,'discovered forest');\n        for(final root in app!.forest) {\n          expect(await repository!.start(root.path),false);\n          expect(await repository!.login(root.path,'read_only_refusal',''),false);\n        }","        app!.addListener(()=>record('state'));\n        await until(()=>app!.link==LinkState.live && app!.forest.isNotEmpty,'discovered forest');")
replace("      await capture('overview',null,null);","""      // Warm the first frame before starting acceptance; no stale frame is
      // counted and the original 30-second readiness bound remains in force.
      await tester.runAsync(() async {
        await until(()=>app!.link==LinkState.live && app!.forest.isNotEmpty,'fresh forest after first frame');
        requireLive('desktop-ready');
        final roots=app!.forest.toList();
        expect(roots,isNotEmpty);
        for(final root in roots) {
          expect(await repository!.start(root.path),false);
          expect(await repository!.login(root.path,'read_only_refusal',''),false);
          refusedActions+=2;
        }
      });
      if(forceStale) {
        app!.link=LinkState.stale;
        app!.forest=const [];
      }
      await capture('overview',null,null);""")
replace("      final nodes=[for(final root in app!.forest) ...walk(root)];","      final nodes=[for(final root in app!.forest) ...walk(root)];\n      expect(nodes,isNotEmpty);")
replace("        if(tabs.evaluate().isEmpty) {\n          await capture('module-$module',nodes[module].path,null);\n          continue;\n        }","        expect(tabs,findsWidgets,reason:'module surface cannot be skipped');")
replace("      expect(fixture?.writeCalls ?? 0,0);","""      expect(fixture?.writeCalls ?? 0,0);
      expect(refusedActions,greaterThan(0));
      expect(nodes.map((n)=>n.path).toSet(),List<String>.from(expected['modules'] as List).toSet());
      expect(busNodes.map((n)=>n.name).toSet(),List<String>.from(expected['fieldbusNodes'] as List).toSet());
      expect(shots.map((s)=>s['file']).toSet(),(expected['shots'] as List).map((s)=>(s as Map)['file']).toSet());
      requireLive('completed');""")
replace("        'nativeFreshnessClaim':live,'desktopLiveAccepted':live}));","        'refusedActions':refusedActions,'coverageValidated':true,\n        'nativeFreshnessClaim':live,'desktopLiveAccepted':live}));")
replace('    } finally {',"""    } catch(error) {
      File('${out.path}/failure.json').writeAsStringSync(jsonEncode({
        'passed':false,'live':live,'error':error.toString(),'link':app?.link.name,
        'modules':app==null?[]:modulePaths(app!.forest),'shots':shots,
        'refusedActions':refusedActions,'desktopLiveAccepted':false}));
      rethrow;
    } finally {""")
replace('      repository?.dispose();','      repository?.dispose();\n      debugPrint=oldDebug;')
with (W/'desktop_diagnostic_qualification_test.dart').open('x',encoding='utf-8') as stream:stream.write(source)
print('Generated strict desktop helper; stale/empty coverage cannot pass.')
