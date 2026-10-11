library;

/// A minimal EtherNet/IP + Logix tag client, pure Dart.
///
/// The AB analogue of the ADS fast path: the HMI speaks the controller's own
/// protocol directly, with no gateway process. Tag access goes over a CIP
/// connection (Extended ForwardOpen + SendUnitData) — this controller family
/// refuses unconnected symbolic requests outright.
///
/// Implemented: RegisterSession (0x65), Extended ForwardOpen (0x5B),
/// ForwardClose (0x4E), SendUnitData (0x70) carrying Read Tag (0x4C) and
/// Write Tag (0x4D) for DINT scalars, DINT arrays and raw structure bytes
/// (the manifest's tables and header are structures of DINTs and fixed-width
/// key strings, decoded by `fraktal_manifest.dart`).
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

/// One CIP error carried by a reply the transport delivered.
class CipException implements Exception {
  final String message;
  final int status;
  const CipException(this.message, this.status);

  @override
  String toString() => 'CIP error 0x${status.toRadixString(16)}: $message';
}

class EipCipClient {
  final String host;
  final int port;
  final int slot;
  Socket? _socket;
  int _session = 0;
  int _context = 0x005A0000; // arbitrary, incremented per transaction
  final BytesBuilder _inbox = BytesBuilder();
  final List<Completer<Uint8List>> _waiters = [];

  // Connected-messaging state.
  int _otConnectionId = 0;
  int _toConnectionId = 0;
  int _serialNumber = 0;
  int _sequence = 0;
  bool _connected = false;

  EipCipClient({required this.host, this.port = 44818, this.slot = 0});

  Future<void> connect() async {
    _socket = await Socket.connect(host, port, timeout: const Duration(seconds: 5));
    _socket!.listen(_onData, onDone: () {
      for (final w in _waiters) {
        w.completeError(const CipException('connection closed', -1));
      }
      _waiters.clear();
    });
    // RegisterSession request: protocol version (1) + option flags (0).
    final reply =
        await _exchange(_packet(0x0065, [1, 0, 0, 0], sessionHandle: 0));
    final parsed = ByteData.sublistView(reply);
    // Header field order: command(2), length(2), session(4), status(4).
    if (parsed.getUint32(8, Endian.little) != 0) {
      throw CipException(
          'register session status', parsed.getUint32(8, Endian.little));
    }
    _session = parsed.getUint32(4, Endian.little);
    if (_session == 0) {
      throw const CipException('register session returned no handle', -1);
    }
    await _forwardOpen();
  }

  Future<void> close() async {
    if (_connected) {
      try {
        await _forwardClose();
      } on Object {
        // Best effort.
      }
      _connected = false;
    }
    final session = _session;
    _session = 0;
    if (_socket != null && session != 0) {
      try {
        _socket!.add(_packet(0x0066, [2, 0, 0, 0], sessionHandle: session));
        await _socket!.flush();
      } on Object {
        // Best effort; the peer may already be gone.
      }
    }
    _socket?.destroy();
    _socket = null;
  }

  int _pathLenWords(String tagName) => _symbolPath(tagName).length ~/ 2;

  /// Connected Read Tag, full reply (payload after the reply header).
  Future<Uint8List> connectedReadRaw(String tagName) async {
    final path = _symbolPath(tagName);
    final count = ByteData(2)..setUint16(0, 1, Endian.little);
    final request = BytesBuilder();
    request.add(path);
    request.add(count.buffer.asUint8List());
    return _cipTransaction(
        0x4C, _pathLenWords(tagName), request.toBytes());
  }

  /// Connected Read Tag: returns the element/structure bytes (type word and
  /// UDT instance header stripped).
  Future<Uint8List> connectedRead(String tagName, {int elementCount = 1}) async {
    final path = _symbolPath(tagName);
    final count = ByteData(2)..setUint16(0, elementCount, Endian.little);
    final request = BytesBuilder();
    request.add(path);
    request.add(count.buffer.asUint8List());
    final reply = await _cipTransaction(
        0x4C, _pathLenWords(tagName), request.toBytes());
    if (reply.length < 4) {
      throw const CipException('empty read reply', -1);
    }
    // Read replies lead their payload with the additional status size
    // (2, zero on this family), then the CIP type word — followed, for
    // structure types (0x02A0 instance-specific), by a 2-byte template
    // instance. Atomic reads carry the elements straight after the type.
    final addStatusSize =
        ByteData.sublistView(reply).getUint16(0, Endian.little);
    final type = ByteData.sublistView(reply)
        .getUint16(2 + addStatusSize * 2, Endian.little);
    final isStruct = (type & 0xFF00) == 0x0200 && (type & 0xFF) == 0xA0;
    return Uint8List.sublistView(
        reply, 4 + addStatusSize * 2 + (isStruct ? 2 : 0));
  }

