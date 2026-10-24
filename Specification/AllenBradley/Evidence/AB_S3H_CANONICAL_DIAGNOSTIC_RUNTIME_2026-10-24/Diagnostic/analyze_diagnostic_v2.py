"""Analyze the recorded proof/window clocks only; no controller access."""
from pathlib import Path
import collections,gzip,json,statistics
R=Path(__file__).parent
load=lambda p:json.loads(gzip.decompress(p.read_bytes()))
def distribution(values):
    return dict(minimum=min(values),median=statistics.median(values),maximum=max(values)) if values else None
rows=[]
for path in sorted(R.glob('candidate_regressions_01_window_diagnostic_*.json.gz')):
    d=load(path)
    attempts=d['stateEvidence']['attempts'] if d['acquisitionPassed'] else d['attempts']
    polls=iter(d['generationPolls']);windows=iter(d['readWindows']);spans=[]
    for attempt in attempts:
        opening=next(polls)
        assert opening['generation']==attempt['before']
        if 'after' not in attempt:continue
        closing=next(polls);wire=next(windows)
        assert closing['generation']==attempt['after']
        assert opening['endUs']<=wire['startUs']<=wire['endUs']<=closing['startUs']
        spans.append(dict(generationBefore=attempt['before'],generationAfter=attempt['after'],
            generationDelta=attempt['after']-attempt['before'],closingGenerationOdd=bool(attempt['after']%2),
            openingGenerationReadUs=opening['endUs']-opening['startUs'],
            dispatchGapUs=wire['startUs']-opening['endUs'],wireReadUs=wire['elapsedUs'],
            closingGapUs=closing['startUs']-wire['endUs'],closingGenerationReadUs=closing['endUs']-closing['startUs'],
            fullOpeningToClosingUs=closing['endUs']-opening['startUs']))
    assert next(polls,None) is None and next(windows,None) is None
    row=dict(file=path.name,acquisitionPassed=d['acquisitionPassed'],pollAttempts=len(attempts),
        waitingFreshScan=sum(bool(a.get('waitingFreshScan')) for a in attempts),
        initialOdd=sum(a['before']%2!=0 for a in attempts),completeReadWindows=len(spans),
        generationReadCount=len(d['generationPolls']),wireReadUs=distribution([s['wireReadUs'] for s in spans]),
        openingToClosingUs=distribution([s['fullOpeningToClosingUs'] for s in spans]),
        proofElapsedUs=d['generationPolls'][-1]['endUs'] if d['generationPolls'] else None,
        generationDeltas=sorted(collections.Counter(s['generationDelta'] for s in spans).items()),closingOddReadWindows=sum(s['closingGenerationOdd'] for s in spans),spans=spans)
    if not d['acquisitionPassed']:
        row.update(error=d['error'],taskAfterFailure=d.get('taskAfterFailure'),
            taskReadError=d.get('taskReadError'),unacceptedRawFrames=len(d.get('lastAttemptFrames',[])))
    rows.append(row)
failed=[row for row in rows if not row['acquisitionPassed']]
assert len(rows)==65 and len(failed)==1 and sum(row['acquisitionPassed'] for row in rows)==64
assert failed[0]['pollAttempts']==100 and failed[0]['completeReadWindows']==16
assert failed[0]['proofElapsedUs']<5_000_000
fixture=json.loads((R/'candidate_regressions_01.json').read_text())
items=[dict(group=key,**item) for key,value in fixture.items() if key.endswith('Pairs') for item in value]
failure=[item for item in items if not item['passed']]
assert len(failure)==1 and len(items)==65
tasks={row['tag']:row['value'] for row in failed[0]['taskAfterFailure']}
assert len(tasks)==8 and all(row['status']=='Success' for row in failed[0]['taskAfterFailure'])
assert tasks['FRK_Press_CanonicalTiming.OverlapCount']==tasks['FRK_Press_HealthProbe.TaskOverlapCount']==0
report=dict(passed=True,readOnly=True,controllerAccess=False,instrumented=True,
    acquisitionWindows=65,acceptedAcquisitions=64,failedAcquisitions=1,
    acceptedComparisons=sum(item['passed'] for item in items),failedFixtureCapture=failure[0],
    recordedCandidateRows=len(fixture['rows']),accessRows=len(fixture['s3hAccessRows']),configurationRows=len(fixture['s3hConfigRows']),
    failure=failed[0],allWindows=rows,
    interpretation='The unchanged 100-poll gate stops acquisition. All completed failed windows cross PLC scan boundaries. The post-failure TASK sample shows no overlaps; wire/closing timing leaves insufficient reliable margin in the 10 ms task period. The timing samples diagnose a coherence-acquisition failure, not a controller fault or an accepted mixed snapshot.',
    qualification='TASK values are sampled immediately after failure, before inherited fixture cleanup; they do not provide per-window scan execution time. Instrumentation adds clock/list overhead. No task period, read budget, tolerance or acceptance rule changed. Revision 2 retains exact generation deltas and closing parity; revision 1 floor-divided deltas of one and misleadingly labelled those five odd closes as zero scan deltas. The original report is retained.')
with (R/'diagnostic_analysis_02.json').open('x') as out:json.dump(report,out,indent=2)
print(json.dumps({key:report[key] for key in ('passed','acquisitionWindows','acceptedComparisons','recordedCandidateRows','accessRows','configurationRows','failedFixtureCapture')}))
print(json.dumps({key:failed[0][key] for key in ('pollAttempts','waitingFreshScan','initialOdd','completeReadWindows','generationReadCount','wireReadUs','openingToClosingUs','proofElapsedUs','generationDeltas','closingOddReadWindows','taskAfterFailure')}))
