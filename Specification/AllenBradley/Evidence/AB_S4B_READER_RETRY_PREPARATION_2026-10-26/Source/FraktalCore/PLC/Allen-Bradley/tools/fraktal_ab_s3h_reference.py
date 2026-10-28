"""Independent S3h oracle: legacy owners plus only the 36 approved types.

Station declaration and legacy projection knowledge belong to this acceptance
reference. No canonical value is used to construct an expected value.
"""
import fraktal_ab_host_events as host
import fraktal_ab_part as part
import fraktal_ab_nameplate as nameplate
import fraktal_ab_manifest as manifest
import fraktal_ab_signal_tower as tower


def values(app,raw_part,batch,raw_tower):
    result=part.project(app,raw_part) if app.part_carrier is not None else {}
    if result.get('Part/Result/Stamp')=='':result['Part/Result/Stamp']=0
    if app.host_event_capacity:result.update(host.project(batch))
    rows=manifest.content(app)
    for index,owner in enumerate((app,*app.modules),1):
        prefix='' if owner is app else owner.name+'/'
        result.update({prefix+p:v for p,v in nameplate.project(rows,index).items()})
    if app.signal_tower is not None:result.update(tower.project(raw_tower))
    return result
