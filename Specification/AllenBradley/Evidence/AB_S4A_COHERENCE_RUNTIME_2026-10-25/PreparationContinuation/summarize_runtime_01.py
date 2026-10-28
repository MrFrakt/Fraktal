"""Independently replay S4a captures and check the completed native session."""
from collections import Counter
from pathlib import Path
import gzip,hashlib,json,math,statistics,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;D=W.parent/'session_01'
T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
from fraktal_ab_canonical_reader import decode_record,snapshot
from fraktal_ab_canonical_equivalence import compare_documents
from fraktal_ab_read_coherence import validate_rows

def load(name):
    path=D/name
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def percentile(items,percent):return sorted(items)[max(0,math.ceil(len(items)*percent/100)-1)]
def timing(name):
    held=load(name);rows=[row['values'] for row in held['samples']]
    prefix='FRK_Press_HealthProbe.'
    return dict(samples=len(rows),lastScanMedianUs=statistics.median(r[prefix+'TaskLastScanUs'] for r in rows),
        cumulativeMaxScanUs=max(r[prefix+'TaskMaxScanUs'] for r in rows),
        overlaps=max(r[prefix+'TaskOverlapCount'] for r in rows),periodUs=10000)

session=load('session_result.json');assert session['passed'] and session['genealogyRestored']
candidate=load('candidate_regressions.json');baseline=load('baseline_regressions.json')
for rows in (candidate,baseline):
    assert len(rows['rows'])==31 and all(r.get('passed') is True for r in rows['rows'])
    assert rows['restored'] and rows['policyRestored']
equivalence=load('idle_equivalence.json.gz');assert equivalence['passed']
replayed=snapshot(equivalence['pair']['capture'])
assert replayed==equivalence['pair']['canonical']
comparison=compare_documents(equivalence['pair']['projection'],replayed)
assert comparison['equal'] and comparison['typeAcceptance'] and comparison['comparedPaths']==4428
capture=load('generic_capture.json.gz');generic=snapshot(capture)
assert generic==load('generic_snapshot.json.gz') and generic['nodeCount']==4428 and generic['moduleCount']==7
assert capture['manifest']['schemaMinor']==7 and len(generic['readCoherenceBindings'])==2
validate_rows(generic['readCoherenceBindings'],expected_prefixes={'Press','PressFieldbus/Topology'})
probe=load('read_group_qualification.json.gz')
assert probe['passed'] and probe['failure'] is None and len(probe['groups'])==8 and len(probe['rows'])==800
assert probe['metadata']['manifest']==capture['manifest']
quality=Counter(row['quality'] for row in probe['rows'])
assert quality=={'GOOD':798,'UNCERTAIN':2}
groups=[];replayed_rows=0
for index,group in enumerate(probe['groups']):
    rows=[r for r in probe['rows'] if r['group']==index]
    assert len(rows)==100 and {r['iteration'] for r in rows}==set(range(100))
    accepted=[r for r in rows if r['quality']=='GOOD']
    assert len(accepted)>=95 and len({r['revision'] for r in accepted})>1
    for row in rows:
        if row['quality']!='GOOD':
            assert row['rawHex'] is None and 'revision' not in row
            continue
        assert row['revision']>0 and row['revision']%2==0 and row['windowUs']<group['binding']['MutationPeriodUs']
        assert 1<=row['attempts']<=3
        raw=bytes.fromhex(row['rawHex']);assert len(raw)==group['bytes']
        decode_record(raw,group['handle'],probe['metadata']['templates']);replayed_rows+=1
    windows=[r['windowUs'] for r in accepted]
    groups.append(dict(symbol=group['symbol'],bytes=group['bytes'],good=len(accepted),uncertain=len(rows)-len(accepted),
        medianUs=statistics.median(windows),p95Us=percentile(windows,95),maxUs=max(windows),
        attempts=dict(Counter(r['attempts'] for r in rows)),progress=True))
windows=[r['windowUs'] for r in probe['rows'] if r['quality']=='GOOD']
assert replayed_rows==798
final=load('final_checks.json');assert final['passed'] and all(final['checks'].values())
assert load('medium_restored_01.json')['originalDocumentsRestored']==5
assert load('preflight_final_exit.json')['exitCode']==0
candidate_time=timing('candidate_timing.json');baseline_time=timing('baseline_timing.json')
assert candidate_time['overlaps']==baseline_time['overlaps']==0
assert candidate_time['cumulativeMaxScanUs']<candidate_time['periodUs']
for label in ('backup_audit','backup_access','deploy_audit','deploy_readback','deploy_access',
              'restore_genealogy_audit','restore_access','candidate_regressions','baseline_regressions',
              'final_checks','preflight_final','baseline_timing','read_group_qualification'):
    assert load(label+'_exit.json')['exitCode']==0,label
assert session['dumpFiles']==[] and all(session[k]==0 for k in ('faultClears','clockChanges','powerOperations','hardKills'))
report=dict(passed=True,candidateChecks=31,baselineChecks=31,valueComparison=comparison,
    independentCanonicalReplays=2,independentCoherentRowReplays=replayed_rows,
    genericValues=generic['nodeCount'],genericModules=generic['moduleCount'],
    manifestMinor=7,readCoherenceBindings=generic['readCoherenceBindings'],
    qualityCounts=dict(quality),rejectedReasons=dict(Counter(r.get('reason') for r in probe['rows'] if r['quality']!='GOOD')),groups=groups,
    acceptedWindowUs=dict(median=statistics.median(windows),p95=percentile(windows,95),maximum=max(windows)),
    failedPayloadsSuppressed=True,proofScope=probe['scope'],
    candidateTiming=candidate_time,baselineTiming=baseline_time,finalChecks=final,
    genealogyRestored=True,originalHostDocumentsRestored=5,sessionApprovalConsumed=True,
    shippingClientAccepted=False,physicalAccepted=False)
with (D/'runtime_summary_01.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('groups','finalChecks','readCoherenceBindings','valueComparison')}))
