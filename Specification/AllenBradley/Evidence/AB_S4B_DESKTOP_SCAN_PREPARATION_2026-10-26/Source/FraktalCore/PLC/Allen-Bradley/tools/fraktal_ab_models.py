"""Optional bounded model catalog, owned and committed by the PLC.

Creation appends an inactive recipe. Existing ordinals never move and activation
still uses the application's prepare/changeover/commit path. No host tag write
can modify catalog or recipe storage directly.
"""
import fraktal_ab_declaration as decl

CODE_MAX = 80


def tag(app):
    return f'FRK_{app.name}_ModelCatalog'


def type_name():
    return 'FRK_T_ModelCatalogV1'


def members(app):
    return (decl.scalar('SchemaVersion'), decl.scalar('Count'),
            decl.scalar('CodeLength', dimension=app.model_capacity),
            decl.scalar('CodeBytes', dimension=app.model_capacity * CODE_MAX))


def ordinal_guard(app, value):
    bounds = f'({value} >= 1) AND ({value} <= {count_expression(app)})'
    return bounds + (f' AND ({value} <= {app.model_capacity})' if app.model_capacity else '')


def count_expression(app):
    return tag(app) + '.Count' if app.model_capacity else str(len(app.models))


def restore(app, persist):
    import fraktal_ab_generate as gen
    c, array = tag(app), gen.model_cfg_tag(app)
    import fraktal_ab_sets as sets
    i, j, b = sets.scratch_names(app)
    version = gen.model_cfg_schema_version(app)
    lines = [f'IF {c}.SchemaVersion = 0 THEN']
    for index, model in enumerate(app.models):
        lines += [f'{c}.CodeLength[{index}] := {len(model.code)};']
        lines += [f'{c}.CodeBytes[{index * CODE_MAX + k}] := {ord(ch)};'
                  for k, ch in enumerate(model.code)]
    lines += [f'{c}.Count := {len(app.models)};', f'{c}.SchemaVersion := 1;',
              f'ELSIF ({c}.SchemaVersion <> 1) OR ({c}.Count < {len(app.models)}) OR ({c}.Count > {app.model_capacity}) THEN',
              f'{c}.Count := 0;', f'{persist}.RestoreLost := 1;',
              f'{persist}.LostModuleId := 1;', 'END_IF;',
              # A corrupt commissioned catalog fails closed; never invent names.
              f'FOR {i} := 0 TO {c}.Count - 1 DO',
              f'IF ({c}.CodeLength[{i}] < 1) OR ({c}.CodeLength[{i}] > {CODE_MAX}) OR ({array}[{i}].SchemaVersion <> {version}) THEN',
              f'{c}.Count := 0;', f'{persist}.RestoreLost := 1;', 'END_IF;',
              f'FOR {b} := 0 TO {CODE_MAX - 1} DO', f'IF {b} < {c}.CodeLength[{i}] THEN',
              f'IF ({c}.CodeBytes[{i} * {CODE_MAX} + {b}] < 33) OR ({c}.CodeBytes[{i} * {CODE_MAX} + {b}] > 126) THEN',
              f'{c}.Count := 0;', f'{persist}.RestoreLost := 1;', 'END_IF;', 'END_IF;', 'END_FOR;',
              f'FOR {j} := 0 TO {i} - 1 DO',
              f'IF {c}.CodeLength[{i}] = {c}.CodeLength[{j}] THEN',
              f'{gen.config.candidate_tag(app)} := 1;',
              f'FOR {b} := 0 TO {CODE_MAX - 1} DO',
              f'IF {b} < {c}.CodeLength[{i}] THEN',
              f'IF {c}.CodeBytes[{i} * {CODE_MAX} + {b}] <> {c}.CodeBytes[{j} * {CODE_MAX} + {b}] THEN {gen.config.candidate_tag(app)} := 0; END_IF;',
              'END_IF;', 'END_FOR;',
              f'IF {gen.config.candidate_tag(app)} <> 0 THEN {c}.Count := 0; {persist}.RestoreLost := 1; END_IF;',
              'END_IF;', 'END_FOR;', 'END_FOR;']
    return lines


