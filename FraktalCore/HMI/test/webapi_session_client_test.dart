import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

/// A fake S7 CPU Web API reproducing the behaviour measured on a 1214C V4.7.3
/// (Specification/Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md): leaf-only
/// reads (204 on a structure), 205 on a read-only leaf, 101 on a second login,
/// 2 for an expired token, browse of the root lists DBs.
class _FakeCpu implements WebApiTransport {
  // Tree: name -> child map (structure) or _Leaf.
  final Map<String, Object> dbs = {
    'Unit': {
      'Status': {
        'Name': _Leaf('string', 'Unit'),
        'ModuleType': _Leaf('dint', 1),
        'State': _Leaf('dint', 0),
      },
      'Busy': _Leaf('bool', false),
      'Trace': _Array(0, 2, _Leaf('int', 7)),
      'CylA': {
        'Status': {
          'Name': _Leaf('string', 'Unit.CylA'),
          'ModuleType': _Leaf('dint', 3),
          'State': _Leaf('dint', 2),
        },
        'Execute': _Leaf('bool', false),
      },
      'HmiRequest': {
        'Kind': _Leaf('dint', 0, writable: true),
        'IntValue': _Leaf('dint', 0, writable: true),
        'Sequence': _Leaf('udint', 5, writable: true),
      },
      'Odd': _Leaf('unsupported', null),
      'Broken': _Leaf('dint', 0, readError: 204),
    },
    'Clock': {'NowMs': _Leaf('udint', 1)},
  };

  final List<List<Map<String, Object?>>> requests = [];
  final List<String?> tokens = [];
  String validToken = 'T1';
  int logins = 0;
  bool expireNextCall = false;
  bool revoked = false; // the user lost the right: every data call answers 2

  @override
  Future<Object?> post(Object payload, {String? token}) async {
    final batch = [for (final r in payload as List) Map<String, Object?>.from(r as Map)];
    requests.add(batch);
    tokens.add(token);
    final expired = expireNextCall;
    expireNextCall = false;
    // Round-trip through JSON so the client sees only wire types.
    return jsonDecode(jsonEncode([
      for (final r in batch) {'jsonrpc': '2.0', 'id': r['id'], ..._answer(r, token, expired)},
    ]));
  }

  Map<String, Object?> _answer(Map<String, Object?> r, String? token, bool expired) {
    final method = r['method'];
    final params = (r['params'] as Map?) ?? const {};
    if (method == 'Api.Login') {
      if (token != null) return _err(101, 'Already authenticated');
      logins++;
      validToken = 'T$logins';
      return {'result': {'token': validToken}};
    }
    if (method == 'Api.Logout') return {'result': true};
    if (expired || revoked || token != validToken) return _err(2, 'Permission denied');
    final varName = params['var'] as String?;
    switch (method) {
      case 'PlcProgram.Browse':
        if (varName == null) {
          return {
            'result': [
              for (final db in dbs.keys) {'name': db, 'has_children': true, 'datatype': 'datablock'},
            ]
          };
        }
        final node = _resolve(varName);
        if (node is! Map) return _err(200, 'Address does not exist');
        return {'result': [for (final e in node.entries) _describe(e.key as String, e.value as Object)]};
      case 'PlcProgram.Read':
        final node = _resolve(varName!);
        if (node == null) return _err(200, 'Address does not exist');
        if (node is! _Leaf) return _err(204, 'Unsupported address');
        if (node.readError != null) return _err(node.readError!, 'Unsupported address');
        return {'result': node.value};
      case 'PlcProgram.Write':
        final node = _resolve(varName!);
        if (node is! _Leaf) return _err(200, 'Address does not exist');
        if (!node.writable) return _err(205, 'Address is read-only');
        node.value = params['value'];
        return {'result': true};
    }
    return _err(-32601, 'Method not found');
  }

  Map<String, Object?> _describe(String name, Object node) => switch (node) {
        _Leaf leaf => {'name': name, 'datatype': leaf.type},
        _Array array => {
            'name': name,
            'datatype': array.element.type,
            'array_dimensions': [
              {'start_index': array.start, 'count': array.count}
            ],
          },
        _ => {'name': name, 'has_children': true, 'datatype': 'struct'},
      };

