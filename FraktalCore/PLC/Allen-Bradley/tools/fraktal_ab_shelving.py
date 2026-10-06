"""Core 8.10 annunciation shelves, owned by the generated root alarm log.

TC3's source+description identity, capped whole-second duration and lifecycle
events. Countdown uses the binding's task-duration clock, like its other
durations; calendar time is presentation only and cannot extend a shelf.
"""
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as mf
import fraktal_ab_reasons as reasons

MAX_SHELF_S = 28800  # pinned to TC3 PL_Fraktal by test
IDENTITY = 'std.error.alarmIdentityNotUnique'
REJECTED = mb.REJECTED_KEY
SHELVED = 'std.audit.alarmShelved'
UNSHELVED = 'std.audit.alarmUnshelved'
KEYS = (IDENTITY, SHELVED, UNSHELVED)


def tag(app):
    return f'FRK_{app.name}_AlarmShelfWork'


def members():
    return (*(decl.scalar(n) for n in ('Index', 'Slot', 'Matches', 'ModuleId',
                                      'Reason', 'Byte', 'Seconds', 'Allowed')),
            decl.duration_ms('RemainingMs', dimension=gen.ALARM_ACTIVE))


def record():
    return decl.Record('FRK_T_AlarmShelfWorkV1', members())


def clear(app, slot):
    a = gen.alarm_active_tag(app)
    return [f'{a}.ActShelved[{slot}] := 0;',
        f'{tag(app)}.RemainingMs[{slot}] := 0;']


def routine_name(app):
    return f'FRK_{app.name}_AlarmShelfRequest'


def _match(app, member):
    # Seconds/Slot are temporary length/key-index storage until the alarm slot
    # is resolved. Both were already allocated: no second string/key table.
    w, q = tag(app), mb.request_tag_name(app)
    expected = f'FRK_{app.name}_MfLocalization[{w}.Slot].PortableKey'
    return [f'{w}.Matches := 1;',
            f'FOR {w}.Byte := 0 TO {w}.Seconds - 1 DO',
            f'IF {q}.{member}.DATA[{w}.Byte] <> {expected}.DATA[{w}.Byte] THEN {w}.Matches := 0; END_IF;',
            'END_FOR;']


def _identity(app):
    w, q, a = tag(app), mb.request_tag_name(app), gen.alarm_active_tag(app)
    i, h = w + '.Index', mf.header_tag(app)
    modules, rationale = f'FRK_{app.name}_MfModules', f'FRK_{app.name}_MfRationalization'
    locale = f'FRK_{app.name}_MfLocalization[{w}.Slot].PortableKey'
    rows, width = mf.content(app), mf.key_string_length(app)
    lines = [f'{w}.ModuleId := 0;', f'{w}.Reason := 0;', f'{w}.Allowed := 0;',
             f'IF ({h}.Valid = 1) AND ({h}.Truncated = 0) THEN',
             f'IF ({h}.ModulesCount = {len(rows["Modules"])}) AND ({h}.RationalizationCount = {len(rows["Rationalization"])}) AND ({h}.LocalizationCount = {len(rows["Localization"])}) THEN',
             f'FOR {i} := 0 TO {len(rows["Modules"]) - 1} DO',
             f'{w}.Slot := {modules}[{i}].CanonicalPathKey - 1;',
             f'IF ({w}.Slot >= 0) AND ({w}.Slot < {len(rows["Localization"])}) THEN',
             f'{w}.Seconds := {locale}.LEN;',
             f'IF ({w}.Seconds > 0) AND ({w}.Seconds <= {min(width, mb.TARGET_PATH_LENGTH)}) AND ({q}.TargetPath.LEN = {w}.Seconds) THEN',
             *_match(app, 'TargetPath'),
             f'IF {w}.Matches = 1 THEN {w}.ModuleId := {modules}[{i}].ModuleId; END_IF;',
             'END_IF;', 'END_IF;', 'END_FOR;',
             f'FOR {i} := 0 TO {len(rows["Rationalization"]) - 1} DO',
             f'{w}.Slot := {rationale}[{i}].ActionKey - 1;',
             f'IF ({w}.Slot >= 0) AND ({w}.Slot < {len(rows["Localization"])}) THEN',
             # Manifest ActionKey is reason_key + '.action' by construction.
             # Compare its stem; the same registry row owns permission too.
             f'{w}.Seconds := {locale}.LEN - 7;',
             f'IF ({w}.Seconds > 0) AND ({w}.Seconds <= {min(width - 7, mb.TEXT_VALUE_LENGTH)}) AND ({q}.TextValue.LEN = {w}.Seconds) THEN',
             *_match(app, 'TextValue'),
             f'IF {w}.Matches = 1 THEN', f'{w}.Reason := {rationale}[{i}].ReasonCode;',
             f'IF ({rationale}[{i}].Shelvable = 1) AND (({rationale}[{i}].Category = {reasons.CATEGORY["PROCESS"]}) OR ({rationale}[{i}].Category = {reasons.CATEGORY["SYSTEM"]})) THEN',
             f'{w}.Allowed := 1;', 'ELSE', f'{w}.Allowed := 0;', 'END_IF;',
             'END_IF;', 'END_IF;', 'END_IF;', 'END_FOR;', 'END_IF;', 'END_IF;',
             f'{w}.Matches := 0;', f'{w}.Slot := -1;',
             f'IF ({w}.ModuleId > 0) AND ({w}.Reason <> 0) THEN',
              f'FOR {i} := 0 TO {gen.ALARM_ACTIVE - 1} DO',
              f'IF ({a}.ActState[{i}] <> {gen.ALARM_CLOSED}) AND ({a}.ActSourceModuleId[{i}] = {w}.ModuleId) AND ({a}.ActReasonCode[{i}] = {w}.Reason) THEN',
              f'{w}.Slot := {i};', f'{w}.Matches := {w}.Matches + 1;', 'END_IF;', 'END_FOR;', 'END_IF;']
    return lines


