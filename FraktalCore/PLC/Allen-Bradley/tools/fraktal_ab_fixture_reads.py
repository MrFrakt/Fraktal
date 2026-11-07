"""O10 apparatus views and O11 commands, preserving acceptance predicates.

Published facts are exact leaf aliases; private facts are the acceptance
fixture's native values, co-read under the same scan generation. No lifecycle,
diagnostic, timestamp or count is reconstructed. Other harnesses must account
their own facts before selecting the collapsed profile. Legacy declarations
keep the legacy-baseline reader until its retirement.
"""
from fraktal_ab_canonical_reader import open_row_reader
from fraktal_ab_legacy_reads import read_layout
from fraktal_ab_harness_gateway import connection_state
from contextlib import contextmanager


UNIT_PUBLIC = dict(Mode='ModeActivePublished', Step='CurrentStep/StepNo',
                   DecisionAnswer='Decision/Default', GoodCount='GoodCount',
                   ScrapCount='NokCount', ReworkCount='ReworkCount', RunStyle='RunStyle')
CHART_PUBLIC = dict(CurrentStepMs='CurrentStepElapsed')
# The legacy mailbox keeps its own ACK in the V6.6 adapter. It is not an
# alias of the Core ACK; only its asserted numeric diagnostic is an O10 fact.
MAILBOX_PUBLIC = {}
DEFAULT_GATEWAY = 'ws://127.0.0.1:8080/fraktal'

def public_aliases(name):
    if name in ('ConfigAudit', 'Oee', 'Profiler', 'SetState', 'Persist', 'AccessState', 'AccessAudit', 'AlarmActive', 'AlarmRing', 'ReleaseStart') or name.startswith('Cfg') and name[3:].isdigit():
        return {}
    if name in ('Door', 'PartSlide', 'PressRam'):
        return {'OutImm_ExecState': name + '/Status/State',
                'TimCount': tuple(f'{name}/Timing/Rows[{i}]/Count' for i in range(1, 3)),
                'TimLast': tuple(f'{name}/Timing/Rows[{i}]/Last' for i in range(1, 3))}
    return UNIT_PUBLIC if name == 'Unit' else CHART_PUBLIC if name == 'Chart' else MAILBOX_PUBLIC if name == 'Mailbox' else {
        'OutImm_ExecState': name + '/Status/State'}


class FixtureReads:
    def __init__(self, app, reader, *, expected_serial=None):
        if not app.canonical_collapse or not app.fixture_observation or reader is None:
            raise ValueError('collapsed harness requires its accounted O10 fixture')
        self.root, self.reader = app.name, reader
        self.expected_serial = expected_serial
        self.symbol = f'FRK_{app.name}_FixtureObservation'
        self.fields = dict(app.fixture_observation)
        self.modules = {module.name for module in app.modules}

    def surface(self, name):
        if name not in self.fields and name not in ('Unit', 'Chart', 'Mailbox') and name not in self.modules:
            raise ValueError('unknown fixture surface: ' + name)
        public = public_aliases(name) if name in ('Unit', 'Chart', 'Mailbox') or name in self.modules else {}
        # A canonical anchor makes even a private-only surface a scan-domain row.
        flat_public = tuple(p for path in public.values() for p in (path if isinstance(path, tuple) else (path,)))
        paths = tuple(dict.fromkeys([self.root + '/CurrentStep/StepNo',
                                     *(self.root + '/' + path for path in flat_public)]))
        members = tuple(name + '_' + member for member in self.fields.get(name, ()))
        row = self.reader.read_row(paths, private={self.symbol: members} if members else ())
        native = row['private'].get(self.symbol, {})
        result = {member: native[name + '_' + member] for member in self.fields.get(name, ())}
        result.update({member: ([row['values'][self.root + '/' + p] for p in path]
                                if isinstance(path, tuple) else row['values'][self.root + '/' + path])
                       for member, path in public.items()})
        if name == 'Door':
            # The press's report-only key is explicitly unavailable until a
            # harness that asserts it accounts it in O10. Never invent zero.
            result.setdefault('RunCount', None)
        return result


