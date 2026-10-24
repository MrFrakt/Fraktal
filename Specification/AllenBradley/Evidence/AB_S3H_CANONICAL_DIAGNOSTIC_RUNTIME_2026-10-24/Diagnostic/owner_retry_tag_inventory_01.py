"""Read-only inventory after the approved diagnostic preflight refused."""
from pathlib import Path
import datetime,json,subprocess,sys
from pylogix import PLC
R=Path(__file__).parent
P=R.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
subprocess.run([sys.executable,str(P/'scripts/guard_echo.py')],check=True)
with PLC('127.0.0.1') as native:
    native.ProcessorSlot=0
    native.SocketTimeout=5
    native.ConnectionSize=4000
    identity=native.GetDeviceProperties()
    assert identity.Status=='Success' and int(str(identity.Value.SerialNumber),0)==0x601FC87B
    tags=native.GetTagList()
    names=[tag.TagName for tag in tags.Value] if tags.Value is not None else None
    report=dict(readOnly=True,controllerChanges=0,serial='601FC87B',
                capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                tagListStatus=tags.Status,tagCount=None if names is None else len(names),
                tagNames=names)
with (R/'owner_retry_tag_inventory_01.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps(report))
if tags.Status!='Success':raise SystemExit(1)