  /// `"Unit"."Trace"[1]` -> the node. Every segment must be quoted, as the
  /// client always does; an unquoted name is treated as not found.
  Object? _resolve(String webVar) {
    final parts = RegExp(r'"([^"]+)"(\[(\d+)\])?').allMatches(webVar).toList();
    Object? node = dbs;
    for (final m in parts) {
      if (node is! Map) return null;
      node = node[m.group(1)];
      if (m.group(3) != null) {
        if (node is! _Array) return null;
        final i = int.parse(m.group(3)!);
        if (i < node.start || i >= node.start + node.count) return null;
        node = node.element;
      }
    }
    return node;
  }

  static Map<String, Object?> _err(int code, String message) =>
      {'error': {'code': code, 'message': message}};

  bool closed = false;
  @override
  Future<void> close() async => closed = true;

  /// The methods of the most recent requests, in order.
  List<String> get lastWrites => [
        for (final batch in requests)
          for (final r in batch)
            if (r['method'] == 'PlcProgram.Write') '${(r['params'] as Map)['var']}',
      ];
}

class _Leaf {
  final String type;
  Object? value;
  final bool writable;
  final int? readError;
  _Leaf(this.type, this.value, {this.writable = false, this.readError});
}

class _Array {
  final int start;
  final int count;
  final _Leaf element;
  _Array(this.start, this.count, this.element);
}

Future<WebApiSessionClient> _connect(_FakeCpu cpu, {int batchSize = 4, DateTime Function()? now}) =>
    WebApiSessionClient.connect(
      transport: cpu,
      user: 'fraktal',
      password: 'secret',
      batchSize: batchSize,
      now: now,
    );

