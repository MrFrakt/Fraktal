// Every scrollable in the HMI must be draggable by finger on Windows/Linux/Web,
// the way it already is on mobile. Flutter's desktop default only lets a *touch*
// device drag — a panel with no mouse or keyboard could otherwise never reach the
// bottom of a list. This regressed once: the connection wizard runs in its OWN
// MaterialApp and was missing the behaviour, so language selection could not be
// scrolled on a touch panel.
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/connection_settings_store.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';
import 'package:fraktal_hmi/ui/connection_bootstrap.dart';

ConnectionBootstrap _bootstrap(MemoryConnectionSettingsStore store) {
  final localization =
      LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
  return ConnectionBootstrap(
    store: store,
    repositoryFactory: (_) => SimRepository(),
    localization: localization,
    content: ModuleContentController(localization: localization),
  );
}

void main() {
  test('the shared behaviour drags from every pointer kind', () {
    // Mouse is the one that matters on a desktop build; touch alone is Flutter's
    // default and is what left the wizard unusable.
    expect(kTouchScroll.dragDevices, containsAll(PointerDeviceKind.values));
  });

  testWidgets('every MaterialApp in the app uses it', (tester) async {
    // The wizard app (pre-connection) — the surface that regressed.
    await tester.pumpWidget(_bootstrap(MemoryConnectionSettingsStore(
      const ConnectionSettings(
        transport: ConnectionTransport.simulation,
        endpoint: 'simulation://local',
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
      ),
    )));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    final apps = tester.widgetList<MaterialApp>(find.byType(MaterialApp));
    expect(apps, isNotEmpty);
    for (final app in apps) {
      expect(app.scrollBehavior, isA<TouchScrollBehavior>(),
          reason: 'a MaterialApp without kTouchScroll is touch-unscrollable');
    }
  });

  testWidgets('a wizard list actually scrolls under a finger drag',
      (tester) async {
    tester.view.physicalSize = const Size(800, 600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // Language selection is the first wizard step and lists every language, so
    // on a short panel the lower entries sit below the fold.
    await tester.pumpWidget(_bootstrap(MemoryConnectionSettingsStore()));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    final scrollable = find.byType(Scrollable).first;
    double offset() =>
        tester.state<ScrollableState>(scrollable).position.pixels;
    final before = offset();

    // A finger drag — precisely what desktop Flutter ignores by default.
    await tester.drag(scrollable, const Offset(0, -200),
        kind: PointerDeviceKind.touch);
    await tester.pumpAndSettle();

    expect(offset(), greaterThan(before),
        reason: 'the list must move when dragged by finger');
  });
}