def bind(comm, app, expect_serial):
    """Called after the fixture's exact-identity guard, before its fingerprint."""
    if not app.canonical_collapse:
        return None
    if not expect_serial:
        raise ValueError('fixture reader needs the guarded expected serial')
    comm.ConnectionSize = 4000
    reader = open_row_reader(comm, expect_serial=expect_serial)
    if reader is None:
        # A collapsed acceptance profile cannot identify its fixture on a legacy
        # image. Its ordinary baseline harness still uses the legacy declaration.
        raise ValueError('collapsed fixture is absent; nothing written')
    session = FixtureReads(app, reader, expected_serial=expect_serial)
    connection_state(comm)._fraktal_fixture_reads = session
    return session


def _session(comm, app):
    if not app.canonical_collapse:
        return None
    session = getattr(connection_state(comm), '_fraktal_fixture_reads', None)
    if session is None:
        # The existing Guarded wrapper already owns the exact deployment pin.
        pin = getattr(comm, 'serial', None)
        if type(pin) is int:
            session = bind(comm, app, f'{pin:08X}')
        else:
            raise ValueError('bind the guarded fixture reader before reading its state')
    return session


def read_unit(comm, *, app):
    session = _session(comm, app)
    if session is not None:
        return session.surface('Unit')
    import fraktal_ab_generate as gen
    return read_layout(comm, f'FRK_{app.name}_Unit', gen.unit_context_members(app))


def read_chart(comm, *, app):
    session = _session(comm, app)
    if session is not None:
        return session.surface('Chart')
    import fraktal_ab_generate as gen
    return read_layout(comm, f'FRK_{app.name}_Chart', gen.chart_members(app))


def read_module(comm, name, *, app):
    session = _session(comm, app)
    if session is not None:
        return session.surface(name)
    import fraktal_ab_generate as gen
    module = next(m for m in app.modules if m.name == name)
    return read_layout(comm, gen.ctx_tag_for(app, name), gen.module_members(module, app))


def numeric_key(comm, text, *, app):
    """An asserted refusal key belongs to the deployed image's own key table."""
    session = _session(comm, app)
    if session is not None:
        try:
            return session.reader.command_keys(session.root)[text]
        except KeyError as error:
            raise ValueError('asserted key is absent from the published command metadata') from error
    import fraktal_ab_manifest as legacy
    return legacy.numeric_key(app, text)


def surface(comm, name, *, app):
    session = _session(comm, app)
    if session is None:
        raise ValueError('accounted surface requires the collapsed fixture')
    return session.surface(name)


def read_access(comm, *, app, audit=False):
    if app.canonical_collapse:
        return surface(comm, 'AccessAudit' if audit else 'AccessState', app=app)
    import fraktal_ab_projection as legacy
    return legacy.read_access(comm, audit=audit)


def part_identity(comm, *, app):
    """Only the two live leaves used by held/abort waits; UID is PLC text."""
    if not app.canonical_collapse:
        import fraktal_ab_part as legacy
        raw = legacy.read(comm, app)
        return dict(Present=raw['Present'], Uid=legacy.uid(raw['Uid']))
    paths = (app.name + '/Part/Present', app.name + '/Part/Uid')
    held = values(comm, paths, app=app)
    return dict(Present=held[paths[0]], Uid=held[paths[1]])


def part_values(comm, *, app):
    """The Part result as published; no UID, tolerance or timestamp projection."""
    if not app.canonical_collapse:
        import fraktal_ab_part as legacy
        return legacy.project(app, legacy.read(comm, app))
    if app.part_carrier is None:
        raise ValueError('Part fixture requires a declared carrier')
    names = ['Uid', 'Present', 'CarrierKind', 'Result/Verdict', 'Result/ReasonCode',
             'Result/StationPath', 'Result/TimeSynchronized', 'Result/Stamp']
    if app.part_carrier.genealogy_capacity:
        names += ['ParentCapacity', 'ParentCount', *(f'Parents[{i}]'
                  for i in range(1, app.part_carrier.genealogy_capacity + 1))]
    names += [f'Result/Records[{i}]/{leaf}'
              for i in range(1, app.part_carrier.result_capacity + 1)
              for leaf in ('Name', 'Unit', 'Value', 'Minimum', 'Maximum', 'Target', 'InTol')]
    prefix = app.name + '/'
    held = values(comm, (prefix + 'Part/' + name for name in names), app=app)
    return {path[len(prefix):]: value for path, value in held.items()}


