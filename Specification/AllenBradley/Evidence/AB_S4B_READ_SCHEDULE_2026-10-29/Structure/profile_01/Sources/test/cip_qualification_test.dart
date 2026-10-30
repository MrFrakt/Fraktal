import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

import '../tool/qualify_cip_canonical.dart' as qualification;

Map<String, Object?> sample({
  List<String> roots = const ['Unit'],
  Object? name = 'Unit',
  double ageMs = 10,
}) =>
    {
      'rootChildren': roots,
      'sampleAgeMs': ageMs,
      'values': {if (name != null) 'Unit/Status/Name': name},
      'types': {'Unit/Status/Name': 'String'},
      'dataValues': {
        'Unit/Status/Name': {
          'status': name == null ? 0x40000000 : 0,
          'ageMs': ageMs,
          if (name == null) 'reason': 'coherence-unavailable',
        }
      }
    };

void main() {
  test('sealed native expiry is refused with all 56 leaf diagnostics intact',
      () {
    final report = jsonDecode(utf8.decode(gzip.decode(File(
            '../../Specification/AllenBradley/Evidence/AB_S4B_Q_ATTEMPT_2026-10-29/Runtime/dart_qualification.json.gz')
        .readAsBytesSync()))) as Map;
    final document = Map<String, Object?>.from((report['snapshots'] as List)
        .cast<Map>()
        .singleWhere((s) => s['qualificationRejectedBadSample'] == true));
    final retained = <Map<String, Object?>>[];
    expect(() => qualification.validateCanonicalDataValues(document, retained),
        throwsFormatException);
    final bad = retained.single['badSampleFailure'] as Map;
    expect(bad.length, 56);
    for (final sample in bad.values.cast<Map>()) {
      expect(sample['reason'], 'read-expired');
      expect(sample['ageMs'], 3310.162);
      expect(sample['coherenceAttempts'], 20);
      expect(sample['value'], isNull);
      expect((sample['coherenceFailures'] as List).length, 20);
    }
    expect(retained.single['dataValues'], document['dataValues']);
  });
  test('observer applies exactly the 230 approved O8 configuration leaves', () {
    final scope = jsonDecode(File(
            '../../Specification/AllenBradley/AB_S4B_METADATA_TIER_PATHS_2026-10-28.json')
        .readAsStringSync()) as Map;
    final configuration = (scope['byContainer'] as Map)
        .values
        .expand((paths) => List<String>.from(paths as List))
        .toSet();
    expect(configuration.length, 230);
    final original = qualification.qualificationReadTiers(configuration,
        configurationHeartbeat: false);
    final approved = qualification.qualificationReadTiers(configuration,
        configurationHeartbeat: true);
    expect(original.slow, isEmpty);
    expect(approved.slow, configuration);
    expect(approved.excluded, isEmpty);
  });
  test('observer preserves live identity, alarms and command exclusions', () {
    const fast = {
      'Unit/Status/Name',
      'Unit/Status/State',
      'Unit/Access/Policy',
      'Unit/GoodCount',
      'Unit/AlarmLog/Active[1]/ReasonCode',
      'Unit/SupportedModesPublished'
    };
    const excluded = {
      'Unit/HmiResponse/Report/Rows[1]/Diagnostic',
      'Unit/SequenceStepDef[1]/StepNo',
      'Unit/SequenceSteps[1]/Visited'
    };
    final tiers = qualification.qualificationReadTiers(
        [...fast, ...excluded, 'Unit/ShiftHistory[1]/GoodCount'],
        configurationHeartbeat: true);
    expect(tiers.excluded, excluded);
    expect(tiers.slow, {'Unit/ShiftHistory[1]/GoodCount'});
    expect(tiers.slow.intersection(fast), isEmpty);
  });
  test('a Bad non-root row retains its complete failure evidence', () {
    final document = sample();
    const path = 'Unit/ShiftHistoryTruncated';
    final metadata = {
      'type': 'Boolean',
      'status': 0x80000000,
      'ageMs': 15000,
      'tier': 'slow',
      'reason': 'read-expired',
      'coherenceFailures': [
        {'attempt': 1, 'reason': 'odd-before', 'before': 3, 'windowUs': 100}
      ]
    };
    (document['dataValues'] as Map)[path] = metadata;
    final retained = <Map<String, Object?>>[];
    expect(() => qualification.validateCanonicalDataValues(document, retained),
        throwsFormatException);
    expect(retained.single['qualificationRejectedBadSample'], true);
    expect(retained.single['badSampleFailure'], {path: metadata});
    expect(retained.single['dataValues'], document['dataValues']);
    expect((retained.single['values'] as Map).containsKey(path), false);
  });

  test('a refused first identity keeps its exact snapshot and quality evidence',
      () {
    final document = sample(name: null), retained = <Map<String, Object?>>[];
    expect(() => qualification.validateCanonicalRootSample(document, retained),
        throwsFormatException);
    final rejected = retained.single;
    expect(rejected['qualificationRejectedRootSample'], true);
    expect(rejected['values'], document['values']);
    expect(rejected['types'], document['types']);
    expect(rejected['dataValues'], document['dataValues']);
    final failure = rejected['rootSampleFailure'] as Map;
    expect(failure['reasons'], ['missing or different root identity: Unit']);
    expect(
        ((failure['rootSamples'] as Map)['Unit'] as Map)['identityDataValue'],
        (document['dataValues'] as Map)['Unit/Status/Name']);
  });

  test('age boundary, wrong identity and missing roots retain distinct causes',
      () {
    for (final vector in [
      (sample(ageMs: 1000), 'cyclic sample age reached 1000 ms'),
      (sample(name: 'Other'), 'missing or different root identity: Unit'),
      (sample(roots: const []), 'no discovered root'),
    ]) {
      final retained = <Map<String, Object?>>[];
      expect(
          () => qualification.validateCanonicalRootSample(vector.$1, retained),
          throwsFormatException);
      expect((retained.single['rootSampleFailure'] as Map)['reasons'],
          [vector.$2]);
    }
    final retained = <Map<String, Object?>>[];
    qualification.validateCanonicalRootSample(sample(ageMs: 999.999), retained);
    expect(retained, isEmpty);
  });
}
