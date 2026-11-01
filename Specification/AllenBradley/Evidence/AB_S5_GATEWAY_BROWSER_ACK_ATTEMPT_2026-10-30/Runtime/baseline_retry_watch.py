"""Bounded read-only state/ACK recorder for the unchanged baseline fixture."""
from pathlib import Path
import datetime,json,os,sys,time
D=Path(__file__).parent
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_station as station
import fraktal_ab_mailbox as mb
from s5_session import authorize
authorize(json.loads((D/'authorization.json').read_bytes()))
app=station.application();rows=[];last=None;started=time.monotonic()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    with (D/'baseline_retry_watch_ready.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(ready=True,readOnly=True,serial='601FC87B'),stream)
    while not (D/'baseline_retry_watch_stop.json').exists() and time.monotonic()-started<300:
        unit=px.read_unit(comm)
        access=projection.read_access(comm)
        ack=comm.Read(mb.response_tag_name(app)+'.AckSequence')
        if unit is None or ack.Status!='Success':raise RuntimeError('Read-only baseline witness unavailable')
        state=dict(unit={k:unit[k] for k in ('Mode','Step','Running','Complete','Error','ErrorID','Aborted','RunRequest','AbortRequest','ResetRequest')},
            level=access['CurrentLevel'],loginBusy=bool(access['LoginBusy']),legacyAck=ack.Value)
        if state!=last:
            rows.append(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsedMs=int((time.monotonic()-started)*1000),**state));last=state
        time.sleep(.1)
with (D/'baseline_retry_watch.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(passed=True,readOnly=True,controllerWrites=0,serial='601FC87B',changes=rows),stream,indent=2)
print(json.dumps(dict(passed=True,readOnly=True,changes=len(rows),controllerWrites=0)))
