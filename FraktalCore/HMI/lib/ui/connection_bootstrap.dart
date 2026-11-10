library;

import 'dart:async';
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;
import 'package:flutter/material.dart';
import 'theme_surfaces.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import '../content/module_content_controller.dart';
import '../data/connection_settings_store.dart';
import '../data/plc_repository.dart';
import '../data/repository_factory.dart';
import '../data/s7web_credentials.dart';
import '../data/s7web_endpoint.dart';
import '../data/scoped_plc_repository.dart';
import '../domain/connection_settings.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/default_catalogs.dart';
import '../localization/localization_controller.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'app_theme.dart'
    show ControlScale, ControlScaleScope, UiMetrics, kTouchScroll, themeAt;
import 'access_setup.dart';
import 'appearance_setup.dart';
import 'fraktal_hmi_app.dart';
import 'language_settings.dart';

enum _BootstrapPhase {
  loading,
  languageSelection,
  appearanceSetup,
  accessSetup,
  wizard,
  connecting,
  unitSelection,
  live,
}

/// Owns the connection before AppState exists. A non-live repository never
/// reaches the interactive shell, so stale/down data cannot be commanded.
class ConnectionBootstrap extends StatefulWidget {
  final ConnectionSettingsStore store;
  final ConnectionRepositoryFactory repositoryFactory;
  final LocalizationController localization;
  final ModuleContentController content;
  final Duration editDelay;
  final Duration startupRetryBase;
  final Duration startupRetryMax;

  const ConnectionBootstrap({
    super.key,
    required this.store,
    required this.repositoryFactory,
    required this.localization,
    required this.content,
    this.editDelay = const Duration(seconds: 30),
    this.startupRetryBase = const Duration(milliseconds: 500),
    this.startupRetryMax = const Duration(seconds: 5),
  });

  @override
  State<ConnectionBootstrap> createState() => _ConnectionBootstrapState();
}

class _ConnectionBootstrapState extends State<ConnectionBootstrap> {
  _BootstrapPhase _phase = _BootstrapPhase.loading;

  /// Non-null only while the appearance step is open, so the wizard renders in
  /// the theme/size being chosen (and reverts if the engineer backs out).
  int? _previewTheme;
  ControlScale? _previewScale;
  ConnectionSettings? _settings;
  AppState? _app;
  ScopedPlcRepository? _scopedRepository;
  Timer? _editTimer;
  Timer? _startupRetryTimer;
  int _startupRetryAttempt = 0;
  int _connectionGeneration = 0;
  bool _canEdit = false;
  LinkState _lastLink = LinkState.connecting;
  String? _startupError;
  bool _editingUnitSelection = false;

