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


UNIT_PUBLIC = dict(Mode='ModeActivePublished', Step='CurrentStep/StepNo',
                   DecisionAnswer='Decision/Default', GoodCount='GoodCount',
                   ScrapCount='NokCount', ReworkCount='ReworkCount', RunStyle='RunStyle')
CHART_PUBLIC = dict(CurrentStepMs='CurrentStepElapsed')
# The legacy mailbox keeps its own ACK in the V6.6 adapter. It is not an
# alias of the Core ACK; only its asserted numeric diagnostic is an O10 fact.
MAILBOX_PUBLIC = {}
DEFAULT_GATEWAY = 'ws://127.0.0.1:8080/fraktal'

def public_aliases(name):
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
        if name not in ('Unit', 'Chart', 'Mailbox') and name not in self.modules:
            raise ValueError('unknown fixture surface: ' + name)
        public = public_aliases(name)
        # A canonical anchor makes even a private-only surface a scan-domain row.
        paths = tuple(dict.fromkeys([self.root + '/CurrentStep/StepNo',
                                     *(self.root + '/' + path for path in public.values())]))
        members = tuple(name + '_' + member for member in self.fields.get(name, ()))
        row = self.reader.read_row(paths, private={self.symbol: members} if members else ())
        native = row['private'].get(self.symbol, {})
        result = {member: native[name + '_' + member] for member in self.fields.get(name, ())}
        result.update({member: row['values'][self.root + '/' + path] for member, path in public.items()})
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
