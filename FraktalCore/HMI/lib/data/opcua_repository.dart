library;

import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../domain/fieldbus.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import 'opcua_config_manifest.dart';
import 'opcua_field_tier.dart';
import 'opcua_freshness.dart';
import 'opcua_session_client.dart';
import 'opcua_snapshot_mapper.dart';
import 'plc_repository.dart';

enum _HmiRequestKind {
  none,
  login,
  logout,
  setMode,
  setModel,
  start,
  stop,
  controlOn,
  controlOff,
  operatorReset,
  decisionAnswer,
  manualCommand,
  setRunStyle,
  stepRequest,
  setHoldRun,
  releaseStart,
  releaseManual,
  releaseAction,
  resetOee,
  writeConfig,
  shelveAlarm,
  unshelveAlarm,
  forceChannel,
  queryConfig,
  setAccessLevel,
  setSessionTimeout,
  lampTest,
  // Core §3.8c / §3.8b. Ordinals are the PLC transport contract
  // (E_HmiRequestKind), so these are appended in the PLC's order and never
  // reordered. No HMI control drives them yet, but they are declared here
  // because plc_lint rule E1 compares the two enums member for member: an
  // ordinal that exists on the PLC and not here is how a client ends up sending
  // LOAD_CONFIG_SET when it meant LAMP_TEST. The ignores are deliberate and
  // come off as each control is built.
  // ignore: unused_field
  captureConfig,
  saveConfigSet,
  loadConfigSet,
  listConfigSets,
  ackConfigRestore,
  exportConfigSet,
  importConfigSet,
  // ignore: unused_field
  manualHeld,
  deleteConfigSet,
  setClassLevel,
  createModel,
  exportCurrentConfig,
}

/// Direct native OPC UA repository for Dart-native Flutter platforms. The
/// client browses the Fraktal contract generically; no module type or station
/// screen is compiled into this adapter.
class OpcUaRepository implements PlcRepository {
  final OpcUaSessionClient _client;
  final OpcUaSnapshotMapper _mapper;
  final Duration refreshInterval;
  final _forestController = StreamController<List<ModuleNode>>.broadcast();
  final _fieldbusController = StreamController<List<BusNode>>.broadcast();
  final _linkController = StreamController<LinkState>.broadcast();
  Timer? _timer;
  Duration? _pollPeriod;
  Duration? _refreshStarted;
  Timer? _freshnessTimer;
  final _clock = Stopwatch()..start();
  OpcUaFreshnessBudget? _freshness;
  Duration _sampleTick = Duration.zero, _receivedAge = Duration.zero;
  Duration get _sampleAge => _receivedAge + _clock.elapsed - _sampleTick;
  Future<void>? _refreshInFlight;
  bool _disposed = false;
  final Map<String, int> _requestSequenceByMailbox = {};
  DateTime _lastGood = DateTime.now();
  LinkState _link = LinkState.connecting;
  OpcUaProjection _projection = const OpcUaProjection(
      forest: [], fieldbus: [], browsePathByModulePath: {});
  Map<String, Object?> _values = const {};
  List<String> _discoveredPaths = const [];
  // On-demand (view-gated) paths grouped by activation scope: the fieldbus scope
  // key, or a root Unit's browse base for that root's drill-down rings/trends.
  Map<String, List<String>> _onDemandByScope = const {};
  final Set<String> _activeOnDemandScopes = {};
  final Map<String, Set<String>> _onDemandContainersByScope = {};
  Timer? _onDemandContinuation;
  List<String> _tierSlowPaths = const [];
  List<String> _tierExcludedPaths = const [];
  Future<void> _tierUpdate = Future<void>.value();

  // A budgeted tiered transport can renew the visible detail in its complete
  // snapshots. Leaf-by-leaf targeted sweeps otherwise outlive the Good window
  // even though the native source reads each whole record at once.
  bool get _streamsDetail =>
      _freshness != null && _client is OpcUaTieredReadClient;
  // A declared freshness budget keeps detail work off the complete-sample
  // refresh. Retain each bounded read's own start tick; reading another batch
  // must never renew an older batch or the station's liveness.
  final _onDemandSamples =
      <String, ({Object? value, Duration started, int status})>{};
  bool _onDemandReadInFlight = false;
  int _onDemandGeneration = 0;
  List<String> _lastTierPaths = const [];
  List<String> _lastTierRoots = const [];
  Set<String> _lastTierManifestPaths = const {};
  // Interactive (operator-initiated) requests in flight. While > 0 the periodic
  // full-tree refresh yields the single native worker so the command's small
  // ack polls are not queued behind a full snapshot (Core §14 responsiveness).
  int _interactiveInFlight = 0;
  // §3.10.2 config manifest: synthesized browse-path values overlaid under the
  // live snapshot so the mapper sees the same tree a full publication would give.
  Map<String, Object?> _manifestValues = const {};
  Map<String, List<CfgField>> _manifestConfigByModule = const {};
  String? _manifestRevSignature; // null = never hydrated
  bool _manifestFetchInFlight = false;
  DateTime _manifestRetryAfter = DateTime.fromMillisecondsSinceEpoch(0);
  // §3.10.2 refetch coalescing: the signature we are waiting to settle, and when
  // it last moved. See [_configRevSettle].
  String? _manifestSettlingSignature;
  DateTime _manifestSignatureMovedAt = DateTime.fromMillisecondsSinceEpoch(0);
  String _rootChildren = '';
  String _namespaceUris = '';
  String _aliasSignature = '';
  Future<void> _requestQueue = Future<void>.value();

  OpcUaRepository._(this._client, this._mapper, this.refreshInterval);

  /// [refreshInterval] is the cyclic poll period, and it — not the work per
  /// cycle — is what sets observed I/O staleness: a change is seen after
  /// ~interval/2 on average, ~interval worst case.
  ///
  /// 250 ms (4 Hz) measured against a live 15k-symbol PLC over ADS: the full
  /// snapshot costs ~24 ms and the on-demand fieldbus read ~5 ms, so ~29 ms of
  /// a 250 ms budget is real work — the rest was idle wait. Emission cadence
  /// tracked the requested period exactly at 500/250/125 ms, so this is not
  /// riding a limit. It was 500 ms, chosen when mapping cost ~1.1 s per refresh
  /// and dominated the cycle; that cost is now ~17 ms (see
  /// `_buildParentPaths`), which is what makes the faster poll affordable.
  static Future<OpcUaRepository> connectWithClient(
    OpcUaSessionClient client, {
    Duration refreshInterval = const Duration(milliseconds: 250),
  }) async {
    final repository =
        OpcUaRepository._(client, OpcUaSnapshotMapper(), refreshInterval);
    try {
      await repository._refresh(propagateFailure: true);
      if (repository._projection.forest.isEmpty) {
        final keys = repository._values.keys.take(8).join(', ');
        final onlyStandardServer = repository._values.isEmpty &&
            repository._rootChildren == '0:Server(Object)';
        final plcNamespaceLoaded = repository._namespaceUris
            .contains('urn:BeckhoffAutomation:Ua:PLC1');
        final accessFiltered = onlyStandardServer && plcNamespaceLoaded;
        throw StateError('The OPC UA server is reachable, but no Fraktal root '
            'Unit was discovered. '
            '${accessFiltered ? 'TF6100 reports that the PLC1 Data Access namespace is loaded, but the current OPC UA identity cannot browse it. Assign this identity to a TF6100 group/role with recursive browse/read access to PLC1; grant write only to the HmiRequest command mailbox. ' : 'For TF6100 TMC-Filtered publication, verify ${onlyStandardServer ? 'that this OPC UA identity has browse/read access to the configured PLC Data Access namespace, ' : ''}that the root Unit instance has the OPC.UA.DA publication attribute and that the updated Port_<ADS port>.tmc was downloaded and reloaded. '}'
            'The root must publish Status : ST_ModuleStatus. '
            'Snapshot contained ${repository._values.length} value nodes'
            '${keys.isEmpty ? '' : '; first browse paths: $keys'}. '
            'Objects folder children: '
            '${repository._rootChildren.isEmpty ? '(none)' : repository._rootChildren}. '
            'Server namespaces: '
            '${repository._namespaceUris.isEmpty ? '(unavailable)' : repository._namespaceUris}.');
      }
      repository._startPolling();
      return repository;
    } on Object {
      await repository._close();
      rethrow;
    }
  }

