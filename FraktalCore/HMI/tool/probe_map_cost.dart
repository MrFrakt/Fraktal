// Dev probe: measure the UI-ISOLATE CPU cost of one refresh cycle against a real
// PLC snapshot — validate + map + the JSON decode the transport already paid.
// This runs on the main isolate exactly as OpcUaRepository._performRefresh does,
// so it exposes jank the transport probes cannot see.
//
//   (run from FraktalCore/HMI)
//   dart run tool/probe_map_cost.dart [amsNetId] [amsPort]
import 'dart:io';

import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

String _stats(List<int> us) {
  if (us.isEmpty) return 'n/a';
  final s = [...us]..sort();
  String f(int v) => (v / 1000).toStringAsFixed(1);
  return 'median=${f(s[s.length ~/ 2])}ms min=${f(s.first)}ms max=${f(s.last)}ms';
}

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '192.168.1.6.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 851;

  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    // First snapshot performs discovery; take a second for steady state.
    await client.snapshot();

    final transportUs = <int>[];
    final validateUs = <int>[];
    final mapUs = <int>[];
    final mapper = OpcUaSnapshotMapper();
    Map<String, Object?>? last;

    for (var i = 0; i < 10; i++) {
      final t = Stopwatch()..start();
      final doc = await client.snapshot();
      t.stop();
      transportUs.add(t.elapsedMicroseconds);
      last = doc;

      final v = Stopwatch()..start();
      validateCompleteOpcUaSnapshot(doc);
      v.stop();
      validateUs.add(v.elapsedMicroseconds);

      // Mirror _performRefresh: rebuild the values map, then map the projection.
      final m = Stopwatch()..start();
      final raw = doc['values'];
      if (raw is Map) {
        final values = {
          for (final e in raw.entries) '${e.key}': e.value,
        };
        mapper.map(<String, Object?>{...doc, 'values': values});
      }
      m.stop();
      mapUs.add(m.elapsedMicroseconds);
    }

    final n = (last?['values'] as Map?)?.length ?? 0;
    stdout.writeln('[map] snapshot symbols: $n');
    stdout.writeln('[map] transport snapshot(): ${_stats(transportUs)}');
    stdout.writeln('[map] validate (UI isolate): ${_stats(validateUs)}');
    stdout.writeln('[map] values-copy + mapper.map (UI isolate): ${_stats(mapUs)}');
    stdout.writeln('');
    final medMap = ([...mapUs]..sort())[mapUs.length ~/ 2];
    final medVal = ([...validateUs]..sort())[validateUs.length ~/ 2];
    stdout.writeln('[map] UI-isolate CPU per refresh ~'
        '${((medMap + medVal) / 1000).toStringAsFixed(1)}ms '
        '(blocks rendering AND the ack poll\'s await)');
  } finally {
    await client.close();
  }
}
