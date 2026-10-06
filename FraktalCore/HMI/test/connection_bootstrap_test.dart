import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/connection_settings_store.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/ui/connection_bootstrap.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';
import 'package:fraktal_hmi/ui/shell.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';

ConnectionBootstrap _bootstrap({
  required MemoryConnectionSettingsStore store,
  required PlcRepository Function(ConnectionSettings) repositoryFactory,
  Duration editDelay = const Duration(seconds: 30),
  Duration startupRetryBase = const Duration(milliseconds: 500),
  Duration startupRetryMax = const Duration(seconds: 5),
}) {
  final localization =
      LocalizationController(enabledLanguages: {'en'}, activeLanguage: 'en');
  return ConnectionBootstrap(
    store: store,
    repositoryFactory: repositoryFactory,
    editDelay: editDelay,
    startupRetryBase: startupRetryBase,
    startupRetryMax: startupRetryMax,
    localization: localization,
    content: ModuleContentController(localization: localization),
  );
}

void main() {
  testWidgets('filter interaction and sub-frame data loss retain the unit view',
      (tester) async {
    tester.view.physicalSize = const Size(1800, 2000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repository = _ControlledForestRepository();
    await tester.pumpWidget(_bootstrap(
      store: MemoryConnectionSettingsStore(const ConnectionSettings(
          everConnected: true,
          selectedUnitPaths: ['StationA'],
          unitSelectionComplete: true,
          enabledLanguageCodes: ['en'],
          activeLanguageCode: 'en',
          languageSelectionComplete: true)),
      repositoryFactory: (_) => repository,
    ));
    await tester.pump();
    await tester.pump();
    final app = tester.widget<Shell>(find.byType(Shell)).app;
    app.select('StationA');
    app.scopeTo('StationA');
    await tester.pump();
    await tester.pump();
    expect(app.selected?.path, 'StationA');
    await tester.tap(find.descendant(
        of: find.byType(TabBar), matching: find.text('Statistics')));
    await tester.pump();
    final chips = find.byType(FilterChip);
    expect(chips, findsNWidgets(6));
    for (var i = 0; i < 6; i++) {
      await tester.ensureVisible(chips.at(i));
      await tester.tap(chips.at(i));
      await tester.pump();
      expect(tester.widget<FilterChip>(chips.at(i)).selected, isFalse);
    }
    final controller =
        DefaultTabController.of(tester.element(find.byType(TabBar)));
    expect(controller.index, greaterThan(0));

    // A missed Good deadline can withdraw and recover between browser frames.
    // No connection page is painted, but the empty forest still reaches state.
    repository.emit(LinkState.stale);
    repository.emitForest(const []);
    await tester.idle();
    expect(app.forest, isEmpty);
    expect(app.selected, isNull);
    expect(app.session.level, AccessLevel.none);
    expect(repository.detailActive, isFalse);
    repository.emitForest(_navigationRoots);
    repository.emit(LinkState.live);
    await tester.idle();
    await tester.pump();

    expect(app.showOverview, isFalse);
    expect(app.selectedPath, 'StationA');
    expect(app.scopedRoot, 'StationA');
    expect(DefaultTabController.of(tester.element(find.byType(TabBar))),
        same(controller));
    for (var i = 0; i < 6; i++) {
      expect(tester.widget<FilterChip>(chips.at(i)).selected, isFalse);
    }
    expect(find.byKey(const Key('connection-blocking-title')), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  for (final tab in ['Statistics', 'Events']) {
  testWidgets('$tab choices survive painted STALE and DOWN connection gates',
      (tester) async {
    tester.view.physicalSize = const Size(1800, 2000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repository = _ControlledForestRepository();
    await tester.pumpWidget(_bootstrap(
      store: MemoryConnectionSettingsStore(const ConnectionSettings(
          everConnected: true,
          selectedUnitPaths: ['StationA'],
          unitSelectionComplete: true,
          enabledLanguageCodes: ['en'],
          activeLanguageCode: 'en',
          languageSelectionComplete: true)),
      repositoryFactory: (_) => repository,
    ));
    await tester.pump();
    await tester.pump();
    final app = tester.widget<Shell>(find.byType(Shell)).app;
    app.select('StationA');
    await tester.pump();
    await tester.pump();
    await tester.tap(find.descendant(
        of: find.byType(TabBar), matching: find.text(tab)));
    await tester.pump();
    final controller = DefaultTabController.of(tester.element(find.byType(TabBar)));
    final chips = find.byType(FilterChip);
    expect(chips, findsNWidgets(tab == 'Statistics' ? 6 : 3));
    for (var i = 0; i < (tab == 'Statistics' ? 6 : 3); i++) {
      await tester.ensureVisible(chips.at(i));
      await tester.tap(chips.at(i));
      await tester.pump();
    }
    final selectedIndex = controller.index;
    for (final loss in [LinkState.stale, LinkState.down]) {
    repository.emit(loss);
    repository.emitForest(const []);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 250));
    expect(find.byType(Shell), findsNothing);
    expect(find.byKey(const Key('connection-blocking-title')), findsOneWidget);
    expect(app.selected, isNull);
    expect(app.session.level, AccessLevel.none);
    expect(repository.detailActive, isFalse);
    repository.emitForest(_navigationRoots);
    repository.emit(LinkState.live);
    await tester.pump();
    expect(find.byType(Shell), findsOneWidget);
    expect(app.showOverview, isFalse);
    expect(app.selectedPath, 'StationA');
    await tester.pump();
    final restored = DefaultTabController.of(tester.element(find.byType(TabBar)));
    expect(restored.index, selectedIndex);
    expect(restored, isNot(same(controller)));
    for (final chip in tester.widgetList<FilterChip>(chips)) {
      expect(chip.selected, isFalse);
    }
    }

    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  }

  test('a populated replacement forest still removes an absent selection',
      () async {
    final repository = _ControlledForestRepository();
    final app = AppState(repository);
    addTearDown(app.dispose);
    await Future<void>.delayed(Duration.zero);
    app.select('StationA');
    app.scopeTo('StationA');
    repository.emitForest(const []);
    await Future<void>.delayed(Duration.zero);
    expect(app.forest, isEmpty);
    expect(app.selectedPath, 'StationA');
    expect(app.session.level, AccessLevel.none);
    repository.emitForest(const [
      ModuleNode(path: 'StationB', name: 'StationB', type: ModuleType.unit),
    ]);
    await Future<void>.delayed(Duration.zero);
    expect(app.selectedPath, 'StationB');
    expect(app.scopedRoot, isNull);
    expect(app.showOverview, isTrue);
  });

  testWidgets('first use opens wizard and records first proven connection',
      (tester) async {
    final store = MemoryConnectionSettingsStore();
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => SimRepository(),
      editDelay: const Duration(seconds: 30),
    ));
    await tester.pump();

    expect(find.byKey(const Key('save-language-selection')), findsOneWidget);
    await tester
        .ensureVisible(find.byKey(const Key('save-language-selection')));
    await tester.tap(find.byKey(const Key('save-language-selection')));
    await tester.pump();

    // Appearance (theme + control size for the physical screen)...
    expect(find.byKey(const Key('save-appearance')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('save-appearance')));
    await tester.tap(find.byKey(const Key('save-appearance')));
    await tester.pump();

    // ...then access: panel-local floors that only ever tighten PLC policy.
    expect(find.byKey(const Key('save-access')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('save-access')));
    await tester.tap(find.byKey(const Key('save-access')));
    await tester.pump();

    expect(find.text('Connect Fraktal HMI'), findsOneWidget);
    await tester.tap(find.byKey(const Key('save-connect')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.byKey(const Key('unit-selection-title')), findsOneWidget);
    await tester.tap(find.byKey(const Key('unit-select-StationA')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('save-unit-selection')));
    await tester.pump();
    await tester.pump();

    expect(find.byType(FraktalHmiApp), findsOneWidget);
    expect(store.value?.everConnected, isTrue);
    expect(store.value?.selectedUnitPaths, ['StationA']);
    expect(store.value?.unitSelectionComplete, isTrue);
    expect(store.value?.languageSelectionComplete, isTrue);
  });

  testWidgets(
      'saved connection blocks interaction and reveals edit after timeout',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => ControlledLinkRepository(LinkState.connecting),
      editDelay: const Duration(seconds: 30),
    ));
    await tester.pump();

    expect(find.byKey(const Key('connection-blocking-title')), findsOneWidget);
    expect(find.byType(Shell), findsNothing);
    expect(find.byKey(const Key('edit-connection-settings')), findsNothing);

    await tester.pump(const Duration(seconds: 29));
    expect(find.byKey(const Key('edit-connection-settings')), findsNothing);
    await tester.pump(const Duration(seconds: 1));
    expect(find.byKey(const Key('edit-connection-settings')), findsOneWidget);
  });

  testWidgets('startup failure exposes the exact diagnostic and stays locked',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) =>
          throw StateError('[tcp-preflight] 192.168.132.130:4840 unreachable'),
      editDelay: const Duration(seconds: 30),
    ));
    await tester.pump();

    expect(find.byType(Shell), findsNothing);
    expect(find.byIcon(Icons.link_off), findsOneWidget);
    expect(find.byKey(const Key('connection-state-detail')), findsOneWidget);
    expect(
        find.byKey(const Key('connection-diagnostic-detail')), findsOneWidget);
    expect(find.textContaining('192.168.132.130:4840'), findsOneWidget);
    expect(find.byKey(const Key('edit-connection-settings')), findsNothing);

    await tester.pump(const Duration(seconds: 30));
    expect(find.byKey(const Key('edit-connection-settings')), findsOneWidget);
  });

  testWidgets('startup failure retries automatically and reaches live',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        transport: ConnectionTransport.simulation,
        endpoint: 'simulation://local',
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    var attempts = 0;
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) {
        attempts++;
        if (attempts < 3) throw StateError('gateway unavailable');
        return SimRepository();
      },
      startupRetryBase: const Duration(milliseconds: 10),
      startupRetryMax: const Duration(milliseconds: 20),
    ));
    await tester.pump();
    expect(find.byType(Shell), findsNothing);

    await tester.pump(const Duration(milliseconds: 10));
    await tester.pump(const Duration(milliseconds: 20));
    await tester.pump(const Duration(seconds: 1));

    expect(attempts, 3);
    expect(find.byType(Shell), findsOneWidget);
  });

  testWidgets('lost live link immediately replaces the interactive shell',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    late ControlledLinkRepository repository;
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) =>
          repository = ControlledLinkRepository(LinkState.live),
      editDelay: const Duration(seconds: 30),
    ));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    expect(find.byType(Shell), findsOneWidget);

    repository.emit(LinkState.down);
    await tester.pump();
    expect(find.byType(Shell), findsNothing);
    expect(find.byKey(const Key('connection-blocking-title')), findsOneWidget);
    expect(find.byKey(const Key('edit-connection-settings')), findsNothing);

    await tester.pump(const Duration(seconds: 30));
    expect(find.byKey(const Key('edit-connection-settings')), findsOneWidget);
  });

  testWidgets('admin can reopen and cancel the Unit assignment editor',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        transport: ConnectionTransport.simulation,
        endpoint: 'simulation://local',
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => SimRepository(),
    ));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.byTooltip('Login'));
    await tester.pump();
    await tester.enterText(find.byType(TextField).at(0), 'admin1');
    await tester.enterText(find.byType(TextField).at(1), '2468');
    await tester.tap(find.widgetWithText(FilledButton, 'Login'));
    await tester.pump();
    await tester.pump();

    // The editors moved out of the app bar into the fullscreen Settings dialog,
    // so an admin reaches them through Settings rather than a top-level icon.
    await tester.tap(find.byKey(const Key('settings')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('edit-unit-assignment')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('edit-unit-assignment')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('edit-unit-assignment')));
    await tester.pump(); // let the dialog pop
    await tester.pump(); // then the deferred phase change
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('unit-selection-title')), findsOneWidget);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
    await tester.pump();
    expect(find.byType(Shell), findsOneWidget);
  });

  testWidgets('admin can reopen the connection wizard and change the address',
      (tester) async {
    // The real-world situation: already connected (skips the wizard) to an
    // opc.tcp endpoint, so there is no automatic way back to the wizard.
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        endpoint: 'opc.tcp://127.0.0.1:4840',
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => SimRepository(),
    ));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    expect(find.byType(Shell), findsOneWidget);

    // Before an admin logs in, the connection editor is not offered — the
    // editors live in the fullscreen Settings dialog, so check inside it.
    await tester.tap(find.byKey(const Key('settings')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('edit-connection')), findsNothing);
    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Login'));
    await tester.pump();
    await tester.enterText(find.byKey(const Key('login-user')), 'admin1');
    await tester.enterText(find.byKey(const Key('login-pin')), '2468');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    await tester.pump();

    // Admin sees the editor, and it reopens the wizard prefilled with the
    // current endpoint.
    await tester.tap(find.byKey(const Key('settings')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('edit-connection')), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('edit-connection')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('edit-connection')));
    await tester.pump(); // let the dialog pop
    await tester.pump(); // then the deferred phase change
    await tester.pumpAndSettle();
    expect(find.text('Connect Fraktal HMI'), findsOneWidget);
    expect(find.text('opc.tcp://127.0.0.1:4840'), findsOneWidget);

    // Change the address and reconnect.
    await tester.enterText(
        find.byType(TextFormField), 'ads://192.168.1.6.1.1:854');
    await tester.pump();
    await tester.tap(find.byKey(const Key('save-connect')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.byType(Shell), findsOneWidget);
    expect(store.value?.endpoint, 'ads://192.168.1.6.1.1:854');
  });

  testWidgets('pending login stays pending and closes cleanly on late success',
      (tester) async {
    final repo = _DelayedLoginRepository();
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        transport: ConnectionTransport.simulation,
        endpoint: 'simulation://local',
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester
        .pumpWidget(_bootstrap(store: store, repositoryFactory: (_) => repo));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.tap(find.byTooltip('Login'));
    await tester.pump();
    await tester.enterText(find.byKey(const Key('login-user')), 'admin1');
    await tester.enterText(find.byKey(const Key('login-pin')), '2468');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump(const Duration(seconds: 12));
    expect(find.byKey(const Key('login-error')), findsNothing);
    expect(find.byType(AlertDialog), findsOneWidget);
    repo.release.complete();
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.byKey(const Key('login-error')), findsNothing);
  });

  testWidgets('failed login stays open and explains the failure inline',
      (tester) async {
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        transport: ConnectionTransport.simulation,
        endpoint: 'simulation://local',
        everConnected: true,
        selectedUnitPaths: ['StationA'],
        unitSelectionComplete: true,
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => SimRepository(),
    ));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.byTooltip('Login'));
    await tester.pump();
    await tester.enterText(find.byKey(const Key('login-user')), 'admin1');
    await tester.enterText(find.byKey(const Key('login-pin')), 'wrong');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    await tester.pump();

    expect(find.byKey(const Key('login-error')), findsOneWidget);
    expect(find.textContaining('Check the user name and PIN'), findsOneWidget);
    expect(find.byType(AlertDialog), findsOneWidget);
  });

  testWidgets('wizard: ADS endpoint is editable, guided, and validated',
      (tester) async {
    // Language done + not yet connected -> opens straight to the wizard, seeded
    // with the loopback ADS default.
    final store = MemoryConnectionSettingsStore(const ConnectionSettings(
        endpoint: 'ads://127.0.0.1.1.1:851',
        enabledLanguageCodes: ['en'],
        activeLanguageCode: 'en',
        languageSelectionComplete: true));
    await tester.pumpWidget(_bootstrap(
      store: store,
      repositoryFactory: (_) => SimRepository(),
    ));
    await tester.pump();

    expect(find.text('Connect Fraktal HMI'), findsOneWidget);
    // An ads:// endpoint shows the AmsNetId/port format guidance.
    expect(find.textContaining('AmsNetId'), findsOneWidget);

    // A malformed AmsNetId (four octets) is rejected inline and blocks connect.
    await tester.enterText(find.byType(TextFormField), 'ads://127.0.0.1:851');
    await tester.pump();
    await tester.tap(find.byKey(const Key('save-connect')));
    await tester.pump();
    expect(find.textContaining('six parts'), findsOneWidget);
    expect(find.text('Connect Fraktal HMI'), findsOneWidget);
    expect(store.value?.everConnected, isNot(true));

    // The operator corrects it to their machine's AmsNetId + runtime port.
    await tester.enterText(
        find.byType(TextFormField), 'ads://192.168.1.6.1.1:854');
    await tester.pump();
    await tester.tap(find.byKey(const Key('save-connect')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(store.value?.endpoint, 'ads://192.168.1.6.1.1:854');
  });
}

class _DelayedLoginRepository extends SimRepository {
  final release = Completer<void>();

  @override
  Future<bool> login(String rootPath, String user, String secret) async {
    await release.future;
    return super.login(rootPath, user, secret);
  }
}

class ControlledLinkRepository extends SimRepository {
  final LinkState initial;
  final _controlledLink = StreamController<LinkState>.broadcast(sync: true);

  ControlledLinkRepository(this.initial);

  @override
  Stream<LinkState> linkState() {
    scheduleMicrotask(() => _controlledLink.add(initial));
    return _controlledLink.stream;
  }

  void emit(LinkState state) => _controlledLink.add(state);

  @override
  void dispose() {
    _controlledLink.close();
    super.dispose();
  }
}

const _navigationRoots = [
  ModuleNode(
    path: 'StationA',
    name: 'StationA',
    type: ModuleType.unit,
    access: AccessSession(level: AccessLevel.admin),
    cycle: CycleProfile(
        cycleNo: 1,
        total: Duration(seconds: 3),
        workTime: Duration(seconds: 1),
        waitTime: Duration(seconds: 2),
        steps: [
          StepTiming(10, 'Work', TimeClass.work, Duration(seconds: 1)),
          StepTiming(20, 'Wait', TimeClass.waitOperator, Duration(seconds: 2)),
        ]),
    cycleHistory: [
      CycleSummary(cycleNo: 1, total: Duration(seconds: 3), byClass: [
        Duration(seconds: 1),
        Duration.zero,
        Duration.zero,
        Duration(seconds: 2)
      ]),
      CycleSummary(cycleNo: 2, total: Duration(seconds: 4), byClass: [
        Duration(seconds: 2),
        Duration.zero,
        Duration.zero,
        Duration(seconds: 2)
      ]),
    ],
    stepStats: [
      StepStat(10, 'Work', TimeClass.work, Duration(seconds: 1),
          Duration(seconds: 2)),
      StepStat(20, 'Wait', TimeClass.waitOperator, Duration(seconds: 2),
          Duration(seconds: 3)),
    ],
  ),
];

class _ControlledForestRepository extends ControlledLinkRepository {
  final _forest = StreamController<List<ModuleNode>>.broadcast();
  bool detailActive = false;
  _ControlledForestRepository() : super(LinkState.live);
  @override
  Stream<List<ModuleNode>> forest() {
    scheduleMicrotask(() => emitForest(_navigationRoots));
    return _forest.stream;
  }

  void emitForest(List<ModuleNode> roots) => _forest.add(roots);
  @override
  void setModuleDetailActive(String rootPath, bool active,
          {Set<String>? containers}) =>
      detailActive = active;
  @override
  void dispose() {
    _forest.close();
    super.dispose();
  }
}