  void _startPolling() {
    final period = _freshness?.pollPeriod ?? refreshInterval;
    if (_disposed || (_pollPeriod == period && (_timer?.isActive ?? false))) return;
    _timer?.cancel();
    _pollPeriod = period;
    if (_freshness != null) {
      final elapsed = _refreshStarted == null
          ? Duration.zero : _clock.elapsed - _refreshStarted!;
      final remaining = period - elapsed;
      _timer = Timer(remaining > Duration.zero ? remaining : Duration.zero, () {
        _timer = null;
        unawaited(_pollBudgeted());
      });
      return;
    }
    _timer = Timer.periodic(period, (_) {
      _checkFreshness();
      // Older transports yield their single worker during initial hydration
      // and operator requests. A declared budget requires periodic complete
      // samples even then: partial Ack reads cannot keep a station live.
      if (_freshness == null &&
          _manifestFetchInFlight &&
          _manifestRevSignature == null) return;
      if (_interactiveInFlight > 0 &&
          (_freshness == null || _sampleAge < _freshness!.pollPeriod)) return;
      _refresh();
    });
  }

  Future<void> _pollBudgeted() async {
    if (_disposed) return;
    _checkFreshness();
    final period = _freshness!.pollPeriod;
    if (_interactiveInFlight > 0 && _sampleAge < period) {
      _timer = Timer(period - _sampleAge, () {
        _timer = null;
        unawaited(_pollBudgeted());
      });
      return;
    }
    // One acquisition at a time. If it overruns its period, resume as soon as
    // it completes rather than skipping to a later periodic-timer boundary.
    // Fast acquisitions still wait out the declared minimum period.
    await _refresh();
    _startPolling();
  }

  Future<void> _refresh({bool propagateFailure = false}) {
    if (_disposed) return Future<void>.value();
    final active = _refreshInFlight;
    if (active != null) return active;
    final refresh = _performRefresh(propagateFailure: propagateFailure);
    _refreshInFlight = refresh;
    return refresh.whenComplete(() {
      if (identical(_refreshInFlight, refresh)) _refreshInFlight = null;
    });
  }

  Future<void> _performRefresh({required bool propagateFailure}) async {
    try {
      final started = _clock.elapsed;
      _refreshStarted = started;
      var document = await _client.snapshot();
      if (_disposed) return;
      validateCompleteOpcUaSnapshot(document);
      final freshness = OpcUaFreshnessBudget.parse(document);
      if (_freshness != null && freshness == null) {
        throw const FormatException('Freshness budget disappeared.');
      }
      final transitAge = freshness?.transitAllowance(
          document, _clock.elapsed - started) ?? Duration.zero;
      final receivedAge = freshness == null
          ? Duration.zero
          : OpcUaFreshnessBudget.age(document['sampleAgeMs']) +
              transitAge;
      final receivedTick = _clock.elapsed;
      if (freshness != null) {
        document = freshness.ageDocument(document, transitAge);
      }
      final raw = document['values'];
      if (raw is! Map) throw const FormatException('Snapshot values missing.');
      _values = {for (final entry in raw.entries) '${entry.key}': entry.value};
      // The bridge emits the full discovered `paths` once per (re)discovery;
      // subsequent snapshots carry an empty list. Keep the last non-empty set so
      // path-tier classification and the topology-base lookup stay valid between
      // discoveries. A rediscovery (reconnect/online change) always re-emits.
      final paths = document['paths'];
      if (paths is List && paths.isNotEmpty) {
        _discoveredPaths = [for (final p in paths) '$p'];
      }
      final root = document['rootChildren'];
      _rootChildren = root is List ? root.join(', ') : '';
      final namespaces = document['namespaces'];
      _namespaceUris = namespaces is List ? namespaces.join(', ') : '';
      // On-demand (view-gated) data: target-read only active scopes' paths and
      // overlay under the live snapshot so the mapper sees a complete tree.
      final onDemandOverlay =
          freshness == null ? await _readActiveOnDemand() : null;
      if (_disposed) return;
      if (freshness != null) {
        _freshness = freshness;
        _sampleTick = receivedTick;
        _receivedAge = receivedAge;
        if (_sampleAge >= freshness.fastGood) {
          _checkFreshness();
          throw const FormatException(
              'Complete station sample is late or expired.');
        }
        // Include local processing before mapping the complete tree.
        document =
            freshness.ageDocument(document, _clock.elapsed - receivedTick);
        final current = document['values'] as Map;
        _values = {
          for (final item in current.entries) '${item.key}': item.value
        };
      }
      // §3.10.2 — overlay the hydrated config manifest UNDER the live snapshot
      // so the mapper sees the same flat tree a full publication would give
      // (live values win on any collision). _values stays raw: mailbox reads
      // and the slow-path tier must only ever see real published nodes.
      final detail = freshness == null ? null : _agedOnDemand(freshness);
      final merged = <String, Object?>{
        ..._manifestValues,
        if (onDemandOverlay != null) ...onDemandOverlay,
        if (detail != null)
          ...(detail['values'] as Map).cast<String, Object?>(),
        ..._values,
      };
      _projection = _mapper.map(
          onDemandOverlay == null && _manifestValues.isEmpty && detail == null
              ? document
              : <String, Object?>{
                  ...document,
                  'values': merged,
                  if (detail != null)
                    'dataValues': {
                      ...(detail['dataValues'] as Map),
                      ...(document['dataValues'] as Map),
                    },
                },
          configByModulePath: _manifestConfigByModule);
      if (freshness != null && _projection.forest.isEmpty) {
        throw const FormatException(
            'No current Good root Unit in the complete sample.');
      }
      final aliases = _projection.discardedAliases;
      final aliasSignature = aliases.join('|');
      if (aliases.isNotEmpty && aliasSignature != _aliasSignature) {
        debugPrint('[Fraktal/Connection] stage=opcua-aliases-discarded '
            'count=${aliases.length} paths=${aliases.take(12).join(', ')}');
      }
      _aliasSignature = aliasSignature;
      _lastGood = DateTime.now();
      _maybeUpdatePathTiers();
      _maybeFetchConfigManifest();
      _setLink(LinkState.live);
      _scheduleFreshness();
      if (_timer != null) _startPolling();
      // Same race as _setLink: this refresh may have been disposed across one of
      // the awaits above (snapshot / on-demand read / manifest hydration).
      if (_disposed) return;
      _forestController.add(_projection.forest);
      _fieldbusController.add(_projection.fieldbus);
      if (freshness != null) unawaited(_readBudgetedOnDemand());
    } on Object catch (error) {
      final age = DateTime.now().difference(_lastGood);
      _setLink((_freshness != null
              ? _sampleAge >= _freshness!.fastExpiry
              : age >= const Duration(seconds: 5))
          ? LinkState.down
          : LinkState.stale);
      if (_freshness != null) _withdrawData();
      debugPrint(
          '[Fraktal/Connection] stage=opcua-refresh-failed error=$error');
      if (propagateFailure) rethrow;
    }
  }

  // Classify the FULL discovered contract (emitted once per discovery as
  // `paths`) and push the excluded (on-demand) set to the native client. These
  // paths are never read in the cyclic snapshot — only when their owning view
  // activates the scope. Every non-excluded, non-config leaf is fast (live).
  // Re-runs when the discovered path set or the discovered root set changes
  // (first snapshot, online change, reconnect). The classifier runs over
  // `paths`, not `_values`, since excluded paths are absent from the values.
  void _maybeUpdatePathTiers() {
    // The DEPLOYED root Units only — browsePathByModulePath carries every
    // module, and the published-contract boundary is drawn at the roots
    // TF6100 publishes (`OPC.UA.DA := '1'`), not at each module under one.
    final rootBases = <String>[
      for (final root in _projection.forest)
        if (_browseBase(root.path) case final base?) base,
    ];
    // Re-run on a new path set OR on a new root set. The roots come from the
    // mapped projection, so a first snapshot that discovers paths before it
    // resolves the forest would otherwise pin an unscoped classification for
    // the whole session.
    final manifestPaths = _manifestValues.keys.toSet();
    if (listEquals(_lastTierPaths, _discoveredPaths) &&
        listEquals(_lastTierRoots, rootBases) &&
        setEquals(_lastTierManifestPaths, manifestPaths)) {
      return;
    }
    _lastTierPaths = List.unmodifiable(_discoveredPaths);
    _lastTierRoots = List.unmodifiable(rootBases);
    _lastTierManifestPaths = manifestPaths;
    if (_discoveredPaths.isEmpty) return;
    final slow = <String>[];
    final excluded = <String>[];
    final onDemandByScope = <String, List<String>>{};
    var offContract = 0;
    var manifestServed = 0;
    for (final path in _discoveredPaths) {
      // Match what TF6100 publishes before asking which tier a leaf is in: a
      // path outside the published roots has no tier, because over OPC UA it has
      // no node. Excluded, never scoped — no view can ask for it.
      if (OpcUaFieldTier.isOutsidePublishedRoots(path, rootBases)) {
        excluded.add(path);
        offContract++;
        continue;
      }
      // Exclude published static data only after its exact replacement is
      // hydrated. Bindings need not serve every static container in their
      // pages; guessing from the name removed the AB model list entirely.
      if (OpcUaFieldTier.isManifestServed(path, hydratedPaths: manifestPaths)) {
        excluded.add(path);
        manifestServed++;
        continue;
      }
      switch (OpcUaFieldTier.classify(path)) {
        case FieldTier.slow:
          slow.add(path);
        case FieldTier.onDemand:
          // On-demand data is never in the cyclic snapshot — exclude it whether
          // or not it maps to an activatable scope. A path with a scope is served
          // when its owning view activates; one without an owner (e.g. an ADS-only
          // internal sub-FB's ring) is simply never read. Previously the no-scope
          // case fell through and leaked into the fast tier — invisible over OPC UA
          // (unpublished) but ~3.5k extra cyclic reads over ADS.
          excluded.add(path);
          final scope = OpcUaFieldTier.onDemandScopeOf(path, rootBases);
          if (scope != null) {
            onDemandByScope.putIfAbsent(scope, () => []).add(path);
          }
        case FieldTier.config:
        case FieldTier.live:
          // Config-tier leaves stay in the cyclic (fast) snapshot. Over OPC UA
          // they are unpublished (OPC.UA.DA := '0') so they never reach here;
          // over ADS the whole symbol table is visible and reading them costs a
          // few hundred extra sum-read leaves — cheap with batch handle
          // resolution. They are NOT excluded, because the tier's leaf list is a
          // heuristic that also catches cyclically-required fields (module
          // identity Status/Name, the SupportedModes capability): excluding them
          // dropped modules from the tree and emptied the mode dropdown. The
          // manifest still serves the genuinely obscured subtrees (fieldbus
          // identity) that ARE on-demand/absent from the snapshot.
          break;
      }
    }
    _onDemandByScope = onDemandByScope;
    _invalidateOnDemand();
    debugPrint('[Fraktal/Connection] stage=opcua-read-tiers '
        'discovered=${_discoveredPaths.length} '
        'fast=${_discoveredPaths.length - slow.length - excluded.length} '
        'slow=${slow.length} excluded=${excluded.length} '
        'offContract=$offContract manifest=$manifestServed '
        'scopes=${onDemandByScope.length}');
    _tierSlowPaths = slow;
    _tierExcludedPaths = excluded;
    _publishPathTiers();
  }

