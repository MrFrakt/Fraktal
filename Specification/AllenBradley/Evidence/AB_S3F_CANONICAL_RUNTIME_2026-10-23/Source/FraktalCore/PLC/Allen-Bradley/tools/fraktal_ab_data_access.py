"""Core 3.8d: the controller resolves and enforces each value's access.

One resolver serves writes, captures, set loads/exports and the configuration
page. Policy has a separate retained tag; startup never resets edited levels.
The gateway projects the PLC's effective levels, never computes them.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import fraktal_ab_declaration as decl

MAX_CLASSES = 8  # TC3 PL_Fraktal.MAX_DATA_CLASSES
CLASS_ID_MAX = 40
DENIED = 'std.audit.dataAccessDenied'


def validate(app):
    errors, ids = [], set()
    if len(app.data_classes) > MAX_CLASSES:
        errors.append('data classes exceed MAX_DATA_CLASSES')
    for item in app.data_classes:
        if not isinstance(item, decl.DataClass):
            errors.append('data class declaration must be a DataClass')
            continue
        if not _identity(item.class_id, nonempty=True):
            errors.append('data class id must be 1..40 printable ASCII characters')
        if item.class_id in ids:
            errors.append('duplicate data class id')
        ids.add(item.class_id)
        if not item.label_key or not item.label_key.startswith('project.'):
            errors.append('data class requires a project label key')
        if not all(_level(n) for n in (item.read_level, item.write_level)):
            errors.append('data class default level must be NONE..ADMIN')
    for record in app.records:
        for member in record.members:
            if not _identity(member.class_id):
                errors.append('configuration class id must be at most 40 printable ASCII characters')
            if not all(_level(n) for n in (member.min_read_level, member.min_write_level)):
                errors.append('configuration minimum level must be NONE..ADMIN')
            if (member.class_id or member.min_read_level or member.min_write_level) and not member.editable:
                errors.append('data access requires a registered editable value')
            if app.access_users is None and (member.class_id or member.min_read_level or member.min_write_level):
                errors.append('data access requires the controller access provider')
    if app.data_classes and app.access_users is None:
        errors.append('data classes require the controller access provider')
    return errors


def _identity(value, nonempty=False):
    return isinstance(value, str) and (not nonempty or bool(value)) and len(value) <= CLASS_ID_MAX and all(32 <= ord(c) <= 126 for c in value)


def _level(value):
    return type(value) is int and 0 <= value <= 4


def tag(app, name):
    return f'FRK_{app.name}_Data{name}'


def policy_members(app):
    size = max(1, len(app.data_classes))
    return (decl.scalar('SchemaVersion', initial=1), decl.scalar('Count'),
            *(decl.scalar(n, dimension=size) for n in ('ClassKey', 'LabelKey', 'ReadLevel', 'WriteLevel')))


def levels_members(app):
    import fraktal_ab_generate as gen
    size = max(1, len(gen.editable_values(app)))
    return (decl.scalar('SchemaVersion', initial=levels_version(app)), decl.scalar('Count'),
            *(decl.scalar(n, dimension=size) for n in ('ReadLevel', 'WriteLevel', 'Readable')),
            decl.scalar('RejectSequence'), decl.scalar('RejectCapability'), decl.scalar('RejectRequiredLevel'))


def levels_version(app):
    # Line extends the deployed value arrays; never reinterpret a V1 image.
    return 3 if app.line is not None else 1


def record_name(app, name):
    return f'FRK_T_Data{name}V{levels_version(app) if name == "Levels" else 1}'


def work_members():
    return (decl.scalar('SessionLevel', initial=-1),
            *(decl.scalar(n) for n in ('Index', 'ClassKey', 'Minimum', 'ForWrite', 'Level', 'Valid', 'Byte')))


def records(app):
    return [decl.Record(record_name(app, name), members)
            for name, members in (('Policy', policy_members(app)), ('Levels', levels_members(app)), ('Work', work_members()))]


def policy_data(app):
    import fraktal_ab_manifest as mf
    held = {m.name: [m.initial] * m.dimension if m.dimension else m.initial for m in policy_members(app)}
    held['Count'] = len(app.data_classes)
    for i, item in enumerate(app.data_classes):
        for name, value in (('ClassKey', mf.numeric_key(app, item.class_id)),
                            ('LabelKey', mf.numeric_key(app, item.label_key)),
                            ('ReadLevel', item.read_level), ('WriteLevel', item.write_level)):
            held[name][i] = value
    return held


def tags(app):
    import fraktal_ab_generate as gen
    blocks = [gen._structure_tag(tag(app, name), record_name(app, name), members,
                                external_access='None' if name == 'Work' else 'Read Only')
              for name, members in (('Policy', policy_members(app)), ('Levels', levels_members(app)), ('Work', work_members()))]
    root = ET.fromstring(blocks[0])
    held = policy_data(app)
    for member in root.find('Data/Structure'):
        value = held[member.get('Name')]
        if isinstance(value, list):
            for element, v in zip(member, value):
                element.set('Value', str(v))
        else:
            member.set('Value', str(value))
    blocks[0] = ET.tostring(root, encoding='unicode')
    return blocks


def resolver(app):
    """Same fail-closed, raise-only rule as TC3 M_DataLevel."""
    import fraktal_ab_access as access
    w, p, s = tag(app, 'Work'), tag(app, 'Policy'), access.tag(app, 'State')
    i = w + '.Index'
    return [f'{w}.Level := 4;', f'{w}.Valid := 0;', f'IF {w}.ClassKey = 0 THEN',
            f'IF {w}.ForWrite <> 0 THEN {w}.Level := {s}.Required[1];',
            f'ELSE {w}.Level := {s}.Required[0]; END_IF;', 'ELSE',
            f'IF ({p}.Count >= 0) AND ({p}.Count <= {len(app.data_classes)}) THEN',
            f'FOR {i} := 0 TO {p}.Count - 1 DO', f'IF ({w}.Valid = 0) AND ({p}.ClassKey[{i}] = {w}.ClassKey) THEN',
            f'IF {w}.ForWrite <> 0 THEN {w}.Level := {p}.WriteLevel[{i}];',
            f'ELSE {w}.Level := {p}.ReadLevel[{i}]; END_IF;', f'{w}.Valid := 1;',
            'END_IF;', 'END_FOR;', 'END_IF;', 'END_IF;',
            f'IF ({w}.Level < 0) OR ({w}.Level > 4) THEN {w}.Level := 4; END_IF;',
            f'IF ({w}.Minimum < 0) OR ({w}.Minimum > 4) THEN {w}.Level := 4;',
            f'ELSIF {w}.Minimum > {w}.Level THEN {w}.Level := {w}.Minimum; END_IF;']


def refresh(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    import fraktal_ab_access as access
    d, w, s = tag(app, 'Levels'), tag(app, 'Work'), access.tag(app, 'State')
    values = gen.editable_values(app)
    # The resolver owns Index; Byte is free after class-name comparison and
    # supplies the outer cursor without clobbering set/model iteration.
    slot = w + '.Byte'
    lines = [f'{d}.Count := {len(values)};', f'FOR {slot} := 0 TO {len(values) - 1} DO']
    for name, direction in (('ReadLevel', 0), ('WriteLevel', 1)):
        groups = {}
        for ordinal, _record, member in values:
            minimum = member.min_write_level if direction else member.min_read_level
            key = mf.numeric_key(app, member.class_id) if member.class_id else 0
            groups.setdefault((minimum, key), []).append(str(ordinal - 1))
        lines += [f'{w}.ForWrite := {direction};', f'CASE {slot} OF']
        for (minimum, key), slots in groups.items():
            lines += [','.join(slots) + ':', f'{w}.Minimum := {minimum};', f'{w}.ClassKey := {key};']
        lines += ['ELSE', f'{w}.Minimum := 4;', f'{w}.ClassKey := 0;', 'END_CASE;',
                  f'JSR({tag(app, "ResolveLevel")},0);', f'{d}.{name}[{slot}] := {w}.Level;']
    lines += [f'{d}.Readable[{slot}] := 0;',
              f'IF {permits_level(app, d + ".ReadLevel[" + slot + "]")} THEN {d}.Readable[{slot}] := 1; END_IF;',
              'END_FOR;', f'{w}.SessionLevel := {s}.CurrentLevel;']
    return lines


def cyclic(app):
    """Only input changes need resolution; each committed request rechecks.

    Policy is externally read-only and edited only in this handler. New policy
    edits refresh before acknowledgement; login/expiry refresh on level change.
    """
    import fraktal_ab_access as access
    import fraktal_ab_generate as gen
    d, w, s = tag(app, 'Levels'), tag(app, 'Work'), access.tag(app, 'State')
    return [f'IF ({d}.Count <> {len(gen.editable_values(app))}) OR ({w}.SessionLevel <> {s}.CurrentLevel) THEN',
            f'JSR({tag(app, "RefreshLevels")},0);', 'END_IF;']


def permits_level(app, level):
    import fraktal_ab_access as access
    s = access.tag(app, 'State')
    return f'({level} >= 0) AND ({level} <= 4) AND ({s}.CurrentLevel >= {level}) AND ({s}.CurrentLevel <= 4)'


def reset_rejection(app):
    d = tag(app, 'Levels')
    return [f'{d}.RejectSequence := 0;', f'{d}.RejectCapability := 0;', f'{d}.RejectRequiredLevel := 0;']


def reject(app, ordinal, level):
    import fraktal_ab_access as access
    import fraktal_ab_mailbox as mb
    d, w = tag(app, 'Levels'), access.tag(app, 'Work')
    return [f'{d}.RejectSequence := FRK_{app.name}_HmiLastSequence;',
            f'{d}.RejectCapability := {ordinal};', f'{d}.RejectRequiredLevel := {level};',
            f'{w}.Permitted := 0;', *mb._refuse(app, access.DENIED)]


def check_value(app, ordinal, *, for_write=True):
    """Called before candidate sampling/commit; the ordinal is already validated."""
    direction = 'WriteLevel' if for_write else 'ReadLevel'
    lines = []
    if isinstance(ordinal, int):
        index = ordinal - 1
    else:
        # Studio v33 rejects a nested array lookup in a subscript (press69).
        # Reuse the resolver's private scratch after resolution has completed;
        # set/model iteration uses its own counters. No new tag or unrolling.
        index = tag(app, 'Work') + '.Index'
        lines.append(f'{index} := {ordinal} - 1;')
    level = f'{tag(app, "Levels")}.{direction}[{index}]'
    return lines + [f'IF NOT ({permits_level(app, level)}) THEN', *reject(app, ordinal, level), 'END_IF;']


def dispatch(app):
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    import fraktal_ab_access as access
    q, w, p = mb.request_tag_name(app), tag(app, 'Work'), tag(app, 'Policy')
    # Compare native NameValue bytes, not a gateway-provided ordinal.
    lines = [f'{mb.SET_CLASS_LEVEL}: (* SET_CLASS_LEVEL *)', f'{w}.Valid := 0;',
             f'IF ({q}.NameValue.LEN > 0) AND ({q}.NameValue.LEN <= {CLASS_ID_MAX}) THEN',
             f'IF ({q}.IntValue >= 0) AND ({q}.IntValue <= 4) THEN',
             f'IF ({q}.BoolValue = 0) OR ({q}.BoolValue = 1) THEN']
    for index, item in enumerate(app.data_classes):
        lines += [f'IF {q}.NameValue.LEN = {len(item.class_id)} THEN', f'{w}.Byte := 1;']
        lines += [f'IF {q}.NameValue.DATA[{i}] <> {ord(char)} THEN {w}.Byte := 0; END_IF;' for i, char in enumerate(item.class_id)]
        key = mf.numeric_key(app, item.class_id)
        lines += [f'IF ({w}.Byte <> 0) AND ({p}.Count > {index}) AND ({p}.Count <= {len(app.data_classes)}) AND ({p}.ClassKey[{index}] = {key}) THEN',
                  f'IF {q}.BoolValue <> 0 THEN {p}.WriteLevel[{index}] := {q}.IntValue;',
                  f'ELSE {p}.ReadLevel[{index}] := {q}.IntValue; END_IF;',
                  f'{w}.Valid := 1;', 'END_IF;', 'END_IF;']
    return lines + ['END_IF;', 'END_IF;', 'END_IF;', f'IF {w}.Valid <> 0 THEN',
                    *mb._accept(app), 'ELSE', *mb._refuse(app, access.INVALID), 'END_IF;']


def policy_status(app, rows, held):
    """Decode published identities; retain the PLC's edited policy levels."""
    if held is None or held.get('SchemaVersion') != 1:
        return {'Access/ClassCount': 0}
    keys = {row['NumericKey']: row['PortableKey'] for row in rows.get('Localization', [])}
    count = held.get('Count', -1)
    if not isinstance(count, int) or not 0 <= count <= len(app.data_classes):
        return {'Access/ClassCount': 0}
    out = {'Access/ClassCount': count}
    for i in range(count):
        prefix = f'Access/Classes[{i + 1}]'
        out.update({prefix + '/ClassId': keys.get(held['ClassKey'][i], ''),
                    prefix + '/LabelKey': keys.get(held['LabelKey'][i], ''),
                    prefix + '/ReadLevel': held['ReadLevel'][i],
                    prefix + '/WriteLevel': held['WriteLevel'][i]})
    return out


def entry_levels(held, ordinal, *, app):
    """No host policy arithmetic. Missing/corrupt PLC data cannot reveal a value."""
    if held is not None and held.get('SchemaVersion') == levels_version(app) and 1 <= ordinal <= held.get('Count', 0):
        try:
            read, write, readable = (held[name][ordinal - 1] for name in ('ReadLevel', 'WriteLevel', 'Readable'))
            if _level(read) and _level(write) and readable in (0, 1):
                return read, write, bool(readable)
        except (IndexError, KeyError, TypeError):
            pass
    return 4, 4, False
