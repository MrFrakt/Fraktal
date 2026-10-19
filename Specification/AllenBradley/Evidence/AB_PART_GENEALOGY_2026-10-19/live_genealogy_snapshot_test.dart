import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('current Echo projection hydrates the generic Part genealogy', () {
    final captured = Map<String, Object?>.from(jsonDecode(File(
      'C:/work/fraktal-ab-genealogy-20261018/hmi_part_values.json',
    ).readAsStringSync()) as Map);
    final root = captured.keys.first.split('/Part/').first;
    final node = OpcUaSnapshotMapper().map({
      'values': {
        '$root/Status/Name': root,
        '$root/Status/ModuleType': ModuleType.unit.index,
        ...captured,
      },
    }).forest.single;
    expect(node.part!.parents, ['FIXTURE-BLANK-0001', 'FIXTURE-INSERT-0002']);
    expect(node.part!.present, isFalse);
    expect(node.part!.verdict, Verdict.ok);
  });
}
