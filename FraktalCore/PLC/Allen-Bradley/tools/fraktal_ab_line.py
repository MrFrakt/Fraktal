"""Optional owner Line profile: whole weekly calendars and PLC-owned history.

The line is composition data beside the Unit, never another module. Only an
owner is declared by this binding; a mirror needs a separately validated source
adapter. Calendar search runs at minute changes/boundaries, never per HMI poll.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import fraktal_ab_declaration as decl

MAX_SHIFTS, HISTORY = 5, 8
CALENDAR_SCHEMA, SHIFT_SCHEMA = 3, 3
INVALID_KEY = 'std.error.shiftCalendarInvalid'
AUDIT_KEY = 'std.audit.shiftClosed'


@dataclass(frozen=True)
class Line:
    line_id: str
    owner_id: str
    utc_offset_min: int = 0
    # Monday bit 0 ... Sunday bit 6; -1 start or zero mask disables a row.
    shifts: tuple = ((-1, 480, 0),) * MAX_SHIFTS
    # Good parts per root/shift; zero means no production target configured.
    production_targets: tuple = (0,) * MAX_SHIFTS


def validate_calendar(offset, shifts):
    if type(offset) is not int or not -840 <= offset <= 840 or len(shifts) != MAX_SHIFTS:
        raise ValueError('invalid shift offset/count')
    intervals = []
    for index, row in enumerate(shifts):
        if len(row) != 3 or any(type(v) is not int for v in row):
            raise ValueError('shift values must be integers')
        start, duration, days = row
        if not -1 <= start <= 1439 or not 1 <= duration <= 1440 or not 0 <= days <= 127:
            raise ValueError('invalid shift start/duration/days')
        if start < 0 or days == 0:
            continue
        for day in range(7):
            if days & (1 << day):
                intervals.append((index, day * 1440 + start, duration))
    for a, start, duration in intervals:
        for b, other, span in intervals:
            for wrap in (-10080, 0, 10080):
                if a == b and start == other and wrap == 0:
                    continue
                if start < other + wrap + span and other + wrap < start + duration:
                    raise ValueError('weekly shifts overlap')


def migrate_daily(offset, starts):
    """V1's next-start semantics, including a sole 24-hour shift, preserved."""
    if (len(starts) not in (4, MAX_SHIFTS) or any(type(s) is not int or not -1 <= s <= 1439 for s in starts)
            or len({s for s in starts if s >= 0}) != len([s for s in starts if s >= 0])):
        raise ValueError('invalid daily starts')
    used = sorted(s for s in starts if s >= 0)
    rows = []
    for start in starts:
        if start == -1:
            rows.append((-1, 480, 0))
        else:
            following = next((s for s in used if s > start), used[0] + 1440)
            rows.append((start, following - start, 127))
    rows += [(-1, 480, 0)] * (MAX_SHIFTS - len(rows))
    validate_calendar(offset, rows)
    return tuple(rows)


def migrate_weekly(offset, shifts):
    """Explicit V2 bridge: retain four rows, append an unused fifth row."""
    if len(shifts) != 4:
        raise ValueError('invalid V2 shift count')
    rows = tuple(shifts) + ((-1, 480, 0),)
    validate_calendar(offset, rows)
    return rows


