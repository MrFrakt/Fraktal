library;

import 'dart:async';
import 'dart:isolate';

import 'cip_manifest.dart';
import 'cip_config_read_view.dart';
import 'cip_namespace.dart';
import 'cip_publication.dart';
import 'cip_read_plan.dart';
import 'cip_transport.dart';
import 'opcua_session_client.dart';

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
  Future<Map<String, Object?>> snapshot() async =>
      Map<String, Object?>.from(await _call('snapshot') as Map);
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
  CipSessionEngine._(
      this.wire, this.plan, this.manifestSymbol, this.manifestHandle);
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

  Future<Map<String, Object?>> snapshot() async {
    final timer = Stopwatch()..start();
    await _checkManifest();
    if (!_progressProved) {
      if (!await plan.proveProgress())
        throw const FormatException('CIP publisher is not progressing.');
      _progressProved = true;
    }
    await plan.acquire();
    await _checkManifest();
    final result = plan.snapshot(),
        samples = (result['dataValues'] as Map).values.cast<Map>();
    final fastAges = [
      for (final s in samples)
        if (s['tier'] == 'fast' && s['status'] == 0) s['ageMs'] as double
    ];
    if (fastAges.isEmpty)
      throw const FormatException('No Good cyclic CIP sample.');
    return {
      ...result,
      'paths': plan.publication.discoverPaths(),
      'rootChildren': plan.publication.roots.toList(),
      'namespaces': ['fraktal.ab.canonical'],
      'sampleAgeMs': fastAges.reduce((a, b) => a > b ? a : b),
      'responseProcessingMs': timer.elapsedMicroseconds / 1000,
      'freshnessBudget': CipReadPlan.freshnessBudget
    };
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
    tail = tail.then((_) async {
      if (message is! List || message.length != 3) return;
      final id = message[0], operation = message[1], argument = message[2];
      try {
        Object? result;
        if (operation == 'connect') {
          await engine?.wire.close();
          engine = null;
          final a = argument as Map;
          final wire = await CipSocketTransport.connect(
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
              result = await engine!.snapshot();
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
        owner.send([id, true, result]);
      } on Object catch (error) {
        owner.send([id, false, error.toString()]);
      }
    });
  });
}
