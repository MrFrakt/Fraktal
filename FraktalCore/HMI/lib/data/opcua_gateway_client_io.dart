library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'opcua_session_client.dart';

/// Native WSS authentication material. Deployment supplies this from protected
/// files/environment; it is deliberately absent from ConnectionSettings JSON.
class IoGatewaySecurityOptions {
  final String bearerToken;
  final String clientCertificatePath;
  final String clientPrivateKeyPath;
  final String clientPrivateKeyPassword;
  final String trustedCaPath;

  const IoGatewaySecurityOptions({
    this.bearerToken = '',
    this.clientCertificatePath = '',
    this.clientPrivateKeyPath = '',
    this.clientPrivateKeyPassword = '',
    this.trustedCaPath = '',
  });

  bool get hasClientIdentity => clientCertificatePath.isNotEmpty;

  bool get hasProtectedMaterial =>
      bearerToken.isNotEmpty ||
      clientCertificatePath.isNotEmpty ||
      clientPrivateKeyPath.isNotEmpty ||
      trustedCaPath.isNotEmpty;

  void validate(Uri endpoint) {
    if ((clientCertificatePath.isEmpty) != (clientPrivateKeyPath.isEmpty)) {
      throw ArgumentError(
        'WSS client certificate and private key must be configured together.',
      );
    }
    if (hasProtectedMaterial && endpoint.scheme != 'wss') {
      throw ArgumentError(
        'Gateway credentials and custom trust material require wss://.',
      );
    }
  }

  HttpClient? createHttpClient(Uri endpoint) {
    validate(endpoint);
    if (!hasClientIdentity && trustedCaPath.isEmpty) return null;
    final context = SecurityContext(withTrustedRoots: true);
    if (trustedCaPath.isNotEmpty) {
      context.setTrustedCertificates(trustedCaPath);
    }
    if (hasClientIdentity) {
      context.useCertificateChain(clientCertificatePath);
      context.usePrivateKey(
        clientPrivateKeyPath,
        password:
            clientPrivateKeyPassword.isEmpty ? null : clientPrivateKeyPassword,
      );
    }
    return HttpClient(context: context);
  }
}

/// Native Windows/Linux/Android client for the same versioned WebSocket
/// gateway used by Flutter Web. TLS validation is delegated to the platform
/// trust store by dart:io; deployment authentication belongs at the WSS edge.
class IoGatewayOpcUaClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaTieredReadClient {
  final WebSocket _socket;
  final HttpClient? _httpClient;
  final Map<int, Completer<Object?>> _pending = {};
  late final StreamSubscription<dynamic> _subscription;
  int _nextId = 1;
  bool _closed = false;
  bool _disposed = false;
  int _discoveryRevision = 0;
  List<String> _discoveredPaths = const [];
  Map<String, int> _pathIndex = const {};
  Set<String> _slowPaths = const {};
  Set<String> _excludedPaths = const {};

  IoGatewayOpcUaClient._(this._socket, this._httpClient) {
    _subscription = _socket.listen(
      _onMessage,
      onDone: () {
        _terminate(OpcUaTransportException(
          'Gateway connection closed with code ${_socket.closeCode}: '
          '${_socket.closeReason ?? '(no reason)'}.',
        ));
      },
      onError: (Object error, StackTrace stackTrace) {
        _terminate(OpcUaTransportException('Gateway socket failed.', error));
      },
      cancelOnError: true,
    );
  }

  static Future<IoGatewayOpcUaClient> connect(
    Uri endpoint, {
    Duration timeout = const Duration(seconds: 5),
    Duration heartbeatInterval = const Duration(seconds: 2),
    Map<String, dynamic>? headers,
    IoGatewaySecurityOptions security = const IoGatewaySecurityOptions(),
  }) async {
    security.validate(endpoint);
    final effectiveHeaders = <String, dynamic>{
      'origin': _nativeOrigin(endpoint),
      ...?headers,
    };
    if (security.bearerToken.isNotEmpty) {
      effectiveHeaders['authorization'] = 'Bearer ${security.bearerToken}';
    }
    final httpClient = security.createHttpClient(endpoint);
    try {
      final socket = await WebSocket.connect(
        endpoint.toString(),
        headers: effectiveHeaders,
        customClient: httpClient,
      ).timeout(timeout);
      socket.pingInterval = heartbeatInterval;
      return IoGatewayOpcUaClient._(socket, httpClient);
    } on Object {
      httpClient?.close(force: true);
      rethrow;
    }
  }

  Future<Object?> _call(String method, [Map<String, Object?>? parameters]) {
    if (_closed) {
      return Future.error(
        const OpcUaTransportException('Gateway client is closed.'),
      );
    }
    final id = _nextId++;
    final completer = Completer<Object?>();
    _pending[id] = completer;
    try {
      _socket.add(jsonEncode({
        'protocol': 'fraktal.opcua.gateway.v1',
        'id': id,
        'method': method,
        'params': parameters ?? const <String, Object?>{},
      }));
    } on Object catch (error) {
      _pending.remove(id);
      final transport = OpcUaTransportException(
        'Could not send gateway $method request.',
        error,
      );
      _terminate(transport);
      return Future.error(transport);
    }
    return completer.future.timeout(const Duration(seconds: 5), onTimeout: () {
      _pending.remove(id);
      final error = OpcUaTransportException(
        'Gateway $method request timed out.',
      );
      _terminate(error);
      unawaited(_socket.close(WebSocketStatus.goingAway, 'request timeout'));
      throw error;
    });
  }

