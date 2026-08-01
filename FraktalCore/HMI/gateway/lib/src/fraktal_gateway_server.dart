library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/opcua_session_client.dart';

const String kFraktalGatewayProtocol = 'fraktal.opcua.gateway.v1';
const int _maxRequestBytes = 256 * 1024;
const int _maxStringValueLength = 8192;
const int _maxBatchWrites = 32;
const int _maxTargetReadPaths = 512;
const int _maxTierIndices = 20000;

typedef GatewayLog = void Function(String message);

/// Deployment policy for the browser-to-OPC-UA gateway.
///
/// The server is deliberately loopback-only. A remote browser reaches it
/// through a same-host reverse proxy that owns TLS and authentication. Origin
/// checks remain here as a second, application-layer boundary.
class FraktalGatewayConfig {
  final InternetAddress address;
  final int port;
  final String webSocketPath;
  final Set<String> allowedOrigins;
  final Set<String> readRoots;
  final Set<String> writeRoots;
  final bool allowAllRootMailboxes;
  final bool initialPlcReady;
  final Duration socketPingInterval;
  final Directory? webRoot;

  FraktalGatewayConfig({
    InternetAddress? address,
    this.port = 8080,
    this.webSocketPath = '/fraktal',
    Set<String> allowedOrigins = const {},
    Set<String> readRoots = const {},
    Set<String> writeRoots = const {},
    this.allowAllRootMailboxes = false,
    this.initialPlcReady = false,
    this.socketPingInterval = const Duration(seconds: 2),
    Directory? webRoot,
  })  : address = address ?? InternetAddress.loopbackIPv4,
        webRoot = _canonicalWebRoot(webRoot),
        allowedOrigins = Set.unmodifiable(
          allowedOrigins.map(_normalizeOrigin),
        ),
        readRoots = Set.unmodifiable(
          readRoots.map(_normalizeBrowseRoot),
        ),
        writeRoots = Set.unmodifiable(
          writeRoots.map(_normalizeBrowseRoot),
        ) {
    if (!this.address.isLoopback) {
      throw ArgumentError.value(
        this.address.address,
        'address',
        'The gateway is loopback-only. Use an authenticated TLS reverse proxy '
            'for remote browsers.',
      );
    }
    if (port < 0 || port > 65535) {
      throw RangeError.range(port, 0, 65535, 'port');
    }
    if (socketPingInterval <= Duration.zero) {
      throw ArgumentError.value(
        socketPingInterval,
        'socketPingInterval',
        'WebSocket heartbeat interval must be positive.',
      );
    }
    if (!webSocketPath.startsWith('/') ||
        webSocketPath.contains('?') ||
        webSocketPath.contains('#')) {
      throw ArgumentError.value(
        webSocketPath,
        'webSocketPath',
        'Expected an absolute path without query or fragment.',
      );
    }
  }

  bool acceptsOrigin(String? value) {
    if (value == null || value == 'null') return false;
    Uri origin;
    try {
      origin = Uri.parse(value);
    } on FormatException {
      return false;
    }
    if (origin.scheme != 'http' && origin.scheme != 'https') return false;
    if (origin.path.isNotEmpty && origin.path != '/' ||
        origin.hasQuery ||
        origin.hasFragment ||
        origin.host.isEmpty) {
      return false;
    }
    final normalized = _normalizeOrigin(value);
    if (allowedOrigins.contains(normalized)) return true;
    return _isLoopbackHost(origin.host);
  }

  bool permitsWrite(String path) {
    final parts = path.split('/');
    final mailbox = parts.lastIndexOf('HmiRequest');
    if (mailbox <= 0 || mailbox >= parts.length - 1) return false;
    if (parts.any((part) => part.isEmpty || part == '.' || part == '..')) {
      return false;
    }
    if (writeRoots.isEmpty) return allowAllRootMailboxes;
    final root = parts.take(mailbox).join('/');
    return writeRoots.contains(root);
  }

  /// Read scoping is optional because the upstream OPC UA/ADS identity remains
  /// the primary browse authorization boundary. When configured, it is exact
  /// and applies to snapshots, discovery, tier setup, and targeted reads.
  bool permitsRead(String path) {
    if (!_validBrowsePath(path)) return false;
    if (readRoots.isEmpty) return true;
    return readRoots.any(
      (root) => path == root || path.startsWith('$root/'),
    );
  }
}