def host_events(comm, *, app, attempts=3):
    """Alias the PLC-formatted canonical ring into the fixture's batch shape.

    The ring has its own V6.11 owner revision. Only occupied slots are read;
    a changed planning header retries within the original three-read bound.
    Strings, times, resource values and parents come directly from the PLC.
    """
    if not app.canonical_collapse:
        import fraktal_ab_host_events as legacy
        return legacy.read(comm, app, tuple(m.code for m in app.models), attempts=attempts)
    from fraktal_ab_host_cursor import META, validate_metadata
    from fraktal_ab_host_service_binding import SERVICES
    from datetime import datetime
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError('host fixture acquisition exceeds its original attempt bound')
    session = _session(comm, app)
    bindings = [b for b in session.reader._manifest.get('hostServiceBindings', [])
                if b['RootSymbol'] == session.root and b['Service'] == SERVICES['HostEvents']]
    if len(bindings) != 1 or bindings[0]['CanonicalRoot'] != session.root + '/HostEvents':
        raise ValueError('fixture requires the published read-only host ring')
    prefix = session.root + '/HostEvents/'
    fields = ('Sequence', 'Kind', 'StationPath', 'PartUid', 'Subject', 'Value',
              'Stamp', 'TimeSynchronized', 'Verdict', 'ReasonCode')
    parent_capacity = app.part_carrier.genealogy_capacity if app.part_carrier else 0
    headers = (*META, 'RingHead', *(('GenealogyCapacity',) if parent_capacity else ()))
    paths = tuple(prefix + name for name in headers)
    for _ in range(attempts):
        before = values(comm, paths, app=app)
        def metadata(held):
            if type(held[prefix + 'Wrapped']) is not bool:
                raise ValueError('host ring Wrapped is not a published Boolean')
            return {name: int(held[prefix + name]) if name == 'Wrapped' else held[prefix + name]
                    for name in META}
        meta = metadata(before)
        capacity, count, head, newest = validate_metadata(meta)
        if before[prefix + 'RingHead'] != head or parent_capacity and before[prefix + 'GenealogyCapacity'] != parent_capacity:
            raise ValueError('host ring extent/head differs from its published metadata')
        slots = [(head - count + i) % capacity + 1 for i in range(count)]
        leaves = (*fields, *(('ParentCount', *(f'Parents[{i}]' for i in range(1, parent_capacity + 1)))
                            if parent_capacity else ()))
        held = values(comm, (*paths, *(f'{prefix}Ring[{i}]/{name}' for i in slots for name in leaves)), app=app)
        if any(held[path] != before[path] for path in paths):
            continue
        events = []
        for offset, slot in enumerate(slots):
            stem = f'{prefix}Ring[{slot}]/'
            event = {name: held[stem + name] for name in fields}
            if event['Sequence'] != newest - count + offset + 1 or event['StationPath'] != session.root:
                raise ValueError('host event interval or station differs')
            kind, verdict, reason = (event[n] for n in ('Kind', 'Verdict', 'ReasonCode'))
            if (any(type(event[n]) is not int for n in ('Sequence', 'Kind', 'Verdict', 'ReasonCode'))
                    or not 1 <= kind <= 10 or type(event['TimeSynchronized']) is not bool
                    or kind == 3 and verdict not in (0, 1, 2, 3)
                    or kind != 3 and verdict != (2 if kind == 10 else 0)
                    or (verdict == 2 or kind == 10) and reason == 0
                    or kind not in (3, 4, 10) and reason != 0
                    or any(not isinstance(event[n], str) for n in ('StationPath', 'PartUid', 'Subject', 'Value', 'Stamp'))):
                raise ValueError('invalid canonical host event semantics')
            if bool(event['PartUid']) != (meta['SchemaVersion'] >= 2 and 1 <= kind <= 4) \
                    or bool(event['Subject']) != (meta['SchemaVersion'] >= 3 and kind in (7, 8)):
                raise ValueError('host event identity leaked or is missing')
            if not event['Stamp'].endswith('Z'):
                raise ValueError('host event timestamp unavailable')
            datetime.fromisoformat(event['Stamp'].replace('Z', '+00:00'))
            if parent_capacity:
                n = held[stem + 'ParentCount']
                parents = [held[stem + f'Parents[{i}]'] for i in range(1, parent_capacity + 1)]
                if (type(n) is not int or not 0 <= n <= parent_capacity or n and not 1 <= kind <= 4
                        or any(not isinstance(p, str) or not p for p in parents[:n]) or any(parents[n:])):
                    raise ValueError('host parent slots differ from their count')
                event['Parents'] = parents[:n]
            events.append(event)
        return dict(metadata=meta, events=events, **(dict(genealogyCapacity=parent_capacity) if parent_capacity else {}))
    raise ValueError('host ring changed during every bounded fixture acquisition')


