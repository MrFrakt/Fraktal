"""R1 engineering: sparse V6.4 annotations, paid once per owning UDT member.

The runtime resolves these facts from Template names, never this module or a
station declaration. Released declarations retain their earlier wire layout.
"""
from __future__ import annotations

import json

import fraktal_ab_canonical_manifest as wire


def validate(app):
    if type(app.canonical_type_manifest) is not bool:
        return ['canonical_type_manifest must be a BOOL declaration opt-in']
    if app.canonical_type_manifest and not app.canonical_publication_stage:
        return ['canonical_type_manifest requires canonical publication']
    return []


def tables(app, definitions):
    from fraktal_ab_canonical_publication import root_type
    annotations, exceptions = {}, {}

    def walk(kind, path, depth=0):
        if depth > 64:
            raise ValueError('canonical type annotation depth budget exceeded')
        for member in definitions[kind]:
            target = path + '/' + member.name
            count_member = ''
            if member.count_path:
                parent, separator, count_member = member.count_path.rpartition('/')
                if not separator or parent != path:
                    raise ValueError('V6.4 requires a sibling count member: ' + target)
            row = dict(TypeName=kind, MemberName=member.name, LogicalType=member.logical,
                       LowerBound=member.lower if member.count else 0,
                       ElementCount=(member.extent or member.count) if member.count else 0,
                       CountMember=count_member, EffectiveAccess=member.access)
            pair = (kind, member.name)
            if pair in annotations and annotations[pair] != row:
                raise ValueError('conflicting type-scoped annotation: ' + '.'.join(pair))
            if member.logical or member.count or count_member or member.access:
                annotations[pair] = row
            if member.indices is not None:
                exceptions[target] = dict(CanonicalPath=target,
                    Indices=json.dumps(member.indices, separators=(',', ':')))
            if member.kind in definitions:
                walk(member.kind, target + ('[*]' if member.count else ''), depth+1)

    walk(root_type(app), app.name)
    if app.canonical_publication_stage >= 5:
        from fraktal_ab_canonical_sequence import DEFINITIONS
        walk(DEFINITIONS, app.name)
    if app.canonical_publication_stage >= 6:
        from fraktal_ab_canonical_alarms import METADATA
        walk(METADATA, app.name)
    if app.canonical_publication_stage>=12:
        import fraktal_ab_canonical_fieldbus as fieldbus
        if fieldbus.enabled(app):walk(fieldbus.TOPOLOGY,fieldbus.canonical_root(app))
    if app.canonical_publication_stage>=13:
        from fraktal_ab_canonical_commands import ARGS
        walk(ARGS,app.name+"/HmiRequest")
    import fraktal_ab_config_read_view as config_read
    if config_read.enabled(app):walk(config_read.VIEW,config_read.canonical_root(app))
    rows, paths = list(annotations.values()), list(exceptions.values())
    # The generic wire validator also owns identifier, bound and selection rules.
    wire.type_tables(rows, paths)
    return rows, paths


def augment(app, definitions):
    from fraktal_ab_canonical_publication import Member, PREFIX, string_type
    rows, exceptions = tables(app, definitions)
    annotation_type, exception_type = PREFIX+'TypeAnnotationV64', PREFIX+'PathExceptionV64'
    definitions[annotation_type] = (
        Member('TypeName', string_type(40)), Member('MemberName', string_type(40)),
        Member('LogicalType', string_type(16)), Member('LowerBound', 'DINT'),
        Member('ElementCount', 'DINT'), Member('CountMember', string_type(40)),
        Member('EffectiveAccess', string_type(16)))
    if exceptions:
        definitions[exception_type] = (Member('CanonicalPath', string_type(wire.PATH_WIDTH)),
                                      Member('Indices', string_type(wire.PATH_WIDTH)))
    return (
        Member('TypeAnnotationsCount', 'DINT'), Member('TypeAnnotationsCapacity', 'DINT'),
        Member('TypeAnnotations', annotation_type, count=len(rows)),
        Member('PathExceptionsCount', 'DINT'), Member('PathExceptionsCapacity', 'DINT'),
        *((Member('PathExceptions', exception_type, count=len(exceptions)),) if exceptions else ()))
