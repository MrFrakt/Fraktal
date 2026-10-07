#!/usr/bin/env python3
"""Emit a complete Logix project from one Fraktal/AB declaration.

This is the runtime base in its generated form. It turns a
``fraktal_ab_declaration.Application`` into contract UDTs, one module AOI per
declared module type, one mode-owner AOI per application, the routine that wires
them, and the full-project L5X - all from the committed declaration.

**Hand-authored L5X is forbidden.** Everything here is emitted, and the emitted
file is reproducible through the Phase 0 gate. If a construct is not expressible
in the declaration, the declaration grows; the output is never edited.

The generator refuses rather than emits when the declaration breaks a rule S16
established - see ``fraktal_ab_declaration.validate`` - and it additionally
asserts here, at emit time, that:

* the task it writes carries exactly the declared period, so the millisecond
  timeouts it converted stay true of the project that ships;
* nothing it emitted references a physical I/O operand; and
* no public contract UDT carries a ``BOOL`` member.

Module AOIs are generated **per application** for now. The reusable library form
is Phase 6 and is deliberately not attempted here.
"""

from __future__ import annotations
from fraktal_ab_models import ordinal_guard

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256
import fraktal_ab_declaration as decl
import fraktal_ab_config as config
import fraktal_ab_line as line
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
from fraktal_ab_st_format import format_lines


SCHEMA = "fraktal.ab.generated-application"
# Published in the manifest header so a reader can tell which controller
# the description belongs to without inferring it from the connection.
CONTROLLER_IDENTITY = "1769-L24ER-QB1B/A 33.014"

# Emitted verbatim ahead of every CASE ELSE. The fallback assigns a step number
# but it is not an edge of the declared graph, and the read-back gate has to be
# able to tell the difference without guessing.
MARKER_CASE_ELSE = (
    "(* CASE ELSE - undeclared step. A stall fallback, not a declared transition. *)"
)
SCHEMA_VERSION = 1

# Execution-state ordinals are Core §6.1's and are never renumbered.
STATE_READY, STATE_BUSY, STATE_DONE, STATE_ERROR, STATE_ABORTED = 0, 1, 2, 3, 4
SEVERITY_LOW, SEVERITY_HIGH = 0, 2


# --- the per-module handshake context --------------------------------------

def common_context_members() -> tuple[decl.Member, ...]:
    """What every module type carries: TC3's FB_ModuleBase, as DINTs (S12).

    The Core §6.1 handshake, the one published diagnostic and its onset, and
    the ordering check. The routine, the alarm log and the projection read
    only these, which is what lets them treat every type the same way.
    """
    return (
        decl.scalar("SchemaVersion", "which contract this instance holds", initial=1),
        decl.scalar("OutImm_ExecState", "Core §6.1 ordinals, never renumbered"),
        decl.boolean("OutImm_Held", "held is not an ExecState ordinal"),
        decl.reason("OutImm_Reason", "named reason for the current condition"),
        decl.scalar("OutImm_Severity", "0 LOW, 1 MED, 2 HIGH"),
        decl.scalar("OutImm_IoRoles",
                    "the type's io_roles the current reason implicates, a bit each"),
        decl.boolean("Execute", "command request"),
        decl.boolean("ExecutePrev", "edge memory"),
        decl.boolean("Abort", "abort request"),
        decl.boolean("Busy", ""),
        decl.boolean("Done", ""),
        decl.boolean("Error", ""),
        decl.boolean("Aborted", ""),
        decl.reason("ErrorID", "first-out reason, promoted from the diagnostic"),
        decl.scalar("RunCount", ""),
        decl.scalar("DoneCount", ""),
        decl.scalar("ErrorCount", ""),
        decl.scalar("AbortCount", ""),
        decl.scalar("ResetCount", ""),
        decl.scalar("ModuleScan", "the scan this module last ran - the ordering check"),
        *diagnostic_since_members(),
    )


def type_context_members(mtype: decl.ModuleType) -> tuple[decl.Member, ...]:
    """What one library type adds to the common context: its own plant,
    parameters and published facts. A type with none declared here cannot be
    emitted - the generator refuses rather than guessing a layout."""
    if mtype.type_key == library.CYLINDER.type_key:
        return _cylinder_members()
    if mtype.type_key == library.DIGITAL_INPUT.type_key:
        return _digital_input_members()
    if mtype.type_key == library.TWO_HAND.type_key:
        return _two_hand_members()
    if mtype.type_key == library.AIR_PRESSURE.type_key:
        return _air_pressure_members()
    raise decl.DeclarationError(f"no context layout for {mtype.type_key}")


def module_context_members(mtype: decl.ModuleType) -> tuple[decl.Member, ...]:
    """One type's full context: the common base, then the type's own."""
    return common_context_members() + type_context_members(mtype)


def module_members(module: decl.Module) -> tuple[decl.Member, ...]:
    """An instance's context, which is its type's."""
    return module_context_members(library.type_of(module))


def _digital_input_members() -> tuple[decl.Member, ...]:
    """TC3's ST_DigitalInputHal in, ST_DigitalInputOutImm out."""
    return (
        decl.boolean("RawValue", "the input as its source presents it"),
        decl.boolean("RawQuality", "whether the source vouches for it"),
        decl.boolean("OutImm_Value", "the input's value"),
        decl.boolean("OutImm_Quality", "the value can be trusted"),
    )


def _two_hand_members() -> tuple[decl.Member, ...]:
    """TC3's ST_TwoHandHal in, ST_TwoHandOutImm/OutCmd out, ParCfg's one
    member, and the edge memory R_TRIG keeps."""
    return (
        decl.boolean("RawLeft", "left button, as its source presents it"),
        decl.boolean("RawRight", "right button"),
        decl.boolean("RawSafe", "the certified two-hand result"),
        decl.boolean("RawHealthy", "the fieldbus carrying it is healthy"),
        decl.boolean("Par_RequireRelease",
                      "both buttons must be released between starts", initial=1),
        decl.boolean("OutImm_LeftPressed", ""),
        decl.boolean("OutImm_RightPressed", ""),
        decl.boolean("OutImm_SafeActive", "the certified result, on a healthy bus"),
        decl.boolean("OutImm_FieldbusHealthy", ""),
        decl.boolean("OutImm_Armed", "released since the last start"),
        decl.boolean("OutImm_StartPulse", "one scan: a fresh two-hand start"),
        decl.boolean("OutCmd_StartAccepted", "the start pulse was accepted"),
        decl.boolean("SafePrev", "edge memory for SafeActive"),
    )


def _air_pressure_members() -> tuple[decl.Member, ...]:
    """TC3's ST_AirPressureHal in, ST_AirPressureOutImm out, the station's
    ConflictTime, and what TON keeps."""
    return (
        decl.boolean("RawLow", "the low-pressure switch"),
        decl.boolean("RawOperating", "the operating-pressure switch"),
        decl.boolean("RawQuality", "whether the source vouches for them"),
        decl.boolean("ResetRequest", "the owner's operator reset, fed each scan"),
        decl.duration_ms("Par_ConflictTimeMs",
                         "how long both switches may read on before it is a fault",
                         initial=500),
        decl.duration_ms("Par_TaskPeriodMs", "the task period this instance is scanned at"),
        decl.duration_ms("ConflictMs", "how long both switches have read on"),
        decl.boolean("OutImm_LowPressure", ""),
        decl.boolean("OutImm_OperatingPressure", ""),
        decl.boolean("OutImm_Quality", ""),
        decl.boolean("OutImm_Contradictory", "both switches on, past ConflictTime"),
        decl.boolean("OutImm_PressureOk", "operating, not low, and trusted"),
    )


def type_feed(mtype: decl.ModuleType) -> tuple[tuple[str, object], ...]:
    """How the routine feeds a passive type from its one declared source:
    (member, "source" or a constant). TC3's HAL, simulated: a source that is
    present vouches for itself, and a simulated two-hand press is both
    buttons and the certified result together."""
    if mtype.type_key == library.DIGITAL_INPUT.type_key:
        return (("RawValue", "source"), ("RawQuality", 1))
    if mtype.type_key == library.TWO_HAND.type_key:
        return (("RawLeft", "source"), ("RawRight", "source"),
                ("RawSafe", "source"), ("RawHealthy", 1))
    if mtype.type_key == library.AIR_PRESSURE.type_key:
        # One simulated "air OK" is both switches, consistently: operating on
        # and low off, or the reverse. A conflict needs real switches.
        return (("RawOperating", "source"), ("RawLow", "not source"),
                ("RawQuality", 1), ("ResetRequest", "reset"))
    return ()


def _area_safe_lines(app: decl.Application, module: decl.Module) -> list[str]:
    """TC3's SetAreaSafe, evaluated for the module before it runs."""
    if module.area_safe is None:
        return []
    names = Names(app, in_aoi=False)
    ctx = ctx_tag_for(app, module.name)
    ok = cond_st(module.area_safe, names)
    return [f"IF {ok} THEN {ctx}.AreaSafe := 1; ELSE {ctx}.AreaSafe := 0; END_IF;"]


def permit_chain(app: decl.Application, module: decl.Module, selector: str,
                 on_missing, on_permitted: list[str]) -> list[str]:
    """TC3's SetDirectionalPermits for whichever command `selector` names:
    the permits are tested in their declared order, so the first missing one
    is the one acted on - TC3's press chooses the ram's key the same way.
    One source for the routine (the commanded direction, every scan) and the
    manual release report (the direction an operator asked about)."""
    names = Names(app, in_aoi=False)
    otherwise = ["ELSE", *on_permitted] if on_permitted else []
    lines: list[str] = []
    for command in module.commands:
        permits = decl.module_permits(module, command.name)
        if not permits:
            continue
        lines.append(f"{'ELSIF' if lines else 'IF'} {selector} = {command.ordinal} THEN")
        for index, permit in enumerate(permits):
            lines += [f"{'ELSIF' if index else 'IF'} NOT ({conds_st(permit.conditions, names)}) THEN",
                      *on_missing(permit)]
        lines += [*otherwise, "END_IF;"]
    return lines + [*otherwise, "END_IF;"] if lines else []


def _permit_lines(app: decl.Application, module: decl.Module,
                  keys: dict[str, int]) -> list[str]:
    """The permit for the direction the module is commanded this scan,
    evaluated before it runs."""
    ctx = ctx_tag_for(app, module.name)
    return permit_chain(
        app, module, f"{ctx}.ParCmd_Command",
        lambda permit: [f"{ctx}.Permit := 0;",
                        f"{ctx}.PermitKey := {keys[permit.key]}; (* {permit.key} *)"],
        [f"{ctx}.Permit := 1;", f"{ctx}.PermitKey := 0;"])


def module_setup_lines(app: decl.Application, module: decl.Module,
                       keys: dict[str, int] | None = None) -> list[str]:
    """What the routine does for one module each scan before it runs: its
    simulation injections, its feed, its bound configuration, its interlocks.
    One source, read by the routine and by every test that runs the layer."""
    if keys is None:
        keys = localization_numbers(app)
    ctx = ctx_tag_for(app, module.name)
    return [
        *(f"{ctx}.{injection}Request := {injection_tag(app, module, injection)};"
          for injection in library.type_of(module).injections),
        # A passive module is fed from its declared source, as TC3's HAL feeds
        # it (type_feed); configuration the application binds is carried in;
        # and its interlocks (TC3's SetAreaSafe, SetDirectionalPermits) are
        # evaluated.
        *_feed_lines(app, module),
        *(f"{ctx}.{member} := {record}Tag.{field};"
          for member, record, field in module.config),
        *_area_safe_lines(app, module),
        *_permit_lines(app, module, keys),
    ]


def localization_numbers(app: decl.Application) -> dict[str, int]:
    """Portable key -> the manifest's numeric key, for logic that publishes one."""
    import fraktal_ab_manifest as manifest

    return {row["PortableKey"]: row["NumericKey"]
            for row in manifest.content(app)["Localization"]}


def _feed_lines(app: decl.Application, module: decl.Module) -> list[str]:
    """The routine's feed of one passive module, from type_feed."""
    if not module.input:
        return []
    ctx = ctx_tag_for(app, module.name)
    lines: list[str] = []
    for member, value in type_feed(library.type_of(module)):
        if value == "source":
            lines.append(f"{ctx}.{member} := {module.input};")
        elif value == "not source":
            lines.append(f"IF {module.input} <> 0 THEN {ctx}.{member} := 0; "
                         f"ELSE {ctx}.{member} := 1; END_IF;")
        elif value == "reset":
            lines.append(f"{ctx}.{member} := FRK_{app.name}_ResetRequest;")
        else:
            lines.append(f"{ctx}.{member} := {value};")
    return lines


# Core §8.11.4(a), TC3's PL_Fraktal.MAX_CMD_STATS: timing rows per module, one
# per command ordinal 1..8. The HMI reads exactly 8.
CMD_STATS = 8


def command_timing_members() -> tuple[decl.Member, ...]:
    """TC3's ST_ModuleTiming, as DINT columns indexed by command ordinal - 1.
    A type's ordinals are fixed at declaration, so a row needs no search."""
    return (
        decl.duration_ms("TimMs", "the running command, accepted to now, holds included"),
        decl.scalar("TimSeen", "Done + Error + Abort counts already timed"),
        decl.scalar("TimSlot", "working: the row being closed"),
        decl.boolean("TimTrunc", "a command ordinal past the 8 rows ran"),
        decl.scalar("TimCount", "completed executions, by ordinal", dimension=CMD_STATS),
        decl.duration_ms("TimLast", "last duration, by ordinal", dimension=CMD_STATS),
        decl.duration_ms("TimMin", "shortest, by ordinal", dimension=CMD_STATS),
        decl.duration_ms("TimMax", "longest, by ordinal", dimension=CMD_STATS),
        decl.duration_ms("TimAvg", "running mean, by ordinal", dimension=CMD_STATS),
    )


def _command_timing_logic() -> list[str]:
    """TC3's _M_RecordCmdTiming, once per scan at the end of the handshake.

    TC3 closes a row on its BUSY->not-BUSY edge between two of its cycles, so
    a command accepted and finished in ONE cycle - a cylinder sent to the end
    it is already at - leaves no edge and is never timed. Core §8.11.4(a) says
    every command. Here a row closes whenever Done, Error or Abort counts
    move, which every completion does, including that one."""
    t = "Ctx.TimSlot"
    return [
        "",
        "(* Core 8.11.4(a): command timing (TC3 _M_RecordCmdTiming) *)",
        "IF (Ctx.DoneCount + Ctx.ErrorCount + Ctx.AbortCount) <> Ctx.TimSeen THEN",
        "Ctx.TimSeen := Ctx.DoneCount + Ctx.ErrorCount + Ctx.AbortCount;",
        f"IF (Ctx.ParCmd_Command >= 1) AND (Ctx.ParCmd_Command <= {CMD_STATS}) THEN",
        f"{t} := Ctx.ParCmd_Command - 1;",
        f"Ctx.TimCount[{t}] := Ctx.TimCount[{t}] + 1;",
        f"Ctx.TimLast[{t}] := Ctx.TimMs;",
        f"IF (Ctx.TimCount[{t}] = 1) OR (Ctx.TimMs < Ctx.TimMin[{t}]) THEN",
        f"Ctx.TimMin[{t}] := Ctx.TimMs;",
        "END_IF;",
        f"IF Ctx.TimMs > Ctx.TimMax[{t}] THEN",
        f"Ctx.TimMax[{t}] := Ctx.TimMs;",
        "END_IF;",
        f"Ctx.TimAvg[{t}] := Ctx.TimAvg[{t}] + "
        f"((Ctx.TimMs - Ctx.TimAvg[{t}]) / Ctx.TimCount[{t}]);",
        "ELSE",
        "Ctx.TimTrunc := 1;",
        "END_IF;",
        "END_IF;",
    ]


def _cylinder_members() -> tuple[decl.Member, ...]:
    return (
        decl.scalar("Par_Speed", "simulated plant units per scan", initial=25),
        decl.duration_ms("Par_TimeoutMs", "command timeout, milliseconds", initial=500),
        # The task period this instance runs at. It was a literal in the AOI,
        # which made the AOI belong to one application's task rate - a 10 ms
        # and a 20 ms station would each need their own copy of the cylinder.
        # It is part of the contract (S16 found that), so it travels with the
        # instance and the type stays one definition.
        decl.duration_ms("Par_TaskPeriodMs",
                         "the task period this instance is scanned at"),
        decl.scalar("Par_TimeoutScans", "the same timeout in whole task scans"),
        decl.scalar("ParCmd_Command", "requested command ordinal"),
        decl.scalar("ParCmd_Target", "requested plant target"),
        decl.scalar("ParCmd_Latched", "target latched on the accepted edge"),
        decl.scalar("OutCmd_FinalPos", "position when the command completed"),
        decl.boolean("OutCmd_Ok", "the last command completed cleanly"),
        decl.scalar("OutImm_Pos", "live simulated position"),
        decl.duration_ms("ElapsedMs", "integrated from the declared task period"),
        decl.scalar("HeldScans", "scans spent held; the timeout does not accrue here"),
        decl.scalar("FaultRequest", "simulated device fault: the plant stops moving"),
        decl.scalar("FaultScans", "scans the plant was held still by FaultRequest"),
        *command_timing_members(),
        decl.scalar("HoldRequest", "simulated permissive loss"),
        decl.boolean("AreaSafe", "TC3's SetAreaSafe: the application's interlock",
                     initial=1),
        # TC3's SetDirectionalPermits, evaluated by the routine for the
        # commanded direction each scan; PermitKey names the missing one.
        decl.boolean("Permit", "the commanded direction is permitted", initial=1),
        decl.scalar("PermitKey", "localization key of the missing permit, 0 when "
                    "permitted"),
        # TC3's OutImm.Extended / Retracted: the end sensors, from the
        # simulated position.
        decl.boolean("OutImm_Extended", "the extended end sensor"),
        decl.boolean("OutImm_Retracted", "the retracted end sensor", initial=1),
        # TC3's manual command (§7.6.1): the command the operator asked for in
        # MANUAL, 0 when none. Written by the mailbox, driven by the mode owner.
        decl.scalar("ManualCmd", "the manual command in progress, 0 when none"),
    )


def diagnostic_since_members() -> tuple[decl.Member, ...]:
    """Core §2.7 Since: when the published diagnostic began, stamped by the
    routine on the scan its reason changed. Onset is history, so the gateway
    cannot derive it from a poll; the controller keeps it."""
    return (
        decl.reason("DiagStamped", "the reason the Since stamp belongs to"),
        decl.scalar("DiagSinceDate", "YYYYMMDD the diagnostic began, controller clock"),
        decl.scalar("DiagSinceTime", "hhmmssmmm the diagnostic began"),
    )


def default_model_ordinal(app: decl.Application) -> int:
    """1-based ordinal of the declared default model, or 0 when there is none.

    This is the value `ModelOrdinal` starts at, so a freshly downloaded
    station publishes the model its configuration actually is rather than
    reporting none until someone runs a changeover it does not need.
    """
    for index, model in enumerate(app.models, start=1):
        if model.code == app.default_model:
            return index
    return 0


# Core §3.8b transport ordinals (E_ConfigRestorePolicy, E_ConfigStore). Spelled
# out rather than imported: they are an append-only PLC/HMI contract, and a
# renumbering has to break this file loudly.
CONFIG_RESTORE_DEFAULTS_AND_ANNUNCIATE = 0
CONFIG_STORE_LOCAL_RETAIN = 0


def unit_context_members(app: decl.Application) -> tuple[decl.Member, ...]:
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.scalar("Par_TaskPeriodMs", "the declared period this project was emitted for",
                    initial=app.task_period_ms),
        decl.scalar("Mode", "active mode ordinal"),
        decl.scalar("ModeRequest", "requested mode ordinal"),
        # Core §3.8 changeover. The REQUEST is what the operator asked for and
        # the ORDINAL is what the machine committed to; they differ for the
        # whole of a changeover, which is the point - a station half way
        # through one is still running the previous model's numbers.
        decl.scalar("ModelRequest", "requested model ordinal, 0 = none"),
        decl.scalar("CommitModel",
                    "the model the chain asked to commit; 0 = nothing pending"),
        decl.scalar("ModelOrdinal", "committed model ordinal, 0 = none",
                    initial=default_model_ordinal(app)),
        decl.scalar("ModeSwitches", ""),
        decl.scalar("Step", "active step number"),
        decl.scalar("PrevStep", ""),
        decl.boolean("Running", ""),
        decl.boolean("Complete", ""),
        decl.boolean("Aborted", ""),
        decl.boolean("Error", "the unit adopted a fault"),
        decl.reason("ErrorID", "adopted first-out, verbatim from the child"),
        decl.scalar("ErrorSource", "which module the adopted fault came from"),
        decl.reason("ReportedReason", "reported, NOT adopted - a message"),
        decl.scalar("ReportedCount", ""),
        decl.scalar("ReportedSource", "which module the last report came from"),
        decl.scalar("DecisionId", "the decision the chain is waiting on, 0 when none"),
        decl.scalar("DecisionAnswer", "written by the operator surface"),
        decl.scalar("DecisionCount", ""),
        decl.scalar("CycleCount", ""),
        decl.scalar("GoodCount", ""),
        decl.scalar("ScrapCount", ""),
        # Core §8.11.2 / TC3's CountRework: parts sent for rework. A chain
        # counts one with a mark, as it counts good and scrap; the press
        # declares no rework verdict, on either binding, so it stays 0.
        decl.scalar("ReworkCount", "parts sent for rework"),
        decl.scalar("OrderFail", "a child module had not run when the owner ran"),
        decl.scalar("StepScan", "scan on which the active step was entered"),
        decl.scalar("RunRequest", ""),
        decl.scalar("AbortRequest", ""),
        decl.scalar("ResetRequest", ""),
        # Core §6.9(a): ONE published diagnostic, chosen here rather than by
        # each reader - an adopted fault, else the held reason. A report is an
        # occurrence in the alarm ring, never the Unit's standing diagnostic.
        decl.reason("DiagReason", "the Unit's published diagnostic reason"),
        # Core §6.9 stall watchdog, TC3's _tStall: accrues while the chain runs
        # a step with nothing held, restarts on every step change.
        decl.duration_ms("StallTimeMs", "how long a step may run unheld",
                         initial=app.stall_time_ms),
        # TC3's CurrentStep.ExpectedTime: what the active step is expected to
        # take (decl.expected_member), 0 for no expectation. Where it is set
        # the watchdog times the step against it instead of StallTimeMs.
        decl.duration_ms("StepExpectedMs", "what the active step is expected to "
                         "take, 0 for no expectation"),
        decl.duration_ms("StallMs", "time on the current step, running and unheld"),
        decl.scalar("StallStep", "the step StallMs is timing", initial=-1),
        decl.boolean("StepTimedOut", "the current step outran StallTimeMs"),
        decl.scalar("DiagIoRoles", "the adopted child's implicated io_roles, "
                    "captured the scan it was adopted"),
        *diagnostic_since_members(),
        # TC3 §3.4.2 run styles, when the application paces its sequences.
        *((decl.scalar("RunStyle", "Core E_RunStyle, chosen by the operator"),
           decl.boolean("StepPending", "a SINGLE_STEP request not yet used"),
           decl.boolean("HoldRun", "HOLD_TO_RUN's button, held - NON-SAFETY"),
           # CONTINUOUS's permit, until the mode owner first computes it.
           decl.boolean("StepPermit", "this scan's run-style permit to issue",
                        initial=1),
           decl.boolean("Issued", "the active step has issued its command"))
          if pacing(app) else ()),
        # TC3's press _startLatched (decl.StartControl), when declared.
        *((decl.boolean("StartLatched", "a start pulse, with what it requires "
                        "present; the start step waits on it"),)
          if app.start_control else ()),
    )


def chart_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """Core §3.13 in miniature: a cursor, per-step marks and a stall reason."""
    n = app.chart_steps
    return (
        decl.scalar("StepCursor", "index of the active step in these arrays"),
        decl.scalar("ActiveStepNumber", ""),
        decl.reason("StallReason", "why the active step is not advancing, 0 when it is"),
        decl.scalar("ActiveChain", ""),
        decl.duration_ms("CurrentStepMs", "time in the active step"),
        # TC3's M_Delay timer. Separate from CurrentStepMs because a delay can
        # pause (N220's dwell, while the two-hand is released) and the step's
        # own duration must still count the pause.
        decl.duration_ms("DelayMs", "time the active delay has run while its "
                         "conditions held"),
        decl.scalar("Visited", "1 once the step has been entered", dimension=n),
        decl.duration_ms("LastMs", "duration of the step's last completed visit", dimension=n),
        decl.scalar("EnterCount", "visits to the step", dimension=n),
        decl.scalar("CondOk", "1 while the active step's condition record i holds "
                    "(Core 6.9(b)); labelled by the declaration",
                    dimension=decl.MAX_STEP_CONDS),
        # Core 3.13 rows, as TC3 keeps them: discovered by visit, numbered in
        # the order they were first entered, and scoped to one mode session.
        # A mode change starts a new epoch instead of clearing the arrays -
        # O(1) on that scan, where a clear would walk every step - and a step
        # whose epoch is stale is simply rediscovered on its next visit.
        decl.scalar("RowEpoch", "the current mode session; bumped on mode change",
                    initial=1),
        decl.scalar("RowCount", "rows discovered this mode session"),
        decl.scalar("RowEpochOf", "the session in which the step was last "
                    "discovered", dimension=n),
        decl.scalar("RowOf", "the step's row number in that session", dimension=n),
        decl.reason("WarnReason", "6.9(e): the reason a report left on this step's "
                    "row this visit, 0 when none", dimension=n),
        decl.scalar("WarnSource", "the module that report came from", dimension=n),
    )


# --- XML emission -----------------------------------------------------------

def _member_xml(member: decl.Member) -> str:
    comment = ""
    if member.comment:
        safe = member.comment.replace("]]>", "]] >")
        comment = f"<Description><![CDATA[{safe}]]></Description>"
    return (
        f'<Member Name="{member.name}" DataType="{member.data_type}" '
        f'Dimension="{member.dimension}" Radix="Decimal" Hidden="false" '
        f'ExternalAccess="{member.external_access}">{comment}</Member>'
    )


def data_types(app: decl.Application) -> str:
    blocks: list[str] = []
    records = list(app.records)
    if app.line is not None:
        import fraktal_ab_line as line
        records += line.records(app)
    if app.access_users is not None:
        import fraktal_ab_access as access
        records += access.records(app)
        import fraktal_ab_data_access as data
        records += data.records(app)
    if app.config_sets:
        import fraktal_ab_sets as sets
        records += [decl.Record(sets.request_name(), sets.request_members()),
                    decl.Record(sets.state_name(app), sets.state_members(app))]
    if editable_values(app):
        records.append(decl.Record(config.audit_name(), config.audit_members(),
                                   "Core 3.8c accepted configuration writes"))
    for mtype in library.types_used(app):
        records.append(decl.Record(module_context_name(mtype),
                                   module_context_members(mtype),
                                   f"the Core §6.1 context of {mtype.type_key}"))
    records.append(decl.Record(unit_context_name(app), unit_context_members(app),
                               "the mode owner's context"))
    records.append(decl.Record(chart_name(app), chart_members(app),
                               "Core §3.13 step marks"))
    records.append(decl.Record(config_persist_name(app), config_persist_members(),
                               "Core §3.8b configuration durability"))
    if model_cfg_members(app):
        records.append(decl.Record(model_cfg_name(app), model_cfg_members(app),
                                   "Core §3.8a per-model configuration"))
    records.append(decl.Record(alarm_active_name(), alarm_active_members(),
                               "Core §8.3 open alarm events"))
    records.append(decl.Record(alarm_ring_name(), alarm_ring_members(),
                               "Core §8.3 closed alarm history"))
    import fraktal_ab_shelving as shelving
    records.append(shelving.record())
    records.append(decl.Record(release_report_name(app), release_report_members(),
                               "Core §7.8 release report"))
    records.append(decl.Record(oee_name(), oee_members(),
                               "Core §8.5.1 OEE time accounting and trend"))
    records.append(decl.Record(profiler_name(), profiler_members(app),
                               "Core §8.11.4 cycle-time profile"))
    if app.state_flags:
        records.append(decl.Record(state_flags_name(app), state_flags_members(app),
                                   "Core §3.12 derived state flags"))
    records.append(decl.Record(health_probe_name(), health_probe_members(),
                               "Core §8.12 controller health probe (AB S3)"))
    if app.system_health is not None:
        records.append(decl.Record(health_cfg_name(app), health_cfg_members(app),
                                   "Core §8.12 health thresholds"))
        records.append(decl.Record(system_health_name(), system_health_members(),
                                   "Core §8.12 system health"))
    for record in records:
        members = "\n".join(_member_xml(m) for m in record.members)
        description = ""
        if record.comment:
            description = f"<Description><![CDATA[{record.comment}]]></Description>"
        blocks.append(
            f'<DataType Name="{record.name}" Family="NoFamily" Class="User">'
            f"{description}\n<Members>\n{members}\n</Members>\n</DataType>"
        )
    if app.model_capacity:
        import fraktal_ab_models as models
        members = "\n".join(_member_xml(m) for m in models.members(app))
        blocks.append(f'<DataType Name="{models.type_name()}" Family="NoFamily" Class="User"><Members>{members}</Members></DataType>')
    blocks.extend(mailbox.data_types(app))
    blocks.extend(manifest.data_types(app))
    return "<DataTypes>\n" + "\n".join(blocks) + "\n</DataTypes>"


