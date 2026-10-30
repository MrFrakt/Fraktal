import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'cip_publication_test.dart' as golden;
import 'cip_read_batch_test.dart' show BatchCapture;

class _Epoch {
  int revision = 2, now = 0, active = 0, maximum = 0;
  bool torn = false, zeroClasses = false;
}

class _Wire extends BatchCapture {
  final _Epoch epoch;
  final int capacity;
  int active = 0, maximum = 0;
  final events = <String>[];
  void Function(List<CipBatchRead>)? onReads;
  _Wire(super.capture, this.epoch, {this.capacity = 4000});
  @override
  int get readBatchBytes => capacity;
  void enter() {
    active++;
    epoch.active++;
    if (active > maximum) maximum = active;
    if (epoch.active > epoch.maximum) epoch.maximum = epoch.active;
  }

  void leave() {
    active--;
    epoch.active--;
  }

  CipReply classes(CipReply reply, Uint8List encoded) {
    if (epoch.zeroClasses && path(encoded).last.$1 == 'ClassCount') {
      return CipReply(0, [], Uint8List.fromList([0xc4, 0, 0, 0, 0, 0]));
    }
    return reply;
  }

  @override
  Future<CipReply> request(int service, Uint8List encoded,
      [Uint8List? data]) async {
    enter();
    try {
      if (!raw.containsKey(path(encoded).first.$1)) {
        ordinary++;
        events.add('counter');
        if (epoch.torn) epoch.revision += 2;
        return CipReply(
            0,
            [],
            Uint8List.fromList([
              0xc4,
              0,
              ...(ByteData(4)..setInt32(0, epoch.revision, Endian.little))
                  .buffer
                  .asUint8List()
            ]));
      }
      events.add('body');
      return classes(await super.request(service, encoded, data), encoded);
    } finally {
      leave();
    }
  }

  @override
  Future<List<CipReply>> readBatch(List<CipBatchRead> reads) async {
    enter();
    try {
      events.add('packet');
      onReads?.call(reads);
      expect(cipEncodeReadBatch(reads, capacity), isNotNull);
      expect(reads.length, lessThanOrEqualTo(64));
      for (final read in reads) {
        expect(raw.containsKey(path(read.path).first.$1), true,
            reason: 'no counter is inside the body packet');
      }
      final replies = await super.readBatch(reads);
      return [
        for (var i = 0; i < replies.length; i++)
          classes(replies[i], reads[i].path)
      ];
    } finally {
      leave();
    }
  }
}

// Hide only the optional multi-row capability; ordinary per-row packets and
// the same four-connection pool remain the independent scheduling reference.
class _SeparateRows implements CipGroupedReadTransport {
  final CipReadPool pool;
  _SeparateRows(this.pool);
  @override
  int get groupConcurrency => pool.groupConcurrency;
  @override
  Future<T> withGroup<T>(Future<T> Function(CipReadTransport) work) =>
      pool.withGroup(work);
  @override
  Future<CipReply> request(int s, Uint8List p, [Uint8List? d]) =>
      pool.request(s, p, d);
  @override
  void abort() => pool.abort();
  @override
  Future<void> close() => pool.close();
}

CipPublication _eightRows(Map capture) {
  final pub = golden.publication(capture);
  final parents = <String, List<String>>{};
  for (final field in pub.fields.values) {
    if (field.commandOnly ||
        field.member.isArray ||
        field.member.isStructure ||
        field.path.contains('[*]')) continue;
    final parent = field.path.substring(0, field.path.lastIndexOf('/'));
    parents.putIfAbsent(parent, () => []).add(field.path);
  }
  final parent = parents.entries.firstWhere((p) => p.value.length >= 8);
  final selected = parent.value.take(8).toSet();
  final record = pub.records.firstWhere((r) =>
      !r.fragment &&
      (parent.key == r.target || parent.key.startsWith('${r.target}/')));
  pub.records
    ..clear()
    ..add(CipPublishedRecord(record.source, parent.key, record.handle));
  pub.fields.removeWhere((p, _) => !selected.contains(p));
  return pub;
}