  void _publishPathTiers() {
    final baseSlow = List<String>.of(_tierSlowPaths);
    final demanded = _streamsDetail
        ? _requestedOnDemandPaths().toSet()
        : const <String>{};
    final slow = {...baseSlow, ...demanded};
    final excluded = _tierExcludedPaths
        .where((path) => !demanded.contains(path)).toSet();
    // Serialize updates and remove the previous promotion first. No interim
    // request may contain the same path in both slow and excluded sets.
    _tierUpdate = _tierUpdate.then((_) async {
      if (_disposed) return;
      await _client.setSlowPaths(baseSlow);
      await _client.setExcludedPaths(excluded);
      await _client.setSlowPaths(slow);
    }).catchError((Object error) {
      debugPrint('[Fraktal/Connection] stage=opcua-read-tiers-failed error=$error');
    });
  }

  @override
  void setFieldbusViewActive(bool active) {
    _setOnDemandScopeActive(OpcUaFieldTier.fieldbusScope, active);
    // Core §10.5.1 is a diagnostic surface, so demand-gating is end-to-end: not
    // reading the topology here is only half of it — without this the PLC would
    // still poll the EtherCAT master over ADS every cycle to maintain data
    // nobody is looking at. Best-effort: a PLC that does not publish the flag
    // (older library, or a project that leaves it unmapped) simply keeps its own
    // cadence, so this must never surface as a user-visible failure.
    unawaited(_setFieldbusScanRequested(active));
  }

  /// Publishes the fieldbus-view demand gate to the PLC (`MAIN.FieldbusViewActive`).
  Future<void> _setFieldbusScanRequested(bool active) async {
    final base = _fieldbusScanFlagPath();
    if (base == null) return;
    try {
      await _write(base, OpcUaWriteType.boolean, active);
    } on Object catch (error) {
      debugPrint('[Fraktal/Connection] stage=fieldbus-gate-write-skipped '
          'active=$active error=$error');
    }
  }

  /// Browse path of the PLC's fieldbus demand gate, or null when the running PLC
  /// does not expose one. Derived from the discovered contract rather than
  /// hardcoded, so it works for any project that publishes the flag.
  String? _fieldbusScanFlagPath() {
    for (final path in _discoveredPaths) {
      if (path.endsWith('/FieldbusViewActive')) return path;
    }
    return null;
  }

  @override
  void setModuleDetailActive(String rootPath, bool active,
      {Set<String>? containers}) {
    final base = _browseBase(rootPath);
    if (base != null) {
      _setOnDemandScopeActive(base, active, containers: containers);
    }
  }

  /// Activates an on-demand data scope so the repository target-reads its paths
  /// each refresh (e.g. while the fieldbus diagnostic page is visible). A scope
  /// that is not active is never read cyclically.
  void _setOnDemandScopeActive(String scope, bool active,
      {Set<String>? containers}) {
    final next = active && containers != null
        ? Set<String>.unmodifiable(containers)
        : null;
    var changed = !setEquals(_onDemandContainersByScope[scope], next);
    if (next == null) {
      _onDemandContainersByScope.remove(scope);
    } else {
      _onDemandContainersByScope[scope] = next;
    }
    changed = (active
            ? _activeOnDemandScopes.add(scope)
            : _activeOnDemandScopes.remove(scope)) ||
        changed;
    if (changed) {
      _invalidateOnDemand();
      _publishPathTiers();
      unawaited(_refresh());
    }
  }

  /// The browse base of the fieldbus `ST_FieldbusTopology` instance, from the
  /// full discovered path set (its live members are on-demand/excluded, so it is
  /// not in `_values`). Null when no fieldbus topology is published.
  String? _discoveredTopologyBase() {
    for (final path in _discoveredPaths) {
      final index = path.indexOf('/Topology/');
      if (index >= 0) return path.substring(0, index + '/Topology'.length);
    }
    return null;
  }

  @override
  bool get fieldbusExpected => _discoveredTopologyBase() != null;

  List<String> _requestedOnDemandPaths() => [
        for (final scope in _activeOnDemandScopes)
          for (final path in _onDemandByScope[scope] ?? const <String>[])
            if (_onDemandContainersByScope[scope] == null ||
                OpcUaFieldTier.demandedContainers([path])
                    .any(_onDemandContainersByScope[scope]!.contains))
              path,
      ];

  /// Target-reads the excluded paths of every active on-demand scope in one
  /// batch (bulk-read capable clients only), returning them for the snapshot
  /// overlay. Null when nothing is active or the client cannot bulk-read (the
  /// gateway keeps publishing these paths cyclically, so no overlay is needed).
  Future<Map<String, Object?>?> _readActiveOnDemand() async {
    if (_activeOnDemandScopes.isEmpty) return null;
    final session = _client;
    if (session is! OpcUaBulkReadClient) return null;
    final paths = _requestedOnDemandPaths();
    if (paths.isEmpty) return null;
    try {
      return await session.readValues(paths);
    } on Object {
      return null; // a failed on-demand read degrades to no overlay, not a fault
    }
  }

  void _invalidateOnDemand() {
    _onDemandContinuation?.cancel();
    _onDemandContinuation = null;
    _onDemandGeneration++;
    _onDemandSamples.clear();
  }

  Map<String, Object?>? _agedOnDemand(OpcUaFreshnessBudget budget) {
    if (_onDemandSamples.isEmpty) return null;
    final now = _clock.elapsed;
    return budget.ageDocument({
      'values': {
        for (final item in _onDemandSamples.entries) item.key: item.value.value,
      },
      'dataValues': {
        for (final item in _onDemandSamples.entries)
          item.key: {
            'value': item.value.value,
            'type': PublishedTagValue.good(item.value.value).typeName,
            // Bulk reads return usable scalars, or null for unavailable data.
            'status': item.value.status,
            'tier': 'slow',
            'ageMs': (now - item.value.started).inMicroseconds / 1000,
          },
      },
    }, Duration.zero);
  }

