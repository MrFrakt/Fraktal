"""PLC-owned host events and coherent, acknowledged delivery.

Native AOIs/UDTs supply bounded storage/execution; this adapter supplies the
Core event vocabulary, ordering and loss semantics. It is not an alarm engine.
V1 is non-part; a local carrier selects V2. Confirmed resource producers select
V3, sharing the bounded identity bytes between PartUid and resource Subject.
V4 adds opt-in packed text values; V1-V3 layouts and bodies stay unchanged.
"""
from __future__ import annotations

import copy
import errno
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_resources as resources
import fraktal_ab_genealogy as genealogy
# Delivery is declaration-free and lives with the host adapter.
from fraktal_ab_host_cursor import (  # noqa: F401
    LIMIT, META, HostEventsBad, metadata, validate_metadata, _cursor_lock, Cursor)

KINDS = dict(PART_RECEIVED=1, PROCESSING_STARTED=2, PROCESSED=3,
             PROCESSING_ABORTED=4, CHANGEOVER_STARTED=5, CHANGEOVER_DONE=6,
             TOOL_CHANGED=7, MATERIAL_CHANGED=8, MODE_CHANGED=9, NOK=10)
SUPPORTED = (5, 6, 9, 10)
COLUMNS = ('Sequence', 'Kind', 'ModelOrdinal', 'Value', 'Date', 'Time',
           'TimeSynchronized', 'Verdict', 'ReasonCode')


def validate(app):
    result = []
    if type(app.host_event_capacity) is not int or not 0 <= app.host_event_capacity <= 64:
        return ['HostEvents: capacity must be an integer in 0..64']
    if not app.host_event_capacity:
        return result
    for chain in app.chains:
        for step in chain.steps:
            counts = [mark for mark in step.marks if mark.split(':=')[0].strip() == 'Ctx.ScrapCount']
            if counts and (counts != ['Ctx.ScrapCount := Ctx.ScrapCount + 1']
                           or not (step.nok_reason == 'Ctx.ReportedReason' or (
                               type(step.nok_reason) is int and step.nok_reason in app.reasons.values()
                               and step.nok_reason != 0))):
                result.append(f'HostEvents: {chain.name}/{step.number} NOK requires one increment and a registered nonzero nok_reason')
    return result


def nok_reason(step, names):
    return str(step.nok_reason).replace('Ctx.', names.unit + '.')


def tag(app):
    return f'FRK_{app.name}_HostEvents'


def schema(app):
    if genealogy.enabled(app):
        return 5
    if resources.text_enabled(app):
        return 4
    if resources.enabled(app):
        return 3
    return 2 if app.part_carrier is not None else 1


def profile(app):
    return (f'V5T{int(resources.text_enabled(app))}G{genealogy.capacity(app)}'
            if genealogy.enabled(app) else f'V{schema(app)}')


def type_name(app):
    return f'FRK_T_HostEvents{app.host_event_capacity}{profile(app)}'


def emitter_name(app):
    return f'FRK_HostEmit{app.host_event_capacity}{profile(app)}'


def instance_tag(app):
    return f'FRK_{app.name}_HostEmitter'


def members(app):
    return tuple(decl.scalar(n, initial=(schema(app) if n == 'SchemaVersion' else
                                       app.host_event_capacity if n == 'Capacity' else 0))
                 for n in META) + tuple(decl.scalar(n) for n in
                    ('NowDate', 'NowTime', 'NowSynchronized', 'CompleteSeen')) + (
                        decl.scalar('EpochWords', dimension=2),) + tuple(
                            decl.scalar(n, dimension=app.host_event_capacity) for n in COLUMNS) + (
        (decl.scalar('PendingUid', dimension=64),
         decl.scalar('Uid', dimension=64 * app.host_event_capacity)) if schema(app) >= 2 else ()) + (
        (decl.scalar('PendingTextEnabled'),
         decl.scalar('PendingText', dimension=resources.TEXT_LIMIT + 1),
         decl.scalar('ValueFormat', dimension=app.host_event_capacity),
         decl.scalar('ValueText', dimension=resources.TEXT_WORDS * app.host_event_capacity))
        if resources.text_enabled(app) else ()) + (genealogy.host_members(app) if genealogy.enabled(app) else ())