  /// Set when the direct s7web:// link needs the CPU web login: the screen
  /// asks for it instead of retrying a connection that cannot succeed.
  S7WebLoginRequired? _loginRequired;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await Future.wait([
      widget.localization.load(),
      widget.content.load(),
      // Remembered CPU web logins, so the wizard and the login screen know
      // whether to offer "remember" and a saved endpoint can log in itself.
      s7WebCredentials.ready(),
    ]);
    final loadedSettings = await widget.store.load();
    final settings = loadedSettings ??
        ConnectionSettings(endpoint: defaultConnectionEndpoint());
    debugPrint('[Fraktal/Connection] stage=settings-load '
        'result=${loadedSettings == null ? 'missing-or-invalid' : 'loaded'} '
        'transport=${settings.transport.name} '
        'endpoint=${settings.endpoint} '
        'everConnected=${settings.everConnected}');
    if (!mounted) return;
    if (settings.languageSelectionComplete) {
      widget.localization.configure(
        enabled: settings.enabledLanguageCodes,
        active: settings.activeLanguageCode,
      );
    } else {
      setState(() {
        _settings = settings;
        _phase = _BootstrapPhase.languageSelection;
      });
      return;
    }
    if (!settings.everConnected) {
      setState(() {
        _settings = settings;
        _phase = _BootstrapPhase.wizard;
      });
      return;
    }
    await _connect(settings, newlySaved: false);
  }

  Future<void> _connect(ConnectionSettings settings,
      {required bool newlySaved}) async {
    _startupRetryTimer?.cancel();
    _startupRetryAttempt = 0;
    final generation = ++_connectionGeneration;
    _disposeApp();
    _editTimer?.cancel();
    final candidate =
        newlySaved ? settings.copyWith(everConnected: false) : settings;
    widget.localization.configure(
      enabled: candidate.enabledLanguageCodes,
      active: candidate.activeLanguageCode,
    );
    if (newlySaved) await widget.store.save(candidate);
    if (!mounted) return;
    setState(() {
      _settings = candidate;
      _phase = _BootstrapPhase.connecting;
      _canEdit = false;
      _lastLink = LinkState.connecting;
      _startupError = null;
      _loginRequired = null;
    });
    _armEditDelay();
    debugPrint('[Fraktal/Connection] stage=start '
        'transport=${candidate.transport.name} endpoint=${candidate.endpoint} '
        'newlySaved=$newlySaved selectedUnits=${candidate.selectedUnitPaths}');
    await _attemptRepositoryConnection(candidate, generation);
  }

  Future<void> _attemptRepositoryConnection(
    ConnectionSettings candidate,
    int generation,
  ) async {
    PlcRepository? repository;
    try {
      repository = await widget.repositoryFactory(candidate);
      if (!mounted || generation != _connectionGeneration) {
        repository.dispose();
        return;
      }
      debugPrint('[Fraktal/Connection] stage=repository-created '
          'type=${repository.runtimeType}');
      final scoped = ScopedPlcRepository(
        repository,
        allowedRoots: candidate.selectedUnitPaths,
        configured: candidate.unitSelectionComplete,
      );
      _scopedRepository = scoped;
      final app = AppState(
        scoped,
        connectedEndpoint: candidate.displayEndpoint,
        localization: widget.localization,
        content: widget.content,
        // Panel-local access policy chosen during commissioning (appearance
        // step). The PLC's own §7.7 gates are published per root and untouched.
        config: HmiConfig(
          themeMinLevel:
              AccessLevel.values[(candidate.themeMinLevelIndex).clamp(0, 4)],
          closeAppMinLevel:
              AccessLevel.values[(candidate.closeAppMinLevelIndex).clamp(0, 4)],
          manualMinLevel:
              AccessLevel.values[(candidate.manualMinLevelIndex).clamp(0, 4)],
          alarmResetMinLevel: AccessLevel
              .values[(candidate.alarmResetMinLevelIndex).clamp(0, 4)],
        ),
        initialThemeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
        initialFloatingKeyboard: _settings?.floatingKeyboard ?? true,
        initialControlScale: ControlScale
            .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
        onUiPrefsChanged: _persistUiPrefs,
      );
      _app = app;
      _startupRetryAttempt = 0;
      app.addListener(_onAppChanged);
      debugPrint('[Fraktal/Connection] stage=subscriptions-created');
      _onAppChanged();
    } on S7WebLoginRequired catch (error) {
      repository?.dispose();
      debugPrint('[Fraktal/Connection] stage=s7web-login-required '
          'rejected=${error.rejected}');
      if (!mounted || generation != _connectionGeneration) return;
      setState(() {
        _lastLink = LinkState.down;
        _startupError = null;
        _loginRequired = error;
      });
    } on Object catch (error, stackTrace) {
      repository?.dispose();
      debugPrint('[Fraktal/Connection] stage=startup-failed error=$error');
      debugPrintStack(
        label: '[Fraktal/Connection] startup stack',
        stackTrace: stackTrace,
      );
      if (!mounted || generation != _connectionGeneration) return;
      setState(() {
        _lastLink = LinkState.down;
        _startupError = error.toString();
      });
      _scheduleStartupRetry(candidate, generation);
    }
  }

  void _scheduleStartupRetry(
    ConnectionSettings candidate,
    int generation,
  ) {
    if (!mounted ||
        generation != _connectionGeneration ||
        _phase != _BootstrapPhase.connecting) {
      return;
    }
    _startupRetryAttempt++;
    final exponent = (_startupRetryAttempt - 1).clamp(0, 20);
    final uncapped = widget.startupRetryBase.inMilliseconds * (1 << exponent);
    final delayMs = uncapped.clamp(
      1,
      widget.startupRetryMax.inMilliseconds,
    );
    debugPrint('[Fraktal/Connection] stage=startup-retry-scheduled '
        'attempt=$_startupRetryAttempt retryInMs=$delayMs');
    _startupRetryTimer?.cancel();
    _startupRetryTimer = Timer(Duration(milliseconds: delayMs), () {
      if (!mounted ||
          generation != _connectionGeneration ||
          _phase != _BootstrapPhase.connecting) {
        return;
      }
      debugPrint('[Fraktal/Connection] stage=startup-retry '
          'attempt=$_startupRetryAttempt');
      _attemptRepositoryConnection(candidate, generation);
    });
  }

  void _onAppChanged() {
    final app = _app;
    if (!mounted || app == null) return;
    final link = app.link;
    if (link != _lastLink) {
      debugPrint('[Fraktal/Connection] stage=link-state '
          'from=${_lastLink.name} to=${link.name}');
    }
    if (link == LinkState.live) {
      if (_phase == _BootstrapPhase.unitSelection && _editingUnitSelection) {
        return;
      }
      final available = _scopedRepository?.availableRoots ?? const [];
      if (available.isEmpty) {
        if (_lastLink != link) setState(() => _lastLink = link);
        return;
      }
      final selected = _settings?.selectedUnitPaths.toSet() ?? const <String>{};
      final availablePaths = available.map((root) => root.path).toSet();
      final validSelection = _settings?.unitSelectionComplete == true &&
          selected.isNotEmpty &&
          availablePaths.containsAll(selected);
      if (!validSelection) {
        _editTimer?.cancel();
        setState(() {
          _lastLink = link;
          _phase = _BootstrapPhase.unitSelection;
          _canEdit = false;
        });
        return;
      }
      if (_phase == _BootstrapPhase.live) {
        _lastLink = link;
        return;
      }
      _enterLive();
      return;
    }
    if (_phase == _BootstrapPhase.unitSelection) {
      setState(() {
        _phase = _BootstrapPhase.connecting;
        _lastLink = link;
        _canEdit = false;
      });
      _armEditDelay();
    } else if (_phase == _BootstrapPhase.live) {
      setState(() {
        _phase = _BootstrapPhase.connecting;
        _lastLink = link;
        _canEdit = false;
      });
      _armEditDelay();
    } else if (_phase == _BootstrapPhase.connecting && link != _lastLink) {
      setState(() => _lastLink = link);
    }
  }

  void _enterLive() {
    _startupRetryTimer?.cancel();
    _editTimer?.cancel();
    final firstLive = _phase != _BootstrapPhase.live;
    setState(() {
      _lastLink = LinkState.live;
      _phase = _BootstrapPhase.live;
      _canEdit = false;
    });
    debugPrint('[Fraktal/Connection] stage=live '
        'selectedUnits=${_settings?.selectedUnitPaths ?? const []}');
    if (firstLive && _settings?.everConnected != true) {
      final proven = _settings!.copyWith(everConnected: true);
      _settings = proven;
      widget.store.save(proven);
    }
  }

  Future<void> _saveUnitSelection(Set<String> paths) async {
    if (paths.isEmpty || _settings == null) return;
    final next = _settings!.copyWith(
      selectedUnitPaths: paths.toList()..sort(),
      unitSelectionComplete: true,
      everConnected: true,
    );
    await widget.store.save(next);
    if (!mounted) return;
    _editingUnitSelection = false;
    _settings = next;
    _scopedRepository?.setScope(next.selectedUnitPaths);
    _enterLive();
  }

  void _editUnitSelection() {
    if (_app?.session.level != AccessLevel.admin) return;
    setState(() {
      _editingUnitSelection = true;
      _phase = _BootstrapPhase.unitSelection;
    });
  }

  void _cancelUnitSelection() {
    if (_settings?.unitSelectionComplete == true) {
      _editingUnitSelection = false;
      _enterLive();
    }
  }

  void _setActiveLanguage(String language) {
    widget.localization.setActiveLanguage(language);
    final settings = _settings;
    if (settings == null) return;
    final next = settings.copyWith(activeLanguageCode: language);
    _settings = next;
    widget.store.save(next);
  }

  /// Persist UI prefs (theme index, floating-keyboard toggle) fired from AppState
  /// when they change, so they survive the AppState rebuild on reconnect.
  void _persistUiPrefs() {
    final app = _app;
    final settings = _settings;
    if (app == null || settings == null) return;
    final next = settings.copyWith(
      themeIndex: app.themeIndex,
      floatingKeyboard: app.floatingKeyboard,
      controlScaleIndex: app.controlScale.index,
    );
    _settings = next;
    widget.store.save(next);
  }

  void _armEditDelay() {
    _editTimer?.cancel();
    _editTimer = Timer(widget.editDelay, () {
      if (mounted && _phase == _BootstrapPhase.connecting) {
        debugPrint('[Fraktal/Connection] stage=edit-enabled '
            'afterSeconds=${widget.editDelay.inSeconds}');
        setState(() => _canEdit = true);
      }
    });
  }

  /// The operator entered the CPU web login on the connection screen. It is
  /// held for this endpoint only (in memory, and sealed for the OS user when
  /// [persist]), then the same saved settings connect again.
  void _submitS7WebLogin(String user, String password, bool persist) {
    final settings = _settings;
    if (settings == null) return;
    s7WebCredentials.remember(
        S7WebEndpoint.parse(Uri.parse(settings.endpoint)), user, password,
        persist: persist);
    _connect(settings, newlySaved: false);
  }

  void _editSettings() {
    _connectionGeneration++;
    _startupRetryTimer?.cancel();
    _editTimer?.cancel();
    _disposeApp();
    _editingUnitSelection = false;
    setState(() {
      _phase = _BootstrapPhase.wizard;
      _canEdit = false;
    });
  }

  /// Admin-only path back to the connection wizard from the live shell, so the
  /// endpoint can be changed without hand-editing settings or failing a connect.
  void _editConnection() {
    if (_app?.session.level != AccessLevel.admin) return;
    _editSettings();
  }

  /// Live preview while the engineer picks — the wizard re-themes itself, so the
  /// panel is judged as it will actually look rather than from a swatch.
  void _previewAppearance(int themeIndex, ControlScale scale) {
    setState(() {
      _previewTheme = themeIndex;
      _previewScale = scale;
    });
  }

  Future<void> _saveAppearance(AppearanceSetupResult result) async {
    final next =
        (_settings ?? ConnectionSettings(endpoint: defaultConnectionEndpoint()))
            .copyWith(
      themeIndex: result.themeIndex,
      controlScaleIndex: result.controlScale.index,
    );
    await widget.store.save(next);
    if (!mounted) return;
    setState(() {
      _settings = next;
      _previewTheme = null;
      _previewScale = null;
      _phase = _BootstrapPhase.accessSetup;
    });
  }

  Future<void> _saveAccess(AccessSetupResult result) async {
    final next =
        (_settings ?? ConnectionSettings(endpoint: defaultConnectionEndpoint()))
            .copyWith(
      themeMinLevelIndex: result.themeMinLevel.index,
      closeAppMinLevelIndex: result.closeAppMinLevel.index,
      manualMinLevelIndex: result.manualMinLevel.index,
      alarmResetMinLevelIndex: result.alarmResetMinLevel.index,
      appearanceSetupComplete: true,
    );
    await widget.store.save(next);
    if (!mounted) return;
    setState(() {
      _settings = next;
      _phase = _BootstrapPhase.wizard;
    });
  }

  /// Admin-only path back to the access step from the live shell.
  void _editAccess() {
    if (_app?.session.level != AccessLevel.admin) return;
    _connectionGeneration++;
    _startupRetryTimer?.cancel();
    _editTimer?.cancel();
    _disposeApp();
    _editingUnitSelection = false;
    setState(() {
      _phase = _BootstrapPhase.accessSetup;
      _canEdit = false;
    });
  }

  /// Admin-only path back to the appearance/access step from the live shell.
  void _editAppearance() {
    if (_app?.session.level != AccessLevel.admin) return;
    _connectionGeneration++;
    _startupRetryTimer?.cancel();
    _editTimer?.cancel();
    _disposeApp();
    _editingUnitSelection = false;
    setState(() {
      _phase = _BootstrapPhase.appearanceSetup;
      _canEdit = false;
    });
  }

  Future<void> _saveLanguageSelection(
      Set<String> enabled, String active) async {
    final next =
        (_settings ?? ConnectionSettings(endpoint: defaultConnectionEndpoint()))
            .copyWith(
      enabledLanguageCodes: enabled.toList()..sort(),
      activeLanguageCode: active,
      languageSelectionComplete: true,
    );
    await widget.store.save(next);
    if (!mounted) return;
    setState(() {
      _settings = next;
      // Appearance/access is chosen before the endpoint: the engineer is at the
      // panel, and a legible, correctly-sized wizard makes the rest easier.
      _phase = next.appearanceSetupComplete
          ? _BootstrapPhase.wizard
          : _BootstrapPhase.appearanceSetup;
    });
  }

  void _disposeApp() {
    final app = _app;
    if (app == null) return;
    app.removeListener(_onAppChanged);
    app.dispose();
    _app = null;
    _scopedRepository = null;
  }

  @override
  void dispose() {
    _connectionGeneration++;
    _startupRetryTimer?.cancel();
    _editTimer?.cancel();
    _disposeApp();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => switch (_phase) {
        _BootstrapPhase.loading => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: const ConnectionBlockingScreen(loadingSettings: true),
          ),
        _BootstrapPhase.languageSelection => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: FirstLanguageSelection(
              controller: widget.localization,
              initialEnabled: _settings?.enabledLanguageCodes.isNotEmpty == true
                  ? _settings!.enabledLanguageCodes.toSet()
                  : widget.localization.enabledLanguages,
              initialActive: _settings?.activeLanguageCode ??
                  widget.localization.activeLanguage,
              onContinue: _saveLanguageSelection,
            ),
          ),
        _BootstrapPhase.appearanceSetup => _ConnectionMaterial(
            localization: widget.localization,
            // Live preview: render in whatever is currently selected.
            themeIndex:
                _previewTheme ?? _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: _previewScale ??
                ControlScale
                    .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: AppearanceSetupScreen(
              initialThemeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
              initialControlScale: ControlScale
                  .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
              onPreview: _previewAppearance,
              onContinue: _saveAppearance,
            ),
          ),
        _BootstrapPhase.accessSetup => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: AccessSetupScreen(
              initialThemeMinLevel: AccessLevel
                  .values[(_settings?.themeMinLevelIndex ?? 0).clamp(0, 4)],
              initialCloseAppMinLevel: AccessLevel
                  .values[(_settings?.closeAppMinLevelIndex ?? 2).clamp(0, 4)],
              initialManualMinLevel: AccessLevel
                  .values[(_settings?.manualMinLevelIndex ?? 0).clamp(0, 4)],
              initialAlarmResetMinLevel: AccessLevel.values[
                  (_settings?.alarmResetMinLevelIndex ?? 0).clamp(0, 4)],
              onBack: () =>
                  setState(() => _phase = _BootstrapPhase.appearanceSetup),
              onContinue: _saveAccess,
            ),
          ),
        _BootstrapPhase.wizard => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: ConnectionWizard(
              initial: _settings,
              onConnect: (settings) => _connect(settings, newlySaved: true),
            ),
          ),
        _BootstrapPhase.connecting => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: ConnectionBlockingScreen(
              endpoint: _settings?.endpoint ?? '',
              state: _lastLink,
              canEdit: _canEdit,
              startupError: _startupError,
              onEdit: _editSettings,
              login: _loginRequired == null
                  ? null
                  : S7WebLoginForm(
                      rejected: _loginRequired!.rejected,
                      target: S7WebEndpoint.parse(
                          Uri.parse(_settings?.endpoint ?? '')),
                      onSubmit: _submitS7WebLogin,
                    ),
            ),
          ),
        _BootstrapPhase.unitSelection => _ConnectionMaterial(
            localization: widget.localization,
            themeIndex: _settings?.themeIndex ?? kDefaultThemeIndex,
            controlScale: ControlScale
                .values[(_settings?.controlScaleIndex ?? 0).clamp(0, 2)],
            child: UnitSelectionScreen(
              roots: _scopedRepository?.availableRoots ?? const [],
              initialSelection:
                  _settings?.selectedUnitPaths.toSet() ?? const {},
              onSave: _saveUnitSelection,
              onCancel: _settings?.unitSelectionComplete == true
                  ? _cancelUnitSelection
                  : null,
            ),
          ),
        _BootstrapPhase.live => FraktalHmiApp(
            app: _app!,
            onEditUnitSelection: _editUnitSelection,
            onEditConnection: _editConnection,
            onEditAppearance: _editAppearance,
            onEditAccess: _editAccess,
            onLanguageChanged: _setActiveLanguage,
          ),
      };
}

