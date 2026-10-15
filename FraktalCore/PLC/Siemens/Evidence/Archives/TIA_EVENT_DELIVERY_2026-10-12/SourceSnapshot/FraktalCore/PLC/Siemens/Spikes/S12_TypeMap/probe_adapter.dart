// S12 live type projection through the real gateway session client and HMI date parser.
import 'dart:convert';
import 'dart:io';

import '../../../../HMI/packages/fraktal_opcua_client/lib/opcua_session_client.dart';
import '../../../../HMI/packages/fraktal_opcua_client/lib/webapi_session_client.dart';

import '../../../../HMI/lib/data/opcua_snapshot_mapper.dart';

Future<void> main(List<String> args) async {
  if (args.length != 2) throw ArgumentError('certificate DER and expected JSON are required');
  final expected = Map<String, Object?>.from(jsonDecode(File(args[1]).readAsStringSync()) as Map);
  final password = Platform.environment['FRAKTAL_TIA_WEB_PASSWORD'];
  if (password == null || password.isEmpty) throw StateError('password environment variable is absent');
  final client = await WebApiSessionClient.connect(
    transport: HttpsWebApiTransport(host: '169.254.212.49', pinnedCertificate: File(args[0]).readAsBytesSync()),
    user: 'fraktal', password: password,
    roots: const ['S12Probe', 'S12Diagnostic', 'S12ModuleStatus', 'S12StateFlag'],
  );
  try {
    final document = await client.snapshot();
    validateCompleteOpcUaSnapshot(document);
    stdout.writeln(jsonEncode({'event': 'snapshot', 'document': document}));
    final values = document['values'] as Map;
    final data = document['dataValues'] as Map;
    final failed = <String>[];
    for (final entry in expected.entries) {
      final path = 'PLC1/${entry.key.replaceAll('.', '/')}';
      final actual = values[path];
      final status = (data[path] as Map?)?['status'];
      final passed = status == 0 && actual == entry.value;
      stdout.writeln(jsonEncode({'event': 'adapter-witness', 'path': path,
        'value': actual, 'expected': entry.value, 'passed': passed}));
      if (!passed) failed.add(path);
    }
    for (final path in ['PLC1/S12Probe/StampLdt', 'PLC1/S12Diagnostic/Data/Since',
      'PLC1/S12ModuleStatus/Data/Diagnostic/Since', 'PLC1/S12StateFlag/Data/Since']) {
      final parsed = parsePlcDateTime(values[path]);
      final passed = (data[path] as Map?)?['type'] == 'DateTime' &&
          parsed == DateTime.utc(2024, 2, 29, 23, 59, 58, 123, 456);
      stdout.writeln(jsonEncode({'event': 'hmi-date', 'path': path,
        'parsed_utc': parsed?.toIso8601String(), 'passed': passed}));
      if (!passed) failed.add(path);
    }
    final bad = data.values.where((value) => (value as Map)['status'] != 0).length;
    stdout.writeln(jsonEncode({'event': 'summary', 'checked': expected.length + 4,
      'leaves': data.length, 'bad': bad, 'failed': failed, 'passed': failed.isEmpty && bad == 0}));
    if (failed.isNotEmpty || bad != 0) exitCode = 1;
  } finally {
    await client.close();
  }
}