  /// Connected Write Tag, N DINT elements (the native request frame array).
  Future<void> connectedWriteDints(String tagName, List<int> values) async {
    final path = _symbolPath(tagName);
    // CIP Write Tag request order: path, type word, element count, data.
    final type = ByteData(2)..setUint16(0, 0xC4, Endian.little); // DINT
    final count = ByteData(2)..setUint16(0, values.length, Endian.little);
    final data = ByteData(values.length * 4);
    for (var i = 0; i < values.length; i++) {
      data.setInt32(i * 4, values[i], Endian.little);
    }
    final request = BytesBuilder();
    request.add(path);
    request.add(type.buffer.asUint8List());
    request.add(count.buffer.asUint8List());
    request.add(data.buffer.asUint8List());
    await _cipTransaction(0x4D, _pathLenWords(tagName), request.toBytes());
  }

  /// Connected Write Tag, single DINT element.
  Future<void> connectedWriteDint(String tagName, int value) async {
    final path = _symbolPath(tagName);
    // CIP Write Tag request order: path, type word, element count, data.
    final type = ByteData(2)..setUint16(0, 0xC4, Endian.little); // DINT
    final count = ByteData(2)..setUint16(0, 1, Endian.little);
    final data = ByteData(4)..setInt32(0, value, Endian.little);
    final request = BytesBuilder();
    request.add(path);
    request.add(type.buffer.asUint8List());
    request.add(count.buffer.asUint8List());
    request.add(data.buffer.asUint8List());
    await _cipTransaction(0x4D, _pathLenWords(tagName), request.toBytes());
  }

  /// Connected Write Tag, byte-array member (SINT[count]).
  Future<void> connectedWriteBytes(String tagName, Uint8List bytes) async {
    final path = _symbolPath(tagName);
    final type = ByteData(2)..setUint16(0, 0xC2, Endian.little); // SINT
    final count = ByteData(2)..setUint16(0, bytes.length, Endian.little);
    final request = BytesBuilder();
    request.add(path);
    request.add(type.buffer.asUint8List());
    request.add(count.buffer.asUint8List());
    request.add(bytes);
    await _cipTransaction(0x4D, _pathLenWords(tagName), request.toBytes());
  }

  // ---- connected transport -------------------------------------------------

  /// Sends one CIP service over the connected transport and returns the raw
  /// reply data (after the reply service and status bytes).
  /// [pathLenWords] sizes the request path; [pathAndBody] is the request path
  /// followed by the service body.
  Future<Uint8List> _cipTransaction(
      int service, int pathLenWords, Uint8List pathAndBody) async {
    if (!_connected) {
      throw const CipException('CIP connection is not open', -1);
    }
    _sequence = (_sequence + 1) & 0xFFFF;
    final data = BytesBuilder();
    final seq = ByteData(2)..setUint16(0, _sequence, Endian.little);
    data.add(seq.buffer.asUint8List());
    data.addByte(service);
    data.addByte(pathLenWords);
    data.add(pathAndBody);
    final packet = _packet(
        0x0070, _sendUnitData(data.toBytes()), sessionHandle: _session);
    // ignore: avoid_print
    print('DEBUG connected tx ${packet.length}: ${packet.map((b) => b.toRadixString(16).padLeft(2, '0')).join(' ')}');
    final reply = await _exchange(packet);
    // ignore: avoid_print
    print('DEBUG connected rx ${reply.length}: ${reply.map((b) => b.toRadixString(16).padLeft(2, '0')).join(' ')}');

    // Reply: 24-byte header, then interface handle(4), timeout(2), item
    // count(2), address item (type 0xA1, len 4, T->O connection id), data
    // item (type 0xB1, len, then target sequence(2), reply service(1),
    // status(1), then service-specific payload).
    final payload = Uint8List.sublistView(reply, 24);
    if (payload.length < 20) {
      throw CipException('short SendUnitData reply', payload.length);
    }
    // SendUnitData reply data item: [target seq(2)][reply service][status]
    // then the service payload. Read replies lead it with the additional
    // status size (2, zero here); write replies carry a trailing word with
    // no additional status — so the caller interprets from here per service.
    const dataIndex = 12 + 4 + 4;
    final replyService = payload[dataIndex + 2];
    final status = payload[dataIndex + 3];
    if (replyService != (service | 0x80)) {
      throw CipException('reply service mismatch', replyService);
    }
    if (status != 0) {
      throw CipException('target status', status);
    }
    return Uint8List.sublistView(payload, dataIndex + 4);
  }

