#!/usr/bin/env python3
"""The AB root Unit's ``HmiRequest``/``HmiResponse`` command mailbox.

Core §3.10/§14: a client commands a Unit by writing arguments into a mailbox and
then writing ``Sequence`` last as the commit marker. The Unit dispatches on
``Kind``, answers in ``HmiResponse``, and sets ``AckSequence`` last so a client
that sees its own sequence acknowledged knows the whole answer is present.

**The contract is the TwinCAT oracle's, not a new one.** ``ST_HmiRequest``,
``ST_HmiResponse`` and ``E_HmiRequestKind`` already exist in
``FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs``, and the HMI writes
against them through ``lib/data/opcua_repository.dart``. The ordinals here are
therefore transcribed from that DUT and pinned against it by a test, for the same
reason ``E_Mode`` is pinned: AB shipped AUTO and MANUAL swapped once, and a
mailbox with a drifted ordinal would have a client send ``LOAD_CONFIG_SET`` when
the operator asked for a lamp test.

**Three forced deviations from the oracle's field types**, each a consequence of
the frozen v33 type map rather than a preference:

* ``BoolValue`` is a 0/1 ``DINT``. A ``BOOL`` member in a public UDT has an
  unmeasured layout - the recorded S12 hole - so no public contract here carries
  one.
* ``DurationMs`` and ``Sequence`` are ``DINT``. Logix v33 has no ``UDINT``, so
  the oracle's unsigned counters bind to signed 32-bit. ``Sequence`` is a change
  marker compared for inequality, never ordered, so signedness costs nothing;
  see ``SEQUENCE_WRAPS_AT``.
* Release reports and configuration pages are projected from the native
  records, rather than embedded as strings in ``HmiResponse``.

What this mailbox does **not** do is re-implement any machine behaviour. The
press demo already owns the mode owner, the S16 command handshake, the operator
decision and the per-module manual command. The mailbox is a request-routing
layer onto those; the PLC still re-checks its own rules.
"""

from __future__ import annotations
from fraktal_ab_models import ordinal_guard

# --- E_HmiRequestKind, transcribed from the oracle DUT and pinned by test -----
#
# Append-only: these values are a transport contract with every HMI adapter.
NONE = 0
LOGIN = 1
LOGOUT = 2
SET_MODE = 3
SET_MODEL = 4
START = 5
STOP = 6
CONTROL_ON = 7
CONTROL_OFF = 8
OPERATOR_RESET = 9
DECISION_ANSWER = 10
MANUAL_COMMAND = 11
SET_RUN_STYLE = 12
STEP_REQUEST = 13
SET_HOLD_RUN = 14
RELEASE_START = 15
RELEASE_MANUAL = 16
RELEASE_ACTION = 17
RESET_OEE = 18
WRITE_CONFIG = 19
SHELVE_ALARM = 20
UNSHELVE_ALARM = 21
FORCE_CHANNEL = 22
QUERY_CONFIG = 23
SET_ACCESS_LEVEL = 24
SET_SESSION_TIMEOUT = 25
LAMP_TEST = 26
CAPTURE_CONFIG = 27
SAVE_CONFIG_SET = 28
LOAD_CONFIG_SET = 29
LIST_CONFIG_SETS = 30
ACK_CONFIG_RESTORE = 31
EXPORT_CONFIG_SET = 32
IMPORT_CONFIG_SET = 33
MANUAL_HELD = 34
DELETE_CONFIG_SET = 35
SET_CLASS_LEVEL = 36
CREATE_MODEL = 37
EXPORT_CURRENT_CONFIG = 38

# Every ordinal the oracle declares, by name. The pinning test compares this
# mapping against the DUT itself, so a member added there and not here fails.
KINDS: dict[str, int] = {
    "NONE": NONE, "LOGIN": LOGIN, "LOGOUT": LOGOUT, "SET_MODE": SET_MODE,
    "SET_MODEL": SET_MODEL, "START": START, "STOP": STOP,
    "CONTROL_ON": CONTROL_ON, "CONTROL_OFF": CONTROL_OFF,
    "OPERATOR_RESET": OPERATOR_RESET, "DECISION_ANSWER": DECISION_ANSWER,
    "MANUAL_COMMAND": MANUAL_COMMAND, "SET_RUN_STYLE": SET_RUN_STYLE,
    "STEP_REQUEST": STEP_REQUEST, "SET_HOLD_RUN": SET_HOLD_RUN,
    "RELEASE_START": RELEASE_START, "RELEASE_MANUAL": RELEASE_MANUAL,
    "RELEASE_ACTION": RELEASE_ACTION, "RESET_OEE": RESET_OEE,
    "WRITE_CONFIG": WRITE_CONFIG, "SHELVE_ALARM": SHELVE_ALARM,
    "UNSHELVE_ALARM": UNSHELVE_ALARM, "FORCE_CHANNEL": FORCE_CHANNEL,
    "QUERY_CONFIG": QUERY_CONFIG, "SET_ACCESS_LEVEL": SET_ACCESS_LEVEL,
    "SET_SESSION_TIMEOUT": SET_SESSION_TIMEOUT, "LAMP_TEST": LAMP_TEST,
    "CAPTURE_CONFIG": CAPTURE_CONFIG, "SAVE_CONFIG_SET": SAVE_CONFIG_SET,
    "LOAD_CONFIG_SET": LOAD_CONFIG_SET, "LIST_CONFIG_SETS": LIST_CONFIG_SETS,
    "ACK_CONFIG_RESTORE": ACK_CONFIG_RESTORE,
    "EXPORT_CONFIG_SET": EXPORT_CONFIG_SET,
    "IMPORT_CONFIG_SET": IMPORT_CONFIG_SET, "MANUAL_HELD": MANUAL_HELD,
    "DELETE_CONFIG_SET": DELETE_CONFIG_SET, "SET_CLASS_LEVEL": SET_CLASS_LEVEL,
    "CREATE_MODEL": CREATE_MODEL, "EXPORT_CURRENT_CONFIG": EXPORT_CURRENT_CONFIG,
}

# --- what this binding actually routes ---------------------------------------
#
# A request kind is supported only where the press demo already has the
# mechanism. Everything else is refused by name, with a reason: a silent drop or
# a fake accept would let an operator believe a machine took a command it never
# saw, which is the one failure mode a command mailbox must not have.

SUPPORTED: dict[int, str] = {
    SET_MODE: "the mode owner's mode select; IntValue is the E_Mode ordinal",
    START: "the run request the mode chain already consumes",
    STOP: "the abort request the mode chain already consumes",
    OPERATOR_RESET: "the reset request",
    DECISION_ANSWER: "the operator decision the AUTO chain waits on; IntValue",
    MANUAL_COMMAND: "TC3's ManualCommandTo: in the manual mode, the command "
                    "IntValue to the module the gateway resolved TargetPath to",
    FORCE_CHANNEL: "§10.5.1 output forcing; the gateway resolves TargetPath "
                   "into the packed IntValue, BoolValue applies or clears",
    SET_MODEL: "§3.8 changeover; the gateway resolves the model code in "
               "TextValue into the IntValue ordinal the CHANGEOVER chain waits on",
    RELEASE_START: "TC3's ReleaseReportStart: the report START itself reads",
    RELEASE_MANUAL: "TC3's ReleaseReportManual: the target's own refusals and "
                    "the permit of the direction asked about",
    RELEASE_ACTION: "TC3's ReleaseReportAction: IntValue is the E_GatedAction",
    RESET_OEE: "TC3's ResetOee: the OEE accumulators and trend ring",
}
# SET_RUN_STYLE, STEP_REQUEST and SET_HOLD_RUN are routed only where the Unit
# paces its sequences (decl.Application.run_styles) - refused_for() lifts their
# refusals then, as it does WRITE_CONFIG's for a station with editable values.

# The command-mailbox handover listed STEP_REQUEST, SET_HOLD_RUN and LAMP_TEST
# as routable. They are not, and the declaration is the authority: the press
# demo has no step-request tag and no signal tower, and its Hold* tags are the
# S16 per-module hold *injections* the evidence harness uses, not a sequence
# hold-run control. Routing a command to the nearest similarly-named tag is how
# an operator ends up holding a cylinder when they asked to hold the sequence.

