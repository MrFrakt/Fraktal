"""Explicit S3c migration oracle; the discovery reader stays station-free."""
import fraktal_ab_s3b_equivalence as previous
import fraktal_ab_s3a_equivalence as unit_core
import fraktal_ab_s2_equivalence as shared


def subset_paths(app,codes,*,canonical):
    import fraktal_ab_projection as projection
    paths=previous.subset_paths(app,codes,canonical=canonical)
    root=app.name+'/'
    paths.update(root+name for name in ('SequenceViewEnabled','SequenceStepCount','SequenceAnnotationCount'))
    for index in range(1,projection.sequence_slots(app)+1):
        paths.update(root+f'SequenceSteps[{index}]/'+name for name in (
            'StepNo','Branch','StepName','AwaitingLabel','AwaitsPath','TimeClass','ExpectedTime',
            'Visited','LastDuration','ErrorActive','WarningActive'))
        paths.update(root+f'SequenceAnnotations[{index}]/'+name for name in ('RowIdx','IsError','Key','SourcePath'))
    paths.update(root+f'ActiveSteps[{0 if canonical else 1}]/'+name for name in ('RowIdx','Elapsed','TimedOut'))
    paths.update(root+name for name in ('CurrentStepElapsed','CurrentStepTimedOut','CurrentStep/StepName',
        'CurrentStep/AwaitingLabel','CurrentStep/ExpectedTime','CurrentStep/TimeClass'))
    import fraktal_ab_declaration as decl
    paths.update(root+f'CurrentStep/Conds[{i}]/'+name for i in range(1,decl.MAX_STEP_CONDS+1) for name in ('Label','Ok'))
    return paths


def additional_inputs(reader):
    import fraktal_ab_press_execute as execute
    import fraktal_ab_projection as projection
    chart=execute.read_chart(reader)
    if chart is None:raise ValueError('legacy sequence chart read failed')
    records=projection.read_records(reader)
    if not records or any(v is None for v in records.values()):raise ValueError('legacy recipe read failed')
    return dict(chart=chart,records=records)


def extra_values(app,unit,additional):
    import fraktal_ab_projection as projection
    values=projection.sequence_status(app,unit,additional['chart'],additional['records'])
    values.update({p:v for p,v in projection.step_status(app,unit,additional['chart']).items() if p.startswith('CurrentStep/')})
    values.update(CurrentStepElapsed=additional['chart']['CurrentStepMs'],CurrentStepTimedOut=bool(unit.get('StepTimedOut')))
    return {**unit_core.extra_values(app,unit),**{app.name+'/'+path:value for path,value in values.items()}}


def run(comm):
    import fraktal_ab_genealogy_s3c_demo as candidate
    return shared.run(comm,application_factory=candidate.application,path_contract=subset_paths,
        extra_oracle=extra_values,logical_types=previous.logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