def _text_validation():
    """Validate capture before changing head, sequence, revision or row data."""
    return [
        'TextActive := 0;',
        'IF (Kind = 7) OR (Kind = 8) THEN',
        'IF (Ring.PendingTextEnabled <> 0) AND (Ring.PendingTextEnabled <> 1) THEN Ring.Failed := 1; END_IF;',
        'TextActive := Ring.PendingTextEnabled;',
        'IF TextActive = 1 THEN',
        'IF EventValue <> 0 THEN Ring.Failed := 1; END_IF;',
        'TextEnd := 0;',
        f'FOR ByteIndex := 0 TO {resources.TEXT_LIMIT} DO',
        'IF Ring.PendingText[ByteIndex] = 0 THEN',
        'TextEnd := 1;',
        f'ELSIF (TextEnd <> 0) OR (ByteIndex = {resources.TEXT_LIMIT}) OR '
        '(Ring.PendingText[ByteIndex] < 32) OR (Ring.PendingText[ByteIndex] > 126) THEN',
        'Ring.Failed := 1;', 'END_IF;', 'END_FOR;', 'END_IF;', 'END_IF;',
    ]


def _text_store():
    """Four printable ASCII bytes fit one positive DINT, without overflow."""
    return [
        'Ring.ValueFormat[Slot] := TextActive;',
        f'FOR ByteIndex := 0 TO {resources.TEXT_WORDS - 1} DO',
        f'UidIndex := (Slot * {resources.TEXT_WORDS}) + ByteIndex;',
        'Ring.ValueText[UidIndex] := 0;', 'END_FOR;',
        'IF TextActive = 1 THEN',
        f'FOR ByteIndex := 0 TO {resources.TEXT_WORDS - 2} DO',
        f'UidIndex := (Slot * {resources.TEXT_WORDS}) + ByteIndex;',
        'SourceIndex := ByteIndex * 4;',
        'Ring.ValueText[UidIndex] := Ring.PendingText[SourceIndex] '
        '+ (Ring.PendingText[SourceIndex + 1] * 256) '
        '+ (Ring.PendingText[SourceIndex + 2] * 65536) '
        '+ (Ring.PendingText[SourceIndex + 3] * 16777216);',
        'END_FOR;', 'END_IF;',
    ]


