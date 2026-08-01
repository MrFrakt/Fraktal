library;

import 'dart:async';
import 'dart:math';

import 'opcua_session_client.dart';

typedef OpcUaSessionFactory = Future<OpcUaSessionClient> Function();
typedef ReconnectLog = void Function(String message);

/// Keeps a gateway session self-healing without ever replaying a write.
///
/// Snapshots are safe to retry on a newly authenticated socket. Writes are
/// attempted on the current generation exactly once; a transport failure makes
/// their outcome unknown and invalidates that generation. The repository's
/// next snapshot drives reconnect and must become fresh before writes resume.
class ReconnectingOpcUaSessionClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaTieredReadClient {
  final OpcUaSessionFactory _factory;
  final Duration baseBackoff;
  final Duration maxBackoff;
  final Random _random;
  final DateTime Function() _now;
  final ReconnectLog _log;

  OpcUaSessionClient? _active;
  List<String>? _slowPaths; // re-applied to each freshly connected session
  List<String>? _excludedPaths; // re-applied to each freshly connected session
  Future<OpcUaSessionClient>? _connecting;
  DateTime _nextAttempt = DateTime.fromMillisecondsSinceEpoch(0);
  int _consecutiveFailures = 0;
  int _generation = 1;
  bool _closed = false;

  ReconnectingOpcUaSessionClient._({
    required OpcUaSessionFactory factory,
    required OpcUaSessionClient initial,
    required this.baseBackoff,
    required this.maxBackoff,
    required Random random,
    required DateTime Function() now,
    required ReconnectLog log,
  })  : _factory = factory,
        _active = initial,
        _random = random,
        _now = now,
        _log = log;

