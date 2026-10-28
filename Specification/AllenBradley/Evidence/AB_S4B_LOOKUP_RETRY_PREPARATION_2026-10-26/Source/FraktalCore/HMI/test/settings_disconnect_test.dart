import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/connection_settings_store.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';
import 'package:fraktal_hmi/ui/connection_bootstrap.dart';
import 'package:fraktal_hmi/ui/shell.dart';

void main() {
  for (final scheme in ['opc.tcp', 'ads', 'cip', 'wss']) {
    testWidgets('Settings shows and changes the connected $scheme endpoint',
        (tester) async {
      final first = scheme == 'ads'
          ? 'ads://192.168.0.49.1.1:851'
          : '$scheme://192.168.0.49:4840';
      final second = scheme == 'ads'
          ? 'ads://192.168.0.61.1.1:852'
          : '$scheme://192.168.0.61:4840';
      final store = MemoryConnectionSettingsStore(ConnectionSettings(
        endpoint: first,
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true,
        appearanceSetupComplete: true,
        floatingKeyboard: false,
      ));
      final localization = LocalizationController(
          enabledLanguages: {'en'}, activeLanguage: 'en');
      final repositories = <_ObservedRepository>[];
      final endpoints = <String>[];
      await tester.pumpWidget(ConnectionBootstrap(
        store: store,
        localization: localization,
        content: ModuleContentController(localization: localization),
        repositoryFactory: (settings) {
          endpoints.add(settings.endpoint);
          final repository = _ObservedRepository();
          repositories.add(repository);
          return repository;
        },
      ));
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));

      await tester.tap(find.byKey(const Key('settings')));
      await tester.pumpAndSettle();
      // The connected target is visible even before login. Identical root names
      // do not identify which controller this repository actually connected to.
      final endpoint = find.byKey(const Key('connected-endpoint'));
      await tester.ensureVisible(endpoint);
      expect(find.descendant(of: endpoint, matching: find.text(first)),
          findsOneWidget);
      expect(find.widgetWithText(OutlinedButton, 'Disconnect'), findsNothing);
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Login'));
      await tester.pump();
      await tester.enterText(find.byKey(const Key('login-user')), 'admin1');
      await tester.enterText(find.byKey(const Key('login-pin')), '2468');
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pump();
      await tester.pump();

      await tester.tap(find.byKey(const Key('settings')));
      await tester.pumpAndSettle();
      final disconnect = find.widgetWithText(OutlinedButton, 'Disconnect');
      await tester.ensureVisible(disconnect);
      await tester.pumpAndSettle();
      await tester.tap(disconnect);
      await tester.pump();
      await tester.pump();
      await tester.pumpAndSettle();

      expect(repositories.single.disposeCalls, 1);
      expect(find.byType(Shell), findsNothing);
      expect(find.text('Connect Fraktal HMI'), findsOneWidget);
      expect(find.text(first), findsOneWidget);
      // A deliberate disconnect stays disconnected until Connect is pressed.
      await tester.pump(const Duration(seconds: 31));
      expect(endpoints, [first]);

      await tester.enterText(find.byType(TextFormField), second);
      await tester.ensureVisible(find.byKey(const Key('save-connect')));
      await tester.tap(find.byKey(const Key('save-connect')));
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      expect(find.byType(Shell), findsOneWidget);
      expect(endpoints, [first, second]);
      expect(repositories.first.disposeCalls, 1);
      expect(repositories.last.disposeCalls, 0);
      expect(store.value?.endpoint, second);
      expect(store.value?.floatingKeyboard, isFalse);
      expect(store.value?.selectedUnitPaths, ['StationA']);
      await tester.tap(find.byKey(const Key('settings')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('connected-endpoint')));
      expect(find.text(second), findsOneWidget);
      expect(find.text(first), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
      expect(repositories.last.disposeCalls, 1);
    });
  }
}

class _ObservedRepository extends SimRepository {
  int disposeCalls = 0;

  @override
  void dispose() {
    disposeCalls++;
    super.dispose();
  }
}