def emit_logic(app):
    """One owning append algorithm, called from every rendition."""
    assignments = dict(Kind='Kind', ModelOrdinal='ModelOrdinal', Value='EventValue',
                       Date='Ring.NowDate', Time='Ring.NowTime',
                       TimeSynchronized='Ring.NowSynchronized', Verdict='Verdict',
                       ReasonCode='Reason')
    if schema(app) >= 3:
        # One body per named reusable type, including roots without a carrier.
        # Composition controls producer availability; decoding rejects any Part
        # record from a carrier-off application rather than silently accepting it.
        guard = ('((Kind < 1) OR (Kind > 10)) OR '
                 '((Kind = 3) AND ((Verdict < 0) OR (Verdict > 3) OR ((Verdict = 2) AND (Reason = 0)))) OR ')
    else:
        guard = ('((Kind < 1) OR ((Kind > 6) AND (Kind <> 9) AND (Kind <> 10))) OR '
                 '((Kind = 3) AND ((Verdict < 0) OR (Verdict > 3) OR ((Verdict = 2) AND (Reason = 0)))) OR '
                 if schema(app) == 2 else
                 '((Kind <> 5) AND (Kind <> 6) AND (Kind <> 9) AND (Kind <> 10)) OR ')
    identity_condition = ('((Kind >= 1) AND (Kind <= 4)) OR (Kind = 7) OR (Kind = 8)'
                          if schema(app) >= 3 else '(Kind >= 1) AND (Kind <= 4)')
    return (
        'IF (Ring.Failed = 0) THEN',
        *(_text_validation() if resources.text_enabled(app) else []),
        *(genealogy.host_validation(app) if genealogy.enabled(app) else []),
        *(['IF Ring.Failed = 0 THEN'] if resources.text_enabled(app) or genealogy.enabled(app) else []),
        'IF (Ring.NewestSequence >= 2147483647) OR '
        '(Ring.Capacity <> ' + str(app.host_event_capacity) + ') OR ' +
        guard +
        '((Kind = 10) AND (Reason = 0)) THEN',
        'Ring.Failed := 1;',
        'ELSE',
        'IF Ring.DataRevision >= 2147483646 THEN Ring.DataRevision := 1; '
        'ELSE Ring.DataRevision := Ring.DataRevision + 1; END_IF;',
        'Ring.Head := (Ring.Head MOD Ring.Capacity) + 1;',
        'Slot := Ring.Head - 1;',
        'Ring.NewestSequence := Ring.NewestSequence + 1;',
        'Ring.Sequence[Slot] := Ring.NewestSequence;',
        *(f'Ring.{n}[Slot] := {value};' for n, value in assignments.items()),
        *(['FOR ByteIndex := 0 TO 63 DO',
           'UidIndex := (Slot * 64) + ByteIndex;',
           f'IF {identity_condition} THEN Ring.Uid[UidIndex] := Ring.PendingUid[ByteIndex]; '
           'ELSE Ring.Uid[UidIndex] := 0; END_IF;', 'END_FOR;'] if schema(app) >= 2 else []),
        *(_text_store() if resources.text_enabled(app) else []),
        *(genealogy.host_store(app) if genealogy.enabled(app) else []),
        'IF Ring.Count < Ring.Capacity THEN Ring.Count := Ring.Count + 1; '
        'ELSE Ring.Wrapped := 1; END_IF;',
        'Ring.DataRevision := Ring.DataRevision + 1;',
        'END_IF;',
        'END_IF;',
        *(['END_IF;'] if resources.text_enabled(app) or genealogy.enabled(app) else []),
    )


def emitter(app):
    import fraktal_ab_generate as gen
    params = (gen._parameter('Ring', type_name(app), 'InOut'),) + tuple(
        gen._parameter(n, 'DINT', 'Input', radix='Decimal') for n in
        ('Kind', 'ModelOrdinal', 'EventValue', 'Verdict', 'Reason'))
    return gen._aoi(emitter_name(app), 'Core 11.6 single bounded host-event append owner',
                    gen.ENABLE_PARAMETERS + params, emit_logic(app), (type_name(app),),
                    software_revision=f'v{app.major_revision}.00',
                    local_tags='<LocalTags><LocalTag Name="Slot" DataType="DINT"/>' +
                    ('<LocalTag Name="ByteIndex" DataType="DINT"/><LocalTag Name="UidIndex" DataType="DINT"/>'
                     if schema(app) >= 2 else '') +
                    ('<LocalTag Name="TextActive" DataType="DINT"/><LocalTag Name="TextEnd" DataType="DINT"/>'
                     if resources.text_enabled(app) else '') +
                    ('<LocalTag Name="SourceIndex" DataType="DINT"/>'
                     if resources.text_enabled(app) or genealogy.enabled(app) else '') + '</LocalTags>')


def call(app, kind, *, in_aoi=False, model='0', value='0', reason=0):
    if KINDS[kind] in (1, 2, 3, 4) and app.part_carrier is None:
        raise ValueError('Part host-event producer requires an injected carrier')
    ring, instance = ('HostEvents', 'HostEmitter') if in_aoi else (tag(app), instance_tag(app))
    verdict = 2 if kind == 'NOK' else 0
    return f'{emitter_name(app)}({instance},{ring},{KINDS[kind]},{model},{value},{verdict},{reason})'


