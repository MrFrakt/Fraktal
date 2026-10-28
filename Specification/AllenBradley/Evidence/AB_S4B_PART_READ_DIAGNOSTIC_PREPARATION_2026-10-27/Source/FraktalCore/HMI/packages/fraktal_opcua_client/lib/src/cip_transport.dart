library;

import 'dart:async';
import 'dart:math';
import 'dart:io';
import 'dart:typed_data';

import 'opcua_session_client.dart';

/// Only read services are exposed. Connection-manager operations stay private;
/// no tag-write service, mode operation or station declaration exists here.
abstract interface class CipReadTransport {
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]);
  Future<void> close();
  void abort();
}

bool cipReadRequestAllowed(int service, Uint8List path) =>
    const {3, 0x0e, 0x4c, 0x52, 0x55}.contains(service) &&
    path.isNotEmpty &&
    path.length.isEven &&
    path.length <= 510;

final class CipReply {
  final int status;
  final List<int> additionalStatus;
  final Uint8List data;
  CipReply(this.status, this.additionalStatus, this.data);

  void requireSuccess() {
    if (status != 0) {
      throw OpcUaTransportException(
          'CIP service refused (0x${status.toRadixString(16)}).');
    }
  }
}

Uint8List cipWords(List<int> values) {
  final bytes = ByteData(values.length * 2);
  for (var i = 0; i < values.length; i++) {
    bytes.setUint16(i * 2, values[i], Endian.little);
  }
  return bytes.buffer.asUint8List();
}

Uint8List cipObjectPath(int kind, int instance, [int? attribute]) {
  if (kind < 0 ||
      kind > 255 ||
      instance < 0 ||
      instance > 0xffffffff ||
      attribute != null && (attribute < 0 || attribute > 255)) {
    throw const FormatException('Invalid CIP object path.');
  }
  final bytes = BytesBuilder()..add([0x20, kind]);
  if (instance <= 255) {
    bytes.add([0x24, instance]);
  } else if (instance <= 65535) {
    bytes.add([0x25, 0]);
    bytes.add(cipWords([instance]));
  } else {
    bytes.add([0x26, 0]);
    bytes.add((ByteData(4)..setUint32(0, instance, Endian.little))
        .buffer
        .asUint8List());
  }
  if (attribute != null) bytes.add([0x30, attribute]);
  return bytes.takeBytes();
}

/// ANSI symbolic components and explicit physical array indices. A dotted name
/// is never sent as one segment, and logical lower bounds never enter this path.
Uint8List cipSymbolPath(String symbol) {
  if (symbol.length > 2048)
    throw const FormatException('CIP symbol path too long.');
  final bytes = BytesBuilder();
  for (final segment in symbol.split('.')) {
    final match = RegExp(r'^([A-Za-z_][A-Za-z0-9_]*)(?:\[([0-9]+)\])?$')
        .firstMatch(segment);
    if (match == null || match[1]!.length > 255) {
      throw const FormatException('Invalid CIP symbol component.');
    }
    final name = match[1]!.codeUnits;
    bytes.add([0x91, name.length, ...name, if (name.length.isOdd) 0]);
    if (match[2] != null) {
      final index = int.parse(match[2]!);
      if (index > 0xffffffff)
        throw const FormatException('CIP array index too large.');
      if (index <= 255) {
        bytes.add([0x28, index]);
      } else if (index <= 65535) {
        bytes.add([0x29, 0]);
        bytes.add(cipWords([index]));
      } else {
        bytes.add([0x2a, 0]);
        bytes.add((ByteData(4)..setUint32(0, index, Endian.little))
            .buffer
            .asUint8List());
      }
    }
  }
  final path = bytes.takeBytes();
  if (path.isEmpty || path.length > 510)
    throw const FormatException('CIP path exceeds word count.');
  return path;
}

