library;

import 'dart:async';
import 'dart:typed_data';

import 'cip_transport.dart';
import 'opcua_session_client.dart';

/// Optional capability: a complete guarded row owns one read-only connection.
/// Existing transports and targeted reads retain their serial behavior.
abstract interface class CipGroupedReadTransport implements CipReadTransport {
  int get groupConcurrency;
  Future<T> withGroup<T>(Future<T> Function(CipReadTransport) work);
}

final class CipReadPool implements CipGroupedReadTransport {
  static const _maximumConnections = 4;
  final List<CipReadTransport> _transports;
  final List<CipReadTransport> _available;
  final List<Completer<CipReadTransport>> _waiting = [];
  bool _closed = false;

  CipReadPool.fromConnected(List<CipReadTransport> transports)
      : _transports = List.unmodifiable(transports),
        _available = List.of(transports) {
    if (transports.isEmpty ||
        transports.length > _maximumConnections ||
        transports.toSet().length != transports.length) {
      throw ArgumentError('One to four distinct read transports required.');
    }
  }

  static Future<CipReadPool> connect(
      {required String host,
      int port = 44818,
      int slot = 0,
      String? expectSerial}) async {
    final opened = <CipReadTransport>[];
    try {
      final first = await CipSocketTransport.connect(
          host: host, port: port, slot: slot, expectSerial: expectSerial);
      opened.add(first);
      final serial = first.controllerSerial.toRadixString(16).padLeft(8, '0');
      for (var i = 1; i < _maximumConnections; i++) {
        opened.add(await CipSocketTransport.connect(
            host: host, port: port, slot: slot, expectSerial: serial));
      }
      return CipReadPool.fromConnected(opened);
    } on Object {
      await Future.wait(opened.map((transport) => transport.close()));
      rethrow;
    }
  }

  @override
  int get groupConcurrency => _transports.length;

  @override
  Future<T> withGroup<T>(Future<T> Function(CipReadTransport) work) async {
    if (_closed) throw const OpcUaTransportException('CIP read pool closed.');
    late CipReadTransport transport;
    if (_available.isNotEmpty) {
      transport = _available.removeAt(0);
    } else {
      if (_waiting.length >= 64) {
        throw const OpcUaTransportException('CIP read queue exceeded.');
      }
      final waiter = Completer<CipReadTransport>();
      _waiting.add(waiter);
      transport = await waiter.future;
    }
    try {
      if (_closed) throw const OpcUaTransportException('CIP read pool closed.');
      final result = await work(transport);
      if (_closed) throw const OpcUaTransportException('CIP read pool closed.');
      return result;
    } finally {
      if (!_closed) {
        if (_waiting.isNotEmpty) {
          _waiting.removeAt(0).complete(transport);
        } else {
          _available.add(transport);
        }
      }
    }
  }

  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) {
    if (path.length > 510 || (data?.length ?? 0) > 4000)
      return Future.error(
          const FormatException('CIP read request exceeds bounds.'));
    path = Uint8List.fromList(path);
    data = data == null ? null : Uint8List.fromList(data);
    if (!cipReadRequestAllowed(service, path, data)) {
      return Future.error(const FormatException(
          'Only bounded CIP read services are available.'));
    }
    return withGroup((transport) => transport.request(service, path, data));
  }

  void _stop() {
    _closed = true;
    _available.clear();
    for (final waiter in _waiting) {
      waiter.completeError(
          const OpcUaTransportException('CIP read pool closed.'));
    }
    _waiting.clear();
  }

  @override
  void abort() {
    if (_closed) return;
    _stop();
    for (final transport in _transports) {
      transport.abort();
    }
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    _stop();
    await Future.wait(_transports.map((transport) => transport.close()));
  }
}