void main() {
  test('discovers roots by Status, expands structures and arrays to quoted leaves', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    final paths = await client.discoverPaths();
    expect(paths, containsAll(<String>[
      'PLC1/Unit/Status/Name',
      'PLC1/Unit/CylA/Status/State',
      'PLC1/Unit/Trace[0]',
      'PLC1/Unit/Trace[1]',
      'PLC1/Unit/HmiRequest/Sequence',
    ]));
    // A DB without a top-level Status is not a module root.
    expect(paths.where((p) => p.startsWith('PLC1/Clock')), isEmpty);
    // An unsupported datatype is never a leaf: it could not be read.
    expect(paths, isNot(contains('PLC1/Unit/Odd')));
    final reads = [
      for (final batch in cpu.requests)
        for (final r in batch)
          if (r['method'] == 'PlcProgram.Browse') (r['params'] as Map)['var'],
    ];
    expect(reads, contains('"Unit"."CylA"."Status"'));
  });

  test('snapshot is the shared v1 document: Good values, Bad leaves stay Bad', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    final doc = await client.snapshot();
    expect(doc['protocol'], 'fraktal.opcua.snapshot.v1');
    expect(doc['truncated'], isFalse);
    final values = doc['values'] as Map;
    expect(values['PLC1/Unit/Status/Name'], 'Unit');
    expect(values['PLC1/Unit/CylA/Status/ModuleType'], 3);
    expect(values['PLC1/Unit/Trace[1]'], 7);
    expect(values.containsKey('PLC1/Unit/Broken'), isFalse);
    final dataValues = doc['dataValues'] as Map;
    expect((dataValues['PLC1/Unit/Broken'] as Map)['status'], 0x80000000);
    expect((dataValues['PLC1/Unit/Busy'] as Map)['type'], 'Boolean');
    expect((dataValues['PLC1/Unit/HmiRequest/Sequence'] as Map)['type'], 'UInt32');
  });

  test('no request carries more than the batch size', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu, batchSize: 3);
    await client.snapshot();
    expect(cpu.requests.map((b) => b.length), everyElement(lessThanOrEqualTo(3)));
  });

  test('mailbox: arguments first in one request, the commit marker alone and last', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    cpu.requests.clear();
    final ok = await client.writeBatch(const [
      OpcUaWrite('PLC1/Unit/HmiRequest/Kind', OpcUaWriteType.int32, 3),
      OpcUaWrite('PLC1/Unit/HmiRequest/IntValue', OpcUaWriteType.int32, 1),
      OpcUaWrite('PLC1/Unit/HmiRequest/Sequence', OpcUaWriteType.uint32, 6),
    ]);
    expect(ok, isTrue);
    expect(cpu.requests, hasLength(2));
    expect(cpu.requests[0].map((r) => (r['params'] as Map)['var']),
        ['"Unit"."HmiRequest"."Kind"', '"Unit"."HmiRequest"."IntValue"']);
    expect(cpu.requests[1].single['params'], {'var': '"Unit"."HmiRequest"."Sequence"', 'value': 6});
  });

  test('a refused argument means the commit marker is never written', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    cpu.requests.clear();
    final ok = await client.writeBatch(const [
      OpcUaWrite('PLC1/Unit/CylA/Execute', OpcUaWriteType.boolean, true), // read-only
      OpcUaWrite('PLC1/Unit/HmiRequest/Sequence', OpcUaWriteType.uint32, 6),
    ]);
    expect(ok, isFalse);
    expect(cpu.lastWrites, ['"Unit"."CylA"."Execute"']);
  });

  test('a write off the mailbox is refused, an unknown path is refused locally', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    expect(await client.write('PLC1/Unit/Status/State', OpcUaWriteType.int32, 3), isFalse);
    final before = cpu.requests.length;
    expect(await client.write('PLC1/Unit/Nope', OpcUaWriteType.int32, 1), isFalse);
    expect(cpu.requests.length, before);
  });

  test('an expired token is renewed once, without sending the old token to Api.Login', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    expect(cpu.logins, 1);
    cpu.expireNextCall = true;
    final values = await client.readValues(['PLC1/Unit/Status/Name']);
    expect(values['PLC1/Unit/Status/Name'], 'Unit');
    expect(cpu.logins, 2);
    final loginIndex = cpu.requests.lastIndexWhere((b) => b.first['method'] == 'Api.Login');
    expect(cpu.tokens[loginIndex], isNull);
  });

  test('a genuine permission refusal costs one re-login, never a loop', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    cpu.revoked = true;
    final values = await client.readValues(['PLC1/Unit/Status/Name']);
    expect(values, isEmpty);
    expect(cpu.logins, 2);
  });

  test('excluded paths are never read; slow paths are cached until due', () async {
    var clock = DateTime.utc(2026, 10, 8, 12);
    final cpu = _FakeCpu();
    final client = await _connect(cpu, now: () => clock);
    await client.setExcludedPaths(['PLC1/Unit/Trace[0]', 'PLC1/Unit/Trace[1]']);
    await client.setSlowPaths(['PLC1/Unit/Status/Name']);
    List<Object?> readVars() => [
          for (final batch in cpu.requests)
            for (final r in batch)
              if (r['method'] == 'PlcProgram.Read') (r['params'] as Map)['var'],
        ];

    cpu.requests.clear();
    var doc = await client.snapshot(); // slow tier read on the first snapshot
    expect(readVars(), contains('"Unit"."Status"."Name"'));
    expect(readVars().where((v) => '$v'.contains('Trace')), isEmpty);
    expect((doc['values'] as Map).containsKey('PLC1/Unit/Trace[0]'), isFalse);

    cpu.requests.clear();
    clock = clock.add(const Duration(seconds: 1));
    doc = await client.snapshot(); // not due: served from the cache
    expect(readVars(), isNot(contains('"Unit"."Status"."Name"')));
    expect((doc['values'] as Map)['PLC1/Unit/Status/Name'], 'Unit');

    cpu.requests.clear();
    await client.refreshSlowPaths();
    await client.snapshot();
    expect(readVars(), contains('"Unit"."Status"."Name"'));

    cpu.requests.clear();
    clock = clock.add(const Duration(seconds: 11));
    await client.snapshot(); // the slow period elapsed
    expect(readVars(), contains('"Unit"."Status"."Name"'));
  });

  test('PEM and DER pins decode to the same DER', () {
    final der = List<int>.generate(40, (i) => i * 7 % 256);
    final pem = '-----BEGIN CERTIFICATE-----\n${base64.encode(der)}\n-----END CERTIFICATE-----\n';
    expect(HttpsWebApiTransport.certificateDer(utf8.encode(pem)), der);
    expect(HttpsWebApiTransport.certificateDer(der), der);
  });

  test('close logs out and releases the transport', () async {
    final cpu = _FakeCpu();
    final client = await _connect(cpu);
    await client.close();
    expect(cpu.closed, isTrue);
    expect(cpu.requests.last.single['method'], 'Api.Logout');
    await expectLater(client.snapshot(), throwsA(isA<OpcUaTransportException>()));
  });
}
