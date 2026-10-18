"""PLC-owned host events and coherent, acknowledged delivery.

Native AOIs/UDTs supply bounded storage/execution; this adapter supplies the
Core event vocabulary, ordering and loss semantics. It is not an alarm engine.
V1 is non-part; an injected local carrier selects V2 with PLC-captured identities.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import fraktal_ab_declaration as decl

KINDS = dict(PART_RECEIVED=1, PROCESSING_STARTED=2, PROCESSED=3,
             PROCESSING_ABORTED=4, CHANGEOVER_STARTED=5, CHANGEOVER_DONE=6,
             TOOL_CHANGED=7, MATERIAL_CHANGED=8, MODE_CHANGED=9, NOK=10)
SUPPORTED = (5, 6, 9, 10)
LIMIT = 2**31 - 1
COLUMNS = ('Sequence', 'Kind', 'ModelOrdinal', 'Value', 'Date', 'Time',
           'TimeSynchronized', 'Verdict', 'ReasonCode')
META = ('SchemaVersion', 'Head', 'Count', 'Capacity', 'Wrapped',
        'NewestSequence', 'DataRevision', 'EpochLow', 'EpochHigh', 'Failed')


class HostEventsBad(ValueError):
    pass


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
    return 2 if app.part_carrier is not None else 1


def type_name(app):
    return f'FRK_T_HostEvents{app.host_event_capacity}V{schema(app)}'


def emitter_name(app):
    return f'FRK_HostEmit{app.host_event_capacity}V{schema(app)}'


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
         decl.scalar('Uid', dimension=64 * app.host_event_capacity)) if schema(app) == 2 else ())


def emit_logic(app):
    """One owning append algorithm, called from every rendition."""
    assignments = dict(Kind='Kind', ModelOrdinal='ModelOrdinal', Value='EventValue',
                       Date='Ring.NowDate', Time='Ring.NowTime',
                       TimeSynchronized='Ring.NowSynchronized', Verdict='Verdict',
                       ReasonCode='Reason')
    return (
        'IF (Ring.Failed = 0) THEN',
        'IF (Ring.NewestSequence >= 2147483647) OR '
        '(Ring.Capacity <> ' + str(app.host_event_capacity) + ') OR ' +
        ('((Kind < 1) OR ((Kind > 6) AND (Kind <> 9) AND (Kind <> 10))) OR '
         '((Kind = 3) AND ((Verdict < 0) OR (Verdict > 3) OR ((Verdict = 2) AND (Reason = 0)))) OR '
         if schema(app) == 2 else
         '((Kind <> 5) AND (Kind <> 6) AND (Kind <> 9) AND (Kind <> 10)) OR ') +
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
           'IF (Kind >= 1) AND (Kind <= 4) THEN Ring.Uid[UidIndex] := Ring.PendingUid[ByteIndex]; '
           'ELSE Ring.Uid[UidIndex] := 0; END_IF;', 'END_FOR;'] if schema(app) == 2 else []),
        'IF Ring.Count < Ring.Capacity THEN Ring.Count := Ring.Count + 1; '
        'ELSE Ring.Wrapped := 1; END_IF;',
        'Ring.DataRevision := Ring.DataRevision + 1;',
        'END_IF;',
        'END_IF;',
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
                     if schema(app) == 2 else '') + '</LocalTags>')


def call(app, kind, *, in_aoi=False, model='0', value='0', reason=0):
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


def metadata(raw):
    return {n: raw[n] for n in META}


def validate_metadata(m, expected_capacity=None, expected_schema=None):
    try:
        cap, count, head, newest = (m[n] for n in ('Capacity', 'Count', 'Head', 'NewestSequence'))
        if (any(type(m[n]) is not int or not -2**31 <= m[n] <= LIMIT for n in META)
                or m['SchemaVersion'] not in (1, 2) or m['Failed'] != 0
                or expected_schema is not None and m['SchemaVersion'] != expected_schema
                or (expected_capacity is not None and cap != expected_capacity)
                or not 1 <= cap <= 64 or not 0 <= count <= cap or not 0 <= newest <= LIMIT
                or count != min(newest, cap)
                or not 0 <= m['DataRevision'] <= LIMIT or m['DataRevision'] % 2
                or (newest > 0 and m['DataRevision'] == 0)
                or m['Wrapped'] not in (0, 1)
                or (count == 0 and (head != 0 or m['Wrapped']))
                or (count > 0 and head != (newest - 1) % cap + 1)
                or m['Wrapped'] != int(newest > cap)
                or (m['EpochLow'] == 0 and m['EpochHigh'] == 0)):
            raise HostEventsBad('invalid host-event metadata or exhausted publisher')
        return cap, count, head, newest
    except (KeyError, TypeError) as error:
        raise HostEventsBad('host-event metadata incomplete') from error


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
        if schema(app) == 2 and (not isinstance(raw['Uid'], list) or len(raw['Uid']) != cap * 64):
            raise HostEventsBad('invalid host-event identity column bounds')
        for offset in range(count):
            slot = (head - count + offset) % cap
            ev = {n: raw[n][slot] for n in COLUMNS}
            kind = ev['Kind']
            supported = (*SUPPORTED, 1, 2, 3, 4) if schema(app) == 2 else SUPPORTED
            if (ev['Sequence'] != newest - count + offset + 1 or kind not in supported
                    or ev['TimeSynchronized'] not in (0, 1)
                    or (kind == 3 and ev['Verdict'] not in (0,1,2,3))
                    or (kind != 3 and ev['Verdict'] != (2 if kind == 10 else 0))
                    or (ev['Verdict'] == 2 and ev['ReasonCode'] == 0)
                    or (kind == 10 and ev['ReasonCode'] == 0)
                    or (kind not in (3, 4, 10) and ev['ReasonCode'] != 0)):
                raise HostEventsBad('invalid or discontinuous host-event record')
            identity = ''
            if schema(app) == 2:
                import fraktal_ab_part as part
                identity = part.uid(raw['Uid'][slot*64:(slot+1)*64])
                if bool(identity) != (1 <= kind <= 4):
                    raise HostEventsBad('part-event identity missing or leaked to non-part event')
            value = ''
            if kind == 9:
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
            stamp = projection._controller_time(ev['Date'], ev['Time'])
            if not stamp:
                raise HostEventsBad('host-event timestamp unavailable')
            datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            events.append(dict(Sequence=ev['Sequence'], Kind=kind, StationPath=app.name,
                               PartUid=identity, Subject='', Value=value, Stamp=stamp,
                               TimeSynchronized=bool(ev['TimeSynchronized']),
                               Verdict=ev['Verdict'], ReasonCode=ev['ReasonCode']))
        return dict(metadata=m, events=events)
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
    # The generic HMI walks the physical one-based slots, using Capacity.
    for offset, ev in enumerate(batch['events']):
        slot = ((m['Head'] - m['Count'] + offset) % m['Capacity']) + 1
        for field, value in ev.items():
            values[f'HostEvents/Ring[{slot}]/{field}'] = value
    return values


class Cursor:
    """Per-sink acknowledged cursor. Persist only after the sink accepts.

    Delivery is at least once: a crash after the sink accepts but before the
    local replace can repeat an event. Sinks deduplicate the supplied key.
    An epoch change/reset and an overwritten interval are explicit loss records.
    """
    def __init__(self, station, path=None, *, source=''):
        self.station, self.path = station, Path(path) if path is not None else None
        self.source = source
        self.state = dict(schema=1, station=station, source=source, epoch=None, sequence=0)
        if self.path is not None and self.path.exists():
            loaded = json.loads(self.path.read_text(encoding='utf-8'))
            if (loaded.get('schema') != 1 or loaded.get('station') != station
                    or loaded.get('source', '') != source
                    or type(loaded.get('sequence')) is not int or not 0 <= loaded['sequence'] <= LIMIT
                    or not isinstance(loaded.get('epoch'), list) or len(loaded['epoch']) != 2
                    or any(type(v) is not int or not -2**31 <= v <= LIMIT for v in loaded['epoch'])):
                raise HostEventsBad('invalid acknowledged cursor')
            self.state = loaded

    def _commit(self, epoch, sequence):
        state = dict(schema=1, station=self.station, source=self.source, epoch=epoch, sequence=sequence)
        if self.path is not None:
            # Exclusive creation keeps concurrent writers from sharing a cursor.
            temporary = self.path.with_name(self.path.name + '.pending')
            try:
                with temporary.open('x', encoding='utf-8') as out:
                    json.dump(state, out, sort_keys=True)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temporary, self.path)
            finally:
                # Only remove a temporary file this invocation created.
                if 'out' in locals() and temporary.exists():
                    temporary.unlink()
        self.state = state

    def deliver(self, batch, sink):
        if self.path is not None:
            lock = self.path.with_name(self.path.name + '.lock')
            with lock.open('x'):
                pass
            try:
                # A second Cursor instance may have advanced while idle.
                if self.path.exists():
                    self.state = Cursor(self.station, self.path, source=self.source).state
                return self._deliver(batch, sink)
            finally:
                lock.unlink()
        return self._deliver(batch, sink)

    def _deliver(self, batch, sink):
        m, events = batch['metadata'], batch['events']
        validate_metadata(m)
        if not isinstance(events, list) or len(events) != m['Count']:
            raise HostEventsBad('invalid delivery batch bounds')
        for index, event in enumerate(events):
            if (event.get('StationPath') != self.station
                    or type(event.get('Sequence')) is not int
                    or event['Sequence'] != m['NewestSequence'] - len(events) + index + 1):
                raise HostEventsBad('invalid delivery station or sequence interval')
        epoch, seen = [m['EpochLow'], m['EpochHigh']], self.state['sequence']
        if self.state['epoch'] is not None and self.state['epoch'] != epoch:
            record = dict(kind='dataLoss', reason='publisherEpochChanged',
                          previous=self.state.copy(), epoch=epoch)
            if sink(copy.deepcopy(record)) is not True:
                return False
            seen = 0
            self._commit(epoch, seen)
        elif self.state['epoch'] == epoch and m['NewestSequence'] < seen:
            raise HostEventsBad('publisher sequence regressed within its epoch')
        oldest = m['NewestSequence'] - m['Count'] + 1
        if seen + 1 < oldest:
            record = dict(kind='dataLoss', reason='ringOverwritten',
                          firstMissing=seen + 1, lastMissing=oldest - 1, epoch=epoch)
            if sink(copy.deepcopy(record)) is not True:
                return False
            seen = oldest - 1
            self._commit(epoch, seen)
        for event in events:
            if event['StationPath'] != self.station:
                raise HostEventsBad('host-event station differs from sink cursor')
            if event['Sequence'] <= seen:
                continue
            envelope = dict(kind='event', idempotencyKey=[self.source, self.station, *epoch, event['Sequence']],
                            event=copy.deepcopy(event))
            if sink(envelope) is not True:
                return False
            seen = event['Sequence']
            self._commit(epoch, seen)
        return True


def main(argv=None):
    """One serial/build-guarded read, acknowledged into a local JSONL sink."""
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
    parser.add_argument('--output', type=Path, required=True, help='append-only local JSONL sink')
    args = parser.parse_args(argv)
    app = station.application()
    if not app.host_event_capacity:
        parser.error('the selected declaration does not enable HostEvents')
    if args.cursor.resolve() == args.output.resolve():
        parser.error('cursor and output must be different files')
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
    cursor = Cursor(app.name, args.cursor, source=f'{serial}:{manifest.content_hash(app)}')
    with args.output.open('a', encoding='utf-8') as out:
        def sink(record):
            out.write(json.dumps(record, sort_keys=True) + '\n')
            out.flush()
            os.fsync(out.fileno())
            return True
        return 0 if cursor.deliver(batch, sink) else 1


if __name__ == '__main__':
    raise SystemExit(main())
