// Acceptance helper: captured-fixture mode is rendering proof only. Live mode
// uses the shipping factory and its genuine quality/freshness checks.
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';
import 'file:///C:/work/fraktal-ab-s4b-20261025/hmi_verify_01/tool/screenshots/hmi_driver.dart' show loadHmiFonts;

class _NativeFixtureClient implements OpcUaSessionClient,
    OpcUaWritePolicyClient, OpcUaPathDiscoveryClient, OpcUaBulkReadClient,
    OpcUaDataValueReadClient, OpcUaReadOnlyConfigurationClient,
    OpcUaTieredReadClient {
  final Map<String, Object?> document;
  final List pages;
  int writeCalls = 0;
  _NativeFixtureClient(Map report, Map generic)
      : pages = report['configurationPages'] as List,
        document = Map<String, Object?>.from((report['snapshots'] as List)
            .cast<Map>().lastWhere((s) => s['qualificationDetail'] != true)) {
    final values = <String, Object?>{...Map<String, Object?>.from(generic['values']),
      ...Map<String, Object?>.from(document['values'] as Map)};
    final types = <String, Object?>{...Map<String, Object?>.from(generic['types']),
      ...Map<String, Object?>.from(document['types'] as Map)};
    document.addAll({'values': values, 'types': types, 'paths': values.keys.toList(),
      'nodeCount': values.length, 'dataValues': {for (final e in values.entries)
        e.key: {'type': types[e.key], 'value': e.value, 'status': 0, 'ageMs': 0}}});
    // Deliberately a static UI fixture, not replayed source freshness or a
    // transport acceptance claim. Live mode never applies these substitutions.
    for (final key in ['freshnessBudget','sampleAgeMs','responseProcessingMs']) {
      document.remove(key);
    }
  }
  @override bool get readOnly => true;
  @override Future<Map<String, Object?>> snapshot() async => document;
  @override Future<List<String>> discoverPaths() async => List<String>.from(document['paths'] as List);
  @override Future<Map<String, Object?>> readValues(List<String> paths) async => {
    for (final p in paths) if ((document['values'] as Map).containsKey(p)) p: (document['values'] as Map)[p]};
  @override Future<Map<String, Object?>> readDataValues(List<String> paths) async => {
    'protocol':'fraktal.opcua.read-values.v1', 'values':await readValues(paths),
    'dataValues':{for(final p in paths) if((document['dataValues'] as Map).containsKey(p)) p:(document['dataValues'] as Map)[p]}};
  @override Future<Map<String, Object?>?> readConfigurationPage(String root,int ordinal) async {
    final found = pages.cast<Map>().where((p) => p['root'] == root && p['modelOrdinal'] == ordinal);
    return found.isEmpty ? null : Map<String, Object?>.from(found.single['page'] as Map);
  }
  @override Future<void> setSlowPaths(Iterable<String> paths) async {}
  @override Future<void> setExcludedPaths(Iterable<String> paths) async {}
  @override Future<void> refreshSlowPaths() async {}
  @override Future<bool> write(String path,OpcUaWriteType type,Object value) async {
    writeCalls++;
    throw StateError('Read-only UI attempted a client write.');
  }
  @override Future<void> close() async {}
}

List<String> modulePaths(Iterable<ModuleNode> roots) => [
  for(final node in roots) node.path,
  for(final node in roots) ...modulePaths(node.children)
];

