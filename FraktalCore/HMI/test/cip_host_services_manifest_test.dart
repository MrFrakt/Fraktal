import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';

import 'cip_owner_revision_test.dart' show rehashed;

/// Python-normalized V6.11 manifest (S4b owner demo plus host-service rows);
/// written by the WP6.4 offline evidence. No native ABI claim.
Map<String, Object?> golden() => Map<String, Object?>.from(
    (jsonDecode(File('test/fixtures/cip_host_services_v611.json')
            .readAsStringSync()) as Map)['normalized'] as Map);

Map<String, Object?> copy(Map value) =>
    Map<String, Object?>.from(jsonDecode(jsonEncode(value)) as Map);

void main() {
  test('V6.11 host-service rows decode and hash exactly as Python does', () {
    final d = golden();
    final manifest = CipManifest.fromNormalized(d);
    expect(manifest.minor, 11);
    expect(manifest.contentHash, d['contentHash']);
    expect(manifest.rows('hostServiceBindings').map((r) => r['Service']),
        [1, 2, 3, 4]);
    // The ring is covered by its own whole-scope owner row.
    expect(
        manifest.ownerCoherence
            .any((b) => b.canonicalPrefix == 'Press/HostEvents'),
        isTrue);
  });

  test('correctly rehashed but invalid host-service tables refuse', () {
    // Each case names the rule that must refuse it, not just any refusal.
    final cases = <String, void Function(Map<String, Object?>)>{
      'lacks its owner-read binding': (d) => (d['ownerReadBindings'] as List)
          .removeWhere((o) => o['CanonicalPrefix'] == 'Press/HostEvents'),
      'Invalid host-service binding.|foreign': (d) {
        for (final r in d['hostServiceBindings'] as List) {
          r['RootSymbol'] = 'Oven';
          if (r['Service'] == 4) r['CanonicalRoot'] = 'Oven/HostEvents';
        }
      },
      'read-only ring': (d) => (d['hostServiceBindings'] as List)
          .last['CommitSymbol'] = 'RingCommit',
      'share one ingress': (d) =>
          (d['hostServiceBindings'] as List)[1]['ReplySymbol'] = 'OtherReply',
      'endpoint, bound or gate.|gate': (d) =>
          (d['hostServiceBindings'] as List).first['AccessGate'] = 11,
      'endpoint, bound or gate.|bound': (d) => (d['hostServiceBindings'] as List)
          .first['MaximumChunkBytes'] = 3745,
      'Invalid host-service binding.|duplicate': (d) =>
          (d['hostServiceBindings'] as List)
              .add(Map.from((d['hostServiceBindings'] as List).first as Map)),
      'Unexpected normalized manifest field.': (d) => d['schemaMinor'] = 10,
    };
    for (final entry in cases.entries) {
      final d = copy(golden());
      entry.value(d);
      expect(
          () => CipManifest.fromNormalized(rehashed(d)),
          throwsA(isA<FormatException>().having(
              (e) => e.message, 'message', contains(entry.key.split('|').first))),
          reason: entry.key);
    }
  });

  test('an unrehashed host-service change fails the content hash', () {
    final d = copy(golden());
    (d['hostServiceBindings'] as List).first['ConnectionBytes'] = 3999;
    (d['hostServiceBindings'] as List)[1]['ConnectionBytes'] = 3999;
    (d['hostServiceBindings'] as List)[2]['ConnectionBytes'] = 3999;
    for (final r in (d['hostServiceBindings'] as List).take(3))
      r['MaximumChunkBytes'] = 3000;
    expect(() => CipManifest.fromNormalized(d), throwsFormatException);
    expect(CipManifest.fromNormalized(rehashed(d)).minor, 11);
  });
}
