// Dev probe: connect over ADS and dump exactly what the PLC publishes for the
// fieldbus topology + FB_EcBusHealth diagnostics. Isolates which layer is wrong
// (PLC values vs. ADS expansion vs. HMI mapping) instead of guessing from the UI.
//
//   dart run tool/probe_ads_fieldbus.dart [amsNetId] [amsPort]
//   dart run tool/probe_ads_fieldbus.dart 127.0.0.1.1.1 852
//
// fraktal_ads.dll must be in the CWD (the gateway dir).
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/ads_session_client.dart';

Future<void> main(List<String> args) async {
  final netId = args.isNotEmpty ? args[0] : '127.0.0.1.1.1';
  final port = args.length > 1 ? int.parse(args[1]) : 852;

  stdout.writeln('[probe] connecting ads://$netId:$port ...');
  final client = await AdsSessionClient.connect(amsNetId: netId, amsPort: port);
  try {
    final snap = await client.snapshot();
    final values = snap['values'];
    if (values is! Map) {
      stdout.writeln('[probe] snapshot has no values map; keys=${snap.keys}');
      return;
    }

    // Everything the PLC publishes whose path mentions the fieldbus/topology or
    // the new bus-health diagnostics.
    final interesting = <String, Object?>{};
    for (final e in values.entries) {
      final k = '${e.key}';
      final lk = k.toLowerCase();
      if (lk.contains('fieldbus') ||
          lk.contains('topology') ||
          lk.contains('node') ||
          lk.contains('bushealth') ||
          lk.contains('readok') ||
          lk.contains('netid') ||
          lk.contains('slaves')) {
        interesting[k] = e.value;
      }
    }

    stdout.writeln('[probe] total published symbols: ${values.length}');
    stdout.writeln('[probe] fieldbus-related: ${interesting.length}');
    stdout.writeln('');

    final keys = interesting.keys.toList()..sort();
    for (final k in keys) {
      stdout.writeln('  $k = ${jsonEncode(interesting[k])}');
    }

    if (interesting.isEmpty) {
      stdout.writeln('[probe] NOTHING fieldbus-related published. Sample paths:');
      final sample = values.keys.map((e) => '$e').toList()..sort();
      for (final k in sample.take(40)) {
        stdout.writeln('  $k');
      }
    }
  } finally {
    await client.close();
  }
}