void main() {
  test(
      'bounded shared proofs preserve every golden value/type with fewer packets',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    Future<(Map<String, Object?>, int, CipReadPlan, List<String>)> read(
        bool combined) async {
      final epoch = _Epoch();
      final wires = List.generate(
          4, (_) => _Wire(capture, epoch)..reverseExecution = true);
      final pool = CipReadPool.fromConnected(wires);
      addTearDown(pool.close);
      final plan = CipReadPlan(
          golden.publication(capture), combined ? pool : _SeparateRows(pool),
          clockUs: () => epoch.now,
          guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
      await plan.acquire();
      epoch.revision = 4;
      for (final wire in wires) {
        wire.reads.clear();
      }
      final before = wires.fold<int>(0, (n, w) => n + w.batches + w.ordinary);
      await plan.acquire();
      final packets =
          wires.fold<int>(0, (n, w) => n + w.batches + w.ordinary) - before;
      expect(epoch.maximum, lessThanOrEqualTo(4));
      expect(wires.every((w) => w.maximum <= 1), true);
      for (final wire in wires) {
        for (var i = 0; i < wire.events.length; i++) {
          if (wire.events[i] == 'packet') {
            expect(wire.events[i - 1], 'counter');
            expect(wire.events[i + 1], 'counter');
          }
        }
      }
      return (
        plan.snapshot(),
        packets,
        plan,
        [for (final wire in wires) ...wire.reads]..sort()
      );
    }

    final baseline = await read(false), combined = await read(true);
    for (final key in ['values', 'types']) {
      expect(combined.$1[key], baseline.$1[key]);
      expect(combined.$1[key], (fixture['expected'] as Map)[key]);
    }
    expect(combined.$2, lessThan(baseline.$2));
    expect(combined.$4, baseline.$4, reason: 'every body read is preserved');
    final shared =
        combined.$3.acquisitions.where((r) => r['sharedRows'] != null);
    expect(shared, isNotEmpty);
    expect(shared.every((r) => (r['sharedRows'] as int) <= 64), true);
  });

  for (final failure in ['torn', 'late']) {
    test('$failure shared proof withdraws every row without renewing its age',
        () async {
      final capture = golden.fixtures().last['capture'] as Map,
          epoch = _Epoch();
      final wire = _Wire(capture, epoch),
          pool = CipReadPool.fromConnected([wire]);
      addTearDown(pool.close);
      final plan = CipReadPlan(_eightRows(capture), pool,
          clockUs: () => epoch.now,
          guard:
              CipReadCoherenceGuard(maxAttempts: 3, clockUs: () => epoch.now));
      await plan.acquire();
      epoch.revision = 4;
      await plan.acquire();
      expect((plan.snapshot()['values'] as Map).length, 8);
      epoch.revision = 6;
      if (failure == 'torn') epoch.torn = true;
      if (failure == 'late') wire.onBatch = () => epoch.now += 10000;
      await plan.acquire();
      final result = plan.snapshot();
      expect(result['values'], isEmpty);
      for (final row in (result['dataValues'] as Map).values.cast<Map>()) {
        expect(row['status'], 0x40000000);
        expect(row.containsKey('value'), false);
        expect(row['ageMs'], epoch.now / 1000);
        expect(row['coherenceAttempts'], 3);
      }
    });
  }

  for (final fallback in ['unsupported', 'partial']) {
    test('$fallback multi-row reply retains the bounded original reader',
        () async {
      final capture = golden.fixtures().last['capture'] as Map,
          epoch = _Epoch();
      final wire = _Wire(capture, epoch)
        ..unsupported = fallback == 'unsupported'
        ..partial = fallback == 'partial';
      final pool = CipReadPool.fromConnected([wire]);
      addTearDown(pool.close);
      final plan = CipReadPlan(_eightRows(capture), pool,
          clockUs: () => epoch.now,
          guard:
              CipReadCoherenceGuard(maxAttempts: 3, clockUs: () => epoch.now));
      await plan.acquire();
      epoch.revision = 4;
      await plan.acquire();
      expect((plan.snapshot()['values'] as Map).length, 8);
      expect(plan.acquisitions.any((r) => r['fallbackAttempts'] == 1), true);
      expect(plan.acquisitions.every((r) => (r['attempts'] as int) <= 3), true);
      expect(wire.closed, false);
    });
  }

  test('a malformed shared packet closes the pool without publishing values',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch)..malformed = true;
    final pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final plan = CipReadPlan(_eightRows(capture), pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await expectLater(plan.acquire(), throwsFormatException);
    expect(wire.closed, true);
    expect(plan.snapshot()['values'], isEmpty);
  });

  test('a shrinking count cannot displace a sibling row reply', () async {
    final fixture = golden.fixtures().last,
        capture = fixture['capture'] as Map,
        epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final publication = golden.publication(capture);
    // A legal enumeration order puts an independent scalar after the array.
    // Its path/layout/bytes stay unchanged; it must survive a skipped row.
    publication.fields['Press/Access/LoginFailed'] =
        publication.fields.remove('Press/Access/LoginFailed')!;
    final plan = CipReadPlan(publication, pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    var shrank = false, hasCount = false, hasSibling = false;
    wire.onReads = (reads) {
      if (!shrank &&
          reads.any((r) => wire
              .path(r.path)
              .any((p) => p.$1 == 'Classes' && p.$2 != null))) {
        hasCount = reads.any((r) => wire.path(r.path).last.$1 == 'ClassCount');
        hasSibling =
            reads.any((r) => wire.path(r.path).last.$1 == 'LoginFailed');
        shrank = true;
        epoch.zeroClasses = true;
        epoch.revision = 6;
      }
    };
    await plan.acquire();
    expect(shrank, true);
    expect(hasCount, true);
    expect(hasSibling, true);
    final result = plan.snapshot();
    expect(
        (result['values'] as Map)
            .keys
            .any((p) => (p as String).contains('/Access/Classes[')),
        false);
    expect((result['values'] as Map)['Press/Access/LoginFailed'],
        (fixture['expected'] as Map)['values']['Press/Access/LoginFailed']);
    expect(wire.closed, false);
  });

  test('small connection budgets split rows rather than oversized packets',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch, capacity: 500),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final plan = CipReadPlan(_eightRows(capture), pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    expect((plan.snapshot()['values'] as Map).length, 8);
    expect(wire.closed, false);
  });

  test(
      'fallback cannot obtain a new deadline after its packet consumed the budget',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch)..unsupported = true;
    wire.onBatch = () => epoch.now += 1000000;
    final pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final plan = CipReadPlan(_eightRows(capture), pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
    await expectLater(plan.acquire(), throwsFormatException);
    expect(wire.ordinary, 1,
        reason: 'only the original pre-counter may reach the wire');
    expect(wire.batches, 1);
    expect(wire.closed, true);
    expect(plan.snapshot()['values'], isEmpty);
  });

  test('one total attempt cannot become another attempt through fallback',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch)..unsupported = true;
    final pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final plan = CipReadPlan(_eightRows(capture), pool,
        clockUs: () => 0,
        guard: CipReadCoherenceGuard(maxAttempts: 1, clockUs: () => 0));
    await expectLater(plan.acquire(), throwsFormatException);
    expect(wire.ordinary, 1);
    expect(wire.batches, 1);
    expect(wire.closed, true);
  });

  test(
      'explicit target reads batch only the selected body under an external proof',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = _eightRows(capture), paths = pub.fields.keys.take(5).toSet();
    final plan = CipReadPlan(pub, pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire(paths: paths);
    epoch.revision = 4;
    await plan.acquire(paths: paths);
    expect((plan.snapshot()['values'] as Map).keys.toSet(), paths);
    final expected = golden.fixtures().last['expected'] as Map;
    for (final key in ['values', 'types']) {
      expect(plan.snapshot()[key],
          {for (final path in paths) path: (expected[key] as Map)[path]});
    }
    expect(wire.batches, greaterThan(0));
    expect(wire.ordinary, lessThan(6 * paths.length));
    expect(wire.reads.toSet().length, paths.length);
  });
}
