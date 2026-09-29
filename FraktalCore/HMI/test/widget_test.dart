// Smoke test: the app boots against the shipped SimRepository (the O6 pattern —
// full UI exercised with zero infrastructure) and renders the shell.
import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/tree_menu.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

void main() {
  testWidgets('App boots against SimRepository and renders', (tester) async {
    final app = AppState(SimRepository());
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester
        .pump(const Duration(seconds: 2)); // let the sim publish a frame
    expect(find.byType(FraktalHmiApp), findsOneWidget);
    app.dispose();
  });

  // Every size preset: the default (compact) one alone never showed that a
  // fixed 64 px rail overflows the medium and large presets' touch targets.
  for (final scale in ControlScale.values) {
    testWidgets(
        'navigation tree animates both widths without layout errors '
        '(${scale.name})', (tester) async {
      tester.view.physicalSize = const Size(1400, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final app = AppState(SimRepository());
      app.controlScale = scale;
      await tester.pumpWidget(FraktalHmiApp(app: app));
      await tester.pump(const Duration(seconds: 2));
      expect(find.byType(TreeMenu), findsOneWidget);

      Future<void> toggleAndCheck() async {
        await tester.tap(find.byKey(const Key('navigation-tree-toggle')));
        for (var frame = 0; frame < 8; frame++) {
          await tester.pump(const Duration(milliseconds: 30));
          expect(tester.takeException(), isNull);
        }
      }

      final collapsed =
          math.max(64.0, UiMetrics.of(scale).touchTarget + 16);
      await toggleAndCheck();
      expect(
        tester
            .getSize(find.byKey(const Key('navigation-tree-animated-width')))
            .width,
        collapsed,
      );
      await toggleAndCheck();
      expect(
        tester
            .getSize(find.byKey(const Key('navigation-tree-animated-width')))
            .width,
        300,
      );
      app.dispose();
    });
  }

  testWidgets('tab selection is atomic and does not rebuild the TabBarView',
      (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final app = AppState(SimRepository());
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));
    app.select('StationA.Separator1');
    await tester.pump();

    final before = tester.widget<TabBarView>(find.byType(TabBarView));
    await tester.tap(find.text('Description'));
    await tester.pump();
    final afterStart = tester.widget<TabBarView>(find.byType(TabBarView));
    expect(identical(before, afterStart), isTrue);
    final controller = DefaultTabController.of(
      tester.element(find.byType(TabBar)),
    );
    expect(controller.animationDuration, Duration.zero);
    // Atomic: the animation already stands on the selected tab, wherever the
    // Description tab sits in the row.
    expect(controller.index, greaterThan(0));
    expect(controller.animation!.value, controller.index.toDouble());
    await tester.pump();
    expect(find.text('Information'), findsOneWidget);
    expect(tester.takeException(), isNull);
    app.dispose();
  });
}
