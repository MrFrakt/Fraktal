import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';

import 'cip_read_plan_test.dart' as peer;
import 'cip_publication_test.dart' as golden;
import 'cip_transport_test.dart' as network;

class _Wire implements CipReadTransport {
  bool closed = false;
  int calls = 0, closes = 0, aborts = 0;
  @override
  Future<CipReply> request(int service, Uint8List path,
      [Uint8List? data]) async {
    if (closed) throw StateError('closed');
    calls++;
    return CipReply(0, [], Uint8List(0));
  }

  @override
  void abort() {
    closed = true;
    aborts++;
  }

  @override
  Future<void> close() async {
    closed = true;
    closes++;
  }
}

class _Activity {
  final Map<String, int> revisions = {};
  int? fixedRevision;
  int active = 0, maximum = 0;
}

// One controller communication engine, shared by every TCP connection. Wire
// costs advance a deterministic clock; no wall-clock sleeps or PLC writes.
class _ControllerQueue {
  int now = 0;
  Future<void> tail = Future<void>.value();
  Future<CipReply> schedule(bool body, Future<CipReply> Function() readBody) {
    final result = Completer<CipReply>();
    tail = tail.then((_) async {
      await Future<void>.delayed(Duration.zero);
      now += body ? 4000 : 1000;
      if (body) {
        result.complete(await readBody());
      } else {
        result.complete(CipReply(
            0,
            [],
            Uint8List.fromList([
              0xc4,
              0,
              ...(ByteData(4)..setInt32(0, (now ~/ 10000) * 2, Endian.little))
                  .buffer
                  .asUint8List()
            ])));
      }
    });
    return result.future;
  }
}

class _QueuedCapture extends peer.CaptureWire {
  final _ControllerQueue controller;
  _QueuedCapture(super.capture, this.controller);
  @override
  Future<CipReply> request(int service, Uint8List encoded, [Uint8List? data]) =>
      controller.schedule(raw.containsKey(path(encoded).first.$1),
          () => super.request(service, encoded, data));
}

// Independent channels complete equal-latency requests together. Virtual time
// advances only after all continuations at the previous instant have run.
class _IndependentController {
  int now = 0;
  bool scheduled = false;
  final events = <(int, void Function())>[];
  Future<CipReply> request(bool body, Future<CipReply> Function() readBody) {
    final result = Completer<CipReply>();
    events.add((
      now + 2000,
      () {
        if (body) {
          readBody().then(result.complete, onError: result.completeError);
        } else {
          result.complete(CipReply(
              0,
              [],
              Uint8List.fromList([
                0xc4,
                0,
                ...(ByteData(4)..setInt32(0, (now ~/ 10000) * 2, Endian.little))
                    .buffer
                    .asUint8List()
              ])));
        }
      }
    ));
    if (!scheduled) {
      scheduled = true;
      Timer.run(flush);
    }
    return result.future;
  }

  void flush() {
    scheduled = false;
    events.sort((a, b) => a.$1.compareTo(b.$1));
    now = events.first.$1;
    final due = events.where((e) => e.$1 == now).toList();
    events.removeWhere((e) => e.$1 == now);
    for (final event in due) event.$2();
    if (events.isNotEmpty && !scheduled) {
      scheduled = true;
      Timer.run(flush);
    }
  }
}

class _IndependentCapture extends peer.CaptureWire {
  final _IndependentController controller;
  _IndependentCapture(super.capture, this.controller);
  @override
  Future<CipReply> request(int service, Uint8List encoded, [Uint8List? data]) =>
      controller.request(raw.containsKey(path(encoded).first.$1),
          () => super.request(service, encoded, data));
}

class _RecordingWire extends _Wire {
  final List<Uint8List> received;
  _RecordingWire(this.received);
  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) {
    received.add(Uint8List.fromList(data!));
    return super.request(service, path, data);
  }
}

