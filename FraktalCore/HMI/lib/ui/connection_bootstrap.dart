library;

import 'dart:async';
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import '../content/module_content_controller.dart';
import '../data/connection_settings_store.dart';
import '../data/plc_repository.dart';
import '../data/repository_factory.dart';
import '../data/scoped_plc_repository.dart';
import '../domain/connection_settings.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/default_catalogs.dart';
import '../localization/localization_controller.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'fraktal_hmi_app.dart';
import 'language_settings.dart';

enum _BootstrapPhase {
  loading,
  languageSelection,
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

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await Future.wait([
      widget.localization.load(),
      widget.content.load(),
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
        localization: widget.localization,
        content: widget.content,
      );
      _app = app;
      _startupRetryAttempt = 0;
      app.addListener(_onAppChanged);
      debugPrint('[Fraktal/Connection] stage=subscriptions-created');
      _onAppChanged();
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
      _phase = _BootstrapPhase.wizard;
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
            child: const ConnectionBlockingScreen(loadingSettings: true),
          ),
        _BootstrapPhase.languageSelection => _ConnectionMaterial(
            localization: widget.localization,
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
        _BootstrapPhase.wizard => _ConnectionMaterial(
            localization: widget.localization,
            child: ConnectionWizard(
              initial: _settings,
              onConnect: (settings) => _connect(settings, newlySaved: true),
            ),
          ),
        _BootstrapPhase.connecting => _ConnectionMaterial(
            localization: widget.localization,
            child: ConnectionBlockingScreen(
              endpoint: _settings?.endpoint ?? '',
              state: _lastLink,
              canEdit: _canEdit,
              startupError: _startupError,
              onEdit: _editSettings,
            ),
          ),
        _BootstrapPhase.unitSelection => _ConnectionMaterial(
            localization: widget.localization,
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
            onLanguageChanged: _setActiveLanguage,
          ),
      };
}

class _ConnectionMaterial extends StatelessWidget {
  final Widget child;
  final LocalizationController localization;
  const _ConnectionMaterial({
    required this.child,
    required this.localization,
  });

  @override
  Widget build(BuildContext context) => LocalizationScope(
        controller: localization,
        child: ListenableBuilder(
          listenable: localization,
          builder: (context, _) => MaterialApp(
            title: localization.resolve('std.app.title'),
            debugShowCheckedModeBanner: false,
            locale: localization.locale,
            supportedLocales: [
              for (final code in availableLanguages.keys) Locale(code),
            ],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            theme: ThemeData(
                useMaterial3: true,
                colorScheme:
                    ColorScheme.fromSeed(seedColor: const Color(0xFF3D6DEB))),
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
                child: Card(
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

  @override
  void initState() {
    super.initState();
    _transport = widget.initial?.transport ?? ConnectionTransport.gateway;
    _endpoint = TextEditingController(
      text: widget.initial?.endpoint ?? defaultConnectionEndpoint(),
    );
  }

  @override
  void dispose() {
    _endpoint.dispose();
    super.dispose();
  }

  String? _validateEndpoint(String? value) {
    if (_transport == ConnectionTransport.simulation) return null;
    final uri = Uri.tryParse(value?.trim() ?? '');
    if (uri == null || !uri.hasScheme || uri.host.isEmpty)
      return context.tr('std.connection.endpointInvalid');
    const accepted = {'ws', 'wss', 'http', 'https', 'opc.tcp', 'ads'};
    if (!accepted.contains(uri.scheme))
      return context.tr('std.connection.schemeInvalid');
    if (uri.scheme == 'ads' && uri.host.split('.').length != 6)
      return context.tr('std.connection.adsNetIdInvalid');
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Card(
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
                                    : 'std.connection.transportHelp',
                                style: Theme.of(context).textTheme.bodySmall),
                          ],
                          const SizedBox(height: 24),
                          FilledButton.icon(
                            key: const Key('save-connect'),
                            icon: const Icon(Icons.link),
                            label: const LText('std.connection.saveConnect'),
                            onPressed: () {
                              if (!(_form.currentState?.validate() ?? false))
                                return;
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

  const ConnectionBlockingScreen({
    super.key,
    this.loadingSettings = false,
    this.endpoint = '',
    this.state = LinkState.connecting,
    this.canEdit = false,
    this.startupError,
    this.onEdit,
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
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (failed)
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
