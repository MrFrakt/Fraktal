// Regression: publishing a module layout froze the Windows HMI.
//
// The publish dialog's comment controller was disposed as soon as showDialog
// returned, while the route was still running its exit transition. With the
// comment field focused (the on-screen keyboard feeding it), the closing tap
// unfocused the field, which rebuilt against the disposed controller; the
// failure cascaded into a corrupted element tree (dirty widget in the wrong
// build scope, duplicate Navigator GlobalKey) and the app stopped responding
// before the layout was saved.
import 'package:flutter/material.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';

Future<void> _settle(WidgetTester tester, [int frames = 10]) async {
  // The simulator publishes on a timer, so the tree never "settles" for
  // pumpAndSettle; pump a bounded number of frames instead.
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  for (final typeComment in [false, true]) {
    testWidgets(
        'publishing a layout completes without a disposed-controller error '
        '(comment typed: $typeComment)', (tester) async {
      tester.view.physicalSize = const Size(1400, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repo = SimRepository();
      final app = AppState(repo);
      await tester.pumpWidget(FraktalHmiApp(app: app));
      await tester.pump(const Duration(seconds: 2));
      expect(await repo.login('StationA', 'admin1', '2468'), isTrue);
      app.select('StationA');
      await tester.pump(const Duration(seconds: 2));

      await tester.tap(find.byTooltip('Edit module tabs'));
      await _settle(tester);
      // Invoked directly: in the test surface the edit bar's scroll view
      // overlaps the button's centre, which is not what this test is about.
      tester
          .widget<IconButton>(find
              .ancestor(
                  of: find.byIcon(Icons.publish),
                  matching: find.byType(IconButton))
              .first)
          .onPressed!();
      await _settle(tester, 5);

      final dialog = find.byType(AlertDialog);
      if (typeComment) {
        await tester.tap(
            find.descendant(of: dialog, matching: find.byType(TextField)));
        await _settle(tester, 3);
        expect(app.keyboard.hasField, isTrue);
        await tester.tap(find.text('Q').first);
        await _settle(tester, 3);
      }
      await tester.tap(
          find.descendant(of: dialog, matching: find.byType(FilledButton)));
      // Through the whole exit transition: the error surfaced mid-animation.
      await _settle(tester);

      expect(tester.takeException(), isNull);
      expect(dialog, findsNothing);
      final revisions = app.content.revisionsFor('StationA');
      expect(revisions, hasLength(1), reason: 'the layout was not published');
      if (typeComment) {
        expect(revisions.single.comment, 'Before: Q');
      }
      expect(app.keyboard.hasField, isFalse);
      app.dispose(); // stops the simulator's timer
    });
  }

  testWidgets('a custom tab draws its background image behind its controls',
      (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = SimRepository();
    final app = AppState(repo);
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));
    const capabilities = ModuleTabCapabilities(unit: true);
    await app.content.publishTabs(
      'StationA',
      [
        ...app.content.tabsFor('StationA', capabilities),
        const ModuleTabDefinition(
          id: 'cell',
          title: 'Cell',
          kind: ModuleTabKind.custom,
          background: ModuleTabBackground(imageBase64: _png, imageName: 'c'),
        ),
      ],
      capabilities,
      author: 'test',
    );
    app.select('StationA');
    await tester.pump(const Duration(seconds: 2));
    await tester.tap(find.text('Cell'));
    await _settle(tester);

    expect(find.byType(Image), findsWidgets,
        reason: 'the custom tab rendered without its background');
    app.dispose(); // stops the simulator's timer
  });
}

// A 1x1 transparent PNG.
const _png =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