  Future<void> _readBudgetedOnDemand() async {
    final session = _client;
    if (_disposed ||
        _streamsDetail ||
        _onDemandReadInFlight ||
        _onDemandContinuation != null ||
        _interactiveInFlight > 0 ||
        _link != LinkState.live ||
        _activeOnDemandScopes.isEmpty ||
        session is! OpcUaBulkReadClient) return;
    final paths = _requestedOnDemandPaths();
    if (paths.isEmpty) return;
    _onDemandReadInFlight = true;
    final generation = _onDemandGeneration;
    final sweepStarted = _clock.elapsed;
    var completed = false;
    try {
      // One bounded RPC at a time leaves the shared transport able to serve
      // periodic complete snapshots and operator acknowledgements between
      // batches. Each reply becomes visible at the next complete snapshot.
      for (var offset = 0;
          offset < paths.length;
          offset += opcUaTargetReadBatchSize) {
        if (_disposed ||
            generation != _onDemandGeneration ||
            _interactiveInFlight > 0 ||
            _link != LinkState.live) return;
        final started = _clock.elapsed;
        final end = offset + opcUaTargetReadBatchSize < paths.length
            ? offset + opcUaTargetReadBatchSize
            : paths.length;
        final batch = paths.sublist(offset, end);
        final envelope = session is OpcUaDataValueReadClient
            ? await (session as OpcUaDataValueReadClient).readDataValues(batch)
            : null;
        final values = envelope == null
            ? await session.readValues(batch)
            : (envelope['values'] as Map).cast<String, Object?>();
        if (_disposed || generation != _onDemandGeneration) return;
        for (final path in batch) {
          var sourceAge = Duration.zero;
          var status = values[path] == null ? 0x80320000 : 0;
          if (envelope != null) {
            final source = (envelope['dataValues'] as Map)[path];
            final age = source is Map ? source['ageMs'] : null;
            final quality = source is Map ? source['status'] : null;
            if (age is! num || !age.isFinite || age < 0 ||
                quality is! int || quality < 0 || quality > 0xffffffff) {
              status = 0x80000000;
            } else {
              sourceAge = Duration(microseconds: (age * 1000).ceil());
              status = values[path] == null ? 0x80320000 : quality;
            }
          }
          _onDemandSamples[path] = (value: values[path],
              started: started - sourceAge, status: status);
        }
      }
      completed = true;
    } on Object {
      // Detail failure does not invalidate a separately current station
      // sample. Previously obtained detail still ages out on its own budget.
    } finally {
      _onDemandReadInFlight = false;
      // Do not add a full poll-period gap to a successful detail sweep. The
      // event-loop timer lets complete samples/commands run between bounded
      // RPCs. A fast sweep still respects the declared slow period. Failure
      // keeps the existing complete-refresh retry cadence.
      if (completed && !_disposed && generation == _onDemandGeneration) {
        final remaining =
            _freshness!.slowPeriod - (_clock.elapsed - sweepStarted);
        _onDemandContinuation?.cancel();
        _onDemandContinuation = Timer(
            remaining > Duration.zero ? remaining : Duration.zero, () {
          _onDemandContinuation = null;
          unawaited(_readBudgetedOnDemand());
        });
      }
    }
  }

  /// How long the published `ConfigRev` signature must hold still before a
  /// REFETCH is charged. Long enough to swallow a burst of §3.13 row
  /// discoveries at mode entry, short enough that a config write the operator
  /// just made comes back within one interaction. The first hydration ignores it.
  static const Duration _configRevSettle = Duration(milliseconds: 750);

  // §3.10.2 — fetch (or refetch) the config manifest when a root forest exists
  // and the published ConfigRev signature differs from the hydrated one. The
  // revision is seeded from PLC boot time and bumped on config writes, model
  // changes, and re-activation, so PLC restarts and config edits both refetch;
  // a reconnect alone keeps the still-valid manifest.
  void _maybeFetchConfigManifest() {
    if (_disposed || _manifestFetchInFlight || _projection.forest.isEmpty) {
      return;
    }
    final signature = _configRevSignature();
    // No published ConfigRev = a PLC library without the manifest protocol
    // (it still publishes everything cyclically) — nothing to fetch.
    if (signature.isEmpty) return;
    if (signature == _manifestRevSignature) return;
    if (DateTime.now().isBefore(_manifestRetryAfter)) return;
    // Coalesce a BURST of revisions into one fetch. §3.13 rows are discovered by
    // visit and each newly appended row bumps the Unit's ConfigRev, so entering a
    // mode with a long chain used to charge one full paged refetch per row —
    // AUTO (15 steps) paid roughly eight times what HOME (2 steps) did, which is
    // exactly the asymmetry the operator feels. The PLC coalesces this too
    // (FB_UnitBase._M_ChartRevCyclic), but the HMI cannot assume the PLC in front
    // of it has that library, so the client holds its own guard.
    //
    // The first hydration is exempt: there is no manifest yet, nothing to
    // coalesce, and delaying it would delay the first complete tree.
    if (_manifestRevSignature != null) {
      if (signature != _manifestSettlingSignature) {
        _manifestSettlingSignature = signature;
        _manifestSignatureMovedAt = DateTime.now();
        return; // still moving — refetch once it stops
      }
      if (DateTime.now().difference(_manifestSignatureMovedAt) <
          _configRevSettle) {
        return;
      }
    }
    _manifestFetchInFlight = true;
    unawaited(_fetchConfigManifest(signature).whenComplete(() {
      _manifestFetchInFlight = false;
    }));
  }

  String _configRevSignature() {
    final parts = <String>[
      for (final entry in _values.entries)
        if (entry.key.endsWith('/ConfigRev')) '${entry.key}=${entry.value}',
    ]..sort();
    return parts.join('|');
  }

  Future<void> _fetchConfigManifest(String revSignature) async {
    final entries = <ConfigManifestEntry>[];
    for (final root in _projection.forest) {
      final base = _browseBase(root.path);
      if (base == null) continue;
      final pageBase = '$base/HmiResponse/ConfigPage';
      var page = 0;
      var pageCount = 1;
      while (page < pageCount) {
        // Background fetch: generous ack window — under load (fresh handle
        // pool, large live tree) a single snapshot poll can exceed the default
        // interactive deadline, and a false timeout restarts the whole fetch.
        final response = await _queryConfigPage(root.path, page);
        if (response == null) {
          debugPrint('[Fraktal/Connection] stage=config-manifest-failed '
              'root=${root.path} page=$page');
          _manifestRetryAfter = DateTime.now().add(const Duration(seconds: 5));
          return; // signature not stored -> retried after the backoff
        }
        pageCount = _integer(response['$pageBase/PageCount']);
        entries.addAll(_readConfigPage(pageBase, response));
        page++;
      }
    }
    // A conforming Unit always exports at least its counts/policy, so an empty
    // result means the pages were not readable (naming/transport fault): do not
    // store the signature — a later refresh retries instead of silently keeping
    // an empty manifest until the next ConfigRev change.
    if (entries.isEmpty) {
      debugPrint('[Fraktal/Connection] stage=config-manifest-empty '
          'detail=pages acked but no entries parsed; will retry');
      _manifestRetryAfter = DateTime.now().add(const Duration(seconds: 5));
      return;
    }
    await _applyConfigManifest(entries, revSignature);
  }

  @override
  Future<List<CfgField>?> queryModelConfig(
      String rootPath, int modelIndex) async {
    final base = _browseBase(rootPath);
    if (base == null || modelIndex < 0) return null;
    final pageBase = '$base/HmiResponse/ConfigPage';
    final entries = <ConfigManifestEntry>[];
    var page = 0;
    var pageCount = 1;
    while (page < pageCount) {
      final response =
          await _queryConfigPage(rootPath, page, model: modelIndex);
      if (response == null) return null;
      pageCount = _integer(response['$pageBase/PageCount']);
      entries.addAll(_readConfigPage(pageBase, response)
          .where((entry) => entry.scope == rootPath && entry.modelScoped));
      page++;
    }
    return configFieldsFromManifest(entries)[rootPath] ?? const [];
  }

  /// Capture this query's page before cleanup or a cyclic snapshot can replace
  /// the shared values. Both manifest hydration and model selection use it.
  Future<Map<String, Object?>?> _queryConfigPage(String rootPath, int page,
      {int model = 0}) async {
    final base = _browseBase(rootPath);
    if (base == null) return null;
    Map<String, Object?>? response;
    final accepted = await _request(rootPath, _HmiRequestKind.queryConfig,
        intValue: page,
        durationMs: model,
        ackTimeout: const Duration(seconds: 10),
        onResponseValues: (values) => response = Map.unmodifiable(values));
    final pageBase = '$base/HmiResponse/ConfigPage';
    if (!accepted || response == null) return null;
    final pageCount = response!['$pageBase/PageCount'];
    final entryCount = response!['$pageBase/EntryCount'];
    // The page window belongs to the binding. TwinCAT publishes 16 slots;
    // manifest gateways may publish a larger window. Bound the count by the
    // rows in this freshly read, discovered response instead of a PLC-specific
    // constant, and reject incomplete rows before hydrating any configuration.
    final capacity = response!.keys
        .where((path) =>
            path.startsWith('$pageBase/Entries') && path.endsWith('/Scope'))
        .length;
    if (pageCount is! int ||
        pageCount < 1 ||
        entryCount is! int ||
        entryCount < 0 ||
        entryCount > capacity) return null;
    final prefixes = <String>{};
    for (var i = 1; i <= entryCount; i++) {
      final prefix = _indexedPrefix(response!, '$pageBase/Entries', i);
      if (prefix == null ||
          !prefixes.add(prefix) ||
          response!['$prefix/Scope'] is! String ||
          response!['$prefix/Item'] is! String ||
          response!['$prefix/ValueText'] is! String) return null;
    }
    return response;
  }