/// A standalone WebSocket gateway sharing one native OPC UA session across
/// browser clients. Writes are globally serialized and are attempted once.
class FraktalGatewayServer {
  final OpcUaSessionClient _client;
  final FraktalGatewayConfig config;
  final GatewayLog _log;
  final Set<WebSocket> _sockets = {};
  final Map<WebSocket, _SocketReadProfile> _readProfiles = {};

  HttpServer? _server;
  Future<void> _writeTail = Future<void>.value();
  Future<void> _tierTail = Future<void>.value();
  final Map<String, int> _lastCommittedSequenceByMailbox = {};
  List<String> _discoveredPaths = const [];
  int _discoveryRevision = 0;
  bool _closing = false;
  bool _plcReady;
  DateTime? _lastOpcUaSuccess;
  Object? _lastOpcUaFailure;

  FraktalGatewayServer(
    this._client, {
    required this.config,
    GatewayLog? log,
  })  : _plcReady = config.initialPlcReady,
        _log = log ?? _discardLog;

  int get port => _server?.port ?? config.port;

  Future<void> start() async {
    if (_server != null) throw StateError('Gateway is already running.');
    final server = await HttpServer.bind(config.address, config.port);
    _server = server;
    server.listen(
      (request) => unawaited(_handleHttp(request)),
      onError: (Object error, StackTrace stackTrace) {
        _log('[Fraktal/Gateway] stage=http-error error=$error');
      },
    );
    _log('[Fraktal/Gateway] stage=listen '
        'address=${config.address.address} port=${server.port} '
        'path=${config.webSocketPath} '
        'webRoot=${config.webRoot?.path ?? '-'}');
  }

  Future<void> _handleHttp(HttpRequest request) async {
    if (request.method == 'GET' &&
        const {'/healthz', '/livez', '/readyz'}.contains(request.uri.path)) {
      final isLiveness = request.uri.path == '/livez';
      final isReadiness = request.uri.path == '/readyz';
      final ready = !_closing && _plcReady;
      if (isReadiness && !ready) {
        request.response.statusCode = HttpStatus.serviceUnavailable;
      }
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode({
        'protocol': kFraktalGatewayProtocol,
        'status': _closing
            ? 'stopping'
            : isLiveness
                ? 'live'
                : ready
                    ? 'ready'
                    : 'degraded',
        'plcReady': _plcReady,
        if (_lastOpcUaSuccess != null)
          'lastOpcUaSuccess': _lastOpcUaSuccess!.toUtc().toIso8601String(),
        if (_lastOpcUaFailure != null)
          'lastOpcUaFailure': _lastOpcUaFailure.toString(),
      }));
      await request.response.close();
      return;
    }

    if (request.uri.path != config.webSocketPath ||
        !WebSocketTransformer.isUpgradeRequest(request)) {
      if (config.webRoot != null &&
          request.uri.path != config.webSocketPath &&
          (request.method == 'GET' || request.method == 'HEAD')) {
        await _serveWebAsset(request, config.webRoot!);
        return;
      }
      request.response.statusCode = HttpStatus.notFound;
      await request.response.close();
      return;
    }

    final origin = request.headers.value('origin');
    if (!config.acceptsOrigin(origin)) {
      _log('[Fraktal/Gateway] stage=upgrade-refused reason=origin');
      request.response.statusCode = HttpStatus.forbidden;
      request.response.write('WebSocket origin is not allowed.');
      await request.response.close();
      return;
    }

