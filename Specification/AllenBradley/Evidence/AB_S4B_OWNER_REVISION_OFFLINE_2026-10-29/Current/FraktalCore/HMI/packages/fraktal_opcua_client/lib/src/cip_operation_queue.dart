import 'dart:async';

final class _PendingOperation {
  final String kind;
  final Future<void> Function() execute;
  _PendingOperation(this.kind, this.execute);
}

/// Serializes worker operations. Cyclic samples and background reads alternate
/// when both wait; all other operations fence that scheduling window. No work
/// is dropped, overlapped, retried or moved across a control operation.
final class CipOperationQueue {
  final _pending = <_PendingOperation>[];
  bool _running = false, _backgroundTurn = false;

  Future<T> schedule<T>(String kind, Future<T> Function() execute) {
    final result = Completer<T>();
    _pending.add(_PendingOperation(kind, () async {
      try {
        result.complete(await execute());
      } on Object catch (error, stack) {
        result.completeError(error, stack);
      }
    }));
    unawaited(_drain());
    return result.future;
  }

  bool _background(String kind) => kind == 'read' || kind == 'acquireSlow';

  int _next() {
    // A queued connect/profile/close/command (or a future unknown operation)
    // keeps its position. Only the read prefix before that fence may reorder.
    final limit = _pending
        .indexWhere((p) => p.kind != 'snapshot' && !_background(p.kind));
    final end = limit < 0 ? _pending.length : limit;
    for (var i = 0; i < end; i++) {
      if (_backgroundTurn
          ? _background(_pending[i].kind)
          : _pending[i].kind == 'snapshot') return i;
    }
    return 0;
  }

  Future<void> _drain() async {
    if (_running) return;
    _running = true;
    try {
      while (_pending.isNotEmpty) {
        final operation = _pending.removeAt(_next());
        _backgroundTurn = operation.kind == 'snapshot';
        await operation.execute();
      }
    } finally {
      _running = false;
    }
  }
}