def module_context_name(mtype: decl.ModuleType) -> str:
    """A library type's context UDT: `std.moduleType.cylinder` ->
    `FRK_T_CylinderCtx`. Named for the type and for no application, because a
    library AOI's InOut parameter cannot name a type that changes with whoever
    embeds it - and one shape for every type stopped being true the day the
    second type needed different members."""
    leaf = mtype.type_key.rsplit(".", 1)[-1]
    return f"FRK_T_{leaf[:1].upper()}{leaf[1:]}Ctx"


def unit_context_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}UnitCtx"


def config_persist_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}ConfigPersist"


def config_persist_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_ConfigPersist"


def model_scoped_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """The ParCfg members a changeover rewrites, in record order.

    Derived from what the models declare rather than marked a second time on
    the member: `Model.values` already names them, and a member that is
    model-scoped in one place and not the other is a contradiction nobody would
    notice until a changeover wrote half a model.
    """
    if not app.models:
        return ()
    par_cfg = next((r for r in app.records if r.par_cfg), None)
    if par_cfg is None:
        return ()
    named = set(app.models[0].values)
    return tuple(m for m in par_cfg.members if m.name in named)


def is_model_scoped(app: decl.Application, record: decl.Record, member_name: str) -> bool:
    """A model value belongs to ParCfg, never a same-named Line/station field."""
    return record.par_cfg and any(m.name == member_name for m in model_scoped_members(app))


def model_cfg_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}ModelCfg"


def model_cfg_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_ModelCfg"


def model_cfg_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """One model's stored values, led by §3.8a's never-written marker."""
    scoped = model_scoped_members(app)
    if not scoped:
        return ()
    return (decl.scalar(decl.SCHEMA_VERSION_MEMBER,
                        "0 = never written (Core §3.8a)", initial=0),) + scoped


def editable_values(app: decl.Application) -> tuple[tuple[int, decl.Record, decl.Member], ...]:
    """Every editable configuration value, with the ordinal the wire uses.

    Ordinals are 1-based and assigned by declaration order: record order, then
    member order. They are what the CONTROLLER dispatches on, because it cannot
    read the client's string write key — the gateway resolves key to ordinal
    the same way it already resolves a force channel's path to a bit mask, and
    the controller re-checks the resolved number against this same list.

    That split is the point. Translation happens where strings can be read;
    authority stays where §5.6 requires it, on the controller, which refuses an
    ordinal it does not have and a value outside the declared range.
    """
    out: list[tuple[int, decl.Record, decl.Member]] = []
    for record in app.records:
        for member in record.members:
            if member.editable:
                out.append((len(out) + 1, record, member))
    return tuple(out)


def root_field_records(app: decl.Application):
    """Root-owned published fields, shared by manifest and capture binding."""
    out = [("Unit", unit_context_members(app)), ("Chart", chart_members(app)),
           ("AlarmActive", alarm_active_members()), ("AlarmRing", alarm_ring_members()),
           ("Oee", oee_members()), ("Profiler", profiler_members(app)),
           ("HealthProbe", health_probe_members())]
    if app.system_health is not None:
        out += [("HealthCfg", health_cfg_members(app)),
                ("SystemHealth", system_health_members())]
    if app.state_flags:
        out.append(("StateFlags", state_flags_members(app)))
    if editable_values(app):
        out.append(("ConfigAudit", config.audit_members()))
    if app.config_sets:
        import fraktal_ab_sets as sets
        out.append(("ConfigSetState", sets.state_members(app)))
    if app.line is not None:
        import fraktal_ab_line as line
        out += [('LineState', line.state_members()), ('LineShift', line.shift_members())]
    if app.access_users is not None:
        import fraktal_ab_access as access
        out += [("AccessState", access.state_members(app)), ("AccessAudit", access.audit_members())]
        import fraktal_ab_data_access as data
        out += [("DataPolicy", data.policy_members(app)), ("DataLevels", data.levels_members(app))]
    return tuple(out + [(r.name, r.members) for r in app.records])


def capture_source_tag(app: decl.Application, source: str) -> str:
    prefix, member = source.split(".")
    tag = f"{prefix}Tag" if prefix in {r.name for r in app.records} else f"FRK_{app.name}_{prefix}"
    return f"{tag}.{member}"


def station_cfg_record(app: decl.Application) -> decl.Record | None:
    """The one §3.8a deployment record, or None if this station has none."""
    return next((r for r in app.records if r.station_cfg), None)


def config_persist_members() -> tuple[decl.Member, ...]:
    """Core §3.8b — the root's published answer to "is my configuration safe?".

    All DINT, because S12 froze the v33 type map and a public contract UDT
    carries no BOOL. `LostModuleId` is an ordinal rather than a path string for
    the same reason: the projection already resolves module identities, so the
    controller carries the number and the client is handed the canonical path.
    """
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        # Parameter-set document operations wait for the host's store receipt.
        # Retention of ordinary configuration writes is a separate provisional
        # controller-memory claim; these flags do not prove that retention.
        decl.scalar("Pending", "an accepted write is not yet durable"),
        decl.scalar("Failed", "the store refused, or the window elapsed"),
        decl.scalar("WindowMs", "the declared window a write has to become durable"),
        decl.scalar("PendingSince", "0 = nothing pending"),
        # No parameter-set store: SAVE/LOAD/LIST_CONFIG_SET are refused by name.
        decl.scalar("StorePresent", "a set store is wired"),
        decl.scalar("StoreKind", "E_ConfigStore ordinal"),
        # Restore. This half IS live on this binding.
        decl.scalar("RestoreLost", "a retained image was rejected at startup"),
        decl.scalar("RestoreAcknowledged", "an operator has accepted the loss"),
        decl.scalar("LostModuleId", "manifest module ordinal, 0 = none"),
        decl.scalar("RestorePolicy", "E_ConfigRestorePolicy ordinal"),
    )


def chart_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}Chart"


def type_aoi_name(mtype: decl.ModuleType) -> str:
    """The library AOI's name: from the type, never from an application.

    `std.moduleType.cylinder` -> `FRK_M_Cylinder`. It was `FRK_M_<App><Module>`,
    one AOI per INSTANCE - three identical cylinders were three definitions
    that differed in one comment line.
    """
    leaf = mtype.type_key.rsplit(".", 1)[-1]
    return f"FRK_M_{leaf[:1].upper()}{leaf[1:]}"


def module_aoi_name(app: decl.Application, module: decl.Module) -> str:
    """The AOI an instance calls: its type's. Kept by this name so every call
    site asks the one question - which AOI does this module run - and gets the
    library's answer."""
    return type_aoi_name(library.type_of(module))


def module_logic(app: decl.Application, module: decl.Module) -> tuple[str, ...]:
    """The logic an instance runs, which is its type's and nothing else."""
    return type_logic(library.type_of(module))


def unit_aoi_name(app: decl.Application) -> str:
    return f"FRK_U_{app.name}"


def _parameter(name: str, data_type: str, usage: str, *, radix: str | None = None,
               required: bool = True, visible: bool = True,
               constant: bool | None = False,
               external_access: str | None = None) -> str:
    attributes = [f'Name="{name}"', 'TagType="Base"', f'DataType="{data_type}"',
                  f'Usage="{usage}"']
    if radix is not None:
        attributes.append(f'Radix="{radix}"')
    attributes.extend([f'Required="{str(required).lower()}"',
                       f'Visible="{str(visible).lower()}"'])
    if constant is not None:
        attributes.append(f'Constant="{str(constant).lower()}"')
    if external_access is not None:
        attributes.append(f'ExternalAccess="{external_access}"')
    return f"<Parameter {' '.join(attributes)}/>"


ENABLE_PARAMETERS = (
    _parameter("EnableIn", "BOOL", "Input", radix="Decimal", required=False,
               visible=False, constant=None, external_access="Read Only"),
    _parameter("EnableOut", "BOOL", "Output", radix="Decimal", required=False,
               visible=False, constant=None, external_access="Read Only"),
)


def _aoi(name: str, note: str, parameters: tuple[str, ...],
         logic: tuple[str, ...], dependencies: tuple[str, ...]) -> str:
    parameter_block = "\n".join(parameters)
    lines = st_content_lines(logic)
    deps = "\n".join(f'<Dependency Type="DataType" Name="{d}"/>' for d in dependencies)
    return f"""<AddOnInstructionDefinition Name="{name}" Revision="1.0" ExecutePrescan="false" ExecutePostscan="false" ExecuteEnableInFalse="false" CreatedDate="2026-09-07T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-09-07T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
<RevisionNote><![CDATA[{note}]]></RevisionNote>
<Parameters>
{parameter_block}
</Parameters>
<LocalTags/>
<Routines>
<Routine Name="Logic" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
<Dependencies>
{deps}
</Dependencies>
</AddOnInstructionDefinition>"""


# --- module logic -----------------------------------------------------------

def _execute_drop_reset(*extra: str, edge: bool = False) -> list[str]:
    """Core §6.1's Execute-drop reset, the base behaviour every type shares:
    a terminal state clears only when Execute drops. `extra` is what a type
    resets of its own.

    A commanded type resets while Execute is low. A passive one resets on the
    DROP itself (`edge`): its only command state is a refused command, and a
    level reset would clear, every scan, a fault it raises of its own - the
    air monitor's latched switch conflict."""
    return [
        "(* Execute-drop reset: a terminal state clears only when Execute drops *)",
        "IF (Ctx.Execute = 0) AND (Ctx.ExecutePrev <> 0) THEN" if edge
        else "IF Ctx.Execute = 0 THEN",
        "IF (Ctx.Done <> 0) OR (Ctx.Error <> 0) OR (Ctx.Aborted <> 0) THEN",
        "Ctx.ResetCount := Ctx.ResetCount + 1;",
        "END_IF;",
        "Ctx.Done := 0;",
        "Ctx.Error := 0;",
        "Ctx.Aborted := 0;",
        "Ctx.ErrorID := 0;",
        "Ctx.Busy := 0;",
        "Ctx.OutImm_Held := 0;",
        "Ctx.OutImm_Reason := 0;",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_READY};",
        *extra,
        "END_IF;",
    ]


def _digital_input_logic(mtype: decl.ModuleType) -> tuple[str, ...]:
    """TC3's FB_DigitalInputCM: Value and Quality as the source presents them,
    and any command refused - a passive monitor has nothing to do."""
    import fraktal_ab_reasons as reasons

    return (
        f"(* {mtype.type_key}: a passive input, TC3's FB_DigitalInputCM. *)",
        "(* Generated from the declaration - never hand-edit. *)",
        "Ctx.ModuleScan := Scan;",
        "IF Ctx.RawValue <> 0 THEN Ctx.OutImm_Value := 1; ELSE Ctx.OutImm_Value := 0; END_IF;",
        "IF Ctx.RawQuality <> 0 THEN Ctx.OutImm_Quality := 1; ELSE Ctx.OutImm_Quality := 0; END_IF;",
        "",
        *_passive_handshake(mtype),
    )


def _passive_handshake(mtype: decl.ModuleType) -> list[str]:
    """The §6.1 handshake of a type that takes no command, written once: the
    base's Execute-drop reset, and any command refused with
    UNSUPPORTED_COMMAND as TC3's passive CMs refuse it."""
    import fraktal_ab_reasons as reasons

    refused = mtype.reasons["UNSUPPORTED_COMMAND"]
    severity = reasons.rationalize("UNSUPPORTED_COMMAND", refused).priority
    return [
        *_execute_drop_reset(edge=True),
        "",
        "(* A passive module takes no command: refused, as TC3 refuses it *)",
        "IF (Ctx.Execute <> 0) AND (Ctx.ExecutePrev = 0) THEN",
        "Ctx.RunCount := Ctx.RunCount + 1;",
        "Ctx.Error := 1;",
        "Ctx.Busy := 0;",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        f"Ctx.ErrorID := {refused};",
        f"Ctx.OutImm_Reason := {refused};",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {severity};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "END_IF;",
        "",
        "Ctx.ExecutePrev := Ctx.Execute;",
    ]


def _air_pressure_logic(mtype: decl.ModuleType) -> tuple[str, ...]:
    """TC3's FB_AirPressureMonitorCM.OnCyclic: pressure OK from two switches,
    and their conflict, qualified over ConflictTime, as a latched fault."""
    import fraktal_ab_reasons as reasons

    conflict = mtype.reasons["AIR_SWITCH_CONFLICT"]
    severity = reasons.rationalize("AIR_SWITCH_CONFLICT", conflict).priority
    both = (1 << mtype.io_roles.index("low")) | (1 << mtype.io_roles.index("operating"))
    return (
        f"(* {mtype.type_key}: two pressure switches, TC3's FB_AirPressureMonitorCM. *)",
        "(* Generated from the declaration - never hand-edit. *)",
        "Ctx.ModuleScan := Scan;",
        "IF Ctx.RawLow <> 0 THEN Ctx.OutImm_LowPressure := 1; ELSE Ctx.OutImm_LowPressure := 0; END_IF;",
        "IF Ctx.RawOperating <> 0 THEN Ctx.OutImm_OperatingPressure := 1; "
        "ELSE Ctx.OutImm_OperatingPressure := 0; END_IF;",
        "IF Ctx.RawQuality <> 0 THEN Ctx.OutImm_Quality := 1; ELSE Ctx.OutImm_Quality := 0; END_IF;",
        "(* TC3's _conflictTimer: both switches on, qualified over ConflictTime *)",
        "IF (Ctx.OutImm_LowPressure <> 0) AND (Ctx.OutImm_OperatingPressure <> 0) THEN",
        "Ctx.ConflictMs := Ctx.ConflictMs + Ctx.Par_TaskPeriodMs;",
        "ELSE",
        "Ctx.ConflictMs := 0;",
        "END_IF;",
        "IF (Ctx.OutImm_LowPressure <> 0) AND (Ctx.OutImm_OperatingPressure <> 0) "
        "AND (Ctx.ConflictMs >= Ctx.Par_ConflictTimeMs) THEN",
        "Ctx.OutImm_Contradictory := 1;",
        "ELSE",
        "Ctx.OutImm_Contradictory := 0;",
        "END_IF;",
        "IF (Ctx.OutImm_OperatingPressure <> 0) AND (Ctx.OutImm_LowPressure = 0) "
        "AND (Ctx.OutImm_Quality <> 0) THEN",
        "Ctx.OutImm_PressureOk := 1;",
        "ELSE",
        "Ctx.OutImm_PressureOk := 0;",
        "END_IF;",
        "(* The conflict is a fault naming both switches, latched until an *)",
        "(* operator reset clears it once the switches agree again (TC3).  *)",
        "IF Ctx.OutImm_Contradictory <> 0 THEN",
        "IF Ctx.Error = 0 THEN Ctx.ErrorCount := Ctx.ErrorCount + 1; END_IF;",
        "Ctx.Error := 1;",
        f"Ctx.ErrorID := {conflict};",
        f"Ctx.OutImm_Reason := {conflict};",
        f"Ctx.OutImm_IoRoles := {both};",
        f"Ctx.OutImm_Severity := {severity};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        f"ELSIF (Ctx.ResetRequest <> 0) AND (Ctx.ErrorID = {conflict}) THEN",
        "Ctx.ResetCount := Ctx.ResetCount + 1;",
        "Ctx.Error := 0;",
        "Ctx.ErrorID := 0;",
        "Ctx.OutImm_Reason := 0;",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_READY};",
        "END_IF;",
        "",
        *_passive_handshake(mtype),
    )


def _two_hand_logic(mtype: decl.ModuleType) -> tuple[str, ...]:
    """TC3's FB_TwoHandStartCM.OnCyclic, line for line: a start edge from a
    certified two-hand result, armed only by a release between starts."""
    return (
        f"(* {mtype.type_key}: a start edge, TC3's FB_TwoHandStartCM. *)",
        "(* Generated from the declaration - never hand-edit. *)",
        "Ctx.ModuleScan := Scan;",
        "Ctx.OutImm_StartPulse := 0;",
        "Ctx.OutCmd_StartAccepted := 0;",
        "IF Ctx.RawLeft <> 0 THEN Ctx.OutImm_LeftPressed := 1; ELSE Ctx.OutImm_LeftPressed := 0; END_IF;",
        "IF Ctx.RawRight <> 0 THEN Ctx.OutImm_RightPressed := 1; ELSE Ctx.OutImm_RightPressed := 0; END_IF;",
        "IF Ctx.RawHealthy <> 0 THEN Ctx.OutImm_FieldbusHealthy := 1; ELSE Ctx.OutImm_FieldbusHealthy := 0; END_IF;",
        "(* SafeActive is the safety system's result, never computed here *)",
        "IF (Ctx.RawSafe <> 0) AND (Ctx.OutImm_FieldbusHealthy <> 0) THEN",
        "Ctx.OutImm_SafeActive := 1;",
        "ELSE",
        "Ctx.OutImm_SafeActive := 0;",
        "END_IF;",
        "IF Ctx.OutImm_FieldbusHealthy = 0 THEN",
        "Ctx.OutImm_Armed := 0;",
        "ELSIF (Ctx.OutImm_LeftPressed = 0) AND (Ctx.OutImm_RightPressed = 0) "
        "AND (Ctx.RawSafe = 0) THEN",
        "Ctx.OutImm_Armed := 1;",
        "END_IF;",
        "IF (Ctx.OutImm_SafeActive <> 0) AND (Ctx.SafePrev = 0) AND "
        "((Ctx.OutImm_Armed <> 0) OR (Ctx.Par_RequireRelease = 0)) THEN",
        "Ctx.OutImm_StartPulse := 1;",
        "Ctx.OutCmd_StartAccepted := 1;",
        "Ctx.OutImm_Armed := 0;",
        "END_IF;",
        "Ctx.SafePrev := Ctx.OutImm_SafeActive;",
        "",
        *_passive_handshake(mtype),
    )


def type_logic(mtype: decl.ModuleType) -> tuple[str, ...]:
    """The §6.1 handshake over a simulated plant - a function of the TYPE alone.

    It takes no application and no module, and that is the point: this is the
    body of the library AOI, identical in every project that embeds the type.
    Everything that varies per instance arrives through the context at run
    time; everything the type owns - its reason codes - comes from the type.

    The timeout is carried in milliseconds and integrated from the instance's
    task period, and it does **not** accrue while held: a hold is the operator
    letting go, and a hold that matures into a timeout would report the machine
    as broken for the designed behaviour.
    """
    if mtype.type_key == library.DIGITAL_INPUT.type_key:
        return _digital_input_logic(mtype)
    if mtype.type_key == library.TWO_HAND.type_key:
        return _two_hand_logic(mtype)
    if mtype.type_key == library.AIR_PRESSURE.type_key:
        return _air_pressure_logic(mtype)
    import fraktal_ab_reasons as reasons

    held = mtype.reasons["INTERLOCK_DROPPED"]
    not_extended = mtype.reasons["CYL_NOT_EXTENDED"]
    not_retracted = mtype.reasons["CYL_NOT_RETRACTED"]
    cfg_invalid = mtype.reasons["CYL_CFG_INVALID"]

    def severity(name: str) -> int:
        """The registry's priority - TC3's F_RationalizeDiagnostic."""
        return reasons.rationalize(name, mtype.reasons[name]).priority
    # Which end sensor a timeout implicates, as TC3's FB_CylinderCM names it:
    # still short of a higher target, the extended end did not report.
    extended_fb = 1 << mtype.io_roles.index("extendedFb")
    retracted_fb = 1 << mtype.io_roles.index("retractedFb")
    lines: list[str] = [
        f"(* {mtype.type_key}: Core §6.1 handshake over a simulated plant. *)",
        "(* Generated from the declaration - never hand-edit. *)",
        "Ctx.ModuleScan := Scan;",
        # Guarded: the period is a value now, not a constant, and a divide by
        # zero is a controller fault. A zero period is refused below instead.
        "IF Ctx.Par_TaskPeriodMs > 0 THEN",
        "Ctx.Par_TimeoutScans := Ctx.Par_TimeoutMs / Ctx.Par_TaskPeriodMs;",
        "ELSE",
        "Ctx.Par_TimeoutScans := 0;",
        "END_IF;",
        "",
        *_execute_drop_reset("Ctx.ElapsedMs := 0;"),
        "",
        "(* Rising edge accepts the command and latches the request *)",
        "IF (Ctx.Execute <> 0) AND (Ctx.ExecutePrev = 0) THEN",
        "Ctx.ParCmd_Latched := Ctx.ParCmd_Target;",
        "Ctx.Busy := 1;",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.RunCount := Ctx.RunCount + 1;",
        "Ctx.ElapsedMs := 0;",
        "Ctx.TimMs := 0;",
        "END_IF;",
        "",
        "IF Ctx.Busy <> 0 THEN",
        "(* 8.11.4(a): a command's time runs from acceptance to its end, holds *)",
        "(* included - unlike ElapsedMs, which a hold must not time out. *)",
        f"IF Ctx.TimMs < {2_000_000_000} THEN",
        "Ctx.TimMs := Ctx.TimMs + Ctx.Par_TaskPeriodMs;",
        "END_IF;",
        "IF Ctx.Abort <> 0 THEN",
        "Ctx.Aborted := 1;",
        "Ctx.Busy := 0;",
        "Ctx.AbortCount := Ctx.AbortCount + 1;",
        f"Ctx.OutImm_ExecState := {STATE_ABORTED};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        # A module with no task period cannot time a command, so it must not
        # run one: it faults on its first busy scan rather than waiting forever
        # for a timeout that never accrues. Never a silent default (O10).
        "ELSIF Ctx.Par_TaskPeriodMs <= 0 THEN",
        "Ctx.Error := 1;",
        "Ctx.Busy := 0;",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        f"Ctx.ErrorID := {cfg_invalid};",
        f"Ctx.OutImm_Reason := {cfg_invalid};",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {severity('CYL_CFG_INVALID')};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "ELSIF (Ctx.HoldRequest <> 0) OR (Ctx.AreaSafe = 0) OR (Ctx.Permit = 0) THEN",
        "(* Held: BUSY, a LOW named reason, and no Error. The elapsed clock is *)",
        "(* deliberately NOT advanced here, so a held command never times out. *)",
        "Ctx.OutImm_Held := 1;",
        f"Ctx.OutImm_Reason := {held};",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.HeldScans := Ctx.HeldScans + 1;",
        "ELSE",
        "Ctx.OutImm_Held := 0;",
        "Ctx.OutImm_Reason := 0;",
        "Ctx.OutImm_IoRoles := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        "Ctx.ElapsedMs := Ctx.ElapsedMs + Ctx.Par_TaskPeriodMs;",
        # A simulated device fault is a cylinder that does not move - a stuck
        # valve or a jammed rod - and it is found the way a real one is: the
        # end sensor never reports, and the timeout names it.
        "IF Ctx.FaultRequest <> 0 THEN",
        "Ctx.FaultScans := Ctx.FaultScans + 1;",
        "ELSIF Ctx.OutImm_Pos < Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.OutImm_Pos + Ctx.Par_Speed;",
        "IF Ctx.OutImm_Pos > Ctx.ParCmd_Latched THEN Ctx.OutImm_Pos := Ctx.ParCmd_Latched; END_IF;",
        "ELSIF Ctx.OutImm_Pos > Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.OutImm_Pos - Ctx.Par_Speed;",
        "IF Ctx.OutImm_Pos < Ctx.ParCmd_Latched THEN Ctx.OutImm_Pos := Ctx.ParCmd_Latched; END_IF;",
        "END_IF;",
        "IF Ctx.OutImm_Pos = Ctx.ParCmd_Latched THEN",
        "Ctx.Done := 1;",
        "Ctx.Busy := 0;",
        "Ctx.DoneCount := Ctx.DoneCount + 1;",
        "Ctx.OutCmd_FinalPos := Ctx.OutImm_Pos;",
        "Ctx.OutCmd_Ok := 1;",
        f"Ctx.OutImm_ExecState := {STATE_DONE};",
        "ELSIF Ctx.ElapsedMs >= Ctx.Par_TimeoutMs THEN",
        "Ctx.Error := 1;",
        "Ctx.Busy := 0;",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        # TC3 names the end that did not report, by code and by sensor.
        "IF Ctx.ParCmd_Latched > Ctx.OutImm_Pos THEN",
        f"Ctx.ErrorID := {not_extended};",
        f"Ctx.OutImm_Reason := {not_extended};",
        f"Ctx.OutImm_IoRoles := {extended_fb};",
        f"Ctx.OutImm_Severity := {severity('CYL_NOT_EXTENDED')};",
        "ELSE",
        f"Ctx.ErrorID := {not_retracted};",
        f"Ctx.OutImm_Reason := {not_retracted};",
        f"Ctx.OutImm_IoRoles := {retracted_fb};",
        f"Ctx.OutImm_Severity := {severity('CYL_NOT_RETRACTED')};",
        "END_IF;",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "END_IF;",
        "END_IF;",
        "END_IF;",
        "",
        "(* The end sensors, from where the plant is: TC3's ExtendedFb and *)",
        "(* RetractedFb, read by the permits of the modules around this one. *)",
        f"IF Ctx.OutImm_Pos >= {library.CYLINDER_EXTENDED} THEN Ctx.OutImm_Extended := 1; "
        "ELSE Ctx.OutImm_Extended := 0; END_IF;",
        f"IF Ctx.OutImm_Pos <= {library.CYLINDER_RETRACTED} THEN Ctx.OutImm_Retracted := 1; "
        "ELSE Ctx.OutImm_Retracted := 0; END_IF;",
        *_command_timing_logic(),
        "Ctx.ExecutePrev := Ctx.Execute;",
    ]
    return tuple(lines)


def type_aoi(mtype: decl.ModuleType) -> str:
    """One library type's AOI definition - the same bytes in every application.

    Its RevisionNote describes the TYPE. It used to carry the instance's
    comment ("the press ram; EXTEND presses..."), which was the only other
    thing that made three cylinder definitions differ: instance documentation
    had leaked into a type.
    """
    ctx = module_context_name(mtype)
    return _aoi(
        type_aoi_name(mtype),
        f"Fraktal/AB library type {mtype.type_key}: {mtype.description}",
        ENABLE_PARAMETERS + (
            _parameter("Ctx", ctx, "InOut"),
            _parameter("Scan", "DINT", "Input", radix="Decimal"),
        ),
        type_logic(mtype),
        (ctx,),
    )


def module_aois(app: decl.Application) -> list[str]:
    """One AOI per library type the application uses, not one per instance."""
    return [type_aoi(mtype) for mtype in library.types_used(app)]