    try {
      final socket = await WebSocketTransformer.upgrade(request);
      socket.pingInterval = config.socketPingInterval;
      _sockets.add(socket);
      _readProfiles[socket] = _SocketReadProfile();
      unawaited(_queueAggregateTiers().then(
        (_) {},
        onError: (Object error, StackTrace stackTrace) {
          _log('[Fraktal/Gateway] stage=read-tier-reset-failed error=$error');
        },
      ));
      _serveSocket(socket);
    } on Object catch (error) {
      _log('[Fraktal/Gateway] stage=upgrade-failed error=$error');
    }
  }

  Future<void> _serveWebAsset(HttpRequest request, Directory root) async {
    File? asset;
    try {
      asset = _resolveWebAsset(root, request.uri);
    } on FormatException {
      request.response.statusCode = HttpStatus.badRequest;
      await request.response.close();
      return;
    }
    if (asset == null) {
      request.response.statusCode = HttpStatus.notFound;
      await request.response.close();
      return;
    }
    request.response.headers
      ..set('X-Content-Type-Options', 'nosniff')
      ..set('Referrer-Policy', 'no-referrer')
      ..set('X-Frame-Options', 'DENY')
      ..set(
        HttpHeaders.cacheControlHeader,
        asset.uri.pathSegments.last == 'index.html'
            ? 'no-cache'
            : 'public, max-age=3600',
      )
      ..contentType = _webContentType(asset.path);
    final length = await asset.length();
    request.response.contentLength = length;
    if (request.method == 'GET') {
      await request.response.addStream(asset.openRead());
    }
    await request.response.close();
  }

  void _serveSocket(WebSocket socket) {
    Future<void> requestTail = Future<void>.value();
    socket.listen(
      (message) {
        requestTail = requestTail
            .then((_) => _handleMessage(socket, message))
            .onError((Object error, StackTrace stackTrace) {
          _log('[Fraktal/Gateway] stage=request-error error=$error');
        });
      },
      onError: (Object error, StackTrace stackTrace) {
        _log('[Fraktal/Gateway] stage=socket-error error=$error');
      },
      onDone: () {
        _sockets.remove(socket);
        _readProfiles.remove(socket);
        unawaited(_queueAggregateTiers().then(
          (_) {},
          onError: (Object error, StackTrace stackTrace) {
            _log(
                '[Fraktal/Gateway] stage=read-tier-update-failed error=$error');
          },
        ));
        _log('[Fraktal/Gateway] stage=socket-closed '
            'code=${socket.closeCode} reason=${socket.closeReason ?? '-'}');
      },
      cancelOnError: true,
    );
  }

  Future<void> _handleMessage(WebSocket socket, Object? message) async {
    if (_closing) {
      _sendError(socket, null, 'Gateway is stopping.');
      return;
    }
    if (message is! String) {
      _sendError(socket, null, 'Binary requests are not supported.');
      return;
    }
    if (utf8.encode(message).length > _maxRequestBytes) {
      _sendError(socket, null, 'Request exceeds the 256 KiB limit.');
      await socket.close(WebSocketStatus.messageTooBig, 'Request too large');
      return;
    }

    Object? decoded;
    try {
      decoded = jsonDecode(message);
    } on FormatException {
      _sendError(socket, null, 'Request is not valid JSON.');
      return;
    }
    if (decoded is! Map) {
      _sendError(socket, null, 'Request must be a JSON object.');
      return;
    }
    final request = Map<Object?, Object?>.from(decoded);
    final id = request['id'];
    if (id is! int || id < 0 || id > 0x7fffffff) {
      _sendError(socket, null, 'Request id must be a non-negative integer.');
      return;
    }
    if (request['protocol'] != kFraktalGatewayProtocol) {
      _sendError(socket, id, 'Unsupported gateway protocol.');
      return;
    }
    final parameters = request['params'];
    if (parameters is! Map) {
      _sendError(socket, id, 'Request params must be an object.');
      return;
    }

    switch (request['method']) {
      case 'snapshot':
        await _snapshot(socket, id);
      case 'discoverPaths':
        await _discoverPaths(socket, id);
      case 'setReadTiers':
        await _setReadTiers(
          socket,
          id,
          Map<Object?, Object?>.from(parameters),
        );
      case 'readValues':
        await _readValues(
          socket,
          id,
          Map<Object?, Object?>.from(parameters),
        );
      case 'write':
        await _write(socket, id, Map<Object?, Object?>.from(parameters));
      case 'writeBatch':
        await _writeBatch(socket, id, Map<Object?, Object?>.from(parameters));
      default:
        _sendError(socket, id, 'Unsupported gateway method.');
    }
  }

  Future<void> _snapshot(WebSocket socket, int id) async {
    try {
      await _tierTail;
      final snapshot = await _client.snapshot();
      validateCompleteOpcUaSnapshot(snapshot);
      _rememberDiscovery(snapshot);
      _markOpcUaSuccess();
      _seedMailboxSequences(snapshot);
      _sendResult(socket, id, _projectSnapshot(snapshot, socket));
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA snapshot failed: $error');
    }
  }

  Future<void> _discoverPaths(WebSocket socket, int id) async {
    try {
      await _ensureDiscovery();
      final allowed = _allowedDiscoveredPaths();
      _sendResult(socket, id, {
        'revision': _discoveryRevision,
        'nodeCount': allowed.length,
        'paths': allowed,
      });
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA discovery failed: $error');
    }
  }

  Future<void> _setReadTiers(
    WebSocket socket,
    int id,
    Map<Object?, Object?> parameters,
  ) async {
    try {
      await _ensureDiscovery();
      final revision = parameters['revision'];
      if (revision != _discoveryRevision) {
        throw const FormatException(
          'Discovery revision is stale; discover paths again.',
        );
      }
      final allowed = _allowedDiscoveredPaths();
      final slow = _validatePathIndices(parameters['slow'], allowed.length);
      final excluded =
          _validatePathIndices(parameters['excluded'], allowed.length);
      if (slow.any(excluded.contains)) {
        throw const FormatException(
          'A browse path cannot be both slow and excluded.',
        );
      }
      final profile = _readProfiles[socket];
      if (profile == null) {
        throw const FormatException('WebSocket read profile is unavailable.');
      }
      profile
        ..configured = true
        ..slowPaths = {for (final index in slow) allowed[index]}
        ..excludedPaths = {for (final index in excluded) allowed[index]};
      await _queueAggregateTiers(
        refreshSlow: parameters['refreshSlow'] == true,
      );
      _markOpcUaSuccess();
      _sendResult(socket, id, true);
    } on FormatException catch (error) {
      _sendError(socket, id, error.message);
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA tier configuration failed: $error');
    }
  }

  Future<void> _readValues(
    WebSocket socket,
    int id,
    Map<Object?, Object?> parameters,
  ) async {
    try {
      await _ensureDiscovery();
      if (parameters['revision'] != _discoveryRevision) {
        throw const FormatException(
          'Discovery revision is stale; discover paths again.',
        );
      }
      final allowed = _allowedDiscoveredPaths();
      final indices = _validatePathIndices(
        parameters['indices'],
        allowed.length,
        maximum: _maxTargetReadPaths,
        requireNonEmpty: true,
      );
      final bulk = _client;
      if (bulk is! OpcUaBulkReadClient) {
        throw const FormatException(
          'The configured PLC transport does not support targeted reads.',
        );
      }
      final values = await bulk.readValues(
        [for (final index in indices) allowed[index]],
      );
      _markOpcUaSuccess();
      _sendResult(socket, id, values);
    } on FormatException catch (error) {
      _sendError(socket, id, error.message);
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA targeted read failed: $error');
    }
  }

  Future<void> _ensureDiscovery() async {
    if (_discoveredPaths.isNotEmpty) return;
    await _tierTail;
    final snapshot = await _client.snapshot();
    validateCompleteOpcUaSnapshot(snapshot);
    _rememberDiscovery(snapshot);
    _seedMailboxSequences(snapshot);
    _markOpcUaSuccess();
    if (_discoveredPaths.isEmpty) {
      throw const FormatException(
        'The PLC snapshot did not expose any discoverable browse paths.',
      );
    }
  }

  void _rememberDiscovery(Map<String, Object?> snapshot) {
    final rawPaths = snapshot['paths'];
    final candidate = <String>[];
    if (rawPaths is List && rawPaths.isNotEmpty) {
      for (final path in rawPaths) {
        final text = '$path';
        if (_validBrowsePath(text)) candidate.add(text);
      }
    } else if (_discoveredPaths.isEmpty) {
      final values = snapshot['values'];
      if (values is Map) {
        for (final path in values.keys) {
          final text = '$path';
          if (_validBrowsePath(text)) candidate.add(text);
        }
      }
    }
    if (candidate.isEmpty) return;
    final unique = candidate.toSet().toList(growable: false);
    if (_sameStrings(unique, _discoveredPaths)) return;
    _discoveredPaths = unique;
    _discoveryRevision = (_discoveryRevision + 1) & 0x7fffffff;
    if (_discoveryRevision == 0) _discoveryRevision = 1;
    for (final profile in _readProfiles.values) {
      profile
        ..configured = false
        ..slowPaths = const {}
        ..excludedPaths = const {};
    }
    _log('[Fraktal/Gateway] stage=discovery '
        'revision=$_discoveryRevision paths=${unique.length}');
    unawaited(_queueAggregateTiers().then(
      (_) {},
      onError: (Object error, StackTrace stackTrace) {
        _log('[Fraktal/Gateway] stage=read-tier-reset-failed error=$error');
      },
    ));
  }

  List<String> _allowedDiscoveredPaths() => [
        for (final path in _discoveredPaths)
          if (config.permitsRead(path)) path,
      ];

  Map<String, Object?> _projectSnapshot(
    Map<String, Object?> snapshot,
    WebSocket socket,
  ) {
    final allowed = _allowedDiscoveredPaths();
    final allowedSet = allowed.toSet();
    Map<String, Object?> filter(Object? raw) {
      if (raw is! Map) return const {};
      return {
        for (final entry in raw.entries)
          if (entry.key is String && allowedSet.contains(entry.key))
            entry.key as String: entry.value,
      };
    }

    final profile = _readProfiles[socket];
    return <String, Object?>{
      ...snapshot,
      'discoveryRevision': _discoveryRevision,
      'nodeCount': allowed.length,
      'truncated': false,
      // The repository needs the full contract only until it has installed a
      // tier profile. Thereafter an empty list avoids retransmitting thousands
      // of static path strings on every cyclic snapshot.
      'paths': profile?.configured == true ? const <String>[] : allowed,
      'values': filter(snapshot['values']),
      if (snapshot.containsKey('dataValues'))
        'dataValues': filter(snapshot['dataValues']),
    };
  }

  Future<void> _queueAggregateTiers({bool refreshSlow = false}) {
    final profiles = _readProfiles.values.toList(growable: false);
    final slow = _profileIntersection(
      profiles,
      (profile) => profile.slowPaths,
    );
    final excluded = _profileIntersection(
      profiles,
      (profile) => profile.excludedPaths,
    );
    final operation = _tierTail.then((_) async {
      await _client.setSlowPaths(slow);
      await _client.setExcludedPaths(excluded);
      if (refreshSlow) await _client.refreshSlowPaths();
      _log('[Fraktal/Gateway] stage=read-tiers '
          'clients=${profiles.length} slow=${slow.length} '
          'onDemand=${excluded.length} refreshSlow=$refreshSlow');
    });
    _tierTail = operation.then<void>(
      (_) {},
      onError: (Object _, StackTrace __) {},
    );
    return operation;
  }

  Future<void> _write(
    WebSocket socket,
    int id,
    Map<Object?, Object?> parameters,
  ) async {
    _ValidatedWrite write;
    try {
      write = _validateWrite(parameters);
    } on FormatException catch (error) {
      _sendError(socket, id, error.message);
      return;
    }
    if (!config.permitsWrite(write.path)) {
      _sendError(
          socket, id, 'Write path is outside the allowed HmiRequest scope.');
      return;
    }
    if (write.path.endsWith('/HmiRequest/Sequence')) {
      _sendError(
        socket,
        id,
        'Sequence is a commit field and requires writeBatch.',
      );
      return;
    }

    try {
      final accepted = await _enqueueWrite(write);
      if (!accepted) {
        _sendError(socket, id, 'OPC UA server refused the write.');
        return;
      }
      _markOpcUaSuccess();
      _sendResult(socket, id, true);
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA write failed: $error');
    }
  }

  Future<void> _writeBatch(
    WebSocket socket,
    int id,
    Map<Object?, Object?> parameters,
  ) async {
    _ValidatedBatch batch;
    try {
      batch = _validateBatch(parameters);
    } on FormatException catch (error) {
      _sendError(socket, id, error.message);
      return;
    }
    if (batch.writes.any((write) => !config.permitsWrite(write.path))) {
      _sendError(
        socket,
        id,
        'A write path is outside the allowed HmiRequest scope.',
      );
      return;
    }

    try {
      final accepted = await _enqueueBatch(batch);
      if (!accepted) {
        _sendResult(socket, id, false);
        return;
      }
      _markOpcUaSuccess();
      _sendResult(socket, id, true);
    } on Object catch (error) {
      _markOpcUaFailure(error);
      _sendError(socket, id, 'OPC UA write batch failed: $error');
    }
  }

  Future<bool> _enqueueWrite(_ValidatedWrite write) {
    final operation = _writeTail.then(
      (_) => _client.write(write.path, write.type, write.value),
    );
    _writeTail = operation.then<void>(
      (_) {},
      onError: (Object _, StackTrace __) {},
    );
    return operation;
  }

  Future<bool> _enqueueBatch(_ValidatedBatch batch) {
    final operation = _writeTail.then((_) async {
      final previous = _lastCommittedSequenceByMailbox[batch.mailbox];
      if (previous != null && batch.sequence != ((previous + 1) & 0xffffffff)) {
        _log('[Fraktal/Gateway] stage=write-refused reason=sequence '
            'mailbox=${batch.mailbox} expected=${(previous + 1) & 0xffffffff} '
            'received=${batch.sequence}');
        return false;
      }
      final accepted = await _client.writeBatch(
        batch.writes
            .map((write) => OpcUaWrite(write.path, write.type, write.value))
            .toList(growable: false),
      );
      if (accepted) {
        _lastCommittedSequenceByMailbox[batch.mailbox] = batch.sequence;
      }
      return accepted;
    });
    _writeTail = operation.then<void>(
      (_) {},
      onError: (Object _, StackTrace __) {},
    );
    return operation;
  }

  void _seedMailboxSequences(Map<String, Object?> snapshot) {
    final values = snapshot['values'];
    if (values is! Map) return;
    for (final entry in values.entries) {
      final path = entry.key;
      final value = entry.value;
      if (path is String &&
          path.endsWith('/HmiRequest/Sequence') &&
          value is int &&
          value >= 0 &&
          value <= 0xffffffff) {
        final mailbox = path.substring(0, path.length - '/Sequence'.length);
        _lastCommittedSequenceByMailbox.putIfAbsent(mailbox, () => value);
      }
    }
  }

  void _markOpcUaSuccess() {
    _plcReady = true;
    _lastOpcUaSuccess = DateTime.now();
    _lastOpcUaFailure = null;
  }

  void _markOpcUaFailure(Object error) {
    _plcReady = false;
    _lastOpcUaFailure = error;
  }

  void _sendResult(WebSocket socket, int id, Object? result) {
    socket.add(jsonEncode({'id': id, 'ok': true, 'result': result}));
  }

  void _sendError(WebSocket socket, int? id, String error) {
    socket.add(jsonEncode({'id': id, 'ok': false, 'error': error}));
  }

  Future<void> close() async {
    if (_closing) return;
    _closing = true;
    final server = _server;
    _server = null;
    if (server != null) await server.close(force: true);
    final sockets = List<WebSocket>.from(_sockets);
    _sockets.clear();
    await Future.wait(
      sockets.map((socket) => socket.close(WebSocketStatus.goingAway)),
    );
    await _writeTail;
    await _tierTail;
    await _client.close();
    _log('[Fraktal/Gateway] stage=stopped');
  }
}

