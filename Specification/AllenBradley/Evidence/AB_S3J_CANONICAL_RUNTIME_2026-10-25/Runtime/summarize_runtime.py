from pathlib import Path
import gzip,json,statistics,xml.etree.ElementTree as ET
R=Path(__file__).parent;W=R.parent/'prepare_d93d8292dbb4425d9eba04ba75cd110c'
load=lambda p:json.loads(Path(p).read_bytes())
root=ET.parse(W/'s3j.L5X').getroot();tasks=root.findall('.//Task')
task=next(t for t in tasks if t.get('Type')=='PERIODIC')
period=int(float(task.get('Rate'))*1000)
assert period==10000
summaries={}
for kind in ('candidate','baseline'):
 t=load(R/(kind+'_timing_01.json'));rows=t['samples'];assert len(rows)==20
 values=[r['values'] for r in rows]
 last=[r['FRK_Press_HealthProbe.TaskLastScanUs'] for r in values]
 peaks=[v for r in values for k,v in r.items() if k.endswith(('TaskMaxScanUs','.MaxScanUs'))]
 overlaps=[v for r in values for k,v in r.items() if k.endswith(('TaskOverlapCount','.OverlapCount'))]
 summary=dict(passed=max(peaks)<period and max(overlaps)==0,samples=20,periodUs=period,lastScanMedianUs=statistics.median(last),lastScanMinimumUs=min(last),lastScanMaximumUs=max(last),cumulativeMaxScanUs=max(peaks),overlaps=max(overlaps),marginUs=period-max(peaks))
 with (R/(kind+'_timing_summary_01.json')).open('x') as f:json.dump(summary,f,indent=2)
 summaries[kind]=summary
idle=json.loads(gzip.decompress((R/'idle_equivalence_01.json.gz').read_bytes()))
assert idle['passed']
frame=idle['pair']['stateEvidence']['frame']
summary=dict(passed=all(v['passed'] for v in summaries.values()),timing=summaries,idleTypedPaths=idle['comparison']['typedPaths'],nativeFrameBytes=frame['bytes'],fragmentPackets=len(idle['pair']['fragmentPacketEvidence']),readConnections=idle['pair']['readConnections'],fragmentRevision=frame['fragmentRevision'])
with (R/'measurements_summary_01.json').open('x') as f:json.dump(summary,f,indent=2)
print(json.dumps(summary))
