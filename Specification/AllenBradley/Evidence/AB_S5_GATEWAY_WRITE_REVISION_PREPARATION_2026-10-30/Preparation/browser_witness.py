"""Bounded owner Chrome witness; validates input, never manufactures a pass."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time,uuid
D=Path(__file__).parent
CHECKS=('liveOverview','login','modeAcknowledged','logout')

def validate_owner(record,token,before,after):
    if record.get('token')!=token or record.get('ownerRecorded') is not True or record.get('passed') is not True:
        raise ValueError('Current successful owner checklist required')
    if not isinstance(record.get('ownerWords'),str) or not record['ownerWords'].strip():raise ValueError('Owner words required')
    if record.get('checks')!={key:True for key in CHECKS}:raise ValueError('Complete owner checklist required')
    for state in (before,after):
        if state['serial']!='601FC87B' or state['mode']!=1 or state['currentLevel']!=0 or not state['idle'] or state['loginBusy']:
            raise ValueError('Expected logged-out MANUAL idle browser boundary')
    delta=(after['typedAck']-before['typedAck']) & 0xffffffff
    if not 4<=delta<0x80000000:raise ValueError('No forward login/mode/return/logout acknowledgement evidence')
    return dict(passed=True,ownerRecorded=True,checklist=record['checks'],acknowledgementDelta=delta,
        before=before,after=after,credentialValuesRecorded=False)

def state():
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
    sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
    from pylogix import PLC
    from fraktal_ab_part_execute import Guarded
    import fraktal_ab_station as station
    import fraktal_ab_press_execute as execute
    import fraktal_ab_projection as projection
    app=station.application()
    subprocess.run([sys.executable,str(D/'scripts/guard_echo.py')],check=True)
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
        comm=Guarded(native,0x601FC87B,app);comm.guard()
        unit=execute.read_unit(comm);access=projection.read_access(comm)
        ack=comm.Read('Press.HmiResponse.AckSequence')
        if ack.Status!='Success' or type(ack.Value) is not int:raise ValueError('Browser acknowledgement read failed')
        return dict(serial='601FC87B',mode=unit['Mode'],currentLevel=access['CurrentLevel'],loginBusy=bool(access['LoginBusy']),
            idle=not any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')),
            typedAck=ack.Value&0xffffffff,readOnly=True)

def witness(save,timeout=1200):
    before=state();token=uuid.uuid4().hex
    save('browser_ready.json',dict(ready=True,token=token,before=before,ownerActionRequired=True,
        url='http://127.0.0.1:8080/',viewerUrl='http://127.0.0.1:8081/',
        checklist=list(CHECKS),modeSequence='MANUAL -> AUTO -> MANUAL',deadlineSeconds=timeout,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    deadline=time.monotonic()+timeout;path=D/'browser_owner_checklist.json'
    while not path.exists():
        if time.monotonic()>deadline:raise TimeoutError('Owner C12 checklist not received within browser window')
        time.sleep(.1)
    record=json.loads(path.read_bytes());after=state()
    result=validate_owner(record,token,before,after)
    save('browser_C12_result.json',result)
    return result
