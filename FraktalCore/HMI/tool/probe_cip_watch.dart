// Watch the mailbox sequence for 12 s to measure concurrent writer traffic.
//
// ignore_for_file: avoid_print
import 'dart:typed_data';
import '../lib/data/cip/cip_session_client.dart';

int dint(var raw, int offset) =>
    ByteData.sublistView(raw).getInt32(offset, Endian.little);

Future<void> main(List<String> args) async {
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    var last = -1, changes = 0;
    final lastKind = <int>[];
    for (var i = 0; i < 40; i++) {
      final seq = await client.client.connectedRead('FRK_Press_HmiRequest.Sequence');
      final kind = await client.client.connectedRead('FRK_Press_HmiRequest.Kind');
      final v = dint(seq, 0);
      if (last >= 0 && v != last) {
        changes++;
        lastKind.add(dint(kind, 0));
      }
      last = v;
      await Future.delayed(const Duration(milliseconds: 300));
    }
    print('sequence $last, $changes commits in 12 s, kinds seen: $lastKind');
  } finally {
    await client.close();
  }
}
