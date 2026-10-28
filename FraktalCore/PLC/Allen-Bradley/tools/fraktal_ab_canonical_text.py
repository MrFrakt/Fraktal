"""Private literal-text pool: each text once as constant data, copied by one bounded loop.

A literal written byte by byte costs a statement per character in every place
that publishes it; the configuration page and the audit renderer held most of
the image's logic that way. Here every literal those owners publish is stored
once in a constant SINT pool and referenced by (Offset, Length) slices. Copies
keep the exact semantics they replace: a put sets LEN then writes only DATA[0..LEN-1];
an append refuses (and clears manifest Valid) rather than truncate.

Opt-in per declaration (`canonical_table_driven`), so released images keep their bytes.
"""
from functools import lru_cache

import fraktal_ab_canonical_publication as pub

SLICE = pub.PREFIX + 'TextSliceV1'
WORK = pub.PREFIX + 'TextWorkV1'


def enabled(app):
    return bool(app.canonical_table_driven)


def pool_tag(app):return f'FRK_{app.name}_CanonicalText'
def work_tag(app):return f'FRK_{app.name}_CanonicalTextWork'


def validate(app):
    if not app.canonical_table_driven:
        return []
    if type(app.canonical_table_driven) is not bool:
        return ['table-driven canonical text is a boolean declaration choice']
    if app.canonical_publication_stage < 7:
        return ['table-driven canonical text requires the S3e access audit']
    return []


def texts(app):
    """Every literal the table-driven owners publish, in a deterministic order."""
    import fraktal_ab_canonical_access as access
    import fraktal_ab_canonical_config as config
    result = list(access.literals(app))
    if app.canonical_publication_stage >= 8:
        result += config.literals(app)
    if app.canonical_publication_stage >= 13:
        import fraktal_ab_canonical_mailbox as mailbox
        result += mailbox.literals(app)
        import fraktal_ab_canonical_commands as commands
        result += commands.literals(app)
    return result


@lru_cache(maxsize=None)
def _layout(items):
    """Longest first, so a shorter text that occurs inside a longer one shares its bytes."""
    pool, where = bytearray(), {}
    for text in sorted(set(items), key=lambda t: (-len(t.encode('utf-8')), t)):
        raw = text.encode('utf-8')
        found = pool.find(raw) if raw else 0
        if found < 0:
            found = len(pool)
            pool += raw
        where[text] = (found, len(raw))
    return bytes(pool or b'\0'), where


def layout(app):
    return _layout(tuple(texts(app)))


def slice_of(app, text):
    return layout(app)[1][text]


def slice_value(app, text):
    offset, length = slice_of(app, text)
    return dict(Offset=offset, Length=length)


def augment(app, definitions):
    if not enabled(app):
        return
    M = pub.Member
    definitions[SLICE] = (M('Offset', 'DINT'), M('Length', 'DINT'))
    # Index: Logix refuses an array reference inside a subscript, so table and
    # cache positions are computed into this scalar before they are used.
    definitions[WORK] = (M('Offset', 'DINT'), M('Length', 'DINT'), M('Byte', 'DINT'), M('Index', 'DINT'))


def pool_values(app):
    return [b if b < 128 else b - 256 for b in layout(app)[0]]


def tags(app, serialize):
    if not enabled(app):
        return []
    values = pool_values(app)
    elements = ''.join(f'<Element Index="[{i}]" Value="{v}"/>' for i, v in enumerate(values))
    pool = (f'<Tag Name="{pool_tag(app)}" TagType="Base" DataType="SINT" Dimensions="{len(values)}" Radix="Decimal" '
            f'Constant="true" ExternalAccess="None"><Data Format="Decorated">'
            f'<Array DataType="SINT" Dimensions="{len(values)}" Radix="Decimal">{elements}</Array></Data></Tag>')
    return [pool, serialize(work_tag(app), WORK, {}, access='None')]


def model_tags(app):
    """The same initial values the tags carry, for executed-ST tests."""
    return {pool_tag(app): pool_values(app), work_tag(app): dict(Offset=0, Length=0, Byte=0, Index=0)}


def put(app, target, offset, length):
    """target := pool[offset .. offset+length-1]; offset/length are literals or tag expressions."""
    w, p = work_tag(app), pool_tag(app)
    if type(length) is int and length == 0:
        return [f'{target}.LEN := 0;']
    return [f'{w}.Offset := {offset};', f'{w}.Length := {length};', f'{target}.LEN := {w}.Length;',
            f'FOR {w}.Byte := 0 TO {w}.Length - 1 DO',
            f'{target}.DATA[{w}.Byte] := {p}[{w}.Offset + {w}.Byte];', 'END_FOR;']


def put_text(app, target, text, width):
    offset, length = slice_of(app, text)
    if length > width:
        raise ValueError('canonical literal exceeds its declared byte width')
    return put(app, target, offset, length)


def append_routine_lines(app, render, valid):
    """Shared append: the whole slice fits in a 255-byte render, or nothing is written."""
    w, p = work_tag(app), pool_tag(app)
    return [f'IF {render}.LEN + {w}.Length <= 255 THEN',
            f'FOR {w}.Byte := 0 TO {w}.Length - 1 DO',
            f'{render}.DATA[{render}.LEN + {w}.Byte] := {p}[{w}.Offset + {w}.Byte];', 'END_FOR;',
            f'{render}.LEN := {render}.LEN + {w}.Length;', 'ELSE', f'{valid} := 0;', 'END_IF;']


def append(app, routine, offset, length):
    w = work_tag(app)
    return [f'{w}.Offset := {offset};', f'{w}.Length := {length};', f'JSR({routine},0);']


def append_text(app, routine, text):
    offset, length = slice_of(app, text)
    return append(app, routine, offset, length) if length else []


def keyed_table(app, entries):
    """Dense (base, slices) for {number: text}; numbers without text get an empty slice."""
    if not entries:
        return 0, []
    base, top = min(entries), max(entries)
    return base, [slice_value(app, entries[n]) if n in entries else dict(Offset=0, Length=0)
                  for n in range(base, top + 1)]