# --- chain logic ------------------------------------------------------------

def ordered_steps(app: decl.Application) -> list[int]:
    seen: list[int] = []
    for chain in app.chains:
        for step in chain.steps:
            if step.number not in seen:
                seen.append(step.number)
    return seen


class Names:
    """How a rendition refers to the things a step touches.

    Inside an Add-On Instruction everything is a parameter; inside a program
    routine everything is a controller-scoped tag. The step logic is identical
    either way, so the difference lives here rather than in every emitter - and
    that is what lets one declared graph be rendered in three languages without
    a second maintained source.
    """

    def __init__(self, app: decl.Application, *, in_aoi: bool):
        self.app = app
        self.in_aoi = in_aoi

    @property
    def unit(self) -> str:
        return "Ctx" if self.in_aoi else f"FRK_{self.app.name}_Unit"

    @property
    def chart(self) -> str:
        return "Chart" if self.in_aoi else f"FRK_{self.app.name}_Chart"

    @property
    def cfg(self) -> str:
        return "Cfg" if self.in_aoi else f"{self.app.records[0].name}Tag"

    @property
    def scan(self) -> str:
        return "Scan" if self.in_aoi else f"FRK_{self.app.name}_ScanCount"

    def module(self, name: str) -> str:
        return f"Ctx{name}" if self.in_aoi else ctx_tag_for(self.app, name)

    def sim(self, tag: str) -> str:
        return sim_param(self.app, tag) if self.in_aoi else tag

    def terms(self, condition) -> list[str]:
        """The operands a step condition needs non-zero: a simulated tag, or
        each named member of a module's context (decl.ModuleState)."""
        if isinstance(condition, decl.UnitState):
            known = {m.name for m in unit_context_members(self.app)}
            for member in condition.members:
                if member not in known:
                    raise decl.DeclarationError(
                        f"the Unit has no member {member!r} for a condition")
            return [f"{self.unit}.{m}" for m in condition.members]
        if not isinstance(condition, decl.ModuleState):
            return [self.sim(condition)]
        module = next(m for m in self.app.modules if m.name == condition.module)
        known = {m.name for m in module_members(module)}
        for member in condition.members + condition.zero:
            if member not in known:
                raise decl.DeclarationError(
                    f"{module.name} has no member {member!r} for a condition")
        return [f"{self.module(condition.module)}.{m}" for m in condition.members]

    def zeros(self, condition) -> list[str]:
        """The operands a module condition needs ZERO (decl.ModuleState.zero)."""
        if not isinstance(condition, decl.ModuleState):
            return []
        self.terms(condition)                       # validates every member
        return [f"{self.module(condition.module)}.{m}" for m in condition.zero]

    def policy(self, member: str) -> str:
        """A StationCfg policy flag (decl.RequiredBy). It is read from the
        station record's controller tag, so only a chain hosted in a program
        routine can see it - an AOI cannot reach controller scope."""
        station = station_cfg_record(self.app)
        if self.in_aoi or station is None:
            raise decl.DeclarationError(
                f"policy {member!r} lives in the StationCfg tag, which only a "
                f"chain in a program routine can read")
        return f"{station.name}Tag.{member}"


def cond_st(condition, names: Names) -> str:
    """One step condition as an ST Boolean: every member non-zero - or, for a
    policy-gated one (decl.RequiredBy), that OR its policy off, as TC3 writes
    `SafeActive OR NOT RequireTwoHandStart`. Every step kind, the start rule
    and the interlocks render a condition through here."""
    base = decl.condition_base(condition)
    holds = " AND ".join([f"({t} <> 0)" for t in names.terms(base)]
                         + [f"({z} = 0)" for z in names.zeros(base)])
    if isinstance(condition, decl.RequiredBy):
        return f"(({holds}) OR ({names.policy(condition.policy)} = 0))"
    return holds


def conds_st(conditions, names: Names) -> str:
    """All of `conditions`, as one ST Boolean; empty when there are none."""
    return " AND ".join(cond_st(c, names) for c in conditions)


def ld_holds(condition, names: Names) -> str:
    """The same condition in ladder: its contacts in series, or for a
    policy-gated one, a branch around them on the policy being off."""
    base = decl.condition_base(condition)
    series = "".join([f"NEQ({t},0)" for t in names.terms(base)]
                     + [f"EQU({z},0)" for z in names.zeros(base)])
    if isinstance(condition, decl.RequiredBy):
        return f"[{series},EQU({names.policy(condition.policy)},0)]"
    return series


def ld_fails(conditions, names: Names) -> str:
    """A ladder leg that is true when any of `conditions` does not hold."""
    legs: list[str] = []
    for condition in conditions:
        base = decl.condition_base(condition)
        fails = ([f"EQU({t},0)" for t in names.terms(base)]
                 + [f"NEQ({z},0)" for z in names.zeros(base)])
        if isinstance(condition, decl.RequiredBy):
            any_fail = fails[0] if len(fails) == 1 else f"[{','.join(fails)}]"
            legs.append(f"NEQ({names.policy(condition.policy)},0){any_fail}")
        else:
            legs += fails
    return legs[0] if len(legs) == 1 else f"[{','.join(legs)}]"



def _mark_step(app: decl.Application, index: int, names: Names) -> list[str]:
    """Enter the step: move the cursor, mark it visited, restart its clock."""
    if not names.in_aoi:
        return [f'IF {names.unit}.Step <> {names.unit}.PrevStep THEN',
                f'{names.chart}.StepCursor := {index};', 'END_IF;',
                f'JSR({step_mark_routine_name(app)},0);']
    return _mark_step_body(app, index, names)


def step_mark_routine_name(app: decl.Application) -> str:
    return f'FRK_{app.name}_SequenceMarkStep'


def step_mark_logic(app: decl.Application) -> list[str]:
    names = Names(app, in_aoi=False)
    return _mark_step_body(app, f'{names.chart}.StepCursor', names)


def _mark_step_body(app: decl.Application, index: int | str, names: Names) -> list[str]:
    """Same bookkeeping for AOI-inline steps and shared program services."""
    u, c = names.unit, names.chart
    return [
        f"IF {u}.Step <> {u}.PrevStep THEN",
        f"{c}.StepCursor := {index};",
        f"{c}.ActiveStepNumber := {u}.Step;",
        f"{c}.Visited[{index}] := 1;",
        f"{c}.EnterCount[{index}] := {c}.EnterCount[{index}] + 1;",
        f"{c}.CurrentStepMs := 0;",
        f"{u}.StepScan := {names.scan};",
        f"{u}.PrevStep := {u}.Step;",
        f"{c}.StallReason := 0;",
        f"IF {c}.RowEpochOf[{index}] <> {c}.RowEpoch THEN",
        f"{c}.RowEpochOf[{index}] := {c}.RowEpoch;",
        f"{c}.RowCount := {c}.RowCount + 1;",
        f"{c}.RowOf[{index}] := {c}.RowCount;",
        f"{c}.LastMs[{index}] := 0;",
        "END_IF;",
        f"{c}.WarnReason[{index}] := 0;",
        "END_IF;",
        f"{c}.CurrentStepMs := ({names.scan} - {u}.StepScan) * {app.task_period_ms};",
    ]


def _cond_ok(step: decl.Step, names: Names) -> list[str]:
    """Core §6.9(b), TC3's M_Await: each condition the step waits on, as the
    step sees it this scan. Written by the step itself, after it marks entry,
    so the published Ok and the ActiveStepNumber beside it are always one
    scan's view of one step. The transition still reads the tag directly: this
    records what it reads, and does not change what any rendition decides."""
    c = names.chart
    return [
        f"IF {cond_st(cond, names)} THEN {c}.CondOk[{i}] := 1; "
        f"ELSE {c}.CondOk[{i}] := 0; END_IF;"
        for i, (cond, _) in enumerate(decl.step_conditions(step))
    ]


def _delay_held(step: decl.Step, names: Names) -> str:
    """What a delay waits on while it runs, as one ST expression - empty for
    a plain delay, which has nothing to pause it."""
    return conds_st(step.conditions, names)


def _st_marks(step: decl.Step, names: Names) -> list[str]:
    """A step's marks, as ST statements.

    `Cfg.` as well as `Ctx.`: a changeover commit writes the configuration
    record, and that record is named differently depending on whether the
    chain is hosted inside the mode-owner AOI or in a program routine.
    """
    return [mark.replace("Ctx.", f"{names.unit}.")
            .replace("Cfg.", f"{names.cfg}.") + ";" for mark in step.marks]


def _ld_marks(step: decl.Step, names: Names) -> list[str]:
    """The same marks, as ladder outputs: an increment is an ADD, anything
    else a MOV."""
    u = names.unit
    outputs = []
    for mark in step.marks:
        target, expression = [part.strip() for part in mark.split(":=")]
        target = target.replace("Ctx.", f"{u}.")
        if "+" in expression:
            base = expression.split("+")[0].strip().replace("Ctx.", f"{u}.")
            outputs.append(f"ADD({base},1,{target})")
        else:
            outputs.append(f"MOV({expression.strip()},{target})")
    return outputs


def _st_warning(step: decl.Step, index: int, names: Names) -> list[str]:
    """TC3's M_RaiseWarning: a §6.9(e) message the chain handles itself.
    Published on the Unit and on the step's §3.13 row; the alarm log takes it
    as one AUTO_RESET occurrence. Source 0 is the Unit itself."""
    u, c, reason = names.unit, names.chart, step.report_reason
    return [
        f"{u}.ReportedReason := {reason};",
        f"{u}.ReportedSource := 0;",
        f"{u}.ReportedCount := {u}.ReportedCount + 1;",
        f"{c}.WarnReason[{index}] := {reason};",
        f"{c}.WarnSource[{index}] := 0;",
    ]


def _ld_warning(step: decl.Step, index: int, names: Names) -> str:
    u, c, reason = names.unit, names.chart, step.report_reason
    return _leg(
        f"MOV({reason},{u}.ReportedReason)",
        f"MOV(0,{u}.ReportedSource)",
        f"ADD({u}.ReportedCount,1,{u}.ReportedCount)",
        f"MOV({reason},{c}.WarnReason[{index}])",
        f"MOV(0,{c}.WarnSource[{index}])",
    )


def _delay_clock(app: decl.Application, step: decl.Step,
                 names: Names) -> list[str]:
    """TC3's M_Delay, and its N220 pause: the delay's own clock, zeroed on
    entry and advanced one task period on each later scan its conditions
    hold. Unpaused it equals CurrentStepMs, so a plain delay is this clock
    with nothing to wait for - one delay, not two. Paused it stands still,
    and pressing on finishes the remaining time rather than counting the
    pause as dwell."""
    u, c = names.unit, names.chart
    held = _delay_held(step, names)
    return [
        f"IF {names.scan} = {u}.StepScan THEN",
        f"{c}.DelayMs := 0;",
        f"ELSIF {held} THEN" if held else "ELSE",
        f"{c}.DelayMs := {c}.DelayMs + {app.task_period_ms};",
        "END_IF;",
    ]


def _ld_cond_ok(step: decl.Step, names: Names) -> list[str]:
    """The same record for a ladder rendition: one leg per truth value."""
    c = names.chart
    legs: list[str] = []
    for i, (cond, _) in enumerate(decl.step_conditions(step)):
        legs.append(_leg(ld_holds(cond, names), f"MOV(1,{c}.CondOk[{i}])"))
        legs.append(_leg(ld_fails((cond,), names), f"MOV(0,{c}.CondOk[{i}])"))
    return legs


def module_source(app: decl.Application, name: str) -> int:
    """A module's number in ErrorSource/ReportedSource: its 1-based position
    among the declared modules (0 is the Unit itself)."""
    return [m.name for m in app.modules].index(name) + 1


def _advance(app: decl.Application, step: decl.Step, index: int,
             names: Names) -> list[str]:
    return [
        f"{names.chart}.LastMs[{index}] := {names.chart}.CurrentStepMs;",
        f"{names.unit}.Step := {step.on_advance};",
    ]



def pacing(app: decl.Application) -> bool:
    """Whether the application paces its sequences (TC3 §3.4.2): any run
    style beyond CONTINUOUS. Without it nothing below is emitted."""
    return any(s != decl.RUN_CONTINUOUS for s in app.run_styles)


def _paced_st(app: decl.Application, step: decl.Step, names: "Names",
              issue: list[str]) -> list[str]:
    """TC3's M_TryIssue: a steppable command issues only once the run style
    permits it, then stays issued for the rest of the visit. The Unit's
    StepPermit is CONTINUOUS's always, SINGLE_STEP's pending Step request,
    HOLD_TO_RUN's held button; issuing consumes a pending Step request."""
    if not pacing(app) or not step.steppable:
        return issue
    u = names.unit
    return [f"IF ({u}.Issued = 0) AND ({u}.StepPermit <> 0) THEN",
            f"{u}.Issued := 1;",
            f"{u}.StepPending := 0;",
            "END_IF;",
            f"IF {u}.Issued <> 0 THEN", *issue, "END_IF;"]


def _entry_reset(ctx: str, names: "Names",
                 app: decl.Application | None = None) -> list[str]:
    """Drop Execute on the step's own entry scan, then command from the next.

    This is Core §6.1's Execute-drop reset used as the generator intends it: a
    module clears Done/Error/Aborted only when its Execute falls, so a step that
    asserted Execute unconditionally could never release a child that had
    already terminated - the child would stay faulted and every later step
    aiming at it would stall forever. Dropping on entry also guarantees the
    rising edge the module latches its request on.
    """
    return [
        f"IF {names.scan} = {names.unit}.StepScan THEN",
        f"{ctx}.Execute := 0;",
        *([f"{names.unit}.Issued := 0;"] if app is not None and pacing(app) else []),
        "ELSE",
    ]


def _module_ref(app: decl.Application, name: str) -> str:
    """Inside the mode owner a child context is a parameter, not a tag.

    An Add-On Instruction may only reference its own parameters and local tags;
    reaching a controller-scoped tag from inside one does not compile. Every
    child context is therefore passed in as an InOut, which is also the honest
    shape: the owner is handed what it may touch.
    """
    return f"Ctx{name}"


def sim_param(app: decl.Application, tag: str) -> str:
    """The AOI parameter that carries a declared simulated input."""
    prefix = f"FRK_{app.name}_"
    return "In" + (tag[len(prefix):] if tag.startswith(prefix) else tag)


def ctx_tag_for(app: decl.Application, module_name: str) -> str:
    return f"FRK_{app.name}_Ctx{module_name}"


def injection_tag(app: decl.Application, module: decl.Module, injection: str) -> str:
    """The stimulus tag feeding one instance's `<injection>Request`."""
    return f"FRK_{app.name}_{injection}{module.name}"


def force_tags(app: decl.Application) -> tuple[str, ...]:
    """The §10.5.1 force words, or nothing when the application has no I/O."""
    if not app.io_modules:
        return ()
    stem = f"FRK_{app.name}_Force"
    return (f"{stem}Mask", f"{stem}Value", f"{stem}Permitted", f"{stem}Outputs")


def force_output_mask(app: decl.Application) -> int:
    """Every output bit this application actually has, as one DINT.

    The handler ANDs a request against this, so a force aimed at a bit the
    chassis does not carry - or at an input - is refused rather than held on a
    channel nobody named.
    """
    mask = 0
    for module in app.io_modules:
        for channel in module.channels:
            if channel.direction == decl.DIR_OUTPUT:
                mask |= 1 << channel.bit
    return mask


def force_logic(app: decl.Application) -> list[str]:
    """Publish whether forcing is permitted, apply the held bits, withdraw.

    §10.5.1's rule is that a force must never outlive the condition that
    allowed it. The withdrawal is therefore unconditional and runs BEFORE the
    apply: the moment the permission goes away the words are cleared, so no
    scan can write a held bit that was granted under a condition that has
    already passed. TC3 spells the same rule `M_ApplyForces(Enabled :=
    M_ForcePermitted())`, withdrawing on the falling edge.

    Idle MANUAL is the condition, which is TC3's too. AUTO is excluded because
    a forced output under a running sequence is a machine fighting itself.
    """
    if not app.io_modules:
        return []
    n = app.name
    module = app.io_modules[0]
    manual = app.manual_mode
    if manual is None:
        return []
    return [
        "(* Core 10.5.1 output forcing. *)",
        f"FRK_{n}_ForceOutputs := {force_output_mask(app)};",
        f"IF (FRK_{n}_Unit.Mode = {manual}) AND (FRK_{n}_Unit.Running = 0) "
        f"AND (FRK_{n}_Unit.Error = 0) THEN",
        f"FRK_{n}_ForcePermitted := 1;",
        "ELSE",
        f"FRK_{n}_ForcePermitted := 0;",
        "END_IF;",
        "",
        "(* Withdraw first. A force outliving its permission by even one scan",
        "   is the whole defect this ordering prevents. *)",
        f"IF FRK_{n}_ForcePermitted = 0 THEN",
        f"FRK_{n}_ForceMask := 0;",
        f"FRK_{n}_ForceValue := 0;",
        "END_IF;",
        "",
        "(* The press logic does not drive the cabinet yet, so the computed",
        "   value of every output is zero and a withdrawn force returns the",
        "   terminal to zero with it. When the modules are wired this becomes",
        "   (computed AND NOT Mask) OR (Value AND Mask). *)",
        f"{module.address}:O.Data := FRK_{n}_ForceValue AND FRK_{n}_ForceMask;",
    ]


def step_logic(app: decl.Application, chain: decl.Chain, step: decl.Step,
               index: int, names: Names | None = None) -> list[str]:
    """Emit one step's body. Every branch marks the chart before it decides."""
    names = names or Names(app, in_aoi=True)
    u, c = names.unit, names.chart
    lines: list[str] = [f"{step.number}:", f"(* {step.name}: {step.comment} *)"]
    lines += _mark_step(app, index, names)
    lines += _cond_ok(step, names)
    adv = _advance(app, step, index, names)

    def commanded(action_name: str) -> tuple[str, list[str]]:
        module = next(m for m in app.modules if m.name == action_name)
        command = next(cm for cm in module.commands if cm.name == step.command)
        ctx = names.module(step.module)
        return ctx, _paced_st(app, step, names, [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
        ])

    if step.action == decl.ISSUE:
        ctx, issue = commanded(step.module)
        lines += _entry_reset(ctx, names, app) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + _st_marks(step, names) + adv + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            f"{c}.StallReason := {ctx}.ErrorID;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.GUARDED:
        # TC3's N180: a command that is wanted only while its guard holds.
        # Completion wins if both happen in one scan; a guard lost first is
        # the operator abandoning the command - a warning, not a fault - and
        # the chain takes its recovery jump.
        ctx, issue = commanded(step.module)
        lines += _entry_reset(ctx, names, app) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + _st_marks(step, names) + adv + [
            f"ELSIF NOT ({conds_st(step.conditions, names)}) THEN",
            f"{ctx}.Execute := 0;",
            *_st_warning(step, index, names),
            f"{c}.LastMs[{index}] := {c}.CurrentStepMs;",
            f"{u}.Step := {step.on_jump};",
            f"ELSIF {ctx}.Error <> 0 THEN",
            f"{c}.StallReason := {ctx}.ErrorID;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.ADOPT:
        # An awaited child: its first-out is adopted verbatim and the chain stops
        # on this step. This is the rollup - the parent does not invent a reason.
        ctx, issue = commanded(step.module)
        source = module_source(app, step.module)
        lines += _entry_reset(ctx, names, app) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + adv + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            "(* Adopt the child's first-out verbatim: same reason, no translation *)",
            f"{u}.Error := 1;",
            f"{u}.ErrorID := {ctx}.ErrorID;",
            f"{u}.ErrorSource := {source};",
            f"{c}.StallReason := {ctx}.ErrorID;",
            f"{u}.Running := 0;",
            "(* Release the child: adopting its fault must not also pin it in *)",
            "(* the faulted state, or nothing could ever clear it. *)",
            f"{ctx}.Execute := 0;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.REPORT:
        # Reported, NOT adopted: a message. The chain owns the recovery below, so
        # adopting here would replace a designed recovery with a stop.
        ctx, issue = commanded(step.module)
        lines += _entry_reset(ctx, names, app) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + adv + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            "(* Report the child's own first-out; do NOT adopt it *)",
            f"{u}.ReportedReason := {ctx}.ErrorID;",
            f"{u}.ReportedSource := {module_source(app, step.module)};",
            f"{u}.ReportedCount := {u}.ReportedCount + 1;",
            f"{c}.WarnReason[{index}] := {ctx}.ErrorID;",
            f"{c}.WarnSource[{index}] := {module_source(app, step.module)};",
            f"{ctx}.Execute := 0;",
            f"{c}.LastMs[{index}] := {c}.CurrentStepMs;",
            f"{u}.Step := {step.on_jump};",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.DELAY:
        held = _delay_held(step, names)
        due = f"{c}.DelayMs >= {names.cfg}.{step.duration_member}"
        # WAIT_CONDITION is looked up only where a condition can pause the
        # delay: reasons.validate requires it of no other DELAY step.
        lines += _delay_clock(app, step, names) + (
            [f"IF NOT ({held}) THEN",
             f"{c}.StallReason := {step.hold_reason or app.reasons['WAIT_CONDITION']};",
             f"ELSIF {due} THEN"] if held else [f"IF {due} THEN"]
        ) + adv + [
            "ELSE",
            f"{c}.StallReason := {app.reasons['WAIT_DELAY']};",
            "END_IF;",
        ]

    elif step.action == decl.AWAIT:
        condition = conds_st(step.conditions, names) or "(1 = 1)"
        lines += [f"IF {condition} THEN"] + adv + [
            "ELSE",
            f"{c}.StallReason := "
            f"{step.hold_reason or app.reasons['WAIT_CONDITION']};",
            "END_IF;",
        ]

    elif step.action == decl.DECISION:
        # A decision the chain waits on without faulting. A scrap is deliberate,
        # so there is no timeout default (Core 6.11).
        lines += [
            f"{u}.DecisionId := {step.decision_id};",
            f"IF {u}.DecisionAnswer <> 0 THEN",
            f"{u}.DecisionCount := {u}.DecisionCount + 1;",
            f"IF {u}.DecisionAnswer = 1 THEN",
        ] + adv + [
            "ELSE",
            f"{c}.LastMs[{index}] := {c}.CurrentStepMs;",
            f"{u}.Step := {step.on_jump};",
            "END_IF;",
            f"{u}.DecisionId := 0;",
            f"{u}.DecisionAnswer := 0;",
            "ELSE",
            f"{c}.StallReason := {app.reasons['WAIT_DECISION']};",
            "END_IF;",
        ]

    elif step.action == decl.MARK:
        lines += _st_marks(step, names) + adv

    elif step.action == decl.COMPLETE:
        lines += [
            f"{u}.Complete := 1;",
            f"{u}.Running := 0;",
            f"{c}.StallReason := 0;",
        ]
        if step.on_advance != -1:
            lines += adv

    return [line for line in lines if line != ""]



def unit_logic(app: decl.Application) -> tuple[str, ...]:
    steps_order = ordered_steps(app)
    lines: list[str] = [
        f"(* {app.name} mode owner. Generated - never hand-edit. *)",
        "(* Ordering is self-checked: every child module must already have run *)",
        "(* this scan. S11 proved the rule for sequences, S16 for commands, and *)",
        "(* a generator that could not detect its own violation would be relying *)",
        "(* on the author having got the call order right. *)",
    ]
    latch_clear = ["Ctx.StartLatched := 0;"] if app.start_control else []
    # TC3's OperatorReset and mode change release every command the operator
    # left behind: a manual command still running is dropped, not resumed.
    manual_release = [
        line for module in app.modules if module.commands for line in (
            f"IF {_module_ref(app, module.name)}.ManualCmd <> 0 THEN",
            f"{_module_ref(app, module.name)}.Execute := 0;",
            f"{_module_ref(app, module.name)}.ManualCmd := 0;",
            "END_IF;")
    ] if app.manual_mode is not None else []
    for module in app.modules:
        ctx = _module_ref(app, module.name)
        lines += [
            f"IF {ctx}.ModuleScan <> Scan THEN",
            "Ctx.OrderFail := Ctx.OrderFail + 1;",
            "END_IF;",
        ]
    lines += [
        "",
        "(* A mode change stands the chain down; it never resumes by itself *)",
        "IF Ctx.ModeRequest <> Ctx.Mode THEN",
        "Ctx.ModeSwitches := Ctx.ModeSwitches + 1;",
        "Ctx.Mode := Ctx.ModeRequest;",
        "Ctx.Step := 0;",
        "Ctx.PrevStep := -1;",
        "Ctx.Running := 0;",
        "Ctx.Complete := 0;",
        "Chart.StallReason := 0;",
        "(* Core 3.13: each mode builds its own chart (TC3 OnModeChanged) *)",
        "Chart.RowEpoch := Chart.RowEpoch + 1;",
        "Chart.RowCount := 0;",
        *latch_clear,
        *manual_release,
        "END_IF;",
        "",
        "IF Ctx.ResetRequest <> 0 THEN",
        "Ctx.Step := 0;",
        "Ctx.PrevStep := -1;",
        "Ctx.Error := 0;",
        "Ctx.ErrorID := 0;",
        "Ctx.ErrorSource := 0;",
        "Ctx.Aborted := 0;",
        "Ctx.Complete := 0;",
        "Ctx.Running := 0;",
        *latch_clear,
        *manual_release,
        "END_IF;",
        "",
        "IF Ctx.AbortRequest <> 0 THEN",
        "Ctx.Aborted := 1;",
        "Ctx.Running := 0;",
        "Ctx.Step := 0;",
        "Ctx.PrevStep := -1;",
        *latch_clear,
        *manual_release,
        "END_IF;",
        "",
        "(* A completed chain stays completed. Without the Complete guard the *)",
        "(* latch would re-arm the scan after a COMPLETE step stood the chain *)",
        "(* down, and Running would oscillate for as long as the run request  *)",
        "(* was held - a reader would see a different answer every scan.      *)",
        "IF (Ctx.RunRequest <> 0) AND (Ctx.Error = 0) AND (Ctx.Aborted = 0)",
        "AND (Ctx.Complete = 0) THEN",
        "Ctx.Running := 1;",
        "END_IF;",
        "IF Ctx.RunRequest = 0 THEN",
        "Ctx.Running := 0;",
        "END_IF;",
        *start_latch_logic(app),
        "",
        "(* Lower the pending decision before the chain runs, so only a step *)",
        "(* that is ACTIVE this scan re-raises it. A DECISION step sets      *)",
        "(* DecisionId and nothing else ever cleared it, so the id outlived  *)",
        "(* the step - a chain that had answered and moved on, or been stood *)",
        "(* down entirely, still published a question, and the operator was  *)",
        "(* shown a prompt for a decision that no longer existed. Same shape *)",
        "(* as the mailbox latch: raised on one path, lowered on none.       *)",
        "Ctx.DecisionId := 0;",
        *manual_logic(app),
        *run_style_logic(app),
        "",
        "IF Ctx.Running <> 0 THEN",
    ]
    for chain in app.chains:
        if chain.program_hosted:
            # Hosted in program routines instead: this AOI's routine is ST, and
            # an AOI cannot contain an SFC routine. The owner still owns the
            # latches and the ordering check for it.
            lines.append(f"(* {chain.name}: rendered in "
                         f"{', '.join(chain.renditions)} as program routines *)")
            continue
        lines.append(f"IF Ctx.Mode = {chain.mode_ordinal} THEN")
        lines.append(f"Chart.ActiveChain := {chain.mode_ordinal};")
        lines.append("CASE Ctx.Step OF")
        for step in chain.steps:
            index = steps_order.index(step.number)
            lines += step_logic(app, chain, step, index)
        lines += [
            "ELSE",
            MARKER_CASE_ELSE,
            f"Chart.StallReason := {app.reasons['STEP_STALLED']};",
            "Ctx.Step := 0;",
            "END_CASE;",
            "END_IF;",
        ]
    lines += ["END_IF;"]
    return tuple(lines)


def start_predicate(app: decl.Application) -> str:
    """Whether the Unit may start now, as ST over controller tags - the ONE
    start rule, read by an operator's START and by a physical start alike:
    the release report the routine computes every scan (start_release_logic),
    so the rule and the explanation an operator is shown are one result."""
    return f"({start_release_tag(app)}.Released <> 0)"


# Core E_ReleaseKind, pinned to the TwinCAT DUT by test: what the HMI groups a
# reason under and draws its icon from.
RELEASE_KINDS = {"MODE": 0, "ACCESS": 1, "ALARM": 2, "INTERLOCK": 3, "OTHER": 4}
# Reasons one report holds. TC3's ST_ReleaseReport holds 24; this binding can
# produce at most a handful - the Unit's three, the start permits, and the four
# a manual command can meet - so it carries what it can fill. The HMI reads
# Count, and the projection publishes TC3's 24 slots, empty past Count.
RELEASE_CAPACITY = 8
# The release texts the controller writes, TC3's own keys.
UNIT_NOT_READY_KEY = "std.release.unitNotReady"
MANUAL_RESET_KEY = "std.release.manualReset"
NO_BLOCKING_ALARM_KEY = "std.release.noBlockingAlarm"
# TC3's text while its live documents are read back (FB_UnitBase §163).
CONFIG_RESTORING_KEY = "std.release.configRestoring"
GATED_ALARM_RESET = 7                       # Core E_GatedAction.ALARM_RESET


def release_report_members() -> tuple[decl.Member, ...]:
    """TC3's ST_ReleaseReport in DINTs: each reason as its numeric text key,
    its reason code, the module that owns it (0 is the Unit, n the n-th
    declared module) and its E_ReleaseKind."""
    n = RELEASE_CAPACITY
    return (
        decl.boolean("Released", "nothing blocks: Count = 0"),
        decl.scalar("Count", "reasons listed"),
        decl.scalar("Key", "numeric localization key of each reason", dimension=n),
        decl.reason("Reason", "each reason's code", dimension=n),
        decl.scalar("Source", "who owns it: 0 the Unit, n the n-th module", dimension=n),
        decl.scalar("Kind", "Core E_ReleaseKind", dimension=n),
    )


def release_report_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}ReleaseReport"


