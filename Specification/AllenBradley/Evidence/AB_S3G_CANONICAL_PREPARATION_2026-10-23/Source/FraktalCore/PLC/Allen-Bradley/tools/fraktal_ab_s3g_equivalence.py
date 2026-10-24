"""S3g path-by-path reference, with only the 200+224 approved corrections."""
from functools import partial
import fraktal_ab_s3f_equivalence as previous
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3g_reference as reference
import fraktal_ab_generate as gen
import fraktal_ab_declaration as decl


def metric_paths(app):
    root=app.name+'/'
    paths={root+'Oee/'+n for n in ('RunMs','DownMs','IdleMs','Availability','AvailValid','Performance','PerfValid','Quality','QualValid','Oee','OeeValid')}
    paths.add(root+'OeeTrendHead')
    paths.update(root+f'OeeTrend[{i}]/'+n for i in range(1,gen.OEE_SAMPLES+1) for n in ('Oee','OeeValid'))
    prefix=root+'Profiler/'
    paths.update(prefix+'LastCycle/'+n for n in ('CycleNo','NSteps','Total','WorkTime','WaitTime'))
    paths.update(prefix+f'LastCycle/Steps[{i}]/'+n for i in range(1,gen.PROFILE_STEPS+1) for n in ('StepNo','StepName','TimeClass','Duration','Expected'))
    paths.update(prefix+f'StepStats[{i}]/'+n for i in range(1,gen.PROFILE_STEPS+1) for n in ('Id','Label','TimeClass','Count','Avg','Maximum'))
    paths.update(prefix+n for n in ('LastCycleTime','MinCycleTime','HistoryHead'))
    paths.update(prefix+f'History[{i}]/'+n for i in range(1,gen.CYCLE_HISTORY+1) for n in ('CycleNo','Total','WorkTime','WaitTime',*(f'ByClass[{k}]' for k in range(len(decl.TIME_CLASSES)))))
    if app.system_health is not None:
        paths.update(root+'SystemHealth/'+n for n in ('Present','Healthy','TaskAvailable','TaskCycleUs','TaskJitterUs','TaskOverrun','ControllerAvailable','CpuLoadPct','MemoryAvailableMb','IpcAvailable','IpcTemperatureC','FanHealthy','StorageHealthPct','FieldbusAvailable','FieldbusMasterHealthy','LostFrameCount','SlaveErrorCount','DcAvailable','DcSynchronized','TimeQuality/Available','TimeQuality/Synchronized','TimeQuality/Source','TimeQuality/OffsetUs'))
    return paths


def subset_paths(app,codes,*,canonical,page=0,model=0):
    return previous.subset_paths(app,codes,canonical=canonical,page=page,model=model)|metric_paths(app)


def additional_inputs(reader):
    import fraktal_ab_projection as projection
    result=previous.additional_inputs(reader)
    health,probe=projection.read_system_health(reader)
    result.update(oee=projection.read_oee(reader),profiler=projection.read_profiler(reader),health=health,healthProbe=probe)
    if any(result[n] is None for n in ('oee','profiler','health','healthProbe')):
        raise ValueError('S3g metric owner read failed')
    return result


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    result=previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)
    values=reference.oee_values(app,additional['oee'],unit,additional['records'])
    values.update(reference.profiler_values(app,additional['profiler']))
    values.update(reference.health_values(app,additional['health'],additional['healthProbe']))
    result.update({app.name+'/'+p:v for p,v in values.items()})
    return result


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    for p in metric_paths(app)&paths:
        leaf=p.rsplit('/',1)[-1]
        if '/Oee/' in p or '/OeeTrend[' in p:
            if leaf in ('RunMs','DownMs','IdleMs'):result[p]='UInt32'
            elif leaf in ('Availability','Performance','Quality','Oee'):result[p]='Float'
        elif '/Profiler/' in p:
            if leaf in ('CycleNo','Count'):result[p]='UInt32'
            elif leaf in ('NSteps','StepNo','HistoryHead'):result[p]='Int16'
        elif '/SystemHealth/' in p:
            if leaf in ('TaskCycleUs','TaskJitterUs','MemoryAvailableMb','LostFrameCount','SlaveErrorCount'):result[p]='UInt32'
            elif leaf in ('CpuLoadPct','IpcTemperatureC','StorageHealthPct'):result[p]='Double'
        elif leaf=='OeeTrendHead':result[p]='Int16'
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s3g_demo as candidate
    return shared.run(comm,application_factory=candidate.application,
        path_contract=partial(subset_paths,page=page,model=model),
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),
        logical_types=logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
