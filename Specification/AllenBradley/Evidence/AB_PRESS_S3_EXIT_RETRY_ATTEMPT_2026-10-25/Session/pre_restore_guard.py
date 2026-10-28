"""Read-only idle/logout check after SDK open, immediately before Program mode."""
from pathlib import Path
import json,os,sys
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_press_canonical_echo38'
D=Path(__file__).parent;sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_station as station
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_manifest as manifest
approval=json.loads((D/'authorization.json').read_bytes())
assert approval['CurrentOwnerApproved'] and approval['RestoreGenealogyAuthorized'] and approval['Serial']=='601FC87B'
app=station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    unit=execute.read_unit(comm);access=projection.read_access(comm)
    if unit is None or unit['Mode']!=app.manual_mode or any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')):
        raise RuntimeError('candidate must be MANUAL and idle before restoring genealogy')
    if access['CurrentLevel']!=0 or access['LoginBusy']:raise RuntimeError('active HMI/session; restore refused')
    restoring=bool(projection.read_document(comm)['liveConfig'].restoring)
    result=dict(passed=True,readOnly=True,serial='601FC87B',manifest=manifest.content_hash(app),mode=unit['Mode'],currentLevel=0,idle=True,restoringBeforeRollback=restoring)
with (D/'pre_restore_rollback_guard_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
