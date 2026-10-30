// Rehearsal peer for the canonical AB desktop (plan WP4b.5).
//
// A loopback EtherNet/IP server that serves the Symbol, Template and record
// bytes of a sealed canonical capture, so the shipped desktop acceptance can
// be rehearsed without a controller. It is rehearsal apparatus, never
// acceptance evidence: no shipped endpoint default points at it, and a pass
// against it proves only the client, not any controller behaviour.
//
//   dart run tool/cip_rehearsal_peer.dart \
//     --capture ../../../Specification/AllenBradley/Evidence/.../generic_capture.json.gz \
//     [--port 0] [--seed 7] [--delay-scale 1.0] [--expect-sha256 <hex>]
//
// It prints one JSON status line (port, capture sha256, serial, counters) and
// serves until stdin receives "stop". The per-request delay is interpolated
// from the host-timing record's measured Flutter rendering quantiles, not
// unrecorded empirical samples (median 1.28 ms, p95
// 6.97 ms, max 16.29 ms); synthetic coherence counters advance +2 every 10 ms
// and read odd for the first 1 ms of each window.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

// ---------------------------------------------------------------- SHA-256 --

/// Compact tool-only SHA-256 (FIPS 180-4). The HMI deliberately carries no
/// crypto dependency; the peer only needs to pin the capture it serves.
Uint8List sha256Of(Uint8List message) {
  const k = [
    0x428a2f98,
    0x71374491,
    0xb5c0fbcf,
    0xe9b5dba5,
    0x3956c25b,
    0x59f111f1,
    0x923f82a4,
    0xab1c5ed5,
    0xd807aa98,
    0x12835b01,
    0x243185be,
    0x550c7dc3,
    0x72be5d74,
    0x80deb1fe,
    0x9bdc06a7,
    0xc19bf174,
    0xe49b69c1,
    0xefbe4786,
    0x0fc19dc6,
    0x240ca1cc,
    0x2de92c6f,
    0x4a7484aa,
    0x5cb0a9dc,
    0x76f988da,
    0x983e5152,
    0xa831c66d,
    0xb00327c8,
    0xbf597fc7,
    0xc6e00bf3,
    0xd5a79147,
    0x06ca6351,
    0x14292967,
    0x27b70a85,
    0x2e1b2138,
    0x4d2c6dfc,
    0x53380d13,
    0x650a7354,
    0x766a0abb,
    0x81c2c92e,
    0x92722c85,
    0xa2bfe8a1,
    0xa81a664b,
    0xc24b8b70,
    0xc76c51a3,
    0xd192e819,
    0xd6990624,
    0xf40e3585,
    0x106aa070,
    0x19a4c116,
    0x1e376c08,
    0x2748774c,
    0x34b0bcb5,
    0x391c0cb3,
    0x4ed8aa4a,
    0x5b9cca4f,
    0x682e6ff3,
    0x748f82ee,
    0x78a5636f,
    0x84c87814,
    0x8cc70208,
    0x90befffa,
    0xa4506ceb,
    0xbef9a3f7,
    0xc67178f2
  ];
  int rotr(int v, int n) => (v >> n) | ((v << (32 - n)) & 0xffffffff);
  final h = [
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19
  ];
  final padded = Uint8List((((message.length + 8) ~/ 64) + 1) * 64);
  padded.setRange(0, message.length, message);
  padded[message.length] = 0x80;
  final bits = message.length * 8;
  ByteData.sublistView(padded)
    ..setUint32(padded.length - 8, bits >> 32, Endian.big)
    ..setUint32(padded.length - 4, bits, Endian.big);
  final w = List<int>.filled(64, 0);
  for (var block = 0; block < padded.length; block += 64) {
    final b = ByteData.sublistView(padded, block, block + 64);
    for (var t = 0; t < 16; t++) {
      w[t] = b.getUint32(t * 4, Endian.big);
    }
    for (var t = 16; t < 64; t++) {
      final s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >> 3);
      final s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >> 10);
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) & 0xffffffff;
    }
    var a = h[0], bb = h[1], c = h[2], d = h[3];
    var e = h[4], f = h[5], g = h[6], hh = h[7];
    for (var t = 0; t < 64; t++) {
      final s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      final ch = (e & f) ^ (~e & g);
      final temp1 = (hh + s1 + ch + k[t] + w[t]) & 0xffffffff;
      final s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      final maj = (a & bb) ^ (a & c) ^ (bb & c);
      final temp2 = (s0 + maj) & 0xffffffff;
      hh = g;
      g = f;
      f = e;
      e = (d + temp1) & 0xffffffff;
      d = c;
      c = bb;
      bb = a;
      a = (temp1 + temp2) & 0xffffffff;
    }
    h[0] = (h[0] + a) & 0xffffffff;
    h[1] = (h[1] + bb) & 0xffffffff;
    h[2] = (h[2] + c) & 0xffffffff;
    h[3] = (h[3] + d) & 0xffffffff;
    h[4] = (h[4] + e) & 0xffffffff;
    h[5] = (h[5] + f) & 0xffffffff;
    h[6] = (h[6] + g) & 0xffffffff;
    h[7] = (h[7] + hh) & 0xffffffff;
  }
  final out = ByteData(32);
  for (var i = 0; i < 8; i++) {
    out.setUint32(i * 4, h[i], Endian.big);
  }
  return out.buffer.asUint8List();
}