def start_scan(app):
    """Clock sampled once before event producers; no clock operation writes."""
    import fraktal_ab_generate as gen
    r = tag(app)
    return [*gen.wall_clock_logic(app),
            f'IF FRK_{app.name}_ScanCount = 0 THEN',
            f'{r}.DataRevision := 1;',
            f'GSV(WallClockTime,,CurrentValue,{r}.EpochWords[0]);',
            f'{r}.EpochLow := {r}.EpochWords[0];',
            f'{r}.EpochHigh := {r}.EpochWords[1];',
            f'{r}.DataRevision := 2;',
            'END_IF;',
            f'{r}.NowDate := FRK_{app.name}_NowDate;',
            f'{r}.NowTime := FRK_{app.name}_NowTime;',
            f'GSV(TimeSynchronize,,IsSynchronized,{r}.NowSynchronized);']


def finish_scan(app):
    # Completion is tested after model commit, so a failed recipe emits no DONE.
    r, u = tag(app), f'FRK_{app.name}_Unit'
    modes = [c.mode_ordinal for c in app.chains if c.mode_ordinal == 3]
    return ([f'IF ({u}.Mode = 3) AND ({u}.Complete <> 0) AND ({r}.CompleteSeen = 0) THEN',
             call(app, 'CHANGEOVER_DONE', model=f'{u}.ModelOrdinal') + ';',
             'END_IF;', f'{r}.CompleteSeen := {u}.Complete;'] if modes else [])