def start_release_tag(app: decl.Application) -> str:
    """Why START would be refused right now - computed every scan."""
    return f"FRK_{app.name}_StartRelease"


def release_report_tag(app: decl.Application) -> str:
    """The report the mailbox answers with - TC3's HmiResponse.Report."""
    return f"FRK_{app.name}_ReleaseReport"


def release_index_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_ReleaseIndex"


def report_open(tag: str) -> list[str]:
    return [f"{tag}.Count := 0;", f"{tag}.Released := 0;"]


def report_add(tag: str, key: int, reason: int, source: int, kind: str,
               portable: str = "") -> list[str]:
    """One reason, appended while the report has room - TC3's _M_AddReason."""
    note = f" (* {portable} *)" if portable else ""
    return [f"IF {tag}.Count < {RELEASE_CAPACITY} THEN",
            f"{tag}.Key[{tag}.Count] := {key};{note}",
            f"{tag}.Reason[{tag}.Count] := {reason};",
            f"{tag}.Source[{tag}.Count] := {source};",
            f"{tag}.Kind[{tag}.Count] := {RELEASE_KINDS[kind]};",
            f"{tag}.Count := {tag}.Count + 1;",
            "END_IF;"]


def report_close(tag: str) -> list[str]:
    return [f"IF {tag}.Count = 0 THEN {tag}.Released := 1; "
            f"ELSE {tag}.Released := 0; END_IF;"]


def report_copy(app: decl.Application, source: str, target: str) -> list[str]:
    i = release_index_tag(app)
    return [f"{target}.Released := {source}.Released;",
            f"{target}.Count := {source}.Count;",
            f"FOR {i} := 0 TO {RELEASE_CAPACITY - 1} DO",
            *(f"{target}.{m}[{i}] := {source}.{m}[{i}];"
              for m in ("Key", "Reason", "Source", "Kind")),
            "END_FOR;"]


def release_keys(app: decl.Application) -> tuple[str, ...]:
    """Every text a release report can carry, for the manifest to intern."""
    keys = [UNIT_NOT_READY_KEY, MANUAL_RESET_KEY, NO_BLOCKING_ALARM_KEY]
    if decl.live_documents(app):
        keys.append(CONFIG_RESTORING_KEY)
    keys += [p.key for p in app.start_permits]
    return tuple(keys)


def config_restoring(app: decl.Application) -> str:
    """Core 3.8b, derived and never latched: the controller started on an image
    it did not keep and the gateway's live documents have not answered yet.

    The first-scan gate leaves the station image at version zero (never
    written) instead of stamping it, and the restore's final station load
    stamps it. Until then Start names the restore and configuration writes
    are refused, as TC3's _M_ConfigRestored does: the restore would replay
    over them. Only meaningful when the declaration keeps live documents."""
    record = station_cfg_record(app)
    return f"({record.name}Tag.{decl.SCHEMA_VERSION_MEMBER} = 0)"


def start_release_routine_name(app: decl.Application) -> str:
    return f'FRK_{app.name}_ReleaseStart'


def start_release_call(app: decl.Application) -> list[str]:
    return [f'JSR({start_release_routine_name(app)},0);']


def start_release_logic(app: decl.Application) -> list[str]:
    """TC3's ReleaseReportStart, every scan: why START would be refused right
    now. START, a physical start and the HMI's report all read this one
    result, so the rule and its explanation cannot drift (Core §7.8)."""
    keys = localization_numbers(app)
    names = Names(app, in_aoi=False)
    tag, u = start_release_tag(app), f"FRK_{app.name}_Unit"
    lines = ["", "(* Core 7.8: why START would be refused right now (TC3's *)",
             "(* ReleaseReportStart), the one rule a START and a physical start read *)",
             *report_open(tag)]
    if app.access_users is not None:
        import fraktal_ab_access as access
        lines += access.report(app, tag, '5')
    if app.manual_mode is not None:
        lines += [f"IF {u}.Mode = {app.manual_mode} THEN",
                  *report_add(tag, keys[mailbox.MANUAL_HAS_NO_SEQUENCE_KEY], 0, 0,
                              "MODE", mailbox.MANUAL_HAS_NO_SEQUENCE_KEY),
                  "END_IF;"]
    lines += [f"IF ({u}.Running <> 0) OR ({u}.Error <> 0) OR ({u}.Complete <> 0) "
              f"OR ({u}.Aborted <> 0) THEN",
              *report_add(tag, keys[UNIT_NOT_READY_KEY], 0, 0, "MODE",
                          UNIT_NOT_READY_KEY),
              "END_IF;",
              f"IF {alarm_active_tag(app)}.Blocking <> 0 THEN",
              *report_add(tag, keys[MANUAL_RESET_KEY], 0, 0, "ALARM", MANUAL_RESET_KEY),
              "END_IF;"]
    if decl.live_documents(app):
        lines += [f"IF {config_restoring(app)} THEN",
                  *report_add(tag, keys[CONFIG_RESTORING_KEY], 0, 0, "OTHER",
                              CONFIG_RESTORING_KEY),
                  "END_IF;"]
    for permit in app.start_permits:
        scope = " OR ".join(f"({u}.Mode = {m})" for m in permit.modes)
        guard = f"({scope}) AND " if scope else ""
        lines += [f"IF {guard}NOT ({conds_st(permit.conditions, names)}) THEN",
                  *report_add(tag, keys[permit.key], app.reasons["PERMISSIVE_NOT_MET"],
                              0, "INTERLOCK", permit.key),
                  "END_IF;"]
    return lines + report_close(tag)


def run_style_logic(app: decl.Application) -> list[str]:
    """TC3's _M_StepGate, once per scan before any chain runs: whether a
    steppable command may issue now. NON-SAFETY pacing - the modules'
    interlocks still decide whether anything moves.

    A Unit that is not running holds no Step request and no hold. The mailbox
    takes either only while it runs, so a stop, a fault, a reset, an abort and
    a mode change all end them here, in one place: the operator asks again,
    and a hold whose release never arrived (a dropped HMI link) cannot carry
    into the next START. TC3 keeps both across a stop; this is the stricter
    reading of its own rule that a hold cannot stick."""
    if not pacing(app):
        return []
    return ["", "(* Core 3.4.2: run-style pacing (TC3 _M_StepGate). NON-SAFETY. *)",
            "IF Ctx.Running = 0 THEN",
            "Ctx.StepPending := 0;",
            "Ctx.HoldRun := 0;",
            "END_IF;",
            f"IF Ctx.RunStyle = {decl.RUN_SINGLE_STEP} THEN",
            "Ctx.StepPermit := Ctx.StepPending;",
            f"ELSIF Ctx.RunStyle = {decl.RUN_HOLD_TO_RUN} THEN",
            "Ctx.StepPermit := Ctx.HoldRun;",
            "ELSE",
            "Ctx.StepPermit := 1;",
            "END_IF;"]


def manual_logic(app: decl.Application) -> list[str]:
    """TC3's ManualCommand (§7.6.1), in the mode with no sequence: the
    command the mailbox accepted runs through the module's own handshake and
    interlocks - a blocked direction holds it, exactly as in AUTO - and
    Execute drops once it is done. A command that faults keeps Execute up, so
    the module stays in ERROR where the operator can see it, until the next
    manual command, a reset or a mode change releases it."""
    if app.manual_mode is None:
        return []
    lines = ["", "(* Core 7.6.1: manual commands, in the mode with no sequence *)",
             f"IF Ctx.Mode = {app.manual_mode} THEN"]
    for module in app.modules:
        if not module.commands:
            continue
        m = _module_ref(app, module.name)
        lines += [
            f"IF {m}.ManualCmd <> 0 THEN",
            f"IF ({m}.Done <> 0) OR ({m}.Aborted <> 0) THEN",
            f"{m}.Execute := 0;",
            f"{m}.ManualCmd := 0;",
            f"ELSIF {m}.Error = 0 THEN",
            f"{m}.ParCmd_Command := {m}.ManualCmd;",
            *[f"{'IF' if i == 0 else 'ELSIF'} {m}.ManualCmd = {c.ordinal} THEN "
              f"{m}.ParCmd_Target := {c.target_position};"
              for i, c in enumerate(module.commands)],
            "END_IF;",
            f"{m}.Execute := 1;",
            "END_IF;",
            "END_IF;",
        ]
    return lines + ["END_IF;"]


def start_latch_logic(app: decl.Application) -> list[str]:
    """TC3's press: a start pulse latches the start - with what it requires."""
    control = app.start_control
    if control is None:
        return []
    names = Names(app, in_aoi=True)
    pulse = cond_st(control.pulse, names)
    requires = "".join(f" AND {cond_st(c, names)}" for c in control.requires)
    return [
        "",
        "(* A start pulse latches the start the start step waits on - but only *)",
        "(* with what it requires already present, so a press made before the *)",
        "(* part was loaded never starts the stroke when the part arrives.     *)",
        f"IF {pulse} THEN",
        f"IF (Ctx.Mode = {control.mode}) AND (Ctx.Running <> 0){requires} THEN",
        "Ctx.StartLatched := 1;",
        "ELSE",
        "Ctx.StartLatched := 0;",
        "END_IF;",
        "END_IF;",
    ]


def physical_start_logic(app: decl.Application) -> list[str]:
    """TC3's press: a start pulse starts the start mode from ready, through
    the same predicate an operator START uses (start_predicate)."""
    control = app.start_control
    if control is None:
        return []
    names = Names(app, in_aoi=False)
    u = f"FRK_{app.name}_Unit"
    pulse = cond_st(control.pulse, names)
    return [
        "",
        "(* A physical start starts the chain from ready, by START's own rule *)",
        f"IF {pulse} AND ({u}.Mode = {control.mode}) AND ({u}.Running = 0) "
        f"AND {start_predicate(app)} THEN",
        f"FRK_{app.name}_RunRequest := 1;",
        "END_IF;",
    ]


def unit_parameters(app: decl.Application) -> tuple[str, ...]:
    """InOuts first, then Inputs - the order the ST call site passes them in."""
    params = [
        _parameter("Ctx", unit_context_name(app), "InOut"),
        _parameter("Chart", chart_name(app), "InOut"),
        _parameter("Cfg", app.records[0].name, "InOut"),
    ]
    for module in app.modules:
        params.append(_parameter(_module_ref(app, module.name),
                                 module_context_name(library.type_of(module)),
                                 "InOut"))
    params.append(_parameter("Scan", "DINT", "Input", radix="Decimal"))
    for tag in app.sim_inputs:
        params.append(_parameter(sim_param(app, tag), "DINT", "Input",
                                 radix="Decimal"))
    return tuple(params)


def chain_routine_name(app: decl.Application, chain: decl.Chain,
                       rendition: str) -> str:
    return f"FRK_{app.name}{chain.name.title()}{rendition.title()}"


def sfc_runner_name(app: decl.Application, chain: decl.Chain) -> str:
    return f"FRK_{app.name}{chain.name.title()}SfcRun"


def chain_st_logic(app: decl.Application, chain: decl.Chain) -> tuple[str, ...]:
    """The ST rendition of a multi-rendition chain, as a program routine.

    Byte for byte the same step bodies the AOI would have carried; only the
    names differ, because a program routine reaches controller tags directly.
    """
    names = Names(app, in_aoi=False)
    steps_order = ordered_steps(app)
    u = names.unit
    lines = [
        f"(* {chain.name} - ST rendition. Generated from the declared graph. *)",
        f"{names.chart}.ActiveChain := {chain.mode_ordinal};",
        f"CASE {u}.Step OF",
    ]
    for step in chain.steps:
        lines += step_logic(app, chain, step, steps_order.index(step.number), names)
    lines += [
        "ELSE",
        MARKER_CASE_ELSE,
        f"{names.chart}.StallReason := {app.reasons['STEP_STALLED']};",
        f"{u}.Step := 0;",
        "END_CASE;",
    ]
    return tuple(lines)


# --- the ladder rendition ---------------------------------------------------
#
# An RLL integer state machine: one rung per declared step, gated on
# EQU(Step,N). Two rules make it walk the same trace as ST and SFC:
#
# * **One step per scan.** Rung order is execution order, so a forward
#   transition would otherwise fall straight into the next step's rung in the
#   same scan and run a whole chain in a single pass. Every transition sets an
#   advanced flag and every rung's rung-in requires it clear - the same
#   ordering rule the TwinCAT binding enforces for its ladder rendition.
# * **Rungs ascend by step number**, asserted by the emitter, so the text reads
#   in the order it executes.
#
# No instruction's result is fed into another instruction's condition inside a
# rung; where a value must be computed first it goes to a named scratch tag.

def ld_advanced_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_LdAdvanced"


def ld_scratch_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_LdScratch"


def _leg(*parts: str) -> str:
    return "".join(p for p in parts if p)


def _ld_entry_marking(app: decl.Application, index: int, names: Names) -> str:
    u, c = names.unit, names.chart
    return _leg(
        f"NEQ({u}.Step,{u}.PrevStep)",
        f"MOV({index},{c}.StepCursor)",
        f"MOV({u}.Step,{c}.ActiveStepNumber)",
        f"MOV(1,{c}.Visited[{index}])",
        f"ADD({c}.EnterCount[{index}],1,{c}.EnterCount[{index}])",
        f"MOV(0,{c}.CurrentStepMs)",
        f"MOV({names.scan},{u}.StepScan)",
        f"MOV({u}.Step,{u}.PrevStep)",
        f"MOV(0,{c}.StallReason)",
        # discover the row this mode session; every visit starts clean
        f"[NEQ({c}.RowEpochOf[{index}],{c}.RowEpoch)"
        f"MOV({c}.RowEpoch,{c}.RowEpochOf[{index}])"
        f"ADD({c}.RowCount,1,{c}.RowCount)"
        f"MOV({c}.RowCount,{c}.RowOf[{index}])"
        f"MOV(0,{c}.LastMs[{index}]),"
        f"MOV(0,{c}.WarnReason[{index}])]",
    )


def _ld_advance(app: decl.Application, step: decl.Step, index: int,
                names: Names, target: int) -> str:
    return _leg(
        f"MOV({names.chart}.CurrentStepMs,{names.chart}.LastMs[{index}])",
        f"MOV({target},{names.unit}.Step)",
        f"MOV(1,{ld_advanced_tag(app)})",
    )


def ld_step_rung(app: decl.Application, chain: decl.Chain, step: decl.Step,
                 index: int, names: Names) -> str:
    """One rung for one step; the legs below are branch legs of that rung."""
    u, c = names.unit, names.chart
    adv = ld_advanced_tag(app)
    legs: list[str] = [_ld_entry_marking(app, index, names)]
    legs += _ld_cond_ok(step, names)
    entered = f"NEQ({names.scan},{u}.StepScan)"
    fresh = f"EQU({names.scan},{u}.StepScan)"

    def commanded(mod: str):
        module = next(m for m in app.modules if m.name == mod)
        command = next(cm for cm in module.commands if cm.name == step.command)
        ctx = names.module(mod)
        return ctx, _leg(
            f"MOV({command.ordinal},{ctx}.ParCmd_Command)",
            f"MOV({command.target_position},{ctx}.ParCmd_Target)",
            f"MOV(1,{ctx}.Execute)",
        )

    if step.action in (decl.ISSUE, decl.GUARDED, decl.ADOPT, decl.REPORT):
        ctx, issue = commanded(step.module)
        paced = pacing(app) and step.steppable
        legs.append(_leg(fresh, f"MOV(0,{ctx}.Execute)",
                         f"MOV(0,{u}.Issued)" if pacing(app) else ""))
        if paced:
            # TC3's M_TryIssue: issue once the run style permits, then latch.
            legs.append(_leg(entered, f"EQU({u}.Issued,0)", f"NEQ({u}.StepPermit,0)",
                             f"MOV(1,{u}.Issued)", f"MOV(0,{u}.StepPending)"))
            legs.append(_leg(entered, f"NEQ({u}.Issued,0)", issue))
        else:
            legs.append(_leg(entered, issue))
        legs.append(_leg(entered, f"NEQ({ctx}.Done,0)", f"MOV(0,{ctx}.Execute)",
                         *_ld_marks(step, names),
                         _ld_advance(app, step, index, names, step.on_advance)))
        if step.action == decl.GUARDED:
            # Below the completion leg, so completion wins in one scan: that
            # leg has already moved the step, and this one sees Done.
            legs.append(_leg(entered, f"EQU({ctx}.Done,0)",
                             ld_fails(step.conditions, names),
                             f"MOV(0,{ctx}.Execute)",
                             _ld_warning(step, index, names),
                             _ld_advance(app, step, index, names, step.on_jump)))
        if step.action in (decl.ISSUE, decl.GUARDED):
            legs.append(_leg(entered, f"NEQ({ctx}.Error,0)",
                             f"MOV({ctx}.ErrorID,{c}.StallReason)"))
        elif step.action == decl.ADOPT:
            source = module_source(app, step.module)
            legs.append(_leg(
                entered, f"NEQ({ctx}.Error,0)",
                f"MOV(1,{u}.Error)", f"MOV({ctx}.ErrorID,{u}.ErrorID)",
                f"MOV({source},{u}.ErrorSource)",
                f"MOV({ctx}.ErrorID,{c}.StallReason)",
                f"MOV(0,{u}.Running)", f"MOV(0,{ctx}.Execute)"))
        else:
            legs.append(_leg(
                entered, f"NEQ({ctx}.Error,0)",
                f"MOV({ctx}.ErrorID,{u}.ReportedReason)",
                f"MOV({module_source(app, step.module)},{u}.ReportedSource)",
                f"ADD({u}.ReportedCount,1,{u}.ReportedCount)",
                f"MOV({ctx}.ErrorID,{c}.WarnReason[{index}])",
                f"MOV({module_source(app, step.module)},{c}.WarnSource[{index}])",
                f"MOV(0,{ctx}.Execute)",
                _ld_advance(app, step, index, names, step.on_jump)))

    elif step.action == decl.DELAY:
        member = f"{names.cfg}.{step.duration_member}"
        held = "".join(ld_holds(x, names) for x in step.conditions)
        legs.append(_leg(fresh, f"MOV(0,{c}.DelayMs)"))
        legs.append(_leg(entered, held,
                         f"ADD({c}.DelayMs,{app.task_period_ms},{c}.DelayMs)"))
        legs.append(_leg(held, f"GEQ({c}.DelayMs,{member})",
                         _ld_advance(app, step, index, names, step.on_advance)))
        legs.append(_leg(held, f"LES({c}.DelayMs,{member})",
                         f"MOV({app.reasons['WAIT_DELAY']},{c}.StallReason)"))
        if step.conditions:
            paused = step.hold_reason or app.reasons["WAIT_CONDITION"]
            legs.append(_leg(ld_fails(step.conditions, names),
                             f"MOV({paused},{c}.StallReason)"))

    elif step.action == decl.AWAIT:
        ready = "".join(ld_holds(x, names) for x in step.conditions)
        legs.append(_leg(ready, _ld_advance(app, step, index, names, step.on_advance)))
        reason = step.hold_reason or app.reasons["WAIT_CONDITION"]
        legs.append(_leg(ld_fails(step.conditions, names),
                         f"MOV({reason},{c}.StallReason)"))

    elif step.action == decl.DECISION:
        legs.append(f"MOV({step.decision_id},{u}.DecisionId)")
        legs.append(_leg(f"EQU({u}.DecisionAnswer,1)",
                         f"ADD({u}.DecisionCount,1,{u}.DecisionCount)",
                         _ld_advance(app, step, index, names, step.on_advance),
                         f"MOV(0,{u}.DecisionId)", f"MOV(0,{u}.DecisionAnswer)"))
        legs.append(_leg(f"GRT({u}.DecisionAnswer,1)",
                         f"ADD({u}.DecisionCount,1,{u}.DecisionCount)",
                         _ld_advance(app, step, index, names, step.on_jump),
                         f"MOV(0,{u}.DecisionId)", f"MOV(0,{u}.DecisionAnswer)"))
        legs.append(_leg(f"EQU({u}.DecisionAnswer,0)",
                         f"MOV({app.reasons['WAIT_DECISION']},"
                         f"{c}.StallReason)"))

    elif step.action == decl.MARK:
        legs.append(_leg(*_ld_marks(step, names),
                         _ld_advance(app, step, index, names, step.on_advance)))

    elif step.action == decl.COMPLETE:
        legs.append(_leg(f"MOV(1,{u}.Complete)", f"MOV(0,{u}.Running)",
                         f"MOV(0,{c}.StallReason)"))

    body = ",".join(leg for leg in legs if leg)
    return f"EQU({u}.Step,{step.number})EQU({adv},0)[{body}];"


def chain_ld_rungs(app: decl.Application, chain: decl.Chain) -> list[str]:
    """The rungs of one ladder rendition, in execution order."""
    names = Names(app, in_aoi=False)
    steps_order = ordered_steps(app)
    u, c = names.unit, names.chart
    adv, scratch = ld_advanced_tag(app), ld_scratch_tag(app)
    rungs = [
        f"MOV(0,{adv})MOV({chain.mode_ordinal},{c}.ActiveChain);",
        f"SUB({names.scan},{u}.StepScan,{scratch})"
        f"MUL({scratch},{app.task_period_ms},{c}.CurrentStepMs);",
    ]
    ordered = sorted(chain.steps, key=lambda s: s.number)
    for step in ordered:
        rungs.append(ld_step_rung(app, chain, step,
                                  steps_order.index(step.number), names))
    return rungs


def st_content_lines(logic) -> str:
    """One presentation policy for routines, AOIs and SFC action/condition ST."""
    return "\n".join(
        f'<Line Number="{i}"><![CDATA[{statement}]]></Line>'
        for i, statement in enumerate(format_lines(logic))
    )


def st_program_routine(name: str, logic) -> str:
    lines = st_content_lines(logic)
    return (f'<Routine Name="{name}" Type="ST">\n<STContent>\n{lines}\n'
            "</STContent>\n</Routine>")


def ld_program_routine(name: str, rungs) -> str:
    body = "\n".join(
        f'<Rung Number="{i}" Type="N"><Text><![CDATA[{rung}]]></Text></Rung>'
        for i, rung in enumerate(rungs)
    )
    return (f'<Routine Name="{name}" Type="RLL">\n<RLLContent>\n{body}\n'
            "</RLLContent>\n</Routine>")


def rendition_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_RenditionSelect"


def multi_chains(app: decl.Application):
    """Chains carried in several languages: the ones a selector chooses among."""
    return [c for c in app.chains if c.multi_rendition]


def hosted_chains(app: decl.Application):
    """Chains that run in program routines (every rendition but a lone ST)."""
    return [c for c in app.chains if c.program_hosted]


def rendition_ordinal(rendition: str) -> int:
    return decl.RENDITIONS.index(rendition)


def chain_routines(app: decl.Application) -> list[str]:
    """Every rendition of every program-hosted chain, as program routines."""
    out: list[str] = []
    for chain in hosted_chains(app):
        for rendition in chain.renditions:
            name = chain_routine_name(app, chain, rendition)
            if rendition == decl.ST:
                out.append(st_program_routine(name, chain_st_logic(app, chain)))
            elif rendition == decl.LD:
                out.append(ld_program_routine(name, chain_ld_rungs(app, chain)))
            elif rendition == decl.SFC:
                out.append(chain_sfc_routine(app, chain))
                out.append(st_program_routine(sfc_runner_name(app, chain),
                                              sfc_runner_logic(app, chain)))
    return out


def dispatch_logic(app: decl.Application) -> list[str]:
    """JSR exactly one rendition of the active program-hosted chain.

    The owner AOI has already run, so the latches and the ordering check are
    settled before any rendition executes - sequence intent still comes second.
    A chain carried in one language has nothing to select: it is called.
    """
    lines: list[str] = []
    unit = f"FRK_{app.name}_Unit"
    select = rendition_tag(app)
    for chain in hosted_chains(app):
        lines.append(f"(* {chain.name}: one rendition runs, chosen by {select} *)"
                     if chain.multi_rendition else
                     f"(* {chain.name}: rendered in {chain.renditions[0]} *)")
        lines.append(f"IF ({unit}.Mode = {chain.mode_ordinal}) "
                     f"AND ({unit}.Running <> 0) THEN")
        for rendition in chain.renditions:
            target = (sfc_runner_name(app, chain) if rendition == decl.SFC
                      else chain_routine_name(app, chain, rendition))
            if chain.multi_rendition:
                lines.append(f"IF {select} = {rendition_ordinal(rendition)} THEN")
            lines.append(f"JSR({target},0);")
            if chain.multi_rendition:
                lines.append("END_IF;")
        lines.append("END_IF;")
    return lines


# --- the SFC rendition ------------------------------------------------------
#
# The S11 emission pattern, generalised: a program-owned chart driven by a
# generated JSR/SFR wrapper, with the controller set to execute current active
# steps only so one JSR advances one step.
#
# The split between an action and a transition is what makes this a real SFC
# rendering rather than an ST chain wearing a chart's clothes. The action does
# the step's *work* and the transition carries its *condition*; both are derived
# from the same declared step, so neither is a second source.

SFC_EXECUTION_CONTROL = "CurrentActive"
SFC_RESTART_POSITION = "InitialStep"
SFC_LAST_SCAN = "DontScan"


def sfc_step_tag(app: decl.Application, chain: decl.Chain, number: int) -> str:
    return f"FRK_{app.name}{chain.name.title()}S{number}"


def sfc_action_tag(app: decl.Application, chain: decl.Chain, number: int) -> str:
    return f"FRK_{app.name}{chain.name.title()}A{number}"


def sfc_transition_tag(app: decl.Application, chain: decl.Chain,
                       number: int, kind: str) -> str:
    return f"FRK_{app.name}{chain.name.title()}T{number}{kind}"


