"""Independent engineering oracle for the approved Line/shift correspondence.

Only legacy owner records and the declared localization table supply values.
The published canonical tree never supplies occupancy or expected arithmetic.
"""
from datetime import datetime, timedelta, timezone
import fraktal_ab_line as line
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as legacy
import fraktal_ab_s3g_reference as arithmetic


def stamp(minute,millis=0):
    if minute<0 or not 0<=millis<=59999 or minute*60_000_000_000+millis*1_000_000>2**63-1:
        raise ValueError('shift timestamp outside native LDT range')
    if not minute:return 0
    return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(minutes=minute,milliseconds=millis)).isoformat(timespec='milliseconds').replace('+00:00','Z')


def values(app,state,shifts):
    if app.line is None:return {}
    if state.get('SchemaVersion')!=2 or shifts.get('SchemaVersion')!=line.SHIFT_SCHEMA:
        raise ValueError('S3i oracle owner schema mismatch')
    count=shifts['Count']
    if not 0<=count<=line.HISTORY:raise ValueError('S3i history count outside declared capacity')
    keys={r['NumericKey']:r['PortableKey'] for r in manifest.content(app)['Localization']}
    result={'Line/Role':0,'Line/LineId':keys[state['LineIdKey']],'Line/OwnerId':keys[state['OwnerIdKey']],
        'Line/Revision':arithmetic.unsigned(state['Revision']),'Line/Stale':False,'Line/SourceError':state['SourceError'],
        'Line/TimeSynchronized':bool(state['TimeSynchronized']),
        'Line/LastUpdatedAt':legacy._controller_time(state['UpdatedDate'],state['UpdatedClock']) or 0,
        'Line/AppliedRevision':shifts['AppliedRevision'],'ShiftCalendarPending':shifts['AppliedRevision']!=state['Revision'],
        'CurrentShift':shifts['Current'],'ShiftStartedAt':stamp(shifts['StartedMinute'],shifts['StartedMs']),
        'ShiftEndsAt':stamp(shifts['EndsMinute']),'ShiftTimeSynchronized':bool(shifts['TimeSynchronized']),
        'ShiftProductionTarget':arithmetic.unsigned(shifts['ProductionTarget']),
        'ShiftHistoryCount':count,'ShiftHistoryTruncated':bool(shifts['Truncated']),'ShiftClosedSequence':shifts['ClosedSequence']}
    for i in range(count):
        item={n:shifts['History'+n][i] for n in line.HISTORY_COLUMNS};prefix=f'ShiftHistory[{i+1}]/'
        row=dict(SchemaVersion=line.SHIFT_SCHEMA,ProductionTarget=arithmetic.unsigned(item['ProductionTarget']),
            ShiftIndex=item['Index'],StartAt=stamp(item['StartMinute'],item['StartMs']),EndAt=stamp(item['EndMinute'],item['EndMs']),
            TimeSynchronized=bool(item['TimeSynchronized']),ManualReset=bool(item['ManualReset']))
        row.update({n+'Count':arithmetic.unsigned(item[n]) for n in ('Good','Nok','Rework')})
        buckets={n:arithmetic.unsigned(item[n+'S']*1000+item[n+'Ms']) for n in ('Run','Down','Idle')}
        row.update({n+'Ms':v for n,v in buckets.items()})
        row.update(arithmetic.factors(buckets['Run'],buckets['Down'],item['OeeGood'],item['OeeNok'],item['IdealMs']))
        result.update({prefix+n:v for n,v in row.items()})
    return result
