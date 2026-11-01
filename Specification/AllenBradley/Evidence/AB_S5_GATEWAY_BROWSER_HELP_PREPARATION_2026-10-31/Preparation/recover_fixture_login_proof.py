"""Read-only recovery of the exact logged, accepted C2 login; never infer ownership."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,datetime
from s5_session import authorize
D=Path(__file__).parent
authorize(json.loads((D/'authorization.json').read_bytes()))
assert json.loads((D/'gateway_profile_result.json').read_bytes())['failedCase']=='C2'
log=(D/'gateway_profile.log').read_text()
requests=re.findall(r'stage=opcua-request-start kind=login unit=Press sequence=(\d+)',log)
acks=re.findall(r'stage=opcua-request-ack kind=login sequence=(\d+) accepted=true diagnostic=\s*\n',log)
assert len(requests)==len(acks)==1 and requests==acks
sequence=int(requests[0]);assert not list(D.glob('gateway_authentication_*.json'))
os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from pylogix import PLC
import fraktal_ab_station as station
import fraktal_ab_part_execute as fixture
import fraktal_ab_projection as projection
import fraktal_ab_access as access
from session_ownership import owns_session
account=next(a for a in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_bytes())['users'] if a['level']==4)
subprocess.run([sys.executable,str(D/'scripts/guard_echo.py')],check=True)
app=station.application()
with PLC('127.0.0.1') as native:
    native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
    comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
    observed=access.status(app,projection.read_access(comm))
proof=dict(correlatedByRepository=True,level=4,user=account['user'],loginResultSequence=sequence,
    recoveredFromAcceptedC2=True,readOnly=True,controllerWrites=0,
    acceptedRequestLogSha256=hashlib.sha256((D/'gateway_profile.log').read_bytes()).hexdigest().upper(),
    nativeCorrelation=observed,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
assert owns_session(observed,[proof]), 'Native provider result does not match the single fixture login; no proof or cleanup write'
with (D/'gateway_authentication_recovered_01.json').open('x',encoding='utf-8') as stream:json.dump(proof,stream,indent=2)
print(json.dumps(dict(passed=True,readOnly=True,controllerWrites=0,matchedLoginResultSequence=sequence)))
