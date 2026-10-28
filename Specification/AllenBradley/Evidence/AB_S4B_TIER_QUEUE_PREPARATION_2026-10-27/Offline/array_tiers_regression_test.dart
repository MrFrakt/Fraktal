import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_publication_test.dart' as golden;
import '../../fraktal-ab-s4b-20261025/hmi_verify_01/test/cip_read_plan_test.dart' show CaptureWire;

void main() {
  test('closed profiler histories do not read their primitive ByClass arrays', () async {
    final fixture = golden.fixtures().last;
    final capture = fixture['capture'] as Map;
    expect(((fixture['expected'] as Map)['values'] as Map).keys.any((p) =>
        (p as String).contains('/Profiler/History[') && p.contains('/ByClass[')), true);
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final plan = CipReadPlan(pub, wire)..excludedPaths = pub.discoverPaths()
        .where((p) => OpcUaFieldTier.classify(p) == FieldTier.onDemand).toSet();
    await plan.acquire();
    expect(wire.reads.where((p) => p.contains('.Profiler.History[') &&
        p.endsWith('.ByClass')), isEmpty);
  });

  test('fully excluded primitive array leaves cause no cyclic array read', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final field = pub.fields.values.singleWhere((f) => f.path == '${pub.roots.first}/SupportedModesPublished');
    expect(field.member.isArray, true);
    expect(field.member.isStructure, false);
    final leaves = pub.discoverPaths().where((p) => p.startsWith('${field.path}[')).toSet();
    expect(leaves, isNotEmpty);
    final plan = CipReadPlan(pub, wire)..excludedPaths = leaves;
    await plan.acquire();
    expect(wire.reads.where((p) => p.endsWith('.SupportedModesPublished')), isEmpty);
    expect((plan.snapshot()['values'] as Map).keys.toSet().intersection(leaves), isEmpty);
  });

  test('all consumed primitive array leaves slow means heartbeat-only reads', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final prefix = '${pub.roots.first}/SupportedModesPublished';
    final leaves = pub.discoverPaths().where((p) => p.startsWith('$prefix[')).toSet();
    expect(leaves, isNotEmpty);
    var now = 0;
    final plan = CipReadPlan(pub, wire, clockUs: () => now,
      guard: CipReadCoherenceGuard(clockUs: () => now))..slowPaths = leaves;
    await plan.acquire();
    expect(wire.reads.any((p) => p.endsWith('.SupportedModesPublished')), true);
    wire.reads.clear(); now = 1000000;
    await plan.acquire();
    expect(wire.reads.where((p) => p.endsWith('.SupportedModesPublished')), isEmpty);
    wire.reads.clear(); now = 5000000;
    await plan.acquire();
    expect(wire.reads.any((p) => p.endsWith('.SupportedModesPublished')), true);
  });

  test('excluded siblings do not promote the only slow array consumer to fast', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final prefix = '${pub.roots.first}/SupportedModesPublished';
    final leaves = pub.discoverPaths().where((p) => p.startsWith('$prefix[')).toList()..sort();
    expect(leaves.length, greaterThan(1));
    var now = 0;
    final plan = CipReadPlan(pub, wire, clockUs: () => now,
      guard: CipReadCoherenceGuard(clockUs: () => now))
      ..slowPaths = {leaves.first}..excludedPaths = leaves.skip(1).toSet();
    await plan.acquire(); wire.reads.clear(); now = 1000000;
    await plan.acquire();
    expect(wire.reads.where((p) => p.endsWith('.SupportedModesPublished')), isEmpty);
    plan.slowPaths = {}; wire.reads.clear();
    await plan.acquire();
    expect(wire.reads.any((p) => p.endsWith('.SupportedModesPublished')), true);
  });

  test('explicit targeted array reads bypass exclusion under the same row proof', () async {
    final capture = golden.fixtures().last['capture'] as Map;
    final pub = golden.publication(capture), wire = CaptureWire(capture);
    final prefix = '${pub.roots.first}/SupportedModesPublished';
    final leaves = pub.discoverPaths().where((p) => p.startsWith('$prefix[')).toSet();
    expect(leaves, isNotEmpty);
    final plan = CipReadPlan(pub, wire)..excludedPaths = leaves;
    // Warm a complete walk to establish progress without leaving this captured
    // peer's two-reply revision epochs out of phase with the next row guard.
    await plan.acquire();
    wire.reads.clear();
    await plan.acquire(paths: {leaves.first});
    expect(wire.reads.any((p) => p.endsWith('.SupportedModesPublished')), true);
    expect((plan.snapshot(includeExcluded: true)['values'] as Map).keys, contains(leaves.first));
    expect((plan.snapshot()['values'] as Map).keys.toSet().intersection(leaves), isEmpty);
  });
}
