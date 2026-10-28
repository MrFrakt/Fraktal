library;

import 'dart:async';
import 'dart:typed_data';

/// Metadata-driven guard for one row/group, never a whole live document.
final class CipReadCoherenceBinding {
  final String canonicalPrefix;
  final String revisionSymbol;
  final int mutationPeriodUs;

  CipReadCoherenceBinding(
      this.canonicalPrefix, this.revisionSymbol, this.mutationPeriodUs) {
    if (!RegExp(r'^[A-Za-z_][A-Za-z0-9_]*(/[A-Za-z_][A-Za-z0-9_]*)*$')
            .hasMatch(canonicalPrefix) ||
        !RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,39}$').hasMatch(revisionSymbol) ||
        mutationPeriodUs < 1 ||
        mutationPeriodUs > 60000000) {
      throw const FormatException('Invalid CIP read-coherence binding.');
    }
  }

  bool covers(String path) =>
      path == canonicalPrefix || path.startsWith('$canonicalPrefix/');
}

enum CipSampleQuality { good, uncertain, bad }

final class CipCoherentSample {
  final CipSampleQuality quality;
  final String? reason;
  final Uint8List? bytes;
  final int? revision;
  final int attempts;
  final int acquisitionUs;
  final int? acceptedWindowUs;
  final List<Map<String, Object?>> failures;

  const CipCoherentSample._(this.quality, this.reason, this.bytes,
      this.revision, this.attempts, this.acquisitionUs,
      [this.acceptedWindowUs, this.failures = const []]);
}

/// A transport supplies exact DINT reads and a bounded native row read. Failure
/// returns no bytes: a torn/late value cannot be retained as a Good sample.
final class CipReadCoherenceGuard {
  final int maxAttempts;
  final Duration timeout;
  final int Function() _clockUs;

  CipReadCoherenceGuard({
    this.maxAttempts = 3,
    this.timeout = const Duration(seconds: 1),
    int Function()? clockUs,
  }) : _clockUs = clockUs ?? _monotonicClock() {
    if (maxAttempts < 1 ||
        maxAttempts > 100 ||
        timeout.inMicroseconds < 1 ||
        timeout > const Duration(seconds: 5)) {
      throw ArgumentError('Invalid CIP coherence retry/time budget.');
    }
  }

  static int Function() _monotonicClock() {
    final clock = Stopwatch()..start();
    return () => clock.elapsedMicroseconds;
  }

  Future<CipCoherentSample> read({
    required CipReadCoherenceBinding binding,
    required Future<int> Function(String symbol) readRevision,
    required Future<Uint8List> Function() readGroup,
  }) async {
    final started = _clockUs();
    var attempts = 0;
    final failures = <Map<String, Object?>>[];
    List<Map<String, Object?>> trace() => List.unmodifiable(
        failures.map((row) => Map<String, Object?>.unmodifiable(row)));
    CipCoherentSample failed(CipSampleQuality quality, String reason) =>
        CipCoherentSample._(quality, reason, null, null, attempts,
            _clockUs() - started, null, trace());
    Future<T> bounded<T>(Future<T> Function() operation) {
      final remaining = timeout.inMicroseconds - (_clockUs() - started);
      if (remaining <= 0) throw TimeoutException('CIP read-group deadline.');
      return operation().timeout(Duration(microseconds: remaining));
    }

    try {
      while (attempts < maxAttempts &&
          _clockUs() - started < timeout.inMicroseconds) {
        attempts++;
        final windowStart = _clockUs();
        final before =
            await bounded(() => readRevision(binding.revisionSymbol));
        if (before < 0 || before > 2147483646) {
          return failed(CipSampleQuality.bad, 'coherence-revision-invalid');
        }
        if (before.isOdd) {
          failures.add({
            'attempt': attempts,
            'reason': 'odd-before',
            'before': before,
            'windowUs': _clockUs() - windowStart
          });
          if (attempts < maxAttempts) {
            // Rapid retries can all land in one publication phase. Yield
            // within the original total deadline, without spending an extra
            // attempt or changing the subsequent guarded read window.
            final waitUs = binding.mutationPeriodUs < 1000
                ? binding.mutationPeriodUs
                : 1000;
            await bounded(
                () => Future<void>.delayed(Duration(microseconds: waitUs)));
          }
          continue;
        }
        final bytes = await bounded(readGroup);
        final after = await bounded(() => readRevision(binding.revisionSymbol));
        if (_clockUs() - started >= timeout.inMicroseconds) {
          return failed(CipSampleQuality.bad, 'read-timeout');
        }
        if (after < 0 || after > 2147483646) {
          return failed(CipSampleQuality.bad, 'coherence-revision-invalid');
        }
        // Equal tokens alone cannot justify a group whose read window is at
        // least the publisher's declared mutation interval (Part III 3.13).
        final windowUs = _clockUs() - windowStart;
        if (before == after &&
            after.isEven &&
            windowUs < binding.mutationPeriodUs) {
          return CipCoherentSample._(
              CipSampleQuality.good,
              null,
              Uint8List.fromList(bytes),
              after,
              attempts,
              _clockUs() - started,
              windowUs,
              trace());
        }
        failures.add({
          'attempt': attempts,
          'reason': before != after ? 'revision-changed' : 'window-too-long',
          'before': before,
          'after': after,
          'windowUs': windowUs
        });
      }
      return failed(CipSampleQuality.uncertain, 'coherence-unavailable');
    } on TimeoutException {
      return failed(CipSampleQuality.bad, 'read-timeout');
    } on Object {
      return failed(CipSampleQuality.bad, 'read-failed');
    }
  }
}