class _ConnectionMaterial extends StatelessWidget {
  final Widget child;
  final LocalizationController localization;

  /// The wizard renders in the SAME theme and control size the operator shell
  /// will use, so a commissioning engineer judges the panel as it will really
  /// look — and so a large-target preset is already active while they tap
  /// through setup on the panel itself.
  final int themeIndex;
  final ControlScale controlScale;

  const _ConnectionMaterial({
    required this.child,
    required this.localization,
    this.themeIndex = 0,
    this.controlScale = ControlScale.compact,
  });

  @override
  Widget build(BuildContext context) => LocalizationScope(
        controller: localization,
        child: ListenableBuilder(
          listenable: localization,
          builder: (context, _) => MaterialApp(
            title: localization.resolve('std.app.title'),
            debugShowCheckedModeBanner: false,
            // The wizard is a SEPARATE MaterialApp from the operator shell, so
            // it needs the touch scroll behaviour in its own right: the language
            // list and the Unit selection are touch-only on a panel too.
            scrollBehavior: kTouchScroll,
            locale: localization.locale,
            supportedLocales: [
              for (final code in availableLanguages.keys) Locale(code),
            ],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            theme: themeAt(themeIndex, controlScale),
            builder: (context, child) => ControlScaleScope(
              metrics: UiMetrics.of(controlScale),
              child: FraktalBackdrop(child: child ?? const SizedBox.shrink()),
            ),
            home: child,
          ),
        ),
      );
}

