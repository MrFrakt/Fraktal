"""Summarize only recorded worker phase rows; never alter acceptance."""
from pathlib import Path
import json,statistics
W=Path(__file__).parent;S=W.parent/'session_01'
phases=('queueUs','manifestBeforeUs','progressProofUs','acquireUs','manifestAfterUs',
 'projectionUs','ageSelectionUs','pathExpansionUs','assemblyUs','sendUs')
decoder=json.JSONDecoder()
streams={}
for source,path in (('observer',S/'dart_qualification.log'),('desktop',S/'desktop_readonly.log')):
    rows=[]
    if path.is_file():
        for line_no,line in enumerate(path.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            marker=line.find('{"cipTiming"')
            if marker<0:continue
            value,end=decoder.raw_decode(line[marker:])
            assert value['cipTiming'] in ('snapshot','delivery')
            assert type(value['id']) is int
            for key in phases:
                if key in value:assert type(value[key]) is int and value[key]>=0,(source,key)
            rows.append(dict(line=line_no,**value))
    def series(key):
        values=sorted(r[key] for r in rows if key in r)
        return None if not values else dict(count=len(values),minimum=values[0],median=statistics.median(values),
          p95=values[min(len(values)-1,int(len(values)*.95))],maximum=values[-1])
    snapshots=[r for r in rows if r['cipTiming']=='snapshot']
    streams[source]=dict(rows=len(rows),snapshots=len(snapshots),deliveries=sum(r['cipTiming']=='delivery' for r in rows),
      phases={key:series(key) for key in phases},
      slowestSnapshots=sorted(snapshots,key=lambda r:r['acquireUs'],reverse=True)[:8],
      firstSnapshots=snapshots[:4])
result=dict(passed=True,readOnly=True,controllerAccess=False,traceDefault=False,
 interpretation='Recorded wall-clock intervals include instrumentation and scheduling. Assembly includes timing-summary preparation. No network/host/PLC cause or missing snapshot success is inferred.',
 streams=streams)
with (S/'cip_timing_analysis_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps({source:dict(rows=data['rows'],snapshots=data['snapshots'],deliveries=data['deliveries'],phases=data['phases']) for source,data in streams.items()}))