def record(line):
    validate_calendar(line.utc_offset_min, line.shifts)
    if (len(line.production_targets) != MAX_SHIFTS or any(type(n) is not int or
            not 0 <= n <= 2147483647 for n in line.production_targets)):
        raise ValueError('invalid shift production targets')
    members = [decl.scalar('SchemaVersion'), decl.editable(
        decl.scalar('UtcOffsetMin', initial=line.utc_offset_min), 'line.shift.utcOffsetMin',
        'std.config.shiftUtcOffset', -840, 840, requires_ready=False)]
    members[1] = decl.config_access(members[1], min_write_level=3)
    for i, (start, duration, days) in enumerate(line.shifts, 1):
        for name, value, low, high, suffix in (
                ('StartMin', start, -1, 1439, 'startMin'),
                ('DurationMin', duration, 1, 1440, 'durationMin'),
                ('ActiveDays', days, 0, 127, 'activeDays')):
            members.append(decl.config_access(decl.editable(decl.scalar(f'{name}{i}', initial=value),
                f'line.shift.{i}.{suffix}', f'std.config.shift.{i}.' + dict(StartMin='start', DurationMin='duration', ActiveDays='days')[name],
                low, high, requires_ready=False), min_write_level=3))
    # Append targets after the existing calendar fields: original capability
    # ordinals remain stable across the four-to-five-row extension.
    for i, target in enumerate(line.production_targets, 1):
        members.append(decl.config_access(decl.editable(decl.scalar(f'ProductionTarget{i}', initial=target),
            f'line.shift.{i}.productionTarget', f'std.config.shift.{i}.target',
            0, 2147483647, requires_ready=False), min_write_level=3))
    return decl.Record('FRK_T_LineCfgV3', tuple(members), line_cfg=True, schema_version=CALENDAR_SCHEMA)


def tag(app, suffix):
    return f'FRK_{app.name}_Line{suffix}'


def cfg(app):
    return next(r for r in app.records if r.line_cfg)


def state_members():
    return (decl.scalar('SchemaVersion', initial=1), decl.scalar('Revision', initial=1),
            decl.scalar('UpdatedDate'), decl.scalar('UpdatedClock'),
            decl.scalar('LineIdKey'), decl.scalar('OwnerIdKey'))


HISTORY_COLUMNS = ('Index', 'StartMinute', 'StartMs', 'EndMinute', 'EndMs', 'TimeSynchronized', 'ManualReset',
    'Good', 'Nok', 'Rework', 'OeeGood', 'OeeNok', 'RunS', 'RunMs', 'DownS', 'DownMs', 'IdleS', 'IdleMs', 'IdealMs', 'ProductionTarget')


def shift_members():
    return (decl.scalar('SchemaVersion', initial=SHIFT_SCHEMA),
            *(decl.scalar(n) for n in ('Initialized', 'Current', 'StartedMinute', 'StartedMs', 'EndsMinute',
                'TimeSynchronized', 'ManualReset', 'Count', 'Truncated', 'ClosedSequence', 'AppliedRevision', 'ProductionTarget')),
            *(decl.scalar('History' + n, dimension=HISTORY) for n in HISTORY_COLUMNS))


def work_members():
    return (*(decl.scalar(n) for n in ('Valid', 'I', 'J', 'Day', 'OtherDay', 'Delta',
             'Start', 'OtherStart', 'Year', 'Days', 'NowMinute', 'LocalDay', 'Weekday',
             'CandidateOffset', 'AppliedOffset', 'Selected', 'NextMinute')),
            *(decl.scalar(n, dimension=MAX_SHIFTS) for n in (
                'CandidateStart', 'CandidateDuration', 'CandidateDays',
                'AppliedStart', 'AppliedDuration', 'AppliedDays', 'CandidateTarget', 'AppliedTarget')))


def records(app):
    return [decl.Record('FRK_T_LineStateV1', state_members()),
            decl.Record('FRK_T_ShiftStateV3', shift_members()),
            decl.Record('FRK_T_LineWorkV3', work_members())]


