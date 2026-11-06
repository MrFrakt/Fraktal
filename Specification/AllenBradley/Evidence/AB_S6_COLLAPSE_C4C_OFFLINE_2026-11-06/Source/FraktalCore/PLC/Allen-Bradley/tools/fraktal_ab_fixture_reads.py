"""O10 apparatus views, preserving harness keys and predicates during C4.

Published facts are exact leaf aliases; private facts are the acceptance
fixture's native values, co-read under the same scan generation. No lifecycle,
diagnostic, timestamp or count is reconstructed. Other harnesses must account
their own facts before selecting the collapsed profile. Legacy declarations
keep the legacy-baseline reader until its retirement.
"""
from fraktal_ab_canonical_reader import open_row_reader
from fraktal_ab_legacy_reads import read_layout


UNIT_PUBLIC = dict(Mode='ModeActivePublished', Step='CurrentStep/StepNo',
                   DecisionAnswer='Decision/Default', GoodCount='GoodCount',
                   ScrapCount='NokCount', ReworkCount='ReworkCount', RunStyle='RunStyle')
CHART_PUBLIC = dict(CurrentStepMs='CurrentStepElapsed')


class FixtureReads:
    def __init__(self, app, reader):
        if not app.canonical_collapse or not app.fixture_observation or reader is None:
            raise ValueError('collapsed harness requires its accounted O10 fixture')
        self.root, self.reader = app.name, reader
        self.symbol = f'FRK_{app.name}_FixtureObservation'
        self.fields = dict(app.fixture_observation)
        self.modules = {module.name for module in app.modules}

    def surface(self, name):
        if name not in ('Unit', 'Chart') and name not in self.modules:
            raise ValueError('unknown fixture surface: ' + name)
        public = UNIT_PUBLIC if name == 'Unit' else CHART_PUBLIC if name == 'Chart' else {
            'OutImm_ExecState': name + '/Status/State'}
        # A canonical anchor makes even a private-only surface a scan-domain row.
        paths = tuple(dict.fromkeys([self.root + '/CurrentStep/StepNo',
                                     *(self.root + '/' + path for path in public.values())]))
        row = self.reader.read_row(paths, private=(self.symbol,))
        native = row['private'][self.symbol]
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
    session = FixtureReads(app, reader)
    comm._fraktal_fixture_reads = session
    return session


def _session(comm, app):
    if not app.canonical_collapse:
        return None
    session = getattr(comm, '_fraktal_fixture_reads', None)
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