  /// Extended ForwardOpen against the connection manager in the controller
  /// (slot 0 on the local backplane). Field layout matches pylogix's proven
  /// implementation against this emulator family (large format: 4-byte
  /// connection parameters, 0x4200 flag + connection size).
  Future<void> _forwardOpen() async {
    _otConnectionId = 0x20000002;
    _toConnectionId = 1 + DateTime.now().microsecondsSinceEpoch % 64000;
    _serialNumber = 1 + DateTime.now().microsecondsSinceEpoch % 64000;

    final cip = BytesBuilder();
    cip.addByte(0x02); // path length in words
    cip.addByte(0x20); cip.addByte(0x06); // connection manager class
    cip.addByte(0x24); cip.addByte(0x01); // instance 1
    cip.addByte(0x0A); // priority
    cip.addByte(0x0E); // timeout ticks
    final ot = ByteData(4)..setUint32(0, _otConnectionId, Endian.little);
    cip.add(ot.buffer.asUint8List());
    final to = ByteData(4)..setUint32(0, _toConnectionId, Endian.little);
    cip.add(to.buffer.asUint8List());
    final serial = ByteData(2)..setUint16(0, _serialNumber, Endian.little);
    cip.add(serial.buffer.asUint8List());
    final vendor = ByteData(2)..setUint16(0, 0x1337, Endian.little);
    cip.add(vendor.buffer.asUint8List());
    final originator = ByteData(4)..setUint32(0, 42, Endian.little);
    cip.add(originator.buffer.asUint8List());
    cip.addByte(0x03); // timeout multiplier
    cip.addByte(0x00); cip.addByte(0x00); cip.addByte(0x00); // reserved
    const rpiValue = 0x00201234;
    final rpi = ByteData(4)..setUint32(0, rpiValue, Endian.little);
    cip.add(rpi.buffer.asUint8List()); // O->T RPI
    final otParams =
        ByteData(4)..setUint32(0, (0x4200 << 16) | 4000, Endian.little);
    cip.add(otParams.buffer.asUint8List());
    const toRpiValue = 0x00204001;
    final toRpi = ByteData(4)..setUint32(0, toRpiValue, Endian.little);
    cip.add(toRpi.buffer.asUint8List()); // T->O RPI
    final toParams =
        ByteData(4)..setUint32(0, (0x4200 << 16) | 4000, Endian.little);
    cip.add(toParams.buffer.asUint8List());
    cip.addByte(0xA3); // transport class 3, application trigger
    cip.addByte(0x03); // connection path length in words
    cip.addByte(0x01); cip.addByte(slot); // backplane, slot
    cip.addByte(0x20); cip.addByte(0x02);
    cip.addByte(0x24); cip.addByte(0x01);

    final rr = _rrData(Uint8List.fromList([0x5B, ...cip.toBytes()]));
    final reply = await _exchange(_packet(0x006F, rr, sessionHandle: _session));
    final payload = Uint8List.sublistView(reply, 24);
    if (payload.length < 20) {
      throw CipException('short ForwardOpen reply', payload.length);
    }
    // Data item: reply service(1)@16, reserved@17, general status@18,
    // additional status size@19, then the assigned T->O connection id(4)@20.
    final replyService = payload[16];
    final generalStatus = payload[18];
    if (replyService != (0x5B | 0x80) || generalStatus != 0) {
      throw CipException('ForwardOpen failed', generalStatus);
    }
    final params = Uint8List.sublistView(payload, 20);
    if (params.length >= 4) {
      _toConnectionId =
          ByteData.sublistView(params).getUint32(0, Endian.little);
    }
    _connected = true;
    _sequence = 0;
  }

  Future<void> _forwardClose() async {
    final cip = BytesBuilder();
    cip.addByte(0x03); // connection path length in words
    cip.addByte(0x01); cip.addByte(slot);
    cip.addByte(0x20); cip.addByte(0x02);
    cip.addByte(0x24); cip.addByte(0x01);
    final serial = ByteData(2)..setUint16(0, _serialNumber, Endian.little);
    cip.add(serial.buffer.asUint8List());
    final vendor = ByteData(2)..setUint16(0, 0x1337, Endian.little);
    cip.add(vendor.buffer.asUint8List());
    final originator = ByteData(4)..setUint32(0, 42, Endian.little);
    cip.add(originator.buffer.asUint8List());
    final closeBytes = Uint8List.fromList([0x4E, 0x00, ...cip.toBytes()]);
    final rr = _rrData(closeBytes);
    final reply = await _exchange(_packet(0x006F, rr, sessionHandle: _session));
    final payload = Uint8List.sublistView(reply, 24);
    if (payload.length < 20) {
      throw CipException('short ForwardClose reply', payload.length);
    }
    final replyService = payload[16];
    final generalStatus = payload[18];
    if (replyService != (0x4E | 0x80) || generalStatus != 0) {
      throw CipException('ForwardClose failed', generalStatus);
    }
  }

