"""Two real root frames sharing a version3 calendar and production services."""
import argparse
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('line_owner_fixture',HERE.parent/'Line/make_owner_fixture.py')
OWNER=importlib.util.module_from_spec(spec);spec.loader.exec_module(OWNER)


def declaration(calendar=True):
    value=OWNER.declaration()
    value['config_sets']=dict(capacity=4)
    line=value.pop('line')
    value['records'].pop(line['record'])
    unit=next(t for t in value['types'] if 'unit' in t)
    unit['sequence_view']=dict(capacity=8,branches=0,annotations=4)
    unit['health']={}
    unit['signal_tower']={}
    value['engineering_gates']=[dict(name='USE_SIMULATION',description='std.engineering.simulation',active=True)]
    value['nameplates']={'StationA':dict(ProductUri='urn:fraktal:tia:operations:station-a',ManufacturerName='Fraktal',ProductDesignation='Isolated operations fixture')}
    unit['production']=dict(ideal_cycle='ParCfg.IdealCycleMs',baseline='ParCfg.BaselineMs',degradation_percent='StationCfg.DegradationPercent')
    cfg=unit['contract']['ParCfg'];station=unit['station_config']
    unit['contract']['ParCfg']='ST_ProductionUnitParCfg'
    value['records']['ST_ProductionUnitParCfg']=value['records'][cfg].replace('END_STRUCT','IdealCycleMs : UDINT := 1000; BaselineMs : UDINT := 1000; END_STRUCT')
    value['records'][station]=value['records'][station].replace('SchemaVersion : UINT := 3','SchemaVersion : UINT := 5').replace('END_STRUCT','DegradationPercent : UINT := 10; CapturedCycles : UDINT; END_STRUCT')
    unit['config']=[f for f in unit['config'] if not f['member'].startswith('StationCfg.Offsets[') and f['member']!='StationCfg.Small']
    unit['config'] += [dict(member=member,key=key,revision=1,label='test.config.preset') for member,key in (
        ('ParCfg.IdealCycleMs','idealCycleMs'),('ParCfg.BaselineMs','baselineMs'),('StationCfg.DegradationPercent','degradationPercent'))]
    unit['config'].append(dict(member='StationCfg.CapturedCycles',key='capturedCycles',revision=1,label='test.config.preset',minimum=0,maximum=10,capture='OutImm.Cycles'))
    if calendar:
        from fraktal_tia_binding import Catalog
        count=Catalog.read().capacities['MAX_WEEKLY_SHIFTS']
        original=OWNER.declaration()['records'][line['record']]
        line['record']='ST_LineProductionConfig'
        line['shifts']=dict(utc_offset='UtcOffsetMin',start_min='ShiftStartMin',duration_min='ShiftDurationMin',active_days='ShiftActiveDays',target='ShiftTarget')
        fields='UtcOffsetMin : DINT; '+' '.join('%s : ARRAY[1..%d] OF DINT;'%(line['shifts'][k],count) for k in ('start_min','duration_min','active_days','target'))
        value['records'][line['record']]=original.replace('SchemaVersion : UINT := 1','SchemaVersion : UINT := 2').replace('END_STRUCT',fields+' END_STRUCT')
        line['values'].append(dict(member='Line.UtcOffsetMin',key='line.shift.utcOffsetMin',revision=1,label='test.config.preset',minimum=-840,maximum=840))
        for row in range(1,count+1):
            for kind,key,minimum,maximum in [('start_min','startMin',-1,1439),('duration_min','durationMin',1,1440),('active_days','activeDays',0,127),('target','target',0,2147483647)]:
                line['values'].append(dict(member='Line.%s[%d]'%(line['shifts'][kind],row),key='line.shift.%d.%s'%(row,key),revision=1,label='test.config.preset',minimum=minimum,maximum=maximum))
        value['line']=line
    return value


def prepare(out,frames):
    OWNER.CONFIG.PERSIST.RECOVERY.prepare(out,frames,declaration())
    OWNER.CONFIG.PERSIST.add_controls(out,frames)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('out',type=Path);parser.add_argument('frames',type=Path)
    args=parser.parse_args();prepare(args.out,args.frames)
