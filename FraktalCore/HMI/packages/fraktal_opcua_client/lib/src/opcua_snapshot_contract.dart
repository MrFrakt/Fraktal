library;

/// Raised when a transport returned a syntactically valid snapshot that is not
/// complete enough to drive an operator HMI safely.
final class OpcUaSnapshotException implements Exception {
  final String message;

  const OpcUaSnapshotException(this.message);

  @override
  String toString() => 'OPC UA snapshot error: $message';
}

/// Enforces the fail-closed part of the shared native/gateway snapshot
/// contract. A browse cap is a guardrail, never permission to render or write
/// against an incomplete PLC namespace.
void validateCompleteOpcUaSnapshot(Map<String, Object?> document) {
  if (document['truncated'] != true) return;
  final nodeCount = document['nodeCount'];
  final count = nodeCount is num ? nodeCount.toInt().toString() : 'unknown';
  throw OpcUaSnapshotException(
    'Discovery was truncated after $count nodes. The PLC publication scope '
    'contains implementation aliases or an unbounded fixed-array projection; '
    'the Fraktal contract may be incomplete. Fix publication ownership or '
    'client-side count pruning before reconnecting.',
  );
}
