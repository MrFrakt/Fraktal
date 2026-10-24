"""S3e acceptance oracle; station knowledge stays outside the generic reader."""
import fraktal_ab_s3d_equivalence as previous
import fraktal_ab_s2_equivalence as shared


def subset_paths(app,codes,*,canonical):
    import fraktal_ab_access as access
    paths=previous.subset_paths(app,codes,canonical=canonical);base=app.name+'/Access/'
    paths.update(base+n for n in ('CurrentLevel','CurrentUser','LoginFailed','LoginBusy','LoginTimeoutMs','LoginPrehashRounds','LoginResultSequence','ClassCount','Policy/SessionTimeout'))
    paths.update(base+f'Policy/Required[{i}]' for i in range(0 if canonical else 1,access.GATE_COUNT+(0 if canonical else 1)))
    paths.update(base+f'Classes[{i}]/'+n for i in range(1,len(app.data_classes)+1) for n in ('ClassId','LabelKey','ReadLevel','WriteLevel'))
    return paths


def additional_inputs(reader):
    import fraktal_ab_projection as projection
    result=previous.additional_inputs(reader)
    additions=dict(accessState=projection.read_access(reader),accessAudit=projection.read_access(reader,audit=True),dataPolicy=projection.read_data_access(reader,policy=True))
    if any(v is None for v in additions.values()):raise ValueError('legacy access/audit/policy read failed')
    return dict(result,**additions)


def extra_values(app,unit,additional):
    import fraktal_ab_projection as projection
    import fraktal_ab_manifest as manifest
    import fraktal_ab_data_access as data
    import fraktal_ab_access as access
    rows=manifest.content(app)
    values=projection.access_status(app,level=access.ADMIN,held=additional['accessState'])
    values.update(data.policy_status(app,rows,additional['dataPolicy']))
    values.update(access.audit_status(app,rows,additional['accessAudit'],additional['alarmRing']))
    return {**previous.extra_values(app,unit,additional),**{app.name+'/'+p:v for p,v in values.items()}}


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    if app.name+'/Access/LoginResultSequence' in paths:result[app.name+'/Access/LoginResultSequence']='UInt32'
    return result


def run(comm):
    import fraktal_ab_genealogy_s3e_demo as candidate
    return shared.run(comm,application_factory=candidate.application,path_contract=subset_paths,
        extra_oracle=extra_values,logical_types=logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
