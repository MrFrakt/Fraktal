// Write Kind=1 (no commit), then read it back repeatedly to see whether the
// value lands and whether anything rewrites it.
//
// ignore_for_file: avoid_print
import 'dart:typed_data';

import 'package:fraktal_opcua_client/src/opcua_session_client.dart';
import '../lib/data/cip/cip_session_client.dart';

int dint(var raw, int offset) =>
    ByteData.sublistView(raw).getInt32(offset, Endian.little);

Future<void> main(List<String> args) async {
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    await client.write('Press/HmiRequest/Kind', OpcUaWriteType.int32, 1);
    print('wrote Kind=1');
    for (var i = 0; i < 8; i++) {
      final raw = await client.client.connectedRead('FRK_Press_HmiRequest.Kind');
      print('  t+${i * 200} ms: Kind=${dint(raw, 0)}');
      await Future.delayed(const Duration(milliseconds: 200));
    }
  } finally {
    await client.close();
  }
}
