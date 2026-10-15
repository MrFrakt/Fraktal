// Test-only isolated simulator guard around the production gateway/session code.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_gateway/fraktal_gateway.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

class GuardedTransport implements WebApiTransport {
  final WebApiTransport inner;
  final String simulator;
  GuardedTransport(this.inner, this.simulator);

  @override
  Future<Object?> post(Object payload, {String? token}) async {
    final requests = (payload is List ? payload : [payload]).cast<Map>();
    if (requests.any(
      (request) => (request as Map)['method'] == 'PlcProgram.Write',
    )) {
      final status = await Process.run('powershell.exe', [
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        simulator,
        '-Action',
        'status',
      ]);
      if (status.exitCode != 0)
        throw StateError('simulator status unavailable');
      final row = jsonDecode((status.stdout as String).trim()) as Map;
      final expectedName =
          Platform.environment['FRAKTAL_TIA_SIM_INSTANCE'] ?? 'FrkS12';
      if (!['FrkS12', 'Fraktal'].contains(expectedName) ||
          row['name'] != expectedName ||
          row['cpu'] != 'CPU1516' ||
          row['comm'] != 'TCPIP' ||
          !(row['addresses'] as List).contains('169.254.212.49') ||
          ['ie1', 'ie2', 'ie3'].any((key) => row[key] != 0)) {
        throw StateError('isolated simulator target differs');
      }
      stdout.writeln(
        jsonEncode({
          'event': 'mutation-guard',
          'status': row,
          'targets': [
            for (final request in requests)
              if ((request as Map)['method'] == 'PlcProgram.Write')
                (request['params'] as Map)['var'],
          ],
        }),
      );
    }
    return inner.post(payload, token: token);
  }

  @override
  Future<void> close() => inner.close();
}

Future<void> main(List<String> args) async {
  if (args.length != 3)
    throw ArgumentError('certificate, simulator script, stop file required');
  final password = Platform.environment['FRAKTAL_TIA_WEB_PASSWORD'];
  if (password == null || password.isEmpty)
    throw StateError('password environment missing');
  final client = await WebApiSessionClient.connect(
    transport: GuardedTransport(
      HttpsWebApiTransport(
        host: '169.254.212.49',
        pinnedCertificate: File(args[0]).readAsBytesSync(),
      ),
      args[1],
    ),
    user: 'fraktal',
    password: password,
    roots: const ['StationA', 'StationB'],
    batchSize: 64,
  );
  final gateway = FraktalGatewayServer(
    client,
    config: FraktalGatewayConfig(
      port: 8107,
      instanceName: 'TIA-Manifest-Bench',
      initialPlcReady: true,
      readRoots: const {'PLC1/StationA', 'PLC1/StationB'},
      writeRoots: const {'PLC1/StationA', 'PLC1/StationB'},
    ),
    log: stdout.writeln,
  );
  await gateway.start();
  stdout.writeln(jsonEncode({'event': 'bench-ready', 'port': 8107}));
  final stopped = Completer<void>();
  final timer = Timer.periodic(const Duration(milliseconds: 500), (_) {
    if (File(args[2]).existsSync() && !stopped.isCompleted) stopped.complete();
  });
  try {
    await stopped.future.timeout(const Duration(minutes: 60));
  } finally {
    timer.cancel();
    await gateway.close();
  }
}