  /// The entries of the immutable configuration page this query answered.
  List<ConfigManifestEntry> _readConfigPage(
      String pageBase, Map<String, Object?> values) {
    final entries = <ConfigManifestEntry>[];
    final entryCount = _integer(values['$pageBase/EntryCount']);
    for (var i = 1; i <= entryCount; i++) {
      final prefix = _indexedPrefix(values, '$pageBase/Entries', i);
      if (prefix == null) continue;
      entries.add(ConfigManifestEntry(
        '${values['$prefix/Scope'] ?? ''}',
        '${values['$prefix/Item'] ?? ''}',
        '${values['$prefix/ValueText'] ?? ''}',
        writeKey: '${values['$prefix/WriteKey'] ?? ''}',
        writeRevision: _integer(values['$prefix/WriteRevision']),
        configKind: _integer(values['$prefix/ConfigKind']),
        valueType: _integer(values['$prefix/ValueType']),
        writable: values['$prefix/Writable'] == true,
        requiresReady: values['$prefix/RequiresReady'] == true,
        hasMinimum: values['$prefix/HasMinimum'] == true,
        hasMaximum: values['$prefix/HasMaximum'] == true,
        minimum: _real(values['$prefix/Minimum']),
        maximum: _real(values['$prefix/Maximum']),
        unit: '${values['$prefix/Unit'] ?? ''}',
        labelKey: '${values['$prefix/LabelKey'] ?? ''}',
        enumDomain: '${values['$prefix/EnumDomain'] ?? ''}',
        // Absent OR unread (an older PLC has no such member): legacy text.
        unitCode: values['$prefix/UnitCode'] == null
            ? null
            : _integer(values['$prefix/UnitCode']),
        enumLabelKey: '${values['$prefix/EnumLabelKey'] ?? ''}',
        // §3.8d. A PLC older than data classes publishes none of these:
        // an ABSENT level must read as unknown (-1), never as NONE, or an
        // old controller would appear to open every value to everyone.
        classId: '${values['$prefix/ClassId'] ?? ''}',
        readLevel: values.containsKey('$prefix/ReadLevel')
            ? _integer(values['$prefix/ReadLevel'])
            : -1,
        writeLevel: values.containsKey('$prefix/WriteLevel')
            ? _integer(values['$prefix/WriteLevel'])
            : -1,
        readable: values['$prefix/Readable'] != false,
        modelScoped: values['$prefix/ModelScoped'] == true,
      ));
    }
    return entries;
  }

  Future<void> _applyConfigManifest(
      List<ConfigManifestEntry> entries, String revSignature) async {
    // Derive the topology base from the DISCOVERED path set, not from _values:
    // the topology's live members (NodeCount, node State/LinkOk) are on-demand
    // and therefore excluded from _values, so scanning _values would miss it and
    // drop every #Fieldbus manifest entry.
    final topologyBase = _discoveredTopologyBase();
    _manifestValues = synthesizeManifestValues(
      entries,
      browseBaseByModulePath: _projection.browsePathByModulePath,
      topologyBase: topologyBase,
    );
    _manifestConfigByModule = configFieldsFromManifest(entries);
    _manifestRevSignature = revSignature;
    debugPrint('[Fraktal/Connection] stage=config-manifest-hydrated '
        'entries=${entries.length} values=${_manifestValues.length}');
    await _refresh(); // re-map immediately with the hydrated overlay
  }

  void _setLink(LinkState value) {
    if (_link == value) return;
    _link = value;
    // A refresh is async, so dispose() can close the controllers while one is
    // still in flight (e.g. the user leaves the page mid-request). The
    // _disposed check when the refresh STARTS cannot cover that — the state can
    // change across every await inside it — so re-check at each emit.
    if (_disposed) return;
    _linkController.add(value);
  }

  void _checkFreshness() {
    final budget = _freshness;
    if (_disposed || budget == null || _sampleAge < budget.fastGood) return;
    _setLink(
        _sampleAge >= budget.fastExpiry ? LinkState.down : LinkState.stale);
    // Withdraw cached Good data as well as the operator shell. Keep canonical
    // aliases for recovery; no command may use them while the link is stale.
    _withdrawData();
    _scheduleFreshness();
  }

  void _withdrawData() {
    if (_disposed) return;
    _invalidateOnDemand();
    if (_projection.forest.isNotEmpty || _projection.fieldbus.isNotEmpty) {
      _values = const {};
      _projection = OpcUaProjection(
          forest: const [],
          fieldbus: const [],
          browsePathByModulePath: _projection.browsePathByModulePath);
      _forestController.add(const []);
      _fieldbusController.add(const []);
    }
  }

  void _scheduleFreshness() {
    _freshnessTimer?.cancel();
    final budget = _freshness;
    if (_disposed || budget == null || _sampleAge >= budget.fastExpiry) return;
    final limit =
        _sampleAge < budget.fastGood ? budget.fastGood : budget.fastExpiry;
    _freshnessTimer = Timer(limit - _sampleAge, _checkFreshness);
  }

  @override
  Stream<List<ModuleNode>> forest() async* {
    _checkFreshness();
    yield _projection.forest;
    yield* _forestController.stream;
  }

  @override
  Stream<List<BusNode>> fieldbus() async* {
    _checkFreshness();
    yield _projection.fieldbus;
    yield* _fieldbusController.stream;
  }

  @override
  Stream<LinkState> linkState() async* {
    _checkFreshness();
    yield _link;
    yield* _linkController.stream;
  }

  String? _browseBase(String modulePath) =>
      _projection.browsePathByModulePath[modulePath];

  Future<bool> _write(String path, OpcUaWriteType type, Object value) async {
    _checkFreshness();
    if (_link != LinkState.live) return false;
    try {
      final written = await _client.write(path, type, value);
      if (!written) {
        debugPrint('[Fraktal/Connection] stage=opcua-write-refused path=$path');
      }
      return written;
    } on Object catch (error) {
      debugPrint('[Fraktal/Connection] stage=opcua-write-failed '
          'path=$path error=$error');
      return false;
    }
  }

  Future<bool> _writeBatch(List<OpcUaWrite> writes) async {
    _checkFreshness();
    if (_link != LinkState.live) return false;
    try {
      final written = await _client.writeBatch(writes);
      if (!written) {
        debugPrint('[Fraktal/Connection] stage=opcua-write-batch-refused '
            'commit=${writes.last.path}');
      }
      return written;
    } on Object catch (error) {
      debugPrint('[Fraktal/Connection] stage=opcua-write-batch-failed '
          'commit=${writes.last.path} error=$error');
      return false;
    }
  }

  Future<bool> _request(
    String unitPath,
    _HmiRequestKind kind, {
    String targetPath = '',
    String nameValue = '',
    String textValue = '',
    String user = '',
    String secret = '',
    int intValue = 0,
    bool boolValue = false,
    int durationMs = 0,
    Duration ackTimeout = const Duration(seconds: 2),
    void Function(int)? onSequenceReserved,
    void Function(Map<String, Object?>)? onResponseValues,
  }) {
    // Operator commands mark the repository interactive so the periodic refresh
    // yields the worker; the background manifest fetch (queryConfig) is already
    // gated by _manifestFetchInFlight and must not double-count here.
    final interactive = kind != _HmiRequestKind.queryConfig || durationMs != 0;
    if (interactive) _interactiveInFlight++;
    final result = Completer<bool>();
    _requestQueue = _requestQueue.then((_) async {
      try {
        result.complete(await _performRequest(
          unitPath,
          kind,
          targetPath: targetPath,
          nameValue: nameValue,
          textValue: textValue,
          user: user,
          secret: secret,
          intValue: intValue,
          boolValue: boolValue,
          durationMs: durationMs,
          ackTimeout: ackTimeout,
          onSequenceReserved: onSequenceReserved,
          onResponseValues: onResponseValues,
        ));
      } on Object catch (error, stackTrace) {
        result.completeError(error, stackTrace);
      } finally {
        if (interactive) _interactiveInFlight--;
        if (interactive &&
            _interactiveInFlight == 0 &&
            _link == LinkState.live &&
            _client is OpcUaBulkReadClient) {
          // Show the PLC's actual result promptly after the command. The timer
          // yields while interactive; resume with one shared refresh now.
          _refresh();
        }
      }
    });
    return result.future;
  }

