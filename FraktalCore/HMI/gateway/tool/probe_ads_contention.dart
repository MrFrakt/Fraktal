// Dev probe: measure what a mode change ACTUALLY waits for — the worker isolate
// is single-threaded, so an in-flight cyclic snapshot must finish before a
// command's writes/ack-polls are served. Reproduces that head-of-line blocking.
//
//   dart run tool/probe_ads_contention.dart [amsNetId] [amsPort]
import 'dart:io';

import 'package:fraktal_opcua_client/ads_session_client.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '192.168.1.6.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 851;

  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    const base = 'PLC1/MAIN/PneumaticPress';
    const request = '$base/HmiRequest';
    final ackPaths = [
      '$base/HmiResponse/AckSequence',
      '$base/HmiResponse/Accepted',
      '$base/HmiResponse/Diagnostic',
    ];

    // Warm handles so the numbers reflect steady state, not first-touch.
    await client.snapshot();
    await client.readValues(ackPaths);

    // BASELINE: an idle-transport command sequence (10 writes + one ack poll).
    final idle = Stopwatch()..start();
    await client.writeBatch([
      const OpcUaWrite('$request/Kind', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/IntValue', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/Sequence', OpcUaWriteType.uint32, 0),
    ]);
    await client.readValues(ackPaths);
    idle.stop();
    stdout.writeln('[contention] command with IDLE transport: '
        '${idle.elapsedMilliseconds}ms');

    // CONTENDED: fire a snapshot (as the 500ms timer does), then immediately
    // issue the command — exactly what happens when an operator taps mid-cycle.
    final contended = Stopwatch()..start();
    final snapshotFuture = client.snapshot();
    final cmd = Stopwatch()..start();
    await client.writeBatch([
      const OpcUaWrite('$request/Kind', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/IntValue', OpcUaWriteType.int32, 0),
      const OpcUaWrite('$request/Sequence', OpcUaWriteType.uint32, 0),
    ]);
    await client.readValues(ackPaths);
    cmd.stop();
    await snapshotFuture;
    contended.stop();
    stdout.writeln('[contention] command QUEUED BEHIND a snapshot: '
        '${cmd.elapsedMilliseconds}ms  (snapshot+cmd total '
        '${contended.elapsedMilliseconds}ms)');
    stdout.writeln('');
    stdout.writeln('[contention] The delta is head-of-line blocking on the '
        'single ADS worker isolate.');
  } finally {
    await client.close();
  }
}
