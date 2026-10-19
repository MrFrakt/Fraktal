"""Optional Core 3.16 local carrier, PLC result owner and canonical projection.

Public physical storage uses the measured S12 DINT layout. UIDs are bounded
ASCII bytes; measurements are explicitly scaled signed DINTs, never narrowed
LREALs. Static record metadata belongs to the declaration. RFID/host device
transports and nonempty genealogy are not implemented by this local provider.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

import fraktal_ab_declaration as decl

REASONS = dict(CARRIER_READ_FAILED=2020, CARRIER_WRITE_FAILED=2021,
               PART_ID_MISMATCH=2022, RESULT_RECORD_REJECTED=2023,
               EVENT_PART_RECEIVED=2024, EVENT_PART_PROCESSING_STARTED=2025,
               EVENT_PART_PROCESSED=2026, EVENT_PART_PROCESSING_ABORTED=2027)
ACTIONS = dict(receive=1, start=2, processed=3, aborted=4, record=5)
UID_SIZE = 64


@dataclass(frozen=True)
class Measurement:
    name: str
    unit: str
    minimum: int
    maximum: int
    target: int
    scale: int = 1  # physical number = stored DINT / scale


@dataclass(frozen=True)
class LocalCarrier:
    namespace: str
    records: tuple[Measurement, ...] = ()
    result_capacity: int = 8


def validate(app):
    carrier = app.part_carrier
    steps = [s for c in app.chains for s in c.steps]
    if carrier is None:
        return ['Part: helper requires an injected carrier'] if any(
            s.part_action or s.part_verdict or s.part_reason or s.part_record or s.part_value for s in steps) else []
    findings = []
    if not isinstance(carrier, LocalCarrier):
        return ['Part: unsupported carrier provider; expected LocalCarrier']
    if not (type(carrier.namespace) is str and 1 <= len(carrier.namespace) <= 30
            and re.fullmatch(r'[A-Za-z0-9_-]+', carrier.namespace)):
        findings.append('Part: namespace must be 1..30 ASCII letters, digits, underscores or hyphens')
    if type(carrier.result_capacity) is not int or not 1 <= carrier.result_capacity <= 32:
        findings.append('Part: result capacity must be 1..32')
    if not app.host_event_capacity:
        findings.append('Part: canonical host events require an opted-in ring')
    if any(app.reasons.get(k) != v for k, v in REASONS.items()):
        findings.append('Part: register the canonical Core traceability reasons')
    if not isinstance(carrier.records, tuple) or not 0 <= len(carrier.records) <= 32:
        return findings + ['Part: expected tuple of at most 32 measurement definitions']
    for rec in carrier.records:
        if (not isinstance(rec, Measurement) or type(rec.name) is not str
                or not 1 <= len(rec.name) <= 64 or not rec.name.isascii() or not rec.name.isprintable()
                or type(rec.unit) is not str or not 1 <= len(rec.unit) <= 16
                or not rec.unit.isascii() or not rec.unit.isprintable()
                or any(type(v) is not int or not -2**31 <= v < 2**31
                       for v in (rec.minimum, rec.maximum, rec.target))
                or type(rec.scale) is not int or not 1 <= rec.scale <= 1000000
                or rec.minimum >= rec.maximum or not rec.minimum <= rec.target <= rec.maximum):
            findings.append('Part: invalid scaled measurement definition')
    from fraktal_ab_resources import scalar_operands
    allowed_values = scalar_operands(app)
    for step in steps:
        if step.part_action:
            if step.action != decl.MARK or step.part_action not in ACTIONS:
                findings.append('Part: lifecycle helper must be a supported MARK action')
            if step.part_action == 'processed':
                if (type(step.part_verdict) is not int or step.part_verdict not in (0, 1, 2, 3)
                        or not (step.part_reason == 'Ctx.ReportedReason' or
                                type(step.part_reason) is int and step.part_reason in (0, *app.reasons.values()))
                        or step.part_verdict == 2 and step.part_reason == 0):
                    findings.append('Part: invalid verdict or unattributed NOK')
            elif step.part_verdict or step.part_reason:
                findings.append('Part: verdict/reason belong only to processed')
            if step.part_action == 'record':
                if (type(step.part_record) is not int or not 1 <= step.part_record <= len(carrier.records)
                        or step.part_value not in allowed_values):
                    findings.append('Part: invalid measurement reference/value')
            elif step.part_record or step.part_value:
                findings.append('Part: measurement operands belong only to record')
        elif step.part_verdict or step.part_reason or step.part_record or step.part_value:
            findings.append('Part: helper operands require part_action')
        # Counters have one authority: committing the carrier result.
        if any(m.split(':=')[0].strip() in ('Ctx.GoodCount', 'Ctx.ScrapCount') for m in step.marks):
            findings.append('Part: result counters belong to the processed helper')
    if not any(s.part_action == 'receive' for s in steps):
        findings.append('Part: carrier has no receive consumer')
    return findings


def tag(app):
    return f'FRK_{app.name}_Part'


def carrier_tag(app):
    return f'FRK_{app.name}_PartCarrier'


def type_name(app):
    return f'FRK_T_Part{app.part_carrier.result_capacity}V1'


def carrier_name(app):
    return f'FRK_T_LocalCarrier{app.part_carrier.result_capacity}V1'


def service_name(app):
    import fraktal_ab_host_events as host
    suffix = f'_HostV{host.schema(app)}' if host.schema(app) >= 3 else ''
    return f'FRK_{app.name}Part{app.part_carrier.result_capacity}V1{suffix}'


def instance_tag(app):
    return f'FRK_{app.name}_PartService'


def members(app):
    return tuple(decl.scalar(n, initial=1 if n == 'SchemaVersion' else 2 if n == 'CarrierKind' else 0)
                 for n in ('SchemaVersion', 'DataRevision', 'Present', 'CarrierKind', 'Verdict',
                           'ReasonCode', 'Date', 'Time', 'TimeSynchronized', 'RecordCount')) + (
        decl.scalar('Uid', dimension=UID_SIZE),) + tuple(
        decl.scalar(n, dimension=app.part_carrier.result_capacity)
        for n in ('RecordKind', 'RecordValue', 'RecordInTol'))


def carrier_members(app):
    return tuple(decl.scalar(n, initial=1 if n in ('SchemaVersion', 'ProviderKind', 'ProviderIdx') else 0)
                 for n in ('SchemaVersion', 'ProviderKind', 'ProviderIdx', 'Serial', 'Writes',
                           'LastVerdict', 'LastReason', 'LastDate', 'LastTime', 'LastSynchronized',
                           'LastRecordCount')) + (decl.scalar('LastUid', dimension=UID_SIZE),
                                                 decl.scalar('ActiveUid', dimension=UID_SIZE)) + tuple(
        decl.scalar(n, dimension=app.part_carrier.result_capacity)
        for n in ('LastRecordKind', 'LastRecordValue', 'LastRecordInTol'))


def records(app):
    return [decl.Record(type_name(app), members(app)), decl.Record(carrier_name(app), carrier_members(app))]


def call(app, action, *, in_aoi=False, verdict=0, reason=0, record=0, value=0):
    import fraktal_ab_host_events as host
    p, c, r, u, instance = ('Part', 'Carrier', 'HostEvents', 'Ctx', 'PartService') if in_aoi else (
        tag(app), carrier_tag(app), host.tag(app), f'FRK_{app.name}_Unit', instance_tag(app))
    return f'{service_name(app)}({instance},{p},{c},{r},{u},{ACTIONS[action]},{verdict},{reason},{record},{value})'


def step_call(app, step, names):
    def resolve(value):
        text = str(value)
        for module in app.modules:
            if text.startswith(module.name + '.'):
                return names.module(module.name) + text[len(module.name):]
        return text.replace('Ctx.', names.unit + '.').replace('Cfg.', names.cfg + '.')
    return call(app, step.part_action, in_aoi=names.in_aoi, verdict=step.part_verdict,
                reason=resolve(step.part_reason), record=step.part_record,
                value=resolve(step.part_value) if step.part_value else 0)


def logic(app):
    """One implementation shared by every language and lifecycle path."""
    import fraktal_ab_host_events as host
    cap = app.part_carrier.result_capacity
    def fault(reason):
        return [f'IF Ctx.Error = 0 THEN Ctx.Error := 1; Ctx.ErrorID := {REASONS[reason]}; '
                'Ctx.ErrorSource := 0; END_IF;', 'Ctx.Running := 0;']
    def emit(kind, verdict=0, reason=0):
        return ['FOR Index := 0 TO 63 DO Ring.PendingUid[Index] := Part.Uid[Index]; END_FOR;',
                f'{host.emitter_name(app)}(HostEmitter,Ring,{host.KINDS[kind]},0,0,{verdict},{reason});']
    # Algorithmic hex conversion avoids an unmeasured native STRING operation.
    uid = []
    for i, b in enumerate((app.part_carrier.namespace + '-').encode('ascii')):
        uid.append(f'Part.Uid[{i}] := {b};')
    pos = len(app.part_carrier.namespace) + 1
    for word in ('Ring.EpochHigh', 'Ring.EpochLow', 'Carrier.Serial'):
        uid += [f'WordValue := {word} AND 2147483647;', f'FOR Nibble := {pos + 7} TO {pos} BY -1 DO',
                'Digit := WordValue MOD 16;',
                'WordValue := (WordValue - Digit) / 16;',
                f'IF (Nibble = {pos}) AND ({word} < 0) THEN Digit := Digit + 8; END_IF;',
                'IF Digit < 10 THEN Part.Uid[Nibble] := Digit + 48; '
                'ELSE Part.Uid[Nibble] := Digit + 55; END_IF;',
                'END_FOR;']
        pos += 8
    return (
        'Part.DataRevision := Part.DataRevision + 1;',
        'IF Part.DataRevision >= 2147483646 THEN Part.DataRevision := 1; END_IF;',
        'IF (Operation < 1) OR (Operation > 5) THEN', *fault('RESULT_RECORD_REJECTED'),
        'ELSIF (Operation = 1) AND (Part.Present = 0) AND (Ctx.Error = 0) THEN',
        'IF (Carrier.SchemaVersion <> 1) OR (Carrier.ProviderKind <> 1) OR (Carrier.ProviderIdx <> 1) OR '
        '(Carrier.Serial < 0) OR '
        '(Carrier.Serial >= 2147483647) OR ((Ring.EpochLow = 0) AND (Ring.EpochHigh = 0)) THEN',
        *fault('CARRIER_READ_FAILED'), 'ELSE',
        'Carrier.Serial := Carrier.Serial + 1;',
        'FOR Index := 0 TO 63 DO Part.Uid[Index] := 0; END_FOR;', *uid,
        'FOR Index := 0 TO 63 DO Carrier.ActiveUid[Index] := Part.Uid[Index]; END_FOR;',
        'Part.Present := 1;', 'Part.Verdict := 0;', 'Part.ReasonCode := 0;',
        'Part.Date := 0;', 'Part.Time := 0;', 'Part.TimeSynchronized := 0;',
        'Part.RecordCount := 0;',
        f'FOR Index := 0 TO {cap-1} DO Part.RecordKind[Index] := 0; '
        'Part.RecordValue[Index] := 0; Part.RecordInTol[Index] := 0; END_FOR;',
        *emit('PART_RECEIVED'), 'END_IF;',
        'ELSIF (Operation = 2) AND (Part.Present <> 0) AND (Ctx.Error = 0) THEN',
        *emit('PROCESSING_STARTED'),
        'ELSIF (Operation = 5) AND (Part.Present <> 0) AND (Ctx.Error = 0) THEN',
        f'IF (Part.RecordCount < 0) OR (Part.RecordCount >= {cap}) OR (RecordKind < 1) OR (RecordKind > {len(app.part_carrier.records)}) THEN',
        *fault('RESULT_RECORD_REJECTED'), 'ELSE',
        'Index := Part.RecordCount;', 'Part.RecordKind[Index] := RecordKind;',
        'Part.RecordValue[Index] := MeasuredValue;', 'Part.RecordInTol[Index] := 0;',
        *(line for i, rec in enumerate(app.part_carrier.records, 1) for line in (
            f'IF (RecordKind = {i}) AND (MeasuredValue >= {rec.minimum}) AND '
            f'(MeasuredValue <= {rec.maximum}) THEN Part.RecordInTol[Index] := 1; END_IF;',)),
        'Part.RecordCount := Part.RecordCount + 1;', 'END_IF;',
        'ELSIF (Operation = 3) AND (Part.Present <> 0) AND (Ctx.Error = 0) THEN',
        'IdentityMismatch := 0;',
        'FOR Index := 0 TO 63 DO IF Part.Uid[Index] <> Carrier.ActiveUid[Index] THEN '
        'IdentityMismatch := 1; END_IF; END_FOR;',
        'IF IdentityMismatch <> 0 THEN', *fault('PART_ID_MISMATCH'),
        'ELSIF (Verdict < 0) OR (Verdict > 3) OR ((Verdict = 2) AND (Reason = 0)) THEN',
        *fault('RESULT_RECORD_REJECTED'),
        'ELSIF ((Verdict = 1) AND (Ctx.GoodCount >= 2147483647)) OR '
        '((Verdict = 2) AND (Ctx.ScrapCount >= 2147483647)) OR '
        '((Verdict = 3) AND (Ctx.ReworkCount >= 2147483647)) THEN', *fault('RESULT_RECORD_REJECTED'),
        'ELSIF (Carrier.SchemaVersion <> 1) OR (Carrier.ProviderKind <> 1) OR (Carrier.ProviderIdx <> 1) OR '
        '(Carrier.Writes < 0) OR (Carrier.Writes >= 2147483647) THEN', *fault('CARRIER_WRITE_FAILED'),
        'ELSE',
        'Part.Verdict := Verdict;', 'Part.ReasonCode := Reason;',
        'Part.Date := Ring.NowDate;', 'Part.Time := Ring.NowTime;',
        'Part.TimeSynchronized := Ring.NowSynchronized;',
        # Local WriteResult's commit precedes both counters and host emission.
        'FOR Index := 0 TO 63 DO Carrier.LastUid[Index] := Part.Uid[Index]; END_FOR;',
        'Carrier.LastVerdict := Verdict;', 'Carrier.LastReason := Reason;',
        'Carrier.LastDate := Part.Date;', 'Carrier.LastTime := Part.Time;',
        'Carrier.LastSynchronized := Part.TimeSynchronized;',
        'Carrier.LastRecordCount := Part.RecordCount;',
        f'FOR Index := 0 TO {cap-1} DO Carrier.LastRecordKind[Index] := Part.RecordKind[Index]; '
        'Carrier.LastRecordValue[Index] := Part.RecordValue[Index]; '
        'Carrier.LastRecordInTol[Index] := Part.RecordInTol[Index]; END_FOR;',
        'Carrier.Writes := Carrier.Writes + 1;',
        'IF Verdict = 1 THEN Ctx.GoodCount := Ctx.GoodCount + 1; '
        'ELSIF Verdict = 2 THEN Ctx.ScrapCount := Ctx.ScrapCount + 1; '
        'ELSIF Verdict = 3 THEN Ctx.ReworkCount := Ctx.ReworkCount + 1; END_IF;',
        *emit('PROCESSED', 'Verdict', 'Reason'),
        *[f'IF Verdict = 2 THEN {host.emitter_name(app)}(HostEmitter,Ring,10,0,0,2,Reason); END_IF;'],
        'Part.Present := 0;', 'END_IF;',
        'ELSIF (Operation = 4) AND (Part.Present <> 0) THEN',
        'Part.Verdict := 0;',
        'IF (Part.ReasonCode = 0) AND (Ctx.Error <> 0) THEN Part.ReasonCode := Ctx.ErrorID; END_IF;',
        *emit('PROCESSING_ABORTED', 0, 'Part.ReasonCode'), 'Part.Present := 0;',
        'END_IF;', 'Part.DataRevision := Part.DataRevision + 1;',
    )


def service(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_host_events as host
    params = tuple(gen._parameter(n, t, 'InOut') for n,t in (
        ('Part', type_name(app)), ('Carrier', carrier_name(app)),
        ('Ring', host.type_name(app)), ('Ctx', gen.unit_context_name(app)))) + tuple(
        gen._parameter(n, 'DINT', 'Input', radix='Decimal') for n in
        ('Operation', 'Verdict', 'Reason', 'RecordKind', 'MeasuredValue'))
    local = '<LocalTags>' + ''.join(f'<LocalTag Name="{n}" DataType="DINT"/>' for n in
        ('Index', 'WordValue', 'Nibble', 'Digit', 'IdentityMismatch')) + f'<LocalTag Name="HostEmitter" DataType="{host.emitter_name(app)}"/></LocalTags>'
    return gen._aoi(service_name(app), 'Core 3.16 typed local carrier and result owner',
        gen.ENABLE_PARAMETERS + params, logic(app),
        (type_name(app), carrier_name(app), host.type_name(app), gen.unit_context_name(app)),
        software_revision=f'v{app.major_revision}.00', local_tags=local,
        aoi_dependencies=(host.emitter_name(app),))


def tags(app):
    import fraktal_ab_generate as gen
    return [gen._structure_tag(tag(app), type_name(app), members(app)),
            gen._structure_tag(carrier_tag(app), carrier_name(app), carrier_members(app), external_access='None'),
            f'<Tag Name="{instance_tag(app)}" TagType="Base" DataType="{service_name(app)}" Constant="false" ExternalAccess="None"/>']


def finish_scan(app):
    u = f'FRK_{app.name}_Unit'
    return [f'IF ({u}.Error <> 0) OR ({u}.Aborted <> 0) THEN', call(app, 'aborted') + ';', 'END_IF;']


class PartBad(ValueError):
    pass


def uid(data):
    if not isinstance(data, list) or len(data) != UID_SIZE or any(type(b) is not int for b in data):
        raise PartBad('invalid UID byte bounds')
    end = data.index(0) if 0 in data else UID_SIZE
    if any(not 32 <= b <= 126 for b in data[:end]) or any(data[end:]):
        raise PartBad('invalid UID ASCII/termination')
    return bytes(data[:end]).decode('ascii')


def project(app, raw):
    """Refuse malformed snapshots; generic HMI consumes the canonical paths."""
    if not isinstance(raw, dict):
        raise PartBad('part snapshot unavailable')
    try:
        for member in members(app):
            value = raw[member.name]
            if member.dimension and (not isinstance(value, list) or len(value) != member.dimension):
                raise PartBad('invalid part array bounds')
            values = value if member.dimension and isinstance(value, list) and len(value) == member.dimension else [value]
            if (member.dimension and len(values) != member.dimension
                    or any(type(v) is not int or not -2**31 <= v < 2**31 for v in values)):
                raise PartBad('invalid part member layout')
        if (raw['SchemaVersion'] != 1 or raw['DataRevision'] < 0 or raw['DataRevision'] % 2 or raw['CarrierKind'] != 2
                or raw['Present'] not in (0,1) or raw['Verdict'] not in (0,1,2,3)
                or not 0 <= raw['RecordCount'] <= app.part_carrier.result_capacity
                or raw['TimeSynchronized'] not in (0,1)
                or raw['Verdict'] == 2 and raw['ReasonCode'] == 0):
            raise PartBad('invalid part metadata')
        identity = uid(raw['Uid'])
        if raw['Present'] and not identity:
            raise PartBad('present part lacks identity')
        out = {'Part/Uid': identity, 'Part/Present': bool(raw['Present']), 'Part/CarrierKind': 2,
               'Part/Result/Verdict': raw['Verdict'], 'Part/Result/ReasonCode': raw['ReasonCode'],
               'Part/Result/StationPath': app.name,
               'Part/Result/TimeSynchronized': bool(raw['TimeSynchronized'])}
        import fraktal_ab_projection as projection
        stamp = projection._controller_time(raw['Date'], raw['Time'])
        if raw['Verdict'] and not stamp:
            raise PartBad('result timestamp unavailable')
        out['Part/Result/Stamp'] = stamp or ''
        for index in range(app.part_carrier.result_capacity):
            prefix = f'Part/Result/Records[{index+1}]'
            kind = raw['RecordKind'][index]
            if index >= raw['RecordCount']:
                for field, value in dict(Name='', Unit='', Value=0., Minimum=0.,
                                        Maximum=0., Target=0., InTol=False).items():
                    out[prefix + '/' + field] = value
                continue
            if not 1 <= kind <= len(app.part_carrier.records):
                raise PartBad('unknown measurement definition')
            rec = app.part_carrier.records[kind-1]
            value = raw['RecordValue'][index]
            expected = int(rec.minimum <= value <= rec.maximum)
            if raw['RecordInTol'][index] != expected:
                raise PartBad('measurement tolerance flag disagrees')
            for field, field_value in dict(Name=rec.name, Unit=rec.unit,
                Value=value/rec.scale, Minimum=rec.minimum/rec.scale,
                Maximum=rec.maximum/rec.scale, Target=rec.target/rec.scale,
                InTol=bool(expected)).items():
                out[prefix + '/' + field] = field_value
        return out
    except (KeyError, TypeError, IndexError) as error:
        raise PartBad('incomplete part snapshot') from error


def read(comm, app, attempts=3):
    from fraktal_ab_press_execute import read_layout
    revision = (decl.scalar('SchemaVersion'), decl.scalar('DataRevision'))
    for _ in range(attempts):
        before = read_layout(comm, tag(app), revision)
        raw = read_layout(comm, tag(app), members(app))
        after = read_layout(comm, tag(app), revision)
        if before is None or raw is None or after is None:
            raise PartBad('part acquisition failed')
        if before == {m.name: raw[m.name] for m in revision} == after and not after['DataRevision'] % 2:
            project(app, raw)
            return raw
    raise PartBad('part snapshot changed during every bounded read')