# The reason is a localization key, because a Diagnostic an operator reads has to
# survive translation. Each names the owed work rather than saying "unsupported".
REFUSED: dict[int, str] = {
    LOGIN: "project.mailbox.refused.access_not_enforced",
    LOGOUT: "project.mailbox.refused.access_not_enforced",
    SET_ACCESS_LEVEL: "project.mailbox.refused.access_not_enforced",
    SET_SESSION_TIMEOUT: "project.mailbox.refused.access_not_enforced",
    SET_CLASS_LEVEL: "project.mailbox.refused.access_not_enforced",
    CONTROL_ON: "project.mailbox.refused.no_control_power",
    CONTROL_OFF: "project.mailbox.refused.no_control_power",
    SET_RUN_STYLE: "project.mailbox.refused.no_run_style",
    WRITE_CONFIG: "project.mailbox.refused.no_config_manifest",
    QUERY_CONFIG: "project.mailbox.refused.no_config_manifest",
    CAPTURE_CONFIG: "project.mailbox.refused.no_config_manifest",
    SAVE_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    LOAD_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    LIST_CONFIG_SETS: "project.mailbox.refused.no_config_sets",
    ACK_CONFIG_RESTORE: "project.mailbox.refused.no_config_sets",
    EXPORT_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    IMPORT_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    DELETE_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    CREATE_MODEL: "project.mailbox.refused.no_config_sets",
    EXPORT_CURRENT_CONFIG: "project.mailbox.refused.no_config_sets",
    SHELVE_ALARM: "project.mailbox.refused.no_shelving",
    UNSHELVE_ALARM: "project.mailbox.refused.no_shelving",
    # FORCE_CHANNEL is routed - see force_argument() below.
    MANUAL_HELD: "project.mailbox.refused.no_hold_to_run",
    STEP_REQUEST: "project.mailbox.refused.no_step_control",
    SET_HOLD_RUN: "project.mailbox.refused.no_hold_run_control",
    LAMP_TEST: "project.mailbox.refused.no_signal_tower",
}

# NONE is neither: a mailbox holding Kind 0 has not been commanded, and treating
# that as a refusal would answer a request nobody made.
UNCOMMANDED = NONE

# --- the contract UDTs -------------------------------------------------------
#
# String lengths are the oracle's. They are the declared maximum for each field,
# which is how the frozen contract sizes a string type.
TARGET_PATH_LENGTH = 255
NAME_VALUE_LENGTH = 160
TEXT_VALUE_LENGTH = 255
USER_LENGTH = 32
SECRET_LENGTH = 32
# The oracle answers with `Diagnostic : STRING(255)`. This binding answers with a
# numeric localization key instead, and that is a *measured* deviation rather
# than a preference. Logix v33 ST will not assign a string literal to a
# StringFamily member: the SDK imported 21 such assignments at 0 errors and
# Studio Verify then rejected exactly 21. Setting a string from logic would mean
# a constant tag per key, or writing DATA byte by byte.
#
# Publishing the key is also the better answer here. The manifest already
# carries the numeric-to-portable catalogue an HMI resolves against, so a
# refusal survives translation instead of shipping one hard-coded language, and
# the controller contract stays all-DINT. The projection resolves the key back
# into the string the mapper reads.

# Sequence is a DINT because v33 has no UDINT. It is compared for inequality and
# never ordered, so a wrap is not a fault - but a client that treats it as
# always-increasing would stall here, exactly as it would on ConfigRevision.
SEQUENCE_WRAPS_AT = 2 ** 32

STRING_MEMBER = "string"
DINT_MEMBER = "dint"

REQUEST_MEMBERS: tuple[tuple[str, str, int, str], ...] = (
    ("Kind", DINT_MEMBER, 0, "E_HmiRequestKind ordinal"),
    ("TargetPath", STRING_MEMBER, TARGET_PATH_LENGTH, "which module, when a kind needs one"),
    ("NameValue", STRING_MEMBER, NAME_VALUE_LENGTH, "a named argument"),
    ("TextValue", STRING_MEMBER, TEXT_VALUE_LENGTH, "a free-text argument"),
    ("User", STRING_MEMBER, USER_LENGTH, "who is asking"),
    ("Secret", STRING_MEMBER, SECRET_LENGTH, "cleared immediately after sampling"),
    ("IntValue", DINT_MEMBER, 0, "an integer argument"),
    ("BoolValue", DINT_MEMBER, 0, "0/1, not a BOOL: the S12 hole"),
    ("DurationMs", DINT_MEMBER, 0, "milliseconds; the oracle's UDINT has no v33 type"),
    ("Sequence", DINT_MEMBER, 0, "the commit marker, written last"),
)

RESPONSE_MEMBERS: tuple[tuple[str, str, int, str], ...] = (
    ("AckSequence", DINT_MEMBER, 0, "set last, so a matching ack means the whole answer is present"),
    ("Accepted", DINT_MEMBER, 0, "0/1, not a BOOL: the S12 hole"),
    ("DiagnosticKey", DINT_MEMBER, 0, "the manifest's numeric localization key for the reason"),
)


# --- how the Unit samples what the mailbox drives ---------------------------
#
# The generated Unit copies each request tag into its context every scan and
# tests it as a LEVEL. That makes the deassert the mailbox's job, and which
# tags need one is a property of how the Unit consumes them, not a preference:
#
# * a one-shot is acted on and forgotten - `IF Ctx.AbortRequest <> 0 THEN` sets
#   Aborted once and nothing in the Unit lowers the request, so it must fall
#   again or the machine can never leave that state;
# * `RunRequest` is a level in both directions: `IF Ctx.RunRequest = 0 THEN
#   Ctx.Running := 0`. It stays high for as long as the chain should run, so
#   STOP lowers it rather than a scan boundary;
# * `ModeRequest` is a selection compared against `Mode`. Clearing it would
#   request ordinal 0 - AUTO - on the very next scan.

ONE_SHOT_REQUESTS = ("AbortRequest", "ResetRequest", "DecisionAnswer")
LEVEL_REQUESTS = ("RunRequest", "ModeRequest")


# --- FORCE_CHANNEL, and why its argument is packed --------------------------
#
# The oracle names the channel with `TargetPath : STRING(255)` and carries the
# level in `TextValue`, and TC3 resolves both in the PLC. This binding cannot:
# S12 froze the controller contract as all-DINT precisely because Logix v33 ST
# will not assign a string literal, and comparing twenty channel names in ST
# would need a constant tag per name.
#
# So the GATEWAY resolves the path, exactly as it already resolves the numeric
# DiagnosticKey back into text - the same seam, in the other direction. The
# mailbox still carries `TargetPath` verbatim, so the audit trail names the
# channel an operator actually clicked; the controller reads the resolved form.
#
# The gateway sends the channel's BIT MASK, not its index, and that is a
# correctness choice rather than a convenience. Logix v33 ST has no shift
# operator - shifting is a ladder instruction - so a controller handed an index
# could not turn it into a mask without a lookup table per channel. Handed the
# mask it needs only AND, OR and NOT, which are settled on this baseline. The
# rule this follows is the one that governs the whole binding: resolve it where
# the resolution can be tested, not where it cannot be compiled.
#
#     IntValue   = the channel's bit mask, exactly one bit set
#     BoolValue  = 1 applies the force, 0 clears it (the oracle's meaning)
#     DurationMs = the level to hold, 0 or 1, and only when applying
#
# `DurationMs` carrying a level rather than a duration is a borrowed field, and
# it is named here rather than left to be discovered. The UDT is the frozen S12
# contract and has no spare DINT; adding one would be a downloadable change to
# every deployment for one bit.
FORCE_LEVEL_MEMBER = "DurationMs"

# WRITE_CONFIG. The client sends a STRING write key and a STRING value, and the
# controller can read neither - so the gateway resolves both into DINT slots it
# already has, the way it already resolves a force channel's path to a bit mask
# (resolve_config_batch below). No member is added for this: FORCE_LEVEL_MEMBER
# set the precedent that a named constant on an existing slot is clearer than
# growing a record every client needs to agree about.
#
# IntValue carries the ORDINAL rather than the client's WriteRevision. The
# revision exists so a client cannot write against a stale capability, and on
# this binding the manifest ContentHash already proves the client's picture
# matches the loaded build - a second, weaker version of the same check would
# be a second source for one fact.
#
# BoolValue carries the VALUE. Its name is the S12 story ("0/1, not a BOOL"),
# not a type constraint: it is a DINT like every other member. DurationMs is
# deliberately left alone because the client already sends the model index
# there, so model-scoped configuration stays possible without moving anything.
# MANUAL_COMMAND: the HMI names the module by its identity in TargetPath, as
# TC3's ManualCommandTo compares it with each child's Name. The controller
# cannot compare strings, so the gateway resolves the identity into the
# module's 1-based ordinal here, beside the command value in IntValue - the
# same seam FORCE_CHANNEL uses. An identity that names no commandable module
# resolves to 0, and the controller refuses it by name.
MANUAL_TARGET_MEMBER = "DurationMs"

