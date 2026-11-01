import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_operation_queue.dart';
import 'package:fraktal_opcua_client/src/cip_slow_acquisition.dart';

void main() {
  test('a due sweep drains between polls without duplicate chunk requests',
      () async {
    final gates = List.generate(3, (_) => Completer<bool>());
    var calls = 0;
    final errors = <Object>[];
    final pump = CipSlowAcquisitionPump(
        acquireChunk: () => gates[calls++].future, onError: errors.add);
    pump.request();
    pump.request();
    expect(calls, 1);
    gates[0].complete(true);
    await Future<void>.delayed(Duration.zero);
    expect(calls, 2); // No second snapshot was needed.
    gates[1].complete(true);
    await Future<void>.delayed(Duration.zero);
    expect(calls, 3);
    gates[2].complete(false);
    await Future<void>.delayed(Duration.zero);
    expect(calls, 3);
    expect(errors, isEmpty);
  });

  test('pending snapshots and controls run between bounded slow chunks',
      () async {
    final queue = CipOperationQueue(), release = Completer<bool>();
    final events = <String>[];
    var chunks = 0;
    final done = Completer<void>();
    final pump = CipSlowAcquisitionPump(
        acquireChunk: () => queue.schedule('acquireSlow', () async {
              events.add('slow-${++chunks}');
              if (chunks == 1) return release.future;
              done.complete();
              return false;
            }),
        onError: done.completeError);
    pump.request();
    final fast = queue.schedule('snapshot', () async => events.add('snapshot'));
    final control =
        queue.schedule('writeBatch', () async => events.add('control'));
    release.complete(true);
    await Future.wait([fast, control, done.future]);
    expect(events, ['slow-1', 'snapshot', 'control', 'slow-2']);
  });

  test('failure is reported once without retrying the read', () async {
    final error = StateError('native read refused'), errors = <Object>[];
    var calls = 0;
    final pump = CipSlowAcquisitionPump(
        acquireChunk: () async {
          calls++;
          throw error;
        },
        onError: errors.add);
    pump.request();
    await Future<void>.delayed(Duration.zero);
    expect(errors, [same(error)]);
    expect(calls, 1);
  });

  for (final fails in [false, true]) {
    test('cancelled session cannot continue or poison its replacement ($fails)',
        () async {
      final old = Completer<bool>(), replacement = Completer<bool>();
      final errors = <Object>[];
      var calls = 0;
      final pump = CipSlowAcquisitionPump(
          acquireChunk: () => ++calls == 1 ? old.future : replacement.future,
          onError: errors.add);
      pump.request();
      pump.cancel();
      pump.request();
      if (fails) {
        old.completeError(StateError('old session failed'));
      } else {
        old.complete(true);
      }
      await Future<void>.delayed(Duration.zero);
      pump.request();
      expect(calls, 2); // The old completion must not clear the new lease.
      expect(errors, isEmpty);
      replacement.complete(false);
      await Future<void>.delayed(Duration.zero);
    });
  }
}