def validate_create(app, q, s):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    import fraktal_ab_sets as sets
    req, unit, c = mb.request_tag_name(app), f'FRK_{app.name}_Unit', tag(app)
    i, j, b = sets.scratch_names(app)
    reject = mf.numeric_key(app, sets.REJECTED_KEY)
    if not app.model_capacity:
        return [f'{s}.Reason := {reject};']
    lines = [f'IF ({c}.SchemaVersion <> 1) OR ({c}.Count < 1) OR ({c}.Count >= {app.model_capacity}) THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Kind <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF ({req}.BoolValue < 0) OR ({req}.BoolValue > 1) THEN {s}.Reason := {reject}; END_IF;',
             f'FOR {b} := 0 TO {CODE_MAX - 1} DO', f'IF {b} < {q}.NameLength THEN',
             f'IF ({q}.NameBytes[{b}] < 33) OR ({q}.NameBytes[{b}] > 126) THEN {s}.Reason := {reject}; END_IF;', 'END_IF;', 'END_FOR;',
             f'IF {s}.Reason = 0 THEN',
             f'FOR {i} := 0 TO {c}.Count - 1 DO',
             f'IF {c}.CodeLength[{i}] = {q}.NameLength THEN', f'{j} := 1;',
             f'FOR {b} := 0 TO {CODE_MAX - 1} DO',
             f'IF {b} < {q}.NameLength THEN',
             f'IF {c}.CodeBytes[{i} * {CODE_MAX} + {b}] <> {q}.NameBytes[{b}] THEN {j} := 0; END_IF;',
             'END_IF;', 'END_FOR;',
             f'IF {j} <> 0 THEN {s}.Reason := {reject}; END_IF;', 'END_IF;', 'END_FOR;', 'END_IF;',
             f'{s}.ModelOrdinal := {req}.IntValue;',
             f'IF {s}.ModelOrdinal = 0 THEN {s}.ModelOrdinal := {unit}.ModelOrdinal; END_IF;',
             f'IF {req}.BoolValue = 0 THEN',
             f'IF ({s}.ModelOrdinal < 1) OR ({s}.ModelOrdinal > {c}.Count) THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Count <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {s}.Reason = 0 THEN',
             f'IF {gen.model_cfg_tag(app)}[{s}.ModelOrdinal - 1].SchemaVersion <> {gen.model_cfg_schema_version(app)} THEN {s}.Reason := {reject}; END_IF;', 'END_IF;',
             f'ELSIF {q}.Count <> {len(gen.model_scoped_members(app))} THEN {s}.Reason := {reject}; END_IF;']
    for ordinal, record, member in gen.editable_values(app):
        if not gen.is_model_scoped(app, record, member.name):
            continue
        value = f'{gen.model_cfg_tag(app)}[{s}.ModelOrdinal - 1].{member.name}'
        lines += [f'IF ({req}.BoolValue = 0) AND ({s}.Reason = 0) THEN',
                  f'IF {sets.range_rejected(member, value)} THEN {s}.Reason := {reject}; END_IF;',
                  f'{s}.Snapshot[{ordinal - 1}] := {value};', 'END_IF;']
    if app.access_users is not None:
        import fraktal_ab_data_access as data
        import fraktal_ab_access as access
        ordinals = [str(o - 1) for o, r, m in gen.editable_values(app)
                    if gen.is_model_scoped(app, r, m.name)]
        wanted = ' OR '.join(f'({i} = {o})' for o in ordinals)
        lines += [f'FOR {i} := 0 TO {len(gen.editable_values(app)) - 1} DO',
                  f'IF {wanted} THEN']
        for write in (False, True):
            lines += data.check_value(app, i + ' + 1', for_write=write)
            lines += [f'IF {access.tag(app, "Work")}.Permitted = 0 THEN {s}.Reason := {mf.numeric_key(app, access.DENIED)}; END_IF;']
        lines += ['END_IF;', 'END_FOR;']
    return lines


def commit_create(app, q, s):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_sets as sets
    c, array = tag(app), gen.model_cfg_tag(app)
    req = mb.request_tag_name(app)
    i, j, b = sets.scratch_names(app)
    lines = [f'IF {req}.BoolValue <> 0 THEN', f'FOR {i} := 0 TO {q}.Count - 1 DO', f'CASE {q}.Ordinal[{i}] OF']
    for ordinal, record, member in gen.editable_values(app):
        if gen.is_model_scoped(app, record, member.name):
            lines += [f'{ordinal}: {s}.Snapshot[{ordinal - 1}] := {q}.Value[{i}];']
    lines += ['ELSE', '(* validated before commit *)', 'END_CASE;', 'END_FOR;', 'END_IF;']
    for ordinal, record, member in gen.editable_values(app):
        if gen.is_model_scoped(app, record, member.name):
            lines += [f'{array}[{c}.Count].{member.name} := {s}.Snapshot[{ordinal - 1}];']
    lines += [f'{array}[{c}.Count].SchemaVersion := {gen.model_cfg_schema_version(app)};',
              f'{c}.CodeLength[{c}.Count] := {q}.NameLength;',
              f'FOR {b} := 0 TO {CODE_MAX - 1} DO',
              f'{c}.CodeBytes[{c}.Count * {CODE_MAX} + {b}] := {q}.NameBytes[{b}];', 'END_FOR;',
              f'{c}.Count := {c}.Count + 1; (* publication marker last; inactive *)']
    return lines


def decode(app, raw):
    if raw is not None and raw['Count'] == 0:
        return []  # restore loss remains visible; no selectable recipe is invented
    if raw is None or raw['SchemaVersion'] != 1 or not 1 <= raw['Count'] <= app.model_capacity:
        raise ValueError('unreadable or invalid PLC model catalog')
    codes = []
    for index in range(raw['Count']):
        length = raw['CodeLength'][index]
        if not 1 <= length <= CODE_MAX:
            raise ValueError('invalid model code length')
        data = raw['CodeBytes'][index * CODE_MAX:index * CODE_MAX + length]
        if any(not 33 <= v <= 126 for v in data):
            raise ValueError('invalid model code bytes')
        code = ''.join(map(chr, data))
        if code in codes:
            raise ValueError('duplicate PLC model code')
        codes.append(code)
    return codes


def read(comm, app):
    if not app.model_capacity:
        return [m.code for m in app.models]
    import fraktal_ab_press_execute as execute
    return decode(app, execute.read_layout(comm, tag(app), members(app)))
