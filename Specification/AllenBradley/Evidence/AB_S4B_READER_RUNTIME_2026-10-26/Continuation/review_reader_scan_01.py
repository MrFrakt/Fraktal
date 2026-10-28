from pathlib import Path
import gzip
import json
import statistics

W = Path(__file__).parent
D = W.parent / 'retry_reader_01'
analysis = json.loads((D / 'scan_analysis_01.json').read_bytes())
rows = sorted(analysis['rows'], key=lambda row: row['probe']['Samples'])
first, last = rows[0], rows[-1]
dart = json.loads(gzip.decompress((D / 'dart_qualification.json.gz').read_bytes()))
result = dict(readOnly=True,controllerAccess=False,captures=len(rows),
    firstCapture=dict(output=first['output'],**first['probe']),
    lastCapture=dict(output=last['output'],**last['probe']),
    capturedOverlapCounts=sorted({row['probe']['TaskOverlapCount'] for row in rows}),
    capturedCumulativeMaxScanUs=sorted({row['probe']['TaskMaxScanUs'] for row in rows}),
    capturedLastScanRangeUs=[min(row['probe']['TaskLastScanUs'] for row in rows),max(row['probe']['TaskLastScanUs'] for row in rows)],
    capturedLastScanMedianUs=statistics.median(row['probe']['TaskLastScanUs'] for row in rows),
    firstDartHealth={key:value for key,value in dart['snapshots'][0]['values'].items()
        if any(word in key.lower() for word in ('scan','overlap','faultbits'))},
    finding='One overlap and 10033 us cumulative maximum already present in earliest recorded pair; capture timeline does not locate the initial event.',
    codeOrHostCauseConfirmed=False,clearsPerformed=0,clockChanges=0,
    followup='Observe native TASK scalars from Run through discovery/readiness and the full workload; preserve the original counters without clearing them.')
with (D / 'scan_review_01.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps({key:value for key,value in result.items() if key not in ('firstCapture','lastCapture','firstDartHealth')}))