def tags(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    from dataclasses import replace
    state = tuple(replace(m, initial=mf.numeric_key(app, app.line.line_id if m.name == 'LineIdKey' else app.line.owner_id))
                  if m.name in ('LineIdKey', 'OwnerIdKey') else m for m in state_members())
    return [gen._structure_tag(tag(app, suffix), name, members, external_access=access)
            for suffix, name, members, access in (
                ('State', 'FRK_T_LineStateV1', state, 'Read Only'),
                ('Shift', 'FRK_T_ShiftStateV3', shift_members(), 'Read Only'),
                ('Work', 'FRK_T_LineWorkV3', work_members(), 'None'))]


def candidate_copy(app):
    w, c = tag(app, 'Work'), cfg(app).name + 'Tag'
    return [f'{w}.CandidateOffset := {c}.UtcOffsetMin;',
            *(f'{w}.Candidate{n}[{i}] := {c}.{dict(Start="StartMin", Duration="DurationMin", Days="ActiveDays", Target="ProductionTarget")[n]}{i + 1};'
              for i in range(MAX_SHIFTS) for n in ('Start', 'Duration', 'Days', 'Target'))]


def _candidate_member(member):
    if member.name == 'UtcOffsetMin':
        return 'CandidateOffset'
    for native, candidate in (('StartMin', 'Start'), ('DurationMin', 'Duration'), ('ActiveDays', 'Days'), ('ProductionTarget', 'Target')):
        if member.name.startswith(native):
            return f'Candidate{candidate}[{int(member.name[len(native):]) - 1}]'
    raise ValueError('not a line calendar capability')


def validation_logic(app):
    w = tag(app, 'Work')
    # Duration is at most one day: different rows can intersect only on the
    # same day or across midnight. Unordered row pairs suffice; weekday
    # mask intersection replaces the day/wrap loops and two seven-arm CASEs.
    # Rotating a validated seven-bit mask left maps Sunday to Monday. The
    # conditional subtraction is integral on Logix, with no shift instruction,
    # REAL quotient or added scratch storage.
    lines = [f'{w}.Valid := 1;',
        f'IF ({w}.CandidateOffset < -840) OR ({w}.CandidateOffset > 840) THEN {w}.Valid := 0; END_IF;',
        f'FOR {w}.I := 0 TO {MAX_SHIFTS - 1} DO',
        f'IF ({w}.CandidateStart[{w}.I] < -1) OR ({w}.CandidateStart[{w}.I] > 1439) THEN {w}.Valid := 0; END_IF;',
        f'IF ({w}.CandidateDuration[{w}.I] < 1) OR ({w}.CandidateDuration[{w}.I] > 1440) THEN {w}.Valid := 0; END_IF;',
        f'IF ({w}.CandidateDays[{w}.I] < 0) OR ({w}.CandidateDays[{w}.I] > 127) THEN {w}.Valid := 0; END_IF;',
        f'IF {w}.CandidateTarget[{w}.I] < 0 THEN {w}.Valid := 0; END_IF;',
        'END_FOR;', f'IF {w}.Valid <> 0 THEN', f'FOR {w}.I := 0 TO {MAX_SHIFTS - 2} DO',
        f'FOR {w}.J := {w}.I + 1 TO {MAX_SHIFTS - 1} DO',
        f'IF ({w}.CandidateStart[{w}.I] >= 0) AND ({w}.CandidateStart[{w}.J] >= 0) THEN',
        f'{w}.Selected := {w}.CandidateDays[{w}.I];',
        f'{w}.NextMinute := {w}.CandidateDays[{w}.J];',
        f'{w}.Start := {w}.CandidateStart[{w}.I] + {w}.CandidateDuration[{w}.I];',
        f'{w}.OtherStart := {w}.CandidateStart[{w}.J] + {w}.CandidateDuration[{w}.J];',
        f'IF ({w}.Selected AND {w}.NextMinute) <> 0 THEN',
        f'IF ({w}.CandidateStart[{w}.I] < {w}.OtherStart) AND ({w}.CandidateStart[{w}.J] < {w}.Start) THEN {w}.Valid := 0; END_IF;',
        'END_IF;',
        f'{w}.Day := {w}.Selected * 2;',
        f'IF {w}.Day > 127 THEN {w}.Day := {w}.Day - 127; END_IF;',
        f'IF ({w}.Day AND {w}.NextMinute) <> 0 THEN',
        f'IF {w}.Start > (1440 + {w}.CandidateStart[{w}.J]) THEN {w}.Valid := 0; END_IF;',
        'END_IF;',
        f'{w}.OtherDay := {w}.NextMinute * 2;',
        f'IF {w}.OtherDay > 127 THEN {w}.OtherDay := {w}.OtherDay - 127; END_IF;',
        f'IF ({w}.OtherDay AND {w}.Selected) <> 0 THEN',
        f'IF {w}.OtherStart > (1440 + {w}.CandidateStart[{w}.I]) THEN {w}.Valid := 0; END_IF;',
        'END_IF;', 'END_IF;', 'END_FOR;', 'END_FOR;', 'END_IF;']
    return lines


def routine(app, suffix):
    return f'FRK_{app.name}_Line{suffix}'


def stage_call(app):
    return [f'JSR({routine(app, "Stage")},0);']


def routines(app):
    """Private Line services, emitted once and called with existing scratch."""
    return [(routine(app, suffix), body(app)) for suffix, body in (
        ('Stage', candidate_copy), ('Validate', validation_logic),
        ('Search', search_logic), ('Close', close_logic), ('Apply', apply_calendar))]


def write_validate(app, ordinal, value):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    w = tag(app, 'Work')
    lines = [f'CASE {ordinal} OF']
    numbers = [str(o) for o, r, _ in gen.editable_values(app) if r.line_cfg]
    lines += [','.join(numbers) + ':', *stage_call(app), f'CASE {ordinal} OF']
    for o, r, m in gen.editable_values(app):
        if r.line_cfg:
            lines += [f'{o}: {w}.{_candidate_member(m)} := {value};']
    lines += ['END_CASE;', f'JSR({routine(app, "Validate")},0);',
              f'IF {w}.Valid = 0 THEN', *mb._refuse(app, INVALID_KEY), 'END_IF;',
              'ELSE', '(* Another configuration kind. *)', 'END_CASE;']
    return lines


def accepted(app):
    s = tag(app, 'State')
    return [f'{s}.Revision := {s}.Revision + 1;', f'IF {s}.Revision <= 0 THEN {s}.Revision := 1; END_IF;',
            f'{s}.UpdatedDate := FRK_{app.name}_NowDate;', f'{s}.UpdatedClock := FRK_{app.name}_NowTime;']


def set_validate(app, q, s):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    w = tag(app, 'Work')
    capabilities = [(o, m) for o, r, m in gen.editable_values(app) if r.line_cfg]
    lines = [f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) AND ({q}.Kind = 2) AND ({s}.Reason = 0) THEN',
        *stage_call(app), f'IF {q}.Count <> {len(capabilities)} THEN {s}.Reason := {mf.numeric_key(app, INVALID_KEY)}; END_IF;',
        f'FOR {w}.I := 0 TO {q}.Count - 1 DO', f'CASE {q}.Ordinal[{w}.I] OF']
    lines += [f'{o}: {w}.{_candidate_member(m)} := {q}.Value[{w}.I];' for o, m in capabilities]
    lines += ['ELSE', f'{s}.Reason := {mf.numeric_key(app, INVALID_KEY)};', 'END_CASE;', 'END_FOR;',
        f'JSR({routine(app, "Validate")},0);',
        f'IF {w}.Valid = 0 THEN {s}.Reason := {mf.numeric_key(app, INVALID_KEY)}; END_IF;', 'END_IF;']
    return lines


