"""The configuration document revision: what a set or live document carries (O12).

Every set document and every live document carries `configRev`, in its
header and in each record, and the controller loads only a revision its build
accepts. That check exists so a document is applied only to an image whose
values mean what they meant when it was saved.

Until O12 (approved 2026-11-05) the revision was the first six hex digits of
the V5 manifest content hash. That content includes every published context
member, so adding a status field moved it, although no saved value changed
meaning. Every such release had to enumerate its predecessors by hand, and the
WP6.6 collapse deletes the declarations the hash is built from.

The revision is now derived from what gives a stored value its meaning, and
from nothing else (`identity`):

- the root, and the set document schema;
- for each editable value: its configuration kind (station, model or line),
  its record's schema version, its write key, its value kind and its
  dimension. A record schema change is migrate-or-fault (Core §3.8), so a
  document saved under another record schema is refused.

Three things stay out:
- *ranges and write levels*, which the controller checks itself at load
  (validate-before-load, Core §5.6), so hashing them would only refuse
  documents the controller could have checked;
- *ordinals*, because a document is addressed by key and the key is resolved
  against the controller's current table;
- *record and declaration order*, for the same reason.

The canonical header publishes this identity as `LegacyContentHash`. The path
and the reader's `configRev = LegacyContentHash[:6]` rule are unchanged.

A build accepts its own revision and the predecessors its declaration names
(`Application.config_predecessors`): the revisions its documents carried
before the collapse, and the identity they were saved under. For a
declaration in this tree they are exactly what its pre-collapse build
accepted, recorded at `a3e80ef54` in `fraktal_ab_pre_collapse_revisions.json`
and named with `recorded(<declaration>, <identity>)`, never another
declaration's. A station declared elsewhere records its own revisions with
`fraktal_ab_config_revisions.py` at that commit before it upgrades.

Predecessors are honoured only while the build's identity is still the one
they were saved under. Once a value changes meaning, documents saved before
are migrated or refused (Core §3.8), so `validate` refuses a declaration that
still claims them: the author removes them or migrates the documents.
"""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path

IDENTITY_SCHEMA = 'fraktal.ab.document-identity'
IDENTITY_VERSION = 1
SET_SCHEMA = 1
RECORD = Path(__file__).resolve().with_name('fraktal_ab_pre_collapse_revisions.json')
# The record is written once, at a3e80ef54. An edit to it would silently change
# what every in-tree build accepts, so a different file refuses to load.
RECORD_SHA256 = 'F6EB97ED40A3E5E21E05BF6DDDCA076DD4786F7B937C8A8AF6F2B83FFC32FF84'
REVISION_MAXIMUM = 0xFFFFFF


def identity(app) -> str:
    """The 16 uppercase hex digits naming what this build's documents mean."""
    import fraktal_ab_generate as gen
    import fraktal_ab_sets as sets
    values = sorted([sets.config_kind(record), record.schema_version, member.write_key, member.kind,
                     member.dimension] for _, record, member in gen.editable_values(app))
    payload = dict(identity=IDENTITY_SCHEMA, version=IDENTITY_VERSION, root=app.name,
                   setSchema=SET_SCHEMA, values=values)
    text = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16].upper()


def revision(app) -> int:
    """The revision a document saved by this build carries."""
    return int(identity(app)[:6], 16)


@functools.lru_cache(maxsize=1)
def _rows() -> dict[str, dict]:
    raw = RECORD.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != RECORD_SHA256:
        raise ValueError(f'{RECORD.name}: not the record written at a3e80ef54')
    data = json.loads(raw)
    if data.get('schema') != 'fraktal.ab.config-revisions' or data.get('schemaVersion') != 1:
        raise ValueError(f'{RECORD.name}: unknown schema')
    return {row['declaration']: row for row in data['declarations']}


def _record() -> dict[str, tuple[int, ...]]:
    return {name: tuple(row['acceptedRevisions']) for name, row in _rows().items()}


def saved_revision(declaration: str) -> int:
    """The revision a document saved by an in-tree declaration's pre-collapse build carries."""
    try:
        return _rows()[declaration]['configRevision']
    except KeyError:
        raise ValueError(f'{declaration}: no pre-collapse revisions are recorded for it') from None


def recorded(declaration: str, saved_under: str):
    """Every revision the pre-collapse build of an in-tree declaration accepted,
    bound to the document identity those documents were saved under."""
    import fraktal_ab_declaration as decl
    try:
        revisions = _record()[declaration]
    except KeyError:
        raise ValueError(f'{declaration}: no pre-collapse revisions are recorded for it') from None
    return decl.ConfigPredecessors(identity=saved_under, revisions=revisions)


def validate(app) -> list[str]:
    """Every reason the declared predecessors cannot be honoured."""
    declared = app.config_predecessors
    if declared is None:
        return []
    out = []
    if not isinstance(declared.identity, str) or len(declared.identity) != 16 \
            or any(c not in '0123456789ABCDEF' for c in declared.identity):
        out.append(f'config_predecessors: identity {declared.identity!r} is not 16 uppercase hex digits')
    for value in declared.revisions:
        if type(value) is not int or not 0 <= value <= REVISION_MAXIMUM:
            out.append(f'config_predecessors: {value!r} is not a six-hex-digit revision')
    current = identity(app)
    if not out and declared.identity != current:
        out.append(f'config_predecessors were saved under identity {declared.identity}, but this build is '
                   f'{current}: its values changed meaning, so migrate those documents or remove them')
    return out



def predecessors(app) -> tuple[int, ...]:
    """The declared predecessors this build honours: none unless they are valid
    and were saved under its own identity. `validate` names any it cannot."""
    declared = app.config_predecessors
    if declared is None or validate(app):
        return ()
    return tuple(sorted(set(declared.revisions)))


def accepted(app) -> list[int]:
    """Every revision this build loads, ascending: its own and its predecessors."""
    return sorted({revision(app), *predecessors(app)})