class UnitSelectionScreen extends StatefulWidget {
  final List<ModuleNode> roots;
  final Set<String> initialSelection;
  final ValueChanged<Set<String>> onSave;
  final VoidCallback? onCancel;

  const UnitSelectionScreen({
    super.key,
    required this.roots,
    required this.initialSelection,
    required this.onSave,
    this.onCancel,
  });

  @override
  State<UnitSelectionScreen> createState() => _UnitSelectionScreenState();
}

class _UnitSelectionScreenState extends State<UnitSelectionScreen> {
  late final Set<String> _selected;

  @override
  void initState() {
    super.initState();
    final available = widget.roots.map((root) => root.path).toSet();
    _selected = widget.initialSelection.intersection(available);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 640),
                child: FraktalCard(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Icon(Icons.factory_outlined,
                            size: 52,
                            color: Theme.of(context).colorScheme.primary),
                        const SizedBox(height: 12),
                        LText('std.units.selectTitle',
                            key: const Key('unit-selection-title'),
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        const LText(
                          'std.units.selectHelp',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        for (final root in widget.roots)
                          CheckboxListTile(
                            checkboxScaleFactor:
                                ControlScaleScope.of(context).toggleScale,
                            materialTapTargetSize: MaterialTapTargetSize.padded,
                            key: Key('unit-select-${root.path}'),
                            value: _selected.contains(root.path),
                            title: LText(root.displayNameKey.isEmpty
                                ? root.name
                                : root.displayNameKey),
                            subtitle: LText(root.path),
                            secondary:
                                const Icon(Icons.precision_manufacturing),
                            onChanged: (checked) => setState(() {
                              checked == true
                                  ? _selected.add(root.path)
                                  : _selected.remove(root.path);
                            }),
                          ),
                        if (_selected.isEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: LText('std.units.selectOne',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                    color:
                                        Theme.of(context).colorScheme.error)),
                          ),
                        const SizedBox(height: 20),
                        Row(children: [
                          if (widget.onCancel != null)
                            OutlinedButton(
                              onPressed: widget.onCancel,
                              child: const LText('std.common.cancel'),
                            ),
                          const Spacer(),
                          FilledButton.icon(
                            key: const Key('save-unit-selection'),
                            onPressed: _selected.isEmpty
                                ? null
                                : () => widget.onSave(Set.from(_selected)),
                            icon: const Icon(Icons.check),
                            label: const LText('std.units.save'),
                          ),
                        ]),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
}

class ConnectionWizard extends StatefulWidget {
  final ConnectionSettings? initial;
  final ValueChanged<ConnectionSettings> onConnect;

  const ConnectionWizard({super.key, this.initial, required this.onConnect});

  @override
  State<ConnectionWizard> createState() => _ConnectionWizardState();
}

class _ConnectionWizardState extends State<ConnectionWizard> {
  final _form = GlobalKey<FormState>();
  late ConnectionTransport _transport;
  late final TextEditingController _endpoint;
  final _webUser = TextEditingController();
  final _webPassword = TextEditingController();
  bool _rememberWebLogin = false;

  @override
  void initState() {
    super.initState();
    _transport = widget.initial?.transport ?? ConnectionTransport.gateway;
    _endpoint = TextEditingController(
      text: widget.initial?.endpoint ?? defaultConnectionEndpoint(),
    );
    final target = _s7WebTarget;
    if (target != null) {
      _webUser.text = s7WebCredentials.userFor(target);
      _rememberWebLogin = s7WebCredentials.isRemembered(target);
    }
  }

  @override
  void dispose() {
    _endpoint.dispose();
    _webUser.dispose();
    _webPassword.dispose();
    super.dispose();
  }

  /// The endpoint as a valid direct s7web:// target, or null.
  S7WebEndpoint? get _s7WebTarget {
    final uri = Uri.tryParse(_endpoint.text.trim());
    if (uri == null || uri.scheme != S7WebEndpoint.scheme) return null;
    return S7WebEndpoint.defect(uri) == null ? S7WebEndpoint.parse(uri) : null;
  }

  /// The login already held for the target, kept when the operator leaves
  /// its prefilled user unchanged and the password empty (it is never shown
  /// back).
  S7WebCredentials? get _heldWebLogin {
    final target = _s7WebTarget;
    final held = target == null ? null : s7WebCredentials.lookup(target);
    return held != null &&
            held.user == _webUser.text.trim() &&
            _webPassword.text.isEmpty
        ? held
        : null;
  }

  /// Both or neither: an empty login is asked for on connect (or comes from
  /// the environment on an unattended panel).
  String? _validateWebLogin(String? _) =>
      _heldWebLogin == null &&
              (_webUser.text.trim().isEmpty) != (_webPassword.text.isEmpty)
          ? context.tr('std.connection.s7webLoginMissing')
          : null;

  String? _validateEndpoint(String? value) {
    if (_transport == ConnectionTransport.simulation) return null;
    final uri = Uri.tryParse(value?.trim() ?? '');
    if (uri == null || !uri.hasScheme || uri.host.isEmpty)
      return context.tr('std.connection.endpointInvalid');
    const accepted = {
      'ws', 'wss', 'http', 'https', 'opc.tcp', 'ads', 'cip', 's7web' //
    };
    if (!accepted.contains(uri.scheme))
      return context.tr('std.connection.schemeInvalid');
    if (uri.scheme == 'ads' && uri.host.split('.').length != 6)
      return context.tr('std.connection.adsNetIdInvalid');
    if (uri.scheme == S7WebEndpoint.scheme) {
      // A browser cannot pin a certificate or hold the CPU login: Web builds
      // reach a TIA station through the gateway, which does both.
      if (kIsWeb) return context.tr('std.connection.s7webNative');
      if (S7WebEndpoint.defect(uri) != null)
        return context.tr('std.connection.s7webInvalid');
    }
    return null;
  }

  /// A concrete, editable example for the platform's native default transport.
  String get _endpointHint {
    if (kIsWeb) return 'ws://192.168.1.20:8080/fraktal';
    if (defaultTargetPlatform == TargetPlatform.windows) {
      return 'ads://192.168.1.6.1.1:851';
    }
    return 'opc.tcp://192.168.1.20:4840';
  }

  /// True while the operator is entering an ADS endpoint, so the wizard shows
  /// the AmsNetId/port format guidance next to the field.
  bool get _isAdsEndpoint =>
      _endpoint.text.trim().toLowerCase().startsWith('ads:');

  bool get _isS7WebEndpoint =>
      _endpoint.text.trim().toLowerCase().startsWith('s7web:');

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: FraktalCard(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _form,
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Icon(Icons.settings_ethernet,
                              size: 52,
                              color: Theme.of(context).colorScheme.primary),
                          const SizedBox(height: 12),
                          LText('std.connection.title',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.headlineSmall),
                          const SizedBox(height: 8),
                          const LText('std.connection.step',
                              textAlign: TextAlign.center),
                          const SizedBox(height: 24),
                          DropdownButtonFormField<ConnectionTransport>(
                            initialValue: _transport,
                            decoration: InputDecoration(
                                labelText: context.tr('std.connection.type'),
                                border: const OutlineInputBorder()),
                            items: const [
                              DropdownMenuItem(
                                  value: ConnectionTransport.gateway,
                                  child: LText('std.connection.gateway')),
                              DropdownMenuItem(
                                  value: ConnectionTransport.simulation,
                                  child: LText('std.connection.simulation')),
                            ],
                            onChanged: (value) => setState(
                                () => _transport = value ?? _transport),
                          ),
                          if (_transport == ConnectionTransport.gateway) ...[
                            const SizedBox(height: 16),
                            TextFormField(
                              controller: _endpoint,
                              autofocus: true,
                              decoration: InputDecoration(
                                labelText:
                                    context.tr('std.connection.endpoint'),
                                hintText: _endpointHint,
                                border: const OutlineInputBorder(),
                              ),
                              keyboardType: TextInputType.url,
                              validator: _validateEndpoint,
                              // Re-render so the ADS format help tracks the
                              // scheme the operator is typing.
                              onChanged: (_) => setState(() {}),
                            ),
                            const SizedBox(height: 8),
                            LText(
                                _isAdsEndpoint
                                    ? 'std.connection.adsHelp'
                                    : _isS7WebEndpoint
                                        ? 'std.connection.s7webHelp'
                                        : 'std.connection.transportHelp',
                                style: Theme.of(context).textTheme.bodySmall),
                            if (_isS7WebEndpoint && !kIsWeb) ...[
                              const SizedBox(height: 16),
                              S7WebLoginFields(
                                user: _webUser,
                                password: _webPassword,
                                validator: _validateWebLogin,
                                remember: _rememberWebLogin,
                                onRememberChanged: (value) =>
                                    setState(() => _rememberWebLogin = value),
                              ),
                            ],
                          ],
                          const SizedBox(height: 24),
                          FilledButton.icon(
                            key: const Key('save-connect'),
                            icon: const Icon(Icons.link),
                            label: const LText('std.connection.saveConnect'),
                            onPressed: () {
                              if (!(_form.currentState?.validate() ?? false))
                                return;
                              final target = _s7WebTarget;
                              final held = _heldWebLogin;
                              if (_transport == ConnectionTransport.gateway &&
                                  target != null &&
                                  _webUser.text.trim().isNotEmpty) {
                                s7WebCredentials.remember(
                                    target,
                                    _webUser.text.trim(),
                                    held?.password ?? _webPassword.text,
                                    persist: _rememberWebLogin);
                              }
                              widget.onConnect((widget.initial ??
                                      ConnectionSettings(
                                        endpoint: defaultConnectionEndpoint(),
                                      ))
                                  .copyWith(
                                transport: _transport,
                                endpoint:
                                    _transport == ConnectionTransport.simulation
                                        ? 'simulation://local'
                                        : _endpoint.text.trim(),
                              ));
                            },
                          ),
                        ]),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class ConnectionBlockingScreen extends StatelessWidget {
  final bool loadingSettings;
  final String endpoint;
  final LinkState state;
  final bool canEdit;
  final String? startupError;
  final VoidCallback? onEdit;

  /// The direct s7web:// login prompt, when the link needs one.
  final Widget? login;

  const ConnectionBlockingScreen({
    super.key,
    this.loadingSettings = false,
    this.endpoint = '',
    this.state = LinkState.connecting,
    this.canEdit = false,
    this.startupError,
    this.onEdit,
    this.login,
  });

  @override
  Widget build(BuildContext context) {
    final failed =
        !loadingSettings && (startupError != null || state == LinkState.down);
    final stateKey = switch (state) {
      LinkState.connecting => 'std.connection.stateConnecting',
      LinkState.live => 'std.connection.stateLive',
      LinkState.stale => 'std.connection.stateStale',
      LinkState.down => 'std.connection.stateDown',
    };
    return Scaffold(
      body: SafeArea(
        child: Center(
          // Scrolls on a small panel, where the login form makes it taller
          // than the screen.
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (login != null)
                Icon(Icons.lock_outline,
                    size: 56, color: Theme.of(context).colorScheme.primary)
              else if (failed)
                Icon(Icons.link_off,
                    size: 56, color: Theme.of(context).colorScheme.error)
              else
                const SizedBox(
                    width: 56,
                    height: 56,
                    child: CircularProgressIndicator(strokeWidth: 5)),
              const SizedBox(height: 24),
              LText(
                  loadingSettings
                      ? 'std.connection.loading'
                      : login != null
                          ? 'std.connection.s7webLoginTitle'
                          : 'std.connection.connecting',
                  key: const Key('connection-blocking-title'),
                  style: Theme.of(context).textTheme.headlineSmall),
              if (!loadingSettings && endpoint.isNotEmpty) ...[
                const SizedBox(height: 8),
                LText(endpoint,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium),
              ],
              if (!loadingSettings) ...[
                const SizedBox(height: 8),
                LText(stateKey,
                    key: const Key('connection-state-detail'),
                    textAlign: TextAlign.center),
              ],
              const SizedBox(height: 8),
              LText(
                loadingSettings
                    ? 'std.connection.loadingLocked'
                    : 'std.connection.connectingLocked',
                textAlign: TextAlign.center,
              ),
              if (startupError != null) ...[
                const SizedBox(height: 8),
                LText('std.connection.startFailed',
                    textAlign: TextAlign.center,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error)),
                const SizedBox(height: 8),
                SelectionArea(
                  child: Text(
                    startupError!,
                    key: const Key('connection-diagnostic-detail'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ],
              if (login != null) ...[
                const SizedBox(height: 16),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: login,
                ),
              ],
              if (canEdit) ...[
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  key: const Key('edit-connection-settings'),
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined),
                  label: const LText('std.connection.edit'),
                ),
              ],
            ]),
          ),
        ),
      ),
    );
  }
}