def restore_logic(app):
    import fraktal_ab_generate as gen
    c, r = cfg(app).name + 'Tag', cfg(app)
    defaults = [(m.name, m.initial) for m in r.members[1:]]
    return gen._restore_gate(c, r.schema_version, defaults, gen.config_persist_tag(app), 'Line calendar')


def apply_calendar(app):
    w, state, s = tag(app, 'Work'), tag(app, 'State'), tag(app, 'Shift')
    return [*stage_call(app), f'{w}.AppliedOffset := {w}.CandidateOffset;',
            f'FOR {w}.I := 0 TO {MAX_SHIFTS - 1} DO',
            *(f'{w}.Applied{n}[{w}.I] := {w}.Candidate{n}[{w}.I];' for n in ('Start', 'Duration', 'Days', 'Target')),
            'END_FOR;', f'{s}.AppliedRevision := {state}.Revision;']


def clock_logic(app):
    w, clock = tag(app, 'Work'), f'FRK_{app.name}_Clock'
    # Absolute UTC minutes since 1970. Every quotient is integral before Logix
    # DINT assignment, whose rounding differs from an IEC truncating division.
    def quotient(v, divisor):
        return f'(({v}) - (({v}) MOD {divisor})) / {divisor}'
    y = w + '.Year'
    lines = [f'{y} := {clock}[0] - 1;',
        f'{w}.Days := 365 * ({clock}[0] - 1970) + {quotient(y, 4)} - {quotient(y, 100)} + {quotient(y, 400)} - 477;',
        f'CASE {clock}[1] OF']
    starts = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    lines += [f'{i}: {w}.Days := {w}.Days + {n};' for i, n in enumerate(starts, 1)]
    lines += ['END_CASE;', f'IF {clock}[1] > 2 THEN',
              f'IF (({clock}[0] MOD 4) = 0) AND ((({clock}[0] MOD 100) <> 0) OR (({clock}[0] MOD 400) = 0)) THEN {w}.Days := {w}.Days + 1; END_IF;',
              'END_IF;', f'{w}.Days := {w}.Days + {clock}[2] - 1;',
              f'{w}.NowMinute := {w}.Days * 1440 + {clock}[3] * 60 + {clock}[4];']
    return lines


