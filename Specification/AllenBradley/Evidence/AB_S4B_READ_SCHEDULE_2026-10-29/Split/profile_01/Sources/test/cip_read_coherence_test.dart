import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';

void main() {
  test('publication source ordering accepts wrap and refuses older revisions',
      () {
    for (final vector in [
      (2, 0, true),
      (0, 2147483646, true),
      (4, 2, true),
      (2, 4, false),
      (2147483646, 0, false),
      (2, 2, false),
      (0, 0, false)
    ]) {
      expect(cipRevisionIsLater(vector.$1, vector.$2), vector.$3);
    }
  });
  final binding = CipReadCoherenceBinding('Root', 'CounterFromManifest', 10000);

  test('a shared attempt limit can only reduce the original row budget',
      () async {
    var reads = 0;
    final guard = CipReadCoherenceGuard(maxAttempts: 3, clockUs: () => 0);
    Future<CipCoherentSample> run(int limit) => guard.read(
        binding: binding,
        attemptLimit: limit,
        readRevision: (_) async {
          reads++;
          return 1;
        },
        readGroup: () async => Uint8List(0));
    for (final limit in [0, 4]) {
      await expectLater(run(limit), throwsArgumentError);
    }
    expect(reads, 0);
    final sample = await run(1);
    expect(reads, 1);
    expect(sample.attempts, 1);
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.bytes, isNull);
  });

  test('an odd publisher can finish on a later turn within the same budget',
      () async {
    var publishing = true, scheduled = false, reads = 0;
    final sample = await CipReadCoherenceGuard(maxAttempts: 2).read(
      binding: binding,
      readRevision: (_) async {
        if (!scheduled) {
          scheduled = true;
          Timer.run(() => publishing = false);
        }
        return publishing ? 1 : 2;
      },
      readGroup: () async {
        reads++;
        return Uint8List.fromList([7]);
      },
    );
    expect(sample.quality, CipSampleQuality.good);
    expect(sample.attempts, 2);
    expect(sample.bytes, [7]);
    expect(reads, 1);
  });

  test('Uncertain keeps bounded failed-counter evidence without row bytes',
      () async {
    final revisions = [1, 2, 4, 6, 8];
    var at = 0;
    final sample = await CipReadCoherenceGuard(clockUs: () => 0).read(
      binding: binding,
      readRevision: (_) async => revisions[at++],
      readGroup: () async => Uint8List.fromList([99]),
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.attempts, 3);
    expect(sample.bytes, isNull);
    expect(sample.failures, [
      {'attempt': 1, 'reason': 'odd-before', 'before': 1, 'windowUs': 0},
      {
        'attempt': 2,
        'reason': 'revision-changed',
        'before': 2,
        'after': 4,
        'windowUs': 0
      },
      {
        'attempt': 3,
        'reason': 'revision-changed',
        'before': 4,
        'after': 6,
        'windowUs': 0
      }
    ]);
  });

  test('the wait for an odd publisher stays inside the original deadline',
      () async {
    var reads = 0;
    final sample = await CipReadCoherenceGuard(
      maxAttempts: 2,
      timeout: const Duration(microseconds: 100),
      clockUs: () => 0,
    ).read(
      binding: binding,
      readRevision: (_) async => 1,
      readGroup: () async {
        reads++;
        return Uint8List(1);
      },
    );
    expect(sample.quality, CipSampleQuality.bad);
    expect(sample.reason, 'read-timeout');
    expect(sample.bytes, isNull);
    expect(sample.attempts, 1);
    expect(reads, 0);
  });

  test('small stable-even row succeeds using only its published symbol',
      () async {
    final calls = <String>[];
    final raw = Uint8List.fromList([1, 2]);
    final sample = await CipReadCoherenceGuard(clockUs: () => 0).read(
      binding: binding,
      readRevision: (symbol) async {
        calls.add(symbol);
        return 8;
      },
      readGroup: () async => raw,
    );
    raw[0] = 99;
    expect(sample.quality, CipSampleQuality.good);
    expect(sample.bytes, [1, 2]);
    expect(sample.revision, 8);
    expect(calls, ['CounterFromManifest', 'CounterFromManifest']);
  });

  test('odd or changing revisions consume the same bounded retry budget',
      () async {
    final revisions = [1, 2, 4, 4];
    var index = 0, reads = 0;
    final sample = await CipReadCoherenceGuard(clockUs: () => 0).read(
      binding: binding,
      readRevision: (_) async => revisions[index++],
      readGroup: () async {
        reads++;
        return Uint8List.fromList([reads]);
      },
    );
    expect(sample.quality, CipSampleQuality.good);
    expect(sample.attempts, 3);
    expect(sample.bytes, [2]);
    expect(reads, 2);
    expect(index, 4,
        reason: 'the completed post read supplies the next pre read');
  });

  test('a carried post cannot hide a further revision change within the budget',
      () async {
    final revisions = [1, 2, 4, 6, 6];
    var index = 0;
    final sample = await CipReadCoherenceGuard(clockUs: () => 0).read(
      binding: binding,
      readRevision: (_) async => revisions[index++],
      readGroup: () async => Uint8List.fromList([99]),
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.attempts, 3);
    expect(sample.bytes, isNull);
    expect(index, 4);
  });

  test('a carried pre includes its original request latency in the next window',
      () async {
    var now = 0, revisions = 0, bodies = 0;
    final sample =
        await CipReadCoherenceGuard(clockUs: () => now, maxAttempts: 2).read(
      binding: binding,
      readRevision: (_) async {
        revisions++;
        now += revisions == 2 ? 9000 : 100;
        return revisions == 1 ? 2 : 4;
      },
      readGroup: () async {
        bodies++;
        now += 1000;
        return Uint8List.fromList([bodies]);
      },
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.bytes, isNull);
    expect(sample.attempts, 2);
    expect(sample.failures.last['windowUs'], 10100);
    expect(revisions, 3);
  });

  test('exhaustion returns Uncertain without mixed or stale bytes', () async {
    final sample = await CipReadCoherenceGuard(maxAttempts: 2).read(
      binding: binding,
      readRevision: (_) async => 1,
      readGroup: () async => throw StateError('must not read while mutating'),
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.bytes, isNull);
    expect(sample.revision, isNull);
    expect(sample.attempts, 2);
  });

  test('stable token does not excuse a window exceeding mutation interval',
      () async {
    var now = 0;
    final sample = await CipReadCoherenceGuard(clockUs: () => now).read(
      binding: binding,
      readRevision: (_) async => 2,
      readGroup: () async {
        now += 10000;
        return Uint8List(1);
      },
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.bytes, isNull);
    expect(sample.attempts, 3);
  });

  test('lost connection and invalid counters are Bad without payload',
      () async {
    for (final revision in [-1, 2147483647]) {
      final sample = await CipReadCoherenceGuard().read(
        binding: binding,
        readRevision: (_) async => revision,
        readGroup: () async => Uint8List(1),
      );
      expect(sample.quality, CipSampleQuality.bad);
      expect(sample.reason, 'coherence-revision-invalid');
      expect(sample.bytes, isNull);
    }
    final lost = await CipReadCoherenceGuard().read(
      binding: binding,
      readRevision: (_) async => throw StateError('disconnected'),
      readGroup: () async => Uint8List(1),
    );
    expect(lost.quality, CipSampleQuality.bad);
    expect(lost.bytes, isNull);
  });

  test('the guarded window includes the first revision request latency',
      () async {
    var now = 0;
    final sample = await CipReadCoherenceGuard(clockUs: () => now).read(
      binding: binding,
      readRevision: (_) async {
        now += 10000;
        return 2;
      },
      readGroup: () async => Uint8List(1),
    );
    expect(sample.quality, CipSampleQuality.uncertain);
    expect(sample.bytes, isNull);
  });

  test('completion beyond the total budget cannot return Good', () async {
    var now = 0;
    final sample = await CipReadCoherenceGuard(
      clockUs: () => now,
      timeout: const Duration(microseconds: 100),
    ).read(
      binding: binding,
      readRevision: (_) async {
        now += 60;
        return 2;
      },
      readGroup: () async => Uint8List(1),
    );
    expect(sample.quality, CipSampleQuality.bad);
    expect(sample.reason, 'read-timeout');
    expect(sample.bytes, isNull);
  });

  test('a stalled request is bounded independently of completion', () async {
    final sample = await CipReadCoherenceGuard(
      timeout: const Duration(milliseconds: 10),
    ).read(
      binding: binding,
      readRevision: (_) => Completer<int>().future,
      readGroup: () async => Uint8List(1),
    );
    expect(sample.quality, CipSampleQuality.bad);
    expect(sample.reason, 'read-timeout');
    expect(sample.bytes, isNull);
  });

  test('prefix scope has a segment boundary and metadata has strict bounds',
      () {
    expect(binding.covers('Root/Status/State'), isTrue);
    expect(binding.covers('RootOther/Status/State'), isFalse);
    expect(() => CipReadCoherenceBinding('Root', '', 10000),
        throwsFormatException);
    expect(() => CipReadCoherenceBinding('Root', 'Counter', 0),
        throwsFormatException);
  });
}
