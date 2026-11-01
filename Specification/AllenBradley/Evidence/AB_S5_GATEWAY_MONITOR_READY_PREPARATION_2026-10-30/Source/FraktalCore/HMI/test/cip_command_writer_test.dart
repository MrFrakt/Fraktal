import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_command_writer.dart';
import 'package:fraktal_opcua_client/cip_session_client.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/opcua_session_client.dart';
import 'cip_publication_test.dart' as gold;
import 'cip_transport_test.dart' as socket;
import '../tool/cip_rehearsal_peer.dart' as rehearsal;

class CommandWire implements CipCommandTransport {
  @override
  int get connectionBytes => 4000;
  final requests = <(String, Uint8List)>[];
  int failAt = -1;
  bool aborted = false, malformed = false;
  Completer<void>? pause;
  @override
  Future<CipReply> writeTag(String symbol, Uint8List data) async {
    requests.add((symbol, Uint8List.fromList(data)));
    await pause?.future;
    if (aborted) throw const OpcUaTransportException('Disconnected.');
    return CipReply(
        requests.length == failAt ? 5 : 0, [], Uint8List(malformed ? 1 : 0));
  }

  @override
  void abort() {
    aborted = true;
    pause?.complete();
    pause = null;
  }

  @override
  Future<void> close() async => abort();
}