CONFIG_ORDINAL_MEMBER = "IntValue"
CONFIG_VALUE_MEMBER = "BoolValue"
CONFIG_MODEL_MEMBER = "DurationMs"


def force_argument(module_index: int, bit: int) -> int:
    """The bit mask the controller ANDs with, for a resolved force target.

    Only module 0 is addressable today: the press has one chassis module, and a
    second would need its own mask word rather than more bits in this one. A
    request naming another module is refused rather than folded onto this one.
    """
    if module_index != 0:
        raise ValueError(f"module index {module_index} is not addressable; "
                         "a second I/O module needs its own force word")
    if not 0 <= bit < 32:
        raise ValueError(f"bit {bit} does not fit a DINT mask")
    return 1 << bit


def force_target(app, channel_path: str) -> tuple[int, int] | None:
    """Resolve a published channel path to (module index, bit), or None.

    The path is the projection's own ``<module>.<electrical tag>``. Returning
    None is a refusal, never a guess: a force aimed at a channel this station
    does not have must not land on whichever one happened to be at that index.

    **Outputs only**, and that is not a policy restatement - it is the bug this
    would otherwise have. Inputs and outputs are separate words that share bit
    numbers, so resolving input `_101B301A` at bit 0 yields the same mask as
    output `_101K301A` at bit 0, and a force aimed at a sensor would have
    energized a valve.
    """
    import fraktal_ab_declaration as decl

    for index, module in enumerate(app.io_modules):
        for channel in module.channels:
            if channel_path != f"{module.name}.{channel.name}":
                continue
            if channel.direction != decl.DIR_OUTPUT:
                return None
            return index, channel.bit
    return None


def resolve_force_batch(app, writes: list) -> list:
    """Turn a FORCE_CHANNEL batch's string arguments into the DINTs it needs.

    The HMI writes the oracle's shape - the channel's browse path in
    ``TargetPath`` and 'true'/'false' in ``TextValue`` - and the controller can
    read neither. This is the one place that translates, on the whole batch, so
    the resolution sees `Kind` and cannot fire on some other command that
    happens to carry a path.

    A path that names no declared channel is left alone rather than guessed at:
    the controller's own mask test then refuses it, which is the right place
    for the refusal to be visible to the operator.

    Returns the writes unchanged for every other kind. ``Sequence`` stays last
    because injected writes go before it, never after.
    """
    def member(name):
        for index, (path, _vtype, value) in enumerate(writes):
            if path.endswith(f"/HmiRequest/{name}"):
                return index, path, value
        return None, None, None

    _, _, kind = member("Kind")
    if kind != FORCE_CHANNEL or not app.io_modules:
        return writes

    _, path_write, channel_path = member("TargetPath")
    if path_write is None or not isinstance(channel_path, str):
        return writes
    target = force_target(app, channel_path)
    if target is None:
        return writes
    module_index, bit = target
    _, _, level = member("TextValue")

    root = path_write[: -len("/TargetPath")]
    resolved = {
        f"{root}/IntValue": ("int32", force_argument(module_index, bit)),
        f"{root}/{FORCE_LEVEL_MEMBER}": (
            "int32", 1 if str(level).lower() == "true" else 0),
    }
    out = [w for w in writes if w[0] not in resolved]
    commit = out.pop()
    return out + [(p, t, v) for p, (t, v) in resolved.items()] + [commit]


def model_ordinal(app, code: str) -> int:
    """1-based ordinal of a declared model code, or 0 for one this app lacks.

    Zero is a refusal the controller can act on, not a guess: selecting an
    undeclared model must fail by name rather than land on whichever model
    happened to be first. Same reasoning as `force_target`.
    """
    for index, model in enumerate(app.models, start=1):
        if model.code == code:
            return index
    return 0


def resolve_model_batch(app, writes: list, codes=None) -> list:
    """Turn a SET_MODEL batch's model code into the ordinal the chain reads."""
    def member(name):
        for path, _vtype, value in writes:
            if path.endswith(f"/HmiRequest/{name}"):
                return path, value
        return None, None

    _, kind = member("Kind")
    if kind != SET_MODEL or not app.models:
        return writes
    path, code = member("TextValue")
    if path is None or not isinstance(code, str):
        return writes
    root = path[: -len("/TextValue")]
    codes = codes if codes is not None else [m.code for m in app.models]
    resolved = (f"{root}/IntValue", "int32", codes.index(code) + 1 if code in codes else 0)
    out = [w for w in writes if w[0] != resolved[0]]
    commit = out.pop()
    return out + [resolved, commit]


def config_ordinal(app, write_key: str) -> int | None:
    """The wire ordinal for a client's write key, or None if undeclared."""
    for index, _record, member in _editable_values(app):
        if member.write_key == write_key:
            return index
    return None


def resolve_config_batch(app, writes: list) -> list:
    """Turn a WRITE_CONFIG batch's string arguments into the DINTs it needs.

    The client sends the oracle's shape - a string write key in ``NameValue``
    and the value as text in ``TextValue`` - and the controller can read
    neither. This translates, on the whole batch, and only when ``Kind`` says
    WRITE_CONFIG so it cannot fire on another command carrying a name.

    A key this build does not declare, or a value that is not an integer, is
    left ALONE rather than guessed at. The ordinal then stays whatever the
    client sent, the controller's own CASE refuses it by name, and the operator
    sees the refusal from the authority rather than from the translator.
    """
    def member(name):
        for index, (path, _vtype, value) in enumerate(writes):
            if path.endswith(f"/HmiRequest/{name}"):
                return index, path, value
        return None, None, None

    _, _, kind = member("Kind")
    if kind != WRITE_CONFIG or not _editable_values(app):
        return writes

    _, key_write, write_key = member("NameValue")
    _, _, text = member("TextValue")
    if key_write is None or not isinstance(write_key, str):
        return writes
    ordinal = config_ordinal(app, write_key)
    if ordinal is None:
        return writes
    try:
        # Rounded, not truncated: a client that renders 2.5 s as "2500.0"
        # means 2500, and int("2500.0") raises rather than saying so.
        value = int(round(float(str(text).strip())))
    except (TypeError, ValueError):
        return writes

    root = key_write[: -len("/NameValue")]
    resolved = {
        f"{root}/{CONFIG_ORDINAL_MEMBER}": ("int32", ordinal),
        f"{root}/{CONFIG_VALUE_MEMBER}": ("int32", value),
    }
    out = []
    for path, vtype, value_ in writes:
        if path in resolved:
            out.append((path, *resolved.pop(path)))
        else:
            out.append((path, vtype, value_))
    # A member the client did not send still has to arrive, or the controller
    # would validate against the previous request's leftovers.
    sequence = [w for w in out if w[0].endswith("/HmiRequest/Sequence")]
    body = [w for w in out if not w[0].endswith("/HmiRequest/Sequence")]
    for path, (vtype, value_) in resolved.items():
        body.append((path, vtype, value_))
    return body + sequence


def resolve_capture_batch(app, writes: list) -> list:
    """Resolve identity, retaining the capability revision for the PLC check.

    CAPTURE_CONFIG uses DurationMs for revision, not a model selector: TC3
    captures into the current record only. No client value reaches the source.
    Unknown identities resolve to zero, never the client's numeric ordinal.
    """
    fields = {p.rsplit("/", 1)[-1]: v for p, _t, v in writes}
    if fields.get("Kind") != CAPTURE_CONFIG:
        return writes
    root = writes[-1][0].rsplit("/", 1)[0]
    ordinal = config_ordinal(app, fields.get("NameValue"))
    if fields.get("TargetPath") != app.name:
        ordinal = 0
    revision = fields.get("IntValue")
    resolved = {CONFIG_ORDINAL_MEMBER: ("int32", ordinal or 0),
                CONFIG_VALUE_MEMBER: ("int32", 0),
                "DurationMs": ("int32", revision if type(revision) is int else 0)}
    body = [w for w in writes[:-1] if w[0].rsplit("/", 1)[-1] not in resolved]
    return body + [(f"{root}/{m}", t, v) for m, (t, v) in resolved.items()] + [writes[-1]]


