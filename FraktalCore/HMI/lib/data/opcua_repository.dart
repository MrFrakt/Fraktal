library;

import 'dart:async';
import 'package:flutter/foundation.dart';
import '../domain/fieldbus.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import 'opcua_config_manifest.dart';
import 'opcua_field_tier.dart';
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
  // ignore: unused_field
  saveConfigSet,
  // ignore: unused_field
  loadConfigSet,
  // ignore: unused_field
  listConfigSets,
  // ignore: unused_field
  ackConfigRestore,
  // ignore: unused_field
  exportConfigSet,
  // ignore: unused_field
  importConfigSet,
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
  List<String> _lastTierPaths = const [];
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
      // The native worker executes one operation at a time, so a full-tree
      // snapshot (hundreds of ms) queued ahead of a command's ack poll makes
      // button presses feel laggy. Yield the periodic refresh while an
      // interactive request or the manifest fetch is in flight — each finishes
      // with its own refresh, so the live view stays current without competing
      // for the worker against the operation the operator is waiting on.
      repository._timer = Timer.periodic(refreshInterval, (_) {
        if (repository._manifestFetchInFlight ||
            repository._interactiveInFlight > 0) {
          return;
        }
        repository._refresh();
      });
      return repository;
    } on Object {
      await client.close();
      rethrow;
    }
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
      final document = await _client.snapshot();
      validateCompleteOpcUaSnapshot(document);
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
      final onDemandOverlay = await _readActiveOnDemand();
      // §3.10.2 — overlay the hydrated config manifest UNDER the live snapshot
      // so the mapper sees the same flat tree a full publication would give
      // (live values win on any collision). _values stays raw: mailbox reads
      // and the slow-path tier must only ever see real published nodes.
      final merged = <String, Object?>{
        ..._manifestValues,
        if (onDemandOverlay != null) ...onDemandOverlay,
        ..._values,
      };
      _projection = _mapper.map(
          onDemandOverlay == null && _manifestValues.isEmpty
              ? document
              : <String, Object?>{...document, 'values': merged},
          configByModulePath: _manifestConfigByModule);
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
      // Same race as _setLink: this refresh may have been disposed across one of
      // the awaits above (snapshot / on-demand read / manifest hydration).
      if (_disposed) return;
      _forestController.add(_projection.forest);
      _fieldbusController.add(_projection.fieldbus);
    } on Object catch (error) {
      final age = DateTime.now().difference(_lastGood);
      _setLink(
          age >= const Duration(seconds: 5) ? LinkState.down : LinkState.stale);
      debugPrint(
          '[Fraktal/Connection] stage=opcua-refresh-failed error=$error');
      if (propagateFailure) rethrow;
    }
  }

  // Classify the FULL discovered contract (emitted once per discovery as
  // `paths`) and push the excluded (on-demand) set to the native client. These
  // paths are never read in the cyclic snapshot — only when their owning view
  // activates the scope. Every non-excluded, non-config leaf is fast (live).
  // Re-runs only when the discovered node count changes (first snapshot, online
  // change, reconnect). The classifier runs over `paths`, not `_values`, since
  // excluded paths are absent from the snapshot values.
  void _maybeUpdatePathTiers() {
    if (listEquals(_lastTierPaths, _discoveredPaths)) return;
    _lastTierPaths = List.unmodifiable(_discoveredPaths);
    if (_discoveredPaths.isEmpty) return;
    final roots = _projection.browsePathByModulePath.values;
    final slow = <String>[];
    final excluded = <String>[];
    final onDemandByScope = <String, List<String>>{};
    for (final path in _discoveredPaths) {
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
          final scope = OpcUaFieldTier.onDemandScopeOf(path, roots);
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
    debugPrint('[Fraktal/Connection] stage=opcua-read-tiers '
        'discovered=${_discoveredPaths.length} '
        'fast=${_discoveredPaths.length - slow.length - excluded.length} '
        'slow=${slow.length} onDemand=${excluded.length} '
        'scopes=${onDemandByScope.length}');
    unawaited(_client.setSlowPaths(slow).then((_) {}, onError: (_, __) {}));
    unawaited(
        _client.setExcludedPaths(excluded).then((_) {}, onError: (_, __) {}));
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
  void setModuleDetailActive(String rootPath, bool active) {
    final base = _browseBase(rootPath);
    if (base != null) _setOnDemandScopeActive(base, active);
  }

  /// Activates an on-demand data scope so the repository target-reads its paths
  /// each refresh (e.g. while the fieldbus diagnostic page is visible). A scope
  /// that is not active is never read cyclically.
  void _setOnDemandScopeActive(String scope, bool active) {
    final changed = active
        ? _activeOnDemandScopes.add(scope)
        : _activeOnDemandScopes.remove(scope);
    if (changed) unawaited(_refresh());
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

  /// Target-reads the excluded paths of every active on-demand scope in one
  /// batch (bulk-read capable clients only), returning them for the snapshot
  /// overlay. Null when nothing is active or the client cannot bulk-read (the
  /// gateway keeps publishing these paths cyclically, so no overlay is needed).
  Future<Map<String, Object?>?> _readActiveOnDemand() async {
    if (_activeOnDemandScopes.isEmpty) return null;
    final session = _client;
    if (session is! OpcUaBulkReadClient) return null;
    final paths = <String>[
      for (final scope in _activeOnDemandScopes) ...?_onDemandByScope[scope],
    ];
    if (paths.isEmpty) return null;
    try {
      return await session.readValues(paths);
    } on Object {
      return null; // a failed on-demand read degrades to no overlay, not a fault
    }
  }

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
        final accepted = await _request(root.path, _HmiRequestKind.queryConfig,
            intValue: page, ackTimeout: const Duration(seconds: 10));
        if (!accepted) {
          debugPrint('[Fraktal/Connection] stage=config-manifest-failed '
              'root=${root.path} page=$page');
          _manifestRetryAfter = DateTime.now().add(const Duration(seconds: 5));
          return; // signature not stored -> retried after the backoff
        }
        pageCount = _integer(_values['$pageBase/PageCount']);
        final entryCount = _integer(_values['$pageBase/EntryCount']);
        for (var i = 1; i <= entryCount; i++) {
          final prefix = _indexedPrefix(_values, '$pageBase/Entries', i);
          if (prefix == null) continue;
          entries.add(ConfigManifestEntry(
            '${_values['$prefix/Scope'] ?? ''}',
            '${_values['$prefix/Item'] ?? ''}',
            '${_values['$prefix/ValueText'] ?? ''}',
            writeKey: '${_values['$prefix/WriteKey'] ?? ''}',
            writeRevision: _integer(_values['$prefix/WriteRevision']),
            configKind: _integer(_values['$prefix/ConfigKind']),
            valueType: _integer(_values['$prefix/ValueType']),
            writable: _values['$prefix/Writable'] == true,
            requiresReady: _values['$prefix/RequiresReady'] == true,
            hasMinimum: _values['$prefix/HasMinimum'] == true,
            hasMaximum: _values['$prefix/HasMaximum'] == true,
            minimum: _real(_values['$prefix/Minimum']),
            maximum: _real(_values['$prefix/Maximum']),
            unit: '${_values['$prefix/Unit'] ?? ''}',
            labelKey: '${_values['$prefix/LabelKey'] ?? ''}',
            enumDomain: '${_values['$prefix/EnumDomain'] ?? ''}',
          ));
        }
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

  @override
  Stream<List<ModuleNode>> forest() async* {
    yield _projection.forest;
    yield* _forestController.stream;
  }

  @override
  Stream<List<BusNode>> fieldbus() async* {
    yield _projection.fieldbus;
    yield* _fieldbusController.stream;
  }

  @override
  Stream<LinkState> linkState() async* {
    yield _link;
    yield* _linkController.stream;
  }

  String? _browseBase(String modulePath) =>
      _projection.browsePathByModulePath[modulePath];

  Future<bool> _write(String path, OpcUaWriteType type, Object value) async {
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
  }) {
    // Operator commands mark the repository interactive so the periodic refresh
    // yields the worker; the background manifest fetch (queryConfig) is already
    // gated by _manifestFetchInFlight and must not double-count here.
    final interactive = kind != _HmiRequestKind.queryConfig;
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
        ));
      } on Object catch (error, stackTrace) {
        result.completeError(error, stackTrace);
      } finally {
        if (interactive) _interactiveInFlight--;
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
  }) async {
    final base = _browseBase(unitPath);
    if (base == null || _link != LinkState.live) {
      debugPrint('[Fraktal/Connection] stage=opcua-request-unavailable '
          'kind=${kind.name} unit=$unitPath link=${_link.name}');
      return false;
    }
    final request = '$base/HmiRequest';
    final observedRequest = _integer(_values['$request/Sequence']);
    final observedAck = _integer(_values['$base/HmiResponse/AckSequence']);
    final previous = _requestSequenceByMailbox.putIfAbsent(
      request,
      () => observedRequest > observedAck ? observedRequest : observedAck,
    );
    // Reserve before the attempt. If the connection is lost after commit, the
    // outcome is ambiguous and this sequence must never be reused or replayed.
    final sequence = (previous + 1) & 0xffffffff;
    _requestSequenceByMailbox[request] = sequence;
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
        if (bulk != null && accepted) {
          final followUp = _ackFollowUpPaths(kind, base);
          if (followUp.isNotEmpty) {
            try {
              final extra = await bulk.readValues(followUp);
              if (extra.isNotEmpty) _values = {..._values, ...extra};
            } on Object {
              // Consumers degrade to the last snapshot's values.
            }
          }
        }
        await _write(
            '$request/Kind', OpcUaWriteType.int32, _HmiRequestKind.none.index);
        return accepted;
      }
      await Future<void>.delayed(
          Duration(milliseconds: bulk != null ? 20 : 30));
    }
    debugPrint('[Fraktal/Connection] stage=opcua-request-timeout '
        'kind=${kind.name} sequence=$sequence');
    return false;
  }

  @override
  Future<bool> login(String rootPath, String user, String secret) async {
    // A LOGIN mailbox acknowledgement means the PLC consumed the request; it
    // does not mean the access provider accepted the credentials. The access
    // manager publishes the authoritative outcome immediately afterward.
    final consumed = await _request(
      rootPath,
      _HmiRequestKind.login,
      user: user,
      secret: secret,
    );
    if (!consumed) return false;
    await Future<void>.delayed(const Duration(milliseconds: 30));
    await _refresh();
    final base = _browseBase(rootPath);
    if (base == null) return false;
    final failed = _values['$base/Access/LoginFailed'] == true;
    final level = _integer(_values['$base/Access/CurrentLevel']);
    final currentUser = '${_values['$base/Access/CurrentUser'] ?? ''}';
    final authenticated =
        !failed && level > AccessLevel.none.index && currentUser == user;
    debugPrint('[Fraktal/Connection] stage=opcua-login-result '
        'authenticated=$authenticated level=$level loginFailed=$failed');
    return authenticated;
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

  /// Response-payload paths a fast-path acknowledgement must re-read so the
  /// consumer parses THIS request's data (uses the server's double-segment
  /// array naming, `Reasons/Reasons[1]`, `Entries/Entries[1]`).
  List<String> _ackFollowUpPaths(_HmiRequestKind kind, String base) {
    switch (kind) {
      case _HmiRequestKind.releaseStart:
      case _HmiRequestKind.releaseManual:
      case _HmiRequestKind.releaseAction:
        final report = '$base/HmiResponse/Report';
        return [
          '$report/Released',
          '$report/Count',
          for (var i = 1; i <= 24; i++) ...[
            '$report/Reasons/Reasons[$i]/Description',
            '$report/Reasons/Reasons[$i]/ReasonCode',
            '$report/Reasons/Reasons[$i]/SourcePath',
            '$report/Reasons/Reasons[$i]/Kind',
            '$report/Reasons/Reasons[$i]/Bypassable',
          ],
        ];
      case _HmiRequestKind.queryConfig:
        final page = '$base/HmiResponse/ConfigPage';
        return [
          '$page/Revision',
          '$page/PageIndex',
          '$page/PageCount',
          '$page/EntryCount',
          for (var i = 1; i <= kManifestPageEntries; i++) ...[
            '$page/Entries/Entries[$i]/Scope',
            '$page/Entries/Entries[$i]/Item',
            '$page/Entries/Entries[$i]/ValueText',
          ],
        ];
      default:
        return const [];
    }
  }

  ReleaseReport _readReleaseReport(String unitPath, bool requestAccepted) {
    final base = _browseBase(unitPath);
    if (base == null || !requestAccepted) {
      return const ReleaseReport(false, [
        ReleaseReason('std.release.transportUnavailable', ReleaseKind.other),
      ]);
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
  Future<bool> writeConfig(
      String nodePath, CfgField field, String value) async {
    final capability = _configCapability(nodePath, field.writeKey);
    if (capability == null ||
        capability.writeRevision != field.writeRevision ||
        !capability.hasWriteCapability ||
        !capability.accepts(value)) {
      return false;
    }
    final root = _findModule(_owningRoot(nodePath));
    if (capability.requiresReady && root?.state != ExecState.ready)
      return false;
    final ok = await _request(
        _owningRoot(nodePath), _HmiRequestKind.writeConfig,
        targetPath: nodePath,
        intValue: capability.writeRevision,
        nameValue: capability.writeKey,
        textValue: value.trim());
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

  String _owningRoot(String path) {
    for (final root in _projection.forest) {
      if (path == root.path || path.startsWith('${root.path}.'))
        return root.path;
    }
    return path;
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _timer?.cancel();
    unawaited(_client.close());
    _forestController.close();
    _fieldbusController.close();
    _linkController.close();
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