def sfc_edges(chain: decl.Chain):
    """Every declared edge, as (from, to, kind)."""
    edges = []
    for step in chain.steps:
        if step.on_advance != -1:
            edges.append((step.number, step.on_advance, "A"))
        if step.on_jump != -1:
            edges.append((step.number, step.on_jump, "J"))
    return edges


def sfc_condition(app: decl.Application, step: decl.Step, kind: str,
                  names: Names) -> str:
    """The transition condition for one declared edge.

    Derived from the same step the action is derived from - the graph is
    declared once, and neither half of the chart is hand-written.
    """
    u, c = names.unit, names.chart
    ctx = names.module(step.module) if step.module else ""
    # A commanding step reads its module only after its entry scan, as the
    # ST and LD renditions do. On the entry scan the module still holds the
    # result of whatever it last did: a door opened at N130 is still Done when
    # N180 asks it to close, and a transition reading that Done would leave
    # the step without the door ever moving.
    entered = f"({names.scan} <> {u}.StepScan)"
    if step.action in (decl.ISSUE, decl.ADOPT):
        return f"{entered} AND ({ctx}.Done <> 0)"
    if step.action == decl.GUARDED:
        # Completion wins: the jump only while not done.
        return (f"{entered} AND ({ctx}.Done <> 0)" if kind == "A" else
                f"{entered} AND ({ctx}.Done = 0) "
                f"AND NOT ({conds_st(step.conditions, names)})")
    if step.action == decl.REPORT:
        return (f"{entered} AND ({ctx}.Done <> 0)" if kind == "A" else
                f"{entered} AND ({ctx}.Done = 0) AND ({ctx}.Error <> 0)")
    if step.action == decl.DELAY:
        due = f"{c}.DelayMs >= {names.cfg}.{step.duration_member}"
        held = _delay_held(step, names)
        return f"({held}) AND ({due})" if held else due
    if step.action == decl.AWAIT:
        return conds_st(step.conditions, names) or "1=1"
    if step.action == decl.DECISION:
        return (f"{u}.DecisionAnswer = 1" if kind == "A"
                else f"{u}.DecisionAnswer > 1")
    return "1=1"


def sfc_action_logic(app: decl.Application, chain: decl.Chain, step: decl.Step,
                     index: int, names: Names) -> tuple[str, ...]:
    """The step's work, without the transition: the chart owns the advance."""
    u, c = names.unit, names.chart
    lines = [f"(* {step.name}: {step.comment} *)", f"{u}.Step := {step.number};"]
    lines += _mark_step(app, index, names)
    lines += _cond_ok(step, names)
    # The chart advances on its transition, so the duration is published every
    # scan; the last value written is the duration of the visit.
    lines.append(f"{c}.LastMs[{index}] := {c}.CurrentStepMs;")

    if step.module and step.command:
        module = next(m for m in app.modules if m.name == step.module)
        command = next(cm for cm in module.commands if cm.name == step.command)
        ctx = names.module(step.module)
        issue = _paced_st(app, step, names, [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
        ])
        # The ST branch's own shape, minus the advance the chart's transition
        # makes: drop Execute on the entry scan, command from the next, and
        # read the module only then. Completion drops Execute here too, as ST
        # does, so the module returns to READY the same way in every
        # rendition rather than staying Done until another step drops it.
        lines += _entry_reset(ctx, names, app) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
            *_st_marks(step, names),
        ]
        if step.action == decl.GUARDED:
            lines += [
                f"ELSIF NOT ({conds_st(step.conditions, names)}) THEN",
                "(* Abandoned: the jump transition fires this scan *)",
                f"{ctx}.Execute := 0;",
                *_st_warning(step, index, names),
            ]
        if step.action == decl.ADOPT:
            source = module_source(app, step.module)
            lines += [
                f"ELSIF {ctx}.Error <> 0 THEN",
                "(* Adopt the child's first-out verbatim *)",
                f"{u}.Error := 1;",
                f"{u}.ErrorID := {ctx}.ErrorID;",
                f"{u}.ErrorSource := {source};",
                f"{c}.StallReason := {ctx}.ErrorID;",
                f"{u}.Running := 0;",
                f"{ctx}.Execute := 0;",
            ]
        elif step.action == decl.REPORT:
            lines += [
                f"ELSIF {ctx}.Error <> 0 THEN",
                "(* Report the child's own first-out; do NOT adopt it *)",
                f"{u}.ReportedReason := {ctx}.ErrorID;",
                f"{u}.ReportedSource := {module_source(app, step.module)};",
                f"{u}.ReportedCount := {u}.ReportedCount + 1;",
                f"{c}.WarnReason[{index}] := {ctx}.ErrorID;",
                f"{c}.WarnSource[{index}] := {module_source(app, step.module)};",
                f"{ctx}.Execute := 0;",
            ]
        else:
            lines += [
                f"ELSIF {ctx}.Error <> 0 THEN",
                f"{c}.StallReason := {ctx}.ErrorID;",
            ]
        lines += ["END_IF;", "END_IF;"]

    elif step.action == decl.DELAY:
        held = _delay_held(step, names)
        running = f"{c}.DelayMs < {names.cfg}.{step.duration_member}"
        lines += _delay_clock(app, step, names) + (
            [f"IF NOT ({held}) THEN",
             f"{c}.StallReason := {step.hold_reason or app.reasons['WAIT_CONDITION']};",
             f"ELSIF {running} THEN"] if held else [f"IF {running} THEN"]
        ) + [
            f"{c}.StallReason := {app.reasons['WAIT_DELAY']};",
            "END_IF;",
        ]
    elif step.action == decl.AWAIT:
        ready = conds_st(step.conditions, names)
        reason = step.hold_reason or app.reasons["WAIT_CONDITION"]
        lines += [f"IF NOT ({ready}) THEN", f"{c}.StallReason := {reason};", "END_IF;"]
    elif step.action == decl.DECISION:
        lines += [
            f"{u}.DecisionId := {step.decision_id};",
            f"IF {u}.DecisionAnswer = 0 THEN",
            f"{c}.StallReason := {app.reasons['WAIT_DECISION']};",
            "ELSE",
            f"{u}.DecisionCount := {u}.DecisionCount + 1;",
            f"{u}.DecisionId := 0;",
            "END_IF;",
        ]
    elif step.action == decl.MARK:
        for mark in step.marks:
            lines.append(mark.replace("Ctx.", f"{u}.") + ";")
    elif step.action == decl.COMPLETE:
        lines += [f"{u}.Complete := 1;", f"{u}.Running := 0;",
                  f"{c}.StallReason := 0;"]
    return tuple(line for line in lines if line)


def chain_sfc_routine(app: decl.Application, chain: decl.Chain) -> str:
    """Serialize the chart from the same declared graph the other renditions use."""
    names = Names(app, in_aoi=False)
    steps_order = ordered_steps(app)
    ordered = sorted(chain.steps, key=lambda s: s.number)
    by_number = {s.number: s for s in ordered}
    edges = sfc_edges(chain)

    identifiers: dict[str, int] = {}
    body: list[str] = []
    next_id = 0
    entry = ordered[0]

    for row, step in enumerate(ordered):
        x, y = 240, 60 + row * 120
        step_id, action_id = next_id, next_id + 1
        next_id += 2
        identifiers[f"S{step.number}"] = step_id
        lines = st_content_lines(sfc_action_logic(
            app, chain, step, steps_order.index(step.number), names))
        body.append(
            f'<Step ID="{step_id}" X="{x}" Y="{y}" '
            f'Operand="{sfc_step_tag(app, chain, step.number)}" '
            f'HideDesc="true" DescX="{x + 54}" DescY="{y - 15}" DescWidth="0" '
            f'InitialStep="{str(step is entry).lower()}" '
            'PresetUsesExpr="false" LimitHighUsesExpr="false" '
            'LimitLowUsesExpr="false" ShowActions="true">\n'
            f'<Action ID="{action_id}" '
            f'Operand="{sfc_action_tag(app, chain, step.number)}" '
            'Qualifier="NonStored" IsBoolean="false" PresetUsesExpr="false">\n'
            "<Body>\n<STContent>\n"
            f"{lines}\n"
            "</STContent>\n</Body>\n</Action>\n</Step>"
        )

    for source, target, kind in edges:
        step = by_number[source]
        key = f"T{source}{kind}"
        identifiers[key] = next_id
        x, y = 240, 120 + ordered.index(step) * 120
        body.append(
            f'<Transition ID="{next_id}" X="{x}" Y="{y}" '
            f'Operand="{sfc_transition_tag(app, chain, source, kind)}" '
            f'HideDesc="true" DescX="{x + 35}" DescY="{y - 15}" DescWidth="0">\n'
            "<Condition>\n<STContent>\n"
            f'{st_content_lines((sfc_condition(app, step, kind, names),))}\n'
            "</STContent>\n</Condition>\n</Transition>"
        )
        next_id += 1

    links: list[tuple[int, int]] = []
    outgoing: dict[int, list[tuple[int, int, str]]] = {}
    for source, target, kind in edges:
        outgoing.setdefault(source, []).append((source, target, kind))

    for source, group in outgoing.items():
        if len(group) == 1:
            _, target, kind = group[0]
            links.append((identifiers[f"S{source}"], identifiers[f"T{source}{kind}"]))
        else:
            diverge_id = next_id
            leg_ids = [next_id + 1 + i for i in range(len(group))]
            next_id += 1 + len(group)
            y = 120 + ordered.index(by_number[source]) * 120
            body.append(
                f'<Branch ID="{diverge_id}" Y="{y}" BranchType="Selection" '
                'BranchFlow="Diverge">\n'
                + "\n".join(f'<Leg ID="{leg}"/>' for leg in leg_ids)
                + "\n</Branch>"
            )
            links.append((identifiers[f"S{source}"], diverge_id))
            for leg, (_, _, kind) in zip(leg_ids, group):
                links.append((leg, identifiers[f"T{source}{kind}"]))

    # Logix accepts exactly one directed link into a step. Where the declared
    # graph converges - the loop back to the first working step, and the three
    # ways of reaching the return-to-safe-position step - the chart needs an
    # explicit selection converge, which is the chart's way of saying the same
    # thing the other renditions say with two transitions to one step number.
    incoming: dict[int, list[tuple[int, int, str]]] = {}
    for source, target, kind in edges:
        incoming.setdefault(target, []).append((source, target, kind))

    for target, group in incoming.items():
        if len(group) == 1:
            source, _, kind = group[0]
            links.append((identifiers[f"T{source}{kind}"], identifiers[f"S{target}"]))
            continue
        converge_id = next_id
        leg_ids = [next_id + 1 + i for i in range(len(group))]
        next_id += 1 + len(group)
        y = 60 + ordered.index(by_number[target]) * 120 - 30
        body.append(
            f'<Branch ID="{converge_id}" Y="{y}" BranchType="Selection" '
            'BranchFlow="Converge">\n'
            + "\n".join(f'<Leg ID="{leg}"/>' for leg in leg_ids)
            + "\n</Branch>"
        )
        for leg, (source, _, kind) in zip(leg_ids, group):
            links.append((identifiers[f"T{source}{kind}"], leg))
        links.append((converge_id, identifiers[f"S{target}"]))

    body.extend(
        f'<DirectedLink FromID="{a}" ToID="{b}" Show="true"/>'
        for a, b in sorted(links)
    )
    content = "\n".join(body)
    name = chain_routine_name(app, chain, decl.SFC)
    return (f'<Routine Name="{name}" Type="SFC">\n'
            '<SFCContent SheetSize="Letter - 8.5 x 11 in" SheetOrientation="Landscape" '
            'StepName="Step" TransitionName="Tran" ActionName="Action" StopName="Stop">\n'
            f"{content}\n</SFCContent>\n</Routine>")


def sfc_runner_logic(app: decl.Application, chain: decl.Chain) -> tuple[str, ...]:
    """The generated JSR/SFR wrapper of AB 3.5, as S11 proved it."""
    unit = f"FRK_{app.name}_Unit"
    chart = chain_routine_name(app, chain, decl.SFC)
    entry = sorted(chain.steps, key=lambda s: s.number)[0]
    return (
        "(* Reset the chart to its initial step on a genuine restart edge only. *)",
        "(* PrevStep is -1 exactly on the scan after the owner stood the chain  *)",
        "(* down, and the first step to mark itself clears it. Conditioning the  *)",
        "(* SFR on the step number instead would be self-perpetuating: the first *)",
        "(* step's own action writes that number, so the chart would be reset    *)",
        "(* every scan and could never advance past it.                          *)",
        f"IF {unit}.PrevStep < 0 THEN",
        f"SFR({chart},{sfc_step_tag(app, chain, entry.number)});",
        "END_IF;",
        f"JSR({chart},0);",
    )


def sfc_program_tags(app: decl.Application) -> list[str]:
    """Step, action and transition tags for every emitted chart."""
    tags: list[str] = []
    for chain in app.chains:
        if decl.SFC not in chain.renditions:
            continue
        for step in sorted(chain.steps, key=lambda s: s.number):
            tags.append(
                f'<Tag Name="{sfc_step_tag(app, chain, step.number)}" TagType="Base" '
                'DataType="SFC_STEP" Constant="false" ExternalAccess="Read/Write"/>')
            tags.append(
                f'<Tag Name="{sfc_action_tag(app, chain, step.number)}" TagType="Base" '
                'DataType="SFC_ACTION" Constant="false" ExternalAccess="Read/Write"/>')
        for source, _, kind in sfc_edges(chain):
            tags.append(
                f'<Tag Name="{sfc_transition_tag(app, chain, source, kind)}" '
                'TagType="Base" DataType="BOOL" Radix="Decimal" Constant="false" '
                'ExternalAccess="Read/Write"/>')
    return tags


def unit_aoi(app: decl.Application) -> str:
    return _aoi(
        unit_aoi_name(app),
        f"Generated mode owner for {app.name}: chains {[c.name for c in app.chains]}",
        ENABLE_PARAMETERS + unit_parameters(app),
        unit_logic(app),
        (unit_context_name(app), chart_name(app),
         *(module_context_name(t) for t in library.types_used(app)),
         app.records[0].name),
    )


def aoi_definitions(app: decl.Application) -> str:
    blocks = module_aois(app) + [unit_aoi(app)]
    return "<AddOnInstructionDefinitions>\n" + "\n".join(blocks) + "\n</AddOnInstructionDefinitions>"


# --- tags -------------------------------------------------------------------

def _structure_tag(name: str, data_type: str, members: tuple[decl.Member, ...],
                   external_access: str = "Read Only") -> str:
    """A contract structure tag.

    ``Read Only`` by default, which is AB §11.2.1's rule for public data. These
    are what the machine publishes about itself - its contexts, its chart, its
    configuration record - and a client that could write them could set a
    module's state without the module ever running, or edit configuration
    outside the request that is supposed to carry it. Commands and configuration
    changes arrive through the mailbox, which validates and acknowledges them.
    """
    parts = []
    for member in members:
        if member.dimension:
            values = ",".join(["0"] * member.dimension)
            parts.append(
                f'<ArrayMember Name="{member.name}" DataType="DINT" '
                f'Dimension="{member.dimension}" Radix="Decimal">'
                + "".join(
                    f'<Element Index="[{i}]" Value="0"/>' for i in range(member.dimension)
                )
                + "</ArrayMember>"
            )
        else:
            parts.append(
                f'<DataValueMember Name="{member.name}" DataType="DINT" '
                f'Radix="Decimal" Value="{member.initial}"/>'
            )
    body = "\n".join(parts)
    return f"""<Tag Name="{name}" TagType="Base" DataType="{data_type}" Constant="false" ExternalAccess="{external_access}">
<Data Format="Decorated">
<Structure DataType="{data_type}">
{body}
</Structure>
</Data>
</Tag>"""


def _dint_scratch_tag(name: str, dimension: int = 0) -> str:
    """A controller-scope working DINT (or DINT array). ExternalAccess None:
    AB §11.2.1 - nothing that is neither the mailbox nor public data is
    reachable from outside."""
    if not dimension:
        return (f'<Tag Name="{name}" TagType="Base" DataType="DINT" '
                f'Radix="Decimal" Constant="false" ExternalAccess="None">'
                f'<Data Format="Decorated"><DataValue DataType="DINT" '
                f'Radix="Decimal" Value="0"/></Data></Tag>')
    elements = "".join(f'<Element Index="[{i}]" Value="0"/>'
                       for i in range(dimension))
    return (f'<Tag Name="{name}" TagType="Base" DataType="DINT" '
            f'Dimensions="{dimension}" Radix="Decimal" Constant="false" '
            f'ExternalAccess="None"><Data Format="Decorated">'
            f'<Array DataType="DINT" Dimensions="{dimension}" Radix="Decimal">'
            f'{elements}</Array></Data></Tag>')


def _structure_array_tag(name: str, data_type: str,
                         elements: list[tuple[decl.Member, ...]],
                         external_access: str = "Read Only") -> str:
    """An array of contract structures, one element per declared model.

    Read Only like every other published structure: a client that could write
    these directly would set a model's stored values without the mailbox ever
    validating them, which is the whole point of routing configuration through
    a request that checks bounds.
    """
    newline = chr(10)
    bodies = []
    for index, members in enumerate(elements):
        values = newline.join(
            f'<DataValueMember Name="{m.name}" DataType="DINT" '
            f'Radix="Decimal" Value="{m.initial}"/>' for m in members)
        bodies.append(
            f'<Element Index="[{index}]">{newline}'
            f'<Structure DataType="{data_type}">{newline}'
            f'{values}{newline}</Structure>{newline}'
            f'</Element>')
    body = newline.join(bodies)
    return f"""<Tag Name="{name}" TagType="Base" DataType="{data_type}" Dimensions="{len(elements)}" Constant="false" ExternalAccess="{external_access}">
<Data Format="Decorated">
<Array DataType="{data_type}" Dimensions="{len(elements)}">
{body}
</Array>
</Data>
</Tag>"""


def model_cfg_elements(app: decl.Application) -> list[tuple[decl.Member, ...]]:
    """Each model's element, initialized to that model's declared values.

    The SchemaVersion of every element starts at ZERO. On Logix a download
    resets a tag to its initial value, so a fresh controller reads "never
    written" for each model and installs the declared numbers; a controller
    holding commissioned model data keeps it. The declared values live in the
    initializer only so the restore has something to install.
    """
    scoped = model_scoped_members(app)
    elements = []
    for model in app.models:
        members = [decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=0)]
        for member in scoped:
            members.append(decl.scalar(
                member.name, "", initial=model.values.get(member.name, 0)))
        elements.append(tuple(members))
    for _ in range(max(0, app.model_capacity - len(elements))):
        elements.append(tuple(decl.scalar(m.name, initial=0) for m in model_cfg_members(app)))
    return elements


def command_inputs(app: decl.Application) -> tuple[str, ...]:
    """The request tags the mailbox routes into.

    These are the mailbox's *outputs*, not a client's inputs. A command arrives
    through ``HmiRequest``, where it is validated against the declared modes,
    refused by name when this binding does not support it, and acknowledged with
    the sequence that asked. Leaving these externally writable would let a CIP
    client set ``RunRequest`` directly and skip every one of those checks, so
    they are emitted ``None``: the mailbox is the only way in, and therefore the
    only place a command is recorded.
    """
    return (
        f"FRK_{app.name}_RunRequest",
        f"FRK_{app.name}_AbortRequest",
        f"FRK_{app.name}_ResetRequest",
        f"FRK_{app.name}_ModeRequest",
        f"FRK_{app.name}_DecisionAnswer",
        # ModelRequest is SET_MODEL's output, not the plant's. It is declared a
        # sim input so the CHANGEOVER wait can name it as a condition, and that
        # alone would have left it in the stimulus surface - externally
        # writable, so a CIP client could select a model ordinal directly and
        # skip the range check the mailbox applies. Naming it here is what
        # makes it None.
    ) + ((f"FRK_{app.name}_ModelRequest",) if app.models else ())


def stimulus_inputs(app: decl.Application) -> tuple[str, ...]:
    """The simulated world, and the evidence apparatus' injections.

    A command mailbox cannot carry these and should not try: "the part-present
    sensor went true" is the plant's world, not something an operator asks the
    machine to do, and a request kind invented for it would be a command no
    operator ever issues. They are writable only in a declared test build - see
    ``externally_writable`` - so a shipped build exposes the mailbox and nothing
    else.
    """
    commands = set(command_inputs(app))
    names: list[str] = []
    for module in app.modules:
        for injection in library.type_of(module).injections:
            names.append(injection_tag(app, module, injection))
    names.extend(t for t in app.sim_inputs if t not in commands)
    if multi_chains(app):
        # Which rendition of a multi-rendition chain runs, so the harness can
        # walk one graph in each language in a single session.
        names.append(rendition_tag(app))
    return tuple(names)


def writable_inputs(app: decl.Application) -> tuple[str, ...]:
    """Every input tag the application emits, whatever its external access.

    The name is historical: it predates the mailbox, when all of these really
    were externally writable. What a build actually exposes is
    ``externally_writable``; this is the emission list.
    """
    return command_inputs(app) + stimulus_inputs(app)


def externally_writable(app: decl.Application) -> tuple[str, ...]:
    """What a CIP client may write besides the mailbox itself.

    AB §11.2.1 wants the mailbox ``Read/Write``, public data ``Read Only`` and
    everything else ``None``. What remains here is the simulated plant, and it
    remains for a reason that is a property of *this application* rather than of
    the binding: the press demo declares no physical I/O, so the signals a real
    machine would take from a card are tags instead. A real application has no
    such tags, and this list is empty for it.

    That is a narrowing worth stating plainly rather than hiding behind a build
    flag: on this demo, a CIP client can still move the simulated world. What it
    can no longer do is issue a command - see ``command_inputs``.
    """
    return stimulus_inputs(app)


# --- what a manifest may describe, and what it may not ----------------------
#
# The published contract describes the declared graph **once**, and says nothing
# about which language rendered it - the same way the TC3 HMI sees one chart
# whichever rendition ran. A rendition is an emission of the graph, so publishing
# a way to select one would describe the evidence apparatus rather than the
# machine, and would invite a client to choose a language, which is not a
# machine-level concept at all.
#
# These tags are therefore **probe-only**: writable, because the parity harness
# drives them, and deliberately absent from anything published. The split is
# declared here rather than left to the future manifest emitter to remember.
#
# The ladder scratch and guard tags are here for the same reason from the other
# direction: they are how one rendition happens to be implemented, not anything
# the graph means.

def harness_only_tags(app: decl.Application) -> tuple[str, ...]:
    """Tags that exist for the evidence apparatus, never for an operator."""
    tags: list[str] = []
    if multi_chains(app):
        tags.append(rendition_tag(app))
    if any(decl.LD in c.renditions for c in app.chains):
        tags.extend([ld_advanced_tag(app), ld_scratch_tag(app)])
    return tuple(tags)


def publishable_tags(app: decl.Application) -> tuple[str, ...]:
    """Every emitted tag a manifest may describe: everything else is excluded.

    ``fraktal_ab_manifest.content`` derives the published field list from this,
    so the rendition selector and a rendition's implementation tags are absent
    from the contract by construction rather than by anyone remembering to leave
    them out.
    """
    # A tag the mailbox routes into is not public data: it is the mailbox's own
    # output, it is emitted None, and describing it in the manifest would
    # advertise a surface the controller refuses. The request arrives at
    # HmiRequest, which the manifest does publish.
    excluded = set(harness_only_tags(app)) | set(command_inputs(app))
    published: list[str] = []
    for record in app.records:
        published.append(f"{record.name}Tag")
    for module in app.modules:
        published.append(ctx_tag_for(app, module.name))
    published.append(f"FRK_{app.name}_Unit")
    published.append(f"FRK_{app.name}_Chart")
    published.append(config_persist_tag(app))
    if model_cfg_members(app):
        published.append(model_cfg_tag(app))
    published.append(alarm_active_tag(app))
    published.append(alarm_ring_tag(app))
    published.append(oee_tag(app))
    if app.line is not None:
        import fraktal_ab_line as line
        published += [line.tag(app, n) for n in ('State', 'Shift')]
    published.append(profiler_tag(app))
    if app.access_users is not None:
        import fraktal_ab_access as access
        published += [access.tag(app, 'State'), access.tag(app, 'Audit')]
        import fraktal_ab_data_access as data
        published += [data.tag(app, 'Policy'), data.tag(app, 'Levels')]
    if editable_values(app):
        published.append(config.audit_tag(app))
    if app.config_sets:
        import fraktal_ab_sets as sets
        published.append(sets.state_tag(app))
    if app.state_flags:
        published.append(state_flags_tag(app))
    published.append(health_probe_tag(app))
    if app.system_health is not None:
        published.extend([health_cfg_tag(app), system_health_tag(app)])
    published.extend(writable_inputs(app))
    published.extend(evidence_tags(app))
    return tuple(t for t in dict.fromkeys(published) if t not in excluded)


def evidence_tags(app: decl.Application) -> tuple[str, ...]:
    tags = [
        f"FRK_{app.name}_ScanCount",
        f"FRK_{app.name}_OrderFail",
        f"FRK_{app.name}_TaskPeriodMs",
    ]
    if any(decl.LD in c.renditions for c in app.chains):
        tags.extend([ld_advanced_tag(app), ld_scratch_tag(app)])
    return tuple(tags)


