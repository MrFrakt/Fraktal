import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_pool.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'package:fraktal_opcua_client/src/cip_template.dart';

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

void main() {
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

  test('targeted groups remain serial on a parallel-capable transport',
      () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final activity = _Activity();
    final wires = List.generate(4, (_) => _Capture(capture, activity));
    final pool = CipReadPool.fromConnected(wires);
    final publication = golden.publication(capture);
    final plan = CipReadPlan(publication, pool,
        clockUs: () => 0, guard: CipReadCoherenceGuard(clockUs: () => 0));
    final path = '${publication.roots.first}/Status';
    expect(await plan.proveProgress(), true);
    for (var i = 0; i < 8; i++) {
      await plan.acquire(paths: {path});
    }
    expect(activity.maximum, 1);
    expect((plan.snapshot()['values'] as Map)['$path/Name'],
        publication.roots.first);
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
