"""V6.7 wire validation and engineering of discoverable existing scan guards.

Runtime validation is station-free. The declaration is used only by rows().
"""
import re

MINOR = 7
PROTOCOL = 1
FIELDS = frozenset(('CanonicalPrefix', 'RevisionSymbol', 'Protocol', 'MutationPeriodUs'))
HEADER_FIELDS = frozenset(('ReadCoherenceBindingsCount', 'ReadCoherenceBindingsCapacity', 'ReadCoherenceBindings'))
PREFIX = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)*\Z')
SYMBOL = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')


def validate_rows(rows, *, expected_prefixes=None):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1024:
        raise ValueError('invalid read-coherence binding count')
    prefixes = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('invalid read-coherence binding shape')
        prefix, symbol, protocol, period = (row[k] for k in
            ('CanonicalPrefix', 'RevisionSymbol', 'Protocol', 'MutationPeriodUs'))
        if not isinstance(prefix, str) or not PREFIX.fullmatch(prefix) or len(prefix.encode()) > 255 \
                or not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) \
                or type(protocol) is not int or protocol != PROTOCOL \
                or type(period) is not int or not 1 <= period <= 60000000:
            raise ValueError('invalid read-coherence prefix/symbol/protocol/period')
        if any(prefix == old or prefix.startswith(old + '/') or old.startswith(prefix + '/') for old in prefixes):
            raise ValueError('duplicate or overlapping read-coherence prefix')
        prefixes.add(prefix)
    if expected_prefixes is not None and prefixes != set(expected_prefixes):
        raise ValueError('read-coherence bindings do not cover the published roots/products')
    return rows


def validate(app):
    if type(app.canonical_read_coherence) is not bool:
        return ['canonical_read_coherence must be a BOOL opt-in']
    if app.canonical_read_coherence and (app.canonical_publication_stage != 13 or not app.canonical_type_manifest):
        return ['read-coherence publication requires the complete V6.6 profile']
    return []


def rows(app):
    from fraktal_ab_canonical_publication import generation_tag
    from fraktal_ab_canonical_publication import products
    prefixes = [app.name, *(row['CanonicalRoot'] for row in products(app))]
    return validate_rows([dict(CanonicalPrefix=prefix, RevisionSymbol=generation_tag(app),
                              Protocol=PROTOCOL, MutationPeriodUs=app.task_period_ms * 1000)
                          for prefix in prefixes], expected_prefixes=prefixes)


def augment(app, definitions):
    from fraktal_ab_canonical_publication import PREFIX as P, Member, string_type, header_type
    kind = P + 'ReadCoherenceV67'
    definitions[kind] = (Member('CanonicalPrefix', string_type(255)),
                         Member('RevisionSymbol', string_type(40)),
                         Member('Protocol', 'DINT'), Member('MutationPeriodUs', 'DINT'))
    definitions[header_type(app)] += (Member('ReadCoherenceBindingsCount', 'DINT'),
        Member('ReadCoherenceBindingsCapacity', 'DINT'),
        Member('ReadCoherenceBindings', kind, count=len(rows(app))))
