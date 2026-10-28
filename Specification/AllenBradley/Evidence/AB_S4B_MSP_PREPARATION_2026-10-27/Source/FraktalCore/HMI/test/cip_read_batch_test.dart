import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'cip_publication_test.dart' as golden;
import 'cip_read_plan_test.dart' show CaptureWire;

class BatchCapture extends CaptureWire implements CipBatchReadTransport {
  int batches = 0, ordinary = 0;
  bool unsupported = false, partial = false, malformed = false;
  bool zeroDependencies = false;
  bool reverseExecution = false;
  final spans = <(int, int)>[];
  void Function()? onBatch;
  BatchCapture(super.capture);
  @override
  int get readBatchBytes => 4000;
  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) {
    ordinary++;
    return super.request(service, path, data);
  }

  @override
  Future<List<CipReply>> readBatch(List<CipBatchRead> reads) async {
    batches++;
    onBatch?.call();
    if (unsupported) throw const CipBatchUnavailable();
    final from = this.reads.length;
    final result =
        List<CipReply>.filled(reads.length, CipReply(0, [], Uint8List(0)));
    final order = List.generate(reads.length, (i) => i);
    for (final index in reverseExecution ? order.reversed : order) {
      final read = reads[index];
      result[index] = await super.request(0x52, read.path, read.data);
    }
    spans.add((from, this.reads.length));
    if (zeroDependencies && reads.length > 1) {
      final first = Uint8List.fromList(result[0].data);
      first.fillRange(2, first.length, 0);
      result[0] = CipReply(0, [], first);
    }
    if (malformed) return result.sublist(1);
    if (partial && result.length > 1) {
      final old = result[1];
      result[1] = CipReply(6, old.additionalStatus,
          Uint8List.sublistView(old.data, 0, old.data.length - 1));
    }
    return result;
  }
}

CipBatchRead read(String name, {int size = 4}) => CipBatchRead(
    cipSymbolPath(name), Uint8List.fromList([1, 0, 0, 0, 0, 0]), size + 2);
Uint8List response(List<List<int>> replies) {
  var offset = 2 + 2 * replies.length;
  final offsets = <int>[];
  for (final row in replies) {
    offsets.add(offset);
    offset += row.length;
  }
  return Uint8List.fromList([
    ...cipWords([replies.length, ...offsets]),
    for (final r in replies) ...r
  ]);
}