def is_config_query(writes: list) -> bool:
    """D5: recognize only the inert, commit-last configuration read batch.

    Full HMI requests include empty unused arguments. Missing page/model
    arguments, unknown members and nonempty command/credential arguments do
    not acquire read authority. validate_batch has already checked structure.
    """
    root = writes[-1][0].rsplit("/", 1)[0]
    if any(p != f"{root}/{p.rsplit('/', 1)[-1]}" for p, _t, _v in writes):
        return False
    fields = {p.rsplit("/", 1)[-1]: (t, v) for p, t, v in writes}
    required = {"Kind", "IntValue", "DurationMs", "Sequence"}
    inert = {"TargetPath", "NameValue", "TextValue", "User", "Secret", "BoolValue"}
    if not required <= fields.keys() or fields.keys() - required - inert:
        return False
    if fields["Kind"] != ("int32", QUERY_CONFIG):
        return False
    for member in ("IntValue", "DurationMs"):
        t, v = fields[member]
        if t not in ("int32", "uint32") or type(v) is not int or v < 0:
            return False
    for member in inert & fields.keys():
        t, v = fields[member]
        if member == "BoolValue":
            if (t, v) != ("boolean", False):
                return False
        elif (t, v) != ("string", ""):
            return False
    return True


def requested_config_model(writes: list, current: int = 0) -> int:
    """The model a QUERY_CONFIG batch asks for, or `current` for any other kind.

    Every query carries one - the client's ordinary manifest fetch sends 0 -
    so the answer always tracks the connection's LAST question, exactly as a
    PLC mailbox response would.
    """
    kind = None
    model = 0
    for path, _vtype, value in writes:
        if path.endswith("/HmiRequest/Kind"):
            kind = value
        elif path.endswith(f"/HmiRequest/{CONFIG_MODEL_MEMBER}"):
            model = value if isinstance(value, int) else 0
    if kind != QUERY_CONFIG:
        return current
    return model if model >= 0 else 0


def manual_target(app, identity: str) -> int:
    """A module identity (`Press.Door`) to its 1-based ordinal, or 0 when it
    names no module that takes commands - never a guess."""
    for ordinal, module in enumerate(app.modules, start=1):
        if identity == f"{app.name}.{module.name}" and module.commands:
            return ordinal
    return 0


def resolve_manual_batch(app, writes: list) -> list:
    """MANUAL_COMMAND's TargetPath, resolved into MANUAL_TARGET_MEMBER."""
    kind = next((v for p, _t, v in writes if p.endswith("/HmiRequest/Kind")), None)
    if kind not in (MANUAL_COMMAND, RELEASE_MANUAL):
        return writes
    path_write = next(((p, v) for p, _t, v in writes
                       if p.endswith("/HmiRequest/TargetPath")), None)
    if path_write is None:
        return writes
    root = path_write[0][: -len("/TargetPath")]
    target = f"{root}/{MANUAL_TARGET_MEMBER}"
    out = [w for w in writes if w[0] != target]
    commit = out.pop()
    return out + [(target, "int32", manual_target(app, str(path_write[1])))] + [commit]


def resolve_batch(app, writes: list, model_codes=None) -> list:
    """Every gateway-side resolution, dispatched on the request kind.

    One entry point so the gateway does not grow a call per command, and so a
    kind that needs no resolution passes through untouched.
    """
    return resolve_capture_batch(app, resolve_manual_batch(app, resolve_config_batch(
        app, resolve_model_batch(app, resolve_force_batch(app, writes), model_codes))))


def one_shot_requests() -> tuple[str, ...]:
    """Request tags the handler must lower again on the following scan."""
    return ONE_SHOT_REQUESTS


def is_supported(kind: int) -> bool:
    return kind in SUPPORTED


def refusal_key(kind: int) -> str:
    """The localization key for a kind this binding will not route."""
    if kind in REFUSED:
        return REFUSED[kind]
    return "project.mailbox.refused.unknown_kind"


# --- emission ----------------------------------------------------------------
#
# The mailbox emits its own UDTs rather than going through the declaration, for
# the same reason the manifest does: `decl.Member` is all-DINT by design ("the
# BOOL-member UDT layout is unmeasured"), and it has no string kind. Adding one
# would widen a deliberately narrow contract type to serve two callers, so the
# two string-carrying contracts each emit their own, and the all-DINT test knows
# about the shape rather than the caller.

import fraktal_ab_manifest as _manifest


def string_type_name(app, length: int) -> str:
    return f"FRK_T_{app.name}Str{length}"


def request_type_name(app) -> str:
    # Additive native frame; legacy members retain their layout as private
    # decoded arguments. Web/OPC UA browse paths and ordinals are unchanged.
    return f"FRK_T_{app.name}HmiRequestV3"


def response_type_name(app) -> str:
    return f"FRK_T_{app.name}HmiResponse"


def request_tag_name(app) -> str:
    return f"FRK_{app.name}_HmiRequest"


def response_tag_name(app) -> str:
    return f"FRK_{app.name}_HmiResponse"


def string_lengths() -> tuple[int, ...]:
    """Every distinct string width the mailbox needs, longest first."""
    lengths = {length for _, kind, length, _ in REQUEST_MEMBERS + RESPONSE_MEMBERS
               if kind == STRING_MEMBER}
    return tuple(sorted(lengths, reverse=True))


def _member_xml(name: str, data_type: str, comment: str, access: str) -> str:
    radix = "NullType" if data_type.startswith("FRK_T_") else "Decimal"
    description = f"<Description><![CDATA[{comment}]]></Description>" if comment else ""
    return (f'<Member Name="{name}" DataType="{data_type}" Dimension="0" '
            f'Radix="{radix}" Hidden="false" ExternalAccess="{access}">'
            f"{description}</Member>")


def _record_xml(app, type_name: str, members, access: str, comment: str) -> str:
    body = []
    for name, kind, length, note in members:
        data_type = (string_type_name(app, length) if kind == STRING_MEMBER
                     else "DINT")
        member_access = ('None' if type_name == request_type_name(app)
                         and name != 'Sequence' else access)
        body.append(_member_xml(name, data_type, note, member_access))
    return (f'<DataType Name="{type_name}" Family="NoFamily" Class="User">'
            f"<Description><![CDATA[{comment}]]></Description>\n<Members>\n"
            + "\n".join(body) + "\n</Members>\n</DataType>")


def data_types(app) -> list[str]:
    """The mailbox's string types and its two contract records."""
    import fraktal_ab_mailbox_frame as frame
    blocks = frame.data_types(app)
    for length in string_lengths():
        name = string_type_name(app, length)
        blocks.append(
            f'<DataType Name="{name}" Family="StringFamily" Class="User">\n'
            f"<Members>\n"
            f'<Member Name="LEN" DataType="DINT" Dimension="0" Radix="Decimal" '
            f'Hidden="false" ExternalAccess="Read/Write"/>\n'
            f'<Member Name="DATA" DataType="SINT" Dimension="{length}" '
            f'Radix="ASCII" Hidden="false" ExternalAccess="Read/Write"/>\n'
            f"</Members>\n</DataType>")
    blocks.append(_record_xml(
        app, request_type_name(app), REQUEST_MEMBERS, "Read/Write",
        "Core 3.10/14 command mailbox: arguments first, Sequence last"))
    if app.config_sets:
        import fraktal_ab_sets as sets
        blocks[-1] = blocks[-1].replace('</Members>',
            _member_xml('ConfigSet', sets.request_name(), 'Core 3.8b staged transaction; Sequence commits last', 'Read/Write') + '\n</Members>')
    blocks[-1] = blocks[-1].replace('</Members>',
        _member_xml('Frame', frame.type_name(app), 'S9 bounded operation and arguments', 'Read/Write') + '\n</Members>')
    blocks.append(_record_xml(
        app, response_type_name(app), RESPONSE_MEMBERS, "Read Only",
        "Core 3.10/14 command answer: AckSequence set last"))
    return blocks


def _structure_tag(app, tag_name: str, type_name: str, members,
                   access: str) -> str:
    parts = []
    for name, kind, length, _ in members:
        if kind == STRING_MEMBER:
            string_type = string_type_name(app, length)
            parts.append(
                f'<StructureMember Name="{name}" DataType="{string_type}">\n'
                f'<DataValueMember Name="LEN" DataType="DINT" Radix="Decimal" '
                f'Value="0"/>\n'
                f'<DataValueMember Name="DATA" DataType="{string_type}" '
                f'Radix="ASCII">\n'
                f"<![CDATA[{_manifest.ascii_literal('')}]]>\n"
                f"</DataValueMember>\n</StructureMember>")
        else:
            parts.append(f'<DataValueMember Name="{name}" DataType="DINT" '
                         f'Radix="Decimal" Value="0"/>')
    if app.config_sets and type_name == request_type_name(app):
        import fraktal_ab_sets as sets
        import fraktal_ab_generate as gen
        # Reuse the all-DINT decorated serializer, including array dimensions.
        nested = gen._structure_tag('unused', sets.request_name(), sets.request_members())
        start = nested.index('<Structure DataType=')
        end = nested.index('</Structure>', start) + len('</Structure>')
        payload = nested[start:end].replace('<Structure ', '<StructureMember Name="ConfigSet" ', 1)
        parts.append(payload.replace('</Structure>', '</StructureMember>'))
    if type_name == request_type_name(app):
        import fraktal_ab_mailbox_frame as frame
        import fraktal_ab_generate as gen
        nested = gen._structure_tag('unused', frame.type_name(app), frame.members(app))
        start = nested.index('<Structure DataType=')
        end = nested.index('</Structure>', start) + len('</Structure>')
        payload = nested[start:end].replace('<Structure ', '<StructureMember Name="Frame" ', 1)
        parts.append(payload.replace('</Structure>', '</StructureMember>'))
    return (f'<Tag Name="{tag_name}" TagType="Base" DataType="{type_name}" '
            f'Constant="false" ExternalAccess="{access}">\n'
            f'<Data Format="Decorated">\n'
            f'<Structure DataType="{type_name}">\n'
            + "\n".join(parts)
            + "\n</Structure>\n</Data>\n</Tag>")


