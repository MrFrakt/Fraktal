"""Approved V6.10 owner-row metadata and generated seqlock ownership.

Runtime validators use only published facts. Engineering helpers derive rows
from the declaration; older opt-out images retain their exact publication.
"""
import hashlib
import json
import re

MINOR = 10
PROTOCOL = 2
MAXIMUM_PROOF_US = 1_000_000
# Zero initializes the counter; the recurring stable sequence wraps to two.
# Use its conservative cycle length, not the full even encoding space.
STABLE_TOKEN_COUNT = (1 << 30) - 1
HEADER_MEMBERS = ('Name', 'ModuleType', 'State', 'ConfigRev', 'TypeKey')
FIELDS = frozenset(('CanonicalPrefix', 'MembersJson', 'RevisionSymbol',
                    'ProgressSymbol', 'Protocol', 'MinimumUpdateIntervalUs',
                    'MaximumProofWindowUs'))
HEADER_FIELDS = frozenset(('OwnerReadBindingsCount', 'OwnerReadBindingsCapacity',
                          'OwnerReadBindings'))
_PREFIX = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)*\Z')
_SYMBOL = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')
WORK = 'FRK_T_HeaderOwnerWorkV610'
ROW = 'FRK_T_OwnerReadBindingV610'


def enabled(app):
    return app.canonical_owner_revisions


def validate_rows(rows, *, read_services=None, base_bindings=None):
    """Reject ambiguous selections and unprovable counter-wrap bounds."""
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1024:
        raise ValueError('invalid owner-read binding count')
    seen, revisions = [], set()
    views = None if read_services is None else {s['CanonicalRoot'] for s in read_services}
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('invalid owner-read binding shape')
        prefix, encoded, revision, progress = (row[k] for k in
            ('CanonicalPrefix', 'MembersJson', 'RevisionSymbol', 'ProgressSymbol'))
        period, window = row['MinimumUpdateIntervalUs'], row['MaximumProofWindowUs']
        if not isinstance(prefix, str) or not _PREFIX.fullmatch(prefix) or len(prefix.encode()) > 255 \
                or not isinstance(encoded, str) or len(encoded.encode()) > 255 \
                or not isinstance(revision, str) or not _SYMBOL.fullmatch(revision) \
                or not isinstance(progress, str) or not _SYMBOL.fullmatch(progress) \
                or revision == progress or revision in revisions \
                or type(row['Protocol']) is not int or row['Protocol'] != PROTOCOL \
                or type(period) is not int or not 1 <= period <= 60_000_000 \
                or type(window) is not int or not 1 <= window <= MAXIMUM_PROOF_US \
                or window >= STABLE_TOKEN_COUNT * period:
            raise ValueError('invalid owner-read path/symbol/protocol/bound')
        try:
            members = json.loads(encoded)
        except (ValueError, TypeError) as error:
            raise ValueError('invalid owner member selection') from error
        if not isinstance(members, list) or any(not isinstance(m, str) for m in members) \
                or len(members) != len(set(members)) \
                or (members and (not prefix.endswith('/Status')
                    or not {'Name', 'ModuleType', 'State'} <= set(members) <= set(HEADER_MEMBERS))) \
                or (not members and (views is None or prefix not in views)):
            raise ValueError('invalid owner member selection or scope')
        selection = [prefix + '/' + m for m in members] if members else [prefix]
        if base_bindings is not None:
            if revision in {b['RevisionSymbol'] for b in base_bindings}:
                raise ValueError('owner revision must be separate from every scan counter')
            parent = [b for b in base_bindings if prefix == b['CanonicalPrefix']
                      or prefix.startswith(b['CanonicalPrefix'] + '/')]
            if len(parent) != 1 or progress != parent[0]['RevisionSymbol'] \
                    or period != parent[0]['MutationPeriodUs']:
                raise ValueError('owner progress/period differs from its scan-bound parent')
        for selected in selection:
            if any(selected == old or selected.startswith(old + '/') or old.startswith(selected + '/') for old in seen):
                raise ValueError('duplicate or overlapping owner-read selection')
            seen.append(selected)
        revisions.add(revision)
    return rows


def validate(app):
    if type(app.canonical_owner_revisions) is not bool:
        return ['canonical_owner_revisions must be a BOOL opt-in']
    if enabled(app) and (not app.canonical_config_read_view or not app.canonical_read_coherence
                         or app.canonical_publication_stage != 13):
        return ['owner revisions require the complete V6.8 configuration profile']
    return []


