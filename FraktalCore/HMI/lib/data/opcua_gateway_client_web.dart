// ignore_for_file: deprecated_member_use
library;

import 'dart:async';
import 'dart:convert';
import 'dart:html';
import 'opcua_session_client.dart';

/// Browser implementation of the Fraktal OPC UA gateway protocol. The gateway
/// owns the native OPC UA session and returns the exact same flat snapshot used
/// by the open62541 adapter.
class WebGatewayOpcUaClient implements OpcUaBatchSessionClient {
  final WebSocket _socket;
  final Map<int, Completer<Object?>> _pending = {};
  late final StreamSubscription<MessageEvent> _messageSub;
  late final StreamSubscription<CloseEvent> _closeSub;
  late final StreamSubscription<Event> _errorSub;
  int _nextId = 1;
  bool _closed = false;
  bool _disposed = false;

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
    return Map<String, Object?>.from(result);
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