def read_alarm_log(comm, *, app):
    if app.canonical_collapse:
        return surface(comm, 'AlarmActive', app=app), surface(comm, 'AlarmRing', app=app)
    import fraktal_ab_projection as legacy
    return legacy.read_alarm_log(comm)


def read_oee(comm, *, app):
    if app.canonical_collapse:
        return surface(comm, 'Oee', app=app)
    import fraktal_ab_generate as gen
    return read_layout(comm, gen.oee_tag(app), gen.oee_members())


def read_profiler(comm, *, app):
    if app.canonical_collapse:
        return surface(comm, 'Profiler', app=app)
    import fraktal_ab_generate as gen
    return read_layout(comm, gen.profiler_tag(app), gen.profiler_members(app))


OEE_LEAVES = ('RunMs', 'DownMs', 'IdleMs', 'Availability', 'AvailValid', 'Performance',
              'PerfValid', 'Quality', 'QualValid', 'Oee', 'OeeValid')
HEALTH_LEAVES = ('Present', 'Healthy', 'TaskAvailable', 'TaskCycleUs', 'TaskJitterUs',
                 'TaskOverrun', 'ControllerAvailable', 'CpuLoadPct', 'MemoryAvailableMb',
                 'IpcAvailable', 'IpcTemperatureC', 'FanHealthy', 'StorageHealthPct',
                 'FieldbusAvailable', 'FieldbusMasterHealthy', 'LostFrameCount',
                 'SlaveErrorCount', 'DcAvailable', 'DcSynchronized',
                 'TimeQuality/Available', 'TimeQuality/Synchronized',
                 'TimeQuality/Source', 'TimeQuality/OffsetUs')


