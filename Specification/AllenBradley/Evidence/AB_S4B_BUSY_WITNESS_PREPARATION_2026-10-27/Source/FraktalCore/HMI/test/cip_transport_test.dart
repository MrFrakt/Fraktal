import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

Uint8List u32(int n) =>
    (ByteData(4)..setUint32(0, n, Endian.little)).buffer.asUint8List();

class Peer {
  final ServerSocket server;
  Socket? socket;
  Uint8List buffer = Uint8List(0);
  final List<int> services = [];
  bool split = false, hang = false;
  String? corrupt;
  int identitySerial = 0x601fc87b;
  Peer._(this.server) {
    server.listen((s) {
      socket = s;
      s.listen(receive, onError: (Object _) {});
    });
  }
  static Future<Peer> open() async =>
      Peer._(await ServerSocket.bind(InternetAddress.loopbackIPv4, 0));
  Future<void> close() async {
    socket?.destroy();
    await server.close();
  }

  Future<CipSocketTransport> connect(
          {String serial = '601FC87B',
          Duration timeout = const Duration(seconds: 1)}) =>
      CipSocketTransport.connect(
          host: '127.0.0.1',
          port: server.port,
          expectSerial: serial,
          timeout: timeout);
  void receive(Uint8List chunk) {
    buffer = Uint8List.fromList([...buffer, ...chunk]);
    while (buffer.length >= 24) {
      final size =
          24 + ByteData.sublistView(buffer).getUint16(2, Endian.little);
      if (buffer.length < size) return;
      final frame = Uint8List.sublistView(buffer, 0, size);
      buffer = Uint8List.fromList(buffer.sublist(size));
      unawaited(reply(frame));
    }
  }

  Future<void> reply(Uint8List frame) async {
    final header = ByteData.sublistView(frame);
    final command = header.getUint16(0, Endian.little);
    if (command == 0x66) return;
    Uint8List cpf(int address, int id, int kind, List<int> data) =>
        Uint8List.fromList([
          0,
          0,
          0,
          0,
          0,
          0,
          2,
          0,
          ...cipWords([address, address == 0 ? 0 : 4]),
          if (address != 0) ...u32(id),
          ...cipWords([kind, data.length]),
          ...data
        ]);
    late Uint8List payload;
    if (command == 0x65) {
      payload = Uint8List.fromList([1, 0, 0, 0]);
    } else if (command == 0x6f) {
      final cip = Uint8List.sublistView(frame, 40);
      final service = cip[0];
      services.add(service);
      final body = Uint8List.sublistView(cip, 6),
          b = ByteData.sublistView(body);
      if (service == 0x5b) {
        expect(cip.sublist(2, 6), [0x20, 6, 0x24, 1]);
        expect(b.getUint32(26, Endian.little) & 0xffff, 4000);
        final data = [
          ...u32(0x11223344),
          ...u32(0x55667788),
          ...body.sublist(10, 18),
          ...u32(10000),
          ...u32(10000),
          0,
          0
        ];
        payload = cpf(0, 0, 0xb2, [service | 0x80, 0, 0, 0, ...data]);
      } else {
        expect(service, 0x4e);
        payload = cpf(0, 0, 0xb2, [0xce, 0, 0, 0]);
      }
    } else {
      expect(command, 0x70);
      expect(header.getUint32(36, Endian.little), 0x11223344);
      final sequence = header.getUint16(44, Endian.little), service = frame[46];
      services.add(service);
      if (hang && service == 0x52) return;
      if (service == 0x0e)
        expect(frame.sublist(48), [0x20, 1, 0x24, 1, 0x30, 6]);
      final data = service == 0x0e
          ? u32(identitySerial)
          : Uint8List.fromList([0xc4, 0, ...u32(42)]);
      payload =
          cpf(0xa1, corrupt == 'connection' ? 0x55667789 : 0x55667788, 0xb1, [
        ...cipWords([corrupt == 'sequence' ? sequence + 1 : sequence]),
        service | 0x80,
        0,
        0,
        0,
        ...data
      ]);
    }
    final response = Uint8List.fromList([...frame.sublist(0, 24), ...payload]);
    final b = ByteData.sublistView(response);
    b.setUint16(2, payload.length, Endian.little);
    b.setUint32(4, 0x12343210, Endian.little);
    if (command == 0x70) {
      b.setUint32(12, 0, Endian.little);
      b.setUint32(16, 0, Endian.little);
    }
    if (corrupt == 'context' && command == 0x6f)
      b.setUint32(12, 1234567, Endian.little);
    try {
      if (split) {
        socket!.add(response.sublist(0, 7));
        await socket!.flush();
        await Future<void>.delayed(const Duration(milliseconds: 1));
        socket!.add(response.sublist(7));
      } else {
        socket!.add(response);
      }
      await socket!.flush();
    } on Object {/* Client must close a malformed or timed-out connection. */}
  }
}

