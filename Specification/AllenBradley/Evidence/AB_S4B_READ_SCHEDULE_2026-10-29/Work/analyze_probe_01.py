from pathlib import Path
import collections,gzip,json
W=Path(__file__).parent
d=json.loads(gzip.decompress((W/'header_probe_02.json.gz').read_bytes()));last=d['outcomes'][-1]
raw=last['dataValues'];failed=[v for v in raw.values() if v['status']!=0]
assert len(d['outcomes'])==87 and len(failed)==len(d['paths'])==5
failures=failed[0]['coherenceFailures']
value=dict(measurementComplete=True,samples=87,goodBeforeFailure=86,selectedPaths=d['paths'],
 refusedPaths=len(failed),attempts=last['acquisition']['attempts'],rowReason=last['acquisition']['reason'],
 totalRowAcquisitionUs=last['elapsedUs'],failureReasons=dict(collections.Counter(f['reason'] for f in failures)),
 failedWindowsUs=[f['windowUs'] for f in failures],failedCounters=failures,
 sourceAgeMs=failed[0]['ageMs'],controllerChanges=0,nativeAcceptanceClaim=False,
 note='One root header, no desktop rendering, one logical row outstanding; peer-derived finding only.')
with (W/'header_probe_analysis_01.json').open('x') as f:json.dump(value,f,indent=2)
print(json.dumps(value))