String hexOf(Uint8List bytes) =>
    [for (final b in bytes) b.toRadixString(16).padLeft(2, '0')].join();

// ------------------------------------------- manifest record re-encoding --

String _lowerFirst(String name) =>
    name.isEmpty ? name : name[0].toLowerCase() + name.substring(1);

int _atomicWidth(int code) => CipTemplateDecoder.atomicByteSize(code);

void _writeAtomic(Uint8List bytes, int at, int code, Object? value) {
  final b = ByteData.sublistView(bytes);
  final width = _atomicWidth(code);
  if (width == 8) {
    final v = value is BigInt
        ? value
        : BigInt.from(value is bool ? (value ? 1 : 0) : value as num);
    if (v < BigInt.zero || v >= (BigInt.one << 64)) {
      throw FormatException('Manifest 64-bit value out of range: $v.');
    }
    b.setUint32(at, (v & BigInt.from(0xffffffff)).toInt(), Endian.little);
    b.setUint32(at + 4, (v >> 32).toInt(), Endian.little);
    return;
  }
  final v = (value is bool
          ? (value ? 1 : 0)
          : value is num
              ? value
              : throw const FormatException(
                  'Manifest atomic value is not numeric.'))
      .toDouble();
  switch (code) {
    case 0xc2:
      b.setInt8(at, v.toInt());
    case 0xc6:
      b.setUint8(at, v.toInt());
    case 0xc3:
      b.setInt16(at, v.toInt(), Endian.little);
    case 0xc7:
      b.setUint16(at, v.toInt(), Endian.little);
    case 0xc4 || 0xd6:
      b.setInt32(at, v.toInt(), Endian.little);
    case 0xc8 || 0xd3:
      b.setUint32(at, v.toInt(), Endian.little);
    case 0xca:
      b.setFloat32(at, v, Endian.little);
    case 0xcb:
      b.setFloat64(at, v, Endian.little);
    default:
      throw FormatException('Manifest atomic type not encodable: $code.');
  }
}

