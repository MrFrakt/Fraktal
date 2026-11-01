import 'dart:async';
import 'dart:convert';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

Future<void> main() async {
  final clock = Stopwatch()..start();
  void record(String event, [Object? detail]) => print(jsonEncode({
        'utc': DateTime.now().toUtc().toIso8601String(),
        'elapsedMs': clock.elapsedMilliseconds,
        'event': event,
        'detail': detail?.toString(),
        'readOnly': true,
      }));
  final idle = await CipSocketTransport.connect(
      host: '127.0.0.1', expectSerial: '601FC87B');
  record('idle-connection-ready');
  final active = await CipSocketTransport.connect(
      host: '127.0.0.1', expectSerial: '601FC87B');
  try {
    for (var i = 0; i < 100; i++) {
      await Future<void>.delayed(const Duration(seconds: 1));
      (await active.request(0x0e, cipObjectPath(1, 1, 6))).requireSuccess();
    }
    record('active-100-reads-pass');
    try {
      (await idle.request(0x0e, cipObjectPath(1, 1, 6))).requireSuccess();
      record('idle-first-read-pass');
    } on Object catch (error) {
      record('idle-first-read-failed', error);
    }
  } finally {
    await idle.close();
    await active.close();
  }
}