def controller_tags(app: decl.Application) -> str:
    tags: list[str] = []
    if app.line is not None:
        import fraktal_ab_line as line
        tags += line.tags(app)
    if app.access_users is not None:
        import fraktal_ab_access as access
        tags += access.tags(app)
        import fraktal_ab_data_access as data
        tags += data.tags(app)
    if app.config_sets:
        import fraktal_ab_sets as sets
        tags.append(_structure_tag(sets.state_tag(app), sets.state_name(app), sets.state_members(app)))
        tags.append(_structure_tag(sets.staged_tag(app), sets.request_name(), sets.request_members(), external_access='None'))
        tags += [_dint_scratch_tag(n) for n in sets.scratch_names(app)]
    if editable_values(app):
        tags.append(_structure_tag(config.audit_tag(app), config.audit_name(), config.audit_members()))
        tags.append(_dint_scratch_tag(config.candidate_tag(app)))
        if not app.config_sets:
            tags += [_dint_scratch_tag(n) for n in config.scratch_names(app)]
    for record in app.records:
        tags.append(_structure_tag(f"{record.name}Tag", record.name, record.members))
    tags.append(_structure_tag(config_persist_tag(app), config_persist_name(app),
                               config_persist_members()))
    if model_cfg_members(app):
        tags.append(_structure_array_tag(model_cfg_tag(app), model_cfg_name(app),
                                         model_cfg_elements(app)))
    if app.model_capacity:
        import fraktal_ab_models as models
        tags.append(_structure_tag(models.tag(app), models.type_name(), models.members(app)))
    # Core 8.3: Read Only like every published structure. An alarm a client
    # could write is an alarm a client could close without the reset that
    # §8.3(b) requires before a restart.
    tags.append(_structure_tag(alarm_active_tag(app), alarm_active_name(),
                               alarm_active_members()))
    tags.append(_structure_tag(alarm_ring_tag(app), alarm_ring_name(),
                               alarm_ring_members()))
    import fraktal_ab_shelving as shelving
    tags.append(_structure_tag(shelving.tag(app), shelving.record().name,
                               shelving.members(), external_access='None'))
    # Core 8.5.1: Read Only, so only RESET_OEE - through the mailbox - resets it.
    tags.append(_structure_tag(oee_tag(app), oee_name(), oee_members()))
    # Core 8.11.4: Read Only. Only the routine writes the profile.
    tags.append(_structure_tag(profiler_tag(app), profiler_name(),
                               profiler_members(app)))
    if app.state_flags:
        # Core 3.12: Read Only. A flag is derived, never written.
        tags.append(_structure_tag(state_flags_tag(app), state_flags_name(app),
                                   state_flags_members(app)))
    # Core 8.12: Read Only. What the controller says about itself.
    tags.append(_structure_tag(health_probe_tag(app), health_probe_name(),
                               health_probe_members()))
    if app.system_health is not None:
        tags.append(_structure_tag(health_cfg_tag(app), health_cfg_name(app),
                                   health_cfg_members(app)))
        tags.append(_structure_tag(system_health_tag(app), system_health_name(),
                                   system_health_members()))
    # Core 7.8: the report START reads, and the one the mailbox answers with.
    tags.append(_structure_tag(start_release_tag(app), release_report_name(app),
                               release_report_members()))
    tags.append(_structure_tag(release_report_tag(app), release_report_name(app),
                               release_report_members()))
    for name, dimension in {**clock_tags(app), **alarm_scratch_tags(app),
                            diagnostic_scratch_tag(app): 0,
                            stall_limit_tag(app): 0,
                            release_index_tag(app): 0}.items():
        tags.append(_dint_scratch_tag(name, dimension))
    for module in app.modules:
        # What is per INSTANCE is set here, in the instance's own context, so
        # the type's AOI stays one definition. The task period joins speed and
        # timeout: it is the application's, the instance carries it, and the
        # type reads it at run time instead of having it baked in.
        per_instance = {
            "Par_Speed": module.speed_per_scan,
            "Par_TimeoutMs": module.timeout_ms,
            "Par_TaskPeriodMs": app.task_period_ms,
        }
        initial = tuple(
            m if m.name not in per_instance
            else decl.Member(m.name, m.comment, m.kind, m.dimension,
                             per_instance[m.name])
            for m in module_members(module)
        )
        tags.append(_structure_tag(ctx_tag_for(app, module.name),
                                   module_context_name(library.type_of(module)),
                                   initial))
    tags.append(_structure_tag(f"FRK_{app.name}_Unit", unit_context_name(app),
                               unit_context_members(app)))
    tags.append(_structure_tag(f"FRK_{app.name}_Chart", chart_name(app),
                               chart_members(app)))
    # §11.2.1, emitted rather than asserted. The mailbox is the write surface;
    # a request tag the mailbox drives is None, and the stimulus surface is
    # Read/Write only in a declared test build. What the manifest publishes as a
    # field stays readable, so the contract a client discovers is still there.
    published = set(publishable_tags(app))
    writable = set(externally_writable(app))
    for name in writable_inputs(app):
        if name in writable:
            access = "Read/Write"
        elif name in published:
            access = "Read Only"
        else:
            access = "None"
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", access))
    harness = set(harness_only_tags(app))
    for name in evidence_tags(app):
        # A rendition's own scratch is not evidence anyone reads - nothing
        # outside the generator touches FRK_*_LdAdvanced or FRK_*_LdScratch, and
        # publishable_tags already keeps them out of the manifest. AB §11.2.1
        # says everything that is not the mailbox or public data is None, so
        # they are None rather than quietly readable.
        access = "None" if name in harness else "Read Only"
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", access))
    # §10.5.1 output forcing. Read Only to a client: a force is REQUESTED
    # through the mailbox and applied by the controller, so these are the
    # answer, never the input. Making ForceMask writable would let a client
    # hold an output without passing the permission test at all, which is the
    # write-surface bypass AB §11.2.1 exists to prevent.
    for name in force_tags(app):
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", "Read Only"))
    for module in app.modules:
        tags.append(
            f'<Tag Name="FRK_{app.name}_Inst{module.name}" TagType="Base" '
            f'DataType="{module_aoi_name(app, module)}" Constant="false" '
            f'ExternalAccess="None"/>'
        )
    tags.append(
        f'<Tag Name="FRK_{app.name}_InstUnit" TagType="Base" '
        f'DataType="{unit_aoi_name(app)}" Constant="false" ExternalAccess="None"/>'
    )
    # Core 3.10: the manifest is the runtime source of truth, so it
    # ships in the project rather than being assembled at scan time -
    # a client reads the same bytes the gate verified.
    # Core 3.10/14: the command mailbox is the one writable surface a
    # client is given. It ships with the application because a mailbox that
    # appeared only once something wrote to it could not be discovered.
    tags.extend(mailbox.tags(app))
    tags.extend(manifest.tags(app, CONTROLLER_IDENTITY))
    return "<Tags>\n" + "\n".join(tags) + "\n</Tags>"


def model_commit_logic(app: decl.Application) -> list[str]:
    """Core 3.8 changeover commit: a bounded copy, in the routine.

    The chain cannot do this itself. Its logic runs inside the Unit AOI, and an
    AOI cannot reach a controller-scope tag - so the chain raises CommitModel
    and the routine, which can see both the record and the array, performs the
    copy. It runs immediately after the AOI, so the commit lands in the same
    scan the chain asked for it.

    Fallible and infallible stay where §3.8 puts them. The mailbox already
    refused a model this station does not declare, and this is a fixed number
    of assignments with no validation and no I/O: it cannot fail and leave the
    press configured as neither model. The range test is not validation, it is
    the guard that keeps an out-of-range subscript from faulting the
    controller.
    """
    scoped = model_scoped_members(app)
    if not scoped or not app.models:
        return []
    n = app.name
    unit = f"FRK_{n}_Unit"
    cell = f"{model_cfg_tag(app)}[{unit}.CommitModel - 1]"
    cfg = f"{app.records[0].name}Tag"
    lines = [
        "",
        "(* Core 3.8 changeover: the bounded commit the chain asked for *)",
        f"IF {ordinal_guard(app, unit + '.CommitModel')} THEN",
    ]
    for member in scoped:
        lines.append(f"{cfg}.{member.name} := {cell}.{member.name};")
    lines.append(f"{unit}.CommitModel := 0;")
    lines.append("END_IF;")
    return lines


# --- Core §8.3 alarm log ------------------------------------------------------
#
# The Logix counterpart of TC3's FB_AlarmLog, at TC3's sizes (PL_Fraktal
# MAX_ALARM_ACTIVE / MAX_ALARM_RING). It lives on the CONTROLLER because a
# gateway polling at a few Hz cannot see a fault that clears inside one poll:
# a log built in the gateway would lose exactly the transient faults it most
# needs to show - the same reason §3.13 marks are never accumulated client-side.
#
# Stored as COLUMNS (ActReasonCode[16], RingReasonCode[64], ...) rather than as
# an array of event structures. Every column is a DINT array, which S12 proved
# and which the manifest describes as one Fields row with a Dimensions count -
# the same shape the chart already uses for its per-step marks.
#
# Split in two tags by how often each changes, as §3.13 splits the chart: the
# active events, RingHead and Blocking change with the machine and are read every
# poll; the ring changes only when an event closes, which RingHead says.

ALARM_ACTIVE = 16    # TC3 PL_Fraktal.MAX_ALARM_ACTIVE
ALARM_RING = 64      # TC3 PL_Fraktal.MAX_ALARM_RING
ALARM_SCHEMA = 2     # V1 prefix preserved; Core 8.10 shelf columns appended

# E_AlarmState / E_ResetClass ordinals: the client's AlarmState and ResetClass.
ALARM_CLOSED, ALARM_OPEN, ALARM_WAIT_RESET = 0, 1, 2
RESET_AUTO, RESET_MANUAL = 0, 1

ALARM_COLUMNS = (
    ("State", "E_AlarmState: CLOSED 0, ACTIVE 1, WAIT_RESET 2"),
    ("ReasonCode", "the reason; the projection resolves its description"),
    ("Severity", "rationalized priority: LOW 0, MEDIUM 1, HIGH 2"),
    ("ResetClass", "E_ResetClass: AUTO 0, MANUAL 1"),
    ("SourceModuleId", "manifest ModuleId, 1 = the root; resolved to a path"),
    ("ComeDate", "controller clock, yyyymmdd"),
    ("ComeTime", "controller clock, hhmmssmmm"),
    ("GoneDate", "0 until the condition clears"),
    ("GoneTime", "0 until the condition clears"),
    ("ComeScan", "ScanCount at come, for the duration"),
    ("DurationMs", "come to gone, 0 while open"),
    ("IoRoles", "the source module's implicated io_roles, captured at come"),
    ("Shelved", "Core 8.10: annunciation only; control remains authoritative"),
)


def reason_priority(app: decl.Application, name: str) -> int:
    """The rationalized priority of a registered reason - one rule, two users.

    The manifest's Rationalization table and the alarm log both need it, and an
    alarm raised at a severity its own rationalization row contradicts is the
    two-sources drift O9 exists to prevent. The rule itself is
    fraktal_ab_reasons: the registry's for a registered reason, the project
    rule otherwise.
    """
    import fraktal_ab_reasons as reasons

    return reasons.of(app, name).priority


def alarm_active_name() -> str:
    """Framework-shaped, so named for no application (TC3: Fraktal_Core)."""
    return "FRK_T_AlarmActiveV2"


def alarm_ring_name() -> str:
    return "FRK_T_AlarmRingV2"


def alarm_active_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_AlarmActive"


def alarm_ring_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_AlarmRing"


def alarm_active_members() -> tuple[decl.Member, ...]:
    return (
        decl.scalar("SchemaVersion", "", initial=ALARM_SCHEMA),
        decl.scalar("NActive", "events ACTIVE or WAIT_RESET"),
        decl.scalar("RingHead", "1-based slot of the newest closed event, 0 = none"),
        decl.scalar("Blocking", "any MANUAL_RESET event not closed (Core 8.3(b))"),
        decl.scalar("Truncated", "an event could not be recorded: the list was full"),
        decl.scalar("FaultEvt", "1-based slot of the open fault event, 0 = none"),
        decl.scalar("ReportedSeen", "the Unit's ReportedCount already logged"),
        decl.scalar("DegradedSeen", "the profile's DegradedCount already logged"),
        decl.scalar("HealthEvt", "1-based slot of each open §8.12 event, 0 = none",
                    dimension=len(HEALTH_EVENTS)),
        *(decl.scalar(f"Act{name}", comment, dimension=ALARM_ACTIVE)
          for name, comment in ALARM_COLUMNS),
    )


def alarm_ring_members() -> tuple[decl.Member, ...]:
    return (
        decl.scalar("SchemaVersion", "", initial=ALARM_SCHEMA),
        *(decl.scalar(f"Ring{name}", comment, dimension=ALARM_RING)
          for name, comment in ALARM_COLUMNS),
    )


# Core §8.5.1, TC3's PL_Fraktal.MAX_OEE_SAMPLES and OEE_SAMPLE_MS: a one-hour
# ring of one-minute samples. The HMI reads exactly 60 (its sparkline walks the
# ring from OeeTrendHead), so the length is the contract, not a choice here.
OEE_SAMPLES = 60
OEE_SAMPLE_MS = 60000
# What a sample keeps: the accounting itself, not the factors. The factors are
# derived from these by ONE function in the projection, for the live value and
# for every sample alike, so a sample can never disagree with the formula the
# live value uses - and the controller does no division (UDTs are DINT-only
# on v33, and a factor in basis points would be a second formula).
OEE_SAMPLE_COLUMNS = (
    ("Epoch", "the reset epoch it was taken in; another epoch's is not shown"),
    ("RunS", "run seconds since the reset, at the sample"),
    ("RunMs", "and the milliseconds past them"),
    ("DownS", "down seconds since the reset, at the sample"),
    ("DownMs", "and the milliseconds past them"),
    ("Good", "good parts since the reset, at the sample"),
    ("Nok", "NOK parts since the reset, at the sample"),
    ("IdealMs", "the ideal cycle in force at the sample"),
)


def oee_name() -> str:
    return "FRK_T_Oee"


def oee_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_Oee"


def oee_members() -> tuple[decl.Member, ...]:
    """TC3's ST_Oee buckets and OeeTrend ring, as DINT columns.

    Each bucket is whole seconds plus a millisecond remainder: a DINT of
    milliseconds wraps after 24.8 days, and an availability computed across a
    wrap is a confident lie. Seconds last 68 years."""
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.scalar("Epoch", "bumped by RESET_OEE; a sample of another epoch is gone",
                    initial=1),
        decl.scalar("RunS", "BUSY seconds since the reset"),
        decl.duration_ms("RunMs", "and the milliseconds past them"),
        decl.scalar("DownS", "ERROR or blocking-alarm seconds since the reset"),
        decl.duration_ms("DownMs", "and the milliseconds past them"),
        decl.scalar("IdleS", "every other second since the reset"),
        decl.duration_ms("IdleMs", "and the milliseconds past them"),
        decl.scalar("GoodBase", "GoodCount at the reset"),
        decl.scalar("NokBase", "the NOK count at the reset"),
        decl.duration_ms("SampleMs", "time toward the next trend sample"),
        decl.scalar("Head", "1-based slot of the newest sample, 0 = none since the reset"),
        *(decl.scalar(f"Smp{name}", comment, dimension=OEE_SAMPLES)
          for name, comment in OEE_SAMPLE_COLUMNS),
    )


def _oee_ideal(app: decl.Application) -> str:
    """The ideal cycle in force: the running model's ParCfg value, or 0."""
    if not app.ideal_cycle_member:
        return "0"
    return f"{app.records[0].name}Tag.{app.ideal_cycle_member}"


def oee_logic(app: decl.Application) -> list[str]:
    """TC3's _M_OeeUpdate, once per scan: attribute the scan to run, down or
    idle, and push a sample every OEE_SAMPLE_MS.

    After the alarm log, so a blocking alarm raised this scan counts as down
    this scan. The clock is the task period, as every other duration in this
    routine is. The factors are not computed here (OEE_SAMPLE_COLUMNS)."""
    n = app.name
    o, u, a = oee_tag(app), f"FRK_{n}_Unit", alarm_active_tag(app)

    def bucket(name: str) -> list[str]:
        return [f"{o}.{name}Ms := {o}.{name}Ms + {u}.Par_TaskPeriodMs;",
                f"IF {o}.{name}Ms >= 1000 THEN",
                f"{o}.{name}Ms := {o}.{name}Ms - 1000;",
                f"{o}.{name}S := {o}.{name}S + 1;",
                "END_IF;"]

    slot = f"{o}.Head - 1"
    sample = {
        "Epoch": f"{o}.Epoch",
        "RunS": f"{o}.RunS", "RunMs": f"{o}.RunMs",
        "DownS": f"{o}.DownS", "DownMs": f"{o}.DownMs",
        "Good": f"{u}.GoodCount - {o}.GoodBase",
        "Nok": f"{u}.ScrapCount - {o}.NokBase",
        "IdealMs": _oee_ideal(app),
    }
    assert set(sample) == {name for name, _ in OEE_SAMPLE_COLUMNS}
    return [
        "",
        "(* Core 8.5.1: OEE time accounting (TC3 _M_OeeUpdate). BUSY is run;  *)",
        "(* ERROR or a blocking alarm is down; everything else is idle.       *)",
        f"IF {u}.Running <> 0 THEN",
        *bucket("Run"),
        f"ELSIF ({u}.Error <> 0) OR ({a}.Blocking <> 0) THEN",
        *bucket("Down"),
        "ELSE",
        *bucket("Idle"),
        "END_IF;",
        f"{o}.SampleMs := {o}.SampleMs + {u}.Par_TaskPeriodMs;",
        f"IF {o}.SampleMs >= {OEE_SAMPLE_MS} THEN",
        f"{o}.SampleMs := 0;",
        f"{o}.Head := ({o}.Head MOD {OEE_SAMPLES}) + 1;",
        *(f"{o}.Smp{name}[{slot}] := {value};" for name, value in sample.items()),
        "END_IF;",
    ]


def oee_reset_lines(app: decl.Application, *, clear_trend=True) -> list[str]:
    """TC3's ResetOee: the accumulators and the ring. The ring is cleared by
    its epoch, so the reset is one scan's work with no loop; the counts are
    not reset (Core §8.11.2 resets them only on their own logged action), so
    the reset takes a baseline instead and OEE counts the parts made since -
    the time and the parts it divides then cover the same window."""
    o, u = oee_tag(app), f"FRK_{app.name}_Unit"
    return ([f"{o}.Epoch := {o}.Epoch + 1;"] if clear_trend else []) + [
            *(f"{o}.{name} := 0;" for name in (
                "RunS", "RunMs", "DownS", "DownMs", "IdleS", "IdleMs",
                *(['SampleMs', 'Head'] if clear_trend else []))),
            f"{o}.GoodBase := {u}.GoodCount;",
            f"{o}.NokBase := {u}.ScrapCount;"]


# Core §8.11.4, TC3's PL_Fraktal.MAX_PROFILE_STEPS and MAX_CYCLE_HISTORY: a
# cycle's waterfall holds 32 steps, and the trend ring 60 cycles. The HMI reads
# exactly those bounds, so they are the contract.
PROFILE_STEPS = 32
CYCLE_HISTORY = 60
# A duration that would pass this is held here instead: a DINT of ms wraps in
# 24.8 days, and a step that has waited that long is not shorter for wrapping.
PROFILE_SATURATE_MS = 2_000_000_000
# Core §8.11.4(d), TC3's FB_CycleProfiler.DegradedBandPct default: how far WORK
# time may drift above its baseline before it is a maintenance event.
DEGRADED_BAND_PCT = 20


def profiler_name() -> str:
    return "FRK_T_Profiler"


def profiler_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_Profiler"


def profiler_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """TC3's FB_CycleProfiler outputs, as DINT columns.

    The waterfall is double-buffered: the cycle in progress fills one half and
    a completed cycle becomes LastCycle by flipping CurBuf - no 32-step copy.
    Per-step aggregates are indexed by the step's §3.13 chart row, which the
    step's own entry already sets (Chart.StepCursor), so they need no search."""
    classes = len(decl.TIME_CLASSES)
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.boolean("Open", "a step is being timed"),
        decl.scalar("OpenNo", "the step being timed"),
        decl.duration_ms("OpenMs", "how long it has run"),
        decl.duration_ms("OpenExp", "its expected time, as it opened"),
        decl.scalar("OpenCls", "its Core E_TimeClass"),
        decl.scalar("OpenIdx", "its chart row, from its own entry"),
        decl.scalar("Slot", "working: an array position"),
        decl.boolean("CycleOpen", "a cycle is being timed"),
        decl.duration_ms("CycleMs", "how long it has run"),
        decl.scalar("SeenCycles", "the Unit's CycleCount already counted"),
        decl.scalar("CurBuf", "which waterfall half the open cycle fills"),
        decl.scalar("CurN", "steps in it"),
        decl.boolean("CurTrunc", "it had more steps than it holds"),
        decl.duration_ms("CurByClass", "its time by E_TimeClass", dimension=classes),
        decl.scalar("LastCycleNo", "completed cycles; 0 = none yet"),
        decl.scalar("LastN", "steps in the last cycle"),
        decl.boolean("LastTrunc", "the last cycle had more steps than it holds"),
        decl.duration_ms("LastTotal", "the last cycle, start to finish"),
        decl.duration_ms("LastWork", "its WORK time: the real cycle time"),
        decl.duration_ms("LastCycleTime", "Core §8.11.1: the last cycle's time"),
        decl.duration_ms("MinCycleTime", "the shortest cycle since download; 0 = none"),
        decl.scalar("WfStepNo", "waterfall: step", dimension=2 * PROFILE_STEPS),
        decl.duration_ms("WfDurMs", "waterfall: its duration", dimension=2 * PROFILE_STEPS),
        decl.duration_ms("WfExpMs", "waterfall: its expected time",
                         dimension=2 * PROFILE_STEPS),
        decl.scalar("StatCount", "visits closed, by chart row", dimension=app.chart_steps),
        decl.duration_ms("StatLast", "last duration, by chart row", dimension=app.chart_steps),
        decl.duration_ms("StatMin", "shortest, by chart row", dimension=app.chart_steps),
        decl.duration_ms("StatMax", "longest, by chart row", dimension=app.chart_steps),
        decl.duration_ms("StatAvg", "running mean, by chart row", dimension=app.chart_steps),
        decl.scalar("HistoryHead", "1-based slot of the newest cycle; 0 = none"),
        decl.scalar("HisCycleNo", "trend: cycle", dimension=CYCLE_HISTORY),
        decl.duration_ms("HisTotal", "trend: its time", dimension=CYCLE_HISTORY),
        decl.duration_ms("HisWork", "trend: its WORK time", dimension=CYCLE_HISTORY),
        decl.duration_ms("HisByClass", "trend: its time by class, 5 per cycle",
                         dimension=CYCLE_HISTORY * classes),
        decl.boolean("Degraded", "Core 8.11.4(d): the last cycle's WORK time is past the band"),
        decl.duration_ms("DegradedBase", "the baseline the latch was armed against"),
        decl.scalar("DegradedCount", "excursions raised; the alarm log logs each"),
        decl.duration_ms("DegradedWorkMs", "the WORK time that tripped it"),
    )


def _degradation_logic(app: decl.Application) -> list[str]:
    """TC3's degradation watch, at cycle close: WORK time past the baseline by
    more than the band latches once per excursion and counts it; a cycle back
    under the band re-arms it, and so does a new baseline (TC3's
    M_SetBaselineWork). The alarm log turns each count into one maintenance
    event. Integer arithmetic: past baseline + baseline x 20 / 100 is exactly
    TC3's WorkMs x 100 > Baseline x 120 for whole milliseconds."""
    if not app.baseline_work_member:
        return []
    p = profiler_tag(app)
    base = f"{app.records[0].name}Tag.{app.baseline_work_member}"
    work = f"{p}.CurByClass[0]"
    return [
        "(* Core 8.11.4(d): degradation is data, not downtime *)",
        f"IF {base} <> {p}.DegradedBase THEN",
        f"{p}.DegradedBase := {base};",
        f"{p}.Degraded := 0;",
        "END_IF;",
        f"IF {base} > 0 THEN",
        f"IF {work} > ({base} + (({base} * {DEGRADED_BAND_PCT}) / 100)) THEN",
        f"IF {p}.Degraded = 0 THEN",
        f"{p}.Degraded := 1;",
        f"{p}.DegradedCount := {p}.DegradedCount + 1;",
        f"{p}.DegradedWorkMs := {work};",
        "END_IF;",
        "ELSE",
        f"{p}.Degraded := 0;",
        "END_IF;",
        "END_IF;",
    ]


def profiler_logic(app: decl.Application) -> list[str]:
    """TC3's FB_CycleProfiler, fed once per scan from the step record.

    TC3 calls StepChanged from M_Step and CycleComplete at the finish step.
    Here one observer at the end of the routine does both, for every rendition
    alike, from the record each step already writes on entry: Unit.StepScan
    equals this scan exactly when a step was entered this scan, and the chart
    names it (ActiveStepNumber) and its row (StepCursor). An entry closes the
    step before it; the finish marker - the Unit's CycleCount, which each
    rendition counts - closes the open step and the cycle, as CycleComplete
    does. A step that is entered and left in one scan is still seen.

    A cycle the Unit stops inside - a stop, a fault, an abort, a mode change -
    is abandoned, not published: TC3's CycleAbandon, applied wherever the chain
    is stood down, so a fault's downtime never becomes a production cycle."""
    n = app.name
    p, u, c = profiler_tag(app), f"FRK_{n}_Unit", f"FRK_{n}_Chart"
    scan = f"FRK_{n}_ScanCount"
    period, cap = f"{u}.Par_TaskPeriodMs", PROFILE_SATURATE_MS
    classes = len(decl.TIME_CLASSES)
    waits = [(chain.mode_ordinal, step.number, decl.TIME_CLASSES.index(step.time_class))
             for chain in app.chains for step in chain.steps
             if step.time_class != "WORK"]
    idx = f"{p}.OpenIdx"
    close = [
        "(* close the open step: its row, the waterfall, the class split *)",
        f"{p}.StatCount[{idx}] := {p}.StatCount[{idx}] + 1;",
        f"{p}.StatLast[{idx}] := {p}.OpenMs;",
        f"IF ({p}.StatCount[{idx}] = 1) OR ({p}.OpenMs < {p}.StatMin[{idx}]) THEN",
        f"{p}.StatMin[{idx}] := {p}.OpenMs;",
        "END_IF;",
        f"IF {p}.OpenMs > {p}.StatMax[{idx}] THEN",
        f"{p}.StatMax[{idx}] := {p}.OpenMs;",
        "END_IF;",
        "(* TC3's F_TimingUpdate running mean, in its integer arithmetic *)",
        f"{p}.StatAvg[{idx}] := {p}.StatAvg[{idx}] + "
        f"(({p}.OpenMs - {p}.StatAvg[{idx}]) / {p}.StatCount[{idx}]);",
        f"IF {p}.CurN < {PROFILE_STEPS} THEN",
        f"{p}.Slot := ({p}.CurBuf * {PROFILE_STEPS}) + {p}.CurN;",
        f"{p}.WfStepNo[{p}.Slot] := {p}.OpenNo;",
        f"{p}.WfDurMs[{p}.Slot] := {p}.OpenMs;",
        f"{p}.WfExpMs[{p}.Slot] := {p}.OpenExp;",
        f"{p}.CurN := {p}.CurN + 1;",
        "ELSE",
        f"{p}.CurTrunc := 1;",
        "END_IF;",
        f"{p}.CurByClass[{p}.OpenCls] := {p}.CurByClass[{p}.OpenCls] + {p}.OpenMs;",
        f"{p}.Open := 0;",
    ]
    return [
        "",
        "(* Core 8.11.4: the cycle-time profile (TC3 FB_CycleProfiler), fed   *)",
        "(* from the record each step writes on entry, for every rendition.   *)",
        f"IF {u}.Running = 0 THEN",
        "(* stood down inside a cycle: abandoned, never published *)",
        f"{p}.Open := 0;",
        f"{p}.CycleOpen := 0;",
        f"{p}.SeenCycles := {u}.CycleCount;",
        "ELSE",
        f"IF {u}.StepScan = {scan} THEN",
        "(* a step was entered this scan: TC3's StepChanged *)",
        f"IF {p}.Open <> 0 THEN",
        *close,
        "END_IF;",
        f"IF {p}.CycleOpen = 0 THEN",
        "(* the first step opens the cycle (TC3's start marker) *)",
        f"{p}.CycleOpen := 1;",
        f"{p}.CycleMs := 0;",
        f"{p}.CurN := 0;",
        f"{p}.CurTrunc := 0;",
        *(f"{p}.CurByClass[{k}] := 0;" for k in range(classes)),
        "END_IF;",
        f"{p}.Open := 1;",
        f"{p}.OpenNo := {c}.ActiveStepNumber;",
        f"{p}.OpenIdx := {c}.StepCursor;",
        f"{p}.OpenMs := 0;",
        f"{p}.OpenExp := {u}.StepExpectedMs;",
        f"{p}.OpenCls := 0;",
        *(f"IF ({u}.Mode = {mode}) AND ({c}.ActiveStepNumber = {number}) THEN "
          f"{p}.OpenCls := {cls}; END_IF;" for mode, number, cls in waits),
        "END_IF;",
        "(* this scan's time belongs to the step that ran in it *)",
        f"IF ({p}.Open <> 0) AND ({p}.OpenMs < {cap}) THEN",
        f"{p}.OpenMs := {p}.OpenMs + {period};",
        "END_IF;",
        f"IF ({p}.CycleOpen <> 0) AND ({p}.CycleMs < {cap}) THEN",
        f"{p}.CycleMs := {p}.CycleMs + {period};",
        "END_IF;",
        f"IF {u}.CycleCount <> {p}.SeenCycles THEN",
        f"{p}.SeenCycles := {u}.CycleCount;",
        f"IF {p}.CycleOpen <> 0 THEN",
        "(* TC3's CycleComplete: close the finish step, publish the cycle *)",
        f"IF {p}.Open <> 0 THEN",
        *close,
        "END_IF;",
        f"{p}.LastCycleNo := {p}.LastCycleNo + 1;",
        f"{p}.LastN := {p}.CurN;",
        f"{p}.LastTrunc := {p}.CurTrunc;",
        f"{p}.LastTotal := {p}.CycleMs;",
        f"{p}.LastWork := {p}.CurByClass[0];",
        f"{p}.CurBuf := 1 - {p}.CurBuf;",
        f"{p}.LastCycleTime := {p}.CycleMs;",
        f"IF ({p}.MinCycleTime = 0) OR ({p}.CycleMs < {p}.MinCycleTime) THEN",
        f"{p}.MinCycleTime := {p}.CycleMs;",
        "END_IF;",
        f"{p}.HistoryHead := ({p}.HistoryHead MOD {CYCLE_HISTORY}) + 1;",
        f"{p}.Slot := {p}.HistoryHead - 1;",
        f"{p}.HisCycleNo[{p}.Slot] := {p}.LastCycleNo;",
        f"{p}.HisTotal[{p}.Slot] := {p}.CycleMs;",
        f"{p}.HisWork[{p}.Slot] := {p}.CurByClass[0];",
        f"{p}.Slot := {p}.Slot * {classes};",
        *(f"{p}.HisByClass[{p}.Slot + {k}] := {p}.CurByClass[{k}];"
          for k in range(classes)),
        *_degradation_logic(app),
        f"{p}.CycleOpen := 0;",
        "END_IF;",
        "END_IF;",
        "END_IF;",
    ]