  Future<bool> _performRequest(
    String unitPath,
    _HmiRequestKind kind, {
    required String targetPath,
    required String nameValue,
    required String textValue,
    required String user,
    required String secret,
    required int intValue,
    required bool boolValue,
    required int durationMs,
    required Duration ackTimeout,
    void Function(int)? onSequenceReserved,
    void Function(Map<String, Object?>)? onResponseValues,
  }) async {
    _checkFreshness();
    final base = _browseBase(unitPath);
    if (base == null || _link != LinkState.live) {
      debugPrint('[Fraktal/Connection] stage=opcua-request-unavailable '
          'kind=${kind.name} unit=$unitPath link=${_link.name}');
      return false;
    }
    final request = '$base/HmiRequest';
    final observedRequest = _integer(_values['$request/Sequence']);
    final observedAck = _integer(_values['$base/HmiResponse/AckSequence']);
    var previous = _requestSequenceByMailbox.putIfAbsent(
      request,
      // Request is the committed input, possibly awaiting its ack. Counters
      // wrap, so numeric max would choose the old 0xffffffff over the new 0.
      () =>
          (_values.containsKey('$request/Sequence')
              ? observedRequest
              : observedAck) &
          0xffffffff,
    );
    if (_values.containsKey('$request/Sequence')) {
      final distance = (observedRequest - previous) & 0xffffffff;
      if (distance > 0 && distance < 0x80000000) {
        previous = observedRequest & 0xffffffff;
      }
    }
    // Reserve before the attempt. If the connection is lost after commit, the
    // outcome is ambiguous and this sequence must never be reused or replayed.
    final sequence = (previous + 1) & 0xffffffff;
    _requestSequenceByMailbox[request] = sequence;
    onSequenceReserved?.call(sequence);
    debugPrint('[Fraktal/Connection] stage=opcua-request-start '
        'kind=${kind.name} unit=$unitPath sequence=$sequence');
    final writes = <OpcUaWrite>[
      OpcUaWrite('$request/Kind', OpcUaWriteType.int32, kind.index),
      OpcUaWrite('$request/TargetPath', OpcUaWriteType.string, targetPath),
      OpcUaWrite('$request/NameValue', OpcUaWriteType.string, nameValue),
      OpcUaWrite('$request/TextValue', OpcUaWriteType.string, textValue),
      OpcUaWrite('$request/User', OpcUaWriteType.string, user),
      OpcUaWrite('$request/Secret', OpcUaWriteType.string, secret),
      OpcUaWrite('$request/IntValue', OpcUaWriteType.int32, intValue),
      OpcUaWrite('$request/BoolValue', OpcUaWriteType.boolean, boolValue),
      OpcUaWrite('$request/DurationMs', OpcUaWriteType.uint32, durationMs),
      // Sequence is the commit marker and is deliberately written last.
      OpcUaWrite('$request/Sequence', OpcUaWriteType.uint32, sequence),
    ];
    if (!await _writeBatch(writes)) {
      debugPrint('[Fraktal/Connection] stage=opcua-request-commit-failed '
          'kind=${kind.name} sequence=$sequence');
      return false;
    }

    // A bulk-read-capable client polls the three ack leaves in one targeted
    // service call — a full snapshot per poll costs seconds on a large live
    // tree and starves the ack window. Other transports keep the legacy
    // shared-refresh poll.
    final session = _client;
    final bulk = session is OpcUaBulkReadClient ? session : null;
    final ackPath = '$base/HmiResponse/AckSequence';
    final acceptedPath = '$base/HmiResponse/Accepted';
    final diagnosticPath = '$base/HmiResponse/Diagnostic';
    final deadline = DateTime.now().add(ackTimeout);
    while (DateTime.now().isBefore(deadline) && _link == LinkState.live) {
      int ack;
      bool accepted;
      String diagnostic;
      if (bulk != null) {
        Map<String, Object?> read;
        try {
          read = await bulk.readValues([ackPath, acceptedPath, diagnosticPath]);
        } on Object {
          read = const {};
        }
        ack = _integer(read[ackPath]);
        accepted = read[acceptedPath] == true;
        diagnostic = '${read[diagnosticPath] ?? ''}';
      } else {
        await _refresh();
        ack = _integer(_values[ackPath]);
        accepted = _values[acceptedPath] == true;
        diagnostic = '${_values[diagnosticPath] ?? ''}';
      }
      if (ack == sequence) {
        debugPrint('[Fraktal/Connection] stage=opcua-request-ack '
            'kind=${kind.name} sequence=$sequence accepted=$accepted '
            'diagnostic=$diagnostic');
        // Fast-path consumers read the response payload from _values; pull the
        // kind's payload subtree in one more targeted read so they see THIS
        // acknowledgement's data, not the last snapshot's.
        Map<String, Object?> responseValues = const {};
        if (bulk != null && accepted) {
          final followUp = _ackFollowUpPaths(kind, base);
          if (followUp.isNotEmpty) {
            try {
              final extra = await bulk.readValues(followUp);
              responseValues = extra;
              if (extra.isNotEmpty) _values = {..._values, ...extra};
            } on Object {
              // Page consumers receive no payload and report unavailable;
              // an earlier model's values cannot stand in for this reply.
            }
          }
        }
        if (accepted && onResponseValues != null) {
          onResponseValues(bulk == null ? _values : responseValues);
        }
        // Keep what the PLC SAID, not just whether it agreed. A refusal
        // carries a reason, and reporting "the transport is unavailable" for a
        // request the controller answered promptly sends everyone looking at
        // the network instead of reading the answer.
        _lastRefusal = accepted ? '' : diagnostic;
        await _write(
            '$request/Kind', OpcUaWriteType.int32, _HmiRequestKind.none.index);
        return accepted;
      }
      await Future<void>.delayed(
          Duration(milliseconds: bulk != null ? 20 : 30));
    }
    debugPrint('[Fraktal/Connection] stage=opcua-request-timeout '
        'kind=${kind.name} sequence=$sequence');
    // No acknowledgement at all: this one really is a transport answer.
    _lastRefusal = '';
    return false;
  }

  @override
  Future<bool> login(String rootPath, String user, String secret) async {
    // A LOGIN mailbox acknowledgement means the PLC consumed the request; it
    // does not mean the access provider accepted the credentials. The access
    // manager publishes the authoritative outcome. A bounded asynchronous
    // provider may publish LoginBusy while checking the sampled credentials.
    int? loginSequence;
    final consumed = await _request(
      rootPath,
      _HmiRequestKind.login,
      user: user,
      secret: secret,
      onSequenceReserved: (sequence) => loginSequence = sequence,
    );
    if (!consumed) {
      throw StateError('Login request was not consumed by the access provider');
    }
    final base = _browseBase(rootPath);
    if (base == null) return false;
    final hasResultSequence =
        _values.containsKey('$base/Access/LoginResultSequence');
    final paths = [
      '$base/Access/CurrentUser',
      '$base/Access/CurrentLevel',
      '$base/Access/LoginFailed',
      if (_values.containsKey('$base/Access/LoginBusy'))
        '$base/Access/LoginBusy',
      if (hasResultSequence) '$base/Access/LoginResultSequence',
    ];
    // Background providers declare their result budget. Synchronous/older
    // providers keep the existing six-second wait; cap malformed budgets.
    final declaredTimeout = _integer(_values['$base/Access/LoginTimeoutMs']);
    final timeoutMs = declaredTimeout > 0 && declaredTimeout <= 600000
        ? declaredTimeout
        : 6000;
    final budget = Duration(milliseconds: timeoutMs);
    final elapsed = Stopwatch()..start();
    while (elapsed.elapsed < budget && _link == LinkState.live) {
      await Future<void>.delayed(const Duration(milliseconds: 30));
      final remaining = budget - elapsed.elapsed;
      if (remaining <= Duration.zero) break;
      final client = _client;
      if (client is OpcUaBulkReadClient) {
        try {
          final read = await client.readValues(paths).timeout(remaining);
          if (paths.any((p) => !read.containsKey(p))) continue;
          _values = {..._values, ...read};
        } on Object {
          continue;
        }
      } else {
        await _refresh().timeout(remaining);
      }
      if (_values['$base/Access/LoginBusy'] == true) continue;
      if (hasResultSequence &&
          (_integer(_values['$base/Access/LoginResultSequence']) &
                  0xffffffff) !=
              loginSequence) {
        continue;
      }
      final failed = _values['$base/Access/LoginFailed'] == true;
      final level = _integer(_values['$base/Access/CurrentLevel']);
      final currentUser = '${_values['$base/Access/CurrentUser'] ?? ''}';
      final authenticated =
          !failed && level > AccessLevel.none.index && currentUser == user;
      // An empty/old session is not a credential rejection. Only an explicit
      // provider failure settles failure, including correlated providers.
      if (!authenticated && !failed) continue;
      debugPrint('[Fraktal/Connection] stage=opcua-login-result '
          'authenticated=$authenticated level=$level loginFailed=$failed');
      return authenticated;
    }
    if (_link != LinkState.live) {
      throw StateError('Connection lost while waiting for the login result');
    }
    throw TimeoutException('Access provider login result timed out', budget);
  }

