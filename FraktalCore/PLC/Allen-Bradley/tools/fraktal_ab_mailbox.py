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
* ``HmiResponse`` carries no ``Report`` or ``ConfigPage``. Release reports and
  the config manifest are recorded deferrals, and a member that could only ever
  be zero would claim a surface this binding does not have.

What this mailbox does **not** do is re-implement any machine behaviour. The
press demo already owns the mode owner, the S16 command handshake, the operator
decision and the per-module manual command. The mailbox is a request-routing
layer onto those; the PLC still re-checks its own rules.
"""

from __future__ import annotations

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
    MANUAL_COMMAND: "the declared manual jog; only with an empty TargetPath",
}

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
    SET_MODEL: "project.mailbox.refused.no_recipes",
    CONTROL_ON: "project.mailbox.refused.no_control_power",
    CONTROL_OFF: "project.mailbox.refused.no_control_power",
    SET_RUN_STYLE: "project.mailbox.refused.no_run_style",
    RELEASE_START: "project.mailbox.refused.no_release_reports",
    RELEASE_MANUAL: "project.mailbox.refused.no_release_reports",
    RELEASE_ACTION: "project.mailbox.refused.no_release_reports",
    RESET_OEE: "project.mailbox.refused.no_oee",
    WRITE_CONFIG: "project.mailbox.refused.no_config_manifest",
    QUERY_CONFIG: "project.mailbox.refused.no_config_manifest",
    CAPTURE_CONFIG: "project.mailbox.refused.no_config_manifest",
    SAVE_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    LOAD_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    LIST_CONFIG_SETS: "project.mailbox.refused.no_config_sets",
    ACK_CONFIG_RESTORE: "project.mailbox.refused.no_config_sets",
    EXPORT_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    IMPORT_CONFIG_SET: "project.mailbox.refused.no_config_sets",
    SHELVE_ALARM: "project.mailbox.refused.no_event_core",
    UNSHELVE_ALARM: "project.mailbox.refused.no_event_core",
    FORCE_CHANNEL: "project.mailbox.refused.no_physical_io",
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
SEQUENCE_WRAPS_AT = 2 ** 31

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

ONE_SHOT_REQUESTS = ("AbortRequest", "ResetRequest", "JogCommand",
                     "DecisionAnswer")
LEVEL_REQUESTS = ("RunRequest", "ModeRequest")


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
    return f"FRK_T_{app.name}HmiRequest"


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
        body.append(_member_xml(name, data_type, note, access))
    return (f'<DataType Name="{type_name}" Family="NoFamily" Class="User">'
            f"<Description><![CDATA[{comment}]]></Description>\n<Members>\n"
            + "\n".join(body) + "\n</Members>\n</DataType>")


def data_types(app) -> list[str]:
    """The mailbox's string types and its two contract records."""
    blocks = []
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
    return [
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


def _dispatch(app) -> list[str]:
    """One CASE branch per routed kind, then the refusals grouped by reason."""
    n = app.name
    lines: list[str] = []

    declared_modes = sorted({c.mode_ordinal for c in app.chains})
    guard = " OR ".join(f"({_request(app, 'IntValue')} = {m})"
                        for m in declared_modes)
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
    lines.extend(_accept(app, f"FRK_{n}_RunRequest := 1;"))

    lines.append(f"{STOP}: (* STOP *)")
    # STOP lowers the run level as well as raising the abort pulse. A STOP that
    # left RunRequest high would be a contradiction the Unit then has to
    # resolve every scan: the abort latches Aborted, and the run level tries to
    # set Running again the moment the abort is cleared.
    lines.extend(_accept(app, f"FRK_{n}_AbortRequest := 1;",
                         f"FRK_{n}_RunRequest := 0;"))

    lines.append(f"{OPERATOR_RESET}: (* OPERATOR_RESET *)")
    lines.extend(_accept(app, f"FRK_{n}_ResetRequest := 1;"))

    lines.append(f"{DECISION_ANSWER}: (* DECISION_ANSWER *)")
    lines.append(f"IF {_request(app, 'IntValue')} >= 1 THEN")
    lines.extend(_accept(app,
                         f"FRK_{n}_DecisionAnswer := {_request(app, 'IntValue')};"))
    lines.append("ELSE")
    lines.extend(_refuse(app, DECISION_RANGE_KEY))
    lines.append("END_IF;")

    lines.append(f"{MANUAL_COMMAND}: (* MANUAL_COMMAND *)")
    # The declared manual chain jogs one module. An addressed request cannot be
    # honoured, and honouring it against the wrong module would be worse than
    # refusing, so only an unaddressed jog is accepted. Testing LEN avoids a
    # string comparison, which is not a settled construct on this baseline.
    lines.append(f"IF {_request(app, 'TargetPath')}.LEN = 0 THEN")
    lines.extend(_accept(app, f"FRK_{n}_JogCommand := 1;"))
    lines.append("ELSE")
    lines.extend(_refuse(app, TARGET_KEY))
    lines.append("END_IF;")

    by_key: dict[str, list[int]] = {}
    for kind, portable in sorted(REFUSED.items()):
        by_key.setdefault(portable, []).append(kind)
    for portable, kinds in sorted(by_key.items()):
        lines.append(",".join(str(k) for k in kinds) + ":")
        lines.extend(_refuse(app, portable))

    lines.append("ELSE")
    lines.extend(_refuse(app, UNKNOWN_KEY))
    return lines


def handler_logic(app) -> tuple[str, ...]:
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
    lines = [
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
        f"CASE {_request(app, 'Kind')} OF",
    ]
    lines.extend(_dispatch(app))
    lines.extend([
        "END_CASE;",
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


def localization_keys() -> tuple[str, ...]:
    """Every key the handler can write, sorted so the numbering is stable."""
    extra = {REJECTED_KEY, UNKNOWN_KEY, MODE_NOT_DECLARED_KEY,
             DECISION_RANGE_KEY, TARGET_KEY}
    return tuple(sorted(set(REFUSED.values()) | extra))
