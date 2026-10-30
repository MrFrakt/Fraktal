import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_operation_queue.dart';

void main() {
  test('a snapshot does not wait for two already queued background reads',
      () async {
    final queue = CipOperationQueue(), release = Completer<void>();
    final events = <String>[];
    var active = 0, maximum = 0;
    Future<void> work(String name, {bool hold = false}) async {
      active++;
      if (active > maximum) maximum = active;
      events.add(name);
      if (hold) await release.future;
      active--;
    }

    final running = queue.schedule('read', () => work('running', hold: true));
    final slow = queue.schedule('acquireSlow', () => work('slow'));
    final fast = queue.schedule('snapshot', () => work('fast'));
    release.complete();
    await Future.wait([running, slow, fast]);
    expect(events, ['running', 'fast', 'slow']);
    expect(maximum, 1);
  });
  test('read and snapshot floods alternate without starving either class',
      () async {
    final queue = CipOperationQueue(), release = Completer<void>();
    final events = <String>[];
    final running = queue.schedule('connect', () => release.future);
    Future<String> work(String name) async {
      events.add(name);
      return name;
    }

    final a = queue.schedule('read', () => work('read-a'));
    final b = queue.schedule('acquireSlow', () => work('read-b'));
    final s1 = queue.schedule('snapshot', () => work('snapshot-1'));
    final s2 = queue.schedule('snapshot', () => work('snapshot-2'));
    final s3 = queue.schedule('snapshot', () => work('snapshot-3'));
    release.complete();
    await running;
    expect(await Future.wait([a, b, s1, s2, s3]),
        ['read-a', 'read-b', 'snapshot-1', 'snapshot-2', 'snapshot-3']);
    expect(
        events, ['snapshot-1', 'read-a', 'snapshot-2', 'read-b', 'snapshot-3']);
  });
  test('control and unknown operations fence all read scheduling', () async {
    for (final fence in [
      'connect',
      'close',
      'tiers',
      'slow',
      'excluded',
      'refresh',
      'paths',
      'configurationDescriptor',
      'configurationAssemble',
      'write',
      'future-command'
    ]) {
      final queue = CipOperationQueue(), release = Completer<void>();
      final events = <String>[];
      final running = queue.schedule('connect', () => release.future);
      Future<void> work(String name) async {
        events.add(name);
      }

      final read = queue.schedule('read', () => work('read'));
      final barrier = queue.schedule(fence, () => work(fence));
      final snapshot = queue.schedule('snapshot', () => work('snapshot'));
      release.complete();
      await Future.wait([running, read, barrier, snapshot]);
      expect(events, ['read', fence, 'snapshot'], reason: fence);
    }
  });
  test('a refused operation keeps its error and cannot strand the queue',
      () async {
    final queue = CipOperationQueue(), release = Completer<void>();
    final running = queue.schedule('connect', () => release.future);
    final failed =
        queue.schedule<int>('read', () async => throw StateError('refused'));
    final error = expectLater(failed, throwsStateError);
    final next = queue.schedule('paths', () async => 7);
    release.complete();
    await running;
    await error;
    expect(await next, 7);
  });
}
