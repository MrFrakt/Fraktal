"""Core 3.8c: capture rejoins the ordinary controller configuration write.

The gateway translates identity and revision; the PLC samples the published
source, validates, commits and records the accepted value. It never consumes a
client's candidate for a capture. Access audits use the controller session.
"""
import fraktal_ab_declaration as decl
from fraktal_ab_models import ordinal_guard

AUDIT_CAPACITY = 16
CAPTURE_UNAVAILABLE_KEY = "project.mailbox.refused.capture_not_registered"
CAPTURE_SETUP_KEY = "project.mailbox.refused.capture_needs_setup"
CAPTURE_REVISION_KEY = "project.mailbox.refused.config_revision_stale"


def audit_name():
    return "FRK_T_ConfigAuditV1"


def audit_tag(app):
    return f"FRK_{app.name}_ConfigAudit"


def audit_members():
    import fraktal_ab_mailbox as mailbox
    return (decl.scalar("SchemaVersion", initial=1), decl.scalar("Head"),
            decl.scalar("Count"),
            *(decl.scalar(n, dimension=AUDIT_CAPACITY) for n in
              ("Sequence", "Kind", "Capability", "Value", "SourceKey", "ModelOrdinal", "Revision", "Date", "Clock", "UserLength")),
            decl.scalar("UserBytes", dimension=AUDIT_CAPACITY * mailbox.USER_LENGTH))


def candidate_tag(app):
    return f"FRK_{app.name}_ConfigCandidate"


def audit_routine_name(app):
    return f'FRK_{app.name}_ConfigRecordAudit'


def audit_logic(app):
    """One accepted-write audit body for every capability; no new storage."""
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    a, req = audit_tag(app), mb.request_tag_name(app)
    import fraktal_ab_access as access
    user_length = access.tag(app, 'State') + '.UserLength' if app.access_users is not None else req + '.User.LEN'
    user_bytes = access.tag(app, 'State') + '.UserBytes' if app.access_users is not None else req + '.User.DATA'
    slot = f"{a}.Head - 1"
    lines = [f"{a}.Head := ({a}.Head MOD {AUDIT_CAPACITY}) + 1;",
            f"IF {a}.Count < {AUDIT_CAPACITY} THEN {a}.Count := {a}.Count + 1; END_IF;",
            f"{a}.Sequence[{slot}] := {req}.Sequence;",
            f"{a}.Kind[{slot}] := {req}.Kind;",
            f"{a}.Capability[{slot}] := {req}.{mb.CONFIG_ORDINAL_MEMBER};",
            f"{a}.Value[{slot}] := {candidate_tag(app)};",
            f"{a}.Revision[{slot}] := {mf.config_revision(app)};",
            f"{a}.ModelOrdinal[{slot}] := 0;",
            f"{a}.SourceKey[{slot}] := 0;"]
    values = gen.editable_values(app)
    ordinals = [str(ordinal) for ordinal, record, member in values
                if gen.is_model_scoped(app, record, member.name)]
    if ordinals:
        lines += [f'CASE {req}.{mb.CONFIG_ORDINAL_MEMBER} OF', ','.join(ordinals) + ':',
                  f'{a}.ModelOrdinal[{slot}] := FRK_{app.name}_Unit.ModelOrdinal;',
                  f'IF ({req}.Kind = {mb.WRITE_CONFIG}) AND ({req}.DurationMs <> 0) THEN {a}.ModelOrdinal[{slot}] := {req}.DurationMs; END_IF;',
                  'ELSE', '(* Station values have no model ordinal. *)', 'END_CASE;']
    captures = [(ordinal, member) for ordinal, _, member in values if member.capture_source]
    if captures:
        lines += [f'IF {req}.Kind = {mb.CAPTURE_CONFIG} THEN', f'CASE {req}.{mb.CONFIG_ORDINAL_MEMBER} OF']
        lines += [f'{ordinal}: {a}.SourceKey[{slot}] := {mf.numeric_key(app, member.capture_source)};'
                  for ordinal, member in captures]
        lines += ['ELSE', '(* Only registered captures reach the audit. *)', 'END_CASE;', 'END_IF;']
    return lines + [
            f"{a}.Date[{slot}] := FRK_{app.name}_NowDate;",
            f"{a}.Clock[{slot}] := FRK_{app.name}_NowTime;",
            # Enabled providers supply the authenticated controller actor;
            # legacy declarations retain the request's explicitly claimed actor.
            f"{a}.UserLength[{slot}] := {user_length};",
            f"FOR FRK_{app.name}_HmiWipe := 0 TO {mb.USER_LENGTH - 1} DO",
            f"IF FRK_{app.name}_HmiWipe < {user_length} THEN",
            f"{a}.UserBytes[({slot}) * {mb.USER_LENGTH} + FRK_{app.name}_HmiWipe] := {user_bytes}[FRK_{app.name}_HmiWipe];",
            "ELSE",
            f"{a}.UserBytes[({slot}) * {mb.USER_LENGTH} + FRK_{app.name}_HmiWipe] := 0;",
            "END_IF;",
            "END_FOR;"]


