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
    Future<void> until(bool Function() predicate) async {
      final timer = Stopwatch()..start();
      while (!predicate() && timer.elapsed < const Duration(minutes: 3)) {
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
        final textFont = await File(r'C:\Windows\Fonts\segoeui.ttf').readAsBytes();
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
        expect(node('StationA').supportedModes, contains(UnitMode.changeover));
        expect(node('StationA.Satellite.Inner').supportedModes,
            isNot(contains(UnitMode.changeover)));
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
        // This prototype has no login provider and its PLC MANUAL gate is NONE.
        // Set the matching display preference only in the test's memory store.
        await app!.content.setRequiredLevel(
            target, ModuleSection.operations, AccessLevel.none);
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
        await repository!.setMode('StationB', UnitMode.auto);
        await until(() => node('StationB').modeActive == UnitMode.auto);
        expect(node('StationA').modeActive, UnitMode.manual);
        await repository!.setMode('StationB', UnitMode.manual);
        await until(() => node('StationB').modeActive == UnitMode.manual);
      });
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull);
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
        }));
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
