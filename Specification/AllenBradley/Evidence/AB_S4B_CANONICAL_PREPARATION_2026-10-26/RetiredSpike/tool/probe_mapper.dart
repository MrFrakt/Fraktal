import '../lib/data/cip/cip_session_client.dart';
import '../lib/data/opcua_snapshot_mapper.dart';

// Probe: maps one live CIP snapshot through the repository mapper.
//
// ignore_for_file: avoid_print

Future<void> main(List<String> args) async {
  final client = await CipSessionClient.connect(
      host: args.isNotEmpty ? args[0] : '127.0.0.1');
  try {
    final envelope = await client.snapshot();
    final values = envelope['values'] as Map;
    print('name key type: ${values['Press/Status/Name'].runtimeType}');
    print('moduletype key type: ${values['Press/Status/ModuleType'].runtimeType}'
        ' value: ${values['Press/Status/ModuleType']}');
    final projection = OpcUaSnapshotMapper().map(envelope);
    print('forest: ${projection.forest.length}');
    for (final module in projection.forest) {
      print('  root: ${module.path}');
    }
  } finally {
    await client.close();
  }
}
