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

The legacy branch stays for every other declaration until WP6.7 deletes it.
A collapsed context or AOI is a different layout, so it is a different type
name; a released name never changes its layout.
"""

from __future__ import annotations

R3_REMOVED = ('OutImm_ExecState', 'TimCount', 'TimLast', 'TimMin', 'TimMax', 'TimAvg')
R3_SUFFIX = 'R3'
TIMING = (('TimCount', 'Count'), ('TimLast', 'Last'), ('TimMin', 'Minimum'), ('TimMax', 'Maximum'),
          ('TimAvg', 'Avg'))


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
