// Compares the RAW linked PLC inputs against the PUBLISHED fieldbus channel
// values, twice, a moment apart. This separates the three candidate causes of
// "the fieldbus tree does not update":
//   raw changes + published frozen  -> the PLC publisher is not running
//   raw == published, both frozen   -> the I/O itself is not changing
//   both change here                -> the PLC is fine; the HMI is not re-reading
//
//   dart run tool/probe_io_values.dart <amsNetId> [amsPort]
import 'dart:io';

import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

/// Channel index -> raw GVL symbol, as wired in FB_PressIoDriver.M_RefreshFieldbus
/// for node 3 (=000+S-K010B1, EL1809 inputs).
const _node3 = <int, String>{
  1: '_101B301A',
  2: '_101B301B',
  3: '_101B201A',
  4: '_101B201B',
  5: '_101B202A',
  6: '_101B202B',
  7: '_101S101',
  8: '_101S102',
  9: '_000MB085A_2',
  10: '_000MB085A_4',
  11: '_101B601',
  12: '_000K911_Y32',
  13: '_000K910A',
};

Object? _find(Map<String, Object?> v, String suffix) {
  for (final e in v.entries) {
    if (e.key.endsWith(suffix)) return e.value;
  }
  return null;
}

Object? _channel(Map<String, Object?> v, int node, int ch, String leaf) =>
    _find(v, '/Nodes[$node]/Channels/Channels[$ch]/$leaf') ??
    _find(v, '/Nodes[$node]/Channels[$ch]/$leaf');

String _b(Object? v) => v == null ? '  ?  ' : (v == true ? ' ON  ' : ' off ');

Future<void> main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln('usage: dart run tool/probe_io_values.dart <amsNetId> [port]');
    exitCode = 64;
    return;
  }
  final client = await AdsSessionClient.connect(
      amsNetId: args[0], amsPort: args.length > 1 ? int.parse(args[1]) : 851);
  try {
    final a = Map<String, Object?>.from(
        (await client.snapshot())['values'] as Map? ?? {});
    await Future<void>.delayed(const Duration(milliseconds: 1500));
    final b = Map<String, Object?>.from(
        (await client.snapshot())['values'] as Map? ?? {});

    stdout.writeln('node 3 = =000+S-K010B1 (EL1809 inputs)   '
        'target ads://${args[0]}');
    stdout.writeln('');
    stdout.writeln('  ch  symbol           rawT0 rawT1 | pubT0 pubT1 | quality');
    stdout.writeln('  ' + '-' * 66);
    var rawChanged = 0;
    var pubChanged = 0;
    var mismatched = 0;
    for (final e in _node3.entries) {
      final raw0 = _find(a, '/GVL_PressIO/${e.value}');
      final raw1 = _find(b, '/GVL_PressIO/${e.value}');
      final pub0 = _channel(a, 3, e.key, 'BoolValue');
      final pub1 = _channel(b, 3, e.key, 'BoolValue');
      final q = _channel(b, 3, e.key, 'Quality');
      if (raw0 != raw1) rawChanged++;
      if (pub0 != pub1) pubChanged++;
      if (raw1 != pub1) mismatched++;
      stdout.writeln('  ${e.key.toString().padLeft(2)}  '
          '${e.value.padRight(15)} ${_b(raw0)}${_b(raw1)}| '
          '${_b(pub0)}${_b(pub1)}| $q');
    }
    stdout.writeln('');
    stdout.writeln('  raw values that changed between samples: $rawChanged');
    stdout.writeln('  published values that changed:           $pubChanged');
    stdout.writeln('  raw != published (publisher lagging):    $mismatched');
    final nodeState = _find(b, '/Nodes[3]/State');
    stdout.writeln('  node 3 state = $nodeState  (4 = OPERATIONAL)');
  } finally {
    await client.close();
  }
}