def decode(app, raw, codes=()):
    """Validate all active rows; omit no malformed event to obtain continuity."""
    if not isinstance(raw, dict):
        raise HostEventsBad('host-event read failed')
    try:
        m = metadata(raw)
        cap, count, head, newest = validate_metadata(m, app.host_event_capacity, schema(app))
        for n in COLUMNS:
            if (not isinstance(raw[n], list) or len(raw[n]) != cap
                    or any(type(v) is not int for v in raw[n])):
                raise HostEventsBad('invalid host-event column bounds')
        from datetime import datetime
        import fraktal_ab_projection as projection
        events = []
        if schema(app) >= 2 and (not isinstance(raw['Uid'], list) or len(raw['Uid']) != cap * 64):
            raise HostEventsBad('invalid host-event identity column bounds')
        if resources.text_enabled(app) and (not isinstance(raw['ValueFormat'], list) or len(raw['ValueFormat']) != cap
                or not isinstance(raw['ValueText'], list) or len(raw['ValueText']) != cap * resources.TEXT_WORDS):
            raise HostEventsBad('invalid host-event text column bounds')
        for offset in range(count):
            slot = (head - count + offset) % cap
            ev = {n: raw[n][slot] for n in COLUMNS}
            kind = ev['Kind']
            supported = (*SUPPORTED, *((1, 2, 3, 4) if app.part_carrier is not None else ()),
                         *((7, 8) if resources.enabled(app) else ()))
            if (ev['Sequence'] != newest - count + offset + 1 or kind not in supported
                    or ev['TimeSynchronized'] not in (0, 1)
                    or (kind == 3 and ev['Verdict'] not in (0,1,2,3))
                    or (kind != 3 and ev['Verdict'] != (2 if kind == 10 else 0))
                    or (ev['Verdict'] == 2 and ev['ReasonCode'] == 0)
                    or (kind == 10 and ev['ReasonCode'] == 0)
                    or (kind not in (3, 4, 10) and ev['ReasonCode'] != 0)):
                raise HostEventsBad('invalid or discontinuous host-event record')
            identity, subject = '', ''
            if schema(app) >= 2:
                import fraktal_ab_part as part
                identity = part.uid(raw['Uid'][slot*64:(slot+1)*64])
                resource = schema(app) >= 3 and kind in (7, 8)
                if bool(identity) != (1 <= kind <= 4 or resource):
                    raise HostEventsBad('part-event identity missing or leaked to non-part event')
                if resource:
                    if len(identity) > 63 or not -2**31 <= ev['Value'] <= LIMIT:
                        raise HostEventsBad('invalid captured resource subject/value')
                    subject, identity = identity, ''
            value = ''
            if kind in (7, 8):
                value = str(ev['Value'])
            elif kind == 9:
                if ev['Value'] not in decl.declared_modes(app):
                    raise HostEventsBad('unknown mode in host event')
                value = str(ev['Value'])
            elif kind in (5, 6):
                index = ev['ModelOrdinal']
                if kind == 5 and index == 0:
                    value = ''  # Start may enter the model-selection wait.
                elif not 1 <= index <= len(codes):
                    raise HostEventsBad('unknown model in host event')
                else:
                    value = codes[index - 1]
            if resources.text_enabled(app):
                format_id = raw['ValueFormat'][slot]
                words = raw['ValueText'][slot*resources.TEXT_WORDS:(slot+1)*resources.TEXT_WORDS]
                if (type(format_id) is not int or format_id not in (0, 1)
                        or any(type(word) is not int or not 0 <= word <= LIMIT for word in words)
                        or (format_id == 1 and (kind not in (7, 8) or ev['Value'] != 0))
                        or (format_id == 0 and any(words))):
                    raise HostEventsBad('invalid captured resource text format/data')
                if format_id == 1:
                    import struct
                    cells = struct.pack('<' + 'i' * resources.TEXT_WORDS, *words)
                    end = cells.find(b'\0')
                    if (not 0 <= end <= resources.TEXT_LIMIT or any(cells[end:])
                            or any(not 32 <= byte <= 126 for byte in cells[:end])):
                        raise HostEventsBad('invalid captured resource text ASCII/termination')
                    value = cells[:end].decode('ascii')
            stamp = projection._controller_time(ev['Date'], ev['Time'])
            if not stamp:
                raise HostEventsBad('host-event timestamp unavailable')
            datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            event = dict(Sequence=ev['Sequence'], Kind=kind, StationPath=app.name,
                               PartUid=identity, Subject=subject, Value=value, Stamp=stamp,
                               TimeSynchronized=bool(ev['TimeSynchronized']),
                               Verdict=ev['Verdict'], ReasonCode=ev['ReasonCode'])
            if genealogy.enabled(app):
                event['Parents'] = genealogy.decode_host(app,raw,slot,kind,identity)
            events.append(event)
        return dict(metadata=m, events=events, **({'genealogyCapacity':genealogy.capacity(app)}
                                                if genealogy.enabled(app) else {}))
    except (KeyError, TypeError, IndexError, ValueError) as error:
        if isinstance(error, HostEventsBad):
            raise
        raise HostEventsBad(f'malformed host-event batch: {error}') from error


def read(comm, app, codes=(), attempts=3):
    """Metadata-bracketed raw read. Torn/failed batches are never cached Good."""
    from fraktal_ab_press_execute import read_layout
    if not app.host_event_capacity:
        return None
    for _ in range(attempts):
        before = read_layout(comm, tag(app), tuple(decl.scalar(n) for n in META))
        raw = read_layout(comm, tag(app), members(app))
        after = read_layout(comm, tag(app), tuple(decl.scalar(n) for n in META))
        if before is None or raw is None or after is None:
            raise HostEventsBad('host-event acquisition failed')
        if before == metadata(raw) == after and after['DataRevision'] % 2 == 0:
            return decode(app, raw, codes)
    raise HostEventsBad('host-event batch changed during every bounded read')


