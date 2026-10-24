"""Read-only negotiation/fragment-size measurement on exact restored Echo."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools');sys.path.insert(0,str(T))
from pylogix import PLC
import fraktal_ab_paired_fragments as fragments
W=Path(__file__).parent;P=W.parent/'retry_fc306d330cc642499a52abbb53bae945'
rows=[]
for size in (4000,4002,8000,16000,60000):
 subprocess.run([sys.executable,str(P/'scripts/guard_echo.py')],check=True)
 row=dict(requestedConnectionSize=size)
 try:
  with PLC('127.0.0.1') as comm:
   comm.ProcessorSlot=0;comm.ConnectionSize=size;comm.SocketTimeout=3
   d=comm.GetDeviceProperties();assert d.Status=='Success' and str(d.Value.SerialNumber).lower()=='0x601fc87b'
   result=comm.conn.connect();row.update(connected=bool(result[0]),connectionStatus=str(result[1]),actualConnectionSize=comm.ConnectionSize)
   if result[0]:
    response=comm.conn.send(fragments.request(comm,'FRK_Press_AccessAudit',0))
    status,kind,raw=fragments.unpack(response)
    row.update(fragmentStatus=status,fragmentBytes=len(raw),nativeTypeHex=kind.hex(),payloadSha256=hashlib.sha256(raw).hexdigest())
 except Exception as error:row.update(error=f'{type(error).__name__}: {error}')
 rows.append(row)
report=dict(readOnly=True,controllerChanges=0,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),serial='601FC87B',
 packetService='Read Tag Fragmented 0x52 only after temporary connected session negotiation',rows=rows)
with (W/'message_size_probe_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