class _ValidatedWrite {
  final String path;
  final OpcUaWriteType type;
  final Object value;

  const _ValidatedWrite(this.path, this.type, this.value);
}

class _SocketReadProfile {
  bool configured = false;
  Set<String> slowPaths = const {};
  Set<String> excludedPaths = const {};
}

class _ValidatedBatch {
  final List<_ValidatedWrite> writes;
  final String mailbox;
  final int sequence;

  const _ValidatedBatch(this.writes, this.mailbox, this.sequence);
}

_ValidatedBatch _validateBatch(Map<Object?, Object?> parameters) {
  final rawWrites = parameters['writes'];
  if (rawWrites is! List || rawWrites.isEmpty) {
    throw const FormatException('writeBatch requires a non-empty writes list.');
  }
  if (rawWrites.length > _maxBatchWrites) {
    throw const FormatException('writeBatch exceeds the 32-write limit.');
  }
  final writes = <_ValidatedWrite>[];
  for (final rawWrite in rawWrites) {
    if (rawWrite is! Map) {
      throw const FormatException('Each batch write must be an object.');
    }
    writes.add(_validateWrite(Map<Object?, Object?>.from(rawWrite)));
  }
  final paths = writes.map((write) => write.path).toSet();
  if (paths.length != writes.length) {
    throw const FormatException('Batch write paths must be unique.');
  }
  final commit = writes.last;
  if (!commit.path.endsWith('/HmiRequest/Sequence') ||
      commit.type != OpcUaWriteType.uint32 ||
      commit.value is! int) {
    throw const FormatException(
      'The final batch write must be the uint32 HmiRequest/Sequence commit.',
    );
  }
  if (writes.take(writes.length - 1).any(
        (write) => write.path.endsWith('/HmiRequest/Sequence'),
      )) {
    throw const FormatException('Sequence may appear only as the final write.');
  }
  final mailbox =
      commit.path.substring(0, commit.path.length - '/Sequence'.length);
  if (writes.any((write) => !write.path.startsWith('$mailbox/'))) {
    throw const FormatException(
        'All batch writes must use one HmiRequest mailbox.');
  }
  return _ValidatedBatch(writes, mailbox, commit.value as int);
}