def scratch_names(app):
    """Transient mailbox bounds/flags; set counters have no cross-request state."""
    if app.config_sets:
        from fraktal_ab_sets import scratch_names as set_scratch
        return set_scratch(app)
    return tuple(f'FRK_{app.name}_Config{n}' for n in ('Minimum', 'Maximum', 'Flags'))


def write_routine_name(app):
    return f'FRK_{app.name}_ConfigWrite'


def capability_fact_groups(app, facts):
    """One CASE arm for capabilities with identical immutable facts.

    Group only fact selection, never value sampling, permission checks or
    commit addresses. First-encounter order keeps generated output stable.
    """
    import fraktal_ab_generate as gen
    groups = {}
    for ordinal, record, member in gen.editable_values(app):
        groups.setdefault(facts(record, member), []).append(str(ordinal))
    return [(','.join(ordinals), values) for values, ordinals in groups.items()]


def write_dispatch(app, *, use_routine=False):
    import fraktal_ab_mailbox as mb
    branch = f'{mb.WRITE_CONFIG},{mb.CAPTURE_CONFIG}: (* WRITE_CONFIG / CAPTURE_CONFIG *)'
    body = [f'JSR({write_routine_name(app)},0);'] if use_routine else write_logic(app)
    return [branch, *body]


def write_logic(app):
    """Validate/capture/commit one value, still inside the mailbox access gate."""
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    req, unit = mb.request_tag_name(app), f"FRK_{app.name}_Unit"
    value = candidate_tag(app)
    low, high, flags = scratch_names(app)
    ordinal = f'{req}.{mb.CONFIG_ORDINAL_MEMBER}'
    model = f'{req}.{mb.CONFIG_MODEL_MEMBER}'
    names = gen.Names(app, in_aoi=False)
    values = gen.editable_values(app)
    lines = [f'{flags} := -1;', f'CASE {ordinal} OF']
    # The table selects facts; validation and acceptance are written once.
    # bit 0: READY; bit 1: model scoped; bit 2: capture registered.
    groups = capability_fact_groups(app, lambda record, member: (
        member.minimum, member.maximum, int(member.requires_ready)
        + 2 * int(gen.is_model_scoped(app, record, member.name)) + 4 * int(bool(member.capture_source))))
    for ordinals, (minimum, maximum, bits) in groups:
        lines += [f'{ordinals}:', f'{low} := {minimum};', f'{high} := {maximum};', f'{flags} := {bits};']
    lines += ['ELSE', *mb._refuse(app, mb.CONFIG_KEY_UNKNOWN_KEY), 'END_CASE;',
              f'IF {flags} >= 0 THEN']
    if decl.live_documents(app):
        # Core 3.8b: the live documents' restore would replay over this write.
        lines += [f'IF {gen.config_restoring(app)} THEN', *mb._refuse(app, gen.CONFIG_RESTORING_KEY), 'END_IF;']
    if app.access_users is not None:
        import fraktal_ab_data_access as data
        lines += data.check_value(app, ordinal)
    diagnostic = mb._response(app, 'DiagnosticKey')
    lines += [f'IF {diagnostic} = 0 THEN', f'{value} := {req}.{mb.CONFIG_VALUE_MEMBER};',
              f'IF {req}.Kind = {mb.CAPTURE_CONFIG} THEN', f'IF {flags} < 4 THEN',
              *mb._refuse(app, CAPTURE_UNAVAILABLE_KEY), 'ELSE']
    captures = [(number, member) for number, _, member in values if member.capture_source]
    if captures:
        lines += [f'CASE {ordinal} OF']
        lines += [f'{number}: {value} := {gen.capture_source_tag(app, member.capture_source)};'
                  for number, member in captures]
        lines += ['ELSE', '(* The selected flag guarantees a registered source. *)', 'END_CASE;',
              f'IF {req}.DurationMs <> {mf.config_revision(app)} THEN',
              *mb._refuse(app, CAPTURE_REVISION_KEY),
              f'ELSIF ({unit}.Mode <> {app.manual_mode}) OR ({unit}.Error <> 0) OR ({unit}.Aborted <> 0) THEN',
              *mb._refuse(app, CAPTURE_SETUP_KEY), 'END_IF;']
        for permit in app.start_permits:
            lines += [f'IF NOT ({gen.conds_st(permit.conditions, names)}) THEN', *mb._refuse(app, permit.key), 'END_IF;']
    lines += ['END_IF;', 'END_IF;', f'IF {diagnostic} = 0 THEN',
              f'IF ({flags} MOD 2) <> 0 THEN',
              f'IF (({flags} MOD 4) < 2) OR ({req}.Kind = {mb.CAPTURE_CONFIG}) OR ({model} = 0) THEN',
              f'IF {unit}.Running <> 0 THEN', *mb._refuse(app, mb.CONFIG_NOT_READY_KEY), 'END_IF;', 'END_IF;', 'END_IF;',
              f'IF {diagnostic} = 0 THEN',
              f'IF ({value} < {low}) OR ({value} > {high}) THEN', *mb._refuse(app, mb.CONFIG_OUT_OF_RANGE_KEY), 'END_IF;', 'END_IF;',
              f'IF ({diagnostic} = 0) AND (({flags} MOD 4) >= 2) AND ({req}.Kind = {mb.WRITE_CONFIG}) AND ({model} <> 0) THEN',
              f'IF NOT ({ordinal_guard(app, model)}) THEN', *mb._refuse(app, mb.MODEL_NOT_DECLARED_KEY), 'END_IF;', 'END_IF;',
              f'IF {diagnostic} = 0 THEN']
    if app.line is not None:
        import fraktal_ab_line as line
        lines += line.write_validate(app, ordinal, value)
    lines += [f'IF {diagnostic} = 0 THEN', f'CASE {ordinal} OF']
    for number, record, member in values:
        lines += [f'{number}:']
        assign = f'{record.name}Tag.{member.name} := {value};'
        if gen.is_model_scoped(app, record, member.name):
            lines += [f'IF ({req}.Kind = {mb.CAPTURE_CONFIG}) OR ({model} = 0) THEN', assign,
                      'ELSE', f'{gen.model_cfg_tag(app)}[{model} - 1].{member.name} := {value};', 'END_IF;']
        else:
            lines += [assign]
    lines += ['ELSE', '(* The first CASE validated the ordinal. *)', 'END_CASE;']
    if app.line is not None:
        numbers = ','.join(str(o) for o, r, _ in values if r.line_cfg)
        lines += [f'CASE {ordinal} OF', numbers + ':', *line.accepted(app),
                  'ELSE', '(* Another configuration kind. *)', 'END_CASE;']
    return lines + [
                    *mb._accept(app), f'JSR({audit_routine_name(app)},0);', 'END_IF;', 'END_IF;', 'END_IF;', 'END_IF;', 'END_IF;']
