"""Read and validate completed S3i evidence; no controller connection."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,statistics
R=Path(__file__).parent;W=Path('C:/work/fraktal-ab-s3i-20261024/prepare_d6df75f72d02435aab2ef3fbd7ea986d')
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
session=load(R/'session_execution_01.json');assert session['passed'] and load(R/'start_execution_01.json')['passed']
candidate=load(R/'candidate_regressions_01.json');baseline=load(R/'baseline_regressions_01.json')
assert candidate['restored'] and baseline['restored'] and not candidate.get('error') and not baseline.get('error')
assert len(candidate['rows'])==len(baseline['rows'])==31
assert all(row['passed'] for row in candidate['rows']+baseline['rows'])
for key,n in (('s3iAccessRows',2),('s3iConfigRows',8)):
    assert len(candidate[key])==n and all(row['passed'] for row in candidate[key])
native=candidate['s3iNativeChecks'];assert native['passed'] and native['cases']==8 and native['ownersRestoredExactly']
assert candidate['s3fSetMediumEmpty'] and candidate['policyRestored'] and baseline['policyRestored']
replay=load(R/'independent_replay_01.json');assert replay['passed'] and replay['captures']==88
final=load(R/'final_checks_01.json');assert final['passed'] and all(final['checks'].values())
assert not load(R/'dumps_after_session_01.json')['dumpFiles']
idle=json.loads(gzip.decompress((R/'idle_equivalence_01.json.gz').read_bytes()))
generic=json.loads(gzip.decompress((R/'generic_snapshot_01.json.gz').read_bytes()))
assert idle['passed'] and generic==idle['pair']['canonical'] or idle['passed'] and generic['nodeCount']==3968
assert idle['comparison']['comparedPaths']==3968 and generic['nodeCount']==3968 and generic['moduleCount']==7
records=[dict(tag=row['tag'],bytes=len(row['rawHex'])//2) for row in idle['pair']['capture']['records']]
assert [row['bytes'] for row in records]==[134720,7308,16616]
frame=idle['pair']['fragmentPacketEvidence'];assert len(frame)==44 and frame[0]['plan']['total']==173792
timing={}
for name in ('candidate','baseline'):
    samples=load(R/(name+'_timing_01.json'))['samples'];values=[row['values'] for row in samples]
    timing[name]={key:dict(minimum=min(row[key] for row in values),median=statistics.median(row[key] for row in values),maximum=max(row[key] for row in values))
        for key in values[0] if any(token in key for token in ('LastScan','MaxScan','Overlap'))}
    assert all(row['maximum']==0 for key,row in timing[name].items() if 'Overlap' in key)
all_pairs=[]
for path in sorted(R.glob('*.json.gz')):
    data=json.loads(gzip.decompress(path.read_bytes()))
    if not isinstance(data,dict) or not isinstance(data.get('pair'),dict):continue
    all_pairs.append(data)
assert len(all_pairs)==88
assert all(p['pair']['canonical']['values']['Press/ShiftHistoryCount']==0 for p in all_pairs)
summary=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidateChecks=41,nativePublicationVectors=8,baselineChecks=31,totalChecks=80,
    pairedCaptures=88,independentReplays=88,attempts=replay['attempts'],
    pathCounts=sorted({p['comparison']['comparedPaths'] for p in all_pairs}),
    idlePaths=3968,modules=7,records=records,frameBytes=173792,frameFragments=44,
    calendarProducerLifetimeAccepted=False,observedLiveShiftHistoryCounts=[0],
    nativeBenchPopulatedHistoryRows=8,physicalRetentionAccepted=False,
    timing=timing,final=final,capacity=load(W/'capacity_review.json'),
    preparedAcdSha256='A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42',
    postDownloadSavedAcdSha256=sha(W/'s3i_canonical.ACD'),pristineReviewAcdSha256=sha(W/'capacity_review.ACD'),
    sourceSha256=sha(W/'s3i_bench_05.L5X'),backupSha256=sha(W/'echo_before_s3i.ACD'),
    genealogyOriginalSha256=sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')),
    sessionApprovalConsumed=True,controllerFaultClear=False,clockChanged=False,newDumps=0)
assert summary['pristineReviewAcdSha256'].upper()==summary['preparedAcdSha256']
assert summary['genealogyOriginalSha256'].upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
with (R/'runtime_summary_01.json').open('x') as f:json.dump(summary,f,indent=2)
print(json.dumps({k:summary[k] for k in ('passed','candidateChecks','nativePublicationVectors','baselineChecks','pairedCaptures','idlePaths','frameBytes','calendarProducerLifetimeAccepted','sessionApprovalConsumed')}))
