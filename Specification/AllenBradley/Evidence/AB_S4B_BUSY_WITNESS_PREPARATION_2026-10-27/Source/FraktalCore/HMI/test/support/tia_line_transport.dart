// Test-only guard; the production session/repository still owns the protocol.
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_opcua_client/webapi_session_client.dart';

class GuardedLineTransport implements WebApiTransport {
  final WebApiTransport inner;
  final String helper;
  final String profile;
  GuardedLineTransport(this.inner, this.helper, this.profile);

  @override
  Future<Object?> post(Object payload, {String? token}) async {
    final requests = (payload is List ? payload : [payload]).cast<Map>();
    if (requests.any((r) => r['method'] == 'PlcProgram.Write')) {
      // A status process can fail during the native SDK finalizer. Retrying
      // this observation is safe; the pending PLC write has not been sent.
      ProcessResult? result;
      for (var attempt = 0; attempt < 3; attempt++) {
        result = await Process.run('powershell.exe', [
          '-NoProfile',
          '-ExecutionPolicy',
          'Bypass',
          '-File',
          helper,
          '-Profile',
          profile,
          '-Action',
          'status',
        ]);
        if (result.exitCode == 0) break;
        stdout.writeln(
            '[Fraktal/Test] line-guard-observation-retry exit=${result.exitCode}');
      }
      if (result == null || result.exitCode != 0) {
        throw StateError(
            'line bench guard unavailable; pending write not sent');
      }
      final rows = (result.stdout as String)
          .split('\n')
          .where((line) => line.trim().startsWith('{'))
          .map(jsonDecode)
          .cast<Map>();
      final status = rows.single;
      if (status['name'] != 'FrkLineOwnerTest' ||
          status['cpu'] != 'CPU1516' ||
          status['address'] != '169.254.212.53' ||
          status['state'] != 'Run' ||
          ['ie1', 'ie2', 'ie3'].any((k) => status[k] != 0)) {
        throw StateError('isolated line bench differs');
      }
    }
    return inner.post(payload, token: token);
  }

  @override
  Future<void> close() => inner.close();
}
