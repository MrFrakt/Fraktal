import 'dart:async';

/// Keeps a due slow sweep moving between snapshots. Each callback queues just
/// one bounded worker operation, so snapshots and controls retain their normal
/// scheduling fences. No timer, read retry or completed-value cache is added.
final class CipSlowAcquisitionPump {
  final Future<bool> Function() acquireChunk;
  final void Function(Object) onError;
  Object? _active;

  CipSlowAcquisitionPump({required this.acquireChunk, required this.onError});

  void request() {
    if (_active != null) return;
    final token = _active = Object();
    unawaited(_drain(token));
  }

  void cancel() => _active = null;

  Future<void> _drain(Object token) async {
    try {
      while (identical(_active, token)) {
        final more = await acquireChunk();
        if (!more) return;
      }
    } on Object catch (error) {
      if (identical(_active, token)) onError(error);
    } finally {
      if (identical(_active, token)) _active = null;
    }
  }
}
