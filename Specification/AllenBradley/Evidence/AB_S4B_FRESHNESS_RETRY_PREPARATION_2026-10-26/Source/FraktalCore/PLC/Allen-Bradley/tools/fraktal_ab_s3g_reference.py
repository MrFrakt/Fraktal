"""Independent Core arithmetic oracle for the finite approved S3g amendment.

This test/engineering oracle reads the existing accounting owners, never the
canonical publication. The frozen legacy projection stays unchanged.
"""
import struct
import fraktal_ab_projection as legacy
import fraktal_ab_generate as gen


def real(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def unsigned(value):
    return value & 0xffffffff


def factors(run, down, good, nok, ideal):
    run, down, good, nok = map(unsigned, (run, down, good, nok))
    denominator = unsigned(run+down)
    total = unsigned(good+nok)
    av, pv, qv = denominator > 0, ideal > 0 and run > 0, total > 0
    availability = real(real(run)/real(denominator)) if av else 0.0
    performance = min(1.0, real(real(real(ideal)*real(total))/real(run))) if pv else 0.0
    quality = real(real(good)/real(total)) if qv else 0.0
    product = 1.0
    for valid, factor in ((av, availability), (pv, performance), (qv, quality)):
        if valid: product = real(product*factor)
    return dict(Availability=availability, AvailValid=av, Performance=performance,
        PerfValid=pv, Quality=quality, QualValid=qv,
        Oee=product if av or pv or qv else 0.0, OeeValid=av or pv or qv)


def oee_values(app, owner, unit, records):
    ideal = (records or {}).get(app.records[0].name, {}).get(app.ideal_cycle_member, 0) if app.ideal_cycle_member and app.records else 0
    run, down, idle = (unsigned(legacy._ms(owner, bucket)) for bucket in ('Run','Down','Idle'))
    result = {'Oee/RunMs':run, 'Oee/DownMs':down, 'Oee/IdleMs':idle, 'OeeTrendHead':owner['Head']}
    result.update({'Oee/'+key:value for key,value in factors(run,down,
        unit['GoodCount']-owner['GoodBase'],unit['ScrapCount']-owner['NokBase'],ideal).items()})
    for slot in range(gen.OEE_SAMPLES):
        current = owner['SmpEpoch'][slot] == owner['Epoch']
        row = factors(legacy._ms(owner,'Run',slot),legacy._ms(owner,'Down',slot),
            owner['SmpGood'][slot],owner['SmpNok'][slot],owner['SmpIdealMs'][slot]) if current else {}
        result[f'OeeTrend[{slot+1}]/Oee'] = row.get('Oee',0.0)
        result[f'OeeTrend[{slot+1}]/OeeValid'] = row.get('OeeValid',False)
    return result


def profiler_values(app, owner):
    result = legacy.profiler_status(app, owner)
    result['Profiler/LastCycle/CycleNo'] = unsigned(owner['LastCycleNo'])
    order = gen.ordered_steps(app)
    for slot in range(gen.PROFILE_STEPS):
        prefix = f'Profiler/StepStats[{slot+1}]/'
        visited = slot < len(order) and unsigned(owner['StatCount'][slot]) != 0
        step = legacy.step_by_number(app,order[slot]) if visited else None
        result.update({prefix+key:value for key,value in dict(Id=order[slot] if visited else 0,
            Label='project.step.'+step.name if step else '',
            TimeClass=legacy.decl.TIME_CLASSES.index(step.time_class) if step else 0,
            Count=unsigned(owner['StatCount'][slot]) if visited else 0,
            Avg=owner['StatAvg'][slot] if visited else 0, Maximum=owner['StatMax'][slot] if visited else 0).items()})
    for slot in range(gen.CYCLE_HISTORY):
        result[f'Profiler/History[{slot+1}]/CycleNo'] = unsigned(owner['HisCycleNo'][slot])
    return result


def health_values(app, owner, probe):
    result = legacy.system_health_status(app,owner,probe)
    for name in ('TaskCycleUs','TaskJitterUs','MemoryAvailableMb','LostFrameCount','SlaveErrorCount'):
        if 'SystemHealth/'+name in result: result['SystemHealth/'+name] = unsigned(result['SystemHealth/'+name])
    return result
