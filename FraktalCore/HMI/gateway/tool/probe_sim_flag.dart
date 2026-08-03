// Is the running PLC clearing physical outputs because it is in simulation?
//   dart run tool/probe_sim_flag.dart <amsNetId> [port]
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

Future<void> main(List<String> args) async {
  final c = await AdsSessionClient.connect(
      amsNetId: args[0], amsPort: args.length > 1 ? int.parse(args[1]) : 851);
  try {
    final v = Map<String, Object?>.from(
        (await c.snapshot())['values'] as Map? ?? {});
    const want = ['UseSimulation', 'SimulationActive', 'RealBusOk',
        'ControlCircuitMappingConfirmed', 'FieldbusViewActive'];
    for (final w in want) {
      final hits = v.entries.where((e) => e.key.endsWith('/$w') ||
          e.key.endsWith('.$w') || e.key.split('/').last == w);
      if (hits.isEmpty) {
        stdout.writeln('  $w = <not published>');
      } else {
        for (final h in hits.take(3)) {
          stdout.writeln('  ${h.key.split('/').last.padRight(32)} = ${h.value}');
        }
      }
    }
    // Output coil mirrors, if published.
    stdout.writeln('');
    for (final e in v.entries) {
      final k = e.key;
      if (k.contains('K951') || k.contains('K911_A1') ||
          k.contains('K301') || k.contains('K202')) {
        stdout.writeln('  ${k.split('/').last.padRight(32)} = ${e.value}');
      }
    }
  } finally {
    await c.close();
  }
}