_ValidatedWrite _validateWrite(Map<Object?, Object?> parameters) {
  final path = parameters['path'];
  final typeName = parameters['valueType'];
  final value = parameters['value'];
  if (path is! String ||
      path.isEmpty ||
      path.length > 2048 ||
      path.runes.any((rune) => rune < 0x20)) {
    throw const FormatException('Write path is invalid.');
  }
  if (typeName is! String) {
    throw const FormatException('Write valueType is invalid.');
  }
  OpcUaWriteType type;
  try {
    type = OpcUaWriteType.values.byName(typeName);
  } on ArgumentError {
    throw const FormatException('Write valueType is unsupported.');
  }
  final valid = switch (type) {
    OpcUaWriteType.boolean => value is bool,
    OpcUaWriteType.int32 =>
      value is int && value >= -0x80000000 && value <= 0x7fffffff,
    OpcUaWriteType.uint32 => value is int && value >= 0 && value <= 0xffffffff,
    OpcUaWriteType.int64 => value is int,
    OpcUaWriteType.doubleValue => value is num && value.isFinite,
    OpcUaWriteType.string =>
      value is String && value.length <= _maxStringValueLength,
  };
  if (!valid || value == null) {
    throw const FormatException('Write value does not match valueType.');
  }
  final normalized =
      type == OpcUaWriteType.doubleValue ? (value as num).toDouble() : value;
  return _ValidatedWrite(path, type, normalized);
}