def state_flags_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}StateFlags"


def state_flags_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_StateFlags"


def state_flags_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """TC3's StateFlags table, sized to what the application declares: the
    value and the controller-clock moment it last changed. The key is the
    declaration's and the projection's to publish; the controller keeps only
    what changes."""
    n = len(app.state_flags)
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.boolean("Ok", "working: the flag being derived"),
        decl.boolean("Value", "the flag, this scan", dimension=n),
        decl.scalar("SinceDate", "when it last changed, yyyymmdd; 0 = not yet", dimension=n),
        decl.scalar("SinceTime", "when it last changed, hhmmssmmm", dimension=n),
    )


def state_flags_logic(app: decl.Application) -> list[str]:
    """TC3's _M_State, for each declared flag, every scan: derive it from the
    modules, stamp the moment it changes, publish it. Never latched, never
    behind an IF - which is also why AB's flags cannot go Stale.

    One IF per condition rather than one expression: the load-position flag
    alone is six terms, and Studio v33 refuses a sixth operator of a kind."""
    if not app.state_flags:
        return []
    n = app.name
    f = state_flags_tag(app)
    names = Names(app, in_aoi=False)
    lines = ["",
             "(* Core 3.12: derived state flags (TC3 _M_State) - TRUE right now, *)",
             "(* recomputed from the modules every scan, never latched.          *)"]
    for i, flag in enumerate(app.state_flags):
        lines += [f"(* {flag.key} *)", f"{f}.Ok := 1;"]
        lines += [f"IF NOT ({cond_st(condition, names)}) THEN {f}.Ok := 0; END_IF;"
                  for condition in flag.conditions]
        lines += [f"IF ({f}.Value[{i}] <> {f}.Ok) OR ({f}.SinceDate[{i}] = 0) THEN",
                  f"{f}.SinceDate[{i}] := FRK_{n}_NowDate;",
                  f"{f}.SinceTime[{i}] := FRK_{n}_NowTime;",
                  "END_IF;",
                  f"{f}.Value[{i}] := {f}.Ok;"]
    return lines


def alarm_scratch_tags(app: decl.Application) -> dict[str, int]:
    """Working tags for the capture, by name -> dimension (0 = scalar)."""
    n = app.name
    return {f"FRK_{n}_AlmI": 0, f"FRK_{n}_AlmSlot": 0}


def diagnostic_scratch_tag(app: decl.Application) -> str:
    """Whether any module is held this scan."""
    return f"FRK_{app.name}_AnyHeld"


def stall_limit_tag(app: decl.Application) -> str:
    """How long the active step may run unheld before it is stalled."""
    return f"FRK_{app.name}_StallLimitMs"


def clock_tags(app: decl.Application) -> dict[str, int]:
    """The controller clock, read once per scan: raw GSV words, then the date
    and time every stamp in this routine uses."""
    n = app.name
    return {f"FRK_{n}_Clock": 7, f"FRK_{n}_NowDate": 0, f"FRK_{n}_NowTime": 0}


def wall_clock_logic(app: decl.Application) -> list[str]:
    """Read the controller's wall clock once, as two DINTs.

    LINT is transport-only on v33 (S12), and a date plus hhmmssmmm needs no
    calendar arithmetic. Milliseconds subtract the remainder first, so a
    division that rounds cannot turn 999,600 us into a 1000th millisecond.
    """
    clk, nd, nt = tuple(clock_tags(app))
    return [
        "",
        "(* The controller clock, once per scan, for every stamp below *)",
        f"GSV(WallClockTime,,DateTime,{clk}[0]);",
        f"{nd} := {clk}[0] * 10000 + {clk}[1] * 100 + {clk}[2];",
        f"{nt} := {clk}[3] * 10000000 + {clk}[4] * 100000 + {clk}[5] * 1000 "
        f"+ ({clk}[6] - ({clk}[6] MOD 1000)) / 1000;",
    ]


# The window the probe's extremes are taken over, in scans: one second at the
# press's 10 ms. Published at its close, so a reader sees a settled second.
HEALTH_WINDOW_SCANS = 100


def health_probe_name() -> str:
    return "FRK_T_HealthProbe"


def health_probe_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_HealthProbe"


def health_probe_members() -> tuple[decl.Member, ...]:
    """TC3's ST_SystemHealthInput, as far as a Logix controller says it - the
    raw input Core §8.12's publisher evaluates, measured by AB spike S3 before
    anything is evaluated on it."""
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.scalar("Samples", "scans the probe has measured"),
        decl.scalar("PrevMinuteUs", "the last scan's second x 10^6 + us"),
        decl.scalar("NowMinuteUs", "working: this scan's"),
        decl.duration_ms("IntervalUs", "the task's real period, last scan, us"),
        decl.duration_ms("JitterUs", "its distance from the declared period, us"),
        decl.scalar("WinScans", "scans into the current window"),
        decl.duration_ms("WinMaxIntervalUs", "working: this window's longest period"),
        decl.duration_ms("WinMinIntervalUs", "working: this window's shortest period"),
        decl.duration_ms("WinMaxJitterUs", "working: this window's largest jitter"),
        decl.duration_ms("MaxIntervalUs", "the last full window's longest period, us"),
        decl.duration_ms("MinIntervalUs", "the last full window's shortest period, us"),
        decl.duration_ms("MaxJitterUs", "the last full window's largest jitter, us"),
        decl.duration_ms("TaskLastScanUs", "GSV TASK LastScanTime: execution, us"),
        decl.duration_ms("TaskMaxScanUs", "GSV TASK MaxScanTime, us"),
        decl.scalar("TaskOverlapCount", "GSV TASK OverlapCount: overruns"),
        decl.boolean("TimeIsSynchronized", "GSV TimeSynchronize IsSynchronized"),
        decl.boolean("TimePtpEnable", "GSV TimeSynchronize PTPEnable"),
        decl.scalar("MinorFaultBits", "GSV FaultLog MinorFaultBits"),
        decl.scalar("MajorFaultBits", "GSV FaultLog MajorFaultBits"),
    )


def health_probe_logic(app: decl.Application) -> list[str]:
    """Core §8.12's input, read once per scan - TC3's FB_TcSystemHealthProbe.

    The task's own figures come from the TASK, TimeSynchronize and FaultLog
    objects. Its real period and jitter come from the wall clock this routine
    already reads, as TC3's probe takes them from its monotonic clock: the
    distance between two scans' readings, against the declared period. Every
    GSV here is DINT-typed, and Part III marks them PROVISIONAL S3 until the
    controller has answered for them."""
    p, task = health_probe_tag(app), app.task_name
    clk = next(iter(clock_tags(app)))
    expected = app.task_period_ms * 1000
    return [
        "",
        "(* Core 8.12 controller health probe (TC3 FB_TcSystemHealthProbe); AB S3 *)",
        f"GSV(TASK,{task},LastScanTime,{p}.TaskLastScanUs);",
        f"GSV(TASK,{task},MaxScanTime,{p}.TaskMaxScanUs);",
        f"GSV(TASK,{task},OverlapCount,{p}.TaskOverlapCount);",
        f"GSV(TimeSynchronize,,IsSynchronized,{p}.TimeIsSynchronized);",
        f"GSV(TimeSynchronize,,PTPEnable,{p}.TimePtpEnable);",
        f"GSV(FaultLog,,MinorFaultBits,{p}.MinorFaultBits);",
        f"GSV(FaultLog,,MajorFaultBits,{p}.MajorFaultBits);",
        f"{p}.NowMinuteUs := ({clk}[5] * 1000000) + {clk}[6];",
        f"IF {p}.Samples > 0 THEN",
        f"{p}.IntervalUs := {p}.NowMinuteUs - {p}.PrevMinuteUs;",
        f"IF {p}.IntervalUs < 0 THEN {p}.IntervalUs := {p}.IntervalUs + 60000000; END_IF;",
        f"IF {p}.IntervalUs >= {expected} THEN",
        f"{p}.JitterUs := {p}.IntervalUs - {expected};",
        "ELSE",
        f"{p}.JitterUs := {expected} - {p}.IntervalUs;",
        "END_IF;",
        f"IF {p}.WinScans = 0 THEN",
        f"{p}.WinMaxIntervalUs := {p}.IntervalUs;",
        f"{p}.WinMinIntervalUs := {p}.IntervalUs;",
        f"{p}.WinMaxJitterUs := {p}.JitterUs;",
        "ELSE",
        f"IF {p}.IntervalUs > {p}.WinMaxIntervalUs THEN {p}.WinMaxIntervalUs := {p}.IntervalUs; END_IF;",
        f"IF {p}.IntervalUs < {p}.WinMinIntervalUs THEN {p}.WinMinIntervalUs := {p}.IntervalUs; END_IF;",
        f"IF {p}.JitterUs > {p}.WinMaxJitterUs THEN {p}.WinMaxJitterUs := {p}.JitterUs; END_IF;",
        "END_IF;",
        f"{p}.WinScans := {p}.WinScans + 1;",
        f"IF {p}.WinScans >= {HEALTH_WINDOW_SCANS} THEN",
        f"{p}.MaxIntervalUs := {p}.WinMaxIntervalUs;",
        f"{p}.MinIntervalUs := {p}.WinMinIntervalUs;",
        f"{p}.MaxJitterUs := {p}.WinMaxJitterUs;",
        f"{p}.WinScans := 0;",
        "END_IF;",
        "END_IF;",
        f"{p}.PrevMinuteUs := {p}.NowMinuteUs;",
        f"IF {p}.Samples < 2000000000 THEN {p}.Samples := {p}.Samples + 1; END_IF;",
    ]


# Core §8.12's events, in TC3's order, for the groups a Logix controller has
# (AB S3). CPU, memory, IPC temperature, fan and storage have no source here:
# their conditions cannot become true, so they are not emitted.
HEALTH_EVENTS = ("TASK_OVERRUN", "TASK_JITTER_HIGH", "CONTROLLER_METRICS_UNAVAILABLE",
                 "FIELDBUS_MASTER_FAULT", "DC_SYNC_LOST", "TIME_SYNC_LOST")
HEALTH_SCHEMA = 1                         # TC3's ST_SystemHealthParCfg.SchemaVersion


def health_cfg_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}HealthCfg"


def health_cfg_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_HealthCfg"


def health_cfg_members(app: decl.Application) -> tuple[decl.Member, ...]:
    """TC3's ST_SystemHealthParCfg, schema-first, with the station's values
    as the tag's initial data."""
    h = app.system_health
    return (
        decl.scalar("SchemaVersion", "which health contract this is", initial=HEALTH_SCHEMA),
        decl.duration_ms("MaxTaskCycleUs", "a longer real period is an overrun, us",
                         initial=h.max_task_cycle_us),
        decl.duration_ms("MaxTaskJitterUs", "more jitter than this is high, us",
                         initial=h.max_task_jitter_us),
        decl.boolean("RequireTimeSync", "the station needs a synchronized clock",
                     initial=int(h.require_time_sync)),
        decl.boolean("RequireFieldbus", "the station needs a fieldbus",
                     initial=int(h.require_fieldbus)),
        decl.boolean("RequireDcSync", "the station needs a synchronized distributed clock",
                     initial=int(h.require_dc_sync)),
    )


def system_health_name() -> str:
    return "FRK_T_SystemHealth"


def system_health_tag(app: decl.Application) -> str:
    return f"FRK_{app.name}_SystemHealth"


def system_health_members() -> tuple[decl.Member, ...]:
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.boolean("Present", "the thresholds are valid: health is evaluated"),
        decl.boolean("Healthy", "evaluated, and no condition is bad"),
        decl.boolean("TaskAvailable", "the task's period has been measured"),
        decl.boolean("TaskOverrun", "OverlapCount moved this scan"),
        decl.scalar("SeenOverlap", "the OverlapCount already counted"),
        decl.boolean("Bad", "each HEALTH_EVENTS condition, this scan",
                      dimension=len(HEALTH_EVENTS)),
    )


def system_health_logic(app: decl.Application) -> list[str]:
    """TC3's FB_SystemHealthPublisher.Cyclic over the S3 subset, once per scan.

    Nothing is evaluated on the probe's first sample, as TC3's MAIN skips the
    sample with no prior scan to take a period from: a download never raises a
    false overrun. CONTROLLER_METRICS_UNAVAILABLE is TC3's rule, unchanged:
    a station whose CPU and memory cannot be read says so, as TC3's own press
    does outside simulation."""
    if app.system_health is None:
        return []
    h, p, c = system_health_tag(app), health_probe_tag(app), health_cfg_tag(app)
    k = {name: i for i, name in enumerate(HEALTH_EVENTS)}
    bad = lambda name: f"{h}.Bad[{k[name]}]"
    return [
        "",
        "(* Core 8.12 system health (TC3 FB_SystemHealthPublisher), S3's subset *)",
        f"{h}.Present := 0;",
        f"IF ({c}.SchemaVersion = {HEALTH_SCHEMA}) AND ({c}.MaxTaskCycleUs > 0) "
        f"AND ({c}.MaxTaskJitterUs > 0) THEN {h}.Present := 1; END_IF;",
        f"{h}.TaskAvailable := 0;",
        f"IF {p}.Samples > 1 THEN {h}.TaskAvailable := 1; END_IF;",
        f"IF {p}.Samples <= 1 THEN {h}.SeenOverlap := {p}.TaskOverlapCount; END_IF;",
        f"{h}.TaskOverrun := 0;",
        f"IF {p}.TaskOverlapCount <> {h}.SeenOverlap THEN",
        f"{h}.TaskOverrun := 1;",
        f"{h}.SeenOverlap := {p}.TaskOverlapCount;",
        "END_IF;",
        *(f"{bad(name)} := 0;" for name in HEALTH_EVENTS),
        f"IF ({h}.Present <> 0) AND ({h}.TaskAvailable <> 0) THEN",
        f"IF ({h}.TaskOverrun <> 0) OR ({p}.IntervalUs > {c}.MaxTaskCycleUs) THEN "
        f"{bad('TASK_OVERRUN')} := 1; END_IF;",
        f"IF {p}.JitterUs > {c}.MaxTaskJitterUs THEN {bad('TASK_JITTER_HIGH')} := 1; END_IF;",
        "(* no CPU load or free memory through GSV on this controller (S3) *)",
        f"{bad('CONTROLLER_METRICS_UNAVAILABLE')} := 1;",
        "(* local I/O, no fieldbus or distributed clock here: bad only if required *)",
        f"IF {c}.RequireFieldbus <> 0 THEN {bad('FIELDBUS_MASTER_FAULT')} := 1; END_IF;",
        f"IF {c}.RequireDcSync <> 0 THEN {bad('DC_SYNC_LOST')} := 1; END_IF;",
        f"IF ({c}.RequireTimeSync <> 0) AND ({p}.TimeIsSynchronized = 0) THEN "
        f"{bad('TIME_SYNC_LOST')} := 1; END_IF;",
        "END_IF;",
        "(* healthy only once evaluated: never on a sample nothing was judged on *)",
        f"{h}.Healthy := 0;",
        f"IF ({h}.Present <> 0) AND ({h}.TaskAvailable <> 0) THEN {h}.Healthy := 1; END_IF;",
        *(f"IF {bad(name)} <> 0 THEN {h}.Healthy := 0; END_IF;" for name in HEALTH_EVENTS),
    ]


def implicated_roles(app: decl.Application, source: str, dest: str) -> list[str]:
    """Copy the io_roles the numbered module implicates right now into `dest`.

    Called on the scan a fault is adopted or reported, which is the scan the
    child raised it: the chain drops the child's Execute, but the child's AOI
    does not run again until the next scan, so its reason and roles are still
    the ones that caused this. One rule for the Unit's diagnostic and the log.
    """
    lines = [f"CASE {source} OF"]
    for module in app.modules:
        lines.append(f"{module_source(app, module.name)}: "
                     f"{dest} := {ctx_tag_for(app, module.name)}.OutImm_IoRoles;")
    return lines + ["ELSE", f"{dest} := 0;", "END_CASE;"]


def severity_case(app: decl.Application, reason: str, dest: str) -> list[str]:
    """The rationalized priority of `reason` into `dest` (reason_priority).
    A code this station never registered is still a fault, and an alarm that
    quietly rated itself LOW would be the dangerous way to be wrong."""
    lines = [f"CASE {reason} OF"]
    priorities: dict[int, list[int]] = {}
    for name, code in sorted(app.reasons.items(), key=lambda item: item[1]):
        priorities.setdefault(reason_priority(app, name), []).append(code)
    for priority, codes in priorities.items():
        labels = ','.join(str(code) for code in codes)
        lines.append(f"{labels}: {dest} := {priority};")
    return lines + ["ELSE", f"{dest} := {SEVERITY_HIGH};", "END_CASE;"]


def diagnostic_logic(app: decl.Application) -> list[str]:
    """Core §6.9(a) and §2.7: the Unit's one diagnostic, and when each began.

    TC3's base computes `Status.Diagnostic` once and stamps `Since` where the
    fault is raised. Here the Unit's reason is chosen on the controller - an
    adopted fault, else the held reason - so the stamp and the published
    reason cannot disagree, and each module's reason is stamped on the scan it
    changed. An adopted fault keeps the child's implicated I/O, as TC3's
    verbatim copy of the child's diagnostic does.
    """
    n = app.name
    u, nd, nt = f"FRK_{n}_Unit", f"FRK_{n}_NowDate", f"FRK_{n}_NowTime"
    contexts = [ctx_tag_for(app, m.name) for m in app.modules]
    any_held = diagnostic_scratch_tag(app)
    limit = stall_limit_tag(app)
    cfg = f"{app.records[0].name}Tag"
    expected = [(chain.mode_ordinal, step.number, decl.expected_member(step))
                for chain in app.chains for step in chain.steps
                if decl.expected_member(step)]
    lines = [
        "",
        "(* Core 6.9: the stall watchdog, TC3's _tStall. A hold is a declared *)",
        "(* wait, not a stall, so any hold disarms it; a step change restarts it. *)",
        # One IF per holder, never one OR per holder: Studio v33 rejects an
        # expression with six ORs ("Too many 'OR' operators in expression"),
        # and this list grows with every module an application declares.
        f"{any_held} := 0;",
        *(f"IF {ctx}.OutImm_Held <> 0 THEN {any_held} := 1; END_IF;"
          for ctx in contexts),
        f"IF ({u}.Running <> 0) AND ({u}.Error = 0) AND ({any_held} = 0) "
        f"AND ({u}.Step = {u}.StallStep) THEN",
        f"{u}.StallMs := {u}.StallMs + {u}.Par_TaskPeriodMs;",
        "ELSE",
        f"{u}.StallMs := 0;",
        "END_IF;",
        f"{u}.StallStep := {u}.Step;",
        "(* TC3 times a step against its ExpectedTime when it states one, else *)",
        "(* StallTime. A step that takes exactly its expected time is seen to *)",
        "(* finish one scan later, so it has that scan before it is stalled. *)",
        f"{u}.StepExpectedMs := 0;",
        *(f"IF ({u}.Mode = {mode}) AND ({u}.Step = {number}) THEN "
          f"{u}.StepExpectedMs := {cfg}.{member}; END_IF;"
          for mode, number, member in expected),
        f"IF {u}.StepExpectedMs > 0 THEN",
        f"{limit} := {u}.StepExpectedMs + {u}.Par_TaskPeriodMs;",
        "ELSE",
        f"{limit} := {u}.StallTimeMs;",
        "END_IF;",
        f"IF ({limit} > 0) AND ({u}.StallMs >= {limit}) THEN",
        f"{u}.StepTimedOut := 1;",
        "ELSE",
        f"{u}.StepTimedOut := 0;",
        "END_IF;",
        "(* Core 6.9(a): the Unit's one diagnostic, in TC3's order - an adopted *)",
        "(* fault, the first held child (_M_RollupHold), a stall. *)",
        f"IF {u}.Error <> 0 THEN",
        f"{u}.DiagReason := {u}.ErrorID;",
        *[line for ctx in contexts for line in (
            f"ELSIF ({u}.Running <> 0) AND ({ctx}.OutImm_Held <> 0) THEN",
            f"{u}.DiagReason := {ctx}.OutImm_Reason;")],
        f"ELSIF {u}.StepTimedOut <> 0 THEN",
        f"{u}.DiagReason := {app.reasons['STEP_STALLED']};",
        "ELSE",
        f"{u}.DiagReason := 0;",
        "END_IF;",
        f"IF {u}.DiagReason <> {u}.DiagStamped THEN",
        f"{u}.DiagStamped := {u}.DiagReason;",
        f"{u}.DiagSinceDate := {nd};",
        f"{u}.DiagSinceTime := {nt};",
        f"IF {u}.Error <> 0 THEN",
        *implicated_roles(app, f"{u}.ErrorSource", f"{u}.DiagIoRoles"),
        "ELSE",
        f"{u}.DiagIoRoles := 0;",
        "END_IF;",
        "END_IF;",
    ]
    for module in app.modules:
        ctx = ctx_tag_for(app, module.name)
        lines += [
            f"IF {ctx}.OutImm_Reason <> {ctx}.DiagStamped THEN",
            f"{ctx}.DiagStamped := {ctx}.OutImm_Reason;",
            f"{ctx}.DiagSinceDate := {nd};",
            f"{ctx}.DiagSinceTime := {nt};",
            "END_IF;",
        ]
    return lines


def alarm_service_name(app: decl.Application, operation: str) -> str:
    return f'FRK_{app.name}_Alarm{operation}'


def alarm_open_logic(app: decl.Application) -> list[str]:
    """Allocate and initialize one active event; caller supplies its identity."""
    import fraktal_ab_shelving as shelving
    n = app.name
    a, i, s = alarm_active_tag(app), f'FRK_{n}_AlmI', f'FRK_{n}_AlmSlot'
    return [f'{s} := -1;', f'FOR {i} := 0 TO {ALARM_ACTIVE - 1} DO',
            f'IF ({s} < 0) AND ({a}.ActState[{i}] = {ALARM_CLOSED}) THEN {s} := {i}; END_IF;',
            'END_FOR;', f'IF {s} < 0 THEN', f'{a}.Truncated := 1;', 'ELSE',
            f'{a}.ActState[{s}] := {ALARM_OPEN};',
            f'{a}.ActComeDate[{s}] := FRK_{n}_NowDate;',
            f'{a}.ActComeTime[{s}] := FRK_{n}_NowTime;',
            f'{a}.ActGoneDate[{s}] := 0;', f'{a}.ActGoneTime[{s}] := 0;',
            f'{a}.ActComeScan[{s}] := FRK_{n}_ScanCount;', f'{a}.ActDurationMs[{s}] := 0;',
            *shelving.clear(app, s), f'{a}.NActive := {a}.NActive + 1;', 'END_IF;']


def alarm_close_logic(app: decl.Application) -> list[str]:
    """Copy the selected active event into the ring and release its slot."""
    a, r = alarm_active_tag(app), alarm_ring_tag(app)
    slot, head = f'FRK_{app.name}_AlmSlot', f'{a}.RingHead - 1'
    return [f'{a}.RingHead := ({a}.RingHead MOD {ALARM_RING}) + 1;',
            *(f'{r}.Ring{name}[{head}] := {a}.Act{name}[{slot}];'
              for name, _ in ALARM_COLUMNS if name != 'State'),
            f'{r}.RingState[{head}] := {ALARM_CLOSED};',
            f'{a}.ActState[{slot}] := {ALARM_CLOSED};',
            f'{a}.NActive := {a}.NActive - 1;']


def alarm_service_routines(app: decl.Application) -> list[tuple[str, list[str]]]:
    return [(alarm_service_name(app, 'Open'), alarm_open_logic(app)),
            (alarm_service_name(app, 'Close'), alarm_close_logic(app))]


