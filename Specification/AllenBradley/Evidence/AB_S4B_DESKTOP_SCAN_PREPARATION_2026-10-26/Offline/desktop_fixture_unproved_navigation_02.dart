// Acceptance helper: captured-fixture mode is rendering proof only. Live mode
// uses the shipping factory and its genuine quality/freshness checks.
import 'dart:async';
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

void main() {
  final live = Platform.environment['FRAKTAL_AB_DESKTOP_LIVE'] == '1';
  if (live) {
    final binding = LiveTestWidgetsFlutterBinding.ensureInitialized();
    binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  }
  testWidgets('canonical AB desktop renders discovered surfaces read-only', (tester) async {
    tester.view.physicalSize = const Size(1600,1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final out = Directory(Platform.environment['FRAKTAL_AB_DESKTOP_OUTPUT']!);
    expect(out.existsSync(), false);
    out.createSync(recursive:true);
    final boundary = GlobalKey();
    final shots = <Map<String,Object?>>[];
    PlcRepository? repository;
    AppState? app;
    _NativeFixtureClient? fixture;
    Future<void> until(bool Function() condition, String stage) async {
      final timer=Stopwatch()..start();
      while(!condition() && timer.elapsed < const Duration(seconds:30)) {
        await Future<void>.delayed(const Duration(milliseconds:25));
      }
      expect(condition(),true,reason:stage);
    }
    Future<void> capture(String name, String? path, int? tab) async {
      await tester.pump(const Duration(milliseconds:150));
      expect(tester.takeException(),isNull,reason:name);
      expect(repository!.readOnly,true);
      expect(find.byIcon(Icons.visibility_outlined),findsWidgets);
      await tester.runAsync(() async {
        final image=await (boundary.currentContext!.findRenderObject() as RenderRepaintBoundary).toImage();
        final png=await image.toByteData(format:ui.ImageByteFormat.png);
        await File('${out.path}/$name.png').writeAsBytes(png!.buffer.asUint8List());
        image.dispose();
      });
      shots.add({'file':'$name.png','module':path,'tab':tab});
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
        await until(()=>app!.forest.isNotEmpty,'discovered forest');
        for(final root in app!.forest) {
          expect(await repository!.start(root.path),false);
          expect(await repository!.login(root.path,'read_only_refusal',''),false);
        }
      });
      await tester.pumpWidget(RepaintBoundary(key:boundary,child:FraktalHmiApp(app:app!)));
      await capture('overview',null,null);
      List<ModuleNode> walk(ModuleNode node) => [node,for(final child in node.children) ...walk(child)];
      final nodes=[for(final root in app!.forest) ...walk(root)];
      for(var module=0;module<nodes.length;module++) {
        app!.select(nodes[module].path);
        await tester.pump(const Duration(milliseconds:100));
        expect(app!.permitsLocal(GatedAction.startStop),false);
        expect(app!.permitsLocal(GatedAction.dataWrite),false);
        final tabs=find.byType(TabBar);
        if(tabs.evaluate().isEmpty) {
          await capture('module-$module',nodes[module].path,null);
          continue;
        }
        final count=tester.widget<TabBar>(tabs.first).tabs.length;
        for(var tab=0;tab<count;tab++) {
          final widget=tester.widget<TabBar>(find.byType(TabBar).first).tabs[tab];
          final finder=find.byWidget(widget);
          await tester.ensureVisible(finder);
          await tester.tap(finder);
          await capture('module-$module-tab-$tab',nodes[module].path,tab);
        }
      }
      app!.setFieldbusView(true);
      await capture('fieldbus',null,null);
      expect(fixture?.writeCalls ?? 0,0);
      await File('${out.path}/result.json').writeAsString(jsonEncode({
        'passed':true,'live':live,'capturedFixtureOnly':!live,
        'readOnly':repository!.readOnly,'fixtureClientWriteCalls':fixture?.writeCalls,
        'modules':nodes.map((n)=>n.path).toList(),'shots':shots,
        'nativeFreshnessClaim':live,'desktopLiveAccepted':live}));
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      app?.dispose();
      repository?.dispose();
    }
  }, timeout:const Timeout(Duration(minutes:5)));
}
