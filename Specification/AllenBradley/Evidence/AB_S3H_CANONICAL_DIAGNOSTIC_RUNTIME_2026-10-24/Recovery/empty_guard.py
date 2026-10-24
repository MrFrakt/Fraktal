"""Read-only exact Echo, RemoteProgram and two successful empty-symbol guards."""
from pathlib import Path
import json,subprocess,sys,time
from pylogix import PLC
P=Path('C:/work/fraktal-ab-s3h-20261023/diagnostic_0b74f072e0d74c7c97531e07dec70898')
subprocess.run([sys.executable,str(P/'scripts/guard_echo.py')],check=True)
inspection=subprocess.run(['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'],check=True,text=True,capture_output=True)
state=json.loads(inspection.stdout)
if state['ControllerMode']!=2:raise SystemExit('Empty recovery requires RemoteProgram; no mode switch is made here')
counts=[]
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot=0;comm.ConnectionSize=4000;comm.SocketTimeout=5
    for _ in range(2):
        answer=comm._get_tag_list(False)
        if answer.Status!='Success' or not isinstance(answer.Value,list) or len(answer.Value)!=0:
            raise SystemExit('Recovery refuses a nonempty or unverified symbol table')
        counts.append(len(answer.Value))
        time.sleep(.25)
print(json.dumps(dict(emptyControllerConfirmed=True,serial='601FC87B',mode='RemoteProgram',successfulRawSymbolCounts=counts,controllerChanges=0)))
