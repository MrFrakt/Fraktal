import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/localization/localized_text.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/facet_cards.dart';
import 'package:fraktal_hmi/ui/hmi_icons.dart';
import 'package:fraktal_hmi/ui/overview_and_indicators.dart';
import 'package:fraktal_hmi/ui/theme_chrome.dart';

ModuleNode node(String typeKey, {String name = 'Device'}) => ModuleNode(
    name: name, path: name, type: ModuleType.controlModule, typeKey: typeKey);

class EventRepository extends SimRepository {
  final updates = StreamController<List<ModuleNode>>.broadcast();
  @override
  Stream<List<ModuleNode>> forest() => updates.stream;
  @override
  void dispose() {
    updates.close();
    super.dispose();
  }
}

void main() {
  test('every shipping module type has a distinct device symbol', () {
    final types = <String>{};
    final sources = [
      Directory('../PLC/TwinCAT/Framework/Fraktal_Modules'),
      Directory('../PLC/TwinCAT/Framework/Fraktal_Core/DeviceCMs'),
    ];
    for (final file in sources.expand((dir) => dir.listSync(recursive: true))
        .whereType<File>()) {
      if (!file.path.endsWith('.TcPOU')) continue;
      types.addAll(RegExp(r"TypeKey\s*:=\s*'(std\.moduleType\.[^']+)'")
          .allMatches(file.readAsStringSync())
          .map((match) => match[1]!));
    }
    expect(types.length, greaterThanOrEqualTo(12));
    final symbols = types.map((key) => moduleSymbolFor(node(key))).toList();
    expect(symbols, isNot(contains(ModuleSymbol.device)));
    expect(symbols.toSet().length, types.length);
    expect(moduleSymbolFor(node('custom.type', name: 'Robot Cylinder')),
        ModuleSymbol.device,
        reason: 'instance names cannot invent a type');
    expect(moduleSymbolFor(node('std.moduleType.cylinder', name: 'Tür')),
        moduleSymbolFor(node('std.moduleType.cylinder', name: 'Door')));
  });

  test('drawn device symbols are visible and distinct at navigation size',
      () async {
    final pictures = <String>{};
    for (final symbol in [
      ModuleSymbol.cylinder,
      ModuleSymbol.configurableCylinder,
      ModuleSymbol.separator,
      ModuleSymbol.twoHand
    ]) {
      final recorder = ui.PictureRecorder();
      DeviceSymbolPainter(symbol, Colors.white)
          .paint(Canvas(recorder), const Size(24, 24));
      final picture = recorder.endRecording();
      final image = await picture.toImage(24, 24);
      final pixels = (await image.toByteData())!.buffer.asUint8List();
      expect(pixels.any((value) => value != 0), isTrue);
      expect(pictures.add(pixels.join(',')), isTrue,
          reason: '$symbol must differ');
      image.dispose();
      picture.dispose();
    }
  });

  testWidgets(
      'health distinguishes unavailable, unsynchronized and synchronized time',
      (tester) async {
    for (final (time, label, attention) in [
      (const TimeQualityFacet(), 'TIME QUALITY UNAVAILABLE', true),
      (const TimeQualityFacet(available: true), 'TIME UNSYNCHRONIZED', true),
      (
        const TimeQualityFacet(
            available: true, synchronized: true, source: 'PTP', offsetUs: 12),
        'PTP 12 µs',
        false
      ),
      (
        const TimeQualityFacet(available: false, synchronized: true),
        'TIME QUALITY UNAVAILABLE',
        true
      ),
    ]) {
      await tester.pumpWidget(LocalizationScope(
          controller: LocalizationController(),
          child: MaterialApp(
              theme: themeAt(29),
              home: Scaffold(
                  body: SystemHealthCard(
                      health:
                          SystemHealthFacet(healthy: !attention, time: time),
                      canLampTest: false,
                      onLampTest: () async => false,
                      onExplain: () {})))));
      expect(find.text(label), findsOneWidget);
      expect(find.text(attention ? 'ATTENTION' : 'HEALTHY'), findsOneWidget);
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets(
      'Bosch event bar uses solid semantic fills with white text and keeps drill-down',
      (tester) async {
    final repo = EventRepository();
    final app = AppState(repo);
    final index =
        kThemes.indexWhere((theme) => theme.nameKey == 'std.theme.likeABosch');
    final theme = themeAt(index);
    final chrome = theme.extension<FraktalChromeTheme>()!;
    for (final severity in Severity.values) {
      final event = AlarmEvent(
          severity: severity,
          description: 'Test event',
          sourcePath: 'Station',
          resetClass: ResetClass.autoReset,
          state: AlarmState.active,
          comeAt: DateTime(2026));
      repo.updates.add([
        ModuleNode(
            path: 'Station',
            name: 'Station',
            type: ModuleType.unit,
            activeEvents: [event, event])
      ]);
      await tester.pumpWidget(LocalizationScope(
          controller: app.localization,
          child: MaterialApp(
              theme: theme,
              home: Scaffold(body: GlobalAlarmBanner(app: app)))));
      await tester.pump();
      final banner = find.byType(GlobalAlarmBanner);
      final material =
          find.descendant(of: banner, matching: find.byType(Material)).first;
      final fill = tester.widget<Material>(material).color!;
      expect(fill, chrome.eventFill(severity));
      expect(fill.a, 1);
      expect((1.0 + 0.05) / (fill.computeLuminance() + 0.05),
          greaterThanOrEqualTo(4.5));
      final label = tester.widget<Text>(find.text('Test event  ·  Station'));
      expect(label.style!.color, Colors.white);
      final badge = tester.widget<Text>(find.text('+1'));
      expect(badge.style!.color, fill);
      await tester.tap(find.text('Test event  ·  Station'));
      expect(app.selectedPath, 'Station');
      expect(tester.takeException(), isNull);
    }
    app.dispose();
  });
}
