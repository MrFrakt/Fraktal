// Read the mailbox members that survive processing (Kind, User, IntValue).
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
    for (final tag in ['Kind', 'IntValue', 'BoolValue', 'DurationMs']) {
      try {
        final raw = await client.client
            .connectedRead('FRK_Press_HmiRequest.$tag');
        print('$tag = ${dint(raw, 0)}');
      } on Object catch (e) {
        print('$tag read failed: $e');
      }
    }
    final user = await client.client.connectedRead('FRK_Press_HmiRequest.User');
    const o = 6;
    final len = dint(user, o);
    final text = String.fromCharCodes(
        user.sublist(o + 4, o + 4 + (len.isNegative ? 0 : len)));
    print('User.LEN=$len User="$text"');
    final target = await client.client.connectedRead('FRK_Press_HmiRequest.TargetPath');
    final tlen = dint(target, o);
    print('TargetPath.LEN=$tlen');
  } finally {
    await client.close();
  }
}