void _encodeRecord(Map<int, CipRawTemplate> templates, CipRawTemplate template,
    Uint8List bytes, int base, Object? value) {
  final checked = template.checked();
  final stringWidth = checked.stringByteCapacity;
  if (stringWidth != null) {
    final text = value as String;
    final data = utf8.encode(text);
    if (data.length > stringWidth) {
      throw const FormatException('Manifest string exceeds capacity.');
    }
    ByteData.sublistView(bytes)
        .setInt32(base + checked.members[0].offset, data.length, Endian.little);
    bytes.setRange(base + checked.members[1].offset,
        base + checked.members[1].offset + data.length, data);
    return;
  }
  if (value is! Map) {
    throw const FormatException('Manifest record member is not a struct.');
  }
  for (final raw in template.members) {
    final member = raw;
    final at = base + (member['offset'] as int);
    final code = member['code'] as int;
    final memberValue = value[member['name']];
    final isStructure = code & 0x8000 != 0, isArray = code & 0x6000 != 0;
    final count = isArray ? member['info'] as int : 1;
    if (isStructure) {
      final child = templates[code & 0xfff]!;
      if (isArray) {
        if (memberValue is! List || memberValue.length != count) {
          throw const FormatException('Manifest table row count differs.');
        }
        for (var i = 0; i < count; i++) {
          _encodeRecord(
              templates, child, bytes, at + i * child.byteSize, memberValue[i]);
        }
      } else {
        _encodeRecord(templates, child, bytes, at, memberValue);
      }
    } else if (code & 0xff == 0xc1) {
      if (isArray) {
        if (memberValue is! List || memberValue.length != count) {
          throw const FormatException('Manifest BOOL array differs.');
        }
        for (var i = 0; i < count; i++) {
          if (memberValue[i] == true) {
            bytes[at + i ~/ 8] |= 1 << (i % 8);
          }
        }
      } else if (memberValue == true) {
        final info = member['info'] as int;
        bytes[at + info ~/ 8] |= 1 << (info % 8);
      }
    } else if (isArray) {
      if (memberValue is! List || memberValue.length != count) {
        throw const FormatException('Manifest atomic array differs.');
      }
      final width = _atomicWidth(code & 0xff);
      for (var i = 0; i < count; i++) {
        _writeAtomic(bytes, at + i * width, code & 0xff, memberValue[i]);
      }
    } else {
      _writeAtomic(bytes, at, code & 0xff, memberValue);
    }
  }
}

/// The physical top-level value for one manifest member, from the capture's
/// normalized manifest. Table counts/capacities come from the row lists; the
/// Magic member is validated but never copied by fromPhysical, so it is
/// restored from the constant the physical format requires.
Object? _manifestMemberValue(Map manifest, String memberName) {
  if (memberName == 'Magic') return 0x46524b36;
  if (memberName.endsWith('Count') || memberName.endsWith('Capacity')) {
    final strip = memberName.endsWith('Count') ? 5 : 8;
    final table = manifest[
        _lowerFirst(memberName.substring(0, memberName.length - strip))];
    return table is List ? table.length : 0;
  }
  return manifest[_lowerFirst(memberName)];
}

/// Re-encodes the capture's decoded manifest into the physical record bytes a
/// controller serves, so wire-level discovery can read and re-derive exactly
/// the captured manifest. Round-trip proven in cip_rehearsal_peer_test.dart.
Uint8List encodeManifestRecordFrom(
    CipNamespace namespace, String symbolName, Map manifest) {
  final symbol = namespace.symbols[symbolName]!;
  final template = namespace.templates[symbol.handle]!;
  final bytes = Uint8List(template.byteSize);
  _encodeRecord(namespace.templates, template, bytes, 0, {
    for (final member in template.members)
      member['name'] as String:
          _manifestMemberValue(manifest, member['name'] as String)
  });
  return bytes;
}

// ------------------------------------------------------------- the peer ---

/// Per-request delay quantiles of the host-timing record's "simulator UI
/// rendering" row (us): median 1276.5, p95 6974, max 16290.
const _delayQuantilesUs = [
  (0.00, 440.0),
  (0.50, 1276.5),
  (0.95, 6974.0),
  (1.00, 16290.0),
];

class _Connection {
  int session = 0;
  int clientTargetId = 0, serverSourceId = 0;
  bool open = false;
}

class RehearsalPeer {
  final ServerSocket server;
  final Map capture;
  final String captureSha256;
  final int serial;
  final CipNamespace namespace;
  final Uint8List manifestRecord;
  final Map<String, Uint8List> records;
  final Set<String> counters;
  final Random random;
  final double delayScale;
  final Stopwatch _clock = Stopwatch()..start();
  final List<StreamSubscription> _subscriptions = [];
  final Set<Socket> _sockets = {};
  int readRequests = 0, refusedServices = 0;
  final List<List<int>> delayTimingsUs = [];
  int delayedRequests = 0;