  @override
  Future<void> logout(String rootPath) async {
    await _request(rootPath, _HmiRequestKind.logout);
  }

  @override
  Future<bool> setMode(String unitPath, UnitMode mode) =>
      _request(unitPath, _HmiRequestKind.setMode, intValue: mode.index);

  @override
  Future<bool> setModel(String rootPath, String modelCode) async {
    final ok = await _request(rootPath, _HmiRequestKind.setModel,
        textValue: modelCode);
    // A changeover rewrites recipe/config leaves (the slow tier); pull them now.
    if (ok) {
      unawaited(_client.refreshSlowPaths().then((_) {}, onError: (_, __) {}));
    }
    return ok;
  }

  @override
  Future<bool> start(String unitPath) =>
      _request(unitPath, _HmiRequestKind.start);

  @override
  Future<bool> stop(String unitPath) =>
      _request(unitPath, _HmiRequestKind.stop);

  @override
  Future<bool> controlOn(String unitPath) =>
      _request(unitPath, _HmiRequestKind.controlOn);

  @override
  Future<bool> controlOff(String unitPath) =>
      _request(unitPath, _HmiRequestKind.controlOff);

  @override
  Future<bool> operatorReset(String unitPath) =>
      _request(unitPath, _HmiRequestKind.operatorReset);

  @override
  Future<bool> lampTest(String unitPath) =>
      _request(unitPath, _HmiRequestKind.lampTest);

  @override
  Future<bool> setDecisionAnswer(String unitPath, int option) =>
      _request(unitPath, _HmiRequestKind.decisionAnswer, intValue: option);

  @override
  Future<bool> setAccessLevel(
          String rootPath, GatedAction action, AccessLevel level) =>
      _request(rootPath, _HmiRequestKind.setAccessLevel,
          intValue: action.index, textValue: '${level.index}');

  @override
  Future<bool> setSessionTimeout(String rootPath, Duration timeout) =>
      _request(rootPath, _HmiRequestKind.setSessionTimeout,
          durationMs: timeout.inMilliseconds);

  @override
  Future<bool> manualCommand(String unitPath, String targetPath, int value) =>
      _request(unitPath, _HmiRequestKind.manualCommand,
          targetPath: targetPath, intValue: value);

  @override
  Future<bool> manualHeld(
          String unitPath, String targetPath, int value, bool held) =>
      _request(unitPath, _HmiRequestKind.manualHeld,
          targetPath: targetPath, intValue: value, boolValue: held);

  @override
  Future<bool> setRunStyle(String unitPath, RunStyle style) =>
      _request(unitPath, _HmiRequestKind.setRunStyle, intValue: style.index);

  @override
  Future<void> stepRequest(String unitPath) async {
    await _request(unitPath, _HmiRequestKind.stepRequest);
  }

  @override
  Future<void> setHoldRun(String unitPath, bool held) async {
    await _request(unitPath, _HmiRequestKind.setHoldRun, boolValue: held);
  }

  @override
  Future<ReleaseReport> releaseReportStart(String unitPath) async {
    final accepted = await _request(unitPath, _HmiRequestKind.releaseStart);
    return _readReleaseReport(unitPath, accepted);
  }

  @override
  Future<ReleaseReport> releaseReportManual(
      String unitPath, String targetPath, int commandValue) async {
    final accepted = await _request(unitPath, _HmiRequestKind.releaseManual,
        targetPath: targetPath, intValue: commandValue);
    return _readReleaseReport(unitPath, accepted);
  }

  @override
  Future<ReleaseReport> releaseReportAction(
      String unitPath, GatedAction action) async {
    final accepted = await _request(unitPath, _HmiRequestKind.releaseAction,
        intValue: action.index);
    return _readReleaseReport(unitPath, accepted);
  }

  /// Response payloads follow the exact discovered subtree. Bindings may use
  /// flat or container array names and publish different optional members.
  List<String> _ackFollowUpPaths(_HmiRequestKind kind, String base) {
    final String subtree;
    switch (kind) {
      case _HmiRequestKind.releaseStart:
      case _HmiRequestKind.releaseManual:
      case _HmiRequestKind.releaseAction:
        subtree = '$base/HmiResponse/Report/';
      case _HmiRequestKind.queryConfig:
        subtree = '$base/HmiResponse/ConfigPage/';
      default:
        return const [];
    }
    final published =
        _discoveredPaths.isEmpty ? _values.keys : _discoveredPaths;
    return [
      for (final path in published)
        if (path.startsWith(subtree)) path
    ];
  }

  /// What the controller answered when it refused the last request, or ''
  /// when it did not answer at all. The two are different facts and the
  /// operator needs the first one.
  String _lastRefusal = '';

  ReleaseReport _readReleaseReport(String unitPath, bool requestAccepted) {
    final base = _browseBase(unitPath);
    if (base == null || !requestAccepted) {
      // A station that answered and refused told us why. Saying "the
      // transport is unavailable" there is not a vaguer version of the truth,
      // it is a different and wrong claim - the PLC is reachable and
      // answering, and the operator is sent to look at the network.
      final reason = _lastRefusal.isNotEmpty
          ? _lastRefusal
          : 'std.release.transportUnavailable';
      return ReleaseReport(false, [ReleaseReason(reason, ReleaseKind.other)]);
    }
    final response = '$base/HmiResponse/Report';
    final released = _values['$response/Released'] == true;
    final count = _integer(_values['$response/Count']);
    final reasons = <ReleaseReason>[];
    for (var i = 1; i <= count; i++) {
      final prefix = _indexedPrefix(_values, '$response/Reasons', i);
      if (prefix == null) continue;
      reasons.add(ReleaseReason(
        '${_values['$prefix/Description'] ?? ''}',
        _enumAt(ReleaseKind.values, _integer(_values['$prefix/Kind']),
            ReleaseKind.other),
        bypassable: _values['$prefix/Bypassable'] == true,
        reasonCode: _integer(_values['$prefix/ReasonCode']),
        sourcePath: '${_values['$prefix/SourcePath'] ?? ''}',
      ));
    }
    debugPrint('[Fraktal/Connection] stage=opcua-release-report '
        'unit=$unitPath released=$released count=$count '
        'mappedReasons=${reasons.length}');
    return ReleaseReport(released, reasons);
  }

  @override
  Future<bool> resetOee(String unitPath) =>
      _request(unitPath, _HmiRequestKind.resetOee);

  @override
  Future<bool> writeConfig(String nodePath, CfgField field, String value,
      {int modelIndex = 0}) async {
    final capability = _configCapability(nodePath, field.writeKey);
    if (capability == null ||
        capability.writeRevision != field.writeRevision ||
        !capability.hasWriteCapability ||
        !capability.accepts(value)) {
      return false;
    }
    // Another model's record is not the running recipe: READY does not apply
    // to it (the PLC decides the same way).
    final model = capability.modelScoped ? modelIndex : 0;
    final root = _findModule(_owningRoot(nodePath));
    if (capability.requiresReady &&
        model == 0 &&
        root?.state != ExecState.ready) return false;
    final ok = await _request(
        _owningRoot(nodePath), _HmiRequestKind.writeConfig,
        targetPath: nodePath,
        intValue: capability.writeRevision,
        nameValue: capability.writeKey,
        textValue: value.trim(),
        durationMs: model);
    // A config write changes a slow-tier leaf; refresh it now instead of waiting
    // for the heartbeat so the operator sees the new value promptly.
    if (ok) {
      unawaited(_client.refreshSlowPaths().then((_) {}, onError: (_, __) {}));
    }
    return ok;
  }

  CfgField? _configCapability(String nodePath, String writeKey) {
    final node = _findModule(nodePath);
    if (node == null) return null;
    for (final field in node.config) {
      if (field.writeKey == writeKey) return field;
    }
    return null;
  }

  ModuleNode? _findModule(String path) {
    ModuleNode? visit(ModuleNode node) {
      if (node.path == path) return node;
      for (final child in node.children) {
        final found = visit(child);
        if (found != null) return found;
      }
      return null;
    }

    for (final root in _projection.forest) {
      final found = visit(root);
      if (found != null) return found;
    }
    return null;
  }

  @override
  Future<bool> shelveAlarm(String unitPath, String sourcePath,
          String description, Duration duration) =>
      _request(unitPath, _HmiRequestKind.shelveAlarm,
          targetPath: sourcePath,
          textValue: description,
          durationMs: duration.inMilliseconds);

  @override
  Future<bool> unshelveAlarm(
          String unitPath, String sourcePath, String description) =>
      _request(unitPath, _HmiRequestKind.unshelveAlarm,
          targetPath: sourcePath, textValue: description);

