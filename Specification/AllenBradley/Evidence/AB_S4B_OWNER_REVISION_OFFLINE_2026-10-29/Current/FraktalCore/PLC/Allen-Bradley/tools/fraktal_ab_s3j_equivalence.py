"""S3j paired comparison: inherited surfaces plus the declared fieldbus product."""
from functools import partial
import fraktal_ab_s3i_equivalence as previous
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_s3j_reference as reference
import fraktal_ab_canonical_fieldbus as fieldbus


def additional_inputs(reader,app):
    import fraktal_ab_press_execute as execute
    import fraktal_ab_declaration as declaration
    result=previous.additional_inputs(reader,app);samples=[]
    layout=tuple(declaration.Member(name,'DINT') for name in fieldbus.SAMPLE_FIELDS)
    for module in app.io_modules:
        sample=execute.read_layout(reader,module.sample_tag,layout) if module.sample_tag else {n:0 for n in fieldbus.SAMPLE_FIELDS}
        if sample is None:raise ValueError('S3j sampled-word source unavailable')
        samples.append(sample)
    result['io_samples']=samples
    return result


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    result=previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)
    result.update(reference.values(app,additional['io_samples']))
    return result


def subset_paths(app,codes,*,canonical,count,shift_count,page=0,model=0):
    empty=[{n:0 for n in fieldbus.SAMPLE_FIELDS} for m in app.io_modules]
    return previous.subset_paths(app,codes,canonical=canonical,count=count,shift_count=shift_count,page=page,model=model)|set(reference.values(app,empty))


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    result.update(reference.logical_types(p for p in paths if p.startswith(fieldbus.canonical_root(app)+'/')))
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s3j_demo as candidate
    app=candidate.application();state={}
    def inputs(reader):
        result=additional_inputs(reader,app)
        state.update(count=result['host']['metadata']['Count'],shift_count=result['line_shift']['Count'] if app.line else 0)
        return result
    def paths(app,codes,*,canonical):return subset_paths(app,codes,canonical=canonical,**state,page=page,model=model)
    return shared.run(comm,application_factory=candidate.application,path_contract=paths,
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),logical_types=logical_types,additional_inputs=inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