  RehearsalPeer._(this.server, this.capture, this.captureSha256, this.serial,
      this.namespace, this.manifestRecord, this.records, this.counters,
      {int? seed, this.delayScale = 1.0})
      : random = Random(seed ?? 7) {
    _subscriptions.add(server.listen(_accept, onError: (Object _) {}));
  }

  int get port => server.port;

  static Future<RehearsalPeer> start(
      {required String capturePath,
      int port = 0,
      int? seed,
      double delayScale = 1.0,
      String? expectSha256}) async {
    if (port < 0 ||
        port > 65535 ||
        port == 44818 ||
        !delayScale.isFinite ||
        delayScale < 0) {
      throw const FormatException(
          'Invalid loopback rehearsal port or delay scale.');
    }
    final file = File(capturePath);
    final bytes = await file.readAsBytes();
    final sha = hexOf(sha256Of(bytes));
    if (expectSha256 != null &&
        expectSha256.toLowerCase() != sha.toLowerCase()) {
      throw FormatException(
          'Capture sha256 $sha differs from the pinned $expectSha256.');
    }
    // Plain JSON is accepted beside .json.gz so tests can write captures to
    // temporary files; the magic bytes decide, not the suffix.
    final decoded = bytes.length >= 2 && bytes[0] == 0x1f && bytes[1] == 0x8b
        ? gzip.decode(bytes)
        : bytes;
    final capture = jsonDecode(utf8.decode(decoded)) as Map<String, Object?>;
    final namespace = CipNamespace.fromCapture(capture);
    final manifestSymbol = namespace.symbols.values
        .where((s) =>
            s.structured &&
            s.rank == 0 &&
            CipManifest.looksLike(namespace.templates[s.handle]!.members
                .map((m) => m['name'] as String)
                .toSet()))
        .single;
    final manifestRecord = encodeManifestRecordFrom(
        namespace, manifestSymbol.name, capture['manifest'] as Map);
    final records = <String, Uint8List>{
      for (final row in capture['records'] as List)
        (row as Map)['tag'] as String: _hexBytes(row['rawHex'] as String)
    };
    final counters = {
      for (final row
          in (capture['manifest'] as Map)['readCoherenceBindings'] as List? ??
              const [])
        (row as Map)['RevisionSymbol'] as String
    };
    final serial = int.parse(capture['serial'] as String, radix: 16);
    final server = await ServerSocket.bind(InternetAddress.loopbackIPv4, port);
    return RehearsalPeer._(server, capture, sha, serial, namespace,
        manifestRecord, records, counters,
        seed: seed, delayScale: delayScale);
  }

  Future<void> close() async {
    for (final socket in _sockets.toList()) {
      socket.destroy();
    }
    _sockets.clear();
    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    await server.close();
  }

  static Uint8List _hexBytes(String hex) => Uint8List.fromList([
        for (var i = 0; i < hex.length; i += 2)
          int.parse(hex.substring(i, i + 2), radix: 16)
      ]);

  int _counterValue() {
    final ms = _clock.elapsedMicroseconds / 1000.0;
    final window = ms ~/ 10, fraction = ms % 10;
    // +2 every 10 ms; odd (write in progress) for the first 1 ms of a window.
    return fraction < 1 ? 2 * window + 1 : 2 * window + 2;
  }

  Duration _delay() {
    final q = random.nextDouble();
    for (var i = 1; i < _delayQuantilesUs.length; i++) {
      if (q <= _delayQuantilesUs[i].$1) {
        final below = _delayQuantilesUs[i - 1], above = _delayQuantilesUs[i];
        final us = below.$2 +
            (above.$2 - below.$2) * (q - below.$1) / (above.$1 - below.$1);
        return Duration(microseconds: (us * delayScale).round());
      }
    }
    return Duration(
        microseconds: (_delayQuantilesUs.last.$2 * delayScale).round());
  }

