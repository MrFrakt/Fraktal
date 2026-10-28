// Dev probe: measure the real per-operation ADS latency that makes up a mode
// change, so optimisation targets facts instead of guesses.
//
//   dart run tool/probe_ads_latency.dart [amsNetId] [amsPort]
//
// Needs fraktal_ads.dll in the CWD (the gateway dir).
import 'dart:io';

import 'package:fraktal_opcua_client/ads_session_client.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';

String _ms(List<int> us) {
  if (us.isEmpty) return 'n/a';
  final sorted = [...us]..sort();
  final total = us.reduce((a, b) => a + b);
  String f(int v) => (v / 1000).toStringAsFixed(2);
  return 'avg=${f(total ~/ us.length)}ms min=${f(sorted.first)}ms '
      'median=${f(sorted[sorted.length ~/ 2])}ms max=${f(sorted.last)}ms';
}

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '192.168.1.6.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 851;

  stdout.writeln('[latency] connecting ads://$netId:$port ...');
  final connectWatch = Stopwatch()..start();
  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  connectWatch.stop();
  stdout.writeln('[latency] connect: ${connectWatch.elapsedMilliseconds}ms');

  try {
    // Snapshot cost — this is what a legacy (non-bulk) ack poll would pay.
    final snapWatch = Stopwatch()..start();
    final snap = await client.snapshot();
    snapWatch.stop();
    final values = snap['values'];
    final count = values is Map ? values.length : 0;
    stdout.writeln('[latency] snapshot: ${snapWatch.elapsedMilliseconds}ms '
        '($count symbols)');

    const base = 'PLC1/MAIN/PneumaticPress';
    const request = '$base/HmiRequest';

    // 1) Single targeted bulk read of the 3 ack leaves = one ack poll iteration.
    final ackPaths = [
      '$base/HmiResponse/AckSequence',
      '$base/HmiResponse/Accepted',
      '$base/HmiResponse/Diagnostic',
    ];
    final readUs = <int>[];
    for (var i = 0; i < 20; i++) {
      final w = Stopwatch()..start();
      await client.readValues(ackPaths);
      w.stop();
      readUs.add(w.elapsedMicroseconds);
    }
    stdout.writeln('[latency] ack-poll readValues(3 leaves) x20: ${_ms(readUs)}');

    // 2) A single symbol write — the unit cost writeBatch pays 10x.
    final writeUs = <int>[];
    for (var i = 0; i < 20; i++) {
      final w = Stopwatch()..start();
      await client.write('$request/IntValue', OpcUaWriteType.int32, 0);
      w.stop();
      writeUs.add(w.elapsedMicroseconds);
    }
    stdout.writeln('[latency] single write x20: ${_ms(writeUs)}');

    // 3) The full 10-write commit batch as the repository issues it today.
    final batch = <OpcUaWrite>[
      const OpcUaWrite('$request/Kind', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/TargetPath', OpcUaWriteType.string, ''),
      const OpcUaWrite('$request/NameValue', OpcUaWriteType.string, ''),
      const OpcUaWrite('$request/TextValue', OpcUaWriteType.string, ''),
      const OpcUaWrite('$request/User', OpcUaWriteType.string, ''),
      const OpcUaWrite('$request/Secret', OpcUaWriteType.string, ''),
      const OpcUaWrite('$request/IntValue', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/BoolValue', OpcUaWriteType.boolean, false),
      const OpcUaWrite('$request/DurationMs', OpcUaWriteType.uint32, 0),
      const OpcUaWrite('$request/Sequence', OpcUaWriteType.uint32, 0),
    ];
    final batchUs = <int>[];
    for (var i = 0; i < 10; i++) {
      final w = Stopwatch()..start();
      await client.writeBatch(batch);
      w.stop();
      batchUs.add(w.elapsedMicroseconds);
    }
    stdout.writeln('[latency] writeBatch(10 symbols) x10: ${_ms(batchUs)}');
    stdout.writeln('');
    stdout.writeln('[latency] NOTE: writeBatch is sequential, so its cost is '
        '~10x the single-write cost. Compare the two lines above.');
  } finally {
    await client.close();
  }
}
