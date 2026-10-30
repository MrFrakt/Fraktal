import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart' as current;
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/test/cip_owner_revision_test.dart' as apparatus;
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/test/cip_publication_test.dart' as golden;
import 'before_count_plan.dart' as previous;

void main() {
  test('before/after share every consumed value and type, with fewer routing reads', () async {
    final capture=apparatus.fixture(), pub=golden.publication(capture);
    final excluded=pub.discoverPaths().where((p)=>
      OpcUaFieldTier.classify(p)==FieldTier.onDemand ||
      OpcUaFieldTier.isRequestPayload(p) || p.contains('/SequenceStepDef[')).toSet();
    final oldWire=apparatus.OwnerWire(capture), newWire=apparatus.OwnerWire(capture);
    final dynamic old=previous.CipReadPlan(pub,oldWire,clockUs:()=>oldWire.nowUs,
      guard:CipReadCoherenceGuard(clockUs:()=>oldWire.nowUs));
    final dynamic next=current.CipReadPlan(pub,newWire,clockUs:()=>newWire.nowUs,
      guard:CipReadCoherenceGuard(clockUs:()=>newWire.nowUs));
    for (final plan in [old,next]) plan.excludedPaths=Set<String>.of(excluded);
    await old.refreshProgress();await next.refreshProgress();
    oldWire.progress=newWire.progress=4;
    await old.acquire();await next.acquire();
    final a=old.snapshot() as Map,b=next.snapshot() as Map;
    expect(a['values'],b['values']);expect(a['types'],b['types']);
    expect(newWire.reads.length,lessThan(oldWire.reads.length));
    final report=dict(a,b,oldWire,newWire);
    final output=File('C:/work/fraktal-ab-s4b-owner-20261029/offline_01/count_walk_comparison_01.json');
    expect(output.existsSync(),false);output.writeAsStringSync(jsonEncode(report));
    // ignore: avoid_print
    print(jsonEncode(report));
  });
}
Map dict(Map a,Map b,apparatus.OwnerWire oldWire,apparatus.OwnerWire next) => {
  'passed':true,'beforeReads':oldWire.reads.length,'afterReads':next.reads.length,
  'values':(b['values'] as Map).length,'typesExact':true,'valuesExact':true,
  'droppedReadCounts':{for(final name in oldWire.reads.toSet())
    if(oldWire.reads.where((p)=>p==name).length>next.reads.where((p)=>p==name).length)
      name:oldWire.reads.where((p)=>p==name).length-next.reads.where((p)=>p==name).length},
  'controllerChanges':0,'nativeAcceptanceClaim':false};