def tags(app) -> list[str]:
    """The two mailbox tags.

    The request is the only ``Read/Write`` surface this binding publishes, which
    is exactly the access audit's rule: a client may write the mailbox and
    nothing else. The response is ``Read Only`` - it is the machine's answer,
    not somewhere a client puts anything.
    """
    import fraktal_ab_mailbox_frame as frame
    return frame.tags(app) + [
        _structure_tag(app, request_tag_name(app), request_type_name(app),
                       REQUEST_MEMBERS, "Read/Write"),
        _structure_tag(app, response_tag_name(app), response_type_name(app),
                       RESPONSE_MEMBERS, "Read Only"),
        # The handler's retained memory of the last Sequence it answered. Not a
        # contract member: a client never reads it, and publishing it would
        # invite someone to write it and replay a command.
        f'<Tag Name="FRK_{app.name}_HmiLastSequence" TagType="Base" '
        f'DataType="DINT" Radix="Decimal" Constant="false" '
        f'ExternalAccess="None"/>',
        # The secret-wipe loop index. Also unreachable: it exists for one FOR
        # and nothing outside this routine has any business with it.
        f'<Tag Name="FRK_{app.name}_HmiWipe" TagType="Base" '
        f'DataType="DINT" Radix="Decimal" Constant="false" '
        f'ExternalAccess="None"/>',
    ]


# --- the handler -------------------------------------------------------------


def routine_name(app) -> str:
    return f"FRK_{app.name}HmiMailbox"


def _request(app, member: str) -> str:
    return f"{request_tag_name(app)}.{member}"


def _response(app, member: str) -> str:
    return f"{response_tag_name(app)}.{member}"


def _key(app, portable: str) -> int:
    import fraktal_ab_manifest as manifest

    return manifest.numeric_key(app, portable)


def _accept(app, *statements: str) -> list[str]:
    return list(statements) + [f"{_response(app, 'Accepted')} := 1;"]


def _refuse(app, portable: str) -> list[str]:
    return [f"{_response(app, 'DiagnosticKey')} := {_key(app, portable)}; "
            f"(* {portable} *)"]


def _model_scoped(app):
    import fraktal_ab_generate as gen

    return gen.model_scoped_members(app)


def _model_cfg_tag(app):
    import fraktal_ab_generate as gen

    return gen.model_cfg_tag(app)


def _editable_values(app):
    """Every editable value with its wire ordinal, or () when none are declared.

    Imported lazily: the generator imports this module, so a module-level
    import would be a cycle.
    """
    import fraktal_ab_generate as gen

    return gen.editable_values(app)


def refused_for(app) -> dict[int, str]:
    """REFUSED, minus the kinds THIS application actually routes.

    A kind is refused because the binding has nothing to do with it, and a
    station that declares editable configuration has something to do with
    WRITE_CONFIG. Keeping the static table and subtracting here means the
    refusal reason stays written down once, beside every other one.
    """
    refused = dict(REFUSED)
    if app.access_users is not None:
        for kind in (LOGIN, LOGOUT, SET_ACCESS_LEVEL, SET_SESSION_TIMEOUT, SET_CLASS_LEVEL,
                     SHELVE_ALARM, UNSHELVE_ALARM):
            refused.pop(kind, None)
    if _editable_values(app):
        refused.pop(WRITE_CONFIG, None)
        refused.pop(QUERY_CONFIG, None)
        refused.pop(CAPTURE_CONFIG, None)
    if _restores_anything(app):
        refused.pop(ACK_CONFIG_RESTORE, None)
    if app.config_sets:
        import fraktal_ab_sets as sets
        for kind in sets.SET_KINDS:
            refused.pop(kind, None)
    import fraktal_ab_generate as gen

    if gen.pacing(app):
        for kind in (SET_RUN_STYLE, STEP_REQUEST, SET_HOLD_RUN):
            refused.pop(kind, None)
    return refused


def _restores_anything(app) -> bool:
    """Whether a retained image exists that could be lost and acknowledged."""
    import fraktal_ab_generate as gen

    return (gen.station_cfg_record(app) is not None
            or bool(gen.model_scoped_members(app)))


# WRITE_CONFIG stays in the STATIC table rather than moving to SUPPORTED, and
# the difference matters to an operator: a station that declares no editable
# value still refuses it with `no_config_manifest`, which names the reason,
# while dropping it from the table entirely would land it in the ELSE and
# report `unknown_kind` - wrong, because the kind is perfectly well known and
# it is the station that has nothing to configure.


