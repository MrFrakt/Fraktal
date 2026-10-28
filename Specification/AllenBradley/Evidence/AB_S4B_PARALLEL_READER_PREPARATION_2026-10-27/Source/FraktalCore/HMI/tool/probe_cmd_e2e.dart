// End-to-end: simulate the real interleave — a cyclic refresh (snapshot + map on
// the UI isolate) racing an operator command, which is what determines felt
// latency. Run before/after the mapper fix to compare.
import 'dart:io';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

Future<void> main(List<String> a) async {
  final c = await AdsSessionClient.connect(
      amsNetId: a.isNotEmpty ? a[0] : '192.168.1.6.1.1',
      amsPort: a.length > 1 ? int.parse(a[1]) : 851);
  try {
    const base = 'PLC1/MAIN/PneumaticPress';
    const req = '$base/HmiRequest';
    final ack = [
      '$base/HmiResponse/AckSequence',
      '$base/HmiResponse/Accepted',
      '$base/HmiResponse/Diagnostic',
    ];
    final mapper = OpcUaSnapshotMapper();
    await c.snapshot();

    final samples = <int>[];
    for (var i = 0; i < 5; i++) {
      // Kick off a cyclic refresh like the 500ms timer does...
      final snapFuture = c.snapshot();
      // ...operator taps "change mode" right now.
      final cmd = Stopwatch()..start();
      await c.writeBatch([
        const OpcUaWrite('$req/Kind', OpcUaWriteType.int32, 0),
        const OpcUaWrite('$req/IntValue', OpcUaWriteType.int32, 0),
        const OpcUaWrite('$req/Sequence', OpcUaWriteType.uint32, 0),
      ]);
      // The refresh completes and its mapping runs on the UI isolate, which is
      // exactly what used to delay the ack poll below.
      final doc = await snapFuture;
      mapper.map(doc);
      await c.readValues(ack);
      cmd.stop();
      samples.add(cmd.elapsedMilliseconds);
    }
    samples.sort();
    stdout.writeln('[e2e] command latency while a refresh+map is in flight: '
        'median=${samples[samples.length ~/ 2]}ms min=${samples.first}ms '
        'max=${samples.last}ms');
  } finally {
    await c.close();
  }
}
