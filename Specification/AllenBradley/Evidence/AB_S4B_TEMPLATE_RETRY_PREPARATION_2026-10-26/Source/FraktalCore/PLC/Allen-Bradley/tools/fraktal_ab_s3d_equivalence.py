"""Explicit S3d migration oracle; the discovery reader stays station-free."""
import fraktal_ab_s3c_equivalence as previous
import fraktal_ab_s3b_equivalence as status
import fraktal_ab_s2_equivalence as shared


def subset_paths(app,codes,*,canonical):
    import fraktal_ab_generate as gen
    from fraktal_ab_canonical_alarms import metadata
    paths=previous.subset_paths(app,codes,canonical=canonical);root=app.name+'/'
    paths.update(root+'AlarmLog/'+name for name in ('RingHead','Blocking','MetaCount'))
    event=('State','ReasonCode','Description','Severity','ResetClass','SourcePath','ComeAt','GoneAt',
           'Duration','Shelved','IoTag','IoAddress','ComeTimeSynchronized','GoneTimeSynchronized',
           'ResetTimeSynchronized','ShelfTimeSynchronized')
    for surface,count in (('Active',gen.ALARM_ACTIVE),('Ring',gen.ALARM_RING)):
        paths.update(root+f'AlarmLog/{surface}[{i}]/'+name for i in range(1,count+1) for name in event)
    paths.update(root+f'AlarmLog/Meta[{i}]/'+name for i in range(1,len(metadata(app))+1) for name in
                 ('ReasonCode','OperatorAction','Consequence','Priority','Category','Shelvable'))
    if app.state_flags:
        paths.add(root+'StateFlagCount')
        paths.update(root+f'StateFlags[{i}]/'+name for i in range(1,len(app.state_flags)+1) for name in ('Key','Value','Since','Stale'))
    return paths


def additional_inputs(reader):
    import fraktal_ab_projection as projection
    result=previous.additional_inputs(reader)
    active,ring=projection.read_alarm_log(reader);flags=projection.read_state_flags(reader)
    if active is None or ring is None:raise ValueError('legacy alarm read failed')
    if projection.APP.state_flags and flags is None:raise ValueError('legacy state flags read failed')
    return dict(result,alarmActive=active,alarmRing=ring,stateFlags=flags)


def extra_values(app,unit,additional):
    import fraktal_ab_projection as projection
    import fraktal_ab_manifest as manifest
    values=projection.alarm_log_status(app,additional['alarmActive'],additional['alarmRing'])
    values.update(projection.alarm_meta_status(manifest.content(app)))
    values.update(projection.state_flags_status(app,additional['stateFlags']))
    return {**previous.extra_values(app,unit,additional),**{app.name+'/'+p:v for p,v in values.items()}}


def logical_types(app,paths):
    result=status.logical_types(app,paths)
    result.update({p:'DateTime' for p in paths if
        ('/AlarmLog/' in p and p.endswith(('/ComeAt','/GoneAt'))) or ('/StateFlags[' in p and p.endswith('/Since'))})
    return result


def run(comm):
    import fraktal_ab_genealogy_s3d_demo as candidate
    return shared.run(comm,application_factory=candidate.application,path_contract=subset_paths,
        extra_oracle=extra_values,logical_types=logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
