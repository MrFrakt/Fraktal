"""O10: the acceptance-only fixture observation (S6 WP6.6 C4).

Once the collapse makes the canonical structures the working storage (WP6.6),
an acceptance harness can no longer read a module's or the Unit's private
facts from a legacy context: there is none. O10 (approved 2026-11-03) gives
an acceptance declaration one Read Only structure carrying exactly the
private facts its harnesses assert. Assertions stay unchanged; a harness
reads its private facts here and its published facts from the canonical
rows.

The declaration names those facts, per surface: `Application.fixture_observation`
is a tuple of (surface, members), where a surface is `Unit`, `Chart`, `Mailbox`
or a module name. The structure is one flat UDT whose members are named
`<surface>_<member>`. The canonical publication copies it once a scan,
after its own writes and before the generation's closing increment, so the
copy lies inside the generation's odd window: a reader that sees one even
generation before and after its reads proves canonical and private facts
from one scan, under one counter. A copy after the close would leave a
window in which an unchanged even generation covers a fixture still being
written.

It has no TC3 path, never enters the manifest, and no production declaration
emits one (validation refuses it without the collapse). Contacts nothing.
"""

from __future__ import annotations

import hashlib
import json
import fraktal_ab_declaration as decl

# V2 adds selected-member acquisition and the numeric mailbox refusal key.
# A shape signature prevents different acceptance profiles reusing one UDT
# name with different layouts. V1 remains readable in the generic reader.
VERSION = 2


def enabled(app) -> bool:
    return bool(getattr(app, 'fixture_observation', ()))


def tag(app) -> str:
    return f'FRK_{app.name}_FixtureObservation'


def index_tag(app) -> str:
    return f'FRK_{app.name}_FixtureIndex'


def type_name(app) -> str:
    shape = [(surface, member.name, member.kind, member.dimension) for surface, member, _, _ in facts(app)]
    signature = hashlib.sha256(json.dumps(shape).encode()).hexdigest()[:8].upper()
    return f'FRK_T_{app.name}FixtureV{VERSION}_{signature}'


def routine_name(app) -> str:
    return f'FRK_{app.name}_CopyFixtureObservation'


def _surfaces(app):
    """Every surface a fixture may observe: its members and the tag that holds them."""
    import fraktal_ab_generate as gen
    out = {'Unit': (gen.unit_context_members(app), f'FRK_{app.name}_Unit'),
           'Chart': (gen.chart_members(app), f'FRK_{app.name}_Chart')}
    import fraktal_ab_mailbox as mailbox
    out['Mailbox'] = ((decl.scalar('DiagnosticKey', 'the exact numeric refusal key asserted by the apparatus'),),
                      mailbox.response_tag_name(app))
    import fraktal_ab_config as config
    out['ConfigAudit'] = (config.audit_members(), config.audit_tag(app))
    out['Oee'] = (gen.oee_members(), gen.oee_tag(app))
    out['Profiler'] = (gen.profiler_members(app), gen.profiler_tag(app))
    import fraktal_ab_sets as sets
    out['SetState'] = (sets.state_members(app), sets.state_tag(app))
    out['Persist'] = (gen.config_persist_members(), gen.config_persist_tag(app))
    import fraktal_ab_access as access
    if app.access_users is not None:
        out['AccessState'] = (access.state_members(app), access.tag(app, 'State'))
        out['AccessAudit'] = (access.audit_members(), access.tag(app, 'Audit'))
    out['AlarmActive'] = (gen.alarm_active_members(), gen.alarm_active_tag(app))
    out['AlarmRing'] = (gen.alarm_ring_members(), gen.alarm_ring_tag(app))
    out['ReleaseStart'] = (gen.release_report_members(app=app), gen.release_report_tag(app))
    for index, record in enumerate(app.records):
        out[f'Cfg{index}'] = (record.members, record.name + 'Tag')
    for module in app.modules:
        out[module.name] = (gen.module_members(module, app), f'FRK_{app.name}_Inst{module.name}')
    return out


def validate(app) -> list[str]:
    if not enabled(app):
        return []
    if not getattr(app, 'canonical_collapse', False):
        return ['fixture_observation is for collapsed acceptance images (canonical_collapse)']
    if len(routine_name(app)) > 40:
        return [f'fixture_observation: routine name {routine_name(app)} exceeds 40 characters']
    findings, surfaces, seen = [], _surfaces(app), set()
    for surface, members in app.fixture_observation:
        if surface not in surfaces:
            findings.append(f'fixture_observation: no surface {surface!r}')
            continue
        known = {m.name for m in surfaces[surface][0]}
        for name in members:
            if name not in known:
                findings.append(f'fixture_observation: {surface} has no private member {name!r}')
            if (surface, name) in seen:
                findings.append(f'fixture_observation: {surface}.{name} named twice')
            seen.add((surface, name))
    return findings


def facts(app):
    """(surface, source member, observed member name, source tag), in declared order."""
    surfaces = _surfaces(app)
    out = []
    for surface, names in app.fixture_observation:
        members, source = surfaces[surface]
        by_name = {m.name: m for m in members}
        out += [(surface, by_name[name], f'{surface}_{name}', source) for name in names]
    return out


def records(app):
    if not enabled(app):
        return []
    members = tuple(decl.Member(name, f'{surface}.{m.name}', m.kind, m.dimension, 0)
                    for surface, m, name, _ in facts(app))
    return [decl.Record(type_name(app), members, 'O10: acceptance-only fixture observation')]


def cyclic(app) -> list[str]:
    """The call, for the canonical publication to place inside its generation window."""
    return [f'JSR({routine_name(app)},0);'] if enabled(app) else []


def routines(app):
    return [(routine_name(app), logic(app))] if enabled(app) else []


def logic(app) -> list[str]:
    if not enabled(app):
        return []
    t, i = tag(app), index_tag(app)
    lines = ['(* O10: acceptance-only fixture observation, inside the canonical generation\'s odd window *)']
    for _, member, name, source in facts(app):
        if member.dimension:
            lines += [f'FOR {i} := 0 TO {member.dimension - 1} DO',
                      f'{t}.{name}[{i}] := {source}.{member.name}[{i}];', 'END_FOR;']
        else:
            lines.append(f'{t}.{name} := {source}.{member.name};')
    return lines
