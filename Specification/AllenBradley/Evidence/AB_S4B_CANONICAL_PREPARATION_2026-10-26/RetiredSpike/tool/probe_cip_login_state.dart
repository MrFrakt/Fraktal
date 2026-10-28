// Full published access state. Raw member reads carry
// [addSize(2)][type(2)][instance(2)] before the struct: members start at 6.
// Layout (FRK_T_AccessStateV3): SchemaVersion, CurrentLevel, UserLength,
// LoginFailed, LoginBusy, SessionTimeout, Required[12], UserBytes[32],
// LoginTimeoutMs, LoginPrehashRounds, LoginResultSequence.
//
// ignore_for_file: avoid_print
import 'dart:typed_data';

import '../lib/data/cip/cip_session_client.dart';

int dint(Uint8List raw, int offset) =>
    ByteData.sublistView(raw).getInt32(offset, Endian.little);

Future<void> main(List<String> args) async {
  const o = 6; // addSize(2) + type(2) + instance(2)
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    final state = await client.readRawConnected('FRK_Press_AccessState');
    print('SchemaVersion=${dint(state, o)} CurrentLevel=${dint(state, o + 4)} '
        'UserLength=${dint(state, o + 8)}');
    print('LoginFailed=${dint(state, o + 12)} LoginBusy=${dint(state, o + 16)} '
        'SessionTimeout=${dint(state, o + 20)}');
    const tail = o + 24 + 12 * 4 + 128;
    print('LoginTimeoutMs=${dint(state, tail)} '
        'LoginPrehashRounds=${dint(state, tail + 4)} '
        'LoginResultSequence=${dint(state, tail + 8)}');
    final resp = await client.readRawConnected('FRK_Press_HmiResponse');
    print('HmiResponse: ack=${dint(resp, o)} accepted=${dint(resp, o + 4)} '
        'diag=${dint(resp, o + 8)}');
    final seq = await client.client.connectedRead('FRK_Press_HmiRequest.Sequence');
    print('HmiRequest.Sequence=${dint(seq, 0)}');
  } finally {
    await client.close();
  }
}
