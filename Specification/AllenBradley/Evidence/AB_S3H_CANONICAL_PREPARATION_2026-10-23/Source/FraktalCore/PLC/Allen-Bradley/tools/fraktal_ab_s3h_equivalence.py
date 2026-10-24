"""S3h exact traceability reference with the finite owner-approved amendment."""
from functools import partial
import fraktal_ab_s3g_equivalence as previous
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3h_reference as reference
import fraktal_ab_genealogy as genealogy
import fraktal_ab_host_events as host
import fraktal_ab_part as part
import fraktal_ab_nameplate as nameplate
import fraktal_ab_signal_tower as tower


def trace_paths(app,*,count):
    root=app.name+'/';paths={root+'MachineState'}
    for owner in (app,*app.modules):
        if owner.nameplate is not None:
            paths.update(root+('' if owner is app else owner.name+'/')+'Nameplate/'+leaf for _,_,leaf in nameplate.FIELDS)
    if app.signal_tower is not None:paths.update(root+'SignalTower/'+n for n in tower.OUTPUTS)
    parents=genealogy.capacity(app)
    if app.part_carrier is not None:
        paths.update(root+'Part/'+n for n in ('Uid','Present','CarrierKind','Result/Verdict','Result/ReasonCode','Result/StationPath','Result/Stamp','Result/TimeSynchronized'))
        paths.update(root+f'Part/Result/Records[{i}]/'+n for i in range(1,app.part_carrier.result_capacity+1) for n in ('Name','Value','Minimum','Maximum','Target','Unit','InTol'))
        if parents:
            paths.update(root+'Part/'+n for n in ('ParentCapacity','ParentCount',*(f'Parents[{i}]' for i in range(1,parents+1))))
    if app.host_event_capacity:
        if type(count) is not int or not 0<=count<=app.host_event_capacity:raise ValueError('invalid expected occupied ring count')
        paths.update(root+'HostEvents/'+n for n in (*host.META,'RingHead'))
        if parents:paths.add(root+'HostEvents/GenealogyCapacity')
        paths.update(root+f'HostEvents/Ring[{i}]/'+n for i in range(1,count+1) for n in
            ('Sequence','Kind','StationPath','PartUid','Subject','Value','Stamp','TimeSynchronized','Verdict','ReasonCode',
             *(('ParentCount',*(f'Parents[{k}]' for k in range(1,parents+1))) if parents else ())))
    return paths


def subset_paths(app,codes,*,canonical,page=0,model=0):
    # Occupancy is a PLC fact. Expected rows are separately reconstructed from
    # the bracketed legacy owner in extra_values, and missing/excess rows fail.
    count=canonical['values'][app.name+'/HostEvents/Count'] if app.host_event_capacity else 0
    return previous.subset_paths(app,codes,canonical=canonical,page=page,model=model)|trace_paths(app,count=count)


def additional_inputs(reader):
    import fraktal_ab_projection as projection
    import fraktal_ab_press_execute as execute
    import fraktal_ab_models as models
    result=previous.additional_inputs(reader);app=projection.APP
    result.update(part=part.read(reader,app),host=host.read(reader,app,models.read(reader,app)),
        tower=execute.read_layout(reader,tower.tag(app),tower.members()))
    if result['tower'] is None:raise ValueError('S3h signal tower owner read failed')
    return result


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    result=previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)
    extra=reference.values(app,additional['part'],additional['host'],additional['tower'])
    result.update({app.name+'/'+p:v for p,v in extra.items()})
    return result


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    for p in paths:
        leaf=p.rsplit('/',1)[-1]
        if '/Part/Result/Records[' in p and leaf in ('Value','Minimum','Maximum','Target'):result[p]='Double'
        elif '/HostEvents/Ring[' in p and leaf=='Sequence':result[p]='UInt32'
        elif p in (app.name+'/HostEvents/'+n for n in ('Count','Capacity','RingHead')):result[p]='Int16'
        elif (p.startswith(app.name+'/Part/') or p.startswith(app.name+'/HostEvents/Ring[')) and leaf=='Stamp':result[p]='DateTime'
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s3h_demo as candidate
    return shared.run(comm,application_factory=candidate.application,
        path_contract=partial(subset_paths,page=page,model=model),
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),
        logical_types=logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
