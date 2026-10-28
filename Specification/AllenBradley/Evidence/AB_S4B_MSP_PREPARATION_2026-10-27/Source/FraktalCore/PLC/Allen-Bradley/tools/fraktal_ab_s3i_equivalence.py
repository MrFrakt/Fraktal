"""S3i exact Line/shift reference with the finite approved correspondences."""
from functools import partial
import fraktal_ab_s3h_equivalence as previous
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3i_reference as reference
import fraktal_ab_line as line
import fraktal_ab_canonical_line as publication


def line_paths(app,*,canonical,count):
    if app.line is None:return set()
    if type(count) is not int or not 0<=count<=line.HISTORY:raise ValueError('invalid expected occupied shift count')
    fields=list(publication.LINE_FIELDS)
    if not canonical:fields=[{'Owner':'OwnerId','LastUpdate':'LastUpdatedAt'}.get(n,n) for n in fields]
    return {app.name+'/'+p for p in (
        *('Line/'+n for n in fields),*publication.ROOT_FIELDS,
        *(f'ShiftHistory[{i}]/'+n for i in range(1,count+1) for n in publication.HISTORY_FIELDS))}


def subset_paths(app,codes,*,canonical,count,shift_count,page=0,model=0):
    return previous.subset_paths(app,codes,canonical=canonical,count=count,page=page,model=model)|line_paths(app,canonical=canonical,count=shift_count)


def additional_inputs(reader,app):
    import fraktal_ab_press_execute as execute
    result=previous.additional_inputs(reader)
    if app.line is not None:
        result.update(line_state=execute.read_layout(reader,line.tag(app,'State'),line.state_members(app)),
            line_shift=execute.read_layout(reader,line.tag(app,'Shift'),line.shift_members()))
        if result['line_state'] is None or result['line_shift'] is None:raise ValueError('S3i Line owner read failed')
    return result


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    result=previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)
    if app.line is not None:
        result.update({app.name+'/'+p:v for p,v in reference.values(app,additional['line_state'],additional['line_shift']).items()})
    return result


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    for p in paths:
        leaf=p.rsplit('/',1)[-1]
        if p in (app.name+'/'+n for n in ('CurrentShift','ShiftHistoryCount')):result[p]='Int16'
        elif p in (app.name+'/'+n for n in ('Line/Revision','ShiftProductionTarget')):result[p]='UInt32'
        elif p in (app.name+'/'+n for n in ('Line/LastUpdatedAt','ShiftStartedAt','ShiftEndsAt')):result[p]='DateTime'
        elif p.startswith(app.name+'/ShiftHistory['):
            if leaf=='SchemaVersion':result[p]='UInt16'
            elif leaf=='ShiftIndex':result[p]='Int16'
            elif leaf in ('StartAt','EndAt'):result[p]='DateTime'
            elif leaf in ('GoodCount','NokCount','ReworkCount','ProductionTarget','RunMs','DownMs','IdleMs'):result[p]='UInt32'
            elif leaf in ('Availability','Performance','Quality','Oee'):result[p]='Float'
            elif leaf in ('TimeSynchronized','ManualReset','AvailValid','PerfValid','QualValid','OeeValid'):result[p]='Boolean'
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s3i_demo as candidate
    app=candidate.application();state={}
    def inputs(reader):
        result=additional_inputs(reader,app)
        state.update(count=result['host']['metadata']['Count'],shift_count=result['line_shift']['Count'] if app.line else 0)
        return result
    def paths(app,codes,*,canonical):
        return subset_paths(app,codes,canonical=canonical,**state,page=page,model=model)
    return shared.run(comm,application_factory=candidate.application,path_contract=paths,
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),
        logical_types=logical_types,additional_inputs=inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