  void _accept(Socket socket) {
    socket.setOption(SocketOption.tcpNoDelay, true);
    _sockets.add(socket);
    final connection = _Connection();
    var buffer = Uint8List(0);
    final subscription = socket.listen((chunk) {
      buffer = Uint8List.fromList([...buffer, ...chunk]);
      while (buffer.length >= 24) {
        final size =
            24 + ByteData.sublistView(buffer).getUint16(2, Endian.little);
        if (buffer.length < size) return;
        final frame = Uint8List.sublistView(buffer, 0, size);
        buffer = Uint8List.fromList(buffer.sublist(size));
        unawaited(_handle(socket, connection, frame)
            .catchError((Object error, StackTrace stack) {
          // A rehearsal peer must be loud about what it could not serve.
          stderr.writeln('rehearsal peer: $error\n$stack');
          socket.destroy();
        }));
      }
    }, onDone: () {
      _sockets.remove(socket);
      socket.destroy();
    }, onError: (Object _) {
      _sockets.remove(socket);
      socket.destroy();
    });
    _subscriptions.add(subscription);
  }

  Uint8List _cpf(int addressType, int addressId, int dataType, List<int> data,
          {bool nullAddress = false}) =>
      Uint8List.fromList([
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        0,
        ...cipWords(
            [addressType, nullAddress ? 0 : (addressType == 0 ? 0 : 4)]),
        if (!nullAddress && addressType != 0) ..._u32(addressId),
        ...cipWords([dataType, data.length]),
        ...data
      ]);

  static List<int> _u32(int n) =>
      (ByteData(4)..setUint32(0, n, Endian.little)).buffer.asUint8List();

  void _send(Socket socket, Uint8List frame, int command, Uint8List payload,
      int session, int context, int originator) {
    final response = Uint8List.fromList([...frame.sublist(0, 24), ...payload]);
    final b = ByteData.sublistView(response);
    b.setUint16(0, command, Endian.little);
    b.setUint16(2, payload.length, Endian.little);
    b.setUint32(4, session, Endian.little);
    b.setUint32(8, 0, Endian.little);
    b.setUint32(12, command == 0x70 ? 0 : context, Endian.little);
    b.setUint32(16, command == 0x70 ? 0 : originator, Endian.little);
    b.setUint32(20, 0, Endian.little);
    try {
      socket.add(response);
    } on Object {
      socket.destroy();
    }
  }