def search_logic(app):
    w = tag(app, 'Work')
    # Only today's or yesterday's row can be active (duration <=24 hours).
    # Future starts are searched through next week, so unscheduled gaps get a
    # real next boundary rather than inheriting the last shift indefinitely.
    lines = [f'{w}.Start := {w}.NowMinute + {w}.AppliedOffset;',
        f'{w}.LocalDay := ({w}.Start - ({w}.Start MOD 1440)) / 1440;',
        f'IF ({w}.Start MOD 1440) < 0 THEN {w}.LocalDay := {w}.LocalDay - 1; END_IF;',
        f'{w}.Selected := 0;', f'{w}.NextMinute := 0;',
        f'FOR {w}.I := 0 TO {MAX_SHIFTS - 1} DO', f'IF {w}.AppliedStart[{w}.I] >= 0 THEN',
        f'FOR {w}.Delta := -1 TO 7 DO',
        f'{w}.Day := ({w}.LocalDay + {w}.Delta + 3) MOD 7;',
        f'CASE {w}.Day OF']
    lines += [f'{i}: {w}.Weekday := {w}.AppliedDays[{w}.I] AND {1 << i};' for i in range(7)]
    lines += ['END_CASE;', f'IF {w}.Weekday <> 0 THEN',
        f'{w}.OtherStart := ({w}.LocalDay + {w}.Delta) * 1440 + {w}.AppliedStart[{w}.I] - {w}.AppliedOffset;',
        f'IF ({w}.OtherStart <= {w}.NowMinute) AND ({w}.NowMinute < ({w}.OtherStart + {w}.AppliedDuration[{w}.I])) THEN',
        f'{w}.Selected := {w}.I + 1;',
        f'{w}.NextMinute := {w}.OtherStart + {w}.AppliedDuration[{w}.I];',
        'ELSIF ((' + w + '.OtherStart > ' + w + '.NowMinute) AND ((' + w + '.NextMinute = 0) OR (' + w + '.OtherStart < ' + w + '.NextMinute))) THEN',
        f'{w}.NextMinute := {w}.OtherStart;', 'END_IF;', 'END_IF;', 'END_FOR;', 'END_IF;', 'END_FOR;']
    return lines


