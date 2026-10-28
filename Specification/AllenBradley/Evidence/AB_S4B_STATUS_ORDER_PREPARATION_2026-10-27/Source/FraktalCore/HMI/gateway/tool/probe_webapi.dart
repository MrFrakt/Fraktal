// Dev probe: drive the Siemens S7 Web API session client (Fraktal/TIA Part IV
// §11.1a) against a real CPU and run its snapshot through the UNCHANGED HMI
// snapshot contract checks — discovery, snapshot cost, ack-poll cost, and one
// mailbox round trip (SET_MODE to the current mode: accepted, no state change).
//
//   set FRAKTAL_TIA_WEB_USER=fraktal
//   set FRAKTAL_TIA_WEB_PASSWORD=...          (never on the command line)
//   dart run tool/probe_webapi.dart <host> <pinned-certificate.pem> [root]
import 'dart:io';

import 'package:fraktal_opcua_client/opcua_session_client.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

String _ms(List<int> us) {
  if (us.isEmpty) return 'n/a';
  final sorted = [...us]..sort();
  String f(int v) => (v / 1000).toStringAsFixed(0);
  return 'median=${f(sorted[sorted.length ~/ 2])}ms min=${f(sorted.first)}ms '
      'max=${f(sorted.last)}ms';
}

Future<void> main(List<String> args) async {
  if (args.length < 2) {
    stderr.writeln('usage: probe_webapi.dart <host> <certificate.pem> [root]');
    exitCode = 64;
    return;
  }
  final host = args[0];
  final root = args.length > 2 ? args[2] : 'SpikeUnit';
  final user = Platform.environment['FRAKTAL_TIA_WEB_USER'] ?? '';
  final password = Platform.environment['FRAKTAL_TIA_WEB_PASSWORD'] ?? '';
  if (user.isEmpty || password.isEmpty) {
    stderr.writeln('set FRAKTAL_TIA_WEB_USER and FRAKTAL_TIA_WEB_PASSWORD');
    exitCode = 64;
    return;
  }

  final connectWatch = Stopwatch()..start();
  final client = await WebApiSessionClient.connect(
    transport: HttpsWebApiTransport(
      host: host,
      pinnedCertificate: File(args[1]).readAsBytesSync(),
    ),
    user: user,
    password: password,
  );
  connectWatch.stop();
  try {
    final paths = await client.discoverPaths();
    stdout.writeln('[webapi] connect+login+discovery: '
        '${connectWatch.elapsedMilliseconds}ms, ${paths.length} leaves');

    final snapUs = <int>[];
    late Map<String, Object?> snap;
    for (var i = 0; i < 3; i++) {
      final w = Stopwatch()..start();
      snap = await client.snapshot();
      snapUs.add(w.elapsedMicroseconds);
    }
    validateCompleteOpcUaSnapshot(snap);
    final values = snap['values'] as Map;
    final dataValues = snap['dataValues'] as Map;
    final bad = dataValues.values.where((v) => v is Map && v['status'] != 0).length;
    stdout.writeln('[webapi] snapshot x3: ${_ms(snapUs)} '
        '(${values.length} Good values, $bad Bad)');
    final base = '${WebApiSessionClient.pathPrefix}/$root';
    for (final leaf in ['Status/Name', 'Status/ModuleType', 'Status/State', 'Mode', 'CylB/Status/Name']) {
      stdout.writeln('[webapi]   $base/$leaf = ${values['$base/$leaf']}');
    }

    final ackPaths = [
      '$base/HmiResponse/AckSequence',
      '$base/HmiResponse/Accepted',
      '$base/HmiResponse/Diagnostic',
    ];
    final readUs = <int>[];
    for (var i = 0; i < 10; i++) {
      final w = Stopwatch()..start();
      await client.readValues(ackPaths);
      readUs.add(w.elapsedMicroseconds);
    }
    stdout.writeln('[webapi] ack-poll readValues(3 leaves) x10: ${_ms(readUs)}');

    // One mailbox transaction through writeBatch, exactly as the repository
    // sends it: SET_MODE to the mode already active (accepted, nothing moves).
    final mode = (await client.readValues(['$base/Mode']))['$base/Mode'];
    final seq = (await client.readValues(['$base/HmiRequest/Sequence']))['$base/HmiRequest/Sequence'] as int;
    final next = (seq + 1) & 0xFFFFFFFF;
    final w = Stopwatch()..start();
    final accepted = await client.writeBatch([
      OpcUaWrite('$base/HmiRequest/Kind', OpcUaWriteType.int32, 3),
      OpcUaWrite('$base/HmiRequest/IntValue', OpcUaWriteType.int32, mode as int),
      OpcUaWrite('$base/HmiRequest/Sequence', OpcUaWriteType.uint32, next),
    ]);
    Map<String, Object?> ack = const {};
    while (w.elapsed < const Duration(seconds: 3)) {
      ack = await client.readValues(ackPaths);
      if (ack['$base/HmiResponse/AckSequence'] == next) break;
    }
    w.stop();
    stdout.writeln('[webapi] mailbox SET_MODE($mode) seq=$next writeBatch=$accepted '
        'ack=${ack['$base/HmiResponse/AckSequence'] == next} '
        'accepted=${ack['$base/HmiResponse/Accepted']} '
        'diagnostic="${ack['$base/HmiResponse/Diagnostic']}" in ${w.elapsedMilliseconds}ms');

    final refused = await client.write('$base/Status/State', OpcUaWriteType.int32, 3);
    stdout.writeln('[webapi] write off the mailbox (Status/State): accepted=$refused (expect false)');
  } finally {
    await client.close();
  }
}
