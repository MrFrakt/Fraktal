import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_read_plan.dart';
import 'package:fraktal_opcua_client/src/cip_read_coherence.dart';
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/test/cip_read_plan_test.dart' as peer;
import 'file:///C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/test/cip_publication_test.dart' as fixture;
import 'previous_read_plan.dart' as previous;

void main() {
  test('ordering preserves every wire read and all projected values/types', () async {
    final capture=fixture.fixtures().last['capture'] as Map;
    final a=peer.CaptureWire(capture), b=peer.CaptureWire(capture);
    final old=previous.CipReadPlan(fixture.publication(capture), a,
      clockUs:()=>0, guard:CipReadCoherenceGuard(clockUs:()=>0));
    final current=CipReadPlan(fixture.publication(capture), b,
      clockUs:()=>0, guard:CipReadCoherenceGuard(clockUs:()=>0));
    await old.acquire(); await old.acquire();
    await current.acquire(); await current.acquire();
    Map<String,int> counts(List<String> reads) {
      final result=<String,int>{};
      for(final path in reads) result.update(path,(n)=>n+1,ifAbsent:()=>1);
      return result;
    }
    expect(b.reads, isNot(orderedEquals(a.reads)));
    expect(counts(b.reads),counts(a.reads));
    expect(current.snapshot()['values'],old.snapshot()['values']);
    expect(current.snapshot()['types'],old.snapshot()['types']);
  });
}