Set<int> _validatePathIndices(
  Object? raw,
  int pathCount, {
  int maximum = _maxTierIndices,
  bool requireNonEmpty = false,
}) {
  if (raw is! List || (requireNonEmpty && raw.isEmpty)) {
    throw const FormatException('Browse-path indices are invalid.');
  }
  if (raw.length > maximum) {
    throw FormatException(
      'Browse-path request exceeds the $maximum-path limit.',
    );
  }
  final result = <int>{};
  for (final value in raw) {
    if (value is! int || value < 0 || value >= pathCount) {
      throw const FormatException('Browse-path index is out of range.');
    }
    if (!result.add(value)) {
      throw const FormatException('Browse-path indices must be unique.');
    }
  }
  return result;
}

Set<String> _profileIntersection(
  List<_SocketReadProfile> profiles,
  Set<String> Function(_SocketReadProfile profile) select,
) {
  if (profiles.isEmpty || profiles.any((profile) => !profile.configured)) {
    return const {};
  }
  final result = Set<String>.from(select(profiles.first));
  for (final profile in profiles.skip(1)) {
    result.retainAll(select(profile));
  }
  return result;
}

bool _sameStrings(List<String> left, List<String> right) {
  if (left.length != right.length) return false;
  for (var index = 0; index < left.length; index++) {
    if (left[index] != right[index]) return false;
  }
  return true;
}

