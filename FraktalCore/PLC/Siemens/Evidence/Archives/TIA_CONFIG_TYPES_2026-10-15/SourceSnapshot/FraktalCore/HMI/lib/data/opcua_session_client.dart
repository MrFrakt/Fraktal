library;

export 'package:fraktal_opcua_client/opcua_session_client.dart'
    show
        OpcUaRemoteException,
        OpcUaBatchSessionClient,
        OpcUaBulkReadClient,
        OpcUaPathDiscoveryClient,
        OpcUaSessionClient,
        OpcUaSessionClientBatch,
        OpcUaSessionClientTiering,
        OpcUaSnapshotException,
        OpcUaTieredReadClient,
        OpcUaTransportException,
        OpcUaWrite,
        OpcUaWriteType,
        validateCompleteOpcUaSnapshot;

/// Maximum targeted-read batch in version 1 of the Web gateway contract.
/// Repository detail scheduling uses the same bound as both gateway clients.
const opcUaTargetReadBatchSize = 512;

/// Optional targeted-read envelope. Cached values retain their source age and
/// quality rather than becoming fresh at the time a viewer requests them.
abstract interface class OpcUaDataValueReadClient {
  Future<Map<String, Object?>> readDataValues(List<String> browsePaths);
}

Map<String, Object?> decodeTargetedDataValues(Object? result) {
  if (result is! Map) {
    throw const FormatException('Gateway targeted-read result is invalid.');
  }
  if (result['protocol'] == 'fraktal.opcua.read-values.v1') {
    if (result['values'] is! Map || result['dataValues'] is! Map) {
      throw const FormatException('Gateway targeted-read envelope is invalid.');
    }
    return Map<String, Object?>.from(result);
  }
  if (result.containsKey('protocol')) {
    throw const FormatException('Unknown targeted-read envelope version.');
  }
  // Older gateways force a native targeted read and return scalars only.
  // Preserve that read-start aging behavior until they support the envelope.
  return {
    'values': Map<String, Object?>.from(result),
    'dataValues': {
      for (final item in result.entries)
        '${item.key}': {
          'ageMs': 0,
          'status': item.value == null ? 0x80320000 : 0,
        },
    },
  };
}
