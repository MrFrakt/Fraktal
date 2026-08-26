// Dev probe: dump every live value under a symbol substring, so an axis that
// will not go READY can be diagnosed from what the PLC actually publishes
// rather than from what the source suggests it should.
//
//   (run from FraktalCore/HMI)
//   dart run tool/probe_axis_state.dart [amsNetId] [amsPort] [substring]
import 'dart:io';

import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '192.168.1.6.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 851;
  final needle = args.length > 2 ? args[2] : 'PartFeed';

  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    await client.snapshot();
    final doc = await client.snapshot();
    final values = doc['values'];
    if (values is! Map) {
      stderr.writeln('no values map');
      exitCode = 1;
      return;
    }
    final hits = <String, Object?>{};
    for (final e in values.entries) {
      final k = '${e.key}';
      if (k.toLowerCase().contains(needle.toLowerCase())) hits[k] = e.value;
    }
    stdout.writeln('[axis] ${hits.length} symbols matching "$needle"');
    final keys = hits.keys.toList()..sort();
    for (final k in keys) {
      final v = hits[k];
      // Skip the obvious noise: empty strings and zeroes drown the signal.
      if (v == null) continue;
      if (v is String && v.isEmpty) continue;
      stdout.writeln('  $k = $v');
    }
  } finally {
    await client.close();
  }
}