String _normalizeOrigin(String value) {
  final uri = Uri.parse(value);
  if ((uri.scheme != 'http' && uri.scheme != 'https') || uri.host.isEmpty) {
    throw FormatException('Invalid allowed origin: $value');
  }
  final defaultPort = uri.scheme == 'http' ? 80 : 443;
  final port = uri.port == defaultPort ? '' : ':${uri.port}';
  return '${uri.scheme.toLowerCase()}://${uri.host.toLowerCase()}$port';
}

Directory? _canonicalWebRoot(Directory? value) {
  if (value == null) return null;
  if (!value.existsSync()) {
    throw ArgumentError.value(
      value.path,
      'webRoot',
      'The Web HMI directory does not exist.',
    );
  }
  return Directory(value.resolveSymbolicLinksSync());
}

File? _resolveWebAsset(Directory root, Uri uri) {
  final segments = uri.pathSegments;
  if (segments.any(
    (segment) =>
        segment == '.' ||
        segment == '..' ||
        segment.contains('\\') ||
        segment.contains('/') ||
        segment.runes.any((rune) => rune < 0x20),
  )) {
    throw const FormatException('Invalid Web asset path.');
  }
  final relative = segments.where((segment) => segment.isNotEmpty).join(
        Platform.pathSeparator,
      );
  var candidate = File(
    relative.isEmpty
        ? '${root.path}${Platform.pathSeparator}index.html'
        : '${root.path}${Platform.pathSeparator}$relative',
  );
  if (!candidate.existsSync()) {
    final last = segments.isEmpty ? '' : segments.last;
    if (last.contains('.')) return null;
    candidate = File('${root.path}${Platform.pathSeparator}index.html');
    if (!candidate.existsSync()) return null;
  }
  final resolved = candidate.resolveSymbolicLinksSync();
  final rootPath = Platform.isWindows ? root.path.toLowerCase() : root.path;
  final resolvedPath = Platform.isWindows ? resolved.toLowerCase() : resolved;
  if (resolvedPath != rootPath &&
      !resolvedPath.startsWith('$rootPath${Platform.pathSeparator}')) {
    throw const FormatException('Web asset escaped the configured root.');
  }
  return File(resolved);
}