  Future<void> _handle(
      Socket socket, _Connection connection, Uint8List frame) async {
    final header = ByteData.sublistView(frame);
    final command = header.getUint16(0, Endian.little);
    if (command == 0x66) {
      socket.destroy();
      return;
    }
    if (command == 0x65) {
      // The registration reply carries the assigned session but still echoes
      // the request's sender context and originator.
      connection.session = 0x10000 + socket.remotePort;
      _send(
          socket,
          frame,
          command,
          Uint8List.fromList([1, 0, 0, 0]),
          connection.session,
          header.getUint32(12, Endian.little),
          header.getUint32(16, Endian.little));
      return;
    }
    final delay = _delay(), started = _clock.elapsedMicroseconds;
    await Future<void>.delayed(delay);
    delayedRequests++;
    if (delayTimingsUs.length < 10000) {
      delayTimingsUs
          .add([delay.inMicroseconds, _clock.elapsedMicroseconds - started]);
    }
    if (command == 0x6f) {
      final cip = Uint8List.sublistView(frame, 40);
      final service = cip[0];
      final body = Uint8List.sublistView(cip, 6);
      if (service == 0x5b) {
        connection.open = true;
        connection.clientTargetId = 0x10000000 + socket.remotePort;
        connection.serverSourceId = 0x20000000 + socket.remotePort;
        final data = <int>[
          ..._u32(connection.clientTargetId),
          ..._u32(connection.serverSourceId),
          ...body.sublist(10, 18),
          ..._u32(10000),
          ..._u32(10000),
          0,
          0
        ];
        final payload = _cpf(0, 0, 0xb2, [service | 0x80, 0, 0, 0, ...data],
            nullAddress: true);
        _send(
            socket,
            frame,
            command,
            payload,
            connection.session,
            header.getUint32(12, Endian.little),
            header.getUint32(16, Endian.little));
      } else if (service == 0x4e) {
        connection.open = false;
        final payload = _cpf(0, 0, 0xb2, [0xce, 0, 0, 0], nullAddress: true);
        _send(
            socket,
            frame,
            command,
            payload,
            connection.session,
            header.getUint32(12, Endian.little),
            header.getUint32(16, Endian.little));
      } else {
        socket.destroy();
      }
      return;
    }
    if (command != 0x70) {
      socket.destroy();
      return;
    }
    // Connected Send Unit Data: CPF address 0xa1 with the client target id.
    if (header.getUint32(36, Endian.little) != connection.clientTargetId) {
      socket.destroy();
      return;
    }
    final sequence = header.getUint16(44, Endian.little);
    final service = frame[46];
    final pathWords = frame[47];
    final path = Uint8List.sublistView(frame, 48, 48 + 2 * pathWords);
    final data = frame.length > 48 + 2 * pathWords
        ? Uint8List.sublistView(frame, 48 + 2 * pathWords)
        : null;
    late Uint8List replyData;
    var status = 0;
    switch (service) {
      case 0x0e:
        // Get Attribute Single replies carry the bare value, no type header.
        replyData = Uint8List.fromList(_u32(serial));
      case 0x55:
        replyData = _symbolRows();
      case 0x03:
        replyData = _templateAttributes(path);
      case 0x4c:
        final (fragment, partial) = _definitionFragment(path, data!);
        status = partial ? 6 : 0;
        replyData = fragment;
      case 0x52:
        readRequests++;
        final reply = _readTag(path, data);
        status = reply.status;
        replyData = reply.data;
      case 0x0a:
        final (batch, partial) = _readBatch(data!);
        status = partial ? 0x1e : 0;
        if (batch.isEmpty) status = 8;
        replyData = batch;
      default:
        refusedServices++;
        status = 8;
        replyData = Uint8List(0);
    }
    final cip = Uint8List.fromList([
      ...cipWords([sequence]),
      service | 0x80,
      0,
      status,
      0,
      ...replyData
    ]);
    _send(
        socket,
        frame,
        command,
        _cpf(0xa1, connection.serverSourceId, 0xb1, cip),
        connection.session,
        0,
        0);
  }

  // -------------------------------------------------------- services ----

  Uint8List _symbolRows() {
    final rows = BytesBuilder();
    var instance = 0;
    for (final symbol in namespace.symbols.values) {
      instance++;
      final name = utf8.encode(symbol.name);
      // The namespace's synthesized type code already carries structured
      // flag, array rank and handle/atomic code exactly as the client's
      // CipSymbol.fromCapture expects them.
      rows.add([
        ..._u32(instance),
        ...cipWords([name.length]),
        ...name,
        ...cipWords([symbol.typeCode])
      ]);
    }
    return rows.takeBytes();
  }

  List<(String, int?)> _parsePath(Uint8List path) {
    final out = <(String, int?)>[];
    for (var at = 0; at < path.length;) {
      final kind = path[at++];
      if (kind == 0x91) {
        final n = path[at++];
        out.add((String.fromCharCodes(path.sublist(at, at + n)), null));
        at += n + n % 2;
      } else {
        final b = ByteData.sublistView(path);
        late int index;
        if (kind == 0x28) {
          index = path[at++];
        } else if (kind == 0x29) {
          at++;
          index = b.getUint16(at, Endian.little);
          at += 2;
        } else if (kind == 0x2a) {
          at++;
          index = b.getUint32(at, Endian.little);
          at += 4;
        } else {
          throw FormatException('Unexpected path segment $kind');
        }
        final last = out.removeLast();
        out.add((last.$1, index));
      }
    }
    return out;
  }

  CipRawTemplate _template(int handle) => namespace.templates[handle]!;

  Uint8List _templateAttributes(Uint8List path) {
    final template = _template(_objectInstance(path));
    final members = template.members;
    final words = _definitionWords(template);
    return Uint8List.fromList([
      ...cipWords([4, 4, 0]),
      ..._u32(words),
      ...cipWords([5, 0]),
      ..._u32(template.byteSize),
      ...cipWords([2, 0, members.length, 1, 0, template.structureHandle])
    ]);
  }