def _dispatch(app, *, use_routines=False) -> list[str]:
    """One CASE branch per routed kind, then the refusals grouped by reason."""
    n = app.name
    lines: list[str] = []
    if app.access_users is not None:
        import fraktal_ab_access as access
        lines.extend(access.dispatch(app))
        import fraktal_ab_data_access as data
        lines.extend(data.dispatch(app))
        import fraktal_ab_shelving as shelving
        lines.extend(shelving.dispatch(app))
    if app.config_sets:
        import fraktal_ab_sets as sets
        lines.extend(sets.dispatch(app, use_routine=use_routines))

    import fraktal_ab_declaration as decl

    guard = " OR ".join(f"({_request(app, 'IntValue')} = {m})"
                        for m in decl.declared_modes(app))
    lines.append(f"{SET_MODE}: (* SET_MODE *)")
    lines.append(f"IF {guard} THEN")
    lines.extend(_accept(app, f"FRK_{n}_ModeRequest := {_request(app, 'IntValue')};"))
    lines.append("ELSE")
    # A mode the oracle defines but this application does not declare is refused
    # by name, not clamped: selecting CHANGEOVER on a press that has no
    # changeover must fail visibly rather than land in AUTO.
    lines.extend(_refuse(app, MODE_NOT_DECLARED_KEY))
    lines.append("END_IF;")

    lines.append(f"{START}: (* START *)")
    # Core §8.3(b): an open MANUAL_RESET event blocks a restart. TC3 refuses
    # through its release report; this binding has none yet (audit Phase 4),
    # so the refusal is made here, BY NAME. Accepting START and then simply
    # not running would be a silent dead button - the one thing act-or-explain
    # (§7.6) forbids. The operator's way out is OPERATOR_RESET, always accepted.
    import fraktal_ab_generate as gen

    # TC3's Start: it consumes ReleaseReportStart(Report := HmiResponse.Report).
    # The report is the one the routine computes every scan, so the answer
    # carries the full reason list and the refusal names the first of it.
    start = gen.start_release_tag(app)
    if app.access_users is not None:
        lines.extend(gen.start_release_call(app))
    lines.extend(gen.report_copy(app, start, gen.release_report_tag(app)))
    lines.append(f"IF NOT {gen.start_predicate(app)} THEN")
    lines.append(f"{_response(app, 'DiagnosticKey')} := {start}.Key[0];")
    lines.append("ELSE")
    lines.extend(_accept(app, f"FRK_{n}_RunRequest := 1;"))
    lines.append("END_IF;")

    lines.extend(run_style_dispatch(app))

    lines.append(f"{RELEASE_START}: (* RELEASE_START *)")
    if app.access_users is not None:
        lines.extend(gen.start_release_call(app))
    lines.extend(gen.report_copy(app, start, gen.release_report_tag(app)))
    lines.extend(_accept(app))
    lines.append(f"{RELEASE_MANUAL}: (* RELEASE_MANUAL *)")
    lines.extend(manual_report_lines(app))
    lines.extend(_accept(app))
    lines.append(f"{RELEASE_ACTION}: (* RELEASE_ACTION *)")
    lines.extend(action_report_lines(app))
    lines.extend(_accept(app))
    lines.append(f"{RESET_OEE}: (* RESET_OEE *)")
    lines.extend(_accept(app, *gen.oee_reset_lines(app)))
    if app.line is not None:
        import fraktal_ab_line as line
        lines.append(f'{line.tag(app, "Shift")}.ManualReset := 1;')

    lines.append(f"{STOP}: (* STOP *)")
    # STOP lowers the run level as well as raising the abort pulse. A STOP that
    # left RunRequest high would be a contradiction the Unit then has to
    # resolve every scan: the abort latches Aborted, and the run level tries to
    # set Running again the moment the abort is cleared.
    lines.extend(_accept(app, f"FRK_{n}_AbortRequest := 1;",
                         f"FRK_{n}_RunRequest := 0;"))

    lines.append(f"{OPERATOR_RESET}: (* OPERATOR_RESET *)")
    # TC3's OperatorReset releases its own run command with the latched
    # state (_M_RecoverState): one reset leaves the machine RESTARTABLE, never
    # restarted. RunRequest is a level the START raised, so a reset that left
    # it up let the run latch set Running again in the very scan the fault
    # cleared - the press resumed by itself, seen on press42 when a START
    # after the reset was refused as unitNotReady because it was running.
    lines.extend(_accept(app, f"FRK_{n}_ResetRequest := 1;",
                         f"FRK_{n}_RunRequest := 0;"))

    lines.append(f"{DECISION_ANSWER}: (* DECISION_ANSWER *)")
    lines.append(f"IF {_request(app, 'IntValue')} >= 1 THEN")
    lines.extend(_accept(app,
                         f"FRK_{n}_DecisionAnswer := {_request(app, 'IntValue')};"))
    lines.append("ELSE")
    lines.extend(_refuse(app, DECISION_RANGE_KEY))
    lines.append("END_IF;")

    lines.extend(manual_command_dispatch(app))

    if app.models:
        lines.append(f"{SET_MODEL}: (* SET_MODEL *)")
        # The fallible half of §3.8's prepare/commit split lives here: a model
        # this station does not declare is refused by name, before anything
        # moves. The chain's commit is then a bounded copy that cannot fail.
        lines.append(f"IF {ordinal_guard(app, _request(app, 'IntValue'))} THEN")
        lines.extend(_accept(
            app, f"FRK_{n}_ModelRequest := {_request(app, 'IntValue')};"))
        lines.append("ELSE")
        lines.extend(_refuse(app, MODEL_NOT_DECLARED_KEY))
        lines.append("END_IF;")

    if app.io_modules:
        lines.append(f"{FORCE_CHANNEL}: (* FORCE_CHANNEL *)")
        # §10.5.1: the controller decides, every time. A client that asked
        # while forcing was permitted and arrived a scan after it stopped being
        # permitted must be refused, which is why this is re-tested here and
        # not inferred from the Forceable the client was shown.
        lines.append(f"IF FRK_{n}_ForcePermitted = 0 THEN")
        lines.extend(_refuse(app, FORCE_NOT_PERMITTED_KEY))
        # Exactly one bit, and one this station actually has. A mask of zero
        # would silently force nothing; a mask of several would force channels
        # the operator did not name.
        lines.append(f"ELSIF ({_request(app, 'IntValue')} AND "
                     f"FRK_{n}_ForceOutputs) = 0 THEN")
        lines.extend(_refuse(app, FORCE_TARGET_KEY))
        lines.append("ELSE")
        lines.append(f"IF {_request(app, 'BoolValue')} <> 0 THEN")
        lines.append(f"FRK_{n}_ForceMask := FRK_{n}_ForceMask OR "
                     f"({_request(app, 'IntValue')} AND FRK_{n}_ForceOutputs);")
        lines.append(f"IF {_request(app, FORCE_LEVEL_MEMBER)} <> 0 THEN")
        lines.append(f"FRK_{n}_ForceValue := FRK_{n}_ForceValue OR "
                     f"({_request(app, 'IntValue')} AND FRK_{n}_ForceOutputs);")
        lines.append("ELSE")
        lines.append(f"FRK_{n}_ForceValue := FRK_{n}_ForceValue AND "
                     f"NOT {_request(app, 'IntValue')};")
        lines.append("END_IF;")
        lines.append("ELSE")
        # Clearing drops the held level with the mask. Leaving the level set
        # would re-apply the old value the next time this channel is forced.
        lines.append(f"FRK_{n}_ForceMask := FRK_{n}_ForceMask AND "
                     f"NOT {_request(app, 'IntValue')};")
        lines.append(f"FRK_{n}_ForceValue := FRK_{n}_ForceValue AND "
                     f"NOT {_request(app, 'IntValue')};")
        lines.append("END_IF;")
        lines.extend(_accept(app))
        lines.append("END_IF;")

    editable = _editable_values(app)
    if editable:
        import fraktal_ab_config as config
        lines.extend(config.write_dispatch(app, use_routine=use_routines))

        if _restores_anything(app):
            import fraktal_ab_generate as gen

            persist = gen.config_persist_tag(app)
            lines.append(f"{ACK_CONFIG_RESTORE}: (* ACK_CONFIG_RESTORE *)")
            # The enabled access provider checks ENGINEER before dispatch,
            # independently of policy; then TC3 refuses if nothing was lost.
            lines.append(f"IF {persist}.RestoreLost = 0 THEN")
            lines.extend(_refuse(app, RESTORE_ACK_REFUSED_KEY))
            lines.append("ELSE")
            lines.extend(_accept(
                app, f"{persist}.RestoreAcknowledged := 1;"))
            lines.append("END_IF;")

        lines.append(f"{QUERY_CONFIG}: (* QUERY_CONFIG *)")
        # Accepted, with nothing to compute. The answer is the
        # WriteCapabilities table this controller already publishes, which a
        # client reads with the rest of the manifest - so acknowledging means
        # "yes, this station describes its configuration", and that is true.
        #
        # It is not served as pages of strings from here because it cannot be:
        # v33 assigns no string literal in ST, so every name an operator reads
        # is interned at emission and referenced by number. Paging would be
        # copying static rows the client can already read.
        lines.extend(_accept(app))

    by_key: dict[str, list[int]] = {}
    for kind, portable in sorted(refused_for(app).items()):
        by_key.setdefault(portable, []).append(kind)
    for portable, kinds in sorted(by_key.items()):
        lines.append(",".join(str(k) for k in kinds) + ":")
        lines.extend(_refuse(app, portable))

    lines.append("ELSE")
    lines.extend(_refuse(app, UNKNOWN_KEY))
    return lines


def run_style_dispatch(app) -> list[str]:
    """TC3's SetRunStyle, StepRequest and SetHoldRun (§3.4.2). A style the
    Unit does not declare, a Step outside a running SINGLE_STEP, and a hold
    outside a running HOLD_TO_RUN are refused by name; releasing the hold is
    always taken, so a hold can never stick."""
    import fraktal_ab_generate as gen
    import fraktal_ab_declaration as decl

    if not gen.pacing(app):
        return []
    u, value = f"FRK_{app.name}_Unit", _request(app, "IntValue")
    held = _request(app, "BoolValue")
    allowed = " OR ".join(f"({value} = {s})" for s in app.run_styles)
    lines = [f"{SET_RUN_STYLE}: (* SET_RUN_STYLE *)",
             f"IF {allowed} THEN",
             *_accept(app, f"{u}.RunStyle := {value};",
                      f"IF {value} <> {decl.RUN_HOLD_TO_RUN} THEN {u}.HoldRun := 0; END_IF;",
                      f"IF {value} <> {decl.RUN_SINGLE_STEP} THEN {u}.StepPending := 0; END_IF;"),
             "ELSE", *_refuse(app, RUN_STYLE_REFUSED_KEY), "END_IF;"]
    if decl.RUN_SINGLE_STEP in app.run_styles:
        lines += [f"{STEP_REQUEST}: (* STEP_REQUEST *)",
                  f"IF ({u}.RunStyle = {decl.RUN_SINGLE_STEP}) AND ({u}.Running <> 0) THEN",
                  *_accept(app, f"{u}.StepPending := 1;"),
                  "ELSE", *_refuse(app, STEP_REFUSED_KEY), "END_IF;"]
    else:
        lines += [f"{STEP_REQUEST}: (* STEP_REQUEST *)", *_refuse(app, STEP_REFUSED_KEY)]
    if decl.RUN_HOLD_TO_RUN in app.run_styles:
        lines += [f"{SET_HOLD_RUN}: (* SET_HOLD_RUN *)",
                  f"IF {held} = 0 THEN",
                  *_accept(app, f"{u}.HoldRun := 0;"),
                  f"ELSIF ({u}.RunStyle = {decl.RUN_HOLD_TO_RUN}) AND ({u}.Running <> 0) THEN",
                  *_accept(app, f"{u}.HoldRun := 1;"),
                  "ELSE", *_refuse(app, HOLD_RUN_REFUSED_KEY), "END_IF;"]
    else:
        lines += [f"{SET_HOLD_RUN}: (* SET_HOLD_RUN *)", *_refuse(app, HOLD_RUN_REFUSED_KEY)]
    return lines