ContentType _webContentType(String path) {
  final extension = path.toLowerCase().split('.').last;
  return switch (extension) {
    'html' => ContentType.html,
    'js' || 'mjs' => ContentType('text', 'javascript', charset: 'utf-8'),
    'css' => ContentType('text', 'css', charset: 'utf-8'),
    'json' || 'webmanifest' => ContentType.json,
    'svg' => ContentType('image', 'svg+xml'),
    'png' => ContentType('image', 'png'),
    'jpg' || 'jpeg' => ContentType('image', 'jpeg'),
    'ico' => ContentType('image', 'x-icon'),
    'wasm' => ContentType('application', 'wasm'),
    'woff' => ContentType('font', 'woff'),
    'woff2' => ContentType('font', 'woff2'),
    'ttf' => ContentType('font', 'ttf'),
    _ => ContentType.binary,
  };
}

String _normalizeBrowseRoot(String value) {
  var result = value.trim();
  while (result.endsWith('/')) {
    result = result.substring(0, result.length - 1);
  }
  if (!_validBrowsePath(result)) {
    throw FormatException('Invalid browse root: $value');
  }
  return result;
}

bool _validBrowsePath(String path) {
  if (path.isEmpty ||
      path.length > 2048 ||
      path.runes.any((rune) => rune < 0x20)) {
    return false;
  }
  return !path
      .split('/')
      .any((part) => part.isEmpty || part == '.' || part == '..');
}

bool _isLoopbackHost(String host) {
  if (host.toLowerCase() == 'localhost') return true;
  return InternetAddress.tryParse(host)?.isLoopback == true;
}

void _discardLog(String _) {}