  int _objectInstance(Uint8List path) {
    // 0x20 <class> then 0x24 <instance> (8-bit), 0x25/0x26 for wider forms.
    final b = ByteData.sublistView(path);
    if (path.length >= 4 && path[0] == 0x20 && path[2] == 0x24) {
      return path[3];
    }
    if (path.length >= 6 && path[0] == 0x20 && path[2] == 0x25) {
      return b.getUint16(4, Endian.little);
    }
    if (path.length >= 8 && path[0] == 0x20 && path[2] == 0x26) {
      return b.getUint32(4, Endian.little);
    }
    throw const FormatException('Unexpected object path.');
  }

  int _definitionWords(CipRawTemplate template) {
    var content = template.members.length * 8;
    content += utf8.encode(template.name).length + 1;
    for (final member in template.members) {
      content += utf8.encode(member['name'] as String).length + 1;
    }
    return (content + 23 + 3) ~/ 4;
  }

  Uint8List _definition(CipRawTemplate template) {
    final documented = _definitionWords(template) * 4 - 23;
    final bytes = Uint8List(((documented + 3) ~/ 4) * 4);
    var at = 0;
    final b = ByteData.sublistView(bytes);
    for (final member in template.members) {
      b.setUint16(at, member['info'] as int, Endian.little);
      b.setUint16(at + 2, member['code'] as int, Endian.little);
      b.setUint32(at + 4, member['offset'] as int, Endian.little);
      at += 8;
    }
    void put(String text) {
      final raw = utf8.encode(text);
      bytes.setRange(at, at + raw.length, raw);
      at += raw.length + 1;
    }

    put(template.name);
    for (final member in template.members) {
      put(member['name'] as String);
    }
    return bytes;
  }

  (Uint8List, bool) _definitionFragment(Uint8List path, Uint8List data) {
    final template = _template(_objectInstance(path));
    final definition = _definition(template);
    final b = ByteData.sublistView(data);
    final offset = b.getUint32(0, Endian.little);
    if (offset >= definition.length) {
      throw const FormatException('Template fragment offset out of range.');
    }
    final available = definition.length - offset;
    final take = available > 3000 ? 3000 : available;
    return (
      Uint8List.sublistView(definition, offset, offset + take),
      take < available
    );
  }

  CipReply _readTag(Uint8List path, Uint8List? data) {
    final parts = _parsePath(path);
    final root = parts.first.$1;
    if (counters.contains(root)) {
      return CipReply(
          0, [], Uint8List.fromList([0xc4, 0, ..._u32(_counterValue())]));
    }
    final raw = root == _manifestSymbolName ? manifestRecord : records[root];
    if (raw == null) {
      throw FormatException('Rehearsal peer cannot serve symbol "$root".');
    }
    final symbol = namespace.symbols[root]!;
    var handle = symbol.handle, offset = 0;
    int? atomic;
    var size = _template(handle).byteSize;
    for (final part in parts.skip(1)) {
      final member = _template(handle).members.cast<Map>().singleWhere(
          (m) => m['name'] == part.$1,
          orElse: () => throw FormatException('Unknown member ${part.$1}.'));
      final code = member['code'] as int, info = member['info'] as int;
      offset += member['offset'] as int;
      final structure = code & 0x8000 != 0, array = code & 0x6000 != 0;
      if (structure) {
        handle = code & 0xfff;
        size = _template(handle).byteSize;
        atomic = null;
      } else {
        atomic = code & 0xff;
        size = atomic == 0xc1 ? 1 : CipTemplateDecoder.atomicByteSize(atomic);
      }
      if (part.$2 != null) {
        offset += part.$2! * size;
      } else if (array) {
        size *= ByteData.sublistView(data!).getUint16(0, Endian.little);
      }
      if (atomic == 0xc1 && !array) {
        final bit = (raw[offset + info ~/ 8] >> (info % 8)) & 1;
        return CipReply(0, [], Uint8List.fromList([0xc1, 0, bit]));
      }
    }
    final header = atomic == null
        ? [
            0xa0,
            2,
            ...cipWords([_template(handle).structureHandle])
          ]
        : [atomic, 0];
    final at = data == null
        ? 0
        : ByteData.sublistView(data).getUint32(2, Endian.little);
    final available = size - at, take = available > 3000 ? 3000 : available;
    return CipReply(
        take < available ? 6 : 0,
        [],
        Uint8List.fromList(
            [...header, ...raw.sublist(offset + at, offset + at + take)]));
  }