class _Capture extends peer.CaptureWire {
  final _Activity activity;
  int active = 0, maximum = 0;
  bool refuseBody = false;
  _Capture(super.capture, this.activity);
  @override
  Future<CipReply> request(int service, Uint8List encoded,
      [Uint8List? data]) async {
    active++;
    activity.active++;
    if (active > maximum) maximum = active;
    if (activity.active > activity.maximum) activity.maximum = activity.active;
    try {
      await Future<void>.delayed(Duration.zero);
      if (refuseBody && raw.containsKey(path(encoded).first.$1)) {
        throw StateError('injected row failure');
      }
      final root = path(encoded).first.$1;
      if (!raw.containsKey(root)) {
        final tick =
            activity.revisions.update(root, (n) => n + 1, ifAbsent: () => 0);
        final token = activity.fixedRevision ??
            (frozen
                ? 2
                : torn
                    ? 2 + 2 * tick
                    // Stable epochs for the golden replay; torn/frozen cases
                    // independently exercise refusal without mixed payload.
                    : 2 + 2 * (tick ~/ 64));
        return CipReply(
            0,
            [],
            Uint8List.fromList([
              0xc4,
              0,
              ...(ByteData(4)..setInt32(0, token, Endian.little))
                  .buffer
                  .asUint8List()
            ]));
      }
      return await super.request(service, encoded, data);
    } finally {
      active--;
      activity.active--;
    }
  }
}

// Keep eight independent, genuinely decoded scalar rows from the capture.
// There are no collection/count barriers in this scheduler counterexample.
CipPublication _independentRows(Map capture) {
  final publication = golden.publication(capture);
  final byParent = <String, List<String>>{};
  for (final field in publication.fields.values) {
    if (field.commandOnly ||
        field.member.isArray ||
        field.member.isStructure ||
        field.path.contains('[*]')) continue;
    final parent = field.path.substring(0, field.path.lastIndexOf('/'));
    byParent.putIfAbsent(parent, () => []).add(field.path);
  }
  final row = byParent.entries.firstWhere((entry) => entry.value.length >= 8);
  final selected = row.value.take(8).toSet();
  final source = publication.records.firstWhere((record) =>
      !record.fragment &&
      (row.key == record.target || row.key.startsWith('${record.target}/')));
  publication.records
    ..clear()
    ..add(CipPublishedRecord(source.source, row.key, source.handle));
  publication.fields.removeWhere((path, _) => !selected.contains(path));
  return publication;
}

class _HeldGroups implements CipGroupedReadTransport {
  final CipReadPool pool;
  final first = Completer<void>(),
      threeFinished = Completer<void>(),
      failureObserved = Completer<void>();
  final bool failThird;
  final int? groupLimit;
  int started = 0, active = 0, maximum = 0, finished = 0;
  bool firstStillHeld = true;
  _HeldGroups(this.pool, {this.failThird = false, this.groupLimit});
  @override
  int get groupConcurrency => groupLimit ?? pool.groupConcurrency;
  @override
  Future<T> withGroup<T>(Future<T> Function(CipReadTransport) work) =>
      pool.withGroup((transport) async {
        final id = started++;
        active++;
        if (active > maximum) maximum = active;
        try {
          if (id == 0) {
            await first.future;
            firstStillHeld = false;
          }
          if (id == 2 && failThird) {
            failureObserved.complete();
            throw StateError('injected group failure');
          }
          return await work(transport);
        } finally {
          active--;
          if (id != 0 && ++finished == 3 && !threeFinished.isCompleted)
            threeFinished.complete();
        }
      });
  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) =>
      pool.request(service, path, data);
  @override
  void abort() => pool.abort();
  @override
  Future<void> close() => pool.close();
}