void main() {
  final live = Platform.environment['FRAKTAL_AB_DESKTOP_LIVE'] == '1';
  if (live) {
    final binding = LiveTestWidgetsFlutterBinding.ensureInitialized();
    binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  }
  testWidgets('canonical AB desktop renders discovered surfaces read-only', (tester) async {
    final oldHitTestPolicy=WidgetController.hitTestWarningShouldBeFatal;
    WidgetController.hitTestWarningShouldBeFatal=true;
    addTearDown(()=>WidgetController.hitTestWarningShouldBeFatal=oldHitTestPolicy);
    await tester.binding.setSurfaceSize(const Size(1600,1000));
    addTearDown(()=>tester.binding.setSurfaceSize(null));
    tester.view.physicalSize = const Size(1600,1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final out = Directory(Platform.environment['FRAKTAL_AB_DESKTOP_OUTPUT']!);
    expect(out.existsSync(), false);
    out.createSync(recursive:true);
    final expected=jsonDecode(File(Platform.environment['FRAKTAL_AB_DESKTOP_EXPECTED_INVENTORY']!).readAsStringSync()) as Map;
    final forceStale=Platform.environment['FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE']=='1';
    expect(live && forceStale,false);
    final elapsed=Stopwatch()..start();
    final oldDebug=debugPrint;
    debugPrint=(String? message,{int? wrapWidth}) {
      if(message!=null) File('${out.path}/refresh.log').writeAsStringSync(
        '${elapsed.elapsedMicroseconds} $message\n',mode:FileMode.append);
    };
    addTearDown(()=>debugPrint=oldDebug);
    final boundary = GlobalKey();
    final shots = <Map<String,Object?>>[];
    PlcRepository? repository;
    AppState? app;
    _NativeFixtureClient? fixture;
    var refusedActions=0;
    void record(String stage) {
      File('${out.path}/link_forest.jsonl').writeAsStringSync(jsonEncode({
        'elapsedUs':elapsed.elapsedMicroseconds,'stage':stage,'link':app?.link.name,
        'modules':app==null?[]:modulePaths(app!.forest),
        'selected':app?.selectedPath})+'\n',mode:FileMode.append);
    }
    void requireLive(String stage) {
      record(stage);
      expect(app!.link,LinkState.live,reason:stage);
      expect(modulePaths(app!.forest).toSet(),List<String>.from(expected['modules'] as List).toSet(),reason:stage);
      expect(app!.forest,isNotEmpty,reason:stage);
    }
    Future<void> until(bool Function() condition, String stage) async {
      final timer=Stopwatch()..start();
      while(!condition() && timer.elapsed < const Duration(seconds:30)) {
        await Future<void>.delayed(const Duration(milliseconds:25));
      }
      expect(condition(),true,reason:stage);
    }
    Future<void> capture(String name, String? path, int? tab) async {
      requireLive('before-$name');
      await tester.pump(const Duration(milliseconds:150));
      requireLive('after-$name');
      expect(tester.takeException(),isNull,reason:name);
      expect(repository!.readOnly,true);
      expect(find.byIcon(Icons.visibility_outlined),findsWidgets);
      await tester.runAsync(() async {
        final image=await (boundary.currentContext!.findRenderObject() as RenderRepaintBoundary).toImage();
        final png=await image.toByteData(format:ui.ImageByteFormat.png);
        await File('${out.path}/$name.png').writeAsBytes(png!.buffer.asUint8List());
        image.dispose();
      });
      shots.add({'file':'$name.png','module':path,'tab':tab,'link':app!.link.name,'rootCount':app!.forest.length});
    }
    try {
      await tester.runAsync(() async {
        await loadHmiFonts();
        if (live) {
          final endpoint=Platform.environment['FRAKTAL_AB_DESKTOP_ENDPOINT']!;
          expect(endpoint,'cip://127.0.0.1?slot=0&serial=601FC87B');
          repository=await createExternalRepository(ConnectionSettings(endpoint:endpoint));
        } else {
          final folder=Platform.environment['FRAKTAL_AB_DESKTOP_FIXTURE']!;
          Map read(String name) => jsonDecode(utf8.decode(gzip.decode(File('$folder/$name').readAsBytesSync()))) as Map;
          fixture=_NativeFixtureClient(read('dart_qualification.json.gz'),read('generic_snapshot.json.gz'));
          repository=await OpcUaRepository.connectWithClient(fixture!);
        }
        expect(repository!.readOnly,true);
        final localization=LocalizationController(enabledLanguages:{'en'},activeLanguage:'en');
        app=AppState(repository!,localization:localization,
          content:ModuleContentController(store:MemoryContentStore(),localization:localization));
        app!.addListener(()=>record('state'));
        await until(()=>app!.link==LinkState.live && app!.forest.isNotEmpty,'discovered forest');
      });
      await tester.pumpWidget(RepaintBoundary(key:boundary,child:FraktalHmiApp(app:app!)));
      // Warm the first frame before starting acceptance; no stale frame is
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
      await capture('overview',null,null);
      List<ModuleNode> walk(ModuleNode node) => [node,for(final child in node.children) ...walk(child)];
      final nodes=[for(final root in app!.forest) ...walk(root)];
      expect(nodes,isNotEmpty);
      for(var module=0;module<nodes.length;module++) {
        app!.select(nodes[module].path);
        await tester.pump(const Duration(milliseconds:100));
        expect(app!.permitsLocal(GatedAction.startStop),false);
        expect(app!.permitsLocal(GatedAction.dataWrite),false);
        final tabs=find.byType(TabBar);
        expect(tabs,findsWidgets,reason:'module surface cannot be skipped');
        final count=tester.widget<TabBar>(tabs.first).tabs.length;
        for(var tab=0;tab<count;tab++) {
          final widget=tester.widget<TabBar>(find.byType(TabBar).first).tabs[tab] as Tab;
          expect(widget.text,isNotNull);
          final finder=find.descendant(of:find.byType(TabBar).first,matching:find.text(widget.text!)).first;
          await tester.ensureVisible(finder);
          await tester.pump(const Duration(milliseconds:100));
          await tester.tap(finder);
          await tester.pump(const Duration(milliseconds:300));
          expect(DefaultTabController.of(tester.element(find.byType(TabBar).first)).index,tab);
          await capture('module-$module-tab-$tab',nodes[module].path,tab);
        }
      }
      app!.setFieldbusView(true);
      await capture('fieldbus',null,null);
      List<BusNode> busWalk(BusNode node) => [node,for(final child in node.children) ...busWalk(child)];
      final busNodes=[for(final root in app!.fieldbus) ...busWalk(root)];
      for(var index=0;index<busNodes.length;index++) {
        final finder=find.text(busNodes[index].name).first;
        await tester.ensureVisible(finder);
        await tester.pump(const Duration(milliseconds:100));
        await tester.tap(finder);
        await capture('fieldbus-$index',busNodes[index].name,null);
      }
      expect(fixture?.writeCalls ?? 0,0);
      expect(refusedActions,greaterThan(0));
      expect(nodes.map((n)=>n.path).toSet(),List<String>.from(expected['modules'] as List).toSet());
      expect(busNodes.map((n)=>n.name).toSet(),List<String>.from(expected['fieldbusNodes'] as List).toSet());
      expect(shots.map((s)=>s['file']).toSet(),(expected['shots'] as List).map((s)=>(s as Map)['file']).toSet());
      requireLive('completed');
      File('${out.path}/result.json').writeAsStringSync(jsonEncode({
        'passed':true,'live':live,'capturedFixtureOnly':!live,
        'readOnly':repository!.readOnly,'fixtureClientWriteCalls':fixture?.writeCalls,
        'modules':nodes.map((n)=>n.path).toList(),
        'fieldbusNodes':busNodes.map((n)=>n.name).toList(),'shots':shots,
        'refusedActions':refusedActions,'coverageValidated':true,
        'nativeFreshnessClaim':live,'desktopLiveAccepted':live}));
    } catch(error) {
      File('${out.path}/failure.json').writeAsStringSync(jsonEncode({
        'passed':false,'live':live,'error':error.toString(),'link':app?.link.name,
        'modules':app==null?[]:modulePaths(app!.forest),'shots':shots,
        'refusedActions':refusedActions,'desktopLiveAccepted':false}));
      rethrow;
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      app?.dispose();
      repository?.dispose();
      debugPrint=oldDebug;
    }
  }, timeout:const Timeout(Duration(minutes:5)));
}
