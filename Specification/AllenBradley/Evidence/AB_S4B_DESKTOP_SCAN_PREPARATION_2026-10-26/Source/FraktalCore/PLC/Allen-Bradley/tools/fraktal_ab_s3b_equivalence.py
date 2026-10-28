"""Explicit S3b migration contract. The canonical reader remains station-free."""
import fraktal_ab_s3a_equivalence as unit_core
import fraktal_ab_s2_equivalence as shared


def subset_paths(app,codes,*,canonical):
    import fraktal_ab_generate as gen
    paths=unit_core.subset_paths(app,codes,canonical=canonical)
    for module in (None,*app.modules):
        base=app.name+('/'+module.name if module else '')
        paths.update(base+'/Status/Diagnostic/'+leaf for leaf in
                     ('ReasonCode','Description','IoTag','IoAddress','Since','TimeSynchronized'))
        if module is not None and 'TimCount' in {m.name for m in gen.module_members(module)}:
            paths.update(base+f'/Timing/Rows[{i}]/'+leaf for i in range(1,gen.CMD_STATS+1)
                         for leaf in ('Id','Label','Count','Last','Minimum','Maximum','Avg'))
    return paths


def logical_types(app,paths):
    return {path:'DateTime' for path in paths if path.endswith('/Status/Diagnostic/Since')}


def run(comm):
    import fraktal_ab_genealogy_s3b_demo as candidate
    return shared.run(comm,application_factory=candidate.application,path_contract=subset_paths,
                      extra_oracle=unit_core.extra_values,logical_types=logical_types)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
