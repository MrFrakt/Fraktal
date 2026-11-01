import 'dart:async';
import 'dart:convert';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';

Future<void> main() async {
  final clock = Stopwatch()..start();
  void record(String event, [Object? detail]) => print(jsonEncode({
        'utc': DateTime.now().toUtc().toIso8601String(),
        'elapsedMs': clock.elapsedMilliseconds,
        'event': event,
        'detail': detail,
        'readOnly': true,
        'controllerWrites': 0,
      }));
  final pool = await CipReadPool.connect(
      host: '127.0.0.1', expectSerial: '601FC87B');
  final originals = await Future.wait(List.generate(
      4, (_) => pool.withGroup((wire) async => wire as CipSocketTransport)));
  record('pool-ready');
  final active = await CipSocketTransport.connect(
      host: '127.0.0.1', expectSerial: '601FC87B');
  try {
    for (var i = 0; i < 100; i++) {
      await Future<void>.delayed(const Duration(seconds: 1));
      (await active.request(0x0e, cipObjectPath(1, 1, 6))).requireSuccess();
    }
    record('idle-sockets-closed', originals.where((w) => w.closedWhileIdle).length);
    final replies = await Future.wait(List.generate(4, (_) => pool.withGroup((wire) async {
      final reply = await wire.request(0x0e, cipObjectPath(1, 1, 6));
      reply.requireSuccess();
      return reply.data.toList();
    })));
    record('all-four-renewed-reads-pass', replies);
  } finally {
    await pool.close();
    await active.close();
  }
}
