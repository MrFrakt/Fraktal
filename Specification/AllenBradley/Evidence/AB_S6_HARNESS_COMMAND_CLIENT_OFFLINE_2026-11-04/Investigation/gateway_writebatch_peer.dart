// Evidence apparatus: the real FraktalGatewayServer over a recording upstream.
// Prints {"port": N}, serves until a line arrives on stdin, then prints every
// write the gateway forwarded upstream. No PLC, no network beyond loopback.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:fraktal_gateway/fraktal_gateway.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';

class _Recording implements OpcUaBatchSessionClient {
  final List<List<Map<String, Object?>>> batches = [];

  @override
  Future<Map<String, Object?>> snapshot() async => {
        'protocol': 'fraktal.opcua.snapshot.v1',
        'values': <String, Object?>{},
      };

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      false; // a standalone write is never a command

  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    batches.add([
      for (final w in writes)
        {'path': w.path, 'valueType': w.type.name, 'value': w.value}
    ]);
    return true;
  }

  @override
  Future<void> close() async {}
}

Future<void> main() async {
  final upstream = _Recording();
  final server = FraktalGatewayServer(upstream,
      config: FraktalGatewayConfig(port: 0, writeRoots: {'Press'}));
  await server.start();
  stdout.writeln(jsonEncode({'port': server.port}));
  await stdin.transform(utf8.decoder).transform(const LineSplitter()).first;
  stdout.writeln(jsonEncode({'batches': upstream.batches}));
  await server.close();
  exit(0);
}