void main() {
  test('separate counters bracket body packets even with reversed execution',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final wire = BatchCapture(capture)..reverseExecution = true;
    final pub = golden.publication(capture);
    final plan = CipReadPlan(pub, wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], (fixture['expected'] as Map)['values']);
    expect(plan.snapshot()['types'], (fixture['expected'] as Map)['types']);
    final counters = {
      for (final binding in pub.manifest.coherence) binding.revisionSymbol
    };
    expect(wire.spans, isNotEmpty);
    for (final span in wire.spans) {
      expect(counters, contains(wire.reads[span.$1 - 1]));
      expect(wire.reads[span.$2], wire.reads[span.$1 - 1]);
      expect(
          wire.reads.sublist(span.$1, span.$2).any(counters.contains), false);
    }
  });
  test('an equal-counter packet at the mutation interval cannot remain Good',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final wire = BatchCapture(capture), pub = golden.publication(capture);
    var now = 0;
    final plan = CipReadPlan(pub, wire,
        clockUs: () => now,
        guard: CipReadCoherenceGuard(maxAttempts: 2, clockUs: () => now));
    final array =
        pub.fields.values.firstWhere((f) => f.path.endsWith('/Access/Classes'));
    final scope = '${array.path}[${array.annotation['lowerBound']}]';
    await plan.acquire(paths: {scope});
    await plan.acquire(paths: {scope});
    expect(
        (plan.snapshot()['values'] as Map).containsKey('$scope/ClassId'), true);
    wire.onBatch = () => now += 10000;
    await plan.acquire(paths: {scope});
    expect((plan.snapshot()['values'] as Map).containsKey('$scope/ClassId'),
        false);
    expect((plan.snapshot()['dataValues'] as Map)['$scope/ClassId']['status'],
        0x40000000);
  });
  test('a count shrinking inside the packet withdraws its now-ineligible row',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final wire = BatchCapture(capture), pub = golden.publication(capture);
    final array =
        pub.fields.values.firstWhere((f) => f.path.endsWith('/Access/Classes'));
    final row = '${array.path}[${array.annotation['lowerBound']}]';
    final plan = CipReadPlan(pub, wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire(paths: {row});
    await plan.acquire(paths: {row});
    expect(
        (plan.snapshot()['values'] as Map)
            .keys
            .any((p) => (p as String).startsWith('$row/')),
        true);
    wire.zeroDependencies = true;
    await plan.acquire(paths: {row});
    expect(
        (plan.snapshot()['values'] as Map)
            .keys
            .any((p) => (p as String).startsWith('$row/')),
        false);
  });
  test(
      'batch type, structure handle and successful/partial lengths are validated',
      () {
    final atomic = [read('Value')];
    for (final row in [
      [0xd2, 0, 0, 0, 0xc3, 0, 1, 0],
      [0xd2, 0, 0, 0, 0xc4, 0, 1, 0],
      [0xd2, 0, 6, 0, 0xc4, 0, 1, 0, 0, 0],
      [0xd2, 0, 6, 0, 0xc3, 0, 1, 0]
    ]) {
      expect(
          () => cipDecodeReadBatch(
              CipReply(row[2] == 6 ? 0x1e : 0, [], response([row])), atomic),
          throwsFormatException);
    }
    final structure = [
      CipBatchRead(
          cipSymbolPath('Row'), Uint8List.fromList([1, 0, 0, 0, 0, 0]), 8,
          atomic: null, structureHandle: 123)
    ];
    expect(
        () => cipDecodeReadBatch(
            CipReply(
                0,
                [],
                response([
                  [0xd2, 0, 0, 0, 0xa0, 2, 124, 0, 1, 2, 3, 4]
                ])),
            structure),
        throwsFormatException);
    final valid = cipDecodeReadBatch(
        CipReply(
            0,
            [],
            response([
              [0xd2, 0, 0, 0, 0xa0, 2, 123, 0, 1, 2, 3, 4]
            ])),
        structure);
    expect(valid.single.data.length, 8);
  });
  test('batched guarded reads preserve all golden values/types', () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final wire = BatchCapture(capture);
    final plan = CipReadPlan(golden.publication(capture), wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], (fixture['expected'] as Map)['values']);
    expect(plan.snapshot()['types'], (fixture['expected'] as Map)['types']);
    expect(wire.batches, greaterThan(0));
    expect(wire.ordinary, lessThan(wire.reads.length));
  });
  test('unsupported batch service retains the original row reader', () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final wire = BatchCapture(capture)..unsupported = true;
    final plan = CipReadPlan(golden.publication(capture), wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], (fixture['expected'] as Map)['values']);
    expect(wire.ordinary, greaterThan(0));
  });
  test('partial embedded fragment uses the original fragmented reader',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final wire = BatchCapture(capture)..partial = true;
    final plan = CipReadPlan(golden.publication(capture), wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], (fixture['expected'] as Map)['values']);
    expect(plan.snapshot()['types'], (fixture['expected'] as Map)['types']);
  });
  test('torn batched rows withdraw their previously Good payload', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final wire = BatchCapture(capture);
    final plan = CipReadPlan(golden.publication(capture), wire,
        clockUs: () => 0,
        guard: CipReadCoherenceGuard(maxAttempts: 2, clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], isNotEmpty);
    wire.torn = true;
    await plan.acquire();
    expect(plan.snapshot()['values'], isEmpty);
  });
  test('a malformed batched row fails and closes its transport', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final wire = BatchCapture(capture)..malformed = true;
    final plan = CipReadPlan(golden.publication(capture), wire);
    await expectLater(plan.acquire(), throwsFormatException);
    expect(wire.closed, true);
  });
  test('read MSP encodes repeated counters and decodes ordered typed replies',
      () {
    final reads = [read('Counter'), read('Body'), read('Counter')];
    final data = cipEncodeReadBatch(reads, 4000)!;
    expect(cipReadRequestAllowed(0x0a, cipObjectPath(2, 1), data), true);
    final replies = cipDecodeReadBatch(
        CipReply(
            0,
            [],
            response([
              [0xd2, 0, 0, 0, 0xc4, 0, 2, 0, 0, 0],
              [0xd2, 0, 0, 0, 0xc4, 0, 42, 0, 0, 0],
              [0xd2, 0, 0, 0, 0xc4, 0, 2, 0, 0, 0]
            ])),
        reads);
    expect(replies.map((r) => r.data[2]).toList(), [2, 42, 2]);
  });
  test('embedded write, nested MSP and connection-manager wrapper are refused',
      () {
    final valid = cipEncodeReadBatch([read('Value')], 4000)!;
    final offset = ByteData.sublistView(valid).getUint16(2, Endian.little);
    for (final service in [0x4d, 0x53, 0x54, 0x5b, 0x4e, 0x0a]) {
      final data = Uint8List.fromList(valid)..[offset] = service;
      expect(cipReadRequestAllowed(0x0a, cipObjectPath(2, 1), data), false);
    }
    expect(cipReadRequestAllowed(0x52, cipObjectPath(6, 1)), false);
    expect(cipReadRequestAllowed(0x0a, cipObjectPath(6, 1), valid), false);
    final nested = Uint8List.fromList(
        [1, 0, 4, 0, 0x52, 2, 0x20, 6, 0x24, 1, 1, 0, 0, 0, 0, 0]);
    expect(cipReadRequestAllowed(0x0a, cipObjectPath(2, 1), nested), false);
  });
  test('all supported symbolic array encodings are read-only paths', () {
    for (final name in [
      'Value',
      'Root.Rows[1].Member',
      'Rows[300].Value',
      'Rows[70000].Value'
    ]) {
      final request = read(name);
      expect(cipReadRequestAllowed(0x52, request.path, request.data), true);
      expect(cipEncodeReadBatch([request], 4000), isNotNull);
    }
  });
  test(
      'request offsets, count, path, lengths and zero element count are checked',
      () {
    final original = cipEncodeReadBatch([read('Value'), read('Other')], 4000)!;
    final offset = ByteData.sublistView(original).getUint16(2, Endian.little);
    final broken = <Uint8List>[
      Uint8List.fromList(original)..[0] = 0,
      Uint8List.fromList(original)..[2] = 0,
      Uint8List.fromList(original)..[4] = original[2],
      Uint8List.fromList(original)..[offset + 2] = 0x20,
      Uint8List.fromList(original)..[offset + 1] = 255,
      Uint8List.fromList(original)..[offset + 2 + 2 * original[offset + 1]] = 0,
      Uint8List.fromList([...original, 0])
    ];
    for (final data in broken) {
      expect(cipReadRequestAllowed(0x0a, cipObjectPath(2, 1), data), false);
    }
  });
  test('a row exceeding either request or response capacity keeps fallback',
      () {
    expect(
        cipEncodeReadBatch(
            [read('Large', size: 3800), read('Other', size: 200)], 4000),
        isNull);
    expect(
        cipEncodeReadBatch(
            List.generate(20, (i) => read('LongName_$i' * 8)), 500),
        isNull);
    expect(cipEncodeReadBatch([], 4000), isNull);
    expect(cipEncodeReadBatch(List.generate(65, (i) => read('Value')), 4000),
        isNull);
  });
  test('reply offsets, service, reserved byte and data extent are strict', () {
    final reads = [read('Value'), read('Other')];
    final good = response([
      [0xd2, 0, 0, 0, 0xc4, 0, 1, 0, 0, 0],
      [0xd2, 0, 0, 0, 0xc4, 0, 2, 0, 0, 0]
    ]);
    final offset = ByteData.sublistView(good).getUint16(2, Endian.little);
    final broken = <Uint8List>[
      Uint8List.fromList(good)..[0] = 1,
      Uint8List.fromList(good)..[2] = 0,
      Uint8List.fromList(good)..[4] = good[2],
      Uint8List.fromList(good)..[offset] = 0xcc,
      Uint8List.fromList(good)..[offset + 1] = 1,
      Uint8List.fromList(good)..[offset + 3] = 255,
      Uint8List.fromList([...good, 0])
    ];
    for (final data in broken) {
      expect(() => cipDecodeReadBatch(CipReply(0, [], data), reads),
          throwsFormatException);
    }
  });
  test(
      'unsupported service and failed embedded replies cannot masquerade as success',
      () {
    final reads = [read('Value')];
    expect(() => cipDecodeReadBatch(CipReply(8, [], Uint8List(0)), reads),
        throwsA(isA<CipBatchUnavailable>()));
    final failed = cipDecodeReadBatch(
        CipReply(
            0x1e,
            [],
            response([
              [0xd2, 0, 5, 0]
            ])),
        reads);
    expect(failed.single.status, 5);
    expect(() => failed.single.requireSuccess(), throwsA(isA<Exception>()));
    expect(
        () => cipDecodeReadBatch(
            CipReply(
                0x1e,
                [],
                response([
                  [0xd2, 0, 0, 0, 0xc4, 0, 1, 0, 0, 0]
                ])),
            reads),
        throwsFormatException);
  });
}
