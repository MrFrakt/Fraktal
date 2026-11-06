"""S6 WP6.6: the canonical structures become the working storage (the collapse).

Until the collapse a module type's AOI computes its legacy context, and the
publication copies each published fact into the canonical tree every scan:
`Status.State`, `Status.FaultActive` and the command timing rows. That is two
sources for one fact, and a per-instance copy layer that grows with every
module (capacity plan R3, R8).

`Application.canonical_collapse` (S6-Q declarations only) makes the type AOI
write its own canonical leaf through an InOut, `Leaf`, written once per type:

- **C1 (R3).** The execution state is an AOI local, `ExecState`, published as
  `Leaf.Status.State`. With owner revisions (V6.10) it is published under the
  module's header revision, which the AOI receives as `Revision` and opens
  exactly as the publication did (`fraktal_ab_owner_read_bindings.begin`);
  the publication still closes it once at its end. `Leaf.Status.FaultActive`
  is the module's `Error`. Command timing accumulates in `Leaf.Timing.Rows`,
  only for catalogued commands, the rows the copy layer published.
  The context loses `OutImm_ExecState` and the five timing arrays.
- **C2 (R8).** A Unit or chart member whose value the publication copied,
  unconditionally, into a canonical path is stored at that path instead: the
  mode, the step, the decision default, the part counts, the run style (when
  the application paces) and the current step's elapsed time. Every reader
  and writer names the canonical path, the copy goes, and the Unit and part
  AOIs reach it through an InOut `Root`. A conditional copy (the step's
  expected time, the active-step row) is not storage and stays.

The legacy branch stays for every other declaration until WP6.7 deletes it.
A collapsed context or AOI is a different layout, so it is a different type
name; a released name never changes its layout.
"""

from __future__ import annotations

import re

R3_REMOVED = ('OutImm_ExecState', 'TimCount', 'TimLast', 'TimMin', 'TimMax', 'TimAvg')
R3_SUFFIX = 'R3'
TIMING = (('TimCount', 'Count'), ('TimLast', 'Last'), ('TimMin', 'Minimum'), ('TimMax', 'Maximum'),
          ('TimAvg', 'Avg'))


C2_UNIT = (('Mode', 'ModeActivePublished'), ('Step', 'CurrentStep.StepNo'), ('DecisionAnswer', 'Decision.Default'),
           ('GoodCount', 'GoodCount'), ('ScrapCount', 'NokCount'), ('ReworkCount', 'ReworkCount'),
           ('RunStyle', 'RunStyle'))
C2_CHART = (('CurrentStepMs', 'CurrentStepElapsed'),)
C2_SUFFIX = 'C2'
AOI_SUFFIX = 'R8'
_CODE = re.compile(r'(<(Line|Text)\b[^>]*><!\[CDATA\[)(.*?)(\]\]></\2>)', re.S)
_AOI = re.compile(r'<AddOnInstructionDefinition Name="([^"]+)".*?</AddOnInstructionDefinition>', re.S)


def enabled(app) -> bool:
    return bool(app is not None and getattr(app, 'canonical_collapse', False))


def validate(app) -> list[str]:
    if not enabled(app):
        return []
    if app.canonical_publication_stage != 13:
        return ['canonical_collapse needs the S3k publication (canonical_publication_stage 13)']
    return []


def context_members(members, collapsed: bool):
    return tuple(m for m in members if m.name not in R3_REMOVED) if collapsed else tuple(members)


def context_name(base: str, collapsed: bool) -> str:
    return base + R3_SUFFIX if collapsed else base


def aoi_name(base: str, app) -> str:
    import fraktal_ab_owner_read_bindings as owner
    return base + R3_SUFFIX + ('Rev' if owner.enabled(app) else '') if enabled(app) else base


def leaf_type(app, mtype) -> str:
    """The canonical leaf type every instance of `mtype` publishes into."""
    import fraktal_ab_canonical_publication as pub
    import fraktal_ab_library as library
    kinds = {m.name: m.kind for m in pub.schema(app)[pub.root_type(app)]}
    found = {kinds[m.name] for m in app.modules if library.type_of(m) == mtype}
    if len(found) != 1:
        raise ValueError(f'{mtype.type_key}: instances publish into different leaf types {sorted(found)}')
    return found.pop()


def catalogued_rows(app, mtype) -> int:
    """The highest command ordinal any instance of `mtype` catalogues; rows past it stay unpublished."""
    import fraktal_ab_library as library
    ordinals = {tuple(sorted(c.ordinal for c in m.commands)) for m in app.modules if library.type_of(m) == mtype}
    if len(ordinals) != 1:
        raise ValueError(f'{mtype.type_key}: instances catalogue different commands')
    rows = ordinals.pop()
    if rows != tuple(range(1, len(rows) + 1)):
        raise ValueError(f'{mtype.type_key}: command ordinals are not 1..n')
    return len(rows)


