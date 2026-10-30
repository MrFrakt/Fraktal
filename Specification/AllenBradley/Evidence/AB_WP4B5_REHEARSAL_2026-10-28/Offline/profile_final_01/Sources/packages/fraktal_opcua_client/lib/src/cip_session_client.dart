library;

import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'dart:isolate';

import 'cip_manifest.dart';
import 'cip_config_read_view.dart';
import 'cip_namespace.dart';
import 'cip_publication.dart';
import 'cip_read_coherence.dart';
import 'cip_read_plan.dart';
import 'cip_read_pool.dart';
import 'cip_transport.dart';
import 'opcua_session_client.dart';

const _traceCipTiming = bool.fromEnvironment('fraktal.cip.trace');

/// Desktop canonical CIP reader. Discovery, decoding and polling run on one
/// worker isolate. Unsecured CIP has no write path, including config queries.
final class CipSessionClient
    implements
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaTieredReadClient,
        OpcUaBatchSessionClient,
        OpcUaWritePolicyClient,
        OpcUaDataValueReadClient,
        OpcUaReadOnlyConfigurationClient {
  final Isolate _isolate;
  final SendPort _worker;
  final ReceivePort _responses;
  final StreamSubscription<Object?> _subscription;
  final Map<int, Completer<Object?>> _pending = {};
  final Map<String, Object?> _endpoint;
  int _nextId = 1;
  bool _closed = false;
  CipSessionClient._(this._isolate, this._worker, this._responses,
      this._subscription, this._endpoint);
  @override
  bool get readOnly => true;

  static Future<CipSessionClient> connect(
      {required String host,
      int port = 44818,
      int slot = 0,
      String? expectSerial,
      Duration timeout = const Duration(seconds: 60)}) async {
    final responses = ReceivePort(), ready = Completer<SendPort>();
    CipSessionClient? client;
    Isolate? isolate;
    final subscription = responses.listen((message) {
      if (message is SendPort) {
        if (!ready.isCompleted) ready.complete(message);
        return;
      }
      if (message is List && message.length == 3) {
        final pending = client?._pending.remove(message[0]);
        if (pending != null) {
          if (message[1] == true)
            pending.complete(message[2]);
          else
            pending
                .completeError(OpcUaTransportException(message[2] as String));
        }
      }
    });
    try {
      isolate = await Isolate.spawn(_cipWorker, responses.sendPort,
          debugName: 'fraktal-cip');
      final worker = await ready.future.timeout(timeout);
      client = CipSessionClient._(isolate, worker, responses, subscription, {
        'host': host,
        'port': port,
        'slot': slot,
        'expectSerial': expectSerial
      });
      await client._call('connect', client._endpoint, timeout);
      return client;
    } on Object {
      await subscription.cancel();
      responses.close();
      isolate?.kill(priority: Isolate.immediate);
      rethrow;
    }
  }

  Future<Object?> _call(String operation,
      [Object? argument, Duration timeout = const Duration(seconds: 60)]) {
    if (_closed)
      return Future.error(const OpcUaTransportException('CIP client closed.'));
    final id = _nextId++, pending = Completer<Object?>();
    _pending[id] = pending;
    _worker.send([id, operation, argument]);
    return pending.future.timeout(timeout, onTimeout: () {
      _dispose(const OpcUaTransportException('CIP worker deadline exceeded.'));
      throw const OpcUaTransportException('CIP worker deadline exceeded.');
    });
  }

  Future<void> reconnect() async {
    await _call('connect', _endpoint);
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final sentUs = _traceCipTiming ? Timeline.now : null;
    final document = Map<String, Object?>.from(await _call('snapshot') as Map);
    // Trace-only delivery brackets (WP4b.3). Timeline.now is one monotonic
    // clock across isolates, so the differences need no offset handshake.
    if (sentUs != null) {
      final received = document['workerReceivedTimelineUs'],
          workerSent = document['workerSentTimelineUs'];
      if (received is int && workerSent is int) {
        document['requestDelayUs'] = received - sentUs;
        document['replyWaitUs'] = Timeline.now - workerSent;
      }
    }
    return document;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async =>
      Map<String, Object?>.from(
          (await readDataValues(browsePaths))['values'] as Map);
  @override
  Future<Map<String, Object?>> readDataValues(List<String> browsePaths) async =>
      Map<String, Object?>.from(await _call('read', browsePaths) as Map);
  @override
  Future<Map<String, Object?>?> readConfigurationPage(
      String root, int modelOrdinal) async {
    final descriptor = Map<String, Object?>.from(
        await _call('configurationDescriptor', root) as Map);
    return cipAcquireConfiguration(
        root: root,
        modelOrdinal: modelOrdinal,
        descriptor: descriptor,
        fetch: readValues,
        assemble: (values) async => Map<String, Object?>.from(await _call(
                'configurationAssemble', {
              'root': root,
              'model': modelOrdinal,
              'descriptor': descriptor,
              'values': values
            }) as Map));
  }

  @override
  Future<List<String>> discoverPaths() async =>
      List<String>.from(await _call('paths') as List);
  @override
  Future<void> setSlowPaths(Iterable<String> paths) async {
    await _call('slow', paths.toList());
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> paths) async {
    await _call('excluded', paths.toList());
  }

  @override
  Future<void> refreshSlowPaths() async {
    await _call('refresh');
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      false;
  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async => false;
  void _dispose(Object error) {
    if (_closed) return;
    _closed = true;
    _isolate.kill(priority: Isolate.immediate);
    for (final pending in _pending.values) {
      if (!pending.isCompleted) pending.completeError(error);
    }
    _pending.clear();
    unawaited(_subscription.cancel());
    _responses.close();
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    try {
      await _call('close', null, const Duration(seconds: 6));
    } finally {
      _dispose(const OpcUaTransportException('CIP client closed.'));
    }
  }
}

/// Also used by protocol qualification without an isolate. The transport can
/// be substituted by a captured-wire peer; station facts cannot be injected.
final class CipSessionEngine {
  final CipReadTransport wire;
  final CipReadPlan plan;
  final String manifestSymbol;
  final int manifestHandle;
  bool _progressProved = false;
  // The transport contract sends the discovered path vector once per
  // discovery (OPCUA_TRANSPORT.md); later snapshots carry an empty list and
  // the repository keeps the last non-empty set. A new engine — what every
  // reconnect builds through discover() — starts unsent.
  bool _pathsSent = false;
  CipSessionEngine._(
      this.wire, this.plan, this.manifestSymbol, this.manifestHandle);

  /// Offline replay seam mirroring [discover] for a captured publication (as
  /// [CipNamespace.fromCapture] shapes it): the manifest comes from the
  /// capture's decoded manifest instead of the wire, and the wire serves tag
  /// reads exactly as a live one does. Replay tests and rehearsal tooling use
  /// this; a live client always goes through [discover].
  static CipSessionEngine fromCapture(Map capture, CipReadTransport wire,
      {int Function()? clockUs, CipReadCoherenceGuard? guard}) {
    final namespace = CipNamespace.fromCapture(capture);
    final candidates = namespace.symbols.values
        .where((s) =>
            s.structured &&
            s.rank == 0 &&
            CipManifest.looksLike(namespace.templates[s.handle]!.members
                .map((m) => m['name'] as String)
                .toSet()))
        .toList();
    if (candidates.length != 1)
      throw const FormatException(
          'Exactly one canonical publication manifest is required.');
    final symbol = candidates.single;
    final manifest = CipManifest.fromNormalized(
        Map<String, Object?>.from(capture['manifest'] as Map));
    final publication = CipPublication(namespace, manifest),
        plan = CipReadPlan(publication, wire, clockUs: clockUs, guard: guard);
    plan.excludedPaths = {
      for (final s in manifest.rows('readServices'))
        s['CanonicalRoot'] as String
    };
    return CipSessionEngine._(wire, plan, symbol.name, symbol.handle);
  }

  static Future<CipSessionEngine> discover(CipReadTransport wire) async {
    try {
      final namespace = await CipNamespace.discover(wire);
      final candidates = namespace.symbols.values
          .where((s) =>
              s.structured &&
              s.rank == 0 &&
              CipManifest.looksLike(namespace.templates[s.handle]!.members
                  .map((m) => m['name'] as String)
                  .toSet()))
          .toList();
      if (candidates.length != 1)
        throw const FormatException(
            'Exactly one canonical publication manifest is required.');
      final symbol = candidates.single,
          decoder = namespace.decoderFor([symbol.handle]);
      final first =
          await namespace.readStruct(wire, symbol.name, symbol.handle);
      final second =
          await namespace.readStruct(wire, symbol.name, symbol.handle);
      if (first.length != second.length ||
          [for (var i = 0; i < first.length; i++) first[i] == second[i]]
              .any((v) => !v))
        throw const FormatException('Manifest changed during discovery.');
      final manifest = CipManifest.fromPhysical(Map<String, Object?>.from(
          decoder.decode(symbol.handle, first) as Map));
      final publication = CipPublication(namespace, manifest),
          plan = CipReadPlan(publication, wire);
      plan.excludedPaths = {
        for (final s in manifest.rows('readServices'))
          s['CanonicalRoot'] as String
      };
      return CipSessionEngine._(wire, plan, symbol.name, symbol.handle);
    } on Object {
      wire.abort();
      rethrow;
    }
  }

  Future<void> _checkManifest() async {
    final p = plan.publication;
    final valid = await CipNamespace.readExact(wire, '$manifestSymbol.Valid', 1,
        atomic: 0xc1);
    final revision =
        await CipNamespace.readDint(wire, '$manifestSymbol.ConfigRevision');
    if (valid.single == 0 || revision != p.manifest.revision) {
      wire.abort();
      throw const FormatException(
          'Canonical publication invalidated; rediscovery required.');
    }
  }

  Future<Map<String, Object?>> snapshot(
      {void Function(Map<String, Object?>)? trace,
      Stopwatch? requestClock}) async {
    final timer = Stopwatch()..start();
    final responseClock = requestClock ?? timer;
    final previousAcquisition = trace == null || plan.acquisitions.isEmpty
        ? null
        : plan.acquisitions.last;
    await _checkManifest();
    final checkedBeforeUs = timer.elapsedMicroseconds;
    if (!_progressProved) {
      if (!await plan.proveProgress())
        throw const FormatException('CIP publisher is not progressing.');
      _progressProved = true;
    }
    final progressProvedUs = timer.elapsedMicroseconds;
    await plan.acquire();
    final acquiredUs = timer.elapsedMicroseconds;
    await _checkManifest();
    final checkedAfterUs = timer.elapsedMicroseconds;
    // End the bracket before calculating ages. Projection and serialization
    // after this boundary remain part of the conservative transit allowance.
    final responseProcessingMs = responseClock.elapsedMicroseconds / 1000;
    final result = plan.snapshot(),
        samples = (result['dataValues'] as Map).values.cast<Map>();
    final projectedUs = timer.elapsedMicroseconds;
    final fastAges = [
      for (final s in samples)
        if (s['tier'] == 'fast' && s['status'] == 0) s['ageMs'] as double
    ];
    if (fastAges.isEmpty)
      throw const FormatException('No Good cyclic CIP sample.');
    final agesSelectedUs = timer.elapsedMicroseconds;
    final paths =
        _pathsSent ? const <String>[] : plan.publication.discoverPaths();
    final pathsExpandedUs = timer.elapsedMicroseconds;
    final document = <String, Object?>{
      ...result,
      'paths': paths,
      'rootChildren': plan.publication.roots.toList(),
      'namespaces': ['fraktal.ab.canonical'],
      'sampleAgeMs': fastAges.reduce((a, b) => a > b ? a : b),
      'responseProcessingMs': responseProcessingMs,
      'freshnessBudget': CipReadPlan.freshnessBudget
    };
    if (trace != null) {
      final previousIndex = previousAcquisition == null
          ? -1
          : plan.acquisitions
              .indexWhere((row) => identical(row, previousAcquisition));
      final groups = plan.acquisitions.skip(previousIndex + 1).toList();
      final slowest = List<Map<String, Object?>>.of(groups)
        ..sort((a, b) =>
            (b['acquisitionUs'] as int).compareTo(a['acquisitionUs'] as int));
      trace({
        'manifestBeforeUs': checkedBeforeUs,
        'progressProofUs': progressProvedUs - checkedBeforeUs,
        'acquireUs': acquiredUs - progressProvedUs,
        'manifestAfterUs': checkedAfterUs - acquiredUs,
        'projectionUs': projectedUs - checkedAfterUs,
        'ageSelectionUs': agesSelectedUs - projectedUs,
        if (!_pathsSent) 'pathExpansionUs': pathsExpandedUs - agesSelectedUs,
        'assemblyUs': timer.elapsedMicroseconds - pathsExpandedUs,
        'groups': groups.length,
        'groupHistoryTruncated':
            previousAcquisition != null && previousIndex < 0,
        'slowestGroups': slowest.take(8).toList(),
        if (!_pathsSent) 'pathCount': paths.length,
        if (plan.lastWalkTrace != null) 'walk': plan.lastWalkTrace!,
      });
    }
    _pathsSent = paths.isNotEmpty;
    return document;
  }

  Future<Map<String, Object?>> readValues(List<String> paths) async {
    if (paths.length > 100000 || paths.any((p) => p.length > 2048))
      throw const FormatException('Targeted read budget exceeded.');
    await _checkManifest();
    await plan.acquire(paths: paths.toSet());
    await _checkManifest();
    final snapshot = plan.snapshot(includeExcluded: true);
    bool wanted(String p) =>
        paths.any((v) => p == v || p.startsWith('$v/') || p.startsWith('$v['));
    for (final key in ['values', 'types', 'dataValues'])
      snapshot[key] = {
        for (final e in (snapshot[key] as Map).entries)
          if (wanted(e.key as String)) e.key as String: e.value
      };
    return {...snapshot, 'protocol': 'fraktal.opcua.read-values.v1'};
  }

  Map<String, Object?> configurationDescriptor(String root) {
    final descriptors = plan.publication.manifest
        .rows('readServices')
        .where((r) => r['RootSymbol'] == root)
        .toList();
    if (descriptors.length != 1)
      throw const FormatException('Configuration read service is unavailable.');
    final prefix = descriptors.single['CanonicalRoot'] as String;
    return {
      ...descriptors.single,
      for (final pair in [
        ('Definitions', 'DefinitionCapacity'),
        ('Values', 'ValueCapacity')
      ])
        pair.$2: plan.publication.fields['$prefix/${pair.$1}']!
            .annotation['elementCount']
    };
  }
}

void _cipWorker(SendPort owner) async {
  final commands = ReceivePort();
  owner.send(commands.sendPort);
  CipSessionEngine? engine;
  Future<void> tail = Future.value();
  commands.listen((message) {
    // Server processing includes time queued before acquisition, per the
    // transport envelope. The source/leaf ages still start at their own I/O.
    final requestClock = Stopwatch()..start();
    tail = tail.then((_) async {
      if (message is! List || message.length != 3) return;
      final id = message[0], operation = message[1], argument = message[2];
      final queueUs = requestClock.elapsedMicroseconds;
      if (_traceCipTiming) {
        // Observe command starvation without recording argument values or
        // changing serialization, priority, clocks or request boundaries.
        // A distinct tag keeps existing snapshot-trace parsers unchanged.
        // ignore: avoid_print
        print(jsonEncode({
          'cipOperation': 'started',
          'id': id,
          'operation': operation,
          'queueUs': queueUs,
          if (argument is List) 'paths': argument.length
        }));
      }
      final receivedTimelineUs =
          _traceCipTiming && operation == 'snapshot' ? Timeline.now : null;
      try {
        Object? result;
        if (operation == 'connect') {
          await engine?.wire.close();
          engine = null;
          final a = argument as Map;
          final wire = await CipReadPool.connect(
              host: a['host'] as String,
              port: a['port'] as int,
              slot: a['slot'] as int,
              expectSerial: a['expectSerial'] as String?);
          engine = await CipSessionEngine.discover(wire);
        } else {
          if (engine == null)
            throw const OpcUaTransportException('CIP discovery required.');
          switch (operation) {
            case 'snapshot':
              result = await engine!.snapshot(
                  requestClock: requestClock,
                  trace: _traceCipTiming
                      // Opt-in qualification stdout; normal builds omit it.
                      // ignore: avoid_print
                      ? (timing) => print(jsonEncode({
                            'cipTiming': 'snapshot',
                            'id': id,
                            'queueUs': queueUs,
                            ...timing,
                          }))
                      : null);
            case 'read':
              result =
                  await engine!.readValues(List<String>.from(argument as List));
            case 'configurationDescriptor':
              result = engine!.configurationDescriptor(argument as String);
            case 'configurationAssemble':
              final a = argument as Map, root = a['root'] as String;
              final descriptor = engine!.configurationDescriptor(root);
              if (cipCanonicalJson(descriptor) !=
                  cipCanonicalJson(a['descriptor']))
                throw const FormatException(
                    'Read service changed during acquisition.');
              result = cipConfigurationPage(
                  values: Map<String, Object?>.from(a['values'] as Map),
                  canonicalRoot: descriptor['CanonicalRoot'] as String,
                  rootSymbol: root,
                  modelOrdinal: a['model'] as int);
            case 'paths':
              result = engine!.plan.publication.discoverPaths();
            case 'slow':
              engine!.plan.slowPaths =
                  List<String>.from(argument as List).toSet();
            case 'excluded':
              engine!.plan.excludedPaths = {
                ...List<String>.from(argument as List),
                for (final s
                    in engine!.plan.publication.manifest.rows('readServices'))
                  s['CanonicalRoot'] as String
              };
            case 'refresh':
              engine!.plan.refreshSlow();
            case 'close':
              await engine!.wire.close();
              engine = null;
            default:
              throw const FormatException('Unknown CIP worker operation.');
          }
        }
        final deliveryClock = _traceCipTiming && operation == 'snapshot'
            ? (Stopwatch()..start())
            : null;
        if (_traceCipTiming && result is Map) {
          result['workerSentTimelineUs'] = Timeline.now;
          if (receivedTimelineUs != null)
            result['workerReceivedTimelineUs'] = receivedTimelineUs;
        }
        owner.send([id, true, result]);
        if (_traceCipTiming) {
          // ignore: avoid_print
          print(jsonEncode({
            'cipOperation': 'completed',
            'id': id,
            'operation': operation,
            'elapsedUs': requestClock.elapsedMicroseconds,
            'success': true
          }));
        }
        if (deliveryClock != null) {
          // Opt-in qualification stdout; normal builds omit it.
          // ignore: avoid_print
          print(jsonEncode({
            'cipTiming': 'delivery',
            'id': id,
            'sendUs': deliveryClock.elapsedMicroseconds,
          }));
        }
      } on Object catch (error) {
        if (_traceCipTiming) {
          // ignore: avoid_print
          print(jsonEncode({
            'cipOperation': 'completed',
            'id': id,
            'operation': operation,
            'elapsedUs': requestClock.elapsedMicroseconds,
            'success': false
          }));
        }
        owner.send([id, false, error.toString()]);
      }
    });
  });
}
