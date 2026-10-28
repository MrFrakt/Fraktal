@Tags(['live'])
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/content_store.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/custom_module_tabs.dart';
import 'package:fraktal_hmi/ui/sequence_module_tab.dart';

void main() {
  if (Platform.environment['FRAKTAL_TIA_SEQUENCE_LIVE'] == '1') {
    final binding = LiveTestWidgetsFlutterBinding.ensureInitialized();
    binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  }
  testWidgets(
      'TIA: manifest definitions, live cursor, deferred history and chart',
      (tester) async {
    HttpOverrides.global = null;
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final evidence = Directory(Platform.environment['FRAKTAL_TIA_HMI_OUTPUT']!);
    final boundary = GlobalKey();
    PlcRepository? repository;
    StreamSubscription<List<ModuleNode>>? subscription;
    AppState? app;
    List<ModuleNode> forest = const [];
    ModuleNode station() => forest.singleWhere((n) => n.path == 'StationA');
    Future<void> until(bool Function() predicate, String stage) async {
      final watch = Stopwatch()..start();
      while (!predicate() && watch.elapsed < const Duration(minutes: 3)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      await File('${evidence.path}/$stage.json').writeAsString(jsonEncode([
        for (final root in forest)
          {
            'path': root.path,
            'count': root.sequenceStepCount,
            'rows': [
              for (final row in root.sequenceSteps)
                {
                  'stepNo': row.stepNo,
                  'active': row.active,
                  'visited': row.visited,
                  'lastDurationMs': row.lastDuration.inMilliseconds,
                  'warning': row.warningActive,
                }
            ],
          }
      ]));
      expect(predicate(), isTrue, reason: 'native sequence deadline: $stage');
    }

    try {
      await tester.runAsync(() async {
        final font = await File(r'C:\Windows\Fonts\segoeui.ttf').readAsBytes();
        for (final family in ['Roboto', 'Segoe UI', 'Ahem', 'monospace']) {
          final loader = FontLoader(family);
          loader.addFont(Future.value(ByteData.sublistView(font)));
          await loader.load();
        }
        final icons = FontLoader('MaterialIcons');
        icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
        await icons.load();
        repository = await createExternalRepository(const ConnectionSettings(
            transport: ConnectionTransport.gateway,
            endpoint: 'ws://127.0.0.1:8107/fraktal'));
        subscription = repository!.forest().listen((value) => forest = value);
        await until(
            () =>
                forest.length == 2 &&
                station().sequenceStepCount == 2 &&
                station().sequenceSteps.any((s) => s.stepNo == 42),
            'static');
        expect(moduleTabCapabilities(station()).sequence, isTrue);
        expect(station().sequenceViewEnabled, isTrue);
        expect(
            station().sequenceSteps.singleWhere((s) => s.stepNo == 42).active,
            isTrue);
        // Static metadata and the live cursor arrive before the tab opens.
        // The fast row's visited bit is deferred PLC history, never inferred.
        expect(
            station().sequenceSteps.singleWhere((s) => s.stepNo == 11).visited,
            isFalse);
        final localization = LocalizationController(
            enabledLanguages: {'en'}, activeLanguage: 'en');
        app = AppState(repository!,
            localization: localization,
            content: ModuleContentController(
                store: MemoryContentStore(), localization: localization));
        await until(() => app!.forest.length == 2, 'app');
      });
      app!.select('StationA');
      await tester.pumpWidget(
          RepaintBoundary(key: boundary, child: FraktalHmiApp(app: app!)));
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull);
      await tester.tap(find.descendant(
          of: find.byType(TabBar), matching: find.text('Sequence')));
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.byType(SequenceModuleTab), findsOneWidget);
      await tester.runAsync(() async {
        await until(
            () =>
                station().sequenceSteps.any((s) =>
                    s.stepNo == 11 &&
                    s.visited &&
                    s.lastDuration.inMilliseconds == 2) &&
                station()
                    .sequenceSteps
                    .any((s) => s.stepNo == 42 && s.warningActive),
            'detail');
      });
      await tester.pump(const Duration(milliseconds: 300));
      expect(tester.takeException(), isNull);
      expect(find.byType(SequenceModuleTab), findsOneWidget);
      expect(find.text('N42'), findsOneWidget);
      expect(find.text('N11'), findsOneWidget);
      final main = station().sequenceSteps.singleWhere((s) => s.stepNo == 42);
      expect(main.stepName, 'test.integration.main');
      expect(main.awaitsPath, 'StationA.Cell.Clamp');
      expect(main.active, isTrue);
      expect(main.timedOut, isTrue);
      expect(main.elapsed.inMilliseconds, 75);
      expect(main.expected.inMilliseconds, 50);
      expect(main.warningKey, 'test.integration.warning');
      expect(main.warningSourcePath, 'StationA.Cell.Clamp');
      expect(
          forest.singleWhere((n) => n.path == 'StationB').sequenceStepCount, 0);
      await tester.runAsync(() async {
        final image = await (boundary.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final png = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('${evidence.path}/hmi-sequence.png')
            .writeAsBytes(png!.buffer.asUint8List());
        image.dispose();
        await File('${evidence.path}/hmi-sequence.json')
            .writeAsString(jsonEncode({
          'count': station().sequenceStepCount,
          'rows': [
            for (final s in station().sequenceSteps)
              {
                'stepNo': s.stepNo,
                'title': s.stepName,
                'branch': s.branch,
                'active': s.active,
                'visited': s.visited,
                'elapsedMs': s.elapsed.inMilliseconds,
                'lastDurationMs': s.lastDuration.inMilliseconds,
                'expectedMs': s.expected.inMilliseconds,
                'warning': s.warningActive,
                'warningKey': s.warningKey,
              }
          ],
          'genericChartRendered': true,
          'fastHistoryDeferredUntilTab': true,
        }));
      });
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.runAsync(() async {
        app?.dispose();
        await subscription?.cancel();
        if (app == null) repository?.dispose();
      });
    }
  },
      skip: Platform.environment['FRAKTAL_TIA_SEQUENCE_LIVE'] != '1',
      timeout: const Timeout(Duration(minutes: 6)));
}