  @override
  Future<bool> forceChannel(String rootPath, String channelPath,
          {required bool force,
          bool boolValue = false,
          double analogValue = 0}) =>
      _request(rootPath, _HmiRequestKind.forceChannel,
          targetPath: channelPath,
          boolValue: force,
          textValue: boolValue ? 'true' : 'false',
          nameValue: '$analogValue');

  @override
  Future<bool> setClassLevel(String rootPath, String classId, AccessLevel level,
          {required bool forWrite}) =>
      _request(rootPath, _HmiRequestKind.setClassLevel,
          nameValue: classId, intValue: level.index, boolValue: forWrite);

  // ---- Core §3.8b parameter sets ----------------------------------------------
  // Each operation is a CONFIG_SET-gated mailbox request; the answer (the listing,
  // one export line) is published on the root and target-read right after the
  // acknowledgement - it is on-demand data, never part of the cyclic snapshot.

  Future<Map<String, Object?>> _readRootLeaves(
      String rootPath, List<String> leaves) async {
    final base = _browseBase(rootPath);
    if (base == null) return const {};
    final paths = [
      for (final path in _onDemandByScope[base] ?? const <String>[])
        if (leaves.any((leaf) => path.startsWith('$base/$leaf'))) path,
    ];
    if (paths.isEmpty) return const {};
    final session = _client;
    if (session is OpcUaBulkReadClient) {
      try {
        return await session.readValues(paths);
      } on Object {
        return const {};
      }
    }
    return {for (final path in paths) path: _values[path]};
  }

  @override
  Future<List<ConfigSetInfo>?> listConfigSets(String rootPath) async {
    final base = _browseBase(rootPath);
    if (base == null) return null;
    if (!await _request(rootPath, _HmiRequestKind.listConfigSets)) return null;
    final values = await _readRootLeaves(rootPath, const ['ConfigSet']);
    final count = _integer(values['$base/ConfigSetCount']);
    if (count < 0)
      return null; // the answer was not readable: say so, not "none"
    final sets = <ConfigSetInfo>[];
    for (var i = 1; i <= count; i++) {
      final prefix = _indexedPrefix(values, '$base/ConfigSets', i);
      if (prefix == null) continue;
      final created = values['$prefix/CreatedAt'];
      sets.add(ConfigSetInfo(
        name: '${values['$prefix/SetName'] ?? ''}',
        rootIdentity: '${values['$prefix/RootIdentity'] ?? ''}',
        kind: _enumAt(CfgKind.values, _integer(values['$prefix/Kind']),
            CfgKind.stationCfg),
        modelCode: '${values['$prefix/ModelCode'] ?? ''}',
        recordCount: _integer(values['$prefix/RecordCount']),
        configRev: _integer(values['$prefix/ConfigRev']),
        createdAt: parsePlcDateTime(created),
        timeSynchronized: values['$prefix/TimeSynchronized'] == true,
      ));
    }
    return sets;
  }

  @override
  Future<bool> saveConfigSet(String rootPath, String name, CfgKind kind) =>
      _request(rootPath, _HmiRequestKind.saveConfigSet,
          textValue: name, intValue: kind.index);

  @override
  Future<bool> loadConfigSet(String rootPath, String name) =>
      _request(rootPath, _HmiRequestKind.loadConfigSet, textValue: name);

  @override
  Future<bool> deleteConfigSet(String rootPath, String name) =>
      _request(rootPath, _HmiRequestKind.deleteConfigSet, textValue: name);

  @override
  Future<bool> createModel(String rootPath, String code,
          {int sourceModel = 0, String sourceSet = ''}) =>
      _request(rootPath, _HmiRequestKind.createModel,
          nameValue: code,
          intValue: sourceModel,
          textValue: sourceSet,
          boolValue: sourceSet.isNotEmpty);

  @override
  Future<String?> exportCurrentConfig(String rootPath, CfgKind kind,
          {int modelIndex = 0}) =>
      _export(rootPath, 'current-${kind.name}',
          kind: kind, modelIndex: modelIndex);

  @override
  Future<String?> exportConfigSet(String rootPath, String name) =>
      _export(rootPath, name);

  static final _exportRandom = Random.secure();

  Future<String?> _export(String rootPath, String name,
      {CfgKind? kind, int modelIndex = 0}) async {
    final base = _browseBase(rootPath);
    if (base == null) return null;
    final token = kind == null
        ? ''
        : List.generate(
            4,
            (_) => _exportRandom
                .nextInt(0x100000000)
                .toRadixString(16)
                .padLeft(8, '0')).join();
    final lines = <String>[];
    var total = 0;
    for (var line = 0; line <= total; line++) {
      final current = kind != null && line == 0;
      if (!await _request(
          rootPath,
          current
              ? _HmiRequestKind.exportCurrentConfig
              : _HmiRequestKind.exportConfigSet,
          textValue: name,
          nameValue: token,
          intValue: current ? kind.index : line,
          durationMs: current ? modelIndex : 0)) {
        return null; // refused - an export is never shipped with a hole
      }
      final values =
          await _readRootLeaves(rootPath, const ['ConfigSetDocument']);
      final text = '${values['$base/ConfigSetDocument'] ?? ''}';
      if (text.isEmpty) return null;
      if (line == 0) total = _integer(values['$base/ConfigSetDocumentLines']);
      if (total < 0) return null;
      lines.add(text);
    }
    return lines.join('\n');
  }

  @override
  Future<bool> importConfigSet(String rootPath, String document) async {
    final lines = document
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
    if (lines.isEmpty ||
        lines.any((line) => line.length > kConfigSetImportLineMax)) {
      return false;
    }
    for (var i = 0; i < lines.length; i++) {
      final pieces = configSetLinePieces(lines[i]);
      for (var p = 0; p < pieces.length; p++) {
        final last = p == pieces.length - 1;
        if (!await _request(rootPath, _HmiRequestKind.importConfigSet,
            textValue: pieces[p],
            intValue: last ? 0 : 1,
            boolValue: last && i == lines.length - 1)) {
          return false;
        }
      }
    }
    return true;
  }

  @override
  Future<bool> acknowledgeConfigRestore(String rootPath) =>
      _request(rootPath, _HmiRequestKind.ackConfigRestore);

  @override
  Future<String> configSetRejection(String rootPath) async {
    final base = _browseBase(rootPath);
    if (base == null) return '';
    // A refusal can precede the next cyclic snapshot. Read its named record
    // directly so the dialog explains this attempt, including over AB.
    var values = _values;
    final session = _client;
    if (session is OpcUaBulkReadClient) {
      try {
        values = {
          ...values,
          ...await session.readValues([
            '$base/ConfigPersist/LastRejectScope',
            '$base/ConfigPersist/LastRejectKey',
          ])
        };
      } on Object {
        // Retain the last available explanation when the connection drops.
      }
    }
    final scope = '${values['$base/ConfigPersist/LastRejectScope'] ?? ''}';
    final key = '${values['$base/ConfigPersist/LastRejectKey'] ?? ''}';
    return [scope, key].where((part) => part.isNotEmpty).join(' / ');
  }

  String _owningRoot(String path) {
    for (final root in _projection.forest) {
      if (path == root.path || path.startsWith('${root.path}.'))
        return root.path;
    }
    return path;
  }

  @override
  void dispose() => unawaited(_close());

  Future<void> _close() {
    if (_disposed) return Future<void>.value();
    _disposed = true;
    _invalidateOnDemand();
    _timer?.cancel();
    _freshnessTimer?.cancel();
    _forestController.close();
    _fieldbusController.close();
    _linkController.close();
    return _client.close();
  }
}

int _integer(Object? value) => value is num ? value.toInt() : -1;
double _real(Object? value) => value is num ? value.toDouble() : 0;
T _enumAt<T>(List<T> values, int index, T fallback) =>
    index >= 0 && index < values.length ? values[index] : fallback;

String? _indexedPrefix(
    Map<String, Object?> values, String base, int oneBasedIndex) {
  final separator = base.lastIndexOf('/');
  final member = separator < 0 ? base : base.substring(separator + 1);
  for (final candidate in [
    '$base/$oneBasedIndex',
    '$base[$oneBasedIndex]',
    // TF6100 inserts an ARRAY container before repeating the member browse
    // name on each element: Entries/Entries[1], Reasons/Reasons[1], and so on.
    '$base/$member[$oneBasedIndex]',
    '$base/$member/$oneBasedIndex',
    '$base/${oneBasedIndex - 1}',
    '$base[${oneBasedIndex - 1}]',
    '$base/$member[${oneBasedIndex - 1}]',
  ]) {
    if (values.keys.any((key) => key.startsWith('$candidate/')))
      return candidate;
  }
  return null;
}