/// EtherNet/IP connected explicit messaging. One in-flight request per socket;
/// a late, malformed, unsolicited or mismatched reply poisons that socket.
final class CipSocketTransport implements CipReadTransport {
  late final int controllerSerial;
  final Socket _socket;
  final int slot;
  final int connectionBytes;
  final Duration timeout;
  final int _connectionSerial, _originator;
  int _session = 0,
      _outgoingId = 0,
      _incomingId = 0,
      _context = 0,
      _sequence = 0;
  bool _closed = false;
  Future<void> _tail = Future<void>.value();
  Completer<Uint8List>? _pending;
  Uint8List _buffer = Uint8List(0);
  int _expectedCommand = 0, _expectedContext = 0;

  CipSocketTransport._(this._socket, this.slot, this.connectionBytes,
      this.timeout, this._connectionSerial, this._originator) {
    _socket.setOption(SocketOption.tcpNoDelay, true);
    _socket.listen(_receive,
        onError: (Object error) => _fail(error),
        onDone: () => _fail(const OpcUaTransportException('CIP peer closed.')));
  }

  static Future<CipSocketTransport> connect(
      {required String host,
      int port = 44818,
      int slot = 0,
      int connectionBytes = 4000,
      Duration timeout = const Duration(seconds: 5),
      String? expectSerial}) async {
    if (host.isEmpty ||
        port < 1 ||
        port > 65535 ||
        slot < 0 ||
        slot > 255 ||
        connectionBytes < 500 ||
        connectionBytes > 4000 ||
        timeout.inMilliseconds < 1 ||
        timeout > const Duration(seconds: 30) ||
        expectSerial != null &&
            !RegExp(r'^[0-9A-Fa-f]{8}$').hasMatch(expectSerial)) {
      throw ArgumentError(
          'Invalid CIP endpoint, identity or connection budget.');
    }
    final random = Random.secure();
    final socket = await Socket.connect(host, port, timeout: timeout);
    final client = CipSocketTransport._(socket, slot, connectionBytes, timeout,
        1 + random.nextInt(65534), 1 + random.nextInt(0x7ffffffe));
    try {
      final registered = await client
          ._exchange(0x65, Uint8List.fromList([1, 0, 0, 0]), registering: true);
      final header = ByteData.sublistView(registered);
      client._session = header.getUint32(4, Endian.little);
      if (client._session == 0 ||
          registered.length != 28 ||
          header.getUint16(24, Endian.little) != 1 ||
          header.getUint16(26, Endian.little) != 0) {
        throw const FormatException('Invalid EtherNet/IP registration.');
      }
      await client._forwardOpen();
      final identity = await client.request(0x0e, cipObjectPath(1, 1, 6));
      identity.requireSuccess();
      if (identity.data.length != 4)
        throw const FormatException('Invalid CIP controller serial.');
      final serial =
          ByteData.sublistView(identity.data).getUint32(0, Endian.little);
      if (expectSerial != null &&
          serial != int.parse(expectSerial, radix: 16)) {
        throw const OpcUaTransportException(
            'CIP controller serial guard failed.');
      }
      client.controllerSerial = serial;
      return client;
    } on Object {
      client.abort();
      rethrow;
    }
  }

  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) {
    if (!cipReadRequestAllowed(service, path)) {
      return Future.error(const FormatException(
          'Only bounded CIP read services are available.'));
    }
    final result = Completer<CipReply>();
    _tail = _tail.then((_) async {
      try {
        if (_closed)
          throw const OpcUaTransportException('CIP connection closed.');
        _sequence = (_sequence + 1) & 0xffff;
        final request = Uint8List.fromList([
          ...cipWords([_sequence]),
          service,
          path.length ~/ 2,
          ...path,
          ...?data
        ]);
        if (request.length > connectionBytes)
          throw const FormatException('CIP request exceeds connection.');
        final frame =
            await _exchange(0x70, _cpf(0xa1, _u32(_outgoingId), 0xb1, request));
        final connected = _cpfReply(frame, 0xa1, _incomingId, 0xb1);
        if (connected.length < 6 ||
            ByteData.sublistView(connected).getUint16(0, Endian.little) !=
                _sequence) {
          throw const FormatException('CIP connected sequence mismatch.');
        }
        result.complete(_reply(Uint8List.sublistView(connected, 2), service));
      } on Object catch (error, stack) {
        _fail(error);
        result.completeError(error, stack);
      }
    });
    return result.future;
  }

  static Uint8List _u32(int n) =>
      (ByteData(4)..setUint32(0, n, Endian.little)).buffer.asUint8List();
  static Uint8List _cpf(
          int addressType, Uint8List address, int dataType, Uint8List data) =>
      Uint8List.fromList([
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        0,
        ...cipWords([addressType, address.length]),
        ...address,
        ...cipWords([dataType, data.length]),
        ...data
      ]);

  Uint8List _cpfReply(
      Uint8List frame, int addressType, int addressId, int dataType) {
    if (frame.length < 40)
      throw const FormatException('Short EtherNet/IP CPF.');
    final b = ByteData.sublistView(frame);
    var at = 32;
    if (b.getUint32(24, Endian.little) != 0 ||
        b.getUint16(30, Endian.little) != 2 ||
        b.getUint16(at, Endian.little) != addressType)
      throw const FormatException('Invalid CPF header.');
    final size = b.getUint16(at + 2, Endian.little);
    at += 4;
    if (size != (addressType == 0 ? 0 : 4) ||
        at + size + 4 > frame.length ||
        size == 4 && b.getUint32(at, Endian.little) != addressId)
      throw const FormatException('Invalid CPF connection address.');
    at += size;
    if (b.getUint16(at, Endian.little) != dataType ||
        at + 4 + b.getUint16(at + 2, Endian.little) != frame.length) {
      throw const FormatException('Invalid CPF data item.');
    }
    return Uint8List.sublistView(frame, at + 4);
  }

  static CipReply _reply(Uint8List cip, int service) {
    if (cip.length < 4 ||
        cip[0] != (service | 0x80) ||
        cip[1] != 0 ||
        cip.length < 4 + 2 * cip[3]) {
      throw const FormatException('Invalid CIP reply header.');
    }
    final words = ByteData.sublistView(cip);
    return CipReply(
        cip[2],
        [
          for (var i = 0; i < cip[3]; i++)
            words.getUint16(4 + 2 * i, Endian.little)
        ],
        Uint8List.sublistView(cip, 4 + 2 * cip[3]));
  }

  Future<CipReply> _manager(int service, Uint8List body) async {
    final cip = Uint8List.fromList([service, 2, 0x20, 6, 0x24, 1, ...body]);
    final frame = await _exchange(0x6f, _cpf(0, Uint8List(0), 0xb2, cip));
    final reply = _reply(_cpfReply(frame, 0, 0, 0xb2), service);
    reply.requireSuccess();
    return reply;
  }

  Uint8List get _route => Uint8List.fromList([1, slot, 0x20, 2, 0x24, 1]);
  Future<void> _forwardOpen() async {
    final random = Random.secure();
    final body = Uint8List.fromList([
      10,
      14,
      ..._u32(0x20000000 + random.nextInt(0xffff)),
      ..._u32(0x30000000 + random.nextInt(0xffff)),
      ...cipWords([_connectionSerial, 0x1337]),
      ..._u32(_originator),
      3,
      0,
      0,
      0,
      ..._u32(0x201234),
      ..._u32(0x42000000 | connectionBytes),
      ..._u32(0x204001),
      ..._u32(0x42000000 | connectionBytes),
      0xa3,
      3,
      ..._route
    ]);
    final response = (await _manager(0x5b, body)).data;
    if (response.length < 26)
      throw const FormatException('Short large Forward Open response.');
    final b = ByteData.sublistView(response);
    _outgoingId = b.getUint32(0, Endian.little);
    _incomingId = b.getUint32(4, Endian.little);
    if (_outgoingId == 0 ||
        _incomingId == 0 ||
        b.getUint16(8, Endian.little) != _connectionSerial ||
        b.getUint16(10, Endian.little) != 0x1337 ||
        b.getUint32(12, Endian.little) != _originator ||
        response.length != 26 + response[24] * 2 ||
        response[25] != 0) {
      throw const FormatException('Invalid Forward Open identity/size.');
    }
  }

  Future<Uint8List> _exchange(int command, Uint8List payload,
      {bool registering = false}) async {
    if (_closed || _pending != null)
      throw const OpcUaTransportException('CIP socket unavailable.');
    final header = ByteData(24);
    _context = (_context + 1) & 0x7fffffff;
    header.setUint16(0, command, Endian.little);
    header.setUint16(2, payload.length, Endian.little);
    header.setUint32(4, registering ? 0 : _session, Endian.little);
    // ODVA PUB00123R1 3.3.11.2.3: SendUnitData does not use Sender
    // Context. Its CPF connection ID and connected sequence correlate replies.
    header.setUint32(12, command == 0x70 ? 0 : _context, Endian.little);
    header.setUint32(16, command == 0x70 ? 0 : _originator, Endian.little);
    _expectedCommand = command;
    _expectedContext = _context;
    final pending = Completer<Uint8List>();
    _pending = pending;
    _socket.add([...header.buffer.asUint8List(), ...payload]);
    try {
      return await pending.future.timeout(timeout);
    } on Object catch (error) {
      _fail(error);
      rethrow;
    }
  }

  void _receive(Uint8List chunk) {
    if (_closed) return;
    try {
      if (_pending == null || _buffer.length + chunk.length > 65559)
        throw const FormatException('Unsolicited/oversized EtherNet/IP data.');
      _buffer = Uint8List.fromList([..._buffer, ...chunk]);
      if (_buffer.length < 24) return;
      final b = ByteData.sublistView(_buffer);
      final size = 24 + b.getUint16(2, Endian.little);
      if (b.getUint16(0, Endian.little) != _expectedCommand ||
          b.getUint32(8, Endian.little) != 0 ||
          _expectedCommand != 0x70 &&
              (b.getUint32(12, Endian.little) != _expectedContext ||
                  b.getUint32(16, Endian.little) != _originator) ||
          b.getUint32(20, Endian.little) != 0 ||
          _expectedCommand != 0x65 &&
              b.getUint32(4, Endian.little) != _session) {
        throw FormatException('EtherNet/IP reply identity/status mismatch: '
            'command=${b.getUint16(0, Endian.little)}/$_expectedCommand '
            'context=${b.getUint32(12, Endian.little)}/$_expectedContext '
            'origin=${b.getUint32(16, Endian.little)}/$_originator '
            'session=${b.getUint32(4, Endian.little)}/$_session '
            'status=${b.getUint32(8, Endian.little)} options=${b.getUint32(20, Endian.little)}.');
      }
      if (_buffer.length < size) return;
      if (_buffer.length != size)
        throw const FormatException('Extra EtherNet/IP reply data.');
      final response = _buffer;
      _buffer = Uint8List(0);
      final pending = _pending!;
      _pending = null;
      pending.complete(response);
    } on Object catch (error) {
      _fail(error);
    }
  }

  void _fail(Object error) {
    _closed = true;
    _socket.destroy();
    _buffer = Uint8List(0);
    final pending = _pending;
    _pending = null;
    if (pending != null && !pending.isCompleted) pending.completeError(error);
  }

  @override
  void abort() =>
      _fail(const OpcUaTransportException('CIP connection aborted.'));

  @override
  Future<void> close() async {
    if (_closed) return;
    // Never wait for a hung/queued read when shutting down.
    if (_pending != null) {
      abort();
      return;
    }
    try {
      if (_outgoingId != 0)
        await _manager(
            0x4e,
            Uint8List.fromList([
              10,
              14,
              ...cipWords([_connectionSerial, 0x1337]),
              ..._u32(_originator),
              3,
              0,
              ..._route
            ]));
      final header = ByteData(24)
        ..setUint16(0, 0x66, Endian.little)
        ..setUint32(4, _session, Endian.little);
      _socket.add(header.buffer.asUint8List());
      await _socket.flush().timeout(timeout);
    } on Object {
      /* Best effort on a broken transport; no retry or replay. */
    } finally {
      abort();
    }
  }
}