def close_logic(app):
    import fraktal_ab_generate as gen
    s, w, u, o = tag(app, 'Shift'), tag(app, 'Work'), f'FRK_{app.name}_Unit', gen.oee_tag(app)
    lines = [f'FOR {w}.I := 7 TO 1 BY -1 DO']
    lines += [f'{s}.History{n}[{w}.I] := {s}.History{n}[{w}.I - 1];' for n in HISTORY_COLUMNS]
    lines += ['END_FOR;', f'IF {s}.Count < {HISTORY} THEN {s}.Count := {s}.Count + 1; ELSE {s}.Truncated := 1; END_IF;']
    source = dict(Index=s+'.Current', StartMinute=s+'.StartedMinute', StartMs=s+'.StartedMs',
                  EndMinute=w+'.NowMinute', EndMs=f'FRK_{app.name}_NowTime MOD 100000',
                  TimeSynchronized=s+'.TimeSynchronized', ManualReset=s+'.ManualReset',
                  Good=u+'.GoodCount', Nok=u+'.ScrapCount', Rework=u+'.ReworkCount',
                  OeeGood=u+'.GoodCount - '+o+'.GoodBase', OeeNok=u+'.ScrapCount - '+o+'.NokBase',
                  IdealMs=gen._oee_ideal(app), ProductionTarget=s+'.ProductionTarget')
    source.update({n: o+'.'+n for n in ('RunS','RunMs','DownS','DownMs','IdleS','IdleMs')})
    lines += [f'{s}.History{n}[0] := {source[n]};' for n in HISTORY_COLUMNS]
    lines += [f'{s}.ClosedSequence := {s}.ClosedSequence + 1;',
              f'IF {s}.ClosedSequence <= 0 THEN {s}.ClosedSequence := 1; END_IF;']
    if app.access_users is not None:
        import fraktal_ab_access as access
        # Automatic closure has no operator actor; the ordinary ring records
        # the audit and the immutable shift sequence offers the sink boundary.
        lines += access._audit(app, AUDIT_KEY, '0', s+'.ClosedSequence', '1', '0',
                               access.tag(app, 'State')+'.UserBytes', gate='-1')
    lines += [*(f'{u}.{n} := 0;' for n in ('GoodCount','ScrapCount','ReworkCount')),
              *gen.oee_reset_lines(app, clear_trend=False), f'{s}.ManualReset := 0;']
    return lines


def cyclic(app):
    import fraktal_ab_generate as gen
    w, s, state = tag(app, 'Work'), tag(app, 'Shift'), tag(app, 'State')
    hp = gen.health_probe_tag(app)
    clock = f'FRK_{app.name}_Clock'
    target = [f'{s}.ProductionTarget := 0;', f'IF {s}.Current > 0 THEN',
              f'{w}.J := {s}.Current - 1;', f'{s}.ProductionTarget := {w}.AppliedTarget[{w}.J];', 'END_IF;']
    lines = [f'{w}.Valid := 1;']
    lines += [f'IF ({clock}[{i}] < {low}) OR ({clock}[{i}] > {high}) THEN {w}.Valid := 0; END_IF;'
              for i, low, high in ((0,1970,2099), (1,1,12), (2,1,31), (3,0,23), (4,0,59))]
    lines += [f'IF {w}.Valid <> 0 THEN', *clock_logic(app)]
    lines += [f'IF {hp}.TimeIsSynchronized = 0 THEN {s}.TimeSynchronized := 0; END_IF;',
              f'IF {w}.NowMinute < {s}.StartedMinute THEN {s}.TimeSynchronized := 0; END_IF;',
              f'IF {s}.Initialized = 0 THEN', f'JSR({routine(app, "Apply")},0);',
              f'JSR({routine(app, "Search")},0);',
              f'{s}.Current := {w}.Selected;', *target, f'{s}.StartedMinute := {w}.NowMinute;',
              f'{s}.StartedMs := FRK_{app.name}_NowTime MOD 100000;',
              f'{s}.EndsMinute := {w}.NextMinute;', f'{s}.TimeSynchronized := {hp}.TimeIsSynchronized;',
              f'{s}.Initialized := 1;',
              # Empty schedules have no boundary. An edit applies on next scan;
              # any accrued unscheduled period is first closed, never discarded.
              f'ELSIF ({s}.EndsMinute > 0) AND ({w}.NowMinute >= {s}.EndsMinute) THEN',
              f'IF ({s}.EndsMinute > 0) AND ({w}.NowMinute > {s}.EndsMinute) THEN {s}.TimeSynchronized := 0; END_IF;',
              f'JSR({routine(app, "Close")},0);', f'JSR({routine(app, "Apply")},0);',
              f'JSR({routine(app, "Search")},0);', f'{s}.Current := {w}.Selected;', *target,
              f'{s}.StartedMinute := {w}.NowMinute;', f'{s}.StartedMs := FRK_{app.name}_NowTime MOD 100000;',
              f'{s}.EndsMinute := {w}.NextMinute;', f'{s}.TimeSynchronized := {hp}.TimeIsSynchronized;',
              f'ELSIF ({s}.EndsMinute = 0) AND ({s}.AppliedRevision <> {state}.Revision) THEN',
              f'JSR({routine(app, "Apply")},0);', f'JSR({routine(app, "Search")},0);',
              f'IF {w}.Selected <> {s}.Current THEN', f'JSR({routine(app, "Close")},0);',
              f'{s}.StartedMinute := {w}.NowMinute;', f'{s}.StartedMs := FRK_{app.name}_NowTime MOD 100000;',
              f'{s}.TimeSynchronized := {hp}.TimeIsSynchronized;', 'END_IF;',
              f'{s}.Current := {w}.Selected;', *target, f'{s}.EndsMinute := {w}.NextMinute;', 'END_IF;',
              'ELSE', f'{s}.TimeSynchronized := 0;', 'END_IF;']
    return lines


