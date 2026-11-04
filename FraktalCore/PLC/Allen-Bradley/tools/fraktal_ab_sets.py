"""Core 3.8b parameter sets: PLC transactions, portable lines and host storage.

The declaration's editable walk owns the schema. The host transports documents;
the generated controller code stages, validates and commits a load in one scan.
Model loads deliberately refuse, as TC3 does until recipe-store integration.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import fraktal_ab_declaration as decl

# The document format and its store are declaration-free and live with the
# host adapter; this module re-exports them for engineering callers.
from fraktal_ab_set_documents import (  # noqa: F401
    MAX_SETS, MAX_RECORDS, LINE_MAX, NAME_MAX, SetRejected, _text, _int, HEADER_FIELDS, RECORD_FIELDS,
    checked_header, checked_record, _pairs, parse_line, render_line, checked_document, replace_text,
    FileStore, Session, empty_values, list_values)
WINDOW_MS = 5000
AUDIT_CAPACITY = 16
SET_KINDS = (28, 29, 30, 32, 33, 35, 37, 38)
REJECTED_KEY = 'std.error.configSetRejected'
APPLIED_KEY = 'std.audit.configSetApplied'
STORE_FAILED_KEY = 'std.error.configPersistFailed'
MODEL_KEY = 'project.mailbox.refused.config_set_model_load'
KEYS = (REJECTED_KEY, APPLIED_KEY, STORE_FAILED_KEY, MODEL_KEY)


def request_name():
    return 'FRK_T_ConfigSetRequestV1'


def request_members():
    # Appended to HmiRequestV2. Only the broker can write these via WebSocket;
    # native CIP remains untrusted, so every numeric field is checked in ST.
    return (decl.scalar('SchemaVersion', initial=1),
            *(decl.scalar(n) for n in ('Sequence', 'Operation', 'Commit', 'Valid', 'RootId', 'SetSchema',
              'ConfigRev', 'Kind', 'Count', 'NameLength', 'StoreAck', 'StoreResult')),
            decl.scalar('NameBytes', dimension=NAME_MAX),
            *(decl.scalar(n, dimension=MAX_RECORDS) for n in
              ('Ordinal', 'Revision', 'RecordKind', 'ValueType', 'Value')))


def state_version(app):
    return 3 if app.line is not None else 1


def state_name(app=None):
    return f'FRK_T_ConfigSetStateV{state_version(app) if app is not None else 1}'


def state_tag(app):
    return f'FRK_{app.name}_ConfigSetState'


def staged_tag(app):
    return f'FRK_{app.name}_SetStaged'


def state_members(app):
    import fraktal_ab_generate as gen
    return (decl.scalar('SchemaVersion', initial=state_version(app)),
            *(decl.scalar(n) for n in ('Sequence', 'Count', 'RejectIndex', 'Reason',
              'ModelOrdinal', 'Date', 'Clock', 'TimeSynchronized', 'PendingMs', 'PendingSequence', 'PendingSlot',
              'Head', 'AuditCount')),
            decl.scalar('Snapshot', dimension=max(1, len(gen.editable_values(app)))),
            *(decl.scalar(n, dimension=AUDIT_CAPACITY) for n in
              ('AuditSequence', 'AuditKind', 'AuditRecords', 'AuditReason',
               'AuditAccepted', 'AuditRejectIndex', 'AuditDate', 'AuditClock',
               'AuditNameLength', 'AuditUserLength')),
            decl.scalar('AuditNameBytes', dimension=AUDIT_CAPACITY * NAME_MAX),
            decl.scalar('AuditUserBytes', dimension=AUDIT_CAPACITY * 32))


def scratch_names(app):
    return tuple(f'FRK_{app.name}_Set{n}' for n in ('Index', 'Prior', 'Copy'))


def config_kind(record):
    return 2 if record.line_cfg else 1 if record.station_cfg else 0


def value_type(member):
    return 3 if member.kind == 'duration_ms' else 2 if member.kind == 'boolean' else 0


def revision_rejected(app, value):
    import dataclasses
    import fraktal_ab_manifest as mf
    revisions = {mf.config_revision(app)}
    # Live documents add one release text, not a value: sets saved before them
    # carry the earlier identity. Every earlier build predates them, so the
    # historical variants below are of that identity, never hypothetical
    # live builds (Studio v33 compiles at most five chained ANDs).
    earlier = dataclasses.replace(app, config_medium=None) if decl.live_documents(app) else app
    variants = [earlier]
    if app.line is not None:
        variants.append(dataclasses.replace(earlier, line=None, records=tuple(r for r in app.records if not r.line_cfg)))
    # The catalog extension changes build identity, not the declared value
    # schema. Recognize that exact prior content; all other revisions refuse.
    if app.model_capacity:
        variants += [dataclasses.replace(item, model_capacity=0) for item in variants[:]]
    if app.signal_tower is not None:
        # Tower convention/output fields change discovery, never the editable
        # value schema. Accept only the exact same declaration without it.
        variants += [dataclasses.replace(item,signal_tower=None) for item in (app,*variants)]
    import fraktal_ab_resources as resources
    import fraktal_ab_genealogy as genealogy
    if genealogy.enabled(app):
        variants += [genealogy.without(item) for item in (app,*variants)]
    if resources.text_enabled(app):
        variants += [resources.without_text(item) for item in (app,*variants)]
    if resources.enabled(app):
        variants += [resources.without(item) for item in (app,*variants)]
    if app.canonical_publication_stage == 13:
        # S3k versions the release-report owner and localization catalogue,
        # changing publication identity without changing configuration Records.
        # Derive the exact predecessor from this declaration; a foreign station
        # or changed value schema still has a different revision and refuses.
        variants.append(dataclasses.replace(app, canonical_publication_stage=12))
    revisions.update(mf.config_revision(item) for item in variants)
    terms = [f'({value} <> {revision})' for revision in sorted(revisions)]
    if len(terms) <= 5:
        return ' AND '.join(terms)
    # The v33 compiler rejects more than five chained terms at one level.
    return ' AND '.join('('+' AND '.join(terms[i:i+5])+')' for i in range(0,len(terms),5))


def range_rejected(member, value):
    """One range predicate for ordinary writes, capture and set validation."""
    return f'({value} < {member.minimum}) OR ({value} > {member.maximum})'


def revision_guard(app, value, reason, reject):
    # S3k's predecessor adds one exact revision. Repeating an array-member
    # operand in every comparison exceeds the native compiler's operand limit.
    # This scratch is free here and the following duplicate loop initializes it.
    target=scratch_names(app)[1] if app.canonical_publication_stage==13 else value
    prefix=[f'{target} := {value};'] if target!=value else []
    return prefix+[f'IF {revision_rejected(app,target)} THEN {reason} := {reject}; END_IF;']


def cyclic(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    import fraktal_ab_host_sets as host_sets
    p, s, q = gen.config_persist_tag(app), state_tag(app), mb.request_tag_name(app) + '.ConfigSet'
    # V6.11: the receipt arrives as a STORE job's answer, not a staged member.
    if host_sets.enabled(app):
        q = host_sets.work_tag(app)
    unit, response = f'FRK_{app.name}_Unit', mb.response_tag_name(app)
    failure = mf.numeric_key(app, STORE_FAILED_KEY)
    return [f'{p}.WindowMs := {WINDOW_MS};',
            f'IF {p}.Pending <> 0 THEN',
            f'IF ({q}.StoreAck = {s}.PendingSequence) AND ({q}.StoreResult <> 0) THEN',
            f'{p}.Pending := 0;',
            f'{p}.Failed := 0;',
            f'IF {q}.StoreResult <> 1 THEN {p}.Failed := 1; END_IF;',
            f'ELSIF {s}.PendingMs >= {WINDOW_MS} THEN',
            f'{p}.Pending := 0;', f'{p}.Failed := 1;',
            'ELSE', f'{s}.PendingMs := {s}.PendingMs + {app.task_period_ms};',
            'END_IF;',
            f'IF {p}.Failed <> 0 THEN',
            f'IF {s}.AuditSequence[{s}.PendingSlot] = {s}.PendingSequence THEN',
            f'{s}.AuditAccepted[{s}.PendingSlot] := 0;', f'{s}.AuditReason[{s}.PendingSlot] := {failure};', 'END_IF;',
            f'{unit}.ReportedReason := {app.reasons["CONFIG_PERSIST_FAILED"]};',
            f'{unit}.ReportedSource := 0;', f'{unit}.ReportedCount := {unit}.ReportedCount + 1;',
            f'IF {mb.acknowledged_sequence(app)} = {s}.PendingSequence THEN',
            f'{response}.Accepted := 0;', f'{response}.DiagnosticKey := {failure};', 'END_IF;',
            'END_IF;', 'END_IF;']


def routine_name(app):
    return f'FRK_{app.name}_ConfigSets'


def dispatch(app, *, use_routine=False):
    import fraktal_ab_host_sets as host_sets
    if host_sets.enabled(app):
        # V6.11: the host-set entry parks a command that needs host data.
        return [','.join(map(str, host_sets.SERVED)) + ': (* parameter sets *)',
                f'JSR({host_sets.entry_routine(app)},0);']
    branch = ','.join(map(str, SET_KINDS)) + ': (* parameter sets *)'
    body = [f'JSR({routine_name(app)},0);'] if use_routine else dispatch_logic(app)
    return [branch, *body]


def dispatch_logic(app):
    """One staged set transaction; the caller owns acknowledgement/wipe order."""
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    import fraktal_ab_manifest as mf
    req, unit = mb.request_tag_name(app), f'FRK_{app.name}_Unit'
    q, s, p = staged_tag(app), state_tag(app), gen.config_persist_tag(app)
    i, j, b = scratch_names(app)
    reject = mf.numeric_key(app, REJECTED_KEY)
    import fraktal_ab_models as models
    # Core 3.8b live documents: while the controller restores (station image
    # still unstamped), a model document may load into its bank and the
    # station document answers the restore. Otherwise models stay refused.
    live = decl.live_documents(app)
    restoring = gen.config_restoring(app) if live else ''
    keep = f'NOT {restoring}' if live else ''
    model_ordinal = f'{req}.DurationMs'
    import fraktal_ab_host_sets as host_sets
    # V6.11 stages through the controller's own host-set record, not the request.
    source = host_sets.staged_tag(app) if host_sets.enabled(app) else req + '.ConfigSet'
    lines = [f'CPS({source},{q},1); (* immutable controller staging *)',
             f'{s}.Sequence := FRK_{app.name}_HmiLastSequence;', f'{s}.Count := {q}.Count;',
             f'{s}.RejectIndex := 0;', f'{s}.Reason := 0;',
             # List/export are permission-gated reads in TC3, without READY.
             f'IF ({q}.Operation <> {mb.LIST_CONFIG_SETS}) AND ({q}.Operation <> {mb.EXPORT_CONFIG_SET}) AND ({q}.Operation <> {mb.EXPORT_CURRENT_CONFIG}) AND ({q}.Operation <> {mb.CREATE_MODEL}) THEN',
             f'IF {unit}.Running <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {unit}.Error <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {unit}.Aborted <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {unit}.Complete <> 0 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {p}.Pending <> 0 THEN {s}.Reason := {reject}; END_IF;',
             'END_IF;',
             # A set saved before the restore answered holds unrestored values.
             *([f'IF ({q}.Operation = {mb.SAVE_CONFIG_SET}) AND {restoring} THEN {s}.Reason := {reject}; END_IF;']
               if live else []),
             f'IF {q}.SchemaVersion <> 1 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Sequence <> FRK_{app.name}_HmiLastSequence THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Operation <> {req}.Kind THEN {s}.Reason := {reject}; END_IF;',
             f'IF ({q}.Commit < 0) OR ({q}.Commit > 1) THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Valid <> 1 THEN {s}.Reason := {reject}; END_IF;',
             f'IF ({q}.Count < 0) OR ({q}.Count > {MAX_RECORDS}) THEN {s}.Reason := {reject}; END_IF;',
             f'IF ({q}.NameLength < 0) OR ({q}.NameLength > {NAME_MAX}) THEN {s}.Reason := {reject}; END_IF;',
             f'IF ({req}.User.LEN < 0) OR ({req}.User.LEN > {mb.USER_LENGTH}) THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.Operation <> {mb.LIST_CONFIG_SETS} THEN',
             f'IF {q}.NameLength = 0 THEN {s}.Reason := {reject}; END_IF;', 'END_IF;',
             f'IF ({q}.Operation = {mb.SAVE_CONFIG_SET}) OR ({q}.Operation = {mb.LOAD_CONFIG_SET}) OR ({q}.Operation = {mb.EXPORT_CONFIG_SET}) OR ({q}.Operation = {mb.CREATE_MODEL}) OR ({q}.Operation = {mb.EXPORT_CURRENT_CONFIG}) THEN',
             f'IF {q}.RootId <> 1 THEN {s}.Reason := {reject}; END_IF;',
             f'IF {q}.SetSchema <> 1 THEN {s}.Reason := {reject}; END_IF;',
             *revision_guard(app,q+'.ConfigRev',s+'.Reason',reject),
             f'IF ({q}.Kind < 0) OR ({q}.Kind > {2 if app.line is not None else 1}) THEN {s}.Reason := {reject}; END_IF;',
             'END_IF;',
             f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) OR ({q}.Operation = {mb.EXPORT_CONFIG_SET}) OR (({q}.Operation = {mb.CREATE_MODEL}) AND ({req}.BoolValue <> 0)) THEN',
             f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) AND ({q}.Kind = 0) AND ({s}.Reason = 0){" AND " + keep if live else ""} THEN {s}.Reason := {mf.numeric_key(app, MODEL_KEY)}; END_IF;',
             # The restore names the bank it loads, and the active model with
             # its final station load; each is a model the catalog offers.
             *([f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) AND ({q}.Kind <> 2) AND {restoring} AND (({q}.Kind = 0) OR ({model_ordinal} <> 0)) THEN',
                f'IF NOT ({models.ordinal_guard(app, model_ordinal)}) THEN {s}.Reason := {reject}; END_IF;', 'END_IF;']
               if live else []),
             f'IF {s}.Reason = 0 THEN',
             f'FOR {i} := 0 TO {q}.Count - 1 DO',
             f'IF {s}.Reason = 0 THEN',
             *revision_guard(app,q+'.Revision['+i+']',s+'.Reason',reject),
             # Repeated addresses cannot silently overwrite a value twice.
             f'FOR {j} := 0 TO {i} - 1 DO',
             f'IF {q}.Ordinal[{i}] = {q}.Ordinal[{j}] THEN {s}.Reason := {reject}; END_IF;',
             'END_FOR;', f'CASE {q}.Ordinal[{i}] OF']
    import fraktal_ab_config as config
    facts = config.candidate_tag(app)
    # Prior/Copy are free after duplicate checking. The ordinary-write candidate
    # is transient and unused during a set transaction: no new private data.
    groups = config.capability_fact_groups(app, lambda record, member: (
        member.minimum, member.maximum, config_kind(record) * 4 + value_type(member)
        + 16 * int(gen.is_model_scoped(app, record, member.name))))
    for ordinals, (minimum, maximum, encoded) in groups:
        lines += [f'{ordinals}:', f'{j} := {minimum};', f'{b} := {maximum};', f'{facts} := {encoded};']
    lines += ['ELSE', f'{facts} := -1;', f'{s}.Reason := {reject};', 'END_CASE;',
              f'IF {facts} >= 0 THEN',
              f'IF {q}.RecordKind[{i}] <> (({facts} MOD 16) - ({facts} MOD 4)) / 4 THEN {s}.Reason := {reject}; END_IF;',
              f'IF {q}.RecordKind[{i}] <> {q}.Kind THEN {s}.Reason := {reject}; END_IF;',
              f'IF {q}.ValueType[{i}] <> ({facts} MOD 4) THEN {s}.Reason := {reject}; END_IF;',
              f'IF {q}.Operation = {mb.LOAD_CONFIG_SET} THEN',
              (f'IF ({q}.Kind = 0) AND {keep} THEN {s}.Reason := {reject}; END_IF;' if live
               else f'IF {q}.Kind = 0 THEN {s}.Reason := {reject}; END_IF;'), 'END_IF;',
              f'IF {q}.Operation = {mb.CREATE_MODEL} THEN',
              f'IF {facts} < 16 THEN {s}.Reason := {reject}; END_IF;', 'END_IF;',
              f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) OR ({q}.Operation = {mb.CREATE_MODEL}) THEN',
              f'IF ({q}.Value[{i}] < {j}) OR ({q}.Value[{i}] > {b}) THEN {s}.Reason := {reject}; END_IF;',
              'END_IF;', 'END_IF;']
    if app.access_users is not None:
        import fraktal_ab_data_access as data
        import fraktal_ab_access as access
        # Every arm has validated the ordinal; one bounded indexed check owns
        # permission enforcement for the complete staged transaction.
        lines += [f'IF {s}.Reason = 0 THEN',
                  f'IF ({q}.Operation = {mb.LOAD_CONFIG_SET}) OR ({q}.Operation = {mb.CREATE_MODEL}) THEN',
                  *data.check_value(app, q + '.Ordinal[' + i + ']'), 'ELSE',
                  *data.check_value(app, q + '.Ordinal[' + i + ']', for_write=False), 'END_IF;',
                  f'IF {access.tag(app, "Work")}.Permitted = 0 THEN {s}.Reason := {mf.numeric_key(app, access.DENIED)}; END_IF;', 'END_IF;']
    lines += [f'IF {s}.Reason <> 0 THEN {s}.RejectIndex := {i} + 1; END_IF;',
              'END_IF;', 'END_FOR;', 'END_IF;', 'END_IF;']
    import fraktal_ab_models as models
    lines += [f'IF {q}.Operation = {mb.CREATE_MODEL} THEN',
              *models.validate_create(app, q, s), 'END_IF;']
    if app.line is not None:
        import fraktal_ab_line as line
        lines += line.set_validate(app, q, s)
    lines += [f'IF {q}.Operation = {mb.EXPORT_CURRENT_CONFIG} THEN',
              f'{s}.ModelOrdinal := {req}.DurationMs;',
              f'IF {s}.ModelOrdinal = 0 THEN {s}.ModelOrdinal := {unit}.ModelOrdinal; END_IF;',
              f'IF {q}.Kind = 0 THEN', f'IF NOT ({models.ordinal_guard(app, s + ".ModelOrdinal")}) THEN {s}.Reason := {reject}; END_IF;', 'END_IF;']
    if app.access_users is not None:
        import fraktal_ab_data_access as data
        import fraktal_ab_access as access
        lines += [f'FOR {i} := 0 TO {len(gen.editable_values(app)) - 1} DO', f'{j} := 0;', f'CASE {q}.Kind OF']
        for kind in (0, 1, 2):
            ordinals = [str(o - 1) for o, r, _ in gen.editable_values(app) if config_kind(r) == kind]
            if ordinals:
                lines += [f'{kind}:', f'CASE {i} OF', ','.join(ordinals) + f': {j} := 1;', 'ELSE', '(* another configuration kind *)', 'END_CASE;']
        lines += ['ELSE', '(* kind validated above *)', 'END_CASE;', f'IF {j} <> 0 THEN',
                  *data.check_value(app, i + ' + 1', for_write=False),
                  f'IF {access.tag(app, "Work")}.Permitted = 0 THEN {s}.Reason := {mf.numeric_key(app, access.DENIED)}; END_IF;', 'END_IF;', 'END_FOR;']
    lines += ['END_IF;', f'IF {s}.Reason = 0 THEN',
              f'CASE {q}.Operation OF', f'{mb.SAVE_CONFIG_SET},{mb.EXPORT_CURRENT_CONFIG}:',
              f'{s}.Count := 0;', f'IF {q}.Operation = {mb.SAVE_CONFIG_SET} THEN {s}.ModelOrdinal := {unit}.ModelOrdinal; END_IF;',
              f'{s}.Date := FRK_{app.name}_NowDate;', f'{s}.Clock := FRK_{app.name}_NowTime;',
              f'{s}.TimeSynchronized := {gen.health_probe_tag(app)}.TimeIsSynchronized;']
    for kind in (0, 1, 2):
        values = [(ordinal, record, member) for ordinal, record, member in gen.editable_values(app)
                  if config_kind(record) == kind]
        if not values:
            continue
        lines += [f'IF {q}.Kind = {kind} THEN']
        lines += [f'{s}.Snapshot[{ordinal - 1}] := {record.name}Tag.{member.name};'
                  for ordinal, record, member in values]
        scoped = [(ordinal, member) for ordinal, record, member in values
                  if gen.is_model_scoped(app, record, member.name)]
        if scoped:
            lines += [f'IF ({q}.Operation = {mb.EXPORT_CURRENT_CONFIG}) AND ({req}.DurationMs <> 0) THEN']
            lines += [f'{s}.Snapshot[{ordinal - 1}] := {gen.model_cfg_tag(app)}[{s}.ModelOrdinal - 1].{member.name};'
                      for ordinal, member in scoped]
            lines += ['END_IF;']
        lines += [f'{s}.Count := {len(values)};', 'END_IF;']
    lines += [f'{mb.CREATE_MODEL}:', *(models.commit_create(app, q, s) if app.model_capacity else []), f'{mb.LOAD_CONFIG_SET}:',
              '(* Pass two: all checks finished; bounded, infallible commit. *)',
              f'FOR {i} := 0 TO {q}.Count - 1 DO', f'CASE {q}.Ordinal[{i}] OF']
    for ordinal, record, member in gen.editable_values(app):
        if record.station_cfg or record.line_cfg:
            lines += [f'{ordinal}: {record.name}Tag.{member.name} := {q}.Value[{i}];']
        elif live and gen.is_model_scoped(app, record, member.name):
            # Only a restore reaches here (pass one); the provider's bank, never ParCfg.
            lines += [f'{ordinal}: {gen.model_cfg_tag(app)}[{model_ordinal} - 1].{member.name} := {q}.Value[{i}];']
    lines += ['ELSE', '(* Unreachable: pass one rejected unknown capabilities. *)',
              'END_CASE;', 'END_FOR;']
    if app.line is not None:
        lines += [f'IF {q}.Kind = 2 THEN', *line.accepted(app), 'END_IF;']
    if live:
        unit_tag, station = f'FRK_{app.name}_Unit', gen.station_cfg_record(app)
        # The active model's record follows its bank through the changeover's
        # own bounded commit (model_commit_logic), in this scan.
        lines += [f'IF ({q}.Kind = 0) AND ({model_ordinal} = {unit_tag}.ModelOrdinal) THEN {unit_tag}.CommitModel := {model_ordinal}; END_IF;',
                  # The station document answers the restore: a loss the host
                  # announced is raised here, the active model is the one the
                  # documents kept, and stamping the image ends restoring.
                  f'IF ({q}.Kind = 1) AND {restoring} THEN',
                  f'IF {q}.StoreResult = 2 THEN {p}.RestoreLost := 1; {p}.LostModuleId := 1; END_IF;',
                  f'IF {model_ordinal} <> 0 THEN {unit_tag}.ModelOrdinal := {model_ordinal}; {unit_tag}.CommitModel := {model_ordinal}; END_IF;',
                  f'{station.name}Tag.{decl.SCHEMA_VERSION_MEMBER} := {station.schema_version};', 'END_IF;']
    store = decl.config_medium(app).store
    lines += ['ELSE', '(* Document operations do not apply equipment values. *)',
              'END_CASE;', *mb._accept(app),
              f'{p}.StorePresent := 1;', f'{p}.StoreKind := {store}; (* {decl.CONFIG_STORE_NAMES[store]} *)',
              f'IF ({q}.Operation = {mb.SAVE_CONFIG_SET}) OR ({q}.Operation = {mb.DELETE_CONFIG_SET}) THEN',
              f'{p}.Pending := 1;', f'{p}.Failed := 0;', f'{p}.PendingSince := FRK_{app.name}_NowTime;',
              f'{s}.PendingMs := 0;', f'{s}.PendingSequence := {q}.Sequence;',
              f'{s}.PendingSlot := {s}.Head MOD {AUDIT_CAPACITY};', 'END_IF;',
              f'IF ({q}.Operation = {mb.IMPORT_CONFIG_SET}) AND ({q}.Commit <> 0) THEN',
              f'{p}.Pending := 1;', f'{p}.Failed := 0;', f'{p}.PendingSince := FRK_{app.name}_NowTime;',
              f'{s}.PendingMs := 0;', f'{s}.PendingSequence := {q}.Sequence;',
              f'{s}.PendingSlot := {s}.Head MOD {AUDIT_CAPACITY};', 'END_IF;', 'ELSE',
              f'{mb._response(app, "DiagnosticKey")} := {s}.Reason;', 'END_IF;',
              f'IF {s}.Reason <> 0 THEN',
              f'{unit}.ReportedReason := {app.reasons["CONFIG_SET_REJECTED"]};',
              f'{unit}.ReportedSource := 0;', f'{unit}.ReportedCount := {unit}.ReportedCount + 1;',
              f'ELSIF {q}.Operation = {mb.LOAD_CONFIG_SET} THEN',
              f'{unit}.ReportedReason := {app.reasons["EVENT_CONFIG_SET_APPLIED"]};',
              f'{unit}.ReportedSource := 0;', f'{unit}.ReportedCount := {unit}.ReportedCount + 1;', 'END_IF;',
              # Audit every accepted/refused set transaction on the controller.
              f'{s}.Head := ({s}.Head MOD {AUDIT_CAPACITY}) + 1;',
              f'IF {s}.AuditCount < {AUDIT_CAPACITY} THEN {s}.AuditCount := {s}.AuditCount + 1; END_IF;']
    slot = s + '.Head - 1'
    import fraktal_ab_access as access
    actor_length = access.tag(app, 'State') + '.UserLength' if app.access_users is not None else req + '.User.LEN'
    actor_bytes = access.tag(app, 'State') + '.UserBytes' if app.access_users is not None else req + '.User.DATA'
    for dest, source in (('Sequence', q + '.Sequence'), ('Kind', q + '.Operation'),
                         ('Records', s + '.Count'), ('Reason', s + '.Reason'),
                         ('Accepted', mb._response(app, 'Accepted')),
                         ('RejectIndex', s + '.RejectIndex'), ('Date', f'FRK_{app.name}_NowDate'),
                         ('Clock', f'FRK_{app.name}_NowTime'), ('NameLength', q + '.NameLength'),
                         ('UserLength', actor_length)):
        lines += [f'{s}.Audit{dest}[{slot}] := {source};']
    for width, dest, source in ((NAME_MAX, 'Name', q + '.NameBytes'), (32, 'User', actor_bytes)):
        length = q + '.NameLength' if dest == 'Name' else actor_length
        lines += [f'FOR {b} := 0 TO {width - 1} DO', f'IF {b} < {length} THEN',
                  f'{s}.Audit{dest}Bytes[({slot}) * {width} + {b}] := {source}[{b}];',
                  'ELSE', f'{s}.Audit{dest}Bytes[({slot}) * {width} + {b}] := 0;',
                  'END_IF;', 'END_FOR;']
    if app.canonical_publication_stage>=8:
        import fraktal_ab_canonical_config as publication_config
        needle=f'{p}.PendingSince := FRK_{app.name}_NowTime;'
        result=[]
        for line in lines:
            result.append(line)
            if line==needle:result.extend(publication_config.pending_stamp(app))
        lines=result
    return lines


def values_document(app, name, kind, value_of, model_code, created, clock):
    """One document of `kind` from the editable walk; `value_of(ordinal,
    record, member)` supplies each number. The set snapshot and the live
    documents both render here, so their records cannot disagree."""
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    records = []
    for ordinal, record, member in gen.editable_values(app):
        if config_kind(record) != kind:
            continue
        value = value_of(ordinal, record, member)
        text = ('TRUE' if value else 'FALSE') if member.kind == 'boolean' else str(value)
        records.append({'scope': app.name, 'key': member.write_key,
                        'rev': mf.config_revision(app), 'kind': kind,
                        'type': value_type(member), 'value': text})
    return checked_document([{'set': name, 'root': app.name, 'schema': 1,
              'configRev': mf.config_revision(app), 'kind': kind, 'model': model_code,
              'records': len(records), 'created': created, 'clock': clock}, *records])
