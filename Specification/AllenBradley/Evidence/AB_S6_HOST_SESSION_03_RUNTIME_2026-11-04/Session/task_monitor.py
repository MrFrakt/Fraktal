"""Read-only fixed-target TASK telemetry every 100 ms, through download and Run.

Appends one JSON line per sample to task_monitor.jsonl, writes the ready file
after its first good sample, and stops on task_monitor_stop.json or after
MAX_SECONDS. It reads only the health-probe tags; it never writes.
"""
from pathlib import Path
import datetime, json, time
from pylogix import PLC

D = Path(__file__).parent
MAX_SECONDS = 5400
TAGS = ['FRK_Press_HealthProbe.' + n for n in ('Samples', 'TaskLastScanUs', 'TaskMaxScanUs', 'TaskOverlapCount')]
for name in ('task_monitor_ready.json', 'task_monitor_stop.json', 'task_monitor.jsonl', 'task_monitor_summary.json'):
    assert not (D / name).exists(), name
started, ready, rows, good = time.monotonic(), False, 0, []
with PLC('127.0.0.1') as comm, (D / 'task_monitor.jsonl').open('x', encoding='utf-8') as out:
    comm.ProcessorSlot, comm.ConnectionSize, comm.SocketTimeout = 0, 4000, 1
    identity = comm.GetDeviceProperties()
    assert identity.Status == 'Success' and str(identity.Value.SerialNumber).lower() == '0x601fc87b'
    assert identity.Value.Revision == '38.11' and identity.Value.ProductCode == 288
    while not (D / 'task_monitor_stop.json').exists() and time.monotonic() - started < MAX_SECONDS:
        before = time.monotonic()
        row = dict(elapsedMs=round((before - started) * 1000, 1),
                   utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), available=False)
        try:
            responses = comm.Read(TAGS)
            if (isinstance(responses, list) and len(responses) == len(TAGS)
                    and all(r.Status == 'Success' and type(r.Value) is int for r in responses)):
                row.update(available=True, values={r.TagName.split('.')[-1]: r.Value for r in responses})
                good.append(row['values'])
            else:
                row['statuses'] = [str(r.Status) for r in responses] if isinstance(responses, list) else [str(responses)]
        except Exception as error:
            row['error'] = f'{type(error).__name__}: {error}'
        out.write(json.dumps(row) + '\n')
        out.flush()
        rows += 1
        if row['available'] and not ready:
            with (D / 'task_monitor_ready.json').open('x') as stream:
                json.dump(dict(ready=True, readOnly=True, serial='601FC87B'), stream)
            ready = True
        remaining = .1 - (time.monotonic() - before)
        if remaining > 0:
            time.sleep(remaining)
summary = dict(readOnly=True, serial='601FC87B', samples=rows, available=len(good),
               maxScanUs=max((v['TaskMaxScanUs'] for v in good), default=None),
               lastMaxScanUs=good[-1]['TaskMaxScanUs'] if good else None,
               overlapCount=good[-1]['TaskOverlapCount'] if good else None,
               stoppedByFile=(D / 'task_monitor_stop.json').exists())
with (D / 'task_monitor_summary.json').open('x', encoding='utf-8') as stream:
    json.dump(summary, stream, indent=2)
print(json.dumps(summary))
