import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_publication_test.dart' as golden;
import '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_read_plan_test.dart' show CaptureWire;
import '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_read_batch_test.dart' show BatchCapture;

void main() {
  test('tiered recorded-wire replay preserves all consumed oracle values/types', () async {
    final fixture = golden.fixtures().last;
    final capture = fixture['capture'] as Map;
    final pub = golden.publication(capture), wire = BatchCapture(capture);
    final slow = <String>{}, excluded = <String>{};
    for (final path in pub.discoverPaths()) {
      if (OpcUaFieldTier.isRequestPayload(path) || path.split('/').any((s) =>
          OpcUaFieldTier.unconsumedContainers.contains(s.split('[').first))) {
        excluded.add(path); continue;
      }
      switch (OpcUaFieldTier.classify(path)) {
        case FieldTier.onDemand: excluded.add(path);
        case FieldTier.slow: slow.add(path);
        case FieldTier.config:
        case FieldTier.live: break;
      }
    }
    var now = 0;
    final plan = CipReadPlan(pub, wire, clockUs: () => now,
      guard: CipReadCoherenceGuard(clockUs: () => now))
      ..slowPaths = slow..excludedPaths = excluded;
    await plan.acquire(); plan.refreshSlow(); await plan.acquire();
    wire.reads.clear(); final previousGroups = plan.acquisitions.length;
    final previousBatches=wire.batches,previousOrdinary=wire.ordinary;
    now = 1000000; await plan.acquire();
    final snapshot = plan.snapshot(), expected = fixture['expected'] as Map;
    final values = {for (final entry in (expected['values'] as Map).entries)
      if (!excluded.contains(entry.key)) entry.key as String: entry.value};
    final types = {for (final entry in (expected['types'] as Map).entries)
      if (!excluded.contains(entry.key)) entry.key as String: entry.value};
    expect(snapshot['values'], values); expect(snapshot['types'], types);
    final result = <String,Object?>{
      'passed': true, 'nativeTimingClaim': false,
      'wireReads': wire.reads.length, 'batchPackets':wire.batches-previousBatches,
      'ordinaryRequests':wire.ordinary-previousOrdinary,
      'packetRequests':wire.batches-previousBatches+wire.ordinary-previousOrdinary,
      'groups': plan.acquisitions.length - previousGroups,
      'hiddenByClassReads': wire.reads.where((p) => p.contains('.Profiler.History[') && p.endsWith('.ByClass')).length,
      'values': values, 'types': types, 'consumedValues': values.length,
    };
    final baseline = Platform.environment['FRAKTAL_TIER_BASELINE'];
    if (baseline != null) {
      final before = jsonDecode(File(baseline).readAsStringSync()) as Map;
      expect(result['values'], before['values']); expect(result['types'], before['types']);
      expect(result['packetRequests'] as int, lessThan(before['wireReads'] as int));
      expect(result['groups'], before['groups']);
      expect(result['hiddenByClassReads'], 0);
    }
    final output = File(Platform.environment['FRAKTAL_TIER_OUTPUT']!);
    expect(output.existsSync(), false); output.writeAsStringSync(jsonEncode(result));
    print(jsonEncode({...result}..remove('values')..remove('types')));
  });
}
