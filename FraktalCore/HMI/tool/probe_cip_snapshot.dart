// Dump the CIP snapshot's keys and the response values.
//
// ignore_for_file: avoid_print
import '../lib/data/cip/cip_session_client.dart';

Future<void> main(List<String> args) async {
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    final snapshot = await client.snapshot();
    final values = snapshot['values'] as Map<String, Object?>;
    print('${values.length} values');
    for (final entry in values.entries) {
      if (entry.key.contains('HmiResponse') || entry.key.contains('Access')) {
        print('  ${entry.key} = ${entry.value}');
      }
    }
  } finally {
    await client.close();
  }
}
