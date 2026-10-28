import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_opcua_client/src/cip_transport.dart';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:io';
import 'cip_read_plan_test.dart' as captured;
import 'cip_publication_test.dart' as golden;
import '../lib/data/opcua_field_tier.dart';

class ProfileWire extends captured.CaptureWire {
  int requests = 0;
  ProfileWire(super.capture);
  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) {
    requests++;
    return super.request(service, path, data);
  }
}

void main() {
  test('profile the unchanged cyclic acquisition against recorded bytes', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final publication = golden.publication(capture), wire = ProfileWire(capture);
    final plan = CipReadPlan(publication, wire,
        guard: CipReadCoherenceGuard(clockUs: () => 0));
    final slow = <String>{}, excluded = <String>{};
    final paths = publication.discoverPaths();
    final tiers = <String, int>{};
    for (final path in paths) {
      final tier = OpcUaFieldTier.classify(path);
      tiers.update(tier.name, (n) => n + 1, ifAbsent: () => 1);
      if (OpcUaFieldTier.isRequestPayload(path) ||
          path.split('/').any((s) => OpcUaFieldTier.unconsumedContainers.contains(s.split('[').first)) ||
          tier == FieldTier.onDemand) {
        excluded.add(path);
      } else if (tier == FieldTier.slow) {
        slow.add(path);
      }
    }
    plan.slowPaths = slow;
    plan.excludedPaths = excluded;
    final timer = Stopwatch()..start();
    await plan.acquire();
    final firstUs = timer.elapsedMicroseconds;
    await plan.acquire();
    final secondUs = timer.elapsedMicroseconds - firstUs;
    final snapshot = plan.snapshot();
    final result = <String, Object?>{
      'firstAcquisitionUs': firstUs, 'secondAcquisitionUs': secondUs,
      'requests': wire.requests, 'groups': plan.acquisitions.length,
      'paths': paths.length, 'slow': slow.length, 'excluded': excluded.length,
      'tiers': tiers, 'sampleCount': (snapshot['dataValues'] as Map).length,
      'maximumAgeMs': (snapshot['dataValues'] as Map).values.fold<num>(0,
          (n, dynamic row) => row['ageMs'] > n ? row['ageMs'] as num : n),
    };
    final output = File(Platform.environment['FRAKTAL_SCHEDULE_PROFILE_OUTPUT']!);
    expect(output.existsSync(), false);
    output.writeAsStringSync(jsonEncode(result));
    print(jsonEncode(result));
  });
}
