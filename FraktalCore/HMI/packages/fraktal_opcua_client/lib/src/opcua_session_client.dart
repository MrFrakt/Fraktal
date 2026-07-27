library;

enum OpcUaWriteType { boolean, int32, uint32, int64, doubleValue, string }

final class OpcUaWrite {
  final String path;
  final OpcUaWriteType type;
  final Object value;

  const OpcUaWrite(this.path, this.type, this.value);
}

class OpcUaTransportException implements Exception {
  final String message;
  final Object? cause;

  const OpcUaTransportException(this.message, [this.cause]);

  @override
  String toString() => cause == null
      ? 'OPC UA transport error: $message'
      : 'OPC UA transport error: $message ($cause)';
}

class OpcUaRemoteException implements Exception {
  final String message;

  const OpcUaRemoteException(this.message);

  @override
  String toString() => 'OPC UA remote error: $message';
}

/// Transport-neutral snapshot/write session used by the generic repository.
/// Native platforms implement it with open62541; Web implements it over the
/// Fraktal WebSocket gateway because browsers cannot open OPC UA TCP sockets.
abstract class OpcUaSessionClient {
  Future<Map<String, Object?>> snapshot();
  Future<bool> write(String path, OpcUaWriteType type, Object value);

  Future<void> close();
}

abstract class OpcUaBatchSessionClient implements OpcUaSessionClient {
  Future<bool> writeBatch(List<OpcUaWrite> writes);
}

/// Optional capability: a client that can read a small set of browse paths in
/// one service call, without paying for a full snapshot. Used for mailbox
/// acknowledgement polling and config-manifest page reads; a client without it
/// (gateway, test fakes) is served by the legacy snapshot-poll path.
abstract class OpcUaBulkReadClient implements OpcUaSessionClient {
  Future<Map<String, Object?>> readValues(List<String> browsePaths);
}

/// Optional capability: a client that reads config-tier browse paths at a slow
/// rate instead of on every snapshot. Only the native client and its
/// reconnecting decorator implement it; other transports keep reading everything
/// through the no-op [OpcUaSessionClientTiering] extension below, so adding a
/// client type never has to know about tiering.
abstract class OpcUaTieredReadClient implements OpcUaSessionClient {
  Future<void> setSlowPaths(Iterable<String> browsePaths);
  Future<void> refreshSlowPaths();

  /// Marks browse paths as on-demand: never read in the snapshot, served only
  /// by [OpcUaBulkReadClient.readValues] when the owning view is visible.
  Future<void> setExcludedPaths(Iterable<String> browsePaths);
}

extension OpcUaSessionClientBatch on OpcUaSessionClient {
  /// Writes one commit-last mailbox transaction. Direct clients use this
  /// conservative sequential fallback; gateway clients implement one protocol
  /// request so different HMI connections cannot interleave mailbox fields.
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    final session = this;
    if (session is OpcUaBatchSessionClient) {
      return session.writeBatch(writes);
    }
    for (final writeValue in writes) {
      if (!await session.write(
        writeValue.path,
        writeValue.type,
        writeValue.value,
      )) {
        return false;
      }
    }
    return true;
  }
}

extension OpcUaSessionClientTiering on OpcUaSessionClient {
  /// Marks browse paths as low-frequency "config" reads if this client tiers its
  /// reads ([OpcUaTieredReadClient]); otherwise a no-op — the transport keeps
  /// reading everything.
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    final session = this;
    if (session is OpcUaTieredReadClient) {
      await session.setSlowPaths(browsePaths);
    }
  }

  /// Forces the next snapshot to re-read the slow paths, if supported.
  Future<void> refreshSlowPaths() async {
    final session = this;
    if (session is OpcUaTieredReadClient) {
      await session.refreshSlowPaths();
    }
  }

  /// Marks browse paths as on-demand (never read in the snapshot), if supported.
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    final session = this;
    if (session is OpcUaTieredReadClient) {
      await session.setExcludedPaths(browsePaths);
    }
  }
}
