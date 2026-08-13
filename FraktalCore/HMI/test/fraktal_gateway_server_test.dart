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
    expect((reply['result'] as Map)['values'], client.document['values']);
    expect((reply['result'] as Map)['paths'], [
      'PLC1/MAIN/Unit/Status/Name',
    ]);
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

  test('one host runs an instance per PLC, each naming itself on /healthz',
      () async {
    // A multi-PLC host is several of these processes, one per controller. The
    // health reply is the only thing that says WHICH PLC answered, so a probe
    // on the wrong port must be obvious rather than plausible.
    final pressClient = _FakeOpcUaClient()
      ..document = {
        'protocol': 'fraktal.opcua.snapshot.v1',
        'nodeCount': 1,
        'truncated': false,
        'values': {'PLC1/MAIN/Press/Status/Name': 'Press'},
      };
    final ovenClient = _FakeOpcUaClient()
      ..snapshotError = StateError('PLC session lost');
    final press = FraktalGatewayServer(
      pressClient,
      config: FraktalGatewayConfig(port: 0, instanceName: 'press'),
    );
    final oven = FraktalGatewayServer(
      ovenClient,
      config: FraktalGatewayConfig(port: 0, instanceName: 'oven'),
    );
    addTearDown(press.close);
    addTearDown(oven.close);
    await press.start();
    await oven.start();
    expect(press.port, isNot(oven.port));

    final http = HttpClient();
    addTearDown(http.close);
    Future<Map<Object?, Object?>> health(int port) async {
      final request = await http.getUrl(
        Uri.parse('http://127.0.0.1:$port/healthz'),
      );
      final response = await request.close();
      return jsonDecode(await response.transform(utf8.decoder).join()) as Map;
    }

    final pressSocket = await WebSocket.connect(
      'ws://127.0.0.1:${press.port}/fraktal',
      headers: {'origin': 'http://localhost:7357'},
    );
    pressSocket.add(jsonEncode({
      'protocol': kFraktalGatewayProtocol,
      'id': 1,
      'method': 'snapshot',
      'params': <String, Object?>{},
    }));
    expect(
      (jsonDecode(await pressSocket.first as String) as Map)['ok'],
      isTrue,
    );
    await pressSocket.close();

    // One PLC being unreachable says nothing about the other: the sessions are
    // separate, and so is readiness.
    expect((await health(press.port))['instance'], 'press');
    expect((await health(press.port))['plcReady'], isTrue);
    expect((await health(oven.port))['instance'], 'oven');
    expect((await health(oven.port))['plcReady'], isFalse);

    // A single-gateway host stays exactly as it was: no instance field.
    server = FraktalGatewayServer(
      _FakeOpcUaClient(),
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    expect(await health(server!.port), isNot(contains('instance')));

    // The name also becomes a folder and a log directory, so it is constrained
    // rather than accepted verbatim.
    expect(
      () => FraktalGatewayConfig(port: 0, instanceName: '../evil'),
      throwsArgumentError,
    );
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

    expect(
      (await gatewayClient.snapshot())['values'],
      client.document['values'],
    );
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

  test('gateway client discovers paths, installs tiers, and bulk reads',
      () async {
    const root = 'PLC1/MAIN/Unit';
    const live = '$root/Status/State';
    const slow = '$root/Safety/State';
    const onDemand = '$root/AlarmLog/Ring/Ring[1]/State';
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 3,
      'truncated': false,
      'paths': [live, slow, onDemand],
      'values': {live: 1, slow: 2, onDemand: 3},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0, readRoots: {root}),
    );
    await server!.start();
    final gatewayClient = await IoGatewayOpcUaClient.connect(
      Uri.parse('ws://127.0.0.1:${server!.port}/fraktal'),
      headers: {'origin': 'http://localhost:7357'},
    );

    final snapshot = await gatewayClient.snapshot();
    expect(snapshot['paths'], [live, slow, onDemand]);
    expect(await gatewayClient.discoverPaths(), [live, slow, onDemand]);
    await gatewayClient.setSlowPaths([slow]);
    await gatewayClient.setExcludedPaths([onDemand]);
    expect(client.slowPaths, {slow});
    expect(client.excludedPaths, {onDemand});
    expect(await gatewayClient.readValues([onDemand]), {onDemand: 3});
    expect(client.readBatches.single, [onDemand]);
    await gatewayClient.refreshSlowPaths();
    expect(client.refreshSlowCalls, 1);

    final tieredSnapshot = await gatewayClient.snapshot();
    expect(tieredSnapshot['paths'], isEmpty,
        reason:
            'static discovery paths are not retransmitted after tier setup');
    await gatewayClient.close();
  });

  test('configured read roots filter snapshot values and discovery', () async {
    const allowed = 'PLC1/MAIN/UnitA/Status/State';
    const denied = 'PLC1/MAIN/UnitB/Status/State';
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 2,
      'truncated': false,
      'paths': [allowed, denied],
      'values': {allowed: 1, denied: 2},
      'dataValues': {
        allowed: {'value': 1, 'statusCode': 0},
        denied: {'value': 2, 'statusCode': 0},
      },
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: 0,
        readRoots: {'PLC1/MAIN/UnitA'},
      ),
    );
    await server!.start();
    final gatewayClient = await IoGatewayOpcUaClient.connect(
      Uri.parse('ws://127.0.0.1:${server!.port}/fraktal'),
      headers: {'origin': 'http://localhost:7357'},
    );

    final snapshot = await gatewayClient.snapshot();
    expect(snapshot['nodeCount'], 1);
    expect(snapshot['paths'], [allowed]);
    expect(snapshot['values'], {allowed: 1});
    expect((snapshot['dataValues'] as Map).keys, [allowed]);
    expect(await gatewayClient.discoverPaths(), [allowed]);
    await expectLater(
      gatewayClient.readValues([denied]),
      throwsA(isA<FormatException>()),
    );
    expect(client.readBatches, isEmpty);
    await gatewayClient.close();
  });

  test('shared PLC tiers use the intersection requested by every browser',
      () async {
    const live = 'PLC1/MAIN/Unit/Status/State';
    const slow = 'PLC1/MAIN/Unit/Safety/State';
    const onDemand = 'PLC1/MAIN/Unit/AlarmLog/Ring/Ring[1]/State';
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': 3,
      'truncated': false,
      'paths': [live, slow, onDemand],
      'values': {live: 1, slow: 2, onDemand: 3},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    Future<IoGatewayOpcUaClient> connectClient() =>
        IoGatewayOpcUaClient.connect(
          Uri.parse('ws://127.0.0.1:${server!.port}/fraktal'),
          headers: {'origin': 'http://localhost:7357'},
        );
    final first = await connectClient();
    final second = await connectClient();
    await first.snapshot();
    await second.snapshot();

    await first.setExcludedPaths([onDemand]);
    expect(client.excludedPaths, isEmpty,
        reason: 'an unconfigured browser still requires the full surface');
    await second.setExcludedPaths([onDemand]);
    expect(client.excludedPaths, {onDemand});

    await second.setSlowPaths([slow]);
    expect(client.slowPaths, isEmpty,
        reason: 'the first browser still requests this path at live rate');
    await first.setSlowPaths([slow]);
    expect(client.slowPaths, {slow});

    await first.close();
    await second.close();
  });

  test('large forest traffic follows the surface consumed by every browser',
      () async {
    final paths = [
      for (var root = 1; root <= 20; root++)
        for (var field = 1; field <= 200; field++)
          'PLC1/MAIN/Unit$root/Module${(field - 1) ~/ 20}/Status/Field$field',
    ];
    client.document = {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': paths.length,
      'truncated': false,
      'paths': paths,
      'values': {for (var i = 0; i < paths.length; i++) paths[i]: i},
    };
    server = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(port: 0),
    );
    await server!.start();
    Future<IoGatewayOpcUaClient> connectClient() =>
        IoGatewayOpcUaClient.connect(
          Uri.parse('ws://127.0.0.1:${server!.port}/fraktal'),
          headers: {'origin': 'http://localhost:7357'},
        );
    final browsers = await Future.wait([
      for (var i = 0; i < 4; i++) connectClient(),
    ]);
    addTearDown(() async {
      for (final browser in browsers) {
        await browser.close();
      }
    });

    final bootstrap = await Future.wait([
      for (final browser in browsers) browser.snapshot(),
    ]);
    final bootstrapBytes = utf8.encode(jsonEncode(bootstrap.first)).length;
    const consumedCount = 120;
    final excluded = paths.skip(consumedCount).toList(growable: false);
    for (final browser in browsers) {
      await browser.setExcludedPaths(excluded);
    }
    expect(client.excludedPaths.length, paths.length - consumedCount,
        reason: 'the shared upstream may exclude only the browser intersection');

    final watch = Stopwatch()..start();
    final steady = await Future.wait([
      for (final browser in browsers) browser.snapshot(),
    ]);
    watch.stop();
    for (final snapshot in steady) {
      expect((snapshot['values'] as Map).length, consumedCount);
      expect(snapshot['paths'], isEmpty,
          reason: 'discovery strings are one-time connection data');
      expect(utf8.encode(jsonEncode(snapshot)).length, lessThan(bootstrapBytes ~/ 4));
    }

    final onDemand = excluded.take(600).toList(growable: false);
    expect((await browsers.first.readValues(onDemand)).length, onDemand.length);
    expect(client.readBatches, isNotEmpty);
    expect(client.readBatches, everyElement(hasLength(lessThanOrEqualTo(512))));
    expect(watch.elapsed, lessThan(const Duration(seconds: 2)),
        reason: 'four local WebSocket clients must not starve each other');
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
    expect(
      (await reconnecting.snapshot())['values'],
      client.document['values'],
    );

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
    expect(
      (await reconnecting.snapshot())['values'],
      client.document['values'],
    );
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

class _FakeOpcUaClient
    implements
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaTieredReadClient {
  Map<String, Object?> document = {
    'protocol': 'fraktal.opcua.snapshot.v1',
    'values': <String, Object?>{},
  };
  final List<_WriteCall> writes = [];
  int snapshotCalls = 0;
  int concurrentWrites = 0;
  int maxConcurrentWrites = 0;
  int batchCalls = 0;
  int refreshSlowCalls = 0;
  Object? snapshotError;
  Set<String> slowPaths = const {};
  Set<String> excludedPaths = const {};
  final List<List<String>> readBatches = [];

  @override
  Future<Map<String, Object?>> snapshot() async {
    snapshotCalls++;
    final error = snapshotError;
    if (error != null) throw error;
    if (excludedPaths.isEmpty) return document;
    final result = Map<String, Object?>.from(document);
    final values = document['values'];
    if (values is Map) {
      result['values'] = {
        for (final entry in values.entries)
          if (!excludedPaths.contains(entry.key)) entry.key: entry.value,
      };
      result['nodeCount'] = (result['values'] as Map).length;
    }
    final dataValues = document['dataValues'];
    if (dataValues is Map) {
      result['dataValues'] = {
        for (final entry in dataValues.entries)
          if (!excludedPaths.contains(entry.key)) entry.key: entry.value,
      };
    }
    return result;
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
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    readBatches.add(List.unmodifiable(browsePaths));
    final values = document['values'];
    if (values is! Map) return const {};
    return {
      for (final path in browsePaths)
        if (values.containsKey(path)) path: values[path],
    };
  }

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    slowPaths = Set.unmodifiable(browsePaths);
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    excludedPaths = Set.unmodifiable(browsePaths);
  }

  @override
  Future<void> refreshSlowPaths() async {
    refreshSlowCalls++;
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
