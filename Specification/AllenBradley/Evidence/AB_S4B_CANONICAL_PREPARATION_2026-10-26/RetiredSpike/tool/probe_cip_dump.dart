// Raw reply dump: nails the connected Read Tag reply header length for
// structure and DINT element reads on the Echo v38 controller.
// Usage: dart run tool/probe_cip_dump.dart [host]
//
// ignore_for_file: avoid_print
import '../lib/data/cip/cip_session_client.dart';

Future<void> main(List<String> args) async {
  final host = args.isNotEmpty ? args[0] : '127.0.0.1';
  final client = await CipSessionClient.connect(host: host);
  try {
    for (final tag in [
      'FRK_Press_MfHeader', // struct: known KARF magic at data start
      'FRK_Press_HmiResponse', // struct: AckSequence/Accepted/DiagnosticKey
      'FRK_Press_HmiRequest.Sequence', // plain DINT member (we wrote 1)
      'FRK_Press_Unit.Mode', // plain DINT member (0..4)
      'FRK_Press_MfHeader.KeyLength', // DINT member, known = 56 (0x38)
      'FRK_Press_Unit', // whole unit struct for scale
    ]) {
      try {
        final raw = await client.readRawConnected(tag);
        print('$tag (${raw.length} B): '
            '${raw.take(32).map((b) => b.toRadixString(16).padLeft(2, '0')).join(' ')}');
      } on Object catch (error) {
        print('$tag FAILED: $error');
      }
    }
  } finally {
    await client.close();
  }
}
