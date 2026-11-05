import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_namespace.dart';
import 'package:fraktal_opcua_client/src/cip_publication.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';

import 'cip_publication_test.dart' as golden;
import 'cip_read_plan_test.dart' show CaptureWire;

/// The first native V6.11 capture (Echo, S6 session 03, sealed): the gateway's
/// projection and read plan accept it, HostEvents ring included. Before the
/// ring's own owner row was admitted, CipPublication refused every V6.11 image.
Map capture() => jsonDecode(utf8.decode(gzip.decode(
    File('gateway/test/fixtures/host_events_session03_canonical.json.gz').readAsBytesSync()))) as Map;

void main() {
  test('the projection accepts V6.11 and publishes the host-event ring', () {
    final c = capture();
    final pub = golden.publication(c);
    expect(pub.manifest.minor, 11);
    final values = pub.projectRecords(golden.records(c))['values'] as Map;
    expect(values.keys.where((k) => (k as String).startsWith('Press/HostEvents/')), hasLength(220));
    expect(values['Press/HostEvents/NewestSequence'], 144);
  });

  test('a ring owner row that no HostEvents binding names refuses', () {
    final c = capture();
    final manifest = Map<String, Object?>.from(jsonDecode(jsonEncode(c['manifest'])) as Map);
    (manifest['hostServiceBindings'] as List).removeWhere((r) => (r as Map)['Service'] == 4);
    expect(
        () => CipPublication(CipNamespace.fromCapture(c), CipManifest.fromNormalized(manifest)),
        throwsA(isA<FormatException>()));
  });

  test('the read plan reproduces the projection of the V6.11 capture', () async {
    final c = capture();
    final pub = golden.publication(c);
    var now = 0;
    final plan = CipReadPlan(pub, CaptureWire(c),
        clockUs: () => now++, guard: CipReadCoherenceGuard(clockUs: () => 0));
    await plan.acquire();
    await plan.acquire();
    final expected = pub.projectRecords(golden.records(c));
    final result = plan.snapshot();
    expect(result['values'], expected['values']);
    expect(result['types'], expected['types']);
  });
}
