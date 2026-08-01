// ignore_for_file: deprecated_member_use
library;

import 'dart:async';
import 'dart:convert';
import 'dart:html';
import 'opcua_session_client.dart';

/// Browser implementation of the Fraktal OPC UA gateway protocol. The gateway
/// owns the native OPC UA session and returns the exact same flat snapshot used
/// by the open62541 adapter.
class WebGatewayOpcUaClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaTieredReadClient {
  final WebSocket _socket;
  final Map<int, Completer<Object?>> _pending = {};
  late final StreamSubscription<MessageEvent> _messageSub;
  late final StreamSubscription<CloseEvent> _closeSub;
  late final StreamSubscription<Event> _errorSub;
  int _nextId = 1;
  bool _closed = false;
  bool _disposed = false;
  int _discoveryRevision = 0;
  List<String> _discoveredPaths = const [];
  Map<String, int> _pathIndex = const {};
  Set<String> _slowPaths = const {};
  Set<String> _excludedPaths = const {};

  WebGatewayOpcUaClient._(this._socket) {
    _messageSub = _socket.onMessage.listen(_onMessage);
    _closeSub = _socket.onClose.listen((event) {
      final reason = event.reason;
      _terminate(OpcUaTransportException(
        'Gateway connection closed with code ${event.code}: '
        '${reason == null || reason.isEmpty ? '(no reason)' : reason}.',
      ));
    });
    _errorSub = _socket.onError.listen((_) {
      _terminate(
        const OpcUaTransportException('Gateway WebSocket failed.'),
      );
    });
  }

  static Future<WebGatewayOpcUaClient> connect(
    Uri endpoint, {
    Duration timeout = const Duration(seconds: 5),
  }) async {
    final socket = WebSocket(endpoint.toString());
    final opened = Completer<void>();
    late StreamSubscription<Event> openSub;
    late StreamSubscription<Event> errorSub;
    openSub = socket.onOpen.listen((_) {
      if (!opened.isCompleted) opened.complete();
    });
    errorSub = socket.onError.listen((_) {
      if (!opened.isCompleted) {
        opened.completeError(const OpcUaTransportException(
          'Could not open Fraktal OPC UA WebSocket gateway.',
        ));
      }
    });
    try {
      await opened.future.timeout(timeout);
    } on TimeoutException catch (error) {
      socket.close();
      throw OpcUaTransportException(
        'Gateway connection timed out.',
        error,
      );
    } on Object {
      socket.close();
      rethrow;
    } finally {
      await openSub.cancel();
      await errorSub.cancel();
    }
    return WebGatewayOpcUaClient._(socket);
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
      _socket.send(jsonEncode({
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
      _socket.close(1001, 'request timeout');
      throw error;
    });
  }

  void _onMessage(MessageEvent event) {
    try {
      final decoded = jsonDecode('${event.data}');
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
      _socket.close(1002, 'bad response');
    }
  }

  void _terminate(Object error) {
    if (_closed) return;
    _closed = true;
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
    if (result is! Map)
      throw const FormatException('Gateway snapshot missing.');
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
    await _messageSub.cancel();
    await _closeSub.cancel();
    await _errorSub.cancel();
    _socket.close();
    _failAll(StateError('Gateway client closed.'));
  }
}
