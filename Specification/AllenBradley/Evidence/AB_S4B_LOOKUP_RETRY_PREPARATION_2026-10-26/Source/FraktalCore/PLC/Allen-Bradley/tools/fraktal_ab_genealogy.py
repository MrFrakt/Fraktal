"""Opt-in consumed-component genealogy; one PLC owner and host snapshots.

No device protocol or remote write surface. A confirmed MARK supplies bounded
ASCII sources. The Part service validates the complete batch before appending.
"""
from dataclasses import replace
import struct

import fraktal_ab_declaration as decl
import fraktal_ab_resources as ascii_source

UID_CELLS = 64
UID_WORDS = UID_CELLS // 4
MAX_PARENTS = 8  # Core 3.16.1 / TC3 PL_Fraktal.MAX_GENEALOGY


def capacity(app):
    return getattr(app.part_carrier, 'genealogy_capacity', 0)


def enabled(app):
    count = capacity(app)
    return type(count) is int and count > 0


def validate(app):
    count = capacity(app)
    steps = [step for chain in app.chains for step in chain.steps]
    if type(count) is not int or not 0 <= count <= MAX_PARENTS:
        return ['Part: genealogy capacity must be an integer in 0..8']
    result = []
    consumers = [step for step in steps if step.part_parents]
    if count and not consumers:
        result.append('Part: genealogy storage has no confirmed-parent consumer')
    for step in steps:
        if not isinstance(step.part_parents, tuple):
            result.append('Part: confirmed parents must be a tuple')
            continue
        if not step.part_parents:
            continue
        if (not count or step.action != decl.MARK or len(step.part_parents) > count
                or step.part_action in ('processed', 'aborted')):
            result.append('Part: parent confirmation requires a bounded non-terminal MARK')
        for source in step.part_parents:
            if (not ascii_source.ascii_valid(app, source, UID_CELLS, UID_CELLS)
                    or source.literal == ''):
                result.append('Part: parent UID needs 1..64 printable ASCII bytes or an exact declared array')
    return result


def without(app):
    return replace(app, part_carrier=replace(app.part_carrier, genealogy_capacity=0),
        chains=tuple(replace(chain, steps=tuple(replace(step, part_parents=())
            for step in chain.steps)) for chain in app.chains))


def part_members(app):
    return (decl.scalar('ParentCount'), decl.scalar('Parents', dimension=capacity(app)*UID_CELLS))


def carrier_members(app):
    count = capacity(app)
    return (decl.scalar('LastParentCount'), decl.scalar('LastParents', dimension=count*UID_CELLS),
            decl.scalar('PendingParentCount'), decl.scalar('PendingParents', dimension=count*UID_CELLS),
            decl.scalar('PendingNew', dimension=count))


def clear(app):
    return ['Part.ParentCount := 0;',
            f'FOR Index := 0 TO {capacity(app)*UID_CELLS-1} DO Part.Parents[Index] := 0; END_FOR;']


def commit(app):
    return ['Carrier.LastParentCount := Part.ParentCount;',
            f'FOR Index := 0 TO {capacity(app)*UID_CELLS-1} DO Carrier.LastParents[Index] := Part.Parents[Index]; END_FOR;']


def emit(app):
    return ['Ring.PendingParentCount := Part.ParentCount;',
            f'FOR Index := 0 TO {capacity(app)*UID_CELLS-1} DO Ring.PendingParents[Index] := Part.Parents[Index]; END_FOR;']


LOCALS = ('ParentIndex','OtherParent','CharIndex','SourceIndex','OtherIndex',
          'UidMatch','SelfMatch','UidEnded','HasByte','NewCount','BadParents')


def append_logic(app, fault):
    """Replay is idempotent; a malformed/over-capacity batch changes no Part row."""
    count = capacity(app)
    return [
        'ELSIF Operation = 6 THEN',
        f'IF (Part.Present = 0) OR (Ctx.Error <> 0) OR (Part.ParentCount < 0) OR (Part.ParentCount > {count}) '
        f'OR (Carrier.PendingParentCount < 1) OR (Carrier.PendingParentCount > {count}) THEN',
        *fault('RESULT_RECORD_REJECTED'), 'ELSE',
        'BadParents := 0;', 'NewCount := 0;',
        f'FOR ParentIndex := 0 TO {count-1} DO',
        'Carrier.PendingNew[ParentIndex] := 0;',
        'IF ParentIndex < Carrier.PendingParentCount THEN',
        'Carrier.PendingNew[ParentIndex] := 1;',
        'UidEnded := 0;', 'HasByte := 0;', 'SelfMatch := 1;',
        'FOR CharIndex := 0 TO 63 DO',
        'SourceIndex := (ParentIndex * 64) + CharIndex;',
        'IF Carrier.PendingParents[SourceIndex] <> Part.Uid[CharIndex] THEN SelfMatch := 0; END_IF;',
        'IF Carrier.PendingParents[SourceIndex] = 0 THEN UidEnded := 1;',
        'ELSE', 'HasByte := 1;',
        'IF (UidEnded <> 0) OR (Carrier.PendingParents[SourceIndex] < 32) '
        'OR (Carrier.PendingParents[SourceIndex] > 126) THEN BadParents := 1; END_IF;',
        'END_IF;', 'END_FOR;',
        'IF (HasByte = 0) OR (SelfMatch <> 0) THEN BadParents := 1; END_IF;',
        f'FOR OtherParent := 0 TO {count-1} DO',
        'IF OtherParent < Part.ParentCount THEN', 'UidMatch := 1;',
        'FOR CharIndex := 0 TO 63 DO',
        'SourceIndex := (ParentIndex * 64) + CharIndex;',
        'OtherIndex := (OtherParent * 64) + CharIndex;',
        'IF Carrier.PendingParents[SourceIndex] <> Part.Parents[OtherIndex] THEN UidMatch := 0; END_IF;',
        'END_FOR;', 'IF UidMatch <> 0 THEN Carrier.PendingNew[ParentIndex] := 0; END_IF;', 'END_IF;',
        'IF OtherParent < ParentIndex THEN', 'UidMatch := 1;',
        'FOR CharIndex := 0 TO 63 DO',
        'SourceIndex := (ParentIndex * 64) + CharIndex;',
        'OtherIndex := (OtherParent * 64) + CharIndex;',
        'IF Carrier.PendingParents[SourceIndex] <> Carrier.PendingParents[OtherIndex] THEN UidMatch := 0; END_IF;',
        'END_FOR;', 'IF UidMatch <> 0 THEN Carrier.PendingNew[ParentIndex] := 0; END_IF;', 'END_IF;',
        'END_FOR;', 'NewCount := NewCount + Carrier.PendingNew[ParentIndex];',
        'END_IF;', 'END_FOR;',
        f'IF (BadParents <> 0) OR ((Part.ParentCount + NewCount) > {count}) THEN',
        *fault('RESULT_RECORD_REJECTED'), 'ELSE',
        f'FOR ParentIndex := 0 TO {count-1} DO',
        'IF Carrier.PendingNew[ParentIndex] <> 0 THEN',
        'FOR CharIndex := 0 TO 63 DO',
        'SourceIndex := (ParentIndex * 64) + CharIndex;',
        'OtherIndex := (Part.ParentCount * 64) + CharIndex;',
        'Part.Parents[OtherIndex] := Carrier.PendingParents[SourceIndex];',
        'END_FOR;', 'Part.ParentCount := Part.ParentCount + 1;', 'END_IF;', 'END_FOR;',
        'END_IF;', 'END_IF;',
    ]


