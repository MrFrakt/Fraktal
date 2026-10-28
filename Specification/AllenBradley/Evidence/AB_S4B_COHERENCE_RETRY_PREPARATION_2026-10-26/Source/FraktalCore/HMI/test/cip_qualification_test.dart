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
