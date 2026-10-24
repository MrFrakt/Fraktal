from pathlib import Path
import json,struct,subprocess,sys
W=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools');sys.path.insert(0,str(T))
from pylogix import PLC
import fraktal_ab_paired_fragments as fragments
subprocess.run([sys.executable,'C:/work/fraktal-ab-s3h-20261023/prepare_5822102a73e348ec95ff7082959ef940/scripts/guard_echo.py'],check=True)
rows=[]
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot=0;comm.ConnectionSize=4000;comm.SocketTimeout=3
    d=comm.GetDeviceProperties();assert d.Status=='Success' and str(d.Value.SerialNumber).lower()=='0x601fc87b'
    r=comm.Read('FRK_Press_AccessAudit');assert r.Status=='Success'
    request=fragments.request(comm,'FRK_Press_AccessAudit',0)
    for i in range(5):
        frame=comm.conn._build_eip_header(request);status,reply=comm.conn._get_bytes(frame,True)
        assert status==6
        rows.append(dict(txSession=frame[4:8].hex(),rxSession=reply[4:8].hex(),
            txContext=frame[12:20].hex(),rxContext=reply[12:20].hex(),
            txSequence=struct.unpack_from('<H',frame,44)[0],rxSequence=struct.unpack_from('<H',reply,44)[0]))
with (W/'connected_headers_01.json').open('x') as f:json.dump(dict(readOnly=True,controllerWrites=0,rows=rows),f,indent=2)
print(json.dumps(rows))