/// The CPU web user and password fields shared by the wizard and the login
/// prompt. The password is obscured and never prefilled or suggested. The
/// "remember" box appears only where the platform can seal the login for the
/// OS user (Windows DPAPI); elsewhere the login stays in memory only.
class S7WebLoginFields extends StatelessWidget {
  final TextEditingController user;
  final TextEditingController password;
  final FormFieldValidator<String>? validator;
  final VoidCallback? onSubmitted;
  final bool remember;
  final ValueChanged<bool>? onRememberChanged;

  const S7WebLoginFields({
    super.key,
    required this.user,
    required this.password,
    this.validator,
    this.onSubmitted,
    this.remember = false,
    this.onRememberChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      TextFormField(
        key: const Key('s7web-user'),
        controller: user,
        decoration: InputDecoration(
          labelText: context.tr('std.connection.s7webUser'),
          border: const OutlineInputBorder(),
        ),
        autocorrect: false,
        enableSuggestions: false,
        validator: validator,
      ),
      const SizedBox(height: 12),
      TextFormField(
        key: const Key('s7web-password'),
        controller: password,
        decoration: InputDecoration(
          labelText: context.tr('std.connection.s7webPassword'),
          border: const OutlineInputBorder(),
        ),
        obscureText: true,
        autocorrect: false,
        enableSuggestions: false,
        validator: validator,
        onFieldSubmitted: onSubmitted == null ? null : (_) => onSubmitted!(),
      ),
      if (canRemember) ...[
        const SizedBox(height: 4),
        CheckboxListTile(
          key: const Key('s7web-remember'),
          checkboxScaleFactor: ControlScaleScope.of(context).toggleScale,
          materialTapTargetSize: MaterialTapTargetSize.padded,
          controlAffinity: ListTileControlAffinity.leading,
          contentPadding: EdgeInsets.zero,
          value: remember,
          title: const LText('std.connection.s7webRemember'),
          onChanged: (checked) => onRememberChanged!(checked ?? false),
        ),
      ],
      const SizedBox(height: 8),
      LText(
          canRemember
              ? 'std.connection.s7webLoginHelpRemember'
              : 'std.connection.s7webLoginHelp',
          style: Theme.of(context).textTheme.bodySmall),
    ]);
  }

  bool get canRemember =>
      onRememberChanged != null && s7WebCredentials.canRemember;
}

