"""Read-only S3a gate: explicit Unit-core paths, with the unchanged paired-state proof."""
import fraktal_ab_declaration as decl
import fraktal_ab_s2_equivalence as shared


def subset_paths(app, codes, *, canonical):
    paths=shared.subset_paths(app)
    root=app.name+'/'
    paths.add(root+'Decision/Default')
    if app.decisions:
        paths.add(root+'Decision/Prompt')
        paths.update(root+f'Decision/Options[{i}]' for i in range(1,max(len(d.option_keys) for d in app.decisions)+1))
    shift=0 if canonical else 1
    for ordinal in decl.declared_modes(app):
        paths.add(root+f'SupportedModesPublished[{ordinal+shift}]')
        paths.update(root+f'ModePolicy[{ordinal+shift}]/'+leaf for leaf in ('Shield','Style'))
    paths.update(root+f'SupportedRunStylesPublished[{ordinal+shift}]' for ordinal in decl.RUN_STYLES)
    if app.models:
        paths.update((root+'AvailableModelCount',root+'ModelCapacity'))
        paths.update(root+f'AvailableModels[{i}]/ModelCode' for i in range(1,len(codes)+1))
    for module in app.modules:
        base=root+module.name+'/'
        paths.add(base+'CatalogCount')
        for i in range(1,len(module.commands)+1):
            paths.update(base+f'Catalog[{i}]/'+leaf for leaf in ('Value','Label','Style'))
    return paths


def extra_values(app, unit):
    import fraktal_ab_projection as projection
    return {app.name+'/'+p:v for service in (projection.mode_policy(app),projection.decision_status(app,unit))
            for p,v in service.items()}


def run(comm):
    import fraktal_ab_genealogy_s3a_demo as candidate
    return shared.run(comm,application_factory=candidate.application,
                      path_contract=subset_paths,extra_oracle=extra_values)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