void main() {
  test('queued read packets retain their validated bytes after caller mutation',
      () async {
    final received = <Uint8List>[];
    final body = Uint8List.fromList([1, 0, 0, 0, 0, 0]);
    final packet = cipEncodeReadBatch(
        [CipBatchRead(cipSymbolPath('Value'), body, 6)], 4000)!;
    final before = Uint8List.fromList(packet);
    // Observe the queued argument without introducing another network owner.
    final recording = _RecordingWire(received);
    final queuedPool = CipReadPool.fromConnected([recording]);
    final release = Completer<void>();
    final occupied = queuedPool.withGroup((_) => release.future);
    final request = queuedPool.request(0x0a, cipObjectPath(2, 1), packet);
    packet.fillRange(0, packet.length, 0);
    release.complete();
    await occupied;
    await request;
    expect(received.single, before);
    await queuedPool.close();
  });
  test('invalid group concurrency refuses before starting any row', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    for (final limit in [0, 5]) {
      final pool = CipReadPool.fromConnected([_Capture(capture, _Activity())]);
      final wire = _HeldGroups(pool, groupLimit: limit);
      final plan = CipReadPlan(_independentRows(capture), wire);
      await expectLater(plan.acquire(), throwsFormatException);
      expect(wire.started, 0);
      await wire.close();
    }
  });

  test('a completed row refills its slot before a slow sibling finishes',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final pool = CipReadPool.fromConnected(
        List.generate(4, (_) => _Capture(capture, activity)));
    final wire = _HeldGroups(pool);
    final plan = CipReadPlan(_independentRows(capture), wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final acquisition = plan.acquire();
    try {
      await wire.threeFinished.future;
      for (var i = 0; i < 10; i++) {
        await Future<void>.delayed(Duration.zero);
      }
      expect(wire.firstStillHeld, true);
      expect(wire.started, greaterThan(4));
      expect(wire.maximum, 4);
    } finally {
      wire.first.complete();
      await acquisition;
      await wire.close();
    }
    expect(wire.active, 0);
    expect(wire.started, 8);
  });

  test('a group failure drains its started sibling before acquisition refuses',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final pool = CipReadPool.fromConnected(
        List.generate(4, (_) => _Capture(capture, activity)));
    final wire = _HeldGroups(pool, failThird: true);
    final plan = CipReadPlan(_independentRows(capture), wire,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    var completed = false;
    final acquisition = plan
        .acquire()
        .then<Object?>((_) => null, onError: (Object error) => error)
        .whenComplete(() => completed = true);
    await wire.failureObserved.future;
    expect(completed, false);
    wire.first.complete();
    expect(await acquisition, isA<StateError>());
    expect(wire.active, 0);
    expect(wire.started, lessThanOrEqualTo(4));
    await wire.close();
  });

  test('a guarded group owns its connection through all requests', () async {
    final wires = List.generate(4, (_) => _Wire());
    final pool = CipReadPool.fromConnected(wires);
    final held = <CipReadTransport>{};
    final release = Completer<void>();
    var entered = 0, maximum = 0;
    final jobs = List.generate(
        6,
        (_) => pool.withGroup((wire) async {
              expect(held.add(wire), true);
              entered++;
              if (held.length > maximum) maximum = held.length;
              await release.future;
              for (var i = 0; i < 3; i++) {
                await wire.request(0x52, cipSymbolPath('Value'));
              }
              held.remove(wire);
            }));
    await Future<void>.delayed(Duration.zero);
    expect(entered, 4);
    expect(maximum, 4);
    release.complete();
    await Future.wait(jobs);
    expect(entered, 6);
    expect(wires.fold<int>(0, (n, wire) => n + wire.calls), 18);
    await pool.close();
    expect(wires.every((wire) => wire.closes == 1), true);
  });

  test('close refuses queued and in-flight results without replay', () async {
    final wire = _Wire(), release = Completer<void>();
    final pool = CipReadPool.fromConnected([wire]);
    final first = pool.withGroup((_) async {
      await release.future;
      return 1;
    });
    final second = pool.withGroup((_) async => 2);
    final checks = [
      expectLater(first, throwsA(isA<Exception>())),
      expectLater(second, throwsA(isA<Exception>()))
    ];
    await pool.close();
    release.complete();
    await Future.wait(checks);
    expect(wire.calls, 0);
    expect(wire.closes, 1);
  });

  test('writes and connection services are refused before borrowing a socket',
      () async {
    final wire = _Wire();
    final checked = CipReadPool.fromConnected([wire]);
    for (final service in [0x4d, 0x53, 0x54, 0x5b, 0x4e]) {
      await expectLater(checked.request(service, cipSymbolPath('Value')),
          throwsFormatException);
    }
    expect(wire.calls, 0);
    await checked.close();
  });

  test('all connections pin the first serial and partial opens are closed',
      () async {
    for (final mismatch in [false, true]) {
      final peers = <network.Peer>[];
      for (var i = 0; i < 4; i++) {
        peers.add(await network.Peer.open());
      }
      if (mismatch) peers[1].identitySerial++;
      final bridge = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final sockets = <Socket>[];
      var connections = 0;
      bridge.listen((local) async {
        final index = connections++;
        sockets.add(local);
        final remote =
            await Socket.connect('127.0.0.1', peers[index].server.port);
        sockets.add(remote);
        local.listen(remote.add,
            onDone: remote.destroy, onError: (Object _) => remote.destroy());
        remote.listen(local.add,
            onDone: local.destroy, onError: (Object _) => local.destroy());
      });
      try {
        final future =
            CipReadPool.connect(host: '127.0.0.1', port: bridge.port);
        if (mismatch) {
          await expectLater(future, throwsA(isA<Exception>()));
          expect(connections, 2);
          expect(peers.first.services.last, 0x4e);
        } else {
          final pool = await future;
          expect(pool.groupConcurrency, 4);
          expect(connections, 4);
          await pool.close();
          expect(peers.every((peer) => peer.services.last == 0x4e), true);
        }
      } finally {
        for (final socket in sockets) {
          socket.destroy();
        }
        await bridge.close();
        for (final peer in peers) {
          await peer.close();
        }
      }
    }
  });

  test('controller serialization can invalidate overlapping proof windows',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    Future<Map<String, Object?>> acquire(int concurrency) async {
      final controller = _ControllerQueue();
      final pool = CipReadPool.fromConnected(
          List.generate(4, (_) => _QueuedCapture(capture, controller)));
      addTearDown(pool.close);
      final pub = _independentRows(capture);
      final plan = CipReadPlan(pub, pool,
          groupConcurrencyLimit: concurrency,
          clockUs: () => controller.now,
          guard: CipReadCoherenceGuard(
              maxAttempts: 20, clockUs: () => controller.now));
      expect(await plan.proveProgress(), true);
      await plan.acquire();
      return plan.snapshot();
    }

    final serial = await acquire(1), parallel = await acquire(4);
    expect((serial['values'] as Map).length, 8);
    expect((parallel['values'] as Map).length, lessThan(8));
    for (final sample in (parallel['dataValues'] as Map).values.cast<Map>()) {
      if (sample['status'] != 0) expect(sample.containsKey('value'), false);
    }
  });

  test(
      'startup qualification selects observed throughput without publishing trial data',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    for (final independent in [false, true]) {
      final serial = _ControllerQueue(), parallel = _IndependentController();
      final wires = <CipReadTransport>[
        for (var i = 0; i < 4; i++)
          independent
              ? _IndependentCapture(capture, parallel)
              : _QueuedCapture(capture, serial)
      ];
      final pool = CipReadPool.fromConnected(wires);
      addTearDown(pool.close);
      int clock() => independent ? parallel.now : serial.now;
      final plan = CipReadPlan(_independentRows(capture), pool,
          clockUs: clock,
          guard: CipReadCoherenceGuard(maxAttempts: 20, clockUs: clock));
      final trials = await plan.qualifyConcurrency();
      expect(trials.map((r) => r['concurrentGroups']), [1, 4]);
      expect(plan.groupConcurrency, independent ? 4 : 1);
      expect(plan.snapshot()['values'], isEmpty,
          reason: 'startup values retain no consumer freshness');
      expect(plan.guard.maxAttempts, 20);
      expect(await plan.proveProgress(), true);
      await plan.acquire();
      expect((plan.snapshot()['values'] as Map).length, 8);
    }
  });

  test('startup qualification measures only the applied fast profile',
      () async {
    final capture = golden.fixtures().last['capture'] as Map,
        controller = _IndependentController();
    final pool = CipReadPool.fromConnected(
        List.generate(4, (_) => _IndependentCapture(capture, controller)));
    addTearDown(pool.close);
    final pub = _independentRows(capture), paths = pub.fields.keys.toList();
    final plan = CipReadPlan(pub, pool,
        clockUs: () => controller.now,
        guard: CipReadCoherenceGuard(
            maxAttempts: 20, clockUs: () => controller.now))
      ..excludedPaths = paths.take(4).toSet()
      ..slowPaths = paths.skip(4).take(2).toSet();
    final trials = await plan.qualifyConcurrency();
    expect(trials.map((r) => r['coherentValues']), [2, 2]);
    expect(plan.snapshot()['values'], isEmpty);
  });

  test('parallel row reads preserve all golden values/types and socket bounds',
      () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    final pool = CipReadPool.fromConnected(wires);
    var clock = 0;
    final plan = CipReadPlan(golden.publication(capture), pool,
        clockUs: () => clock++,
        guard: CipReadCoherenceGuard(clockUs: () => clock++));
    await plan.acquire();
    await plan.acquire();
    final result = plan.snapshot(), expected = fixture['expected'] as Map;
    expect(result['values'], expected['values']);
    expect(result['types'], expected['types']);
    expect(activity.maximum, 4);
    expect(wires.every((wire) => wire.maximum == 1), true);
    await pool.close();
  });

  test('targeted groups share bounded leases without reading unrelated rows',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    final pool = CipReadPool.fromConnected(wires);
    final publication = _independentRows(capture);
    final plan = CipReadPlan(publication, pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final paths = publication.fields.keys.take(7).toSet();
    expect(await plan.proveProgress(), true);
    for (var i = 0; i < 8; i++) {
      await plan.acquire(paths: paths);
    }
    expect(activity.maximum, 4);
    expect(wires.every((wire) => wire.maximum == 1), true);
    expect((plan.snapshot()['values'] as Map).keys.toSet(), paths);
    await pool.close();
  });

  test('torn parallel rows cannot retain their earlier Good payload', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    final pool = CipReadPool.fromConnected(wires);
    final plan = CipReadPlan(golden.publication(capture), pool,
        clockUs: () => 0,
        guard: CipReadCoherenceGuard(maxAttempts: 2, clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], isNotEmpty);
    for (final wire in wires) {
      wire.torn = true;
    }
    await plan.acquire();
    expect(plan.snapshot()['values'], isEmpty);
    await pool.close();
  });

  test('a restarted source counter forces rediscovery on every connection',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    final pool = CipReadPool.fromConnected(wires);
    final publication = golden.publication(capture);
    var clock = 0;
    final plan = CipReadPlan(publication, pool,
        clockUs: () => clock++,
        guard: CipReadCoherenceGuard(clockUs: () => clock++));
    await plan.acquire();
    await plan.acquire();
    activity.fixedRevision = 2;
    await expectLater(
        plan.acquire(paths: {'${publication.roots.first}/Status'}),
        throwsFormatException);
    expect(wires.every((wire) => wire.closed), true);
  });

  test('different counts within one revision abort all connections', () async {
    final fixture = golden.fixtures().last, capture = fixture['capture'] as Map;
    final publication = golden.publication(capture);
    final expected = (fixture['expected'] as Map)['values'] as Map;
    final counts = {
      for (final field in publication.fields.values)
        if (field.annotation['countPath'] is String)
          field.annotation['countPath'] as String
    };
    final path = counts.firstWhere((path) =>
        !path.contains('[') &&
        expected[path] is int &&
        (expected[path] as int) > 0 &&
        publication.fields[path]!.member.atomic == 0xc4);
    final source = publication.fields[path]!.sources.single;
    final offset = source.chain.fold<int>(0, (n, m) => n + m.offset);
    expect(CipTemplateDecoder.atomicByteSize(source.member.atomic), 4);
    final activity = _Activity();
    final wires =
        List.generate(4, (_) => _Capture(capture, activity)..frozen = true);
    for (var i = 0; i < wires.length; i++) {
      ByteData.sublistView(wires[i].raw[source.record.source]!)
          .setInt32(offset, i, Endian.little);
    }
    final pool = CipReadPool.fromConnected(wires);
    final plan = CipReadPlan(publication, pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire(paths: {path});
    await expectLater(plan.acquire(paths: {path}), throwsFormatException);
    expect(wires.every((wire) => wire.closed), true);
  });

  test('a frozen publisher cannot acquire Good data through parallel sockets',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires =
        List.generate(4, (_) => _Capture(capture, activity)..frozen = true);
    final pool = CipReadPool.fromConnected(wires);
    final plan = CipReadPlan(golden.publication(capture), pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    expect(plan.snapshot()['values'], isEmpty);
    await pool.close();
  });

  test('one failed row aborts the whole pool before a snapshot is accepted',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    wires.first.refuseBody = true;
    final pool = CipReadPool.fromConnected(wires);
    final plan = CipReadPlan(golden.publication(capture), pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await expectLater(plan.acquire(), throwsA(isA<Exception>()));
    expect(wires.every((wire) => wire.closed), true);
  });
}
