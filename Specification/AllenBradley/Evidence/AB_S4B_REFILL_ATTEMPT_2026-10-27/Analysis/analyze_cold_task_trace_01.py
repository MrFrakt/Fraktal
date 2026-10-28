from pathlib import Path
import gzip
import json
import statistics

W=Path(__file__).parent
D = Path('C:/work/fraktal-ab-s4b-refill-20261027/session_01')
trace=json.loads(gzip.decompress((D/'task_monitor.json.gz').read_bytes()))
assert trace['passed'] and trace['readOnly'] and trace['writes']==0
prefix='FRK_Press_HealthProbe.'
groups=[]
events=[]
previous=None
good=[]
for index,row in enumerate(trace['rows']):
    if not row['available']:
        continue
    values=row['values']
    value={key.removeprefix(prefix):number for key,number in values.items()}
    if previous is None or value['Samples']<previous['Samples']:
        groups.append([])
        events.append(dict(kind='probe-counter-epoch',epoch=len(groups)-1,row=index,
            elapsedUs=row['elapsedUs'],utc=row['utc'],values=value))
    elif value['TaskOverlapCount']!=previous['TaskOverlapCount']:
        events.append(dict(kind='overlap-count-change',epoch=len(groups)-1,row=index,
            elapsedUs=row['elapsedUs'],utc=row['utc'],previous=previous,values=value))
    groups[-1].append(dict(row=index,elapsedUs=row['elapsedUs'],utc=row['utc'],values=value))
    good.append(row)
    previous=value
epochs=[]
for index,rows in enumerate(groups):
    epochs.append(dict(epoch=index,rows=len(rows),first=rows[0],last=rows[-1],
        maxTaskScanUs=max(row['values']['TaskMaxScanUs'] for row in rows),
        maxOverlapCount=max(row['values']['TaskOverlapCount'] for row in rows),
        firstObservedOverlap=next((row for row in rows if row['values']['TaskOverlapCount']>0),None)))
intervals=[b['elapsedUs']-a['elapsedUs'] for a,b in zip(trace['rows'],trace['rows'][1:])]
result=dict(readOnly=True,controllerAccess=False,rows=len(trace['rows']),validRows=len(good),
    unavailableRows=len(trace['rows'])-len(good),nominalPollMs=100,
    actualPollMedianUs=statistics.median(intervals),actualPollMaxUs=max(intervals),
    epochs=epochs,events=events,
    limitations=['Epochs follow the published probe counter, not inferred controller power state.',
        'Polling bounds first observation; it does not identify the exact offending scan or code/host cause.',
        'Individual TASK scalars are observations, not an atomic canonical row.'])
with (D/'task_trace_analysis_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps({key:value for key,value in result.items() if key not in ('epochs','events','limitations')}))
print(json.dumps(dict(epochs=epochs,events=events)))
