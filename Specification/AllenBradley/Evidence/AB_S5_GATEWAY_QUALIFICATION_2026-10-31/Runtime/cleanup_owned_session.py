"""Logout only a correlated login proved to belong to this S5 fixture.

The general active-session guard remains intact. No session without a matching
native test authentication artifact may be logged out by this cleanup.
"""
from pathlib import Path
import json,os,sys
from s5_session import authorize
from session_ownership import owns_session
D=Path(__file__).parent
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_access as access
import fraktal_ab_station as station
import fraktal_ab_mailbox as mb
app=station.application();result=dict(passed=False,controllerWrites=0)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    status=access.status(app,projection.read_access(comm))
    assert not status['Access/LoginBusy'],'authentication still pending; no cleanup write'
    if status['Access/CurrentLevel']:
        proof=[json.loads(p.read_bytes()) for p in sorted(D.glob('gateway_authentication_*.json'))]
        assert owns_session(status,proof),\
            'active session has no matching S5 ownership proof; guard retained'
        answer=execute.command(comm,mb.LOGOUT,settle=4)
        assert answer['accepted']
        result['controllerWrites']='one existing guarded legacy LOGOUT for the proven S5 login only'
    after=access.status(app,projection.read_access(comm))
    assert after['Access/CurrentLevel']==0 and not after['Access/LoginBusy']
    result.update(passed=True,currentLevel=0)
with (D/'owned_session_cleanup.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
