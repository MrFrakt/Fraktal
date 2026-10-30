library;

import 'dart:async';
import 'dart:typed_data';

const cipHeaderCoherenceMembers = {
  'Name',
  'ModuleType',
  'State',
  'ConfigRev',
  'TypeKey'
};

/// Metadata-driven guard for one row/group, never a whole live document.
final class CipReadCoherenceBinding {
  final String canonicalPrefix;
  final String revisionSymbol;
  final int mutationPeriodUs;
  final int protocol;
  final String progressSymbol;
  final int proofWindowUs;
  final Set<String> members;

  CipReadCoherenceBinding(
      this.canonicalPrefix, this.revisionSymbol, this.mutationPeriodUs,
      {this.protocol = 1,
      String? progressSymbol,
      int? proofWindowUs,
      Iterable<String> members = const []})
      : progressSymbol = progressSymbol ?? revisionSymbol,
        proofWindowUs = proofWindowUs ?? mutationPeriodUs,
        members = Set.unmodifiable(members) {
    if (!RegExp(r'^[A-Za-z_][A-Za-z0-9_]*(/[A-Za-z_][A-Za-z0-9_]*)*$')
            .hasMatch(canonicalPrefix) ||
        !RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,39}$').hasMatch(revisionSymbol) ||
        mutationPeriodUs < 1 ||
        mutationPeriodUs > 60000000 ||
        !RegExp(r'^[A-Za-z_][A-Za-z0-9_]{0,39}$')
            .hasMatch(this.progressSymbol) ||
        (protocol != 1 && protocol != 2) ||
        (protocol == 1 &&
            (this.progressSymbol != revisionSymbol ||
                this.proofWindowUs != mutationPeriodUs ||
                this.members.isNotEmpty)) ||
        (protocol == 2 &&
            (this.progressSymbol == revisionSymbol ||
                this.proofWindowUs < 1 ||
                this.proofWindowUs > 1000000 ||
                this.proofWindowUs ~/ mutationPeriodUs >= (1 << 30) - 1))) {
      throw const FormatException('Invalid CIP read-coherence binding.');
    }
  }

  bool covers(String path) => members.isEmpty
      ? path == canonicalPrefix || path.startsWith('$canonicalPrefix/')
      : members.any((m) =>
          path == '$canonicalPrefix/$m' ||
          path.startsWith('$canonicalPrefix/$m/'));
}

enum CipSampleQuality { good, uncertain, bad }

/// Source order for already validated even 31-bit publication counters.
/// A live session cannot span half the counter range without rediscovery.
bool cipRevisionIsLater(int candidate, int previous) {
  final distance = (candidate - previous) & 0x7fffffff;
  return distance > 0 && distance < 0x40000000;
}

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
    final budgetUs =
        binding.protocol == 2 && binding.proofWindowUs < timeout.inMicroseconds
            ? binding.proofWindowUs
            : timeout.inMicroseconds;
    var attempts = 0;
    final failures = <Map<String, Object?>>[];
    (int, int)? carriedBefore;
    List<Map<String, Object?>> trace() => List.unmodifiable(
        failures.map((row) => Map<String, Object?>.unmodifiable(row)));
    CipCoherentSample failed(CipSampleQuality quality, String reason) =>
        CipCoherentSample._(quality, reason, null, null, attempts,
            _clockUs() - started, null, trace());
    Future<T> bounded<T>(Future<T> Function() operation) {
      final remaining = budgetUs - (_clockUs() - started);
      if (remaining <= 0) throw TimeoutException('CIP read-group deadline.');
      return operation().timeout(Duration(microseconds: remaining));
    }

    try {
      while (attempts < maxAttempts && _clockUs() - started < budgetUs) {
        attempts++;
        final previousPost = carriedBefore;
        carriedBefore = null;
        final windowStart = previousPost?.$2 ?? _clockUs();
        final int before = previousPost != null
            ? previousPost.$1
            : await bounded(() => readRevision(binding.revisionSymbol));
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
        final afterStarted = _clockUs();
        final after = await bounded(() => readRevision(binding.revisionSymbol));
        if (_clockUs() - started >= budgetUs) {
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
            windowUs < binding.proofWindowUs) {
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
        // A completed post read is already a valid pre read for the next
        // body. Retain its actual I/O start for that window; the retry gets
        // neither a renewed timestamp nor another attempt/deadline budget.
        carriedBefore = (after, afterStarted);
      }
      return failed(CipSampleQuality.uncertain, 'coherence-unavailable');
    } on TimeoutException {
      return failed(CipSampleQuality.bad, 'read-timeout');
    } on Object {
      return failed(CipSampleQuality.bad, 'read-failed');
    }
  }
}