void main() {
  late CipPublication publication;
  late Map fixture;
  late String root;
  List<OpcUaWrite> batch(Map vector) => [
        for (final entry in (vector['arguments'] as Map).entries)
          OpcUaWrite(
              '$root/HmiRequest/${entry.key}',
              entry.value is String
                  ? OpcUaWriteType.string
                  : entry.value is bool
                      ? OpcUaWriteType.boolean
                      : entry.key == 'DurationMs'
                          ? OpcUaWriteType.uint32
                          : OpcUaWriteType.int32,
              entry.value as Object),
        OpcUaWrite('$root/HmiRequest/Sequence', OpcUaWriteType.uint32,
            vector['sequence'] as int),
      ];
  setUpAll(() {
    publication = gold.publication(gold.fixtures().last['capture'] as Map);
    fixture = jsonDecode(utf8.decode(gzip.decode(
        File('test/fixtures/cip_command_goldens.json.gz')
            .readAsBytesSync()))) as Map;
    root = fixture['root'] as String;
  });
  test('39 Core kinds match independent Python bytes over a real socket',
      () async {
    final peer = await socket.Peer.open();
    final wire = await CipCommandSocketTransport.connect(
        host: '127.0.0.1',
        port: peer.server.port,
        expectSerial: '601FC87B',
        connectionBytes: 4000);
    final writer = CipCommandWriter(publication, wire);
    try {
      for (final vector in fixture['vectors'] as List) {
        expect(await writer.writeBatch(batch(vector as Map)), isTrue);
        expect(peer.tagWrites[peer.tagWrites.length - 2],
            gold.bytes(vector['payloadRequestHex'] as String));
        expect(peer.tagWrites.last,
            gold.bytes(vector['commitRequestHex'] as String));
      }
      expect(peer.tagWrites.length, 78);
    } finally {
      await writer.close();
      await peer.close();
    }
  });
  test('absent arguments have their Core zero values and no stale string tail',
      () {
    final plan = cipCommandWritePlan(
        publication,
        [OpcUaWrite('$root/HmiRequest/Sequence', OpcUaWriteType.uint32, 1)],
        4000);
    final row = publication.manifest.rows('commandBindings').first;
    final type = publication.namespace.symbols[row['PayloadSymbol']]!;
    final decoded = publication.decoder
        .decode(type.handle, Uint8List.sublistView(plan.payload, 6)) as Map;
    final arguments = decoded[row['ArgumentsMember']] as Map;
    expect(arguments.values.whereType<String>(), everyElement(''));
    expect(arguments['BoolValue'], isFalse);
    expect(arguments['DurationMs'], 0);
    plan.clear();
    expect(plan.payload, everyElement(0));
  });
  test('all malformed batches fail before I/O without echoing values',
      () async {
    var checks = 0;
    final wire = CommandWire(),
        writer =
            CipCommandWriter(publication, wire, verifyPublication: () async {
          checks++;
        });
    final good = batch((fixture['vectors'] as List).first as Map);
    final invalid = <List<OpcUaWrite>>[
      [],
      good.reversed.toList(),
      [...good, good.last],
      [
        const OpcUaWrite('Other/HmiRequest/Kind', OpcUaWriteType.int32, 1),
        good.last
      ],
      [
        OpcUaWrite('$root/HmiRequest/Unknown', OpcUaWriteType.int32, 1),
        good.last
      ],
      [good.first, good.first, good.last],
      for (final value in [-1, 0x100000000])
        [OpcUaWrite('$root/HmiRequest/Sequence', OpcUaWriteType.uint32, value)],
      for (final value in [-0x80000001, 0x80000000, 1.5])
        [
          OpcUaWrite('$root/HmiRequest/IntValue', OpcUaWriteType.int32, value),
          good.last
        ],
      [
        OpcUaWrite('$root/HmiRequest/DurationMs', OpcUaWriteType.int32, 1),
        good.last
      ],
      [
        OpcUaWrite('$root/HmiRequest/BoolValue', OpcUaWriteType.boolean, 1),
        good.last
      ],
      [
        OpcUaWrite('$root/HmiRequest/User', OpcUaWriteType.string, 'é' * 17),
        good.last
      ],
      [
        OpcUaWrite('$root/HmiRequest/Secret', OpcUaWriteType.string, '\u0000'),
        good.last
      ],
      [
        OpcUaWrite('$root/HmiRequest/Secret', OpcUaWriteType.string,
            String.fromCharCode(0xd800)),
        good.last
      ],
    ];
    for (final input in invalid) {
      await expectLater(
          Future.sync(() => writer.writeBatch(input)), throwsFormatException);
    }
    expect(wire.requests, isEmpty);
    expect(checks, 0);
    await writer.close();
  });
  test('insufficient connection capacity is refused before I/O', () {
    expect(
        () => cipCommandWritePlan(
            publication, batch((fixture['vectors'] as List).first as Map), 500),
        throwsFormatException);
  });
  test('payload refusal sends no commit; commit refusal returns false',
      () async {
    for (final failure in [1, 2]) {
      final wire = CommandWire()..failAt = failure;
      final writer = CipCommandWriter(publication, wire);
      expect(
          await writer
              .writeBatch(batch((fixture['vectors'] as List).first as Map)),
          isFalse);
      expect(wire.requests.length, failure);
      await writer.close();
    }
  });
  test('concurrent batches serialize whole pairs', () async {
    final wire = CommandWire(), writer = CipCommandWriter(publication, wire);
    await Future.wait([
      for (final v in (fixture['vectors'] as List).take(3))
        writer.writeBatch(batch(v as Map))
    ]);
    final row = publication.manifest.rows('commandBindings').first;
    expect(wire.requests.map((r) => r.$1), [
      for (var i = 0; i < 3; i++) ...[row['PayloadSymbol'], row['CommitSymbol']]
    ]);
    await writer.close();
  });
  test('disconnect discards the in-flight commit and queued batches', () async {
    final wire = CommandWire()..pause = Completer<void>();
    final writer = CipCommandWriter(publication, wire);
    final first =
        writer.writeBatch(batch((fixture['vectors'] as List).first as Map));
    final second =
        writer.writeBatch(batch((fixture['vectors'] as List)[1] as Map));
    final checks = Future.wait([
      expectLater(first, throwsA(isA<OpcUaTransportException>())),
      expectLater(second, throwsA(isA<OpcUaTransportException>())),
    ]);
    await Future<void>.delayed(Duration.zero);
    await writer.close();
    await checks;
    expect(wire.requests.length, 1);
    await expectLater(
        writer.writeBatch(batch((fixture['vectors'] as List).first as Map)),
        throwsA(isA<OpcUaTransportException>()));
  });
  test('malformed success reply poisons connection and never commits',
      () async {
    final wire = CommandWire()..malformed = true;
    final writer = CipCommandWriter(publication, wire);
    await expectLater(
        writer.writeBatch(batch((fixture['vectors'] as List).first as Map)),
        throwsFormatException);
    expect(wire.aborted, isTrue);
    expect(wire.requests.length, 1);
  });
  test('read-only socket still rejects writes before sending', () async {
    final peer = await socket.Peer.open();
    final wire = await peer.connect();
    try {
      await expectLater(wire.request(0x4d, cipSymbolPath('Any'), Uint8List(8)),
          throwsFormatException);
      expect(peer.tagWrites, isEmpty);
    } finally {
      await wire.close();
      await peer.close();
    }
  });
  test('default session refuses commands without even a read request',
      () async {
    final peer = await rehearsal.RehearsalPeer.start(
        capturePath: 'test/fixtures/cip_owner_apparatus_v610.json.gz',
        delayScale: 0);
    final client = await CipSessionClient.connect(
        host: '127.0.0.1', port: peer.port, expectSerial: '601FC87B');
    try {
      final before = peer.readRequests;
      expect(client.readOnly, isTrue);
      expect(
          await client
              .writeBatch(batch((fixture['vectors'] as List).first as Map)),
          isFalse);
      expect(
          await client.write('$root/HmiRequest/Kind', OpcUaWriteType.int32, 1),
          isFalse);
      expect(peer.readRequests, before);
      expect(peer.refusedServices, 0);
      await expectLater(
          CipSessionClient.connect(
              host: '127.0.0.1', port: peer.port, commandWrites: true),
          throwsFormatException);
      expect(peer.readRequests, before);
    } finally {
      await client.close();
      await peer.close();
    }
  });
}