def manual_report_lines(app) -> list[str]:
    """TC3's ReleaseReportManual: the full list of why a manual command to
    TargetPath in direction IntValue would not run - the mode, the target and
    its catalogue, a module still busy (each refused by MANUAL_COMMAND) and
    the direction's missing permit (which would hold it). The same tests the
    gate and the routine make, from the same declaration."""
    import fraktal_ab_generate as gen

    n = app.name
    report = gen.release_report_tag(app)
    target, value = _request(app, MANUAL_TARGET_MEMBER), _request(app, "IntValue")
    lines = gen.report_open(report)
    if app.access_users is not None:
        import fraktal_ab_access as access
        lines += access.report(app, report, '2')
    if app.manual_mode is not None:
        lines += [f"IF FRK_{n}_Unit.Mode <> {app.manual_mode} THEN",
                  *gen.report_add(report, _key(app, MANUAL_MODE_REQUIRED_KEY), 0, 0,
                                  "MODE", MANUAL_MODE_REQUIRED_KEY),
                  "END_IF;"]
    unsupported = app.reasons.get("UNSUPPORTED_COMMAND", 0)
    held = app.reasons.get("INTERLOCK_DROPPED", 0)
    lines.append(f"CASE {target} OF")
    for ordinal, module in enumerate(app.modules, start=1):
        if not module.commands:
            continue
        ctx = gen.ctx_tag_for(app, module.name)
        allowed = " OR ".join(f"({value} = {c.ordinal})" for c in module.commands)
        lines += [f"{ordinal}: (* {module.name} *)",
                  f"IF NOT ({allowed}) THEN",
                  *gen.report_add(report, _key(app, MANUAL_COMMAND_UNKNOWN_KEY), unsupported,
                                  ordinal, "INTERLOCK", MANUAL_COMMAND_UNKNOWN_KEY),
                  "ELSE",
                  f"IF {ctx}.Busy <> 0 THEN",
                  *gen.report_add(report, _key(app, MANUAL_BUSY_KEY), 0, ordinal,
                                  "OTHER", MANUAL_BUSY_KEY),
                  "END_IF;",
                  *gen.permit_chain(
                      app, module, value,
                      lambda permit, o=ordinal: gen.report_add(
                          report, _key(app, permit.key), held, o, "INTERLOCK", permit.key),
                      []),
                  "END_IF;"]
    lines += ["ELSE",
              *gen.report_add(report, _key(app, TARGET_KEY), unsupported, 0, "OTHER",
                              TARGET_KEY),
              "END_CASE;"]
    return lines + gen.report_close(report)


def action_report_lines(app) -> list[str]:
    """TC3's ReleaseReportAction for the gates this binding has. TC3 adds
    the session's access level first, which this controller does not hold
    yet (audit Phase 6); a mode change is never refused here (every mode
    switch is INTERRUPTIBLE); and a model may be chosen while CHANGEOVER
    runs, because this press's changeover waits for it there. What remains
    is TC3's operator reset: there is nothing for it to reset."""
    import fraktal_ab_generate as gen

    report = gen.release_report_tag(app)
    lines = gen.report_open(report)
    if app.access_users is not None:
        import fraktal_ab_access as access
        lines += access.report(app, report, _request(app, 'IntValue'))
    return [*lines,
            f"IF ({_request(app, 'IntValue')} = {gen.GATED_ALARM_RESET}) AND "
            f"({gen.alarm_active_tag(app)}.Blocking = 0) THEN",
            *gen.report_add(report, _key(app, gen.NO_BLOCKING_ALARM_KEY), 0, 0,
                            "OTHER", gen.NO_BLOCKING_ALARM_KEY),
            "END_IF;",
            *gen.report_close(report)]


def manual_command_dispatch(app) -> list[str]:
    """TC3's ManualCommandTo + ManualCommand: only in the manual mode, only to
    a module that takes commands, only a command in its catalogue, and only
    while it is not already busy. Accepting drops the module's Execute first,
    so the command it then runs starts on a fresh edge - and a fault a
    previous manual command left is released by the same drop."""
    import fraktal_ab_generate as gen

    n = app.name
    lines = [f"{MANUAL_COMMAND}: (* MANUAL_COMMAND *)"]
    commandable = [(ordinal, module) for ordinal, module in
                   enumerate(app.modules, start=1) if module.commands]
    if app.manual_mode is None or not commandable:
        return lines + _refuse(app, MANUAL_MODE_REQUIRED_KEY)
    target, value = _request(app, MANUAL_TARGET_MEMBER), _request(app, "IntValue")
    lines += [f"IF FRK_{n}_Unit.Mode <> {app.manual_mode} THEN",
              *_refuse(app, MANUAL_MODE_REQUIRED_KEY),
              "ELSE",
              f"CASE {target} OF"]
    for ordinal, module in commandable:
        ctx = gen.ctx_tag_for(app, module.name)
        allowed = " OR ".join(f"({value} = {c.ordinal})" for c in module.commands)
        lines += [f"{ordinal}: (* {module.name} *)",
                  f"IF NOT ({allowed}) THEN",
                  *_refuse(app, MANUAL_COMMAND_UNKNOWN_KEY),
                  f"ELSIF {ctx}.Busy <> 0 THEN",
                  *_refuse(app, MANUAL_BUSY_KEY),
                  "ELSE",
                  *_accept(app, f"{ctx}.Execute := 0;", f"{ctx}.ManualCmd := {value};"),
                  "END_IF;"]
    lines += ["ELSE", *_refuse(app, TARGET_KEY), "END_CASE;", "END_IF;"]
    return lines


def handler_logic(app, *, use_routines=False) -> tuple[str, ...]:
    """Core §3.10/§14, mirroring the oracle's ``_M_HandleHmiRequest``.

    The ordering is the contract and none of it is incidental. A request is
    consumed only when ``Sequence`` changes, and the retained value moves first,
    so a command runs exactly once however many scans it sits there. The
    response is cleared before dispatch, so nothing of the previous answer can
    be read as part of this one. ``Secret`` is wiped after sampling, as the
    oracle does. And ``AckSequence`` is written **last**, because a client polls
    it to learn the whole answer is present - set it early and a client can read
    an acknowledgement attached to a half-written response.
    """
    n = app.name
    import fraktal_ab_sets as sets
    import fraktal_ab_access as access
    import fraktal_ab_data_access as data
    enabled = app.access_users is not None
    lines = (access.cyclic(app) + data.cyclic(app) if enabled else []) + (sets.cyclic(app) if app.config_sets else []) + [
        "(* Lower the one-shot requests raised by an earlier scan.",
        "",
        "   This runs unconditionally, before the sequence check, and that is the",
        "   whole fix for the latch found on the bench on 2026-09-22. The mailbox",
        "   routine is JSR'd first and the Unit AOI runs later in the SAME scan,",
        "   so a request raised below has already been sampled by the time this",
        "   clears it - a one-scan pulse, with no countdown needed.",
        "",
        "   The oracle does not need any of this: _M_HandleHmiRequest calls",
        "   Start() and Stop() directly. This binding maps the same commands onto",
        "   level-sensitive tags that something else samples, and the mapping",
        "   inherited the raise without the lower. While those tags were",
        "   externally writable every client wrote 1 then 0 and supplied the",
        "   deassert itself; closing AB 11.2.1 made the mailbox their only",
        "   writer, which is what turned a latent defect into a blocking one. *)",
    ] + [f"FRK_{n}_{name} := 0;" for name in one_shot_requests()] + [
        "",
        "(* ModeRequest and RunRequest are NOT cleared here. ModeRequest is a",
        "   selection compared against Mode, so zeroing it would command AUTO",
        "   every scan. RunRequest is a genuine level - the chain stops when it",
        "   goes low - so STOP lowers it explicitly instead. *)",
        "",
        "(* Core 3.10/14: consume one committed request exactly once. *)",
        f"IF {_request(app, 'Sequence')} <> FRK_{n}_HmiLastSequence THEN",
        f"FRK_{n}_HmiLastSequence := {_request(app, 'Sequence')};",
        "",
        "(* Clear the answer before dispatch: no part of the previous one may",
        "   be read as part of this one. *)",
        f"{_response(app, 'Accepted')} := 0;",
        f"{_response(app, 'DiagnosticKey')} := 0;",
        "",
    ]
    if enabled:
        import fraktal_ab_generate as gen
        lines += [f"IF {_request(app, 'Kind')} <> {LOGIN} THEN", *access.wipe_secret(app), "END_IF;"]
        lines += data.reset_rejection(app)
        lines += [f'JSR({data.tag(app, "RefreshLevels")},0);']
        lines += access.check(app)
        lines += [f"IF {access.tag(app, 'Work')}.Permitted = 0 THEN",
                  *_refuse(app, access.DENIED),
                  *gen.report_open(gen.release_report_tag(app)),
                  *gen.report_add(gen.release_report_tag(app), _key(app, access.DENIED), 0, 0, 'ACCESS', access.DENIED),
                  *gen.report_close(gen.release_report_tag(app)), "ELSE"]
    lines += [f"CASE {_request(app, 'Kind')} OF"]
    lines.extend(_dispatch(app, use_routines=use_routines))
    lines.extend([
        "END_CASE;",
        *(["END_IF;", *access.after(app), f'JSR({data.tag(app, "RefreshLevels")},0);'] if enabled else []),
        "",
        "(* A refusal that named no reason would be indistinguishable from a",
        "   command that silently did nothing. *)",
        f"IF ({_response(app, 'Accepted')} = 0) AND "
        f"({_response(app, 'DiagnosticKey')} = 0) THEN",
        f"{_response(app, 'DiagnosticKey')} := {_key(app, REJECTED_KEY)};",
        "END_IF;",
        "",
        "(* Wipe the secret, as the oracle does. Clearing LEN alone would leave",
        "   the characters in DATA for anyone reading the member directly, so",
        "   the bytes go too. *)",
        f"{_request(app, 'Secret')}.LEN := 0;",
        f"FOR FRK_{n}_HmiWipe := 0 TO {SECRET_LENGTH - 1} DO",
        f"{_request(app, 'Secret')}.DATA[FRK_{n}_HmiWipe] := 0;",
        "END_FOR;",
        "",
        f"{_response(app, 'AckSequence')} := FRK_{n}_HmiLastSequence;",
        "END_IF;",
    ])
    return tuple(lines)