def alarm_log_logic(app: decl.Application) -> list[str]:
    """Core §8.3(c) fault capture, as TC3's FB_UnitBase does it, line for line.

    TC3 captures at the UNIT: ERROR entry raises one MANUAL_RESET event whose
    source is the module the rollup adopted, ERROR exit marks it gone - which
    for a manual event means WAIT_RESET, still blocking a restart. An operator
    reset closes WAIT_RESET events AND active manual ones (TC3 §76, the fault
    hard-lock): a still-live cause is simply re-raised on the next scan, because
    the owner's capture sees ERROR with no open event. A HELD condition is not
    an alarm, in TC3 or here.

    Runs in the routine after the Unit AOI, so Error, ErrorID and ErrorSource
    are this scan's. The reset close reads ResetRequest, which the mailbox
    raised at the top of this same scan.
    """
    import fraktal_ab_shelving as shelving
    n = app.name
    a, r, u = alarm_active_tag(app), alarm_ring_tag(app), f"FRK_{n}_Unit"
    nd, nt = f"FRK_{n}_NowDate", f"FRK_{n}_NowTime"
    i, s, scan = f"FRK_{n}_AlmI", f"FRK_{n}_AlmSlot", f"FRK_{n}_ScanCount"
    last = ALARM_ACTIVE - 1

    def gone_stamp(slot: str) -> list[str]:
        return [
            f"{a}.ActGoneDate[{slot}] := {nd};",
            f"{a}.ActGoneTime[{slot}] := {nt};",
            f"{a}.ActDurationMs[{slot}] := ({scan} - {a}.ActComeScan[{slot}]) "
            f"* {u}.Par_TaskPeriodMs;",
        ]

    head = f"{a}.RingHead - 1"

    def raise_into(slot_holder: str, reason: str, severity: list[str],
                   reset_class: int, source: str, roles: list[str]) -> list[str]:
        """Open an event in the first closed active slot, or say the list is
        full - never overwrite an open one. One body for every held event."""
        return [
            f'JSR({alarm_service_name(app, "Open")},0);',
            f'IF {s} >= 0 THEN',
            f"{a}.ActReasonCode[{s}] := {reason};",
            *severity,
            f"{a}.ActResetClass[{s}] := {reset_class};",
            f"{a}.ActSourceModuleId[{s}] := {source};",
            *roles,
            f"{slot_holder} := {s} + 1;",
            "END_IF;",
        ]

    def close_into_ring(slot: str) -> list[str]:
        """Move a closed-out active event into the ring, newest first."""
        return ([f'{s} := {slot};'] if slot != s else []) + [
            f'JSR({alarm_service_name(app, "Close")},0);']

    held: list[str] = []
    if app.system_health is not None:
        hs = system_health_tag(app)
        held.append("(* 8.12: each health condition is an AUTO_RESET event while it "
                    "lasts - raised once, closed into the ring when it clears *)")
        for index, name in enumerate(HEALTH_EVENTS):
            slot_holder = f"{a}.HealthEvt[{index}]"
            held += [
                f"IF {hs}.Bad[{index}] <> 0 THEN",
                f"IF {slot_holder} = 0 THEN",
                *raise_into(slot_holder, str(app.reasons[name]),
                            [f"{a}.ActSeverity[{s}] := {reason_priority(app, name)};"],
                            RESET_AUTO, "1", [f"{a}.ActIoRoles[{s}] := 0;"]),
                "END_IF;",
                f"ELSIF {slot_holder} > 0 THEN",
                f"{s} := {slot_holder} - 1;",
                *gone_stamp(s),
                *close_into_ring(s),
                f"{slot_holder} := 0;",
                "END_IF;",
            ]

    def occurrence(reason: str, severity: list[str], source: str,
                   roles: list[str]) -> list[str]:
        """One AUTO_RESET event, come and gone at once, straight to the ring:
        an occurrence that can never block a start."""
        return [
            f"{a}.RingHead := ({a}.RingHead MOD {ALARM_RING}) + 1;",
            f"{r}.RingState[{head}] := {ALARM_CLOSED};",
            f"{r}.RingReasonCode[{head}] := {reason};",
            *severity,
            f"{r}.RingResetClass[{head}] := {RESET_AUTO};",
            f"{r}.RingSourceModuleId[{head}] := {source};",
            f"{r}.RingComeDate[{head}] := {nd};",
            f"{r}.RingComeTime[{head}] := {nt};",
            f"{r}.RingGoneDate[{head}] := {nd};",
            f"{r}.RingGoneTime[{head}] := {nt};",
            f"{r}.RingComeScan[{head}] := {scan};",
            f"{r}.RingDurationMs[{head}] := 0;",
            f"{r}.RingShelved[{head}] := 0;",
            *roles,
        ]

    degraded: list[str] = []
    if app.baseline_work_member:
        p = profiler_tag(app)
        code = app.reasons["CYCLE_TIME_DEGRADED"]
        degraded = [
            "(* 8.11.4(d): a degradation excursion is a maintenance occurrence,",
            "   LOW, from the Unit - data, never downtime *)",
            f"IF {p}.DegradedCount <> {a}.DegradedSeen THEN",
            f"{a}.DegradedSeen := {p}.DegradedCount;",
            *occurrence(str(code),
                        [f"{r}.RingSeverity[{head}] := "
                         f"{reason_priority(app, 'CYCLE_TIME_DEGRADED')};"],
                        "1", [f"{r}.RingIoRoles[{head}] := 0;"]),
            "END_IF;",
        ]
    return [
        "",
        "(* Core 8.3 alarm log: fault capture, as TC3's FB_UnitBase *)",
        f"{a}.SchemaVersion := {ALARM_SCHEMA};",
        f"{r}.SchemaVersion := {ALARM_SCHEMA};",
        *shelving.cyclic(app),
        "(* 8.3(c): ERROR entry raises *)",
        f"IF ({u}.Error <> 0) AND ({a}.FaultEvt = 0) THEN",
        # ErrorSource counts modules from 1; ModuleId counts the root as 1. One
        # expression maps both: a Unit's own fault (0) is the root (1).
        *raise_into(f"{a}.FaultEvt", f"{u}.ErrorID",
                    severity_case(app, f"{u}.ErrorID", f"{a}.ActSeverity[{s}]"),
                    RESET_MANUAL, f"{u}.ErrorSource + 1",
                    implicated_roles(app, f"{u}.ErrorSource", f"{a}.ActIoRoles[{s}]")),
        "(* ERROR exit: a manual event goes WAIT_RESET and keeps blocking *)",
        f"ELSIF ({u}.Error = 0) AND ({a}.FaultEvt > 0) THEN",
        f"{s} := {a}.FaultEvt - 1;",
        f"IF {a}.ActState[{s}] = {ALARM_OPEN} THEN",
        *gone_stamp(s),
        f"{a}.ActState[{s}] := {ALARM_WAIT_RESET};",
        "END_IF;",
        f"{a}.FaultEvt := 0;",
        "END_IF;",
        "(* 6.9(e): a report is an occurrence - AUTO_RESET, come and gone at",
        "   once - so it goes straight to the ring and can never block a start *)",
        f"IF {u}.ReportedCount <> {a}.ReportedSeen THEN",
        f"{a}.ReportedSeen := {u}.ReportedCount;",
        *occurrence(f"{u}.ReportedReason",
                    severity_case(app, f"{u}.ReportedReason", f"{r}.RingSeverity[{head}]"),
                    f"{u}.ReportedSource + 1",
                    implicated_roles(app, f"{u}.ReportedSource", f"{r}.RingIoRoles[{head}]")),
        "END_IF;",
        *degraded,
        *held,
        "(* Operator reset: WAIT_RESET and active manual events close (TC3 76) *)",
        f"IF FRK_{n}_ResetRequest <> 0 THEN",
        f"FOR {i} := 0 TO {last} DO",
        f"IF ({a}.ActState[{i}] = {ALARM_WAIT_RESET}) OR "
        f"(({a}.ActState[{i}] = {ALARM_OPEN}) AND "
        f"({a}.ActResetClass[{i}] = {RESET_MANUAL})) THEN",
        f"IF {a}.ActState[{i}] = {ALARM_OPEN} THEN",
        *gone_stamp(i),
        "END_IF;",
        *close_into_ring(i),
        f"IF {a}.FaultEvt = {i} + 1 THEN {a}.FaultEvt := 0; END_IF;",
        "END_IF;",
        "END_FOR;",
        "END_IF;",
        "(* 8.3(b): any manual event not closed blocks a restart *)",
        f"{a}.Blocking := 0;",
        f"FOR {i} := 0 TO {last} DO",
        f"IF ({a}.ActResetClass[{i}] = {RESET_MANUAL}) AND "
        f"({a}.ActState[{i}] <> {ALARM_CLOSED}) THEN {a}.Blocking := 1; END_IF;",
        "END_FOR;",
    ]


def config_restore_logic(app: decl.Application) -> list[str]:
    """Core §3.8a restore: fail-closed at startup, and never silent.

    Runs on the first scan only, before anything reads a configured value.

    The three cases are distinguished by the stored SchemaVersion, and the
    reason that works on Logix is that a DOWNLOAD resets a tag to the initial
    value in the L5X. A StationCfg declares that initial as ZERO (validated in
    the declaration), so:

      0            never written. A first boot has lost nothing, so the
                   declared defaults are installed SILENTLY and stamped with
                   the current contract version. The next boot is an ordinary
                   restore.
      the declared the commissioned image is intact. Nothing is touched.
      anything else a real image was rejected. The declared defaults are
                   installed and RestoreLost is raised, because the difference
                   between an empty machine and one that has just lost its
                   commissioning is exactly what an operator needs told.

    What this does NOT do is claim the image will survive. Whether a written
    tag outlives a power cycle is a property of controller memory and its
    nonvolatile medium, which AB Part III §3.8b marks [PROVISIONAL] pending a
    measured retention matrix. The mechanism is correct either way; the claim
    is not made here.
    """
    record = station_cfg_record(app)
    persist = config_persist_tag(app)
    lines = [
        "(* Core §3.8a restore - first scan, fail-closed, never silent *)",
        f"{persist}.SchemaVersion := {SCHEMA_VERSION};",
        f"{persist}.RestorePolicy := {CONFIG_RESTORE_DEFAULTS_AND_ANNUNCIATE};",
        # A declaration without parameter sets advertises local retention only.
        *([] if app.config_sets else [f"{persist}.StorePresent := 0;",
                                     f"{persist}.StoreKind := {CONFIG_STORE_LOCAL_RETAIN};"]),
        # S:FS, not `ScanCount = 0`. ScanCount is an ordinary controller tag:
        # it is zero after a DOWNLOAD, which made the gate look right on the
        # bench, but a POWER CYCLE resumes it at whatever it had reached — so
        # the gate would never have run on the one event it exists for. S:FS is
        # true on the first scan after entering Run, whichever way the
        # controller got there, and it does not depend on the retention
        # question that Part III §3.8b still owes a spike on.
        "IF S:FS THEN",
        # A loss is decided ONCE per start: cleared here, and only ever RAISED
        # by the restores below. Clearing it anywhere else is how a second
        # record's verdict overwrote the first's - the old no-StationCfg branch
        # wrote 0 every scan and would have wiped a model loss the moment it was
        # raised. A new loss also needs a new acknowledgement, as TC3 does.
        f"{persist}.RestoreLost := 0;",
        f"{persist}.RestoreAcknowledged := 0;",
        f"{persist}.LostModuleId := 0;",
    ]
    if record is not None:
        # With live documents the station image is not stamped here: version
        # zero is the derived "restoring" state until the gateway's restore
        # answers through the staged set path (config_restoring).
        lines += _restore_gate(
            f"{record.name}Tag", record.schema_version,
            [(m.name, m.initial) for m in record.members
             if m.name != decl.SCHEMA_VERSION_MEMBER],
            persist, label="StationCfg",
            stamp=0 if decl.live_documents(app) else record.schema_version)
    lines += _model_restore_logic(app, persist)
    lines.append("END_IF;")
    return lines


def _restore_gate(tag: str, version: int, defaults: list[tuple[str, int]],
                  persist: str, label: str, stamp: int | None = None) -> list[str]:
    """Core §3.8a's three cases for ONE retained image.

    Written once and used for every record, because the model elements first
    shipped with only the zero case: an element carrying an unrecognized
    version was kept and driven as-is, which §3.8a forbids in so many words -
    "shall not be interpreted by field position". Two copies of this rule is
    how one of them came to be missing a branch.

      0             never written. Declared values, silently.
      the declared  intact. Nothing is touched, and there is no ELSE: a branch
                    that "restored" a matching image would overwrite the
                    machine with the program's idea of itself every boot.
      anything else rejected. Declared values, and SAY SO.

    `stamp` is the version the installed values are marked with: the declared
    one, or zero for a station image whose live documents are still to come.
    """
    install = [f"{tag}.{name} := {value};" for name, value in defaults]
    stamp = f"{tag}.{decl.SCHEMA_VERSION_MEMBER} := {version if stamp is None else stamp};"
    return [
        f"(* {label} *)",
        f"IF {tag}.{decl.SCHEMA_VERSION_MEMBER} <> {version} THEN",
        f"IF {tag}.{decl.SCHEMA_VERSION_MEMBER} <> 0 THEN",
        f"{persist}.RestoreLost := 1;",
        f"{persist}.LostModuleId := 1;",
        "END_IF;",
        *install,
        stamp,
        "END_IF;",
    ]


def _model_restore_logic(app: decl.Application, persist: str) -> list[str]:
    """Core 3.8a restore for each model's stored values.

    Same gate as the station record and for the same reason: zero is "never
    written" and is what a download leaves behind, so a fresh controller
    installs each model's declared numbers and a commissioned one keeps what
    it was given. Unrolled per element rather than looped because the declared
    values differ per model - there is nothing to loop over.
    """
    scoped = model_scoped_members(app)
    if not scoped:
        return []
    array = model_cfg_tag(app)
    version = model_cfg_schema_version(app)
    lines: list[str] = []
    for index, model in enumerate(app.models):
        lines += _restore_gate(
            f"{array}[{index}]", version,
            [(m.name, model.values.get(m.name, 0)) for m in scoped],
            persist, label=f"model {model.code}")
    if app.model_capacity:
        import fraktal_ab_models as models
        lines += models.restore(app, persist)
    return lines


def model_cfg_schema_version(app: decl.Application) -> int:
    """The contract version of a model element: its ParCfg record's.

    One source. A model element holds a subset of the ParCfg record's values
    and means what they mean, so a change to what those values mean is a
    change to both - which a separately numbered model version could forget.
    It was a literal 1 before, which is how the per-model restore first
    shipped unable to recognize an image it should have rejected.
    """
    par_cfg = next((r for r in app.records if r.par_cfg), None)
    return par_cfg.schema_version if par_cfg is not None else 1


def scan_sections(app: decl.Application) -> list[tuple[str | None, tuple[str, ...]]]:
    """One ordered scan plan for both the emitted caller and its inline oracle.

    Sections own complete blocks and share controller/program scope. Moving
    them behind JSR changes neither scan order nor the tags any block sees.
    Never extract a RETURN/EXIT across a routine/loop boundary.
    """
    n = app.name
    import fraktal_ab_access as access
    import fraktal_ab_mailbox_frame as frame
    sections = []

    def add(suffix, body):
        if body:
            name = f'FRK_{n}_Scan{suffix}' if suffix else None
            sections.append((name, tuple(body)))

    if app.access_users is not None:
        add('AccessStartup', access.startup(app))
    add(None, [
        # The mailbox runs before anything else reads a request tag, so a
        # command lands in the scan it was committed in rather than the next.
        f"JSR({frame.routine_name(app)},0);",
        f"JSR({mailbox.routine_name(app)},0);",
    ])
    add('ConfigRestore', [
        # Before the increment, so `ScanCount = 0` is genuinely the first scan,
        # and before any module runs so nothing reads a value that is about to
        # be replaced by its default.
        *config_restore_logic(app),
        *(line.restore_logic(app) if app.line is not None else []),
    ])
    add(None, [
        f"FRK_{n}_ScanCount := FRK_{n}_ScanCount + 1;",
        f"FRK_{n}_TaskPeriodMs := {app.task_period_ms};",
    ])
    modules = ["(* Every module runs unconditionally, before any sequence intent *)"]
    # Passive modules first: their published state is what a commanded
    # module's interlock and every step condition read, in the same scan.
    ordered = sorted(app.modules, key=lambda m: not library.type_of(m).passive)
    keys = localization_numbers(app)
    for module in ordered:
        ctx = ctx_tag_for(app, module.name)
        modules += [
            *module_setup_lines(app, module, keys),
            f"{module_aoi_name(app, module)}(FRK_{n}_Inst{module.name},{ctx},FRK_{n}_ScanCount);",
        ]
    add('Modules', modules)
    add('Start', start_release_call(app) + physical_start_logic(app))
    unit = [
        "(* Sequence intent second, and it checks the ordering itself *)",
        f"FRK_{n}_Unit.RunRequest := FRK_{n}_RunRequest;",
        f"FRK_{n}_Unit.AbortRequest := FRK_{n}_AbortRequest;",
        f"FRK_{n}_Unit.ResetRequest := FRK_{n}_ResetRequest;",
        f"FRK_{n}_Unit.ModeRequest := FRK_{n}_ModeRequest;",
        f"FRK_{n}_Unit.DecisionAnswer := FRK_{n}_DecisionAnswer;",
        *([f"FRK_{n}_Unit.ModelRequest := FRK_{n}_ModelRequest;"]
          if app.models else []),
        (
            f"{unit_aoi_name(app)}(FRK_{n}_InstUnit,FRK_{n}_Unit,FRK_{n}_Chart,"
            + f"{app.records[0].name}Tag,"
            + "".join(f"{ctx_tag_for(app, m.name)}," for m in app.modules)
            + f"FRK_{n}_ScanCount"
            + "".join(f",{t}" for t in app.sim_inputs)
            + ");"
        ),
        *model_commit_logic(app),
        f"FRK_{n}_OrderFail := FRK_{n}_Unit.OrderFail;",
    ]
    dispatch = dispatch_logic(app)
    if dispatch:
        unit += [""] + dispatch
    add('Unit', unit)
    # After every chain rendition has run, so a fault a chain adopted or
    # reported THIS scan is stamped and logged this scan - while the child
    # still holds the reason and the implicated I/O that caused it. Before
    # dispatch, the AUTO renditions' adoptions reached the log a scan late,
    # after the child had already cleared both.
    add('Health', [*wall_clock_logic(app), *health_probe_logic(app), *system_health_logic(app)])
    add('Diagnostics', [*diagnostic_logic(app), *alarm_log_logic(app)])
    add('Statistics', [*(line.cyclic(app) if app.line is not None else []),
                       *oee_logic(app), *profiler_logic(app), *state_flags_logic(app)])
    # Last, so the outputs written this scan reflect the permission this scan
    # computed. Running it earlier would apply a force under the previous
    # scan's verdict.
    forcing = force_logic(app)
    if forcing:
        add('Forcing', forcing)
    return sections


def routine_logic(app: decl.Application, *, use_routines=False) -> tuple[str, ...]:
    """Inline executable view for tests, or the same plan as explicit JSR calls."""
    lines = []
    for name, body in scan_sections(app):
        if lines:
            lines.append('')
        lines.extend([f'JSR({name},0);'] if use_routines and name else body)
    return tuple(lines)


def program_tags(app: decl.Application) -> str:
    tags = sfc_program_tags(app)
    return "<Tags>\n" + "\n".join(tags) + "\n</Tags>" if tags else "<Tags/>"


def programs(app: decl.Application) -> str:
    import fraktal_ab_access as access
    import fraktal_ab_data_access as data
    import fraktal_ab_shelving as shelving
    import fraktal_ab_mailbox_frame as frame
    import fraktal_ab_sets as sets
    routines = "\n".join(
        [st_program_routine(app.routine, routine_logic(app, use_routines=True)),
         st_program_routine(frame.routine_name(app), frame.logic(app)),
         st_program_routine(mailbox.routine_name(app), mailbox.handler_logic(app, use_routines=True)),
         st_program_routine(start_release_routine_name(app), start_release_logic(app))]
        + [st_program_routine(name, body) for name, body in scan_sections(app) if name]
        + ([st_program_routine(config.write_routine_name(app), config.write_logic(app))]
           if editable_values(app) else [])
        + ([st_program_routine(sets.routine_name(app), sets.dispatch_logic(app))]
           if app.config_sets else [])
        + chain_routines(app)
        + [st_program_routine(name, body) for name, body in alarm_service_routines(app)]
        + ([st_program_routine(step_mark_routine_name(app), step_mark_logic(app))]
           if any(decl.ST in c.renditions or decl.SFC in c.renditions for c in hosted_chains(app)) else [])
        + ([st_program_routine(name, body) for name, body in line.routines(app)]
           if app.line is not None else [])
        + ([st_program_routine(config.audit_routine_name(app), config.audit_logic(app))]
           if editable_values(app) else [])
        + ([st_program_routine(name, lines) for name, lines in access.routines(app)]
           if app.access_users is not None else [])
        + ([st_program_routine(data.tag(app, 'ResolveLevel'), data.resolver(app)),
            st_program_routine(data.tag(app, 'RefreshLevels'), data.refresh(app)),
            st_program_routine(shelving.routine_name(app), shelving.handler(app))]
           if app.access_users is not None else [])
    )
    return f"""<Programs>
<Program Name="{app.program}" TestEdits="false" MainRoutineName="{app.routine}" Disabled="false" UseAsFolder="false">
{program_tags(app)}
<Routines>
{routines}
</Routines>
</Program>
</Programs>"""


def tasks(app: decl.Application) -> str:
    return f"""<Tasks>
<Task Name="{app.task_name}" Type="PERIODIC" Rate="{app.task_period_ms}" Watchdog="{app.watchdog_ms}" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{app.program}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


# --- emit -------------------------------------------------------------------

# The scope fence keeps the application from growing runtime-base structure it
# is not authorized to have. It changed once, deliberately: publishing a
# manifest is now in scope (Core 3.10 makes it the runtime source of truth, and
# nothing could discover the station without it), so "Manifest" is no longer
# forbidden. Everything else still is.
#
# It changed a second time, also deliberately: the root Unit now has a Core
# §3.10/§14 command mailbox. The project owner authorized writes on 2026-09-21
# and chose the controller-side mailbox over translating in the gateway, so
# "Mailbox" is no longer forbidden either.
#
# It changed a third time, for the same kind of reason: the AB/TC3 parity
# audit's Phase 4 brings TC3's Core §7.8 release reports to the controller,
# under the owner's rule that the AB build is the same as the TC3 build
# (AB_TC3_PARITY_AUDIT_2026-09-29, §7-§8). So "ReleaseReport" is no longer
# forbidden. Each change followed a recorded decision rather than an
# implementer finding the fence inconvenient.
#
# One frozen-contract manifest member still names a structure that does not
# exist - a module's registry index. It is a *reference*, published as zero, and
# the contract requires the field by that name. Naming it differently to slip
# past a substring check would be worse than the check: it would put the
# manifest out of step with the frozen schema to keep a fence quiet. It is
# allowed by exact name, and only by exact name.
EXCLUDED_SCOPE_TERMS = (
    "Recipe", "ParCfgRecord", "Registry",
    "Traceability",
)

SCOPE_FENCE_ALLOWED = ("RegistryIndex",)


def all_generated_logic(app: decl.Application) -> str:
    parts: list[str] = []
    for mtype in library.types_used(app):
        parts.extend(type_logic(mtype))
    parts.extend(unit_logic(app))
    parts.extend(routine_logic(app))
    import fraktal_ab_mailbox_frame as frame
    parts.extend(frame.logic(app))
    return "\n".join(parts)


def generate(app: decl.Application, source: Path, output: Path, *, initial_config=None) -> dict[str, object]:
    decl.require_valid(app)
    library.require_valid(app)
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    if source.suffix.lower() != ".l5x" or output.suffix.lower() != ".l5x":
        raise ValueError("source and output must use the .L5X extension")
    if source == output:
        raise ValueError("output must differ from source")
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")

    text = source.read_text(encoding="utf-8-sig")
    required = (
        f'ProcessorType="{app.controller}"',
        f'MajorRev="{app.major_revision}"',
        '<Controller Use="Target" Name="FraktalPhase0"',
        "<DataTypes/>", "<AddOnInstructionDefinitions/>", "<Tags/>",
        "<Programs/>", "<Tasks/>",
    )
    missing = [m for m in required if m not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 seed: {missing}")

    # Reject an undiscoverable station before producing a downloadable file.
    # Evidence and this gate consume the same derived counts and byte estimate.
    manifest_info = manifest.evidence(app)
    overflow = [f"{name} {table['rows']}/{table['capacity']}"
                for name, table in manifest_info["Tables"].items()
                if table["rows"] > table["capacity"]]
    if overflow:
        raise ValueError("manifest tables exceed capacity: " + ", ".join(overflow))
    if manifest_info["EstimatedBytes"] > manifest.MANIFEST_BUDGET_BYTES:
        raise ValueError(
            f"manifest is {manifest_info['EstimatedBytes']} bytes, exceeding "
            f"the {manifest.MANIFEST_BUDGET_BYTES}-byte budget")

    logic = all_generated_logic(app)
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", logic):
        raise AssertionError("generated logic references a physical I/O operand")

    types_xml = data_types(app)
    if re.search(r'DataType="BOOL"', types_xml):
        raise AssertionError("a public contract UDT carries a BOOL member (S12 hole)")
    for forbidden in decl.EXCLUDED_TYPES + decl.TRANSPORT_ONLY_TYPES:
        if re.search(rf'DataType="{forbidden}"', types_xml):
            raise AssertionError(f"contract uses a type S12 excluded: {forbidden}")

    tasks_xml = tasks(app)
    # Build-time assertion: the task that ships carries the period the durations
    # were converted from. S16 found the task rate is part of the contract.
    rate = re.search(r'Rate="(\d+)"', tasks_xml)
    if not rate or int(rate.group(1)) != app.task_period_ms:
        raise AssertionError(
            "emitted task period does not match the declared period the "
            "millisecond timeouts were converted from"
        )

    text = replace_once(text, "<DataTypes/>", types_xml)
    text = replace_once(text, "<AddOnInstructionDefinitions/>", aoi_definitions(app))
    import fraktal_ab_initial_config as initial
    text = replace_once(text, "<Tags/>", initial.apply(app, controller_tags(app), initial_config))
    text = replace_once(text, "<Programs/>", programs(app))
    text = replace_once(text, "<Tasks/>", tasks_xml)

    if any(decl.SFC in c.renditions for c in app.chains):
        # AB 3.5 requires current-active execution so one JSR advances one
        # step, which is what makes the chart's trace comparable with ST's.
        for attribute, value in (
            ("SFCExecutionControl", SFC_EXECUTION_CONTROL),
            ("SFCRestartPosition", SFC_RESTART_POSITION),
            ("SFCLastScan", SFC_LAST_SCAN),
        ):
            text, count = re.subn(
                rf'{attribute}="[A-Za-z]+"', f'{attribute}="{value}"',
                text, count=1)
            if count != 1:
                raise ValueError(
                    f"source did not carry exactly one {attribute}")

    # The embedded module is inhibited unless the application declares the
    # channels on it. That inversion is the whole of "no physical I/O" as a
    # property of the DECLARATION rather than a property of the emitter: an
    # application with no io_modules still cannot reach a terminal, and one
    # that declares them is saying so deliberately, in a committed file, under
    # review. The assertion stays either way, because a substitution that
    # matched zero times or twice would leave the chassis in whichever state
    # the source happened to carry.
    wanted = "false" if app.io_modules else "true"
    text, changed = re.subn(
        r'(<Module Name="Discrete_IO"[^>]*\bInhibited=")(?:true|false)("[^>]*>)',
        rf"\g<1>{wanted}\g<2>", text, count=1)
    if changed != 1:
        raise ValueError(
            "embedded Discrete_IO module inhibit was not set exactly once")

    fenced = text
    for allowed in SCOPE_FENCE_ALLOWED:
        fenced = fenced.replace(allowed, "")
    for term in EXCLUDED_SCOPE_TERMS:
        if term in fenced:
            raise AssertionError(f"out-of-scope construct emitted: {term}")

    output.write_text(text, encoding="utf-8", newline="\n")
    import xml.etree.ElementTree as ET
    import fraktal_ab_generated_size as generated_size
    steps = ordered_steps(app)
    emitted = ET.fromstring(text)
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Application": app.name,
        "Source": str(source),
        "SourceSha256": sha256(source),
        "Output": str(output),
        "OutputSha256": sha256(output),
        "GeneratedSize": generated_size.report(emitted),
        "Controller": app.controller,
        "MajorRevision": app.major_revision,
        "TaskName": app.task_name,
        "TaskPeriodMs": app.task_period_ms,
        "WatchdogMs": app.watchdog_ms,
        "PhysicalIoReferences": sum(len(m.channels) for m in app.io_modules),
        "EmbeddedIoInhibited": not app.io_modules,
        "TaskOutputUpdatesDisabled": not app.io_modules,
        "ForceableOutputs": bin(force_output_mask(app)).count("1"),
        "BoolMembersInPublicUdt": 0,
        "ContractRecords": [r.name for r in app.records],
        # Distinct TYPES: one AOI each, however many instances call it.
        "ModuleTypes": [type_aoi_name(t) for t in library.types_used(app)],
        "ModeOwner": unit_aoi_name(app),
        "AoiDefinitions": len(emitted.findall('./Controller/AddOnInstructionDefinitions/AddOnInstructionDefinition')),
        "Chains": {c.name: [s.number for s in c.steps] for c in app.chains},
        "DistinctSteps": len(steps),
        "ChartSteps": app.chart_steps,
        "WritableInputs": list(externally_writable(app)),
        "CommandInputs": list(command_inputs(app)),
        "EvidenceTags": list(evidence_tags(app)),
        "HarnessOnlyTags": list(harness_only_tags(app)),
        "PublishableTags": list(publishable_tags(app)),
        "Manifest": manifest_info,
        "Programs": len(emitted.findall('./Controller/Programs/Program')),
        "Routines": len(emitted.findall('./Controller/Programs/Program/Routines/Routine')),
        "Tasks": len(emitted.findall('./Controller/Tasks/Task')),
    }


def main(argv: list[str] | None = None) -> int:
    import fraktal_ab_station as station

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--declaration", default=None,
                        help="the station's declaration module; default "
                             f"${station.ENV} or {station.DEFAULT}")
    parser.add_argument("--initial-config", type=Path,
                        help="validated commissioning configuration JSON; no sessions or credentials")
    args = parser.parse_args(argv)
    if args.declaration:
        import os
        os.environ[station.ENV] = args.declaration
    try:
        image = json.loads(args.initial_config.read_text(encoding="utf-8")) if args.initial_config else None
        evidence = generate(station.application(), args.source, args.output, initial_config=image)
        if args.initial_config:
            import hashlib
            evidence["InitialConfigSha256"] = hashlib.sha256(args.initial_config.read_bytes()).hexdigest().upper()
    except (OSError, ValueError, AssertionError, decl.DeclarationError) as exc:
        print(f"ERROR [generate] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