def marks(app, step, names, *, ladder=False):
    import fraktal_ab_part as part
    carrier = 'Carrier' if names.in_aoi else part.carrier_tag(app)
    def assign(field, value):
        return f'MOV({value},{carrier}.{field})' if ladder else f'{carrier}.{field} := {value};'
    result = [assign('PendingParentCount',len(step.part_parents))]
    cells = [value for source in step.part_parents
             for value in ascii_source.ascii_cells(app, source, names, UID_CELLS)]
    cells += [0] * (capacity(app)*UID_CELLS - len(cells))
    result += [assign(f'PendingParents[{index}]',value) for index,value in enumerate(cells)]
    call = part.call(app,'parents',in_aoi=names.in_aoi)
    if ladder:
        return [f'EQU({names.unit}.Error,0)', *result, call]
    return [f'IF {names.unit}.Error = 0 THEN', *result, call + ';', 'END_IF;']


def host_members(app):
    count = capacity(app)
    return (decl.scalar('PendingParentCount'), decl.scalar('PendingParents',dimension=count*UID_CELLS),
            decl.scalar('ParentCount',dimension=app.host_event_capacity),
            decl.scalar('ParentWords',dimension=app.host_event_capacity*count*UID_WORDS))


def host_validation(app):
    return ['IF (Kind >= 1) AND (Kind <= 4) THEN',
            f'IF (Ring.PendingParentCount < 0) OR (Ring.PendingParentCount > {capacity(app)}) THEN Ring.Failed := 1; END_IF;',
            'END_IF;']


def host_store(app):
    words = capacity(app)*UID_WORDS
    return ['Ring.ParentCount[Slot] := 0;',
            f'FOR ByteIndex := 0 TO {words-1} DO',
            f'UidIndex := (Slot * {words}) + ByteIndex;', 'Ring.ParentWords[UidIndex] := 0;', 'END_FOR;',
            'IF (Kind >= 1) AND (Kind <= 4) THEN',
            'Ring.ParentCount[Slot] := Ring.PendingParentCount;',
            f'FOR ByteIndex := 0 TO {words-1} DO',
            f'UidIndex := (Slot * {words}) + ByteIndex;', 'SourceIndex := ByteIndex * 4;',
            'Ring.ParentWords[UidIndex] := Ring.PendingParents[SourceIndex] '
            '+ (Ring.PendingParents[SourceIndex + 1] * 256) '
            '+ (Ring.PendingParents[SourceIndex + 2] * 65536) '
            '+ (Ring.PendingParents[SourceIndex + 3] * 16777216);', 'END_FOR;', 'END_IF;']


def uids(data, count, bound, child):
    from fraktal_ab_part import uid
    if type(count) is not int or not 0 <= count <= bound or not isinstance(data,list) or len(data) != bound*UID_CELLS:
        raise ValueError('invalid genealogy bounds')
    parents = [uid(data[index*UID_CELLS:(index+1)*UID_CELLS]) for index in range(bound)]
    if (any(not parent or parent == child for parent in parents[:count])
            or any(parents[count:]) or len(set(parents[:count])) != count):
        raise ValueError('invalid, duplicate or self-referencing genealogy')
    return parents[:count]


def decode_host(app, raw, slot, kind, child):
    bound = capacity(app)
    count = raw['ParentCount'][slot]
    width = bound*UID_WORDS
    words = raw['ParentWords'][slot*width:(slot+1)*width]
    if (len(raw['ParentCount']) != app.host_event_capacity
            or len(raw['ParentWords']) != app.host_event_capacity*width
            or len(words) != width or any(type(word) is not int or not 0 <= word <= 2**31-1 for word in words)):
        raise ValueError('invalid host genealogy layout')
    if kind not in (1,2,3,4) and (count or any(words)):
        raise ValueError('genealogy leaked to non-part event')
    cells = list(struct.pack('<'+'i'*width,*words))
    return uids(cells,count,bound,child)
