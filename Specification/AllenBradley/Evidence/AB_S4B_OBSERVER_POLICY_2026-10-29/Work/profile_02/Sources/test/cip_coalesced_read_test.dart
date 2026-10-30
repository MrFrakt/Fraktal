import 'dart:async';
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
  FutureOr<void> Function(List<CipBatchRead>)? onReads;
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
      await onReads?.call(reads);
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

CipPublication _eightRows(Map capture, {int count = 8}) {
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
  final parent = parents.entries.firstWhere((p) => p.value.length >= count);
  final selected = parent.value.take(count).toSet();
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
  test('one costly group does not reduce packing for unrelated rows', () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = _eightRows(capture, count: 16);
    final plan = CipReadPlan(pub, pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(maxAttempts: 3, clockUs: () => epoch.now));
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    final all = pub.fields.keys.toList(), expensive = all.take(8).toSet();
    final unaffected = all.skip(8).toSet(), packets = <List<String>>[];
    wire.onReads = (reads) {
      final paths = reads.map((r) => wire.path(r.path).last.$1).toList();
      packets.add(paths);
      if (reads.length > 2 &&
          paths.any((p) => expensive.any((e) => e.endsWith('/$p')))) {
        epoch.revision += 2;
        epoch.now += 12000;
      }
    };
    await plan.acquire(paths: expensive);
    expect(plan.snapshot()['values'], isNotEmpty,
        reason: 'the separate healthy rows retain their own accepted samples');
    packets.clear();
    await plan.acquire();
    final unaffectedNames = unaffected.map((p) => p.split('/').last).toSet();
    expect(
        packets.where((p) => p.toSet().containsAll(unaffectedNames)).length, 1);
    final values = plan.snapshot()['values'] as Map;
    expect(unaffected.every(values.containsKey), true);
    expect(plan.guard.maxAttempts, 3);
  });
  test(
      'exhausted oversized proofs shrink future packets without a retry or age reset',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = _eightRows(capture),
        plan = CipReadPlan(_eightRows(capture), pool,
            clockUs: () => epoch.now,
            guard: CipReadCoherenceGuard(
                maxAttempts: 3, clockUs: () => epoch.now));
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    final good = plan.snapshot();
    final sizes = <int>[];
    wire.onReads = (reads) {
      sizes.add(reads.length);
      if (reads.length > 2) {
        // Native counterexample: the body crosses a publication boundary.
        epoch.revision += 2;
        epoch.now += 12000;
      }
    };
    await plan.acquire();
    expect(sizes, [8, 8, 8],
        reason: 'no same-acquisition fallback after the three attempts');
    expect(plan.snapshot()['values'], isEmpty);
    for (final sample
        in (plan.snapshot()['dataValues'] as Map).values.cast<Map>()) {
      expect(sample['status'], 0x40000000);
      expect(sample.containsKey('value'), false);
      expect(sample['ageMs'], 36);
    }
    sizes.clear();
    await plan.acquire();
    expect(sizes, [4, 4, 4, 4, 4, 4],
        reason: 'each half learns its own bound within three attempts');
    sizes.clear();
    await plan.acquire();
    expect(sizes, [2, 2, 2, 2]);
    final recovered = plan.snapshot();
    expect(recovered['values'], good['values']);
    expect(recovered['types'], good['types']);
    expect((recovered['values'] as Map).keys.toSet(), pub.fields.keys.toSet());
    expect(plan.guard.maxAttempts, 3);
    expect(epoch.maximum, 1);
  });
  test(
      'small module headers stay coherent and withdraw together on a torn proof',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final pub = golden.publication(capture);
    final wires = List.generate(4, (_) => _Wire(capture, epoch));
    final pool = CipReadPool.fromConnected(wires);
    addTearDown(pool.close);
    final plan = CipReadPlan(pub, pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
    await plan.acquire();
    epoch.revision = 4;
    final headerReads = <String>[];
    var tear = false;
    const names = {'Name', 'ModuleType', 'State', 'ConfigRev', 'TypeKey'};
    for (final wire in wires) {
      wire.onReads = (reads) {
        bool header(CipBatchRead read) {
          final parts = wire.path(read.path);
          return parts.length > 1 &&
              parts[parts.length - 2].$1 == 'Status' &&
              names.contains(parts.last.$1);
        }

        if (!reads.any(header)) return;
        expect(reads.every(header), true);
        headerReads.addAll(
            reads.map((r) => wire.path(r.path).map((p) => p.$1).join('.')));
        if (tear) epoch.torn = true;
      };
    }
    await plan.acquire();
    expect(headerReads, isNotEmpty);
    expect(headerReads.toSet().length, headerReads.length,
        reason:
            'each header field is read once rather than retried as a second group');
    final identity =
        pub.discoverPaths().where((p) => p.endsWith('/Status/Name')).toList();
    final good = plan.snapshot()['values'] as Map;
    expect(identity, isNotEmpty);
    expect(identity.every(good.containsKey), true);
    tear = true;
    epoch.revision = 6;
    await plan.acquire();
    final refused = plan.snapshot();
    for (final path in identity) {
      expect((refused['values'] as Map).containsKey(path), false);
      final sample = (refused['dataValues'] as Map)[path] as Map;
      expect(sample['status'], 0x40000000);
      expect(sample.containsKey('value'), false);
      expect(sample['reason'], 'coherence-unavailable');
    }
  });
  test('packet dependencies are unique and fresh for each protected window',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = golden.publication(capture);
    final plan = CipReadPlan(pub, pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
    var packets = 0;
    wire.onReads = (reads) {
      packets++;
      final signatures = reads
          .map((r) => (
                r.atomic,
                r.structureHandle,
                r.replyDataBytes,
                r.path.toString(),
                r.data.toString()
              ))
          .toSet();
      expect(signatures.length, reads.length);
    };
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    expect(packets, greaterThan(0));
    final classes = pub.fields.values.firstWhere((f) =>
        (f.annotation['countPath'] as String?)?.endsWith('/ClassCount') ??
        false);
    final countPath = classes.annotation['countPath'] as String;
    expect((plan.snapshot()['values'] as Map)[countPath], greaterThan(0));
    epoch.zeroClasses = true;
    epoch.revision = 6;
    await plan.acquire();
    final values = plan.snapshot()['values'] as Map;
    expect(values[countPath], 0);
    expect(values.keys.any((p) => (p as String).startsWith('${classes.path}[')),
        false);
  });
  test(
      'a retried packet ages from the carried pre read that actually protects it',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final plan = CipReadPlan(_eightRows(capture), pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
    await plan.acquire();
    epoch.revision = 4;
    var bodies = 0;
    wire.events.clear();
    wire.onReads = (_) {
      bodies++;
      epoch.now += bodies == 1 ? 3000 : 1000;
      epoch.revision = 6;
    };
    await plan.acquire();
    expect(bodies, 2);
    expect(wire.events.where((e) => e == 'counter').length, 3);
    for (final sample
        in (plan.snapshot()['dataValues'] as Map).values.cast<Map>()) {
      expect(sample['status'], 0);
      expect(sample['ageMs'], 1);
      expect(sample['acceptedWindowUs'], 1000);
    }
  });
  test(
      'fast snapshots neither acquire nor renew independently scheduled slow rows',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = _eightRows(capture), slow = pub.fields.keys.take(4).toSet();
    final plan = CipReadPlan(pub, pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now))
      ..slowPaths = slow;
    await plan.acquire(fastOnly: true);
    epoch.revision = 4;
    wire.reads.clear();
    await plan.acquire(fastOnly: true);
    expect((plan.snapshot()['values'] as Map).keys.toSet(),
        pub.fields.keys.toSet().difference(slow));
    expect(wire.reads.length, 4,
        reason: 'no slow body is in the fast operation');
    await plan.acquireSlowChunk();
    expect((plan.snapshot()['values'] as Map).length, 8);
    epoch.now = 2000;
    epoch.revision = 6;
    await plan.acquire(fastOnly: true);
    final before = wire.reads.length;
    await plan.acquireSlowChunk();
    expect(wire.reads.length, before,
        reason: 'a fast envelope does not force another slow sweep');
    for (final path in slow) {
      expect(((plan.snapshot()['dataValues'] as Map)[path] as Map)['ageMs'], 2);
    }
    epoch.now = 15000000;
    epoch.revision = 8;
    await plan.acquire(fastOnly: true);
    for (final path in slow) {
      final sample = (plan.snapshot()['dataValues'] as Map)[path] as Map;
      expect(sample['status'], 0x80000000);
      expect(sample.containsKey('value'), false);
    }
  });

  test(
      'slow chunks resume across intervening fast snapshots without repeating bodies',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wire = _Wire(capture, epoch, capacity: 500),
        pool = CipReadPool.fromConnected([wire]);
    addTearDown(pool.close);
    final pub = _eightRows(capture, count: 16), paths = pub.fields.keys.toSet();
    final plan = CipReadPlan(pub, pool,
        clockUs: () => epoch.now,
        guard: CipReadCoherenceGuard(clockUs: () => epoch.now));
    await plan.acquire();
    epoch.revision = 4;
    await plan.acquire();
    plan.slowPaths = paths;
    wire.reads.clear();
    var chunks = 0;
    while (wire.reads.length < paths.length && chunks < paths.length) {
      await plan.acquire(fastOnly: true);
      final before = wire.reads.length;
      await plan.acquireSlowChunk();
      expect(wire.reads.length, greaterThan(before));
      chunks++;
    }
    expect(chunks, greaterThan(1));
    expect(wire.reads.length, paths.length);
    expect(wire.reads.toSet().length, paths.length);
    expect((plan.snapshot()['values'] as Map).keys.toSet(), paths);
  });

  test('array expansion waits for the drained level of independent counts',
      () async {
    final capture = golden.fixtures().last['capture'] as Map, epoch = _Epoch();
    final wires = List.generate(4, (_) => _Wire(capture, epoch));
    final pool = CipReadPool.fromConnected(wires);
    addTearDown(pool.close);
    final plan = CipReadPlan(golden.publication(capture), pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    epoch.revision = 4;
    final held = Completer<void>(), release = Completer<void>();
    var arrayBodyBeforeRelease = false, independentCounts = 0;
    for (final wire in wires) {
      wire.onReads = (reads) async {
        final names = reads.map((r) => wire.path(r.path).last.$1).toList();
        final isCountLevel = names.contains('AvailableModelCount') &&
            names.contains('ClassCount');
        if (isCountLevel && !held.isCompleted) {
          independentCounts = names.length;
          held.complete();
          await release.future;
        } else if (!release.isCompleted &&
            reads.any((r) => wire.path(r.path).any((p) => p.$2 != null))) {
          arrayBodyBeforeRelease = true;
        }
      };
    }
    final walk = plan.acquire();
    await held.future.timeout(const Duration(seconds: 2));
    try {
      await Future<void>.delayed(Duration.zero);
      expect(independentCounts, greaterThanOrEqualTo(2));
      expect(arrayBodyBeforeRelease, false);
    } finally {
      release.complete();
    }
    await walk;
    expect(plan.snapshot()['values'],
        (golden.fixtures().last['expected'] as Map)['values']);
  });

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
    expect(combined.$4.toSet(), baseline.$4.toSet(),
        reason: 'every native body fact is still read');
    expect(combined.$4.length, lessThan(baseline.$4.length),
        reason: 'duplicate guarded dependencies are acquired once per packet');
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
