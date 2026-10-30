// Session-only read timing. No values, write services or declaration are logged.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:fraktal_opcua_client/src/cip_session_client.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';

import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/tool/qualify_cip_canonical.dart'
    as qualifier;

class TimedWire implements CipBatchReadTransport {
  final CipSocketTransport wire;
  final events = <Map<String, Object?>>[];
  final counters = <String>{};
  String phase = 'discovery';
  TimedWire(this.wire);
  String key(Uint8List path) => base64Encode(path);
  @override
  int get readBatchBytes => wire.readBatchBytes;
  @override
  Future<CipReply> request(
    int service,
    Uint8List path, [
    Uint8List? data,
  ]) async {
    final clock = Stopwatch()..start();
    final reply = await wire.request(service, path, data);
    events.add({
      'phase': phase,
      'kind': counters.contains(key(path)) ? 'counter' : 'read',
      'us': clock.elapsedMicroseconds,
      'service': service,
      'status': reply.status,
    });
    return reply;
  }

  @override
  Future<List<CipReply>> readBatch(List<CipBatchRead> reads) async {
    final clock = Stopwatch()..start();
    final replies = await wire.readBatch(reads);
    events.add({
      'phase': phase,
      'kind': 'body',
      'reads': reads.length,
      'us': clock.elapsedMicroseconds,
      'expectedReplyBytes': reads.fold<int>(0, (n, r) => n + r.replyDataBytes),
      'statuses': [for (final r in replies) r.status],
    });
    return replies;
  }

  @override
  void abort() => wire.abort();
  @override
  Future<void> close() => wire.close();
}

Future<void> main(List<String> args) async {
  final destination = File(args.single);
  if (destination.existsSync()) throw StateError('new output required');
  final transports = <TimedWire>[];
  for(var i=0;i<4;i++) {
    transports.add(TimedWire(await CipSocketTransport.connect(host:'127.0.0.1',slot:0,expectSerial:'601FC87B')));
  }
  final transport=transports.first;
  final pool=CipReadPool.fromConnected(transports);
  final outcomes = <Map<String, Object?>>[];
  String? failure;
  try {
    final engine = await CipSessionEngine.discover(pool),
        pub = engine.plan.publication;
    for(final transport in transports) transport.counters.addAll(
      pub.manifest.coherence.map(
        (b) => base64Encode(cipSymbolPath(b.revisionSymbol)),
      ),
    );
    final paths = pub.discoverPaths();
    final tiers = qualifier.qualificationReadTiers(
      paths,
      configurationHeartbeat: true,
    );
    engine.plan.slowPaths = tiers.slow;
    engine.plan.excludedPaths = {
      ...engine.plan.excludedPaths,
      ...tiers.excluded,
    };
    final root = pub.roots.first, status = '$root/Status';
    final refused = jsonDecode(
      utf8.decode(
        gzip.decode(
          File(
            'C:/work/fraktal-ab-s4b-q-20261029/session_01/dart_qualification.json.gz',
          ).readAsBytesSync(),
        ),
      ),
    ) as Map;
    final raw = (refused['snapshots'] as List).cast<Map>().last;
    final selected = (raw['dataValues'] as Map).entries
        .where(
          (e) =>
              (e.key as String).startsWith('$status/') &&
              ((e.value as Map)['status'] as int) & 0xc0000000 == 0x80000000,
        )
        .map((e) => e.key as String)
        .toList();
    if (selected.isEmpty) throw StateError('no refused Status selection');
    for (final phase in [
      'cyclic-coalesced',
      'whole-status',
      'selected-status',
    ]) {
      for(final transport in transports) transport.phase = phase;
      for (var i = 0; i < 8; i++) {
        final before = engine.plan.acquisitions.length,
            clock = Stopwatch()..start();
        final document = phase == 'cyclic-coalesced'
            ? await engine.snapshot(fastOnly: true)
            : await engine.readValues(
                phase == 'whole-status' ? [status] : selected,
              );
        final samples = (document['dataValues'] as Map).values.cast<Map>();
        outcomes.add({
          'phase': phase,
          'sample': i,
          'us': clock.elapsedMicroseconds,
          'values': (document['values'] as Map).length,
          'bad': samples
              .where((s) => (s['status'] as int) & 0xc0000000 == 0x80000000)
              .length,
          'uncertain': samples
              .where((s) => (s['status'] as int) & 0xc0000000 == 0x40000000)
              .length,
          'groups': engine.plan.acquisitions.skip(before).toList(),
        });
        if (phase == 'cyclic-coalesced') await engine.acquireSlowChunk();
      }
    }
  } catch (error) {
    failure = error.toString();
  } finally {
    await pool.close();
  }
  final report = {
    'readOnly': true,
    'serial': '601FC87B',
    'connections': 4,
    'controllerWrites': 0,
    'purpose': 'Diagnostic timing only; not UI/worker acceptance. No reply values recorded.',
    'error': failure,
    'events': [for(var i=0;i<transports.length;i++) for(final e in transports[i].events) {'socket':i,...e}],
    'outcomes': outcomes,
  };
  await destination.create(exclusive: true);
  await destination.writeAsBytes(gzip.encode(utf8.encode(jsonEncode(report))));
  print(
    jsonEncode({
      'readOnly': true,
      'error': failure,
      'events': transports.fold<int>(0,(n,t)=>n+t.events.length),
      'outcomes': outcomes.length,
    }),
  );
  if (failure != null) exitCode = 1;
}
