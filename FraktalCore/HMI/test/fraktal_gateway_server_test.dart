import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_gateway/fraktal_gateway.dart';
import 'package:fraktal_hmi/data/opcua_gateway_client_io.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/reconnecting_opcua_session_client.dart';

void main() {
  late _FakeOpcUaClient client;
  FraktalGatewayServer? server;

  setUp(() {
    client = _FakeOpcUaClient();
  });

  tearDown(() async {
    await server?.close();
  });

  Future<WebSocket> connect({String origin = 'http://localhost:7357'}) =>
      WebSocket.connect(
        'ws://127.0.0.1:${server!.port}/fraktal',
        headers: {'origin': origin},
      );

  test('snapshot reply preserves the native snapshot document', () async {
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 2,
      'truncated': false,
      'values': {'PLC1/MAIN/Unit/Status/Name': 'Unit'},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final socket = await connect();
    socket.add(jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': 1,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));

    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['id'], 1);
    expect(reply['ok'], isTrue);
    expect(reply['result'], client.document);
    await socket.close();
  });

  test('readiness degrades after an observed PLC failure but liveness stays up',
      () async {
    client.snapshotError = StateError('PLC session lost');
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final socket = await connect();
    socket.add(jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': 1,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));
    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['ok'], isFalse);

    final http = HttpClient();
    addTearDown(http.close);
    final readyRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/readyz'),
    );
    final readyResponse = await readyRequest.close();
    expect(readyResponse.statusCode, HttpStatus.serviceUnavailable);
    await readyResponse.drain<void>();
    final liveRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/livez'),
    );
    final liveResponse = await liveRequest.close();
    expect(liveResponse.statusCode, HttpStatus.ok);
    await liveResponse.drain<void>();
    await socket.close();
  });

  test('truncated snapshots are refused and keep readiness degraded', () async {
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 20000,
      'truncated': true,
      'values': {'PLC1/MAIN/Unit/Status/Name': 'Unit'},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final socket = await connect();
    socket.add(jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': 1,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));

    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['ok'], isFalse);
    expect(reply['error'], allOf(contains('truncated'), contains('20000')));

    final http = HttpClient();
    addTearDown(() => http.close(force: true));
    final request = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/readyz'),
    );
    final response = await request.close();
    expect(response.statusCode, HttpStatus.serviceUnavailable);
    await response.drain<void>();
    await socket.close();
  });

  test('readiness is fail-closed until a PLC operation succeeds', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final http = HttpClient();
    addTearDown(() => http.close(force: true));

    final initialRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/readyz'),
    );
    final initialResponse = await initialRequest.close();
    expect(initialResponse.statusCode, HttpStatus.serviceUnavailable);
    await initialResponse.drain<void>();

    final socket = await connect();
    socket.add(jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': 1,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));
    await socket.first;

    final readyRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/readyz'),
    );
    final readyResponse = await readyRequest.close();
    expect(readyResponse.statusCode, HttpStatus.ok);
    await readyResponse.drain<void>();
    await socket.close();
  });

  test('optional Web root serves the HMI and SPA routes from the same origin',
      () async {
    final webRoot = await Directory.systemTemp.createTemp('fraktal-web-test-');
    addTearDown(() => webRoot.delete(recursive: true));
    await File('${webRoot.path}/index.html').writeAsString('<h1>Fraktal</h1>');
    await File('${webRoot.path}/main.dart.js').writeAsString('main();');
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0, webRoot: webRoot),
    );
    await server!.start();
    final http = HttpClient();
    addTearDown(() => http.close(force: true));

    for (final path in ['/', '/operator']) {
      final request = await http.getUrl(
        Uri.parse('http://127.0.0.1:${server!.port}$path'),
      );
      final response = await request.close();
      expect(response.statusCode, HttpStatus.ok);
      expect(response.headers.contentType?.mimeType, 'text/html');
      expect(await utf8.decodeStream(response), contains('Fraktal'));
    }
    final scriptRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/main.dart.js'),
    );
    final scriptResponse = await scriptRequest.close();
    expect(scriptResponse.statusCode, HttpStatus.ok);
    expect(scriptResponse.headers.value('x-content-type-options'), 'nosniff');
    await scriptResponse.drain<void>();

    final missingRequest = await http.getUrl(
      Uri.parse('http://127.0.0.1:${server!.port}/missing.js'),
    );
    final missingResponse = await missingRequest.close();
    expect(missingResponse.statusCode, HttpStatus.notFound);
    await missingResponse.drain<void>();
  });

  test('native IO client uses the same snapshot and write protocol', () async {
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {'PLC1/MAIN/Unit/Status/Name': 'Unit'},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        writeRoots: {'PLC1/MAIN/Unit'},
      ),
    );
    await server!.start();
    final gatewayClient = await IoGatewayOpcUaClient.connect(
      Uri.parse('ws://127.0.0.1:${server!.port}/fraktal'),
      headers: {'origin': 'http://localhost:7357'},
    );

    expect(await gatewayClient.snapshot(), client.document);
    expect(
      await gatewayClient.write(
        'PLC1/MAIN/Unit/HmiRequest/Kind',
        OpcUaWriteType.int32,
        4,
      ),
      isTrue,
    );
    expect(client.writes.single.path, 'PLC1/MAIN/Unit/HmiRequest/Kind');
    expect(
      await gatewayClient.writeBatch([
        const OpcUaWrite(
          'PLC1/MAIN/Unit/HmiRequest/Kind',
          OpcUaWriteType.int32,
          5,
        ),
        const OpcUaWrite(
          'PLC1/MAIN/Unit/HmiRequest/Sequence',
          OpcUaWriteType.uint32,
          1,
        ),
      ]),
      isTrue,
    );
    expect(client.batchCalls, 1);
    await gatewayClient.close();
  });

  test('native gateway client reconnects after a gateway restart', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final port = server!.port;
    Future<OpcUaSessionClient> connectClient() => IoGatewayOpcUaClient.connect(
          Uri.parse('ws://127.0.0.1:$port/fraktal'),
          headers: {'origin': 'http://localhost:7357'},
        );
    final reconnecting = await ReconnectingOpcUaSessionClient.connect(
      factory: connectClient,
      baseBackoff: const Duration(milliseconds: 1),
      maxBackoff: const Duration(milliseconds: 1),
    );
    addTearDown(reconnecting.close);
    expect(await reconnecting.snapshot(), client.document);

    await server!.close();
    server = null;
    await expectLater(
      reconnecting.snapshot(),
      throwsA(isA<OpcUaTransportException>()),
    );

    client = _FakeOpcUaClient();
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: port),
    );
    await server!.start();
    await Future<void>.delayed(const Duration(milliseconds: 3));
    expect(await reconnecting.snapshot(), client.document);
  });

  test('mailbox batches are globally serialized without field interleaving',
      () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        allowAllRootMailboxes: true,
      ),
    );
    await server!.start();
    final first = await connect();
    final second = await connect(origin: 'http://127.0.0.1:8123');
    first.add(_batchRequest(1, 1, 4));
    await Future<void>.delayed(const Duration(milliseconds: 5));
    second.add(_batchRequest(2, 2, 5));

    final replies = await Future.wait([
      first.first,
      second.first,
    ]);
    final decoded =
        replies.map((reply) => jsonDecode(reply as String) as Map).toList();
    expect(decoded, everyElement(containsPair('ok', true)));
    expect(decoded, everyElement(containsPair('result', true)));
    expect(client.maxConcurrentWrites, 1);
    expect(client.batchCalls, 2);
    expect(client.writes.map((write) => write.path), [
      'PLC1/MAIN/Unit/HmiRequest/Kind',
      'PLC1/MAIN/Unit/HmiRequest/Sequence',
      'PLC1/MAIN/Unit/HmiRequest/Kind',
      'PLC1/MAIN/Unit/HmiRequest/Sequence',
    ]);
    await first.close();
    await second.close();
  });

  test('duplicate mailbox sequence is refused without a second PLC write',
      () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        allowAllRootMailboxes: true,
      ),
    );
    await server!.start();
    final socket = await connect();
    socket.add(_batchRequest(1, 7, 4));
    socket.add(_batchRequest(2, 7, 5));
    final replies = (await socket.take(2).toList())
        .map((value) => jsonDecode(value as String) as Map)
        .toList();
    expect(replies[0]['result'], isTrue);
    expect(replies[1]['ok'], isTrue);
    expect(replies[1]['result'], isFalse);
    expect(client.batchCalls, 1);
    await socket.close();
  });

  test('Sequence cannot be written outside a commit-last batch', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        allowAllRootMailboxes: true,
      ),
    );
    await server!.start();
    final socket = await connect();
    socket.add(_writeRequest(
      1,
      'PLC1/MAIN/Unit/HmiRequest/Sequence',
      'uint32',
      1,
    ));
    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['ok'], isFalse);
    expect(client.writes, isEmpty);
    await socket.close();
  });

  test('write roots and HmiRequest boundary are fail-closed', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        writeRoots: {'PLC1/MAIN/UnitA'},
      ),
    );
    await server!.start();
    final socket = await connect();
    socket.add(_writeRequest(
      1,
      'PLC1/MAIN/UnitB/HmiRequest/Kind',
      'int32',
      4,
    ));
    socket.add(_writeRequest(
      2,
      'PLC1/MAIN/UnitA/ParCfg/Timeout',
      'uint32',
      100,
    ));

    final replies = (await socket.take(2).toList())
        .map((reply) => jsonDecode(reply as String) as Map)
        .toList();
    expect(replies, everyElement(containsPair('ok', false)));
    expect(client.writes, isEmpty);
    await socket.close();
  });

  test('writes default to read-only until a root is configured', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final socket = await connect();
    socket.add(_writeRequest(
      1,
      'PLC1/MAIN/Unit/HmiRequest/Kind',
      'int32',
      4,
    ));

    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['ok'], isFalse);
    expect(client.writes, isEmpty);
    await socket.close();
  });

  test('unknown protocol is refused without touching OPC UA', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    final socket = await connect();
    socket.add(jsonEncode({
      'protocol': 'fraktal.opcua.gateway.v2',
      'id': 8,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));

    final reply = jsonDecode(await socket.first as String) as Map;
    expect(reply['ok'], isFalse);
    expect(client.snapshotCalls, 0);
    await socket.close();
  });

  test('non-allowlisted remote origin cannot upgrade', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();

    await expectLater(
      connect(origin: 'https://untrusted.example'),
      throwsA(isA<WebSocketException>()),
    );
  });

  test('an exact configured reverse-proxy origin can upgrade', () async {
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        allowedOrigins: {'https://hmi.example'},
      ),
    );
    await server!.start();

    final socket = await connect(origin: 'https://hmi.example');
    expect(socket.readyState, WebSocket.open);
    await socket.close();
  });
}

