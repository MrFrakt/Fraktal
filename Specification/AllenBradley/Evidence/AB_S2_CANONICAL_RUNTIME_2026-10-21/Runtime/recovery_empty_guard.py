"""Read-only zero-tag/Program guard for recovery of the approved genealogy image."""
import json,subprocess,sys,time
from pylogix import PLC
work='C:/work/fraktal-ab-s2-20261021/prepare_3701f795c13b4329891f4eca1346b3a5'
subprocess.run([sys.executable,work+'/scripts/guard_echo.py'],check=True)
inspection=subprocess.run(['C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe','inspect'],check=True,text=True,stdout=subprocess.PIPE)
state=json.loads(inspection.stdout)
if state['ControllerMode']!=2:raise SystemExit('Recovery requires Program mode; will not replace a running image')
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot=0;comm.ConnectionSize=4000;comm.SocketTimeout=5
    for unused in range(2):
        response=comm.GetTagList()
        if response.Status!='Success' or response.Value is None or len(response.Value)!=0:
            raise SystemExit('Recovery requires an empty controller; will not replace an unexpected image')
        time.sleep(.25)
print(json.dumps(dict(emptyControllerConfirmed=True,serial='601FC87B',mode='Program')))
