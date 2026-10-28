"""Read-only full equivalence immediately before a separately authorized cycle."""
from pathlib import Path
import json,os,sys
W=Path(__file__).parent
# Installed under scripts/: keep the session root as the authorization owner.
if W.name=='scripts':W=W.parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0,str(W))
from candidate_profile import configure
configure()
import fraktal_ab_s3i_lifetime_execute as fixture
import fraktal_ab_part_execute as guarded
import fraktal_ab_station as station
from pylogix import PLC
approval=fixture.authorize(W/'authorization.json');R=Path(approval['RuntimeDirectory'])
before=json.loads((R/'calendar_01.json').read_text(encoding='utf-8'))
destination=R/'retention_preflight_01.json';assert not destination.exists()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,10
    comm=guarded.Guarded(native,0x601FC87B,station.application());comm.guard()
    result=fixture.verify_retention(comm,before,destination)
with destination.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],controllerWrites=0)))