def _name(app, suffix):
    value = f'FRK_{app.name}_{suffix}'
    return value if len(value) <= 40 else value[:23] + '_' + hashlib.sha256(value.encode()).hexdigest()[:16]


def header_revision(app, index):
    return _name(app, f'HeaderRevision{index}')


def view_revision(app):
    return _name(app, 'ConfigViewRevision')


def work_tag(app):
    return _name(app, 'HeaderOwnerWork')


def module_paths(app):
    return [app.name, *(app.name + '/' + m.name for m in app.modules)]


def rows(app, definitions=None):
    if not enabled(app):
        return []
    from fraktal_ab_canonical_publication import generation_tag, root_type, schema
    from fraktal_ab_config_read_view import descriptors
    if definitions is None:
        definitions = schema(app)
    root = definitions[root_type(app)]
    def selection(module):
        parent = root if module is None else definitions[next(m.kind for m in root if m.name == module.name)]
        status = definitions[next(m.kind for m in parent if m.name == 'Status')]
        names = {m.name for m in status}
        return [n for n in HEADER_MEMBERS if n in names]
    common = dict(ProgressSymbol=generation_tag(app), Protocol=PROTOCOL,
                  MinimumUpdateIntervalUs=app.task_period_ms * 1000,
                  MaximumProofWindowUs=MAXIMUM_PROOF_US)
    result = [dict(CanonicalPrefix=path + '/Status',
                   MembersJson=json.dumps(selection(module), separators=(',', ':')),
                   RevisionSymbol=header_revision(app, i), **common)
              for i, (path, module) in enumerate(zip(module_paths(app), (None, *app.modules)))]
    result += [dict(CanonicalPrefix=s['CanonicalRoot'], MembersJson='[]',
                    RevisionSymbol=view_revision(app), **common) for s in descriptors(app)]
    from fraktal_ab_read_coherence import rows as scan_rows
    return validate_rows(result, read_services=descriptors(app), base_bindings=scan_rows(app))


def augment(app, definitions):
    if not enabled(app):
        return
    from fraktal_ab_canonical_publication import Member as M, string_type as S, header_type
    definitions[WORK] = (M('NextState', 'DINT'),)
    definitions[ROW] = (M('CanonicalPrefix', S(255)), M('MembersJson', S(255)),
                        M('RevisionSymbol', S(40)), M('ProgressSymbol', S(40)),
                        *(M(n, 'DINT') for n in ('Protocol', 'MinimumUpdateIntervalUs', 'MaximumProofWindowUs')))
    definitions[header_type(app)] += (M('OwnerReadBindingsCount', 'DINT'),
        M('OwnerReadBindingsCapacity', 'DINT'), M('OwnerReadBindings', ROW, count=len(rows(app, definitions))))


def tags(app, serialize):
    if not enabled(app):
        return []
    symbols = [header_revision(app, i) for i in range(len(module_paths(app)))] + [view_revision(app)]
    return [serialize(work_tag(app), WORK, {}, access='None'), *[
        f'<Tag Name="{name}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read Only"/>'
        for name in symbols]]


def begin(symbol):
    # Several protected members can change in one scan. Open at most once;
    # recover an already-odd interrupted transaction without publishing even.
    return [f'IF ({symbol} MOD 2) = 0 THEN',
            f'IF {symbol} >= 2147483646 THEN {symbol} := 0; END_IF;',
            f'{symbol} := {symbol} + 1;', 'END_IF;']


def close(symbol):
    return [f'IF ({symbol} MOD 2) <> 0 THEN {symbol} := {symbol} + 1; END_IF;']


def write_header(app, index, member, expression):
    """Publish at the original write point; close once at publication end."""
    target = module_paths(app)[index].replace('/', '.') + '.Status.' + member
    if not enabled(app):
        return [f'{target} := {expression};']
    if member not in ('State', 'ConfigRev'):
        raise ValueError('cyclic identity mutation requires an explicit generated owner')
    return [f'IF S:FS OR ({target} <> {expression}) THEN',
            *begin(header_revision(app, index)), f'{target} := {expression};', 'END_IF;']


def close_headers(app):
    return [line for i in range(len(module_paths(app))) for line in close(header_revision(app, i))] if enabled(app) else []
