"""S3i publication of PLC-owned Line identity and occupied V3 shift history.

Calendar policy stays with the Line owner. This adapter samples committed
metadata and rebuilds closed rows at the owner's closure marker. It calls the
same Core Float32/UInt32 factor routine as live OEE; no client reconstructs it.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_traceability as trace
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_line as owner
import fraktal_ab_manifest as manifest

P=pub.PREFIX
LINE=P+'LineStatusS3iV63'
SHIFT=P+'ShiftRecordS3iV63'
WORK=P+'LineWorkS3iV63'
HISTORY_FIELDS=('SchemaVersion','ProductionTarget','ShiftIndex','StartAt','EndAt',
    'TimeSynchronized','ManualReset','GoodCount','NokCount','ReworkCount',
    'RunMs','DownMs','IdleMs','Availability','AvailValid','Performance','PerfValid',
    'Quality','QualValid','Oee','OeeValid')
LINE_FIELDS=('LineId','Role','Owner','Revision','LastUpdate','TimeSynchronized','Stale','SourceError','AppliedRevision')
ROOT_FIELDS=('CurrentShift','ShiftStartedAt','ShiftProductionTarget','ShiftHistoryCount',
    'ShiftHistoryTruncated','ShiftEndsAt','ShiftTimeSynchronized','ShiftCalendarPending','ShiftClosedSequence')


def state_tag(app):return f'FRK_{app.name}_CanonicalLineState'
def routine(app):return f'FRK_{app.name}_CanonicalMinuteStamp'
def publish_routine(app):return f'FRK_{app.name}_CanonicalLinePublish'


def validate(app):
    if app.line is None:return []
    findings=[]
    if owner.HISTORY != core.core_limit('MAX_SHIFT_HISTORY'):
        findings.append('S3i history capacity differs from Core MAX_SHIFT_HISTORY')
    for name,width in (('line_id',40),('owner_id',80)):
        if len(getattr(app.line,name).encode('utf-8'))>width:
            findings.append(f'S3i Line {name} exceeds its Core width {width}')
    return findings


def augment(app,definitions):
    if app.line is None:return
    M=pub.Member
    definitions[LINE]=(M('LineId',pub.string_type(40)),M('Role','DINT','ENUM'),M('Owner',pub.string_type(80)),
        M('Revision','DINT','BITSTRING32'),M('LastUpdate','LDT','TIMESTAMP'),M('TimeSynchronized','BOOL'),
        M('Stale','BOOL'),M('SourceError','DINT'),M('AppliedRevision','DINT'))
    definitions[SHIFT]=(M('SchemaVersion','DINT','UINT16'),M('ProductionTarget','DINT','BITSTRING32'),
        M('ShiftIndex','INT'),M('StartAt','LDT','TIMESTAMP'),M('EndAt','LDT','TIMESTAMP'),
        M('TimeSynchronized','BOOL'),M('ManualReset','BOOL'),
        *(M(n,'DINT','BITSTRING32') for n in ('GoodCount','NokCount','ReworkCount','RunMs','DownMs','IdleMs')),
        *(M(n,'BOOL' if n.endswith('Valid') else 'REAL') for n in HISTORY_FIELDS[13:]))
    definitions[pub.root_type(app)]+=(M('Line',LINE),M('CurrentShift','INT'),M('ShiftStartedAt','LDT','TIMESTAMP'),
        M('ShiftProductionTarget','DINT','BITSTRING32'),
        M('ShiftHistory',SHIFT,count=owner.HISTORY,lower=1,count_path=app.name+'/ShiftHistoryCount'),
        M('ShiftHistoryCount','INT'),M('ShiftHistoryTruncated','BOOL'),M('ShiftEndsAt','LDT','TIMESTAMP'),
        M('ShiftTimeSynchronized','BOOL'),M('ShiftCalendarPending','BOOL'),M('ShiftClosedSequence','DINT'))
    definitions[WORK]=tuple(M(n,'DINT') for n in ('Initialized','SeenRevision','SeenDate','SeenClock','SeenQuality','SeenError',
        'SeenStartedMinute','SeenStartedMs','SeenEndsMinute','SeenClosed','SeenCount','Index','MinuteValue','MillisValue'))+(
        M('EpochNs','LINT'),M('SubNs','LINT'),M('EmptyShift',SHIFT))


def initialize(app,result):
    if app.line is None:return
    result['Line']=dict(LineId=app.line.line_id,Owner=app.line.owner_id)
    result['ShiftHistory']=[dict(SchemaVersion=owner.SHIFT_SCHEMA) for _ in range(owner.HISTORY)]


def tags(app,serialize):
    if app.line is None:return []
    return [serialize(state_tag(app),WORK,dict(EmptyShift=dict(SchemaVersion=owner.SHIFT_SCHEMA)),access='None')]


def minute_logic(app):
    """UTC minutes and ms to LDT ns, with exact integer range checks."""
    w=state_tag(app);bad=pub.header_tag(app)+'.Valid'
    # floor(INT64_MAX/60e9)=153722867, remaining whole milliseconds=16854.
    # Widen each operand before multiplication; no large floating literal.
    return [f'{w}.EpochNs := 0;',f'IF ({w}.MinuteValue < 0) OR ({w}.MinuteValue > 153722867) '
        f'OR ({w}.MillisValue < 0) OR ({w}.MillisValue > 59999) '
        f'OR (({w}.MinuteValue = 153722867) AND ({w}.MillisValue > 16854)) THEN {bad} := 0;',
        f'ELSIF {w}.MinuteValue > 0 THEN',f'{w}.EpochNs := {w}.MinuteValue;',
        f'{w}.EpochNs := {w}.EpochNs * 60;',f'{w}.EpochNs := {w}.EpochNs * 1000000000;',
        f'{w}.SubNs := {w}.MillisValue;',f'{w}.SubNs := {w}.SubNs * 1000000;',
        f'{w}.EpochNs := {w}.EpochNs + {w}.SubNs;','END_IF;']


def stamp(app,target,minute,millis='0'):
    w=state_tag(app)
    return [f'{w}.MinuteValue := {minute};',f'{w}.MillisValue := {millis};',
        f'JSR({routine(app)},0);',f'{target} := {w}.EpochNs;']


def history_logic(app):
    w=state_tag(app);s=owner.tag(app,'Shift');t=app.name;bad=pub.header_tag(app)+'.Valid'
    i=w+'.Index';row=f'{t}.ShiftHistory[{i}]';f=metrics.state_tag(app)
    lines=[f'IF ({w}.Initialized = 0) OR ({w}.SeenClosed <> {s}.ClosedSequence) OR ({w}.SeenCount <> {s}.Count) THEN',
        f'FOR {i} := 0 TO {owner.HISTORY-1} DO',f'CPS({w}.EmptyShift,{row},1);',f'IF {i} < {s}.Count THEN',
        f'IF ({s}.HistoryIndex[{i}] < 0) OR ({s}.HistoryIndex[{i}] > {owner.MAX_SHIFTS}) '
        f'OR ({s}.HistoryTimeSynchronized[{i}] < 0) OR ({s}.HistoryTimeSynchronized[{i}] > 1) '
        f'OR ({s}.HistoryManualReset[{i}] < 0) OR ({s}.HistoryManualReset[{i}] > 1) THEN {bad} := 0;',
        'ELSE',f'{row}.ShiftIndex := {s}.HistoryIndex[{i}];',
        f'{row}.TimeSynchronized := {s}.HistoryTimeSynchronized[{i}] <> 0;',
        f'{row}.ManualReset := {s}.HistoryManualReset[{i}] <> 0;']
    for target,source in (('ProductionTarget','ProductionTarget'),('GoodCount','Good'),('NokCount','Nok'),('ReworkCount','Rework')):
        lines += [f'{row}.{target} := {s}.History{source}[{i}];']
    lines += stamp(app,row+'.StartAt',f'{s}.HistoryStartMinute[{i}]',f'{s}.HistoryStartMs[{i}]')
    lines += stamp(app,row+'.EndAt',f'{s}.HistoryEndMinute[{i}]',f'{s}.HistoryEndMs[{i}]')
    for n in ('Run','Down','Idle'):
        # LINT scratch first: DINT seconds *1000 would overflow before assignment.
        lines += [f'{f}.{n} := {s}.History{n}S[{i}];',f'{f}.{n} := {f}.{n} * 1000 + {s}.History{n}Ms[{i}];']
    lines += [f'{f}.Good := {s}.HistoryOeeGood[{i}];',f'{f}.Nok := {s}.HistoryOeeNok[{i}];',
        f'{f}.Ideal := {s}.HistoryIdealMs[{i}];',f'JSR({metrics.factor_routine(app)},0);']
    lines += [f'{row}.{n} := {f}.Factors.{n};' for n in ('RunMs','DownMs','IdleMs',*HISTORY_FIELDS[13:])]
    return lines+['END_IF;','END_IF;','END_FOR;',f'IF {bad} THEN {w}.SeenClosed := {s}.ClosedSequence; '
        f'{w}.SeenCount := {s}.Count; END_IF;','END_IF;']


def publication_logic(app):
    if app.line is None:return []
    w=state_tag(app);s=owner.tag(app,'State');h=owner.tag(app,'Shift');t=app.name;bad=pub.header_tag(app)+'.Valid'
    lines=[f'IF ({s}.SchemaVersion <> 2) OR ({s}.Revision <= 0) '
        f'OR ({s}.LineIdKey <> {manifest.numeric_key(app,app.line.line_id)}) '
        f'OR ({s}.OwnerIdKey <> {manifest.numeric_key(app,app.line.owner_id)}) '
        f'OR ({s}.TimeSynchronized < 0) OR ({s}.TimeSynchronized > 1) OR ({s}.SourceError <> 0) '
        f'OR ({h}.SchemaVersion <> {owner.SHIFT_SCHEMA}) OR ({h}.Count < 0) OR ({h}.Count > {owner.HISTORY}) '
        f'OR ({h}.Current < 0) OR ({h}.Current > {owner.MAX_SHIFTS}) '
        f'OR ({h}.TimeSynchronized < 0) OR ({h}.TimeSynchronized > 1) '
        f'OR ({h}.Truncated < 0) OR ({h}.Truncated > 1) THEN {bad} := 0;',
        'ELSE',f'{t}.Line.Revision := {s}.Revision;',f'{t}.Line.AppliedRevision := {h}.AppliedRevision;',
        f'{t}.CurrentShift := {h}.Current;',f'{t}.ShiftProductionTarget := {h}.ProductionTarget;',
        f'{t}.ShiftTimeSynchronized := {h}.TimeSynchronized <> 0;',f'{t}.ShiftCalendarPending := {h}.AppliedRevision <> {s}.Revision;',
        f'{t}.ShiftHistoryCount := {h}.Count;',f'{t}.ShiftHistoryTruncated := {h}.Truncated <> 0;',
        f'{t}.ShiftClosedSequence := {h}.ClosedSequence;',
        f'IF ({w}.Initialized = 0) OR ({w}.SeenRevision <> {s}.Revision) OR ({w}.SeenDate <> {s}.UpdatedDate) '
        f'OR ({w}.SeenClock <> {s}.UpdatedClock) OR ({w}.SeenQuality <> {s}.TimeSynchronized) '
        f'OR ({w}.SeenError <> {s}.SourceError) THEN']
    lines += trace.timestamp(app,t+'.Line.LastUpdate',s+'.UpdatedDate',s+'.UpdatedClock')
    lines += [f'{t}.Line.TimeSynchronized := {s}.TimeSynchronized <> 0;',f'{t}.Line.SourceError := {s}.SourceError;']
    lines += [f'{w}.Seen{target} := {s}.{source};' for target,source in
        (('Revision','Revision'),('Date','UpdatedDate'),('Clock','UpdatedClock'),('Quality','TimeSynchronized'),('Error','SourceError'))]
    lines += ['END_IF;',f'IF ({w}.Initialized = 0) OR ({w}.SeenStartedMinute <> {h}.StartedMinute) '
        f'OR ({w}.SeenStartedMs <> {h}.StartedMs) OR ({w}.SeenEndsMinute <> {h}.EndsMinute) THEN']
    lines += stamp(app,t+'.ShiftStartedAt',h+'.StartedMinute',h+'.StartedMs')
    lines += stamp(app,t+'.ShiftEndsAt',h+'.EndsMinute')
    lines += [f'IF {bad} THEN {w}.SeenStartedMinute := {h}.StartedMinute; {w}.SeenStartedMs := {h}.StartedMs; '
        f'{w}.SeenEndsMinute := {h}.EndsMinute; END_IF;','END_IF;']
    lines += history_logic(app)
    return lines+[f'IF {bad} THEN {w}.Initialized := 1; ELSE {w}.Initialized := 0; END_IF;','END_IF;']


def cyclic(app):
    return [f'IF S:FS THEN {state_tag(app)}.Initialized := 0; END_IF;',f'JSR({publish_routine(app)},0);'] if app.line is not None else []


def routines(app):
    return [(routine(app),minute_logic(app)),(publish_routine(app),publication_logic(app))] if app.line is not None else []
