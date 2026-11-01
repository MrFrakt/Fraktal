"""The existing five-document migration bootstrap, not a new regression walk."""
from pathlib import Path
import json,os,sys
from s5_session import authorize
D=Path(__file__).parent
authorize(json.loads((D/'authorization.json').read_bytes()))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_station as station
import fraktal_ab_mailbox as mb
app=station.application()
account=next(a for a in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_bytes())['users'] if a['level']==4)
assert account['user'] in {u.name for u in app.access_users}
evidence=dict(serial='601FC87B',rows=[],regressionCases=0)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    run=fixture.Run(comm,app,account,evidence)
    try:
        run.login()
        run.restore_configuration()
        evidence['passed']=True
    finally:run.command(mb.LOGOUT)
with (D/'commission_candidate.json').open('x',encoding='utf-8') as stream:json.dump(evidence,stream,indent=2)
print(json.dumps(evidence))