def projection(app, state, shifts, *, rows=None):
    if not app.line or state is None or shifts is None or state.get('SchemaVersion') != 1 or shifts.get('SchemaVersion') != SHIFT_SCHEMA:
        return {}
    count = shifts.get('Count', -1)
    if type(count) is not int or not 0 <= count <= HISTORY or not 0 <= shifts.get('Current', -1) <= MAX_SHIFTS:
        return {}
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    def stamp(value, millis=0):
        return (epoch + timedelta(minutes=value, milliseconds=millis)).isoformat() if type(value) is int and value > 0 else None
    import fraktal_ab_projection as px
    keys = {r['NumericKey']: r['PortableKey'] for r in (rows or {}).get('Localization', [])}
    out = {'Line/Role': 0, 'Line/LineId': keys.get(state['LineIdKey'], ''),
           'Line/OwnerId': keys.get(state['OwnerIdKey'], ''),
           'Line/Revision': state['Revision'], 'Line/Stale': False,
           'Line/LastUpdatedAt': px._controller_time(state['UpdatedDate'], state['UpdatedClock']),
           'Line/AppliedRevision': shifts['AppliedRevision'],
           'ShiftCalendarPending': shifts['AppliedRevision'] != state['Revision'],
           'CurrentShift': shifts['Current'], 'ShiftStartedAt': stamp(shifts['StartedMinute'], shifts['StartedMs']),
           'ShiftProductionTarget': shifts['ProductionTarget'],
           'ShiftEndsAt': stamp(shifts['EndsMinute']), 'ShiftTimeSynchronized': bool(shifts['TimeSynchronized']),
           'ShiftHistoryCount': count, 'ShiftHistoryTruncated': bool(shifts['Truncated']),
           'ShiftClosedSequence': shifts['ClosedSequence']}
    for i in range(count):
        row = 'ShiftHistory['+str(i+1)+']/'
        item = {n: shifts['History'+n][i] for n in HISTORY_COLUMNS}
        out.update({row+'ShiftIndex': item['Index'], row+'StartAt': stamp(item['StartMinute'], item['StartMs']),
            row+'EndAt': stamp(item['EndMinute'], item['EndMs']), row+'TimeSynchronized': bool(item['TimeSynchronized']),
            row+'ManualReset': bool(item['ManualReset']), row+'GoodCount': item['Good'],
            row+'NokCount': item['Nok'], row+'ReworkCount': item['Rework'], row+'ProductionTarget': item['ProductionTarget']})
        buckets = {n: item[n+'S'] * 1000 + item[n+'Ms'] for n in ('Run','Down','Idle')}
        out.update({row+n+'Ms': v for n, v in buckets.items()})
        out.update({row+n: v for n, v in px.oee_factors(buckets['Run'], buckets['Down'], item['OeeGood'], item['OeeNok'], item['IdealMs']).items()})
    return out
