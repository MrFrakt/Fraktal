@Tags(['live'])
library;

// Opt-in simulated S7-1500 gate through the production gateway/repository/UI.
// Tests/Manifest/run_gateway.dart guards every native write before transport.
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
import 'package:fraktal_hmi/data/opcua_gateway_client_io.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/reason_catalog.g.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';

void main() {
  if (Platform.environment['FRAKTAL_TIA_MANIFEST_LIVE'] == '1') {
    final binding = LiveTestWidgetsFlutterBinding.ensureInitialized();
    binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  }
  testWidgets('TIA: live forest, static hydration, rendered manual command',
      (tester) async {
    HttpOverrides.global = null;
    tester.view.physicalSize = const Size(1600, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final endpoint = Uri.parse('ws://127.0.0.1:8107/fraktal');
    final evidence = Directory(Platform.environment['FRAKTAL_TIA_HMI_OUTPUT']!);
    final authenticated =
        Platform.environment['FRAKTAL_TIA_ACCESS_LIVE'] == '1';
    final stateAlarm =
        Platform.environment['FRAKTAL_TIA_STATE_ALARM_LIVE'] == '1';
    final configLive = Platform.environment['FRAKTAL_TIA_CONFIG_LIVE'] == '1';
    final setsLive =
        Platform.environment['FRAKTAL_TIA_CONFIG_SETS_LIVE'] == '1';
    PlcRepository? repository;
    IoGatewayOpcUaClient? observer;
    StreamSubscription<List<ModuleNode>>? subscription;
    AppState? app;
    List<ModuleNode> forest = const [];

    Iterable<ModuleNode> walk(List<ModuleNode> nodes) sync* {
      for (final node in nodes) {
        yield node;
        yield* walk(node.children);
      }
    }

    ModuleNode node(String path) =>
        walk(forest).singleWhere((n) => n.path == path);
    Future<void> until(bool Function() predicate,
        {Duration timeout = const Duration(minutes: 3)}) async {
      final timer = Stopwatch()..start();
      while (!predicate() && timer.elapsed < timeout) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      expect(predicate(), isTrue, reason: 'live state deadline');
    }

    const target = 'StationA.Cell.Gate';
    const browse = 'PLC1/StationA/Cell/Gate';
    const started = '$browse/OutImm/StartCount';
    final boundary = GlobalKey();
    try {
      await tester.runAsync(() async {
        final textFont =
            await File(r'C:\Windows\Fonts\segoeui.ttf').readAsBytes();
        for (final family in ['Roboto', 'Segoe UI', 'Ahem', 'monospace']) {
          final loader = FontLoader(family);
          loader.addFont(Future.value(ByteData.sublistView(textFont)));
          await loader.load();
        }
        final icons = FontLoader('MaterialIcons');
        icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
        await icons.load();
        observer = await IoGatewayOpcUaClient.connect(endpoint);
        repository = await createExternalRepository(ConnectionSettings(
            transport: ConnectionTransport.gateway,
            endpoint: endpoint.toString()));
        subscription = repository!.forest().listen((value) => forest = value);
        await until(() => walk(forest).any((n) =>
            n.path == 'StationB.Satellite.Inner.Cell.Gate' &&
            n.commands.length == 7));
        expect(forest.map((n) => n.path).toList(), ['StationA', 'StationB']);
        expect(walk(forest), hasLength(24));
        expect(node(target).commands.singleWhere((c) => c.value == 6).label,
            'Instant');
        expect(
            node(target).commands.every((c) => c.style == CommandStyle.oneShot),
            isTrue);
        expect(node('StationA').modeActive, UnitMode.manual);
        if (stateAlarm) {
          expect(
              node('StationA').stateFlags.single.key, 'project.state.atHome');
          expect(node('StationA').stateFlags.single.value, isTrue);
          expect(node('StationA').stateFlags.single.stale, isFalse);
        }
        expect(node('StationA').supportedModes, contains(UnitMode.changeover));
        expect(node('StationA.Satellite.Inner').supportedModes,
            isNot(contains(UnitMode.changeover)));
        if (authenticated) {
          expect(node('StationA').access?.level, AccessLevel.none);
          final blocked =
              await repository!.releaseReportManual('StationA', target, 6);
          expect(blocked.released, isFalse);
          expect(await repository!.login('StationA', 'operator', 'wrong'),
              isFalse);
          expect(
              await repository!.login('StationA', 'operator',
                  Platform.environment['FRAKTAL_TIA_OPERATOR_PIN']!),
              isTrue);
          await until(
              () => node('StationA').access?.level == AccessLevel.operator);
          expect(node('StationB').access?.level, AccessLevel.none);
        }
        final release =
            await repository!.releaseReportManual('StationA', target, 6);
        expect(release.released, isTrue);
        final denied =
            await repository!.releaseReportManual('StationA', target, 999);
        expect(denied.released, isFalse);
        expect(
            await repository!
                .manualCommand('StationA', 'StationB.Cell.Gate', 6),
            isFalse);
        final localization = LocalizationController(
            enabledLanguages: {'en'}, activeLanguage: 'en');
        app = AppState(repository!,
            localization: localization,
            content: ModuleContentController(
                store: MemoryContentStore(), localization: localization));
        if (!authenticated) {
          // The earlier manifest-only fixture has no login provider.
          await app!.content.setRequiredLevel(
              target, ModuleSection.operations, AccessLevel.none);
        }
        await until(() => app!.forest.length == 2);
      });
      app!.expanded.addAll([
        'StationA',
        'StationA.Cell',
        'StationA.Satellite',
        'StationA.Satellite.Inner'
      ]);
      app!.select(target);
      await tester.pumpWidget(
          RepaintBoundary(key: boundary, child: FraktalHmiApp(app: app!)));
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull);
      expect(find.text('Instant'), findsWidgets);
      final before = await tester.runAsync(
          () async => (await observer!.readValues([started]))[started] as int);
      final button = find
          .ancestor(
              of: find.text('Instant'), matching: find.byType(FilledButton))
          .first;
      await tester.runAsync(() async {
        await tester.tap(button);
        final timer = Stopwatch()..start();
        var actual = before;
        while (
            actual == before && timer.elapsed < const Duration(seconds: 30)) {
          actual = (await observer!.readValues([started]))[started] as int;
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        expect(actual, before! + 1,
            reason: 'native command counter after rendered button');
        if (stateAlarm) {
          final faultButton = find
              .ancestor(
                  of: find.text('Fault'), matching: find.byType(FilledButton))
              .first;
          await tester.tap(faultButton);
          await until(() =>
              node('StationA').blocking &&
              node('StationA').activeEvents.any((event) =>
                  event.sourcePath == target &&
                  event.state == AlarmState.waitReset));
          final event = node('StationA')
              .activeEvents
              .singleWhere((event) => event.sourcePath == target);
          expect(event.resetClass, ResetClass.manualReset);
          expect(event.description, reasonDescriptionKey(2901, 'test.first'));
          expect(event.goneAt, isNotNull);
          expect(event.comeTimeSynchronized, isFalse);
          expect(
              (await repository!.releaseReportManual('StationA', target, 6))
                  .released,
              isFalse);
        }
        if (authenticated) {
          expect(
              await repository!.login('StationB', 'operator',
                  Platform.environment['FRAKTAL_TIA_OPERATOR_PIN']!),
              isTrue);
        }
        await repository!.setMode('StationB', UnitMode.auto);
        await until(() => node('StationB').modeActive == UnitMode.auto);
        expect(node('StationA').modeActive, UnitMode.manual);
        await repository!.setMode('StationB', UnitMode.manual);
        await until(() => node('StationB').modeActive == UnitMode.manual);
      });
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull);
      if (stateAlarm) {
        app!.select('StationA');
        await tester.pump(const Duration(milliseconds: 500));
        expect(
            find.textContaining(generatedReasonEnglish[
                reasonDescriptionKey(2901, 'test.first')]!),
            findsWidgets);
        await tester.runAsync(() async {
          final alarmImage = await (boundary.currentContext!.findRenderObject()
                  as RenderRepaintBoundary)
              .toImage();
          final png =
              await alarmImage.toByteData(format: ui.ImageByteFormat.png);
          await File('${evidence.path}/hmi-alarm.png')
              .writeAsBytes(png!.buffer.asUint8List());
          alarmImage.dispose();
          await tester.tap(find.byKey(const Key('global-reset')));
          await until(() =>
              !node('StationA').blocking &&
              node('StationA').activeEvents.isEmpty);
          expect(
              node('StationA').ringEvents.any((event) =>
                  event.sourcePath == target &&
                  event.resetClass == ResetClass.manualReset),
              isTrue);
        });
        app!.select(target);
        await tester.pump(const Duration(milliseconds: 500));
      }
      if (configLive) {
        await tester.runAsync(() async {
          expect(
              await repository!.login('StationA', 'admin',
                  Platform.environment['FRAKTAL_TIA_ADMIN_PIN']!),
              isTrue);
          await until(
              () => node('StationA').access?.level == AccessLevel.admin);
          await until(() =>
              node('StationA').config.any((f) => f.writeKey == 'preset') &&
              app!.forest.any((n) =>
                  n.path == 'StationA' &&
                  n.config.any((f) => f.writeKey == 'preset')));
        });
        app!.select('StationA');
        await tester.pump(const Duration(milliseconds: 500));
        await tester.tap(find.descendant(
            of: find.byType(TabBar), matching: find.text('Configuration')));
        await tester.pump(const Duration(milliseconds: 500));
        expect(find.text('Model config'), findsWidgets);
        expect(find.text('Station config'), findsWidgets);
        final row = find.byKey(const ValueKey('cfg-0-preset'));
        expect(row, findsOneWidget);
        await tester.ensureVisible(row);
        await tester.pump(const Duration(milliseconds: 500));
        final input =
            find.descendant(of: row, matching: find.byType(EditableText));
        await tester.enterText(input, '21');
        await tester.pump(const Duration(milliseconds: 500));
        await tester.runAsync(() async {
          await tester.tap(find
              .descendant(of: row, matching: find.byType(IconButton))
              .first);
          // The simulator guard adds a process round-trip to every mailbox
          // write, so allow the complete two-root config manifest to finish.
          // The independent observer below also verifies the actual value.
          final writeTimer = Stopwatch()..start();
          await until(
              () => node('StationA').config.any(
                  (f) => f.writeKey == 'preset' && int.tryParse(f.value) == 21),
              timeout: const Duration(minutes: 8));
          debugPrint('[Fraktal/Test] config-write-visible-ms='
              '${writeTimer.elapsedMilliseconds}');
          final native =
              await observer!.readValues(['PLC1/StationA/ParCfg/Preset']);
          expect(native['PLC1/StationA/ParCfg/Preset'], 21);
          final inactive = await repository!.queryModelConfig('StationA', 2);
          expect(inactive, isNotNull);
          expect(
              inactive!.every((f) => f.kind == CfgKind.parCfg && f.modelScoped),
              isTrue);
          expect(inactive.singleWhere((f) => f.writeKey == 'preset').value,
              isNot('21'));
          final image = await (boundary.currentContext!.findRenderObject()
                  as RenderRepaintBoundary)
              .toImage();
          final png = await image.toByteData(format: ui.ImageByteFormat.png);
          await File('${evidence.path}/hmi-config.png')
              .writeAsBytes(png!.buffer.asUint8List());
          image.dispose();
          final field = node('StationA')
              .config
              .singleWhere((f) => f.writeKey == 'preset');
          expect(
              await repository!.writeConfig('StationA', field, '10'), isTrue);
          await until(
              () => node('StationA').config.any(
                  (f) => f.writeKey == 'preset' && int.tryParse(f.value) == 10),
              timeout: const Duration(minutes: 8));
        });
        app!.select(target);
        await tester.pump(const Duration(milliseconds: 500));
      }
      if (setsLive) {
        await tester.runAsync(() async {
          expect(
              await repository!
                  .saveConfigSet('StationA', 'hmi-station', CfgKind.stationCfg),
              isTrue);
          final sets = await repository!.listConfigSets('StationA');
          expect(
              sets!.any((set) =>
                  set.name == 'hmi-station' && set.rootIdentity == 'StationA'),
              isTrue);
          final document =
              await repository!.exportConfigSet('StationA', 'hmi-station');
          expect(document, isNotNull);
          final lines = document!
              .split('\n')
              .map((line) => jsonDecode(line) as Map<String, dynamic>)
              .toList();
          expect(lines.first['records'], lines.length - 1);
          lines.first['set'] = 'hmi-imported';
          expect(
              await repository!.importConfigSet(
                  'StationA', lines.map(jsonEncode).join('\n')),
              isTrue);
          expect(await repository!.loadConfigSet('StationA', 'hmi-imported'),
              isTrue);
          await File('${evidence.path}/hmi-set.jsonl').writeAsString(document);
        });
        app!.select('StationA');
        await tester.pump(const Duration(milliseconds: 500));
        await tester.tap(find.descendant(
            of: find.byType(TabBar), matching: find.text('Configuration')));
        await tester.pump(const Duration(milliseconds: 500));
        final setsButton = find.byTooltip('Parameter sets').first;
        await tester.ensureVisible(setsButton);
        await tester.pump(const Duration(milliseconds: 500));
        await tester.tap(setsButton);
        await tester.pump(const Duration(milliseconds: 500));
        await tester.runAsync(() async {
          await until(() => find.text('hmi-station').evaluate().isNotEmpty);
          final image = await (boundary.currentContext!.findRenderObject()
                  as RenderRepaintBoundary)
              .toImage();
          final png = await image.toByteData(format: ui.ImageByteFormat.png);
          await File('${evidence.path}/hmi-sets.png')
              .writeAsBytes(png!.buffer.asUint8List());
          image.dispose();
        });
        expect(find.text('hmi-imported'), findsWidgets);
        await tester.tap(find.text('Close'));
        await tester.pump(const Duration(milliseconds: 500));
        await tester.runAsync(() async {
          expect(await repository!.deleteConfigSet('StationA', 'hmi-station'),
              isTrue);
          expect(await repository!.deleteConfigSet('StationA', 'hmi-imported'),
              isTrue);
        });
        app!.select(target);
      }
      await tester.runAsync(() async {
        final image = await (boundary.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final png = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('${evidence.path}/hmi-manual.png')
            .writeAsBytes(png!.buffer.asUint8List());
        image.dispose();
        await File('${evidence.path}/hmi-forest.json')
            .writeAsString(jsonEncode({
          'roots': forest.map((n) => n.path).toList(),
          'modules': [
            for (final n in walk(forest))
              {
                'path': n.path,
                'type': n.type.name,
                'mode': n.modeActive?.name,
                'commands': [
                  for (final c in n.commands)
                    {'value': c.value, 'label': c.label, 'style': c.style.name}
                ]
              }
          ],
          'renderedButtonCommand': {
            'target': target,
            'value': 6,
            'before': before,
            'after': before! + 1
          },
          'authenticatedSession': authenticated,
          'stateAlarmProjection': stateAlarm,
          'configProjection': configLive,
          'configSets': setsLive,
        }));
        if (authenticated) {
          await repository!.logout('StationA');
          await repository!.logout('StationB');
        }
      });
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.runAsync(() async {
        app?.dispose();
        await subscription?.cancel();
        if (app == null) repository?.dispose();
        await observer?.close();
      });
    }
  },
      skip: Platform.environment['FRAKTAL_TIA_MANIFEST_LIVE'] != '1',
      timeout: const Timeout(Duration(minutes: 8)));
}
