// The reset confirmation is a transient message: it must disappear on its own.
// The authoritative state is the reset button's armed/idle rendering, which is
// always on screen, so a banner that never clears is just noise covering content.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/main.dart';
import 'package:fraktal_hmi/state/app_state.dart';

void main() {
  testWidgets('the reset confirmation auto-dismisses', (tester) async {
    tester.view.physicalSize = const Size(1400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final app = AppState(SimRepository());
    await tester.pumpWidget(FraktalHmiApp(app: app));
    await tester.pump(const Duration(seconds: 2));

    await tester.tap(find.byKey(const Key('global-reset')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(SnackBar), findsOneWidget,
        reason: 'the outcome is reported');

    // The trap this guards: Flutter never auto-dismisses a SnackBar carrying a
    // SnackBarAction — it waits for the user — so `duration` is silently ignored
    // and the banner sits over the machine view forever. The "Why?" affordance
    // must therefore live inside `content`, not as an action.
    expect(tester.widget<SnackBar>(find.byType(SnackBar)).action, isNull,
        reason: 'an action would defeat the timeout');

    // Well past the 10 s window.
    await tester.pump(const Duration(seconds: 11));
    await tester.pumpAndSettle();
    expect(find.byType(SnackBar), findsNothing,
        reason: 'it must clear itself, not sit over the machine view');

    app.dispose();
  });
}
