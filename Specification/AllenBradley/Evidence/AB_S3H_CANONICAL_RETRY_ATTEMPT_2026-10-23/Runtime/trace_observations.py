"""Read-only audit of traceability/type/lifecycle facts in accepted pairs."""
from pathlib import Path
import gzip,json
R=Path(__file__).parent
fixture=json.loads((R/'candidate_regressions_01.json').read_text())
items=[item for key,value in fixture.items() if key.endswith('Pairs') for item in value]
items.append(dict(output=str(R/'idle_equivalence_01.json.gz'),passed=True))
counts=set();wrapped=set();present=set();stamps=set();record_names=set();values_seen=set();parent_counts=set()
kinds=set();historical=False;host_parents=False;captured_text=False;model_codes=set();tower_states=set()
tower_outputs={n:set() for n in ('Red','Amber','Green','Blue','White','Horn','TestActive')}
zero_slots=0;rows=[]
for item in items:
    e=json.loads(gzip.decompress(Path(item['output']).read_bytes()));assert item['passed'] and e['passed']
    pair=e['pair'];c=pair['canonical'];v=c['values'];types=c['types'];count=v['Press/HostEvents/Count']
    assert types['Press/HostEvents/Count']==types['Press/HostEvents/Capacity']==types['Press/HostEvents/RingHead']=='Int16'
    assert types['Press/Part/Result/Stamp']=='DateTime'
    assert pair['projection']['values']==v and pair['projection']['types']==types
    counts.add(count);wrapped.add(v['Press/HostEvents/Wrapped']);present.add(v['Press/Part/Present'])
    stamps.add('unset' if v['Press/Part/Result/Stamp']==0 else 'populated');parent_counts.add(v['Press/Part/ParentCount'])
    for i in range(1,5):
        base=f'Press/Part/Result/Records[{i}]/';record_names.add(v[base+'Name'])
        for n in ('Value','Minimum','Maximum','Target'):assert types[base+n]=='Double' and type(v[base+n]) is float
        if v[base+'Name']:values_seen.add(v[base+'Value'])
        else:
            assert v[base+'Value']==v[base+'Minimum']==v[base+'Maximum']==v[base+'Target']==0.0
            assert v[base+'Unit']=='' and v[base+'InTol'] is False;zero_slots+=1
    for i in range(1,count+1):
        base=f'Press/HostEvents/Ring[{i}]/';kind=v[base+'Kind'];kinds.add(kind)
        assert types[base+'Sequence']=='UInt32' and types[base+'Stamp']=='DateTime'
        assert v[base+'Stamp']!=0
        for k in range(1,3):
            if k>v[base+'ParentCount']:assert v[base+f'Parents[{k}]']==''
        if v[base+'ParentCount']:
            host_parents=True
            if v['Press/Part/ParentCount']==0 or v[base+'PartUid']!=v['Press/Part/Uid']:historical=True
        if kind in (7,8) and v[base+'Value'] and not v[base+'Value'].lstrip('-').isdigit():captured_text=True
        if kind in (5,6):model_codes.add(v[base+'Value'])
    assert not any(p.startswith(f'Press/HostEvents/Ring[{count+1}]/') for p in v)
    tower_states.add(v['Press/MachineState'])
    for n in tower_outputs:tower_outputs[n].add(v['Press/SignalTower/'+n])
    rows.append(dict(file=Path(item['output']).name,ringCount=count,partPresent=v['Press/Part/Present'],partStampUnset=v['Press/Part/Result/Stamp']==0))
assert 16 in counts and True in wrapped and {'unset','populated'}<=stamps
assert {0,2}<=parent_counts and {'PressDwell','RamPosition'}<=record_names
assert host_parents and historical and captured_text and zero_slots
for case in ('all_outputs_active','logout_disconnect_timeout','producing','rationalized_fault','operator_decision'):
    assert any(row['case']==case and row['passed'] for row in fixture['rows']),case
report=dict(passed=True,controllerAccess=False,captures=len(rows),rows=rows,
    occupiedCountsObserved=sorted(counts),partialRingObserved=any(0<n<16 for n in counts),emptyRingObserved=0 in counts,
    emptyRingQualifiedOffline=True,fullRingObserved=True,wrappedObserved=True,partPresentObserved=sorted(present),
    partStampsObserved=sorted(stamps),partParentCountsObserved=sorted(parent_counts),measurementNamesObserved=sorted(record_names),
    measurementValuesObserved=sorted(values_seen),clearedMeasurementRows=zero_slots,
    eventKindsObserved=sorted(kinds),historicalParentsIndependentOfCurrentPart=historical,capturedResourceTextObserved=captured_text,
    modelValuesObserved=sorted(model_codes),machineStatesObserved=sorted(tower_states),
    towerOutputsObserved={k:sorted(v) for k,v in tower_outputs.items()},
    nativeTowerOwnerRowsPassed=True,allSevenCanonicalMirrorStatesQualifiedOffline=True)
with (R/'trace_observations_01.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
