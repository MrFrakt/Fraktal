"""Read-only fixed-target TASK telemetry, including download/Run transition."""
from pathlib import Path
import datetime
import gzip
import json
import time
from pylogix import PLC
from qualification_session_v2 import authorize

D=Path(__file__).parent
TAGS=['FRK_Press_HealthProbe.'+name for name in
      ('Samples','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')]

def acquire(comm,started):
    before=time.monotonic()
    row=dict(elapsedUs=int((before-started)*1000000),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),available=False)
    try:
        responses=comm.Read(TAGS)
        good=isinstance(responses,list) and len(responses)==len(TAGS) and all(
            response.Status=='Success' and type(response.Value) is int for response in responses)
        row['available']=good
        if good:
            row['values']={response.TagName:response.Value for response in responses}
        else:
            row['statuses']=[str(response.Status) for response in responses] if isinstance(responses,list) else [str(responses)]
    except Exception as error:
        row['error']=f'{type(error).__name__}: {error}'
    row['readUs']=int((time.monotonic()-before)*1000000)
    return row

def main():
    authorize(json.loads((D/'authorization.json').read_bytes()))
    for name in ('task_monitor_ready.json','task_monitor_stop.json','task_monitor.json.gz'):
        assert not (D/name).exists(),name
    rows=[]
    started=time.monotonic()
    ready=False
    with PLC('127.0.0.1') as comm:
        comm.ProcessorSlot=0
        comm.ConnectionSize=4000
        comm.SocketTimeout=1
        identity=comm.GetDeviceProperties()
        assert identity.Status=='Success' and str(identity.Value.SerialNumber).lower()=='0x601fc87b'
        assert identity.Value.Revision=='38.11' and identity.Value.ProductCode==288
        while not (D/'task_monitor_stop.json').exists() and time.monotonic()-started<1800:
            before=time.monotonic()
            row=acquire(comm,started)
            rows.append(row)
            if row['available'] and not ready:
                with (D/'task_monitor_ready.json').open('x') as stream:
                    json.dump(dict(ready=True,readOnly=True,serial='601FC87B'),stream)
                ready=True
            remaining=.1-(time.monotonic()-before)
            if remaining>0:
                time.sleep(remaining)
        final=comm.GetDeviceProperties()
        assert final.Status=='Success' and str(final.Value.SerialNumber).lower()=='0x601fc87b'
    report=dict(schema='fraktal.ab.s4b-native-task-monitor',readOnly=True,serial='601FC87B',
        source='PLC GSV TASK scalars, nominal 100 ms host polling; per-tag observations, not an atomic canonical row',
        passed=ready and (D/'task_monitor_stop.json').exists(),rows=rows,
        missingTagsDuringDownloadRetained=True,counterOrFaultClears=0,clockChanges=0,writes=0)
    with (D/'task_monitor.json.gz').open('xb') as stream:
        stream.write(gzip.compress(json.dumps(report).encode(),mtime=0))
    print(json.dumps(dict(passed=report['passed'],rows=len(rows),readOnly=True,writes=0)))
    return 0 if report['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
