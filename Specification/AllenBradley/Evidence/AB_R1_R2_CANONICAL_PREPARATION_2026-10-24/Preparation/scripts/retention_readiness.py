"""Fresh idle/login/restore check after the offline ACD has opened."""
from pathlib import Path
import json,os,sys
W=Path(__file__).parent
if W.name=='scripts':W=W.parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0,str(W))
from candidate_profile import configure
configure()
import fraktal_ab_s3i_lifetime_execute as fixture
import fraktal_ab_part_execute as guarded
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_station as station
from pylogix import PLC
fixture.authorize(W/'authorization.json');app=station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=guarded.Guarded(native,0x601FC87B,app);comm.guard()
    unit=px.read_unit(comm);access=projection.read_access(comm)
    assert unit is not None and unit['Mode']==app.manual_mode and not any(unit[n] for n in
        ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest'))
    assert access['CurrentLevel']==0 and not projection.read_document(comm)['liveConfig'].restoring
print(json.dumps(dict(passed=True,controllerWrites=0,manual=True,idle=True,loggedOut=True)))