def revision_symbol(app, module) -> str | None:
    """The module's V6.10 header revision, which its AOI opens when it publishes."""
    import fraktal_ab_owner_read_bindings as owner
    if not owner.enabled(app):
        return None
    return owner.header_revision(app, list(app.modules).index(module) + 1)


def type_logic(lines, app) -> tuple[str, ...]:
    """The legacy type body, with its published facts written to `Leaf` instead."""
    import fraktal_ab_owner_read_bindings as owner
    text = '\n'.join(lines)
    if 'Ctx.OutImm_ExecState' not in text:
        raise ValueError('type body has no execution state to publish')
    text = text.replace('Ctx.OutImm_ExecState', 'ExecState')
    for source, _ in TIMING:
        if f'Ctx.{source}' in text:
            raise ValueError(f'type body still uses the legacy timing array {source}')
    out = text.split('\n')
    out += ['', '(* WP6.6 R3: the type publishes its own canonical leaf. *)']
    if owner.enabled(app):
        out += ['IF S:FS OR (Leaf.Status.State <> ExecState) THEN', *owner.begin('Revision'),
                'Leaf.Status.State := ExecState;', 'END_IF;']
    else:
        out += ['Leaf.Status.State := ExecState;']
    out += ['Leaf.Status.FaultActive := Ctx.Error <> 0;']
    return tuple(out)


def unit_storage(app) -> dict[str, str]:
    """Unit member -> the canonical path that stores it (C2). The run style is
    copied only when the application paces; otherwise the root publishes 0."""
    import fraktal_ab_generate as gen
    return {m: c for m, c in C2_UNIT if m != 'RunStyle' or gen.pacing(app)} if enabled(app) else {}


def chart_storage(app) -> dict[str, str]:
    return dict(C2_CHART) if enabled(app) else {}


def without(members, storage):
    return tuple(m for m in members if m.name not in storage)


def layout_name(base: str, app) -> str:
    """A Unit or chart type whose layout C2 changed is another type."""
    return base + C2_SUFFIX if enabled(app) else base


def aoi_suffix(app) -> str:
    """The Unit and part AOIs take R1/R3 contexts and the root: another signature (S2)."""
    return AOI_SUFFIX if enabled(app) else ''


def rename_storage(text: str, app, scoped: set[str]) -> str:
    """Point every reference to a C2 member at the canonical path that stores it.

    Only the code is touched: the CDATA of each `Line` (ST, SFC actions and
    conditions) and each `Text` (ladder rungs). Controller-scope names change
    everywhere; an AOI cannot name a controller tag, so they occur only in
    programs. Inside the `scoped` AOIs, whose `Ctx` is the Unit context and
    whose `Chart` is the chart, those parameters' members move to `Root`; every
    other AOI's `Ctx` is its own module's and is left alone. Refuses to return
    text that still names a moved member.
    """
    n = app.name
    unit, chart = unit_storage(app), chart_storage(app)
    rules = [(re.compile(rf'(?<![\w.])FRK_{n}_Unit\.{m}(?![\w])'), f'{n}.{c}') for m, c in unit.items()]
    rules += [(re.compile(rf'(?<![\w.])FRK_{n}_Chart\.{m}(?![\w])'), f'{n}.{c}') for m, c in chart.items()]
    local = [(re.compile(rf'(?<![\w.])Ctx\.{m}(?![\w])'), f'Root.{c}') for m, c in unit.items()]
    local += [(re.compile(rf'(?<![\w.])Chart\.{m}(?![\w])'), f'Root.{c}') for m, c in chart.items()]

    def region(segment, active):
        def code(match):
            body = match.group(3)
            for pattern, replacement in active:
                body = pattern.sub(replacement, body)
            return match.group(1) + body + match.group(4)
        return _CODE.sub(code, segment)

    out, position = [], 0
    for aoi in _AOI.finditer(text):
        out.append(region(text[position:aoi.start()], rules))
        out.append(region(aoi.group(0), rules + (local if aoi.group(1) in scoped else [])))
        position = aoi.end()
    out.append(region(text[position:], rules))
    result = ''.join(out)
    left = [p.pattern for p, _ in rules if any(p.search(m.group(3)) for m in _CODE.finditer(result))]
    for aoi in _AOI.finditer(result):
        if aoi.group(1) in scoped:
            left += [p.pattern for p, _ in local if any(p.search(m.group(3)) for m in _CODE.finditer(aoi.group(0)))]
    if left:
        raise ValueError(f'C2 storage still referenced: {left}')
    return result