void main() {
  test('symbolic and array path encoding is physical, bounded and unambiguous',
      () {
    expect(cipSymbolPath('Root.Row[3].Name'), [
      0x91,
      4,
      82,
      111,
      111,
      116,
      0x91,
      3,
      82,
      111,
      119,
      0,
      0x28,
      3,
      0x91,
      4,
      78,
      97,
      109,
      101
    ]);
    expect(cipSymbolPath('Row[256]').sublist(6), [0x29, 0, 0, 1]);
    for (final name in [
      'Root..Value',
      'Root[foo]',
      'Root[-1]',
      'Root[4294967296]',
      'Root/Name',
      ''
    ]) {
      expect(() => cipSymbolPath(name), throwsFormatException);
    }
  });
  test(
      'register, large Forward Open, identity, fragmented TCP and exact native reads',
      () async {
    final peer = await Peer.open()
      ..split = true;
    addTearDown(peer.close);
    final client = await peer.connect();
    addTearDown(client.close);
    expect(client.controllerSerial, 0x601fc87b);
    expect(await CipNamespace.readDint(client, 'Counter'), 42);
    expect(peer.services, [0x5b, 0x0e, 0x52]);
    await client.close();
    expect(peer.services.last, 0x4e);
  });
  test(
      'read transport refuses write/mode/connection services before any wire request',
      () async {
    final peer = await Peer.open();
    addTearDown(peer.close);
    final client = await peer.connect();
    addTearDown(client.close);
    final before = peer.services.length;
    for (final service in [0x4d, 0x53, 0x4e, 0x54, 0x5b, 0x01]) {
      await expectLater(client.request(service, cipSymbolPath('Command')),
          throwsFormatException);
    }
    expect(peer.services.length, before);
  });
  test(
      'serial pin and reply context, connection and sequence mismatches fail closed',
      () async {
    final wrong = await Peer.open();
    addTearDown(wrong.close);
    await expectLater(
        wrong.connect(serial: '00000001'), throwsA(isA<Exception>()));
    final badContext = await Peer.open()
      ..corrupt = 'context';
    addTearDown(badContext.close);
    await expectLater(badContext.connect(), throwsFormatException);
    for (final error in ['connection', 'sequence']) {
      final peer = await Peer.open();
      addTearDown(peer.close);
      final client = await peer.connect();
      peer.corrupt = error;
      await expectLater(
          CipNamespace.readDint(client, 'Counter'), throwsFormatException);
      await expectLater(
          CipNamespace.readDint(client, 'Counter'), throwsA(isA<Exception>()));
      await client.close();
    }
  });
  test(
      'deadline closes socket and queued requests cannot consume a late response',
      () async {
    final peer = await Peer.open();
    addTearDown(peer.close);
    final client =
        await peer.connect(timeout: const Duration(milliseconds: 200));
    peer.hang = true;
    final first = CipNamespace.readDint(client, 'Counter');
    final second = CipNamespace.readDint(client, 'Other');
    await Future.wait([
      expectLater(first, throwsA(isA<TimeoutException>())),
      expectLater(second, throwsA(isA<Exception>()))
    ]);
    expect(peer.services.where((s) => s == 0x52).length, 1);
    await client.close();
  });
}
