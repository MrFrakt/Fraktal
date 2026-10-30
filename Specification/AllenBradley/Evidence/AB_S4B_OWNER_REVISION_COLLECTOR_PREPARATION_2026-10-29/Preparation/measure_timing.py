"""Read-only native TASK timing samples on the guarded local Echo fixture."""
import json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from pylogix import PLC
work=Path('C:/work/fraktal-ab-s4b-owner-20261029/session_03')
output=Path(sys.argv[1]); candidate='--candidate' in sys.argv[2:]
if output.exists(): raise SystemExit('new output required')
subprocess.run([sys.executable,str(work/'scripts/guard_echo.py')],check=True)
tags=['FRK_Press_HealthProbe.'+name for name in ('Samples','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')]
if candidate: tags += ['FRK_Press_CanonicalTiming.'+name for name in ('Scan','LastScanUs','MaxScanUs','OverlapCount')]
rows=[]
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot=0; comm.ConnectionSize=4000; comm.SocketTimeout=5
    for unused in range(20):
        started=time.perf_counter()
        responses=comm.Read(tags)
        if any(response.Status!='Success' or type(response.Value) is not int for response in responses):
            raise RuntimeError('native timing read failed')
        rows.append(dict(values={response.TagName:response.Value for response in responses},readMs=(time.perf_counter()-started)*1000))
        time.sleep(.05)
report=dict(schema='fraktal.ab.native-task-timing',readOnly=True,serial='601FC87B',capturedUtc=datetime.now(timezone.utc).isoformat(),candidate=candidate,unit='microseconds',source='PLC GSV TASK LastScanTime/MaxScanTime; cumulative since task reset',samples=rows)
with output.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
print(json.dumps(dict(samples=len(rows),first=rows[0]['values'],last=rows[-1]['values'])))