def project(batch):
    if batch is None:
        raise HostEventsBad('host-event batch unavailable')
    m = batch['metadata']
    values = {f'HostEvents/{k}': v for k, v in m.items()}
    values['HostEvents/RingHead'] = m['Head']
    values['HostEvents/Wrapped'] = bool(m['Wrapped'])
    if 'genealogyCapacity' in batch:
        values['HostEvents/GenealogyCapacity'] = batch['genealogyCapacity']
    # The generic HMI walks the physical one-based slots, using Capacity.
    for offset, ev in enumerate(batch['events']):
        slot = ((m['Head'] - m['Count'] + offset) % m['Capacity']) + 1
        for field, value in ev.items():
            if field == 'Parents':
                values[f'HostEvents/Ring[{slot}]/ParentCount'] = len(value)
                for index in range(batch['genealogyCapacity']):
                    values[f'HostEvents/Ring[{slot}]/Parents[{index+1}]'] = value[index] if index < len(value) else ''
            else:
                values[f'HostEvents/Ring[{slot}]/{field}'] = value
    return values


def main(argv=None):
    """One serial/build-guarded read into a local JSONL or SQLite sink."""
    import argparse
    import fraktal_ab_station as station
    import fraktal_ab_projection as projection
    import fraktal_ab_manifest as manifest
    import fraktal_ab_manifest_read as reader
    import fraktal_ab_models as models
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='controller IP/path; read-only')
    parser.add_argument('--expect-serial', required=True)
    parser.add_argument('--slot', type=int, default=0)
    parser.add_argument('--cursor', type=Path, required=True, help='dedicated per-sink cursor file')
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument('--output', type=Path, help='append-only local JSONL sink (at least once)')
    outputs.add_argument('--sqlite-output', type=Path, help='local SQLite sink with duplicate exclusion')
    args = parser.parse_args(argv)
    app = station.application()
    if not app.host_event_capacity:
        parser.error('the selected declaration does not enable HostEvents')
    output = args.sqlite_output or args.output
    cursor_files = {args.cursor.resolve(), *(args.cursor.with_name(args.cursor.name + suffix).resolve()
                    for suffix in ('.lock', '.guard', '.pending'))}
    sink_files = {output.resolve()}
    if args.sqlite_output:
        sink_files.update(output.with_name(output.name + suffix).resolve()
                          for suffix in ('-journal', '-wal', '-shm'))
    if cursor_files & sink_files:
        parser.error('cursor, its companions and sink files must be different')
    # Check declaration bounds before opening any controller connection.
    decl.require_valid(app)
    from pylogix import PLC
    with PLC() as comm:
        comm.IPAddress, comm.ProcessorSlot = args.target, args.slot
        serial, valid = projection.verify_serial(comm, args.expect_serial)
        if not valid:
            raise HostEventsBad('controller serial does not match')
        before, status, _ = reader._read_raw(comm, manifest.header_tag(app))
        if before is None:
            raise HostEventsBad('manifest acquisition failed: ' + status)
        projection.validate(reader.decode_header(before))
        batch = read(comm, app, models.read(comm, app))
        after, _, _ = reader._read_raw(comm, manifest.header_tag(app))
        if after != before:
            raise HostEventsBad('manifest changed during host-event acquisition')
    # The published LegacyContentHash, as the Dart adapter keys its cursor (O12).
    source = f'{serial}:{__import__("fraktal_ab_document_revision").identity(app)}'
    cursor = Cursor(app.name, args.cursor, source=source)
    if args.sqlite_output:
        from fraktal_ab_host_sink import SqliteSink
        with SqliteSink(output, app.name, source=source) as sink:
            return 0 if cursor.deliver(batch, sink) else 1
    with args.output.open('a', encoding='utf-8') as out:
        def sink(record):
            out.write(json.dumps(record, sort_keys=True) + '\n')
            out.flush()
            os.fsync(out.fileno())
            return True
        return 0 if cursor.deliver(batch, sink) else 1


if __name__ == '__main__':
    raise SystemExit(main())
