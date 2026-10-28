import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';

void main() {
  final binding = CipReadCoherenceBinding('Root', 'CounterFromManifest', 10000);

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
    final revisions = [1, 2, 4, 6, 6];
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