  static Future<ReconnectingOpcUaSessionClient> connect({
    required OpcUaSessionFactory factory,
    Duration baseBackoff = const Duration(milliseconds: 250),
    Duration maxBackoff = const Duration(seconds: 5),
    Random? random,
    DateTime Function()? now,
    ReconnectLog? log,
  }) async {
    if (baseBackoff <= Duration.zero || maxBackoff < baseBackoff) {
      throw ArgumentError('Reconnect backoff range is invalid.');
    }
    final initial = await factory();
    return ReconnectingOpcUaSessionClient._(
      factory: factory,
      initial: initial,
      baseBackoff: baseBackoff,
      maxBackoff: maxBackoff,
      random: random ?? Random(),
      now: now ?? DateTime.now,
      log: log ?? (_) {},
    );
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final session = await _sessionForSnapshot();
    try {
      final result = await session.snapshot();
      if (identical(_active, session)) {
        if (_consecutiveFailures != 0) {
          _log('[Fraktal/Connection] stage=gateway-reconnected '
              'generation=$_generation');
        }
        _consecutiveFailures = 0;
        _nextAttempt = DateTime.fromMillisecondsSinceEpoch(0);
      }
      return result;
    } on OpcUaTransportException catch (error) {
      await _invalidate(session, error);
      rethrow;
    }
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) =>
      _writeOnce((session) => session.write(path, type, value));

  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) =>
      _writeOnce((session) => session.writeBatch(writes));

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    final session = _active;
    if (_closed || session == null) {
      throw const OpcUaTransportException(
        'Gateway is reconnecting; targeted reads are not queued.',
      );
    }
    if (session is! OpcUaBulkReadClient) return const {};
    try {
      return await session.readValues(browsePaths);
    } on OpcUaTransportException catch (error) {
      await _invalidate(session, error);
      rethrow;
    }
  }

  @override
  Future<List<String>> discoverPaths() async {
    final session = await _sessionForSnapshot();
    if (session is OpcUaPathDiscoveryClient) {
      try {
        return await session.discoverPaths();
      } on OpcUaTransportException catch (error) {
        await _invalidate(session, error);
        rethrow;
      }
    }
    final document = await snapshot();
    final paths = document['paths'];
    if (paths is! List) return const [];
    return [for (final path in paths) '$path'];
  }

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    final paths = browsePaths.toList(growable: false);
    _slowPaths = paths;
    await _active?.setSlowPaths(paths);
  }

  @override
  Future<void> refreshSlowPaths() async {
    await _active?.refreshSlowPaths();
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    final paths = browsePaths.toList(growable: false);
    _excludedPaths = paths;
    await _active?.setExcludedPaths(paths);
  }

  Future<bool> _writeOnce(
    Future<bool> Function(OpcUaSessionClient session) operation,
  ) async {
    if (_closed) {
      throw const OpcUaTransportException('Gateway session is closed.');
    }
    final session = _active;
    if (session == null) {
      throw const OpcUaTransportException(
        'Gateway is reconnecting; writes are not queued.',
      );
    }
    try {
      return await operation(session);
    } on OpcUaTransportException catch (error) {
      await _invalidate(session, error);
      rethrow;
    }
  }

  Future<OpcUaSessionClient> _sessionForSnapshot() async {
    if (_closed) {
      throw const OpcUaTransportException('Gateway session is closed.');
    }
    final active = _active;
    if (active != null) return active;
    final connecting = _connecting;
    if (connecting != null) return connecting;
    final remaining = _nextAttempt.difference(_now());
    if (remaining > Duration.zero) {
      throw OpcUaTransportException(
        'Gateway reconnect backoff active for ${remaining.inMilliseconds} ms.',
      );
    }

    final attemptGeneration = _generation + 1;
    _log('[Fraktal/Connection] stage=gateway-reconnect-attempt '
        'generation=$attemptGeneration attempt=${_consecutiveFailures + 1}');
    final future = _factory();
    _connecting = future;
    try {
      final session = await future;
      if (_closed) {
        await session.close();
        throw const OpcUaTransportException(
          'Gateway client closed during reconnect.',
        );
      }
      _active = session;
      _generation = attemptGeneration;
      // A freshly connected session starts reading everything; restore the tier.
      final slow = _slowPaths;
      if (slow != null) {
        unawaited(session.setSlowPaths(slow).then((_) {}, onError: (_, __) {}));
      }
      final excluded = _excludedPaths;
      if (excluded != null) {
        unawaited(session
            .setExcludedPaths(excluded)
            .then((_) {}, onError: (_, __) {}));
      }
      return session;
    } on Object catch (error) {
      _recordFailure(error);
      if (error is OpcUaTransportException) rethrow;
      throw OpcUaTransportException('Gateway reconnect failed.', error);
    } finally {
      if (identical(_connecting, future)) _connecting = null;
    }
  }

  Future<void> _invalidate(
    OpcUaSessionClient session,
    Object error,
  ) async {
    if (!identical(_active, session)) return;
    _active = null;
    _recordFailure(error);
    try {
      await session.close().timeout(const Duration(seconds: 2));
    } on Object {
      // The failed generation is already detached and cannot be reused.
    }
  }

  void _recordFailure(Object error) {
    _consecutiveFailures++;
    final exponent = min(_consecutiveFailures - 1, 20);
    final uncapped = baseBackoff.inMilliseconds * (1 << exponent);
    final capped = min(uncapped, maxBackoff.inMilliseconds);
    final jittered =
        max(1, (capped * (0.75 + _random.nextDouble() * 0.5)).round());
    _nextAttempt = _now().add(Duration(milliseconds: jittered));
    _log('[Fraktal/Connection] stage=gateway-disconnected '
        'generation=$_generation retryInMs=$jittered error=$error');
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    final active = _active;
    _active = null;
    if (active != null) await active.close();
    final connecting = _connecting;
    if (connecting != null) {
      try {
        final lateSession =
            await connecting.timeout(const Duration(seconds: 2));
        await lateSession.close();
      } on Object {
        // The factory owns cleanup when connection establishment itself fails.
      }
    }
  }
}
