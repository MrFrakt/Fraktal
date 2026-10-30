@Tags(['live'])
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/ui/cycle_profile_view.dart';
import 'package:fraktal_hmi/ui/cycle_trend_view.dart';

void main() {
  testWidgets('TIA native cycle profile hydrates and renders generic charts',
      (tester) async {
    HttpOverrides.global = null;
    tester.view.physicalSize = const Size(1280, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final evidence = Directory(Platform.environment['FRAKTAL_TIA_HMI_OUTPUT']!);
    final expected = jsonDecode(
        File('${evidence.path}/native_expected.json').readAsStringSync()) as Map;
    final boundary = GlobalKey();
    PlcRepository? repository;
    StreamSubscription<List<ModuleNode>>? subscription;
    List<ModuleNode> forest = const [];
    ModuleNode station() => forest.singleWhere((n) => n.path == 'StationA');
    try {
      await tester.runAsync(() async {
        repository = await createExternalRepository(const ConnectionSettings(
            transport: ConnectionTransport.gateway,
            endpoint: 'ws://127.0.0.1:8107/fraktal'));
        subscription = repository!.forest().listen((value) => forest = value);
        repository!.setModuleDetailActive('StationA', true,
            containers: {'History', 'StepStats'});
        final watch = Stopwatch()..start();
        while (watch.elapsed < const Duration(minutes: 3)) {
          if (forest.length == 2 &&
              station().cycle?.cycleNo == expected['cycleNo'] &&
              station().cycle!.steps.length == (expected['steps'] as List).length &&
              station().cycleHistory.isNotEmpty &&
              station().stepStats.length == (expected['stats'] as List).length) {
            break;
          }
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        expect(forest, hasLength(2));
        final node = station();
        final cycle = node.cycle!;
        expect(cycle.cycleNo, expected['cycleNo']);
        expect(cycle.total.inMilliseconds, expected['total']);
        expect(cycle.workTime.inMilliseconds, expected['work']);
        expect(cycle.waitTime.inMilliseconds, expected['wait']);
        expect(node.lastCycleTime.inMilliseconds, expected['total']);
        expect(node.minCycleTime.inMilliseconds, expected['minimum']);
        expect(cycle.steps, hasLength((expected['steps'] as List).length));
        for (var i = 0; i < cycle.steps.length; i++) {
          final step = cycle.steps[i];
          final actual = (expected['steps'] as List)[i] as Map;
          expect(step.stepNo, actual['number']);
          expect(step.stepName, actual['name']);
          expect(step.timeClass.index, actual['class']);
          expect(step.duration.inMilliseconds, actual['duration']);
          expect(step.expected.inMilliseconds, actual['expected']);
        }
        for (var i = 0; i < node.stepStats.length; i++) {
          final stat = node.stepStats[i];
          final actual = (expected['stats'] as List)[i] as Map;
          expect(stat.stepNo, actual['number']);
          expect(stat.timeClass.index, actual['class']);
          expect(stat.avg.inMilliseconds, actual['average']);
          expect(stat.max.inMilliseconds, actual['maximum']);
        }
        expect(node.cycleHistory.last.cycleNo, expected['cycleNo']);
        expect(node.cycleHistory.last.total.inMilliseconds, expected['total']);
        expect(forest.singleWhere((n) => n.path == 'StationB').cycle, isNull);
        await File('${evidence.path}/hmi_profile.json').writeAsString(jsonEncode({
          'cycleNo': cycle.cycleNo,
          'totalMs': cycle.total.inMilliseconds,
          'workMs': cycle.workTime.inMilliseconds,
          'waitMs': cycle.waitTime.inMilliseconds,
          'steps': cycle.steps.length,
          'stats': node.stepStats.length,
          'history': node.cycleHistory.length,
          'nativeValuesMatch': true,
        }));
      });
      final node = station();
      await tester.pumpWidget(LocalizationScope(
          controller: LocalizationController(
              enabledLanguages: {'en'}, activeLanguage: 'en'),
          child: MaterialApp(
              home: Scaffold(
                  body: RepaintBoundary(
                      key: boundary,
                      child: Column(children: [
                        Expanded(child: CycleProfileView(profile: node.cycle!)),
                        SizedBox(
                            height: 300,
                            child: CycleTrendView(
                                history: node.cycleHistory,
                                minCycleTime: node.minCycleTime)),
                      ]))))));
      await tester.pumpAndSettle();
      expect(find.byType(CycleProfileView), findsOneWidget);
      expect(find.byType(CycleTrendView), findsOneWidget);
      expect(find.byType(CustomPaint), findsWidgets);
      expect(tester.takeException(), isNull);
      await tester.runAsync(() async {
        final image = await (boundary.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('${evidence.path}/hmi_cycle_profile.png')
            .writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.runAsync(() async {
        await subscription?.cancel();
        repository?.dispose();
      });
    }
  },
      skip: Platform.environment['FRAKTAL_TIA_PROFILE_LIVE'] != '1',
      timeout: const Timeout(Duration(minutes: 6)));
}
