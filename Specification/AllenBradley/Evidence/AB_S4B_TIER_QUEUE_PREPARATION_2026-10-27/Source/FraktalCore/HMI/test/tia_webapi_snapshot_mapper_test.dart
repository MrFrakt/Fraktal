import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/types.dart';

/// The fixture is a real snapshot served by the gateway's Web API session
/// client from the Fraktal/TIA S2 spike on a CPU 1214C V4.7.3 (2026-10-08,
/// `tool/probe_gateway_ws.dart`). It proves the UNCHANGED mapper rebuilds the
/// module tree from what the licence-free Siemens transport emits — paths,
/// quoting and array spelling included — not only from TwinCAT namespaces.
void main() {
  final document = jsonDecode(
    File('test/fixtures/tia_webapi_spike_snapshot.json').readAsStringSync(),
  ) as Map<String, Object?>;

  test('the Web API snapshot is complete and carries Good quality', () {
    expect(() => validateCompleteOpcUaSnapshot(document), returnsNormally);
    final dataValues = document['dataValues'] as Map;
    expect(dataValues, isNotEmpty);
    expect(dataValues.values.every((v) => (v as Map)['status'] == 0), isTrue);
  });

  test('the unchanged mapper rebuilds the S7 forest from Status alone', () {
    final projection = OpcUaSnapshotMapper().map(document);
    expect(projection.forest, hasLength(1));
    final unit = projection.forest.single;
    expect(unit.path, 'SpikeUnit');
    expect(unit.type, ModuleType.unit);
    expect([for (final child in unit.children) child.path], ['SpikeUnit.CylA', 'SpikeUnit.CylB']);
    expect(unit.children.every((child) => child.type == ModuleType.controlModule), isTrue);
    expect(projection.browsePathByModulePath['SpikeUnit.CylB'], 'PLC1/SpikeUnit/CylB');
    expect(projection.discardedAliases, isEmpty);
  });
}