def oee_card(comm, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        prefix = f'{app.name}/'
        return {k[len(prefix):]: v for k, v in held.items() if k.startswith(f'{prefix}Oee')}
    import fraktal_ab_generate as gen
    root = session.root
    paths = (*(f'{root}/Oee/{n}' for n in OEE_LEAVES), f'{root}/OeeTrendHead',
             *(f'{root}/OeeTrend[{i}]/{n}' for i in range(1, gen.OEE_SAMPLES + 1) for n in ('Oee', 'OeeValid')))
    held = values(comm, paths, app=app)
    prefix = root + '/'
    return {k[len(prefix):]: v for k, v in held.items()}


def machine_summary(comm, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        return held.get(f'{app.name}/MachineState'), held.get(f'{app.name}/ReworkCount')
    paths = (f'{session.root}/MachineState', f'{session.root}/ReworkCount')
    held = values(comm, paths, app=app)
    return held[paths[0]], held[paths[1]]


def run_style_offer(comm, *, app):
    import fraktal_ab_declaration as decl
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        return [held.get(f'{app.name}/SupportedRunStylesPublished[{s + 1}]') for s in decl.RUN_STYLES], held.get(f'{app.name}/RunStyle')
    paths = (*(f'{session.root}/SupportedRunStylesPublished[{s}]' for s in decl.RUN_STYLES), f'{session.root}/RunStyle')
    held = values(comm, paths, app=app)
    return [held[f'{session.root}/SupportedRunStylesPublished[{s}]'] for s in decl.RUN_STYLES], held[f'{session.root}/RunStyle']


def profiler_summary(comm, *, app):
    import fraktal_ab_declaration as decl
    import fraktal_ab_generate as gen
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        return legacy.read_document(comm)['values']
    root = session.root
    base = f'{root}/Profiler/LastCycle'
    step_leaves = ('StepNo', 'StepName', 'TimeClass', 'Duration', 'Expected')
    hist_leaves = ('CycleNo', 'Total', 'WorkTime', 'WaitTime', *(f'ByClass[{k}]' for k in range(len(decl.TIME_CLASSES))))
    paths = (*(f'{base}/{n}' for n in ('CycleNo', 'NSteps', 'Total', 'WorkTime', 'WaitTime')),
             f'{root}/Profiler/LastCycleTime', f'{root}/Profiler/HistoryHead',
             *(f'{base}/Steps[{i}]/{n}' for i in range(1, gen.PROFILE_STEPS + 1) for n in step_leaves),
             *(f'{root}/Profiler/History[{i}]/{n}' for i in range(1, gen.CYCLE_HISTORY + 1) for n in hist_leaves))
    return values(comm, paths, app=app)


def timing_row(comm, module, index=1, *, app):
    leaves = ('Id', 'Label', 'Count', 'Last', 'Minimum', 'Maximum', 'Avg')
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        return {n: held.get(f'{app.name}/{module}/Timing/Rows[{index}]/{n}') for n in leaves}
    paths = tuple(f'{session.root}/{module}/Timing/Rows[{index}]/{n}' for n in leaves)
    held = values(comm, paths, app=app)
    return {n: held[f'{session.root}/{module}/Timing/Rows[{index}]/{n}'] for n in leaves}


def alarm_ring_entry(comm, slot, *, app):
    if not slot:
        return {}
    leaves = ('ReasonCode', 'SourcePath')
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        return {n: held.get(f'{app.name}/AlarmLog/Ring[{slot}]/{n}') for n in leaves}
    paths = tuple(f'{session.root}/AlarmLog/Ring[{slot}]/{n}' for n in leaves)
    held = values(comm, paths, app=app)
    return {n: held[f'{session.root}/AlarmLog/Ring[{slot}]/{n}'] for n in leaves}


def state_flags(comm, *, app):
    leaves = ('Key', 'Value', 'Since', 'Stale')
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        count = held.get(f'{app.name}/StateFlagCount') or 0
        return [{n: held.get(f'{app.name}/StateFlags[{i}]/{n}') for n in leaves} for i in range(1, count + 1)]
    count_path = f'{session.root}/StateFlagCount'
    count = values(comm, (count_path,), app=app)[count_path]
    if type(count) is not int or not 0 <= count <= len(app.state_flags):
        raise ValueError('invalid published state flag count')
    paths = (count_path, *(f'{session.root}/StateFlags[{i}]/{n}' for i in range(1, count + 1) for n in leaves))
    held = values(comm, paths, app=app)
    if held[count_path] != count:
        raise ValueError('state flag count changed')
    return [{n: held[f'{session.root}/StateFlags[{i}]/{n}'] for n in leaves} for i in range(1, count + 1)]


def system_health(comm, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        held = legacy.read_document(comm)['values']
        prefix = f'{app.name}/SystemHealth/'
        return {k[len(prefix):]: v for k, v in held.items() if k.startswith(prefix)}
    paths = tuple(f'{session.root}/SystemHealth/{n}' for n in HEALTH_LEAVES)
    held = values(comm, paths, app=app)
    prefix = f'{session.root}/SystemHealth/'
    return {k[len(prefix):]: v for k, v in held.items()}


def config_capability(comm, key, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_mailbox as legacy
        return legacy.config_ordinal(app, key)
    try:
        return session.reader.command_capabilities(session.root)[key]
    except KeyError as error:
        raise ValueError('asserted configuration key has no published capability') from error


def class_levels(comm, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_projection as legacy
        import fraktal_ab_data_access as data
        import fraktal_ab_manifest as manifest
        held = data.policy_status(app, manifest.content(app), legacy.read_data_access(comm, policy=True))
        return {held[f'Access/Classes[{i}]/ClassId']: {
            'read': held[f'Access/Classes[{i}]/ReadLevel'], 'write': held[f'Access/Classes[{i}]/WriteLevel']}
            for i in range(1, held['Access/ClassCount'] + 1)}
    count_path = session.root + '/Access/ClassCount'
    count = values(comm, (count_path,), app=app)[count_path]
    if type(count) is not int or not 0 <= count <= 10000:
        raise ValueError('invalid published access class count')
    names = ('ClassId', 'ReadLevel', 'WriteLevel')
    paths = (count_path, *(f'{session.root}/Access/Classes[{i}]/{n}' for i in range(1, count + 1) for n in names))
    held = values(comm, paths, app=app)
    if held[count_path] != count:
        raise ValueError('access class count changed')
    result = {}
    for i in range(1, count + 1):
        identity, read, write = (held[f'{session.root}/Access/Classes[{i}]/{n}'] for n in names)
        if not isinstance(identity, str) or not identity or identity in result or any(type(v) is not int or not 0 <= v <= 4 for v in (read, write)):
            raise ValueError('invalid or duplicate access class')
        result[identity] = dict(read=read, write=write)
    return result


def alarm_descriptions(comm, slots, *, app):
    # Each text is a separate row proof; there is no whole-history certificate.
    session = _session(comm, app)
    if session is None:
        raise ValueError('canonical history requires the collapsed fixture')
    result = {}
    for slot in slots:
        if type(slot) is not int or slot < 0:
            raise ValueError('invalid native audit slot')
        suffix = f'AlarmLog/Ring[{slot + 1}]/Description'
        path = session.root + '/' + suffix
        result[suffix] = values(comm, (path,), app=app)[path]
    return result


def configuration_entries(comm, *, app, keys=None):
    """Active-bank definitions and masked text, read independently from the PLC."""
    from fraktal_ab_canonical_reader import MAX_LEAVES
    session = _session(comm, app)
    bindings = [b for b in session.reader._manifest.get('readServices', [])
                if b['RootSymbol'] == session.root and b['Kind'] == 1 and b['Version'] == 1]
    if len(bindings) != 1:
        raise ValueError('fixture requires one published configuration view')
    prefix = bindings[0]['CanonicalRoot']
    names = ('SchemaVersion', 'RootIdentity', 'Revision', 'DefinitionCount', 'ValueCount')
    header = values(comm, (prefix + '/' + n for n in names), app=app)
    definitions, total = header[prefix + '/DefinitionCount'], header[prefix + '/ValueCount']
    if header[prefix + '/SchemaVersion'] != 1 or header[prefix + '/RootIdentity'] != session.root \
            or type(definitions) is not int or type(total) is not int or not 0 < definitions <= total <= 65535 \
            or 5 + definitions * 5 + total * 5 > MAX_LEAVES:
        raise ValueError('invalid configuration view identity/counts')
    fields = ('DefinitionIndex', 'WriteKey', 'ClassId', 'ReadLevel', 'WriteLevel')
    row_fields = ('DefinitionIndex', 'ModelOrdinal', 'ValueText', 'Readable', 'Revision')
    # Static key/ordinal directories select only the values this caller consumes.
    key_paths = tuple(f'{prefix}/Definitions[{i}]/WriteKey' for i in range(definitions))
    directory_keys = values(comm, key_paths, app=app)
    by_key = {}
    for i, path in enumerate(key_paths):
        key = directory_keys[path]
        if not isinstance(key, str) or not key or key in by_key:
            raise ValueError('invalid or duplicate configuration key directory')
        by_key[key] = i
    wanted = set(by_key) if keys is None else set(keys)
    if not wanted or not wanted <= set(by_key):
        raise ValueError('asserted configuration key absent from its published view')
    wanted_indices = {by_key[key] for key in wanted}
    # Discover active-bank addresses from published ordinals. Other banks'
    # ValueText/Readable payloads are never acquired by this fixture view.
    directory = values(comm, (f'{prefix}/Values[{i}]/{n}' for i in range(total)
                              for n in ('DefinitionIndex', 'ModelOrdinal')), app=app)
    active = []
    for i in range(total):
        index, bank = (directory[f'{prefix}/Values[{i}]/{n}'] for n in ('DefinitionIndex', 'ModelOrdinal'))
        if type(index) is not int or not 0 <= index < definitions or type(bank) is not int or bank < 0:
            raise ValueError('invalid configuration bank directory')
        if bank == 0 and index in wanted_indices:
            active.append((i, index))
    if sorted(index for _, index in active) != sorted(wanted_indices):
        raise ValueError('active configuration directory is incomplete or duplicated')
    paths = (*(prefix + '/' + n for n in names),
             *(f'{prefix}/Definitions[{i}]/{n}' for i in sorted(wanted_indices) for n in fields),
             *(f'{prefix}/Values[{i}]/{n}' for i, _ in active for n in row_fields))
    held = values(comm, paths, app=app)
    if any(held[prefix + '/' + n] != header[prefix + '/' + n] for n in names):
        raise ValueError('configuration changed while planning its entries')
    result, indices = {}, {}
    for i in sorted(wanted_indices):
        row = {n: held[f'{prefix}/Definitions[{i}]/{n}'] for n in fields}
        key = row.pop('WriteKey')
        if row.pop('DefinitionIndex') != i or key != directory_keys[f'{prefix}/Definitions[{i}]/WriteKey'] or key in result:
            raise ValueError('invalid or duplicate configuration definition')
        if not isinstance(row['ClassId'], str) or any(type(row[n]) is not int or not 0 <= row[n] <= 4 for n in ('ReadLevel', 'WriteLevel')):
            raise ValueError('invalid configuration access metadata')
        result[key] = dict(WriteKey=key, **row)
        indices[i] = key
    selected = set()
    for i, planned_index in active:
        row = {n: held[f'{prefix}/Values[{i}]/{n}'] for n in row_fields}
        if row['Revision'] != header[prefix + '/Revision'] or row['ModelOrdinal'] != 0 or row['DefinitionIndex'] != planned_index:
            raise ValueError('configuration values cross a revision/bank change')
        index = row['DefinitionIndex']
        if index not in indices or index in selected or type(row['Readable']) is not bool \
                or not isinstance(row['ValueText'], str) or not row['Readable'] and row['ValueText'] != '':
            raise ValueError('invalid or duplicate active configuration value')
        selected.add(index)
        result[indices[index]].update(Readable=row['Readable'], ValueText=row['ValueText'])
    if selected != set(indices):
        raise ValueError('active configuration values are incomplete')
    return result


def read_records(comm, *, app):
    session = _session(comm, app)
    if session is None:
        raise ValueError('canonical records require the collapsed fixture')
    result = {}
    for index, record in enumerate(app.records):
        name = f'Cfg{index}'
        if set(session.fields.get(name, ())) != {m.name for m in record.members}:
            raise ValueError('record comparison requires every original native member accounted in O10')
        result[record.name] = session.surface(name)
    return result


def values(comm, paths, *, app):
    """An independent canonical row; no projection or gateway value cache."""
    session = _session(comm, app)
    if session is None:
        raise ValueError('canonical values require the collapsed fixture')
    return session.reader.read_row(tuple(paths))['values']


def revision(comm, *, app):
    session = _session(comm, app)
    if session is None:
        import fraktal_ab_manifest as legacy
        return legacy.config_revision(app)
    path = session.root + '/Status/ConfigRev'
    return session.reader.read_row((path,))['values'][path]


def capture_definition(comm, key, *, app):
    """Read the PLC's read-only definition view, independently of the gateway."""
    session = _session(comm, app)
    bindings = [b for b in session.reader._manifest.get('readServices', [])
                if b['RootSymbol'] == session.root and b['Kind'] == 1 and b['Version'] == 1]
    if len(bindings) != 1:
        raise ValueError('fixture requires one published configuration view')
    prefix = bindings[0]['CanonicalRoot']
    count_path = prefix + '/DefinitionCount'
    count = session.reader.read_row((count_path,))['values'][count_path]
    if type(count) is not int or not 0 < count <= 32767:
        raise ValueError('invalid published definition count')
    names = ('WriteKey', 'CaptureSource', 'CanCapture')
    paths = (count_path, *(f'{prefix}/Definitions[{i}]/{name}'
                          for i in range(count) for name in names))
    values = session.reader.read_row(paths)['values']
    if values[count_path] != count:
        raise ValueError('configuration definition count changed')
    found = [{name: values[f'{prefix}/Definitions[{i}]/{name}'] for name in names}
             for i in range(count) if values[f'{prefix}/Definitions[{i}]/WriteKey'] == key]
    if len(found) != 1:
        raise ValueError('capture key absent or ambiguous in published definitions')
    return found[0]


@contextmanager
def viewer(comm, *, app):
    """A separate, owned read-only deployment of the same pinned gateway."""
    from fraktal_ab_harness_gateway import GatewayLease
    from fraktal_ab_harness_commands import GatewayCommands
    session = _session(comm, app)
    _guard_command(comm, session)
    prepared = connection_state(comm)._fraktal_gateway_lease
    with GatewayLease(prepared.executable, prepared.digest, host=comm.IPAddress,
                      slot=comm.ProcessorSlot, serial=session.expected_serial,
                      root=session.root, directory=prepared.directory, read_only=True) as lease:
        if not lease.guard(serial=session.expected_serial, root=session.root, url=lease.url):
            raise ValueError('read-only gateway target binding changed')
        client = GatewayCommands(lease.url)
        try:
            yield client
        finally:
            client.close()


class _CommandRows:
    """One request's coherent observations, including its asserted numeric key."""
    def __init__(self, session):
        self.session, self.last = session, None

    def read_row(self, paths):
        self.last = self.session.reader.read_row(paths, private={self.session.symbol: ('Mailbox_DiagnosticKey',)})
        return self.last


def _guard_command(comm, session):
    if session.expected_serial is None or 'DiagnosticKey' not in session.fields.get('Mailbox', ()):
        raise ValueError('commands require the guarded O10 mailbox observation')
    guard = getattr(comm, 'guard', None)
    if callable(guard):
        guard()
    identity = comm.GetDeviceProperties()
    if identity.Status != 'Success' or identity.Value is None or \
            int(str(identity.Value.SerialNumber), 0) != int(session.expected_serial, 16):
        raise ValueError('controller identity changed before gateway command')
    state = connection_state(comm)
    gateway_guard = getattr(state, '_fraktal_gateway_guard', None)
    if gateway_guard is None:
        import fraktal_ab_harness_gateway as launched
        try:
            launched.bind(comm, session)
        except ValueError as error:
            raise ValueError('a pinned gateway target binding is required before command') from error
        gateway_guard = getattr(state, '_fraktal_gateway_guard', None)
    if not callable(gateway_guard) or gateway_guard(serial=session.expected_serial, root=session.root,
            url=getattr(state, '_fraktal_gateway_url', DEFAULT_GATEWAY)) is not True:
        raise ValueError('a pinned gateway target binding is required before command')


def controls(comm, *, app):
    session = _session(comm, app)
    if session is None:
        raise ValueError('canonical command observation requires the collapsed profile')
    root = session.root
    paths = (root+'/HmiRequest/Sequence', root+'/HmiResponse/AckSequence',
             root+'/HmiResponse/Accepted', root+'/HmiResponse/Diagnostic')
    row = _CommandRows(session).read_row(paths)
    v = row['values']
    return dict(sequence=v[paths[0]] & 0xffffffff, ack=v[paths[1]] & 0xffffffff,
                accepted=bool(v[paths[2]]), diagnosticKey=row['private'][session.symbol]['Mailbox_DiagnosticKey'])


def command(comm, kind, *, app, settle, **arguments):
    """The gateway writes; the apparatus observes independently over CIP.

    Each explicit command owns a client that closes after this request. There
    is no retry, queued request or native-CIP fallback. A later explicit cleanup
    request must first observe a settled controller acknowledgement of its own.
    """
    import fraktal_ab_harness_commands as gateway
    session = _session(comm, app)
    if session is None:
        raise ValueError('canonical commands require the collapsed profile')
    arguments = dict(arguments)
    if type(arguments.get('BoolValue')) is int and arguments['BoolValue'] in (0, 1):
        arguments['BoolValue'] = bool(arguments['BoolValue'])
    # Validation before identity/read/network I/O; this is Core JSON, not a PLC encoder.
    gateway.encode(session.root, 0, dict(Kind=kind, **arguments))
    _guard_command(comm, session)
    observed = _CommandRows(session)
    client = gateway.GatewayCommands(getattr(connection_state(comm), '_fraktal_gateway_url', DEFAULT_GATEWAY))
    try:
        answer = gateway.command(client, observed, session.root, kind, settle=settle, **arguments)
        if not answer['sent']:
            raise AssertionError('gateway refused command before transport: ' + str(answer.get('error')))
        key = observed.last['private'][session.symbol]['Mailbox_DiagnosticKey']
        return dict(sequence=answer['sequence'], accepted=bool(answer['accepted']), diagnosticKey=key)
    finally:
        client.close()