/// Asks for the CPU web login of a saved s7web:// endpoint (after an HMI
/// restart, or after the CPU refused the previous one).
class S7WebLoginForm extends StatefulWidget {
  final bool rejected;
  final S7WebEndpoint target;
  final void Function(String user, String password, bool remember) onSubmit;

  const S7WebLoginForm({
    super.key,
    required this.rejected,
    required this.target,
    required this.onSubmit,
  });

  @override
  State<S7WebLoginForm> createState() => _S7WebLoginFormState();
}

class _S7WebLoginFormState extends State<S7WebLoginForm> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _user =
      TextEditingController(text: s7WebCredentials.userFor(widget.target));
  final _password = TextEditingController();
  late bool _remember = s7WebCredentials.isRemembered(widget.target);

  @override
  void dispose() {
    _user.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    if (!(_form.currentState?.validate() ?? false)) return;
    widget.onSubmit(_user.text.trim(), _password.text, _remember);
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _form,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (widget.rejected) ...[
          LText('std.connection.s7webLoginRejected',
              key: const Key('s7web-login-rejected'),
              textAlign: TextAlign.center,
              style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const SizedBox(height: 12),
        ],
        S7WebLoginFields(
          user: _user,
          password: _password,
          validator: (value) => (value ?? '').trim().isEmpty
              ? context.tr('std.connection.s7webLoginMissing')
              : null,
          onSubmitted: _submit,
          remember: _remember,
          onRememberChanged: (value) => setState(() => _remember = value),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          key: const Key('s7web-login-connect'),
          icon: const Icon(Icons.login),
          label: const LText('std.connection.s7webLoginConnect'),
          onPressed: _submit,
        ),
      ]),
    );
  }
}