# --- the localization keys this mailbox can answer with ----------------------

REJECTED_KEY = "project.mailbox.refused.rejected"
UNKNOWN_KEY = "project.mailbox.refused.unknown_kind"
MODE_NOT_DECLARED_KEY = "project.mailbox.refused.mode_not_declared"
DECISION_RANGE_KEY = "project.mailbox.refused.decision_out_of_range"
TARGET_KEY = "project.mailbox.refused.target_not_addressable"
FORCE_NOT_PERMITTED_KEY = "project.mailbox.refused.force_not_permitted"
FORCE_TARGET_KEY = "project.mailbox.refused.force_target_unknown"
MODEL_NOT_DECLARED_KEY = "project.mailbox.refused.model_not_declared"
CONFIG_KEY_UNKNOWN_KEY = "project.mailbox.refused.config_key_unknown"
CONFIG_OUT_OF_RANGE_KEY = "project.mailbox.refused.config_out_of_range"
CONFIG_NOT_READY_KEY = "project.mailbox.refused.config_requires_ready"
# TC3's own key, reused rather than paralleled: the two bindings refuse the same
# acknowledgement for the same reason, and one key is one catalogue entry.
RESTORE_ACK_REFUSED_KEY = "std.error.configRestoreAckRefused"
# TC3's own release texts for the same two refusals.
MANUAL_HAS_NO_SEQUENCE_KEY = "std.release.manualHasNoAutoSequence"
MANUAL_MODE_REQUIRED_KEY = "std.release.manualModeRequired"
MANUAL_COMMAND_UNKNOWN_KEY = "project.mailbox.refused.command_not_in_catalog"
MANUAL_BUSY_KEY = "project.mailbox.refused.module_busy"
# TC3 refuses a style outside E_RunStyle with this key; one the Unit does not
# offer it refuses with none. Both get it here, so neither is a silent no.
RUN_STYLE_REFUSED_KEY = "std.error.unsupportedRunStyleRequest"
STEP_REFUSED_KEY = "project.mailbox.refused.step_needs_running_single_step"
HOLD_RUN_REFUSED_KEY = "project.mailbox.refused.hold_needs_running_hold_to_run"


def localization_keys() -> tuple[str, ...]:
    """Every key the handler can write, sorted so the numbering is stable."""
    import fraktal_ab_config as config
    import fraktal_ab_sets as sets
    import fraktal_ab_shelving as shelving
    extra = {config.CAPTURE_UNAVAILABLE_KEY, config.CAPTURE_SETUP_KEY,
             config.CAPTURE_REVISION_KEY, REJECTED_KEY, UNKNOWN_KEY, MODE_NOT_DECLARED_KEY,
             DECISION_RANGE_KEY, TARGET_KEY, FORCE_NOT_PERMITTED_KEY,
             FORCE_TARGET_KEY, MODEL_NOT_DECLARED_KEY,
             CONFIG_KEY_UNKNOWN_KEY, CONFIG_OUT_OF_RANGE_KEY,
             CONFIG_NOT_READY_KEY, RESTORE_ACK_REFUSED_KEY,
             MANUAL_HAS_NO_SEQUENCE_KEY,
             MANUAL_MODE_REQUIRED_KEY, MANUAL_COMMAND_UNKNOWN_KEY,
             MANUAL_BUSY_KEY, RUN_STYLE_REFUSED_KEY, STEP_REFUSED_KEY,
             HOLD_RUN_REFUSED_KEY}
    return tuple(sorted(set(REFUSED.values()) | extra | set(sets.KEYS) | set(shelving.KEYS)))


# --- commanding over CIP -----------------------------------------------------
#
# The mailbox tag is Read/Write, so a client with a CIP connection can command
# the station without a gateway in front of it. The evidence harnesses do
# exactly that: they are not operators, they are the apparatus, and putting a
# WebSocket server in the middle of a fixed-vector test would add a moving part
# the test is not about.
#
# The member-to-writes mapping lives here rather than in the gateway because
# both callers need it and it is a property of the contract, not of a transport.


def member_writes(app, member: str, value) -> list[tuple[str, object]]:
    """Validate a logical member and describe its legacy native representation.

    V3 command writers use ``command_writes`` and its complete native frame.
    This helper retains the public per-field bounds and the signed sequence
    conversion; decoded string/scalar argument storage is now private.
    """
    kinds = {name: kind for name, kind, _, _ in REQUEST_MEMBERS}
    widths = {name: length for name, _, length, _ in REQUEST_MEMBERS}
    if member not in kinds:
        raise ValueError(f"{member} is not a declared mailbox member")
    tag = f"{request_tag_name(app)}.{member}"

    if kinds[member] == STRING_MEMBER:
        text = "" if value is None else str(value)
        if not text.isascii():
            raise ValueError(f"{member} requires ASCII text on the pinned v33 binding")
        if len(text) > widths[member]:
            # Refused, never truncated: a shortened TargetPath would address a
            # different module.
            raise ValueError(
                f"{member} holds {widths[member]} characters, not {len(text)}")
        writes: list[tuple[str, object]] = [(f"{tag}.LEN", len(text))]
        if text:
            writes.append((f"{tag}.DATA", [ord(c) for c in text]))
        return writes
    if isinstance(value, bool):
        return [(tag, 1 if value else 0)]
    if member == 'Sequence':
        from fraktal_ab_mailbox_frame import signed
        return [(tag, signed(value))]
    return [(tag, int(value))]


def command_writes(app, kind: int, sequence: int, **arguments
                   ) -> list[tuple[str, object]]:
    """Every write one command is, in the order it must be issued.

    One complete, bounded frame stages all arguments; a separate ``Sequence``
    write commits it last. A payload failure stops before commit. A failed
    commit has an ambiguous outcome and must never be retried automatically.
    """
    supplied = dict(arguments)
    supplied["Kind"] = kind
    supplied["Sequence"] = sequence
    unknown = set(supplied) - {name for name, _, _, _ in REQUEST_MEMBERS}
    if unknown:
        raise ValueError(f"not mailbox members: {sorted(unknown)}")

    import fraktal_ab_mailbox_frame as frame
    return [(frame.native_path(app), frame.encode(app, supplied)),
            *member_writes(app, 'Sequence', sequence)]
