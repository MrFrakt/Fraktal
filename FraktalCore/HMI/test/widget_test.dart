// Smoke test: the app boots against the shipped SimRepository (the O6 pattern —
// full UI exercised with zero infrastructure) and renders the shell.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/tree_menu.dart';

void main() {
  testWidgets('App boots against SimRepository and renders', (tester) async {
    final app = AppState(SimRepository());
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester
        .pump(const Duration(seconds: 2)); // let the sim publish a frame
    expect(find.byType(FraktalHmiApp), findsOneWidget);
    app.dispose();
  });

  testWidgets('navigation tree animates both widths without layout errors',
      (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final app = AppState(SimRepository());
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

    await toggleAndCheck();
    expect(
      tester
          .getSize(find.byKey(const Key('navigation-tree-animated-width')))
          .width,
      64,
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
    expect(controller.animation!.value, 1);
    await tester.pump();
    expect(find.text('Information'), findsOneWidget);
    expect(tester.takeException(), isNull);
    app.dispose();
  });
}