String _writeRequest(
  int id,
  String path,
  String valueType,
  Object value,
) =>
    jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': id,
      'method': 'write',
      'params': {
        'path': path,
        'valueType': valueType,
        'value': value,
      },
    });

String _batchRequest(int id, int sequence, int kind) => jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': id,
      'method': 'writeBatch',
      'params': {
        'writes': [
          {
            'path': 'PLC1/MAIN/Unit/HmiRequest/Kind',
            'valueType': 'int32',
            'value': kind,
          },
          {
            'path': 'PLC1/MAIN/Unit/HmiRequest/Sequence',
            'valueType': 'uint32',
            'value': sequence,
          },
        ],
      },
    });

class _FakeOpcUaClient implements OpcUaBatchSessionClient {
  Map<String, Object?> document = {
    'protocol': 'fraktal.opcua.snapshot.v1',
    'values': <String, Object?>{},
  };
  final List<_WriteCall> writes = [];
  int snapshotCalls = 0;
  int concurrentWrites = 0;
  int maxConcurrentWrites = 0;
  int batchCalls = 0;
  Object? snapshotError;

  @override
  Future<Map<String, Object?>> snapshot() async {
    snapshotCalls++;
    final error = snapshotError;
    if (error != null) throw error;
    return document;
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    concurrentWrites++;
    if (concurrentWrites > maxConcurrentWrites) {
      maxConcurrentWrites = concurrentWrites;
    }
    writes.add(_WriteCall(path, type, value));
    await Future<void>.delayed(const Duration(milliseconds: 20));
    concurrentWrites--;
    return true;
  }

  @override
  Future<bool> writeBatch(List<OpcUaWrite> values) async {
    batchCalls++;
    for (final value in values) {
      if (!await write(value.path, value.type, value.value)) return false;
    }
    return true;
  }

  @override
  Future<void> close() async {}
}

class _WriteCall {
  final String path;
  final OpcUaWriteType type;
  final Object value;

  const _WriteCall(this.path, this.type, this.value);
}