  void _onMessage(dynamic event) {
    if (event is! String) {
      _terminate(
        const OpcUaTransportException('Gateway sent a binary response.'),
      );
      unawaited(_socket.close(
        WebSocketStatus.unsupportedData,
        'binary response',
      ));
      return;
    }
    try {
      final decoded = jsonDecode(event);
      if (decoded is! Map) return;
      final id = decoded['id'];
      if (id is! int) return;
      final completer = _pending.remove(id);
      if (completer == null) return;
      if (decoded['ok'] == true) {
        completer.complete(decoded['result']);
      } else {
        completer.completeError(OpcUaRemoteException('${decoded['error']}'));
      }
    } on Object catch (error) {
      _terminate(
        OpcUaTransportException('Invalid gateway response.', error),
      );
      unawaited(_socket.close(WebSocketStatus.protocolError, 'bad response'));
    }
  }

  void _terminate(Object error) {
    if (_closed) return;
    _closed = true;
    _httpClient?.close(force: true);
    _failAll(error);
  }

  void _failAll(Object error) {
    for (final completer in _pending.values) {
      if (!completer.isCompleted) completer.completeError(error);
    }
    _pending.clear();
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final result = await _call('snapshot');
    if (result is! Map) {
      throw const FormatException('Gateway snapshot missing.');
    }
    final document = Map<String, Object?>.from(result);
    _rememberDiscovery(document);
    return document;
  }

  @override
  Future<List<String>> discoverPaths() async {
    final result = await _call('discoverPaths');
    if (result is! Map || result['paths'] is! List) {
      throw const FormatException('Gateway discovery result is invalid.');
    }
    _installDiscovery(
      result['revision'],
      result['paths'] as List,
    );
    return _discoveredPaths;
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    if (browsePaths.isEmpty) return const {};
    await _ensureDiscovery();
    final indices = <int>[];
    for (final path in browsePaths) {
      final index = _pathIndex[path];
      if (index == null) {
        throw FormatException(
            'Browse path is outside gateway discovery: $path');
      }
      indices.add(index);
    }
    final values = <String, Object?>{};
    for (var offset = 0; offset < indices.length; offset += 512) {
      final end = offset + 512 < indices.length ? offset + 512 : indices.length;
      final result = await _call('readValues', {
        'revision': _discoveryRevision,
        'indices': indices.sublist(offset, end),
      });
      if (result is! Map) {
        throw const FormatException('Gateway targeted-read result is invalid.');
      }
      for (final entry in result.entries) {
        values['${entry.key}'] = entry.value;
      }
    }
    return values;
  }

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    _slowPaths = Set.unmodifiable(browsePaths);
    await _publishReadTiers();
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    _excludedPaths = Set.unmodifiable(browsePaths);
    await _publishReadTiers();
  }

  @override
  Future<void> refreshSlowPaths() => _publishReadTiers(refreshSlow: true);

  Future<void> _publishReadTiers({bool refreshSlow = false}) async {
    await _ensureDiscovery();
    List<int> indices(Set<String> paths) {
      final result = <int>[];
      for (final path in paths) {
        final index = _pathIndex[path];
        if (index == null) {
          throw FormatException(
            'Tier path is outside gateway discovery: $path',
          );
        }
        result.add(index);
      }
      result.sort();
      return result;
    }

    await _call('setReadTiers', {
      'revision': _discoveryRevision,
      'slow': indices(_slowPaths),
      'excluded': indices(_excludedPaths),
      'refreshSlow': refreshSlow,
    });
  }

  Future<void> _ensureDiscovery() async {
    if (_discoveredPaths.isEmpty) await discoverPaths();
  }

  void _rememberDiscovery(Map<String, Object?> document) {
    final paths = document['paths'];
    if (paths is List && paths.isNotEmpty) {
      _installDiscovery(document['discoveryRevision'], paths);
    }
  }

  void _installDiscovery(Object? revision, List rawPaths) {
    if (revision is! int || revision <= 0) {
      throw const FormatException('Gateway discovery revision is invalid.');
    }
    final paths = [for (final path in rawPaths) '$path'];
    _discoveryRevision = revision;
    _discoveredPaths = List.unmodifiable(paths);
    _pathIndex = Map.unmodifiable({
      for (var index = 0; index < paths.length; index++) paths[index]: index,
    });
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      (await _call('write', {
        'path': path,
        'valueType': type.name,
        'value': value,
      })) ==
      true;

  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async =>
      (await _call('writeBatch', {
        'writes': [
          for (final writeValue in writes)
            {
              'path': writeValue.path,
              'valueType': writeValue.type.name,
              'value': writeValue.value,
            },
        ],
      })) ==
      true;

  @override
  Future<void> close() async {
    if (_disposed) return;
    _disposed = true;
    _closed = true;
    await _subscription.cancel();
    await _socket.close();
    _httpClient?.close(force: true);
    _failAll(StateError('Gateway client closed.'));
  }
}

String _nativeOrigin(Uri endpoint) {
  final scheme = endpoint.scheme == 'wss' ? 'https' : 'http';
  final defaultPort = endpoint.scheme == 'wss' ? 443 : 80;
  final port = endpoint.hasPort && endpoint.port != defaultPort
      ? ':${endpoint.port}'
      : '';
  return '$scheme://${endpoint.host}$port';
}
