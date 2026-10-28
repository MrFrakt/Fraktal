import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';

void main() {
  test('recorded V6.8 path expansion preserves the complete discovery set', () {
    final record = jsonDecode(utf8.decode(gzip.decode(File(
            'C:/work/fraktal-ab-s4b-partdiag-20261027/session_01/candidate_regressions_configuration_01.json.gz')
        .readAsBytesSync()))) as Map;
    expect(record['passed'], true);
    final capture = (record['pair'] as Map)['capture'] as Map;
    final publication = CipPublication(CipNamespace.fromCapture(capture),
        CipManifest.fromNormalized(Map<String, Object?>.from(capture['manifest'] as Map)));
    final firstClock = Stopwatch()..start();
    final paths = publication.discoverPaths();
    final firstUs = firstClock.elapsedMicroseconds;
    final expected = ((record['pair'] as Map)['canonical'] as Map)['values'] as Map;
    expect(paths, containsAll(expected.keys));
    expect(paths.length, paths.toSet().length);
    expect(paths, orderedEquals(List<String>.of(paths)..sort()));
    final baseline = Platform.environment['FRAKTAL_DISCOVERY_BASELINE'];
    if (baseline != null) {
      expect(paths, orderedEquals((jsonDecode(File(baseline).readAsStringSync()) as Map)['paths'] as List));
    }
    final timings = <int>[];
    for (var i = 0; i < 12; i++) {
      final clock = Stopwatch()..start();
      final next = publication.discoverPaths();
      timings.add(clock.elapsedMicroseconds);
      expect(next, orderedEquals(paths));
      next.clear();
      expect(publication.discoverPaths(), orderedEquals(paths));
    }
    timings.sort();
    final result = {
      'passed': true, 'nativeAcceptance': false, 'recordedCapture': true,
      'paths': paths, 'pathCount': paths.length, 'oracleValues': expected.length,
      'firstUs': firstUs, 'repeatMedianUs': (timings[5] + timings[6]) / 2,
      'repeatMinUs': timings.first, 'repeatMaxUs': timings.last,
      'encodedPathBytes': utf8.encode(jsonEncode(paths)).length,
    };
    final output = File(Platform.environment['FRAKTAL_DISCOVERY_OUTPUT']!);
    expect(output.existsSync(), false);
    output.writeAsStringSync(jsonEncode(result));
    // No wall-clock speed threshold is a correctness requirement.
    print(jsonEncode({...result}..remove('paths')));
  });
}
