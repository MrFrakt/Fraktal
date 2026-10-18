// Core §3.8d(b) - the data classes a root declared, at their policy levels, as
// the access policy editor sees them.
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('the class table maps, and a corrupt level never reads as more open', () {
    final projection = OpcUaSnapshotMapper().map({
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/MAIN/Press/Status/Name': 'Press',
        'PLC1/MAIN/Press/Status/ModuleType': 1,
        'PLC1/MAIN/Press/Status/State': 0,
        'PLC1/MAIN/Press/Status/TileEnable': true,
        'PLC1/MAIN/Press/Access/CurrentLevel': 3,
        'PLC1/MAIN/Press/Access/ClassCount': 2,
        'PLC1/MAIN/Press/Access/Classes/1/ClassId': 'public',
        'PLC1/MAIN/Press/Access/Classes/1/LabelKey': 'project.dataClass.public',
        'PLC1/MAIN/Press/Access/Classes/1/ReadLevel': 0,
        'PLC1/MAIN/Press/Access/Classes/1/WriteLevel': 1,
        'PLC1/MAIN/Press/Access/Classes/2/ClassId': 'broken',
        'PLC1/MAIN/Press/Access/Classes/2/ReadLevel': 0,
        'PLC1/MAIN/Press/Access/Classes/2/WriteLevel': 99,
      },
    });
    final classes = projection.forest.single.access!.classes;
    expect(classes, hasLength(2));
    expect(classes.first.classId, 'public');
    expect(classes.first.writeLevel, AccessLevel.operator);
    expect(classes.last.writeLevel, AccessLevel.admin,
        reason: 'an out-of-range level must not be shown as open');
  });

  test('a class the station never declared cannot be edited', () async {
    final repo = SimRepository();
    addTearDown(repo.dispose);
    expect(
        await repo.setClassLevel('StationA', 'public', AccessLevel.operator,
            forWrite: true),
        isFalse);
  });
}