  // ---- wire shaping --------------------------------------------------------

  Uint8List _symbolPath(String tagName) {
    // One symbolic segment per dotted component. The Echo resolves
    // `Tag.Member` only in this split form — a single 0x91 segment carrying
    // the literal dot reads back as a success stub with zeroed data (writes
    // do land, which made the failure look like a PLC-side refusal).
    final out = BytesBuilder();
    for (final segment in tagName.split('.')) {
      final bytes = segment.codeUnits;
      out.addByte(0x91); // ANSI extended symbolic segment
      out.addByte(bytes.length);
      out.add(bytes);
      if (bytes.length.isOdd) {
        out.addByte(0); // segments pad to even length
      }
    }
    return out.toBytes();
  }

  /// SendUnitData over the established connection: the address item carries
  /// the controller-assigned T->O connection id; the data item leads with the
  /// sequence count, then the CIP service.
  Uint8List _sendUnitData(Uint8List connectedData) {
    final out = BytesBuilder();
    out.add(ByteData(4).buffer.asUint8List()); // null interface handle
    out.addByte(0x00); out.addByte(0x00); // timeout = 0
    out.addByte(0x02); out.addByte(0x00); // two items
    out.addByte(0xA1); out.addByte(0x00); // connected address item
    final alen = ByteData(2)..setUint16(0, 4, Endian.little);
    out.add(alen.buffer.asUint8List());
    final cid = ByteData(4)..setUint32(0, _toConnectionId, Endian.little);
    out.add(cid.buffer.asUint8List());
    out.addByte(0xB1); out.addByte(0x00); // connected data item
    final dlen =
        ByteData(2)..setUint16(0, connectedData.length, Endian.little);
    out.add(dlen.buffer.asUint8List());
    out.add(connectedData);
    return out.toBytes();
  }

  Uint8List _rrData(Uint8List cipMessage) {
    final out = BytesBuilder();
    out.add(ByteData(4).buffer.asUint8List()); // null interface handle
    out.addByte(0x00);
    out.addByte(0x00); // timeout = 0
    out.addByte(0x02);
    out.addByte(0x00); // two address/data items
    out.addByte(0x00);
    out.addByte(0x00); // null address item type = 0x0000
    out.addByte(0x00);
    out.addByte(0x00); // null address item length = 0
    out.addByte(0xB2);
    out.addByte(0x00); // unconnected message data item type = 0x00B2
    final len = ByteData(2)..setUint16(0, cipMessage.length, Endian.little);
    out.add(len.buffer.asUint8List());
    out.add(cipMessage);
    return out.toBytes();
  }

  /// One encapsulation packet. Header field order (24 bytes):
  /// command(2), length(2), session(4), status(4), sender context(8),
  /// options(4) — then the command-specific data.
  Uint8List _packet(int command, List<int> data, {required int sessionHandle}) {
    final out = BytesBuilder();
    final header = ByteData(24);
    header.setUint16(0, command, Endian.little);
    header.setUint16(2, data.length, Endian.little);
    header.setUint32(4, sessionHandle, Endian.little);
    header.setUint32(8, 0, Endian.little); // status (request: zero)
    _context = (_context + 1) & 0xFFFFFFFF;
    header.setUint32(12, _context, Endian.little); // sender context (8 bytes)
    header.setUint32(16, _context ^ 0xFFFFFFFF, Endian.little);
    header.setUint32(20, 0, Endian.little); // options
    out.add(header.buffer.asUint8List());
    out.add(data);
    return out.toBytes();
  }

  void _onData(Uint8List chunk) {
    _inbox.add(chunk);
    while (true) {
      final buffer = _inbox.toBytes();
      if (buffer.length < 24) {
        return;
      }
      final header = ByteData.sublistView(buffer);
      final command = header.getUint16(0, Endian.little);
      final length = header.getUint16(2, Endian.little);
      if (buffer.length < 24 + length) {
        return;
      }
      final reply = Uint8List.sublistView(buffer, 0, 24 + length);
      _inbox.clear();
      if (buffer.length > 24 + length) {
        _inbox.add(Uint8List.sublistView(buffer, 24 + length));
      }
      if (command != 0x006F &&
          command != 0x0070 &&
          command != 0x0065 &&
          command != 0x0066) {
        continue; // not a reply to anything we send
      }
      if (_waiters.isNotEmpty) {
        _waiters.removeAt(0).complete(reply);
      }
    }
  }

  Future<Uint8List> _exchange(Uint8List packet) {
    final completer = Completer<Uint8List>();
    _waiters.add(completer);
    _socket!.add(packet);
    return completer.future.timeout(const Duration(seconds: 5));
  }
}
