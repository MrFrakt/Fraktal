"""Evaluate every native read gate; retain independent failures before rollback."""
from pathlib import Path
import datetime,gzip,json
D=Path(__file__).parent
def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def stamp(text):return datetime.datetime.fromisoformat(text.replace('Z','+00:00'))

def evaluate(directory):
    gates={}
    def check(name,action):
        try:gates[name]=dict(passed=True,**action())
        except Exception as error:gates[name]=dict(passed=False,error=f'{type(error).__name__}: {error}')
    def fixture():
        value=load(directory/'paired_replay_01.json')
        assert value['passed'] and value['pairs']==87
        assert value['caseCounts']==dict(rows=31,s4bAccessRows=2,s4bConfigRows=8)
        return dict(cases=41,pairs=87)
    def configuration():
        value=load(directory/'configuration_page_comparison_01.json')
        assert value['passed'] and value['pages']==4 and value['scalarComparisons']==1100
        return dict(pages=4,scalars=1100)
    def idle():
        value=load(directory/'idle_equivalence.json.gz')
        assert value['passed'] and len(value['pair']['canonical']['values'])==5407
        return dict(paths=5407)
    def generic():
        value=load(directory/'generic_snapshot.json.gz')
        assert len(value['values'])==5407 and value['moduleCount']==7
        return dict(values=5407,modules=7)
    def desktop():
        from desktop_coverage import validate_coverage
        value=load(directory/'desktop_profile/result.json')
        validate_coverage(value,load(directory/'desktop_expected_inventory.json'),require_live=True)
        assert value['desktopLiveAccepted'] and value['nativeFreshnessClaim'] and not value['rehearsal']
        return dict(views=31,modules=7,fieldbusNodes=3)
    def observer():
        value=load(directory/'dart_qualification.json.gz')
        assert value['passed'] and value['readOnly'] and value['writes']==0
        assert value['samples'] and all(row['bad']==0 for row in value['samples'])
        return dict(samples=len(value['samples']),bad=0,writes=0)
    def timing():
        marker=load(directory/'candidate_run_requested.json')
        assert marker['Serial']=='601FC87B' and marker['ReadOnlyMarker']
        start=stamp(marker['Utc'])
        trace=load(directory/'task_monitor.json.gz')
        assert trace['passed'] and trace['readOnly'] and trace['writes']==trace['counterOrFaultClears']==0
        candidates=[r for r in trace['rows'] if r['available'] and stamp(r['utc'])>=start]
        assert len(candidates)>=20,'insufficient post-download TASK observations'
        final=load(directory/'candidate_timing.json')
        assert final['readOnly'] and final['candidate'] and final['serial']=='601FC87B'
        assert final['unit']=='microseconds' and len(final['samples'])==20 and stamp(final['capturedUtc'])>=start
        values=[r['values'] for r in candidates]+[r['values'] for r in final['samples']]
        prefix='FRK_Press_HealthProbe.'
        assert all(type(v[prefix+k]) is int and v[prefix+k]>=0 for v in values
                   for k in ['Samples','TaskMaxScanUs','TaskOverlapCount'])
        assert values[-1][prefix+'Samples']>values[0][prefix+'Samples'],'TASK did not scan'
        maximum=max(v[prefix+'TaskMaxScanUs'] for v in values)
        overlaps=max(v[prefix+'TaskOverlapCount'] for v in values)
        assert maximum<10000 and overlaps==0,(maximum,overlaps)
        return dict(monitorSamples=len(candidates),finalSamples=20,cumulativeMaxUs=maximum,overlaps=overlaps)
    for name,action in [('E1_E2',fixture),('E3',observer),('E4',configuration),('E5',idle),
                        ('E6',generic),('E7',desktop),('E8',timing)]:check(name,action)
    return dict(passed=all(v['passed'] for v in gates.values()),readOnly=True,gates=gates,
                rollbackGate='E9 evaluated separately after guarded restore')
def main():
    result=evaluate(D)
    with (D/'native_read_gates_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
