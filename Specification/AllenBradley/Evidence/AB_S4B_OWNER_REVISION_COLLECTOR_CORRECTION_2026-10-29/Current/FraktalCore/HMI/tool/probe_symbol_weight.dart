// Dev probe: WHERE the cyclic snapshot's symbols come from.
//
// probe_map_cost tells you the transport is slow and the mapper is not; it
// cannot tell you which subtree is paying for it. This groups the snapshot's
// value keys by browse prefix so a regression in published surface — a new
// bulk array, a retained table, a module that started publishing — is a line
// item rather than a guess.
//
//   (run from FraktalCore/HMI)
//   dart run tool/probe_symbol_weight.dart [amsNetId] [amsPort] [depth]
import 'dart:io';

import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

import 'probe_read_tiers.dart';

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '192.168.1.6.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 851;
  final depth = args.length > 2 ? int.parse(args[2]) : 2;

  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    final first = await client.snapshot(); // discovery
    await applyReadTiers(client, first);
    final doc = await client.snapshot();
    final values = doc['values'];
    if (values is! Map) {
      stderr.writeln('no values map in snapshot');
      exitCode = 1;
      return;
    }
    final total = values.length;
    final byPrefix = <String, int>{};
    for (final key in values.keys) {
      final parts = '$key'.split(RegExp(r'[./]'));
      final prefix = parts.take(depth).join('.');
      byPrefix[prefix] = (byPrefix[prefix] ?? 0) + 1;
    }
    final rows = byPrefix.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    stdout.writeln('[sym] total symbols in cyclic snapshot: $total');
    stdout.writeln('[sym] (read tiers applied - this is what the HMI polls)');
    stdout.writeln('[sym] top ${rows.length < 25 ? rows.length : 25} '
        'prefixes at depth $depth:');
    for (final row in rows.take(25)) {
      final pct = (row.value * 100 / total).toStringAsFixed(1);
      stdout.writeln('  ${row.value.toString().padLeft(6)}  '
          '${pct.padLeft(5)}%  ${row.key}');
    }
  } finally {
    await client.close();
  }
}
