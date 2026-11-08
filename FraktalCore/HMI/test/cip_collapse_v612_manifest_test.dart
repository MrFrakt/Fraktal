import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';

import 'cip_owner_revision_test.dart' show rehashed;

Map<String, Object?> goldenV611() => Map<String, Object?>.from(
    (jsonDecode(File('test/fixtures/cip_host_services_v611.json')
            .readAsStringSync()) as Map)['normalized'] as Map);

Map<String, Object?> copy(Map value) =>
    Map<String, Object?>.from(jsonDecode(jsonEncode(value)) as Map);

Map<String, Object?> goldenV612() {
  final d = copy(goldenV611());
  d['schemaMinor'] = 12;
  d['services'] = <Object?>[];
  return rehashed(d);
}

void main() {
  test('V6.12 collapse manifest decodes with empty services table and retains host services', () {
    final d = goldenV612();
    final manifest = CipManifest.fromNormalized(d);
    expect(manifest.minor, 12);
    expect(manifest.contentHash, d['contentHash']);
    expect(manifest.rows('services'), isEmpty);
    expect(manifest.rows('hostServiceBindings').map((r) => r['Service']),
        [1, 2, 3, 4]);
    expect(
        manifest.ownerCoherence
            .any((b) => b.canonicalPrefix == 'Press/HostEvents'),
        isTrue);
  });

  test('V6.12 refuses non-empty services', () {
    final d = copy(goldenV611());
    d['schemaMinor'] = 12;
    // services remains non-empty from V6.11 golden
    expect(
        () => CipManifest.fromNormalized(rehashed(d)),
        throwsA(isA<FormatException>().having(
            (e) => e.message, 'message', contains('V6.12 requires empty services'))));
  });
}
