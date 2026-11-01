"""Evaluate every native read gate; retain independent failures before rollback."""
from pathlib import Path
import datetime,gzip,json,sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
from fraktal_ab_canonical_equivalence import compare_documents
from fraktal_ab_canonical_reader import snapshot
D=Path(__file__).parent
def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def stamp(text):return datetime.datetime.fromisoformat(text.replace('Z','+00:00'))

def evaluate(directory):
    gates={}
    def check(name,action):
        try:gates[name]=dict(passed=True,**action())
        except Exception as error:gates[name]=dict(passed=False,error=f'{type(error).__name__}: {error}')
    def configuration():
        value=load(directory/'configuration_page_comparison_01.json')
        assert value['passed'] and value['pages']==4 and value['scalarComparisons']==1100
        return dict(pages=4,scalars=1100)
    def idle():
        value=load(directory/'idle_equivalence.json.gz')
        pair=value['pair']
        assert value['passed'] and pair['canonical']['values']
        report=compare_documents(pair['projection'],pair['canonical'])
        assert report['equal'] and report['typeAcceptance'],report
        return dict(paths=len(pair['canonical']['values']),independentComparison=True)
    def generic():
        value=load(directory/'generic_snapshot.json.gz')
        assert value['values'] and value['moduleCount']==7 and value['truncated'] is False
        assert value['nodeCount']==len(value['values']) and value['values'].keys()==value['types'].keys()
        replay=snapshot(load(directory/'generic_capture.json.gz'))
        assert value['values']==replay['values'] and value['types']==replay['types']
        assert value['contentHash']==replay['contentHash'] and value['configRevision']==replay['configRevision']
        return dict(values=len(value['values']),modules=7,rawCaptureReplay=True)
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
    def gateway():
        value=load(directory/'gateway_profile_result.json')
        assert value['passed'] and value['credentialValuesRecorded'] is False
        assert [r['case'] for r in value['cases']]==[*(f'C{i}' for i in range(1,12)),'C13']
        assert all(r['passed'] for r in value['cases'])
        comparison=load(directory/'gateway_configuration_comparison.json')
        assert comparison['passed'] and comparison['scalarComparisons']==1100
        return dict(automatedCases=12,ownerBrowserC12Pending=True)
    def simulation():
        before=load(directory/'simulation_original.json');after=load(directory/'simulation_restored.json')
        assert before['serial']==after['serial']=='601FC87B'
        assert before['tag']==after['tag']=='FRK_Press_AirOk' and before['temporary']==1
        assert after['passed'] and before['original']==after['original']==after['restored']
        return dict(exactRestoration=True,tag=before['tag'])
    for name,action in [('C1_C11_C13',gateway),('simulation_setup_restore',simulation),('configuration_readback',configuration),
                        ('idle_equivalence',idle),('generic_acquisition',generic),('native_scan',timing)]:check(name,action)
    return dict(passed=all(v['passed'] for v in gates.values()),readOnly=True,gates=gates,
                rollbackGate='E9 evaluated separately after guarded restore')
def main():
    result=evaluate(D)
    with (D/'native_read_gates_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
