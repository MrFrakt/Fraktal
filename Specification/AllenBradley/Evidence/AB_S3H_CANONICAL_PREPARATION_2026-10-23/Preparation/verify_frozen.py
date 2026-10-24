"""Run emitted S3h ST against the immutable 278-path genealogy owner snapshot."""
from pathlib import Path
from types import SimpleNamespace
import gzip,hashlib,json,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');P=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
sys.path.insert(0,str(T))
import fraktal_ab_host_events as host
import fraktal_ab_part as part
import fraktal_ab_signal_tower as tower
import fraktal_ab_press_execute as execute
import fraktal_ab_s3h_reference as reference
from test_fraktal_ab_s3h_traceability import TraceabilityTests
raw=gzip.decompress((T/'fixtures/canonical/genealogy_projection_01.json.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest()=='5ca907e6076a02833a5670ef3741cd62aca626f762f9dd557f1e4b9c2c3bbe0c'
frozen=json.loads(raw)
class Captured:
    def Read(self,name):
        rows=[r for r in frozen['reads'] if r['tag']==name and r['status']=='Success' and isinstance(r['value'],dict) and 'bytes' in r['value']]
        chosen=max(rows,key=lambda r:len(r['value']['bytes']))
        return SimpleNamespace(Status='Success',Value=bytes.fromhex(chosen['value']['bytes']))
test=TraceabilityTests();test.setUp();app=test.app
for name,members,destination in ((part.tag(app),part.members(app),test.raw_part),
    (host.tag(app),host.members(app),test.raw_host),(tower.tag(app),tower.members(),test.raw_tower)):
    held=execute.read_layout(Captured(),name,members);assert held is not None;destination.update(held)
expected={p.removeprefix(app.name+'/'):v for p,v in frozen['values'].items() if p.split('/')[1] in ('Part','HostEvents','Nameplate','SignalTower','MachineState')}
projected=reference.values(app,test.raw_part,host.decode(app,test.raw_host,test.codes),test.raw_tower)
assert projected==expected and len(expected)==278
test.scan();test.assert_exact();assert test.actual()==expected
report=dict(passed=True,paths=278,exactValues=True,executedGeneratedST=True,independentReference=True,
    frozenExpandedSha256=hashlib.sha256(raw).hexdigest(),dateTimeUnsetCoveredByFocusedTest=True)
with (P/'frozen_verification_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