def _audit(app, key, slot, *, automatic=False):
    import fraktal_ab_access as access
    s = access.tag(app, 'State')
    return access._audit(app, key, str(mb.UNSHELVE_ALARM if key == UNSHELVED else mb.SHELVE_ALARM),
                         '0' if automatic else f'FRK_{app.name}_HmiLastSequence', '1',
                         '0' if automatic else s + '.UserLength', s + '.UserBytes',
                         event_source=f'{gen.alarm_active_tag(app)}.ActSourceModuleId[{slot}]', gate='9')


def dispatch(app):
    if app.access_users is None:
        return []
    return [f'{mb.SHELVE_ALARM},{mb.UNSHELVE_ALARM}: (* Core 8.10: annunciation only *)',
            f'JSR({routine_name(app)},0);']


def handler(app):
    """One bounded helper; mailbox code does not grow with paths or reasons."""
    w, q, a = tag(app), mb.request_tag_name(app), gen.alarm_active_tag(app)
    slot = w + '.Slot'
    lines = [*_identity(app),
             f'IF {w}.Matches <> 1 THEN', *mb._refuse(app, IDENTITY), 'ELSE',
             f'IF {q}.Kind = {mb.SHELVE_ALARM} THEN',
              f'IF ({w}.Allowed = 0) OR ({q}.DurationMs < 1000) THEN', *mb._refuse(app, REJECTED), 'ELSE',
              # Logix DINT division rounds: remove the remainder first, as the
              # existing wall-clock and configuration integer divisions do.
              f'{w}.Seconds := ({q}.DurationMs - ({q}.DurationMs MOD 1000)) / 1000;',
              f'IF {w}.Seconds > {MAX_SHELF_S} THEN {w}.Seconds := {MAX_SHELF_S}; END_IF;',
              f'{a}.ActShelved[{slot}] := 1;',
              f'{w}.RemainingMs[{slot}] := {w}.Seconds * 1000;',
              *_audit(app, SHELVED, slot), *mb._accept(app), 'END_IF;', 'ELSE',
              f'IF {a}.ActShelved[{slot}] = 0 THEN', *mb._refuse(app, REJECTED), 'ELSE',
              f'{a}.ActShelved[{slot}] := 0;', f'{w}.RemainingMs[{slot}] := 0;',
              *_audit(app, UNSHELVED, slot), *mb._accept(app), 'END_IF;', 'END_IF;', 'END_IF;']
    return lines


def cyclic(app):
    if app.access_users is None:
        return []
    a, w = gen.alarm_active_tag(app), tag(app)
    i = w + '.Index'
    return ['(* Core 8.10: bounded task-duration countdown; no wall-clock dependency *)',
            f'FOR {i} := 0 TO {gen.ALARM_ACTIVE - 1} DO',
            f'IF {a}.ActShelved[{i}] <> 0 THEN',
            f'IF {w}.RemainingMs[{i}] > FRK_{app.name}_Unit.Par_TaskPeriodMs THEN',
            f'{w}.RemainingMs[{i}] := {w}.RemainingMs[{i}] - FRK_{app.name}_Unit.Par_TaskPeriodMs;', 'ELSE',
            f'{a}.ActShelved[{i}] := 0;', f'{w}.RemainingMs[{i}] := 0;',
            *_audit(app, UNSHELVED, i, automatic=True), 'END_IF;', 'END_IF;', 'END_FOR;']
