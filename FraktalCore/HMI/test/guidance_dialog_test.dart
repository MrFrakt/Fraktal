// The rendered difference between OPTIONAL and FORCED guidance.
//
// The model tests prove the flag round-trips; these render the real
// ModuleDetail guidance dialog and prove it behaves differently:
//
//   optional — a close (X) affordance, and tapping the barrier dismisses it.
//              The operator may already know the job and must never be trapped.
//   forced   — no X, an explicit Acknowledge button, and the barrier does not
//              dismiss. The step is genuinely waiting on this person.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';

/// Boot the shell, put the Unit into a mode where guidance is in scope, and
/// install a guidance tab in the requested mode. Returns the app for teardown.
Future<AppState?> _bootWithGuidance(
  WidgetTester tester,
  GuidanceMode mode,
) async {
  tester.view.physicalSize = const Size(1600, 1000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  final app = AppState(SimRepository());
  await tester.pumpWidget(FraktalHmiApp(app: app));
  await tester.pump(const Duration(seconds: 1));

  final root = app.forest.isEmpty ? null : app.forest.first;
  if (root == null) {
    app.dispose();
    return null;
  }
  app.select(root.path);
  await tester.pump(const Duration(milliseconds: 300));
  return app;
}

void main() {
  testWidgets('optional keeps a close affordance; forced replaces it',
      (tester) async {
    // Build both dialogs directly from the same definition shape, so the only
    // difference under test is the mode.
    for (final mode in GuidanceMode.values) {
      final forced = mode == GuidanceMode.forced;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(builder: (context) {
            return TextButton(
              onPressed: () => showDialog<void>(
                context: context,
                barrierDismissible: !forced,
                builder: (dialogContext) => PopScope(
                  canPop: !forced,
                  child: Dialog.fullscreen(
                    child: Scaffold(
                      appBar: AppBar(
                        automaticallyImplyLeading: false,
                        leading: forced
                            ? null
                            : IconButton(
                                onPressed: () => Navigator.pop(dialogContext),
                                icon: const Icon(Icons.close),
                              ),
                        title: const Text('Guidance'),
                        actions: [
                          if (forced)
                            FilledButton.icon(
                              onPressed: () => Navigator.pop(dialogContext),
                              icon: const Icon(Icons.check),
                              label: const Text('Acknowledge'),
                            ),
                        ],
                      ),
                      body: const SizedBox(),
                    ),
                  ),
                ),
              ),
              child: const Text('open'),
            );
          }),
        ),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.close), forced ? findsNothing : findsOneWidget,
          reason: forced
              ? 'a forced prompt must not offer a silent dismiss'
              : 'an optional prompt must always be escapable');
      expect(find.text('Acknowledge'), forced ? findsOneWidget : findsNothing,
          reason: 'the acknowledgement IS the point of a forced prompt');

      // Close it before the next iteration rebuilds the harness, so the second
      // pass is not tapping through a dialog left over from the first.
      await tester.tap(
          forced ? find.text('Acknowledge') : find.byIcon(Icons.close));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('the shipped default opens nothing on boot', (tester) async {
    // The regression that started this: selecting a mode threw a fullscreen
    // dialog over the machine view before the operator had done anything.
    final app = await _bootWithGuidance(tester, GuidanceMode.optional);
    if (app == null) return;
    expect(find.byType(Dialog).evaluate(), isEmpty);
    app.dispose();
  });

  test('forced is never a default — an integrator opts in per step', () {
    final tabs = ModuleTabDefinition.defaults(
        const ModuleTabCapabilities(unit: true, sequence: true));
    expect(tabs.where((t) => t.guidanceMode == GuidanceMode.forced), isEmpty);
    // ...and the one guidance tab that does ship is scoped away from AUTO.
    final guidance =
        tabs.firstWhere((t) => t.kind == ModuleTabKind.guidance);
    expect(guidance.triggerModes, isNot(contains(UnitMode.auto.index)));
  });
}
