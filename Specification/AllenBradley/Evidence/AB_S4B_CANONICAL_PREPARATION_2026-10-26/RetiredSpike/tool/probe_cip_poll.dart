// Replicates the repository's ack poll against readValues, plus a direct
// snapshot for comparison.
//
// ignore_for_file: avoid_print
import '../lib/data/cip/cip_session_client.dart';

Future<void> main(List<String> args) async {
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    final paths = [
      'Press/HmiResponse/AckSequence',
      'Press/HmiResponse/Accepted',
      'Press/HmiResponse/Diagnostic',
    ];
    final snapshot = await client.snapshot();
    final values = snapshot['values'] as Map<String, Object?>;
    print('snapshot: ${values.length} values, '
        'ack=${values['Press/HmiResponse/AckSequence']}');
    final read = await client.readValues(paths);
    print('readValues: ${read.length} entries');
    read.forEach((k, v) => print('  $k = $v'));
  } finally {
    await client.close();
  }
}
