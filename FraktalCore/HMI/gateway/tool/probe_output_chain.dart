// Walks the "why is no output energized" chain on a live PLC.
//   dart run tool/probe_output_chain.dart <amsNetId> [port]
import 'dart:io';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

Future<void> main(List<String> a) async {
  final c = await AdsSessionClient.connect(
      amsNetId: a[0], amsPort: a.length > 1 ? int.parse(a[1]) : 851);
  try {
    final v = Map<String, Object?>.from(
        (await c.snapshot())['values'] as Map? ?? {});
    void show(String label, List<String> needles) {
      stdout.writeln('-- $label');
      var any = false;
      for (final e in v.entries) {
        final leaf = e.key.split('/').last;
        if (needles.any((n) => leaf == n || leaf.endsWith(n))) {
          stdout.writeln('   ${leaf.padRight(34)} = ${e.value}');
          any = true;
        }
      }
      if (!any) stdout.writeln('   <none published>');
    }
    show('commissioning gates (mirrors)',
        ['UseSimulation', 'ControlCircuitMappingConfirmed']);
    show('power request -> the coils', ['EnableRequestOut', 'PowerFeedback']);
    show('unit / control domain state',
        ['ModeActive', 'State', 'ReadyForStart', 'ControlOn', 'PoweredUp']);
    show('permits', ['PressureOk', 'AirPressureOk', 'PartPresent']);
  } finally {
    await c.close();
  }
}