  (Uint8List, bool) _readBatch(Uint8List data) {
    final b = ByteData.sublistView(data);
    final count = b.getUint16(0, Endian.little);
    final header = 2 + 2 * count;
    final items = <List<int>>[];
    var anyPartial = false;
    for (var index = 0; index < count; index++) {
      final at = b.getUint16(2 + 2 * index, Endian.little);
      final end = index + 1 == count
          ? data.length
          : b.getUint16(4 + 2 * index, Endian.little);
      final pathWords = data[at + 1];
      if (data[at] != 0x52) {
        refusedServices++;
        items.add([data[at] | 0x80, 0, 8, 0]);
        anyPartial = true;
        continue;
      }
      final itemPath =
          Uint8List.sublistView(data, at + 2, at + 2 + 2 * pathWords);
      final itemData = Uint8List.sublistView(data, at + 2 + 2 * pathWords, end);
      final reply = _readTag(itemPath, itemData);
      readRequests++;
      if (reply.status == 6) anyPartial = true;
      items.add([0xd2, 0, reply.status, 0, ...reply.data]);
    }
    var offset = header;
    final offsets = <int>[];
    for (final item in items) {
      offsets.add(offset);
      offset += item.length;
    }
    return (
      Uint8List.fromList([
        ...cipWords([count, ...offsets]),
        for (final item in items) ...item
      ]),
      anyPartial
    );
  }

  late final String _manifestSymbolName = namespace.symbols.values
      .where((s) =>
          s.structured &&
          s.rank == 0 &&
          CipManifest.looksLike(namespace.templates[s.handle]!.members
              .map((m) => m['name'] as String)
              .toSet()))
      .single
      .name;
}

Future<void> main(List<String> arguments) async {
  String? capturePath, expectSha256;
  var port = 0, seed = 7;
  var delayScale = 1.0;
  for (var i = 0; i < arguments.length; i++) {
    switch (arguments[i]) {
      case '--capture':
        capturePath = arguments[++i];
      case '--port':
        port = int.parse(arguments[++i]);
      case '--seed':
        seed = int.parse(arguments[++i]);
      case '--delay-scale':
        delayScale = double.parse(arguments[++i]);
      case '--expect-sha256':
        expectSha256 = arguments[++i];
      default:
        throw FormatException('Unknown argument ${arguments[i]}.');
    }
  }
  if (capturePath == null) {
    throw const FormatException(
        '--capture <generic_capture.json.gz> required.');
  }
  final peer = await RehearsalPeer.start(
      capturePath: capturePath,
      port: port,
      seed: seed,
      delayScale: delayScale,
      expectSha256: expectSha256);
  // ignore: avoid_print
  print(jsonEncode({
    'rehearsalPeer': true,
    'port': peer.port,
    'capture': capturePath,
    'sha256': peer.captureSha256,
    'serial': peer.serial.toRadixString(16).padLeft(8, '0').toUpperCase(),
    'counters': peer.counters.toList(),
    'delayScale': delayScale,
    'seed': seed,
  }));
  final stopped = Completer<void>();
  final input = stdin
      .transform(utf8.decoder)
      .transform(const LineSplitter())
      .listen((line) {
    if (line == 'stop' && !stopped.isCompleted) stopped.complete();
  });
  await stopped.future;
  await input.cancel();
  await peer.close();
  // ignore: avoid_print
  print(jsonEncode({
    'rehearsalStopped': true,
    'readRequests': peer.readRequests,
    'refusedServices': peer.refusedServices,
    'delayedRequests': peer.delayedRequests,
    'delayTimingsUs': peer.delayTimingsUs,
    'delayTimingsTruncated': peer.delayedRequests > peer.delayTimingsUs.length,
    'controllerWrites': 0
  }));
}
