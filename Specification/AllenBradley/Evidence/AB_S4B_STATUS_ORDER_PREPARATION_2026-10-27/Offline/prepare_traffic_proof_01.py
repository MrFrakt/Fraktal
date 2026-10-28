from pathlib import Path
W=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal')
old=R/'Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26/Source/FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/cip_read_plan.dart'
source=old.read_text(encoding='utf-8')
source=source.replace("import 'cip_", "import 'package:fraktal_opcua_client/src/cip_")
with (W/'previous_read_plan.dart').open('x',encoding='utf-8') as f:f.write(source)
test="""import 'package:flutter_test/flutter_test.dart';
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
"""
with (W/'status_read_traffic_test.dart').open('x',encoding='utf-8') as f:f.write(test)
print('Prepared traffic/value comparison against the immutable prior reader.')
