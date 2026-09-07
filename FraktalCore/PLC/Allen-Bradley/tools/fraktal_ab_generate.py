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

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256
import fraktal_ab_declaration as decl


SCHEMA = "fraktal.ab.generated-application"
SCHEMA_VERSION = 1

# Execution-state ordinals are Core §6.1's and are never renumbered.
STATE_READY, STATE_BUSY, STATE_DONE, STATE_ERROR, STATE_ABORTED = 0, 1, 2, 3, 4
SEVERITY_LOW, SEVERITY_HIGH = 0, 2


# --- the per-module handshake context --------------------------------------

def module_context_members() -> tuple[decl.Member, ...]:
    """The Core §6.1 handshake, carried as the S12-proved DINT-only layout."""
    return (
        decl.scalar("SchemaVersion", "which contract this instance holds", initial=1),
        decl.scalar("Par_Speed", "simulated plant units per scan", initial=25),
        decl.duration_ms("Par_TimeoutMs", "command timeout, milliseconds", initial=500),
        decl.scalar("Par_TimeoutScans", "the same timeout in whole task scans"),
        decl.scalar("ParCmd_Command", "requested command ordinal"),
        decl.scalar("ParCmd_Target", "requested plant target"),
        decl.scalar("ParCmd_Latched", "target latched on the accepted edge"),
        decl.scalar("OutCmd_FinalPos", "position when the command completed"),
        decl.boolean("OutCmd_Ok", "the last command completed cleanly"),
        decl.scalar("OutImm_Pos", "live simulated position"),
        decl.scalar("OutImm_ExecState", "Core §6.1 ordinals, never renumbered"),
        decl.boolean("OutImm_Held", "held is not an ExecState ordinal"),
        decl.reason("OutImm_Reason", "named reason for the current condition"),
        decl.scalar("OutImm_Severity", "0 LOW, 2 HIGH"),
        decl.boolean("Execute", "command request"),
        decl.boolean("ExecutePrev", "edge memory"),
        decl.boolean("Abort", "abort request"),
        decl.boolean("Busy", ""),
        decl.boolean("Done", ""),
        decl.boolean("Error", ""),
        decl.boolean("Aborted", ""),
        decl.reason("ErrorID", "first-out reason, promoted from the diagnostic"),
        decl.duration_ms("ElapsedMs", "integrated from the declared task period"),
        decl.scalar("RunCount", ""),
        decl.scalar("DoneCount", ""),
        decl.scalar("ErrorCount", ""),
        decl.scalar("AbortCount", ""),
        decl.scalar("HeldScans", "scans spent held; the timeout does not accrue here"),
        decl.scalar("ResetCount", ""),
        decl.scalar("ModuleScan", "the scan this module last ran - the ordering check"),
        decl.scalar("FaultRequest", "simulated device fault input"),
        decl.scalar("HoldRequest", "simulated permissive loss"),
    )


def unit_context_members(app: decl.Application) -> tuple[decl.Member, ...]:
    return (
        decl.scalar("SchemaVersion", "", initial=SCHEMA_VERSION),
        decl.scalar("Par_TaskPeriodMs", "the declared period this project was emitted for",
                    initial=app.task_period_ms),
        decl.scalar("Mode", "active mode ordinal"),
        decl.scalar("ModeRequest", "requested mode ordinal"),
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
        decl.boolean("Held", ""),
        decl.reason("HeldReason", ""),
        decl.scalar("HeldSeverity", ""),
        decl.scalar("DecisionId", "the decision the chain is waiting on, 0 when none"),
        decl.scalar("DecisionAnswer", "written by the operator surface"),
        decl.scalar("DecisionCount", ""),
        decl.scalar("CycleCount", ""),
        decl.scalar("GoodCount", ""),
        decl.scalar("ScrapCount", ""),
        decl.scalar("OrderFail", "a child module had not run when the owner ran"),
        decl.scalar("StepScan", "scan on which the active step was entered"),
        decl.scalar("RunRequest", ""),
        decl.scalar("AbortRequest", ""),
        decl.scalar("ResetRequest", ""),
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
        decl.scalar("Visited", "1 once the step has been entered", dimension=n),
        decl.duration_ms("LastMs", "duration of the step's last completed visit", dimension=n),
        decl.scalar("EnterCount", "visits to the step", dimension=n),
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
    records.append(decl.Record(module_context_name(app), module_context_members(),
                               "the Core §6.1 handshake context"))
    records.append(decl.Record(unit_context_name(app), unit_context_members(app),
                               "the mode owner's context"))
    records.append(decl.Record(chart_name(app), chart_members(app),
                               "Core §3.13 step marks"))
    for record in records:
        members = "\n".join(_member_xml(m) for m in record.members)
        description = ""
        if record.comment:
            description = f"<Description><![CDATA[{record.comment}]]></Description>"
        blocks.append(
            f'<DataType Name="{record.name}" Family="NoFamily" Class="User">'
            f"{description}\n<Members>\n{members}\n</Members>\n</DataType>"
        )
    return "<DataTypes>\n" + "\n".join(blocks) + "\n</DataTypes>"


def module_context_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}ModuleCtx"


def unit_context_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}UnitCtx"


def chart_name(app: decl.Application) -> str:
    return f"FRK_T_{app.name}Chart"


def module_aoi_name(app: decl.Application, module: decl.Module) -> str:
    return f"FRK_M_{app.name}{module.name}"


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
    lines = "\n".join(
        f'<Line Number="{i}"><![CDATA[{statement}]]></Line>'
        for i, statement in enumerate(logic)
    )
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

def module_logic(app: decl.Application, module: decl.Module) -> tuple[str, ...]:
    """The §6.1 handshake over a simulated plant, generated per module type.

    The timeout is carried in milliseconds and integrated from the declared task
    period, and it does **not** accrue while held: a hold is the operator letting
    go, and a hold that matures into a timeout would report the machine as broken
    for the designed behaviour.
    """
    period = app.task_period_ms
    lines: list[str] = [
        f"(* {module.name}: Core §6.1 handshake over a simulated plant. *)",
        "(* Generated from the declaration - never hand-edit. *)",
        "Ctx.ModuleScan := Scan;",
        f"Ctx.Par_TimeoutScans := Ctx.Par_TimeoutMs / {period};",
        "",
        "(* Execute-drop reset: a terminal state clears only when Execute drops *)",
        "IF Ctx.Execute = 0 THEN",
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
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_READY};",
        "Ctx.ElapsedMs := 0;",
        "END_IF;",
        "",
        "(* Rising edge accepts the command and latches the request *)",
        "IF (Ctx.Execute <> 0) AND (Ctx.ExecutePrev = 0) THEN",
        "Ctx.ParCmd_Latched := Ctx.ParCmd_Target;",
        "Ctx.Busy := 1;",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.RunCount := Ctx.RunCount + 1;",
        "Ctx.ElapsedMs := 0;",
        "END_IF;",
        "",
        "IF Ctx.Busy <> 0 THEN",
        "IF Ctx.Abort <> 0 THEN",
        "Ctx.Aborted := 1;",
        "Ctx.Busy := 0;",
        "Ctx.AbortCount := Ctx.AbortCount + 1;",
        f"Ctx.OutImm_ExecState := {STATE_ABORTED};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        "ELSIF Ctx.FaultRequest <> 0 THEN",
        "Ctx.Error := 1;",
        "Ctx.Busy := 0;",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        f"Ctx.ErrorID := {app.reasons.get('DEVICE_FAULT', 6102)};",
        f"Ctx.OutImm_Reason := {app.reasons.get('DEVICE_FAULT', 6102)};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "ELSIF Ctx.HoldRequest <> 0 THEN",
        "(* Held: BUSY, a LOW named reason, and no Error. The elapsed clock is *)",
        "(* deliberately NOT advanced here, so a held command never times out. *)",
        "Ctx.OutImm_Held := 1;",
        f"Ctx.OutImm_Reason := {app.reasons.get('HELD_PERMISSIVE', 6101)};",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.HeldScans := Ctx.HeldScans + 1;",
        "ELSE",
        "Ctx.OutImm_Held := 0;",
        "Ctx.OutImm_Reason := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.ElapsedMs := Ctx.ElapsedMs + {period};",
        "IF Ctx.OutImm_Pos < Ctx.ParCmd_Latched THEN",
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
        f"Ctx.ErrorID := {app.reasons.get('TIMEOUT', 6103)};",
        f"Ctx.OutImm_Reason := {app.reasons.get('TIMEOUT', 6103)};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "END_IF;",
        "END_IF;",
        "END_IF;",
        "",
        "Ctx.ExecutePrev := Ctx.Execute;",
    ]
    return tuple(lines)


def module_aois(app: decl.Application) -> list[str]:
    ctx = module_context_name(app)
    out = []
    for module in app.modules:
        out.append(_aoi(
            module_aoi_name(app, module),
            f"Generated module type: {module.comment}",
            ENABLE_PARAMETERS + (
                _parameter("Ctx", ctx, "InOut"),
                _parameter("Scan", "DINT", "Input", radix="Decimal"),
            ),
            module_logic(app, module),
            (ctx,),
        ))
    return out


# --- chain logic ------------------------------------------------------------

def ordered_steps(app: decl.Application) -> list[int]:
    seen: list[int] = []
    for chain in app.chains:
        for step in chain.steps:
            if step.number not in seen:
                seen.append(step.number)
    return seen


def _mark_step(app: decl.Application, index: int) -> list[str]:
    return [
        "IF Ctx.Step <> Ctx.PrevStep THEN",
        f"Chart.StepCursor := {index};",
        "Chart.ActiveStepNumber := Ctx.Step;",
        f"Chart.Visited[{index}] := 1;",
        f"Chart.EnterCount[{index}] := Chart.EnterCount[{index}] + 1;",
        "Chart.CurrentStepMs := 0;",
        "Ctx.StepScan := Scan;",
        "Ctx.PrevStep := Ctx.Step;",
        "Chart.StallReason := 0;",
        "END_IF;",
        f"Chart.CurrentStepMs := (Scan - Ctx.StepScan) * {app.task_period_ms};",
    ]


def _advance(app: decl.Application, step: decl.Step, index: int) -> list[str]:
    return [
        f"Chart.LastMs[{index}] := Chart.CurrentStepMs;",
        f"Ctx.Step := {step.on_advance};",
    ]


def _entry_reset(ctx: str) -> list[str]:
    """Drop Execute on the step's own entry scan, then command from the next.

    This is Core §6.1's Execute-drop reset used as the generator intends it: a
    module clears Done/Error/Aborted only when its Execute falls, so a step that
    asserted Execute unconditionally could never release a child that had
    already terminated - the child would stay faulted and every later step
    aiming at it would stall forever. Dropping on entry also guarantees the
    rising edge the module latches its request on.
    """
    return [
        "IF Scan = Ctx.StepScan THEN",
        f"{ctx}.Execute := 0;",
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


def step_logic(app: decl.Application, chain: decl.Chain, step: decl.Step,
               index: int) -> list[str]:
    """Emit one step's body. Every branch marks the chart before it decides."""
    lines: list[str] = [f"{step.number}:", f"(* {step.name}: {step.comment} *)"]
    lines += _mark_step(app, index)

    if step.action == decl.ISSUE:
        module = next(m for m in app.modules if m.name == step.module)
        command = next(c for c in module.commands if c.name == step.command)
        ctx = _module_ref(app, step.module)
        lines += _entry_reset(ctx) + [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + _advance(app, step, index) + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            f"Chart.StallReason := {ctx}.ErrorID;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.ADOPT:
        # An awaited child: its first-out is adopted verbatim and the chain stops
        # on this step. This is the rollup - the parent does not invent a reason.
        module = next(m for m in app.modules if m.name == step.module)
        command = next(c for c in module.commands if c.name == step.command)
        ctx = _module_ref(app, step.module)
        source = app.modules.index(module) + 1
        lines += _entry_reset(ctx) + [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + _advance(app, step, index) + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            "(* Adopt the child's first-out verbatim: same reason, no translation *)",
            "Ctx.Error := 1;",
            f"Ctx.ErrorID := {ctx}.ErrorID;",
            f"Ctx.ErrorSource := {source};",
            f"Chart.StallReason := {ctx}.ErrorID;",
            "Ctx.Running := 0;",
            "(* Release the child: adopting its fault must not also pin it in *)",
            "(* the faulted state, or nothing could ever clear it. *)",
            f"{ctx}.Execute := 0;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.REPORT:
        # Reported, NOT adopted: a message. The chain owns the recovery below, so
        # adopting here would replace a designed recovery with a stop.
        module = next(m for m in app.modules if m.name == step.module)
        command = next(c for c in module.commands if c.name == step.command)
        ctx = _module_ref(app, step.module)
        lines += _entry_reset(ctx) + [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + _advance(app, step, index) + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            "(* Report the child's own first-out; do NOT adopt it *)",
            f"Ctx.ReportedReason := {ctx}.ErrorID;",
            "Ctx.ReportedCount := Ctx.ReportedCount + 1;",
            f"{ctx}.Execute := 0;",
            f"Chart.LastMs[{index}] := Chart.CurrentStepMs;",
            f"Ctx.Step := {step.on_jump};",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.DELAY:
        member = step.duration_member
        scans = None
        for record in app.records:
            for m in record.members:
                if m.name == member:
                    scans = decl.scans_for(app, m.initial)
        lines += [
            f"(* {member} = {scans} scans at the declared {app.task_period_ms} ms period *)",
            f"IF Chart.CurrentStepMs >= Cfg.{member} THEN",
        ] + _advance(app, step, index) + [
            "ELSE",
            f"Chart.StallReason := {app.reasons.get('WAIT_DELAY', 6110)};",
            "END_IF;",
        ]

    elif step.action == decl.AWAIT:
        condition = " AND ".join(
            f"({sim_param(app, c)} <> 0)" for c in step.conditions
        ) or "(1 = 1)"
        lines += [
            f"IF {condition} THEN",
        ] + _advance(app, step, index) + [
            "ELSE",
            f"Chart.StallReason := {step.hold_reason or app.reasons.get('WAIT_CONDITION', 6111)};",
            "END_IF;",
        ]

    elif step.action == decl.HELD_AWAIT:
        # The S16 held rule, restated for a chain step: BUSY, a LOW named reason,
        # no Error, and progress resumes on its own when the condition returns.
        ctx = _module_ref(app, step.module) if step.module else ""
        command_lines: list[str] = []
        if step.module and step.command:
            module = next(m for m in app.modules if m.name == step.module)
            command = next(c for c in module.commands if c.name == step.command)
            command_lines = [
                f"{ctx}.ParCmd_Command := {command.ordinal};",
                f"{ctx}.ParCmd_Target := {command.target_position};",
            ]
        lines += ([f"IF Scan = Ctx.StepScan THEN", f"{ctx}.Execute := 0;", "END_IF;"]
                  if ctx else []) + [
            f"IF ({sim_param(app, step.hold_condition)} <> 0) THEN",
            "Ctx.Held := 0;",
            "Ctx.HeldReason := 0;",
            f"Ctx.HeldSeverity := {SEVERITY_LOW};",
            "Chart.StallReason := 0;",
        ] + command_lines + ([f"{ctx}.Execute := 1;"] if ctx else []) + [
            f"IF {ctx}.Done <> 0 THEN" if ctx else "IF 1 = 1 THEN",
            f"{ctx}.Execute := 0;" if ctx else "",
        ] + _advance(app, step, index) + [
            "END_IF;",
            "ELSE",
            "(* Held: the motion stands still, a LOW named reason is published, *)",
            "(* no Error is raised, and nothing times out. It self-resumes. *)",
            "Ctx.Held := 1;",
            f"Ctx.HeldReason := {step.hold_reason};",
            f"Ctx.HeldSeverity := {SEVERITY_LOW};",
            f"Chart.StallReason := {step.hold_reason};",
        ] + ([f"{ctx}.Execute := 0;"] if ctx else []) + [
            "END_IF;",
        ]

    elif step.action == decl.DECISION:
        # A decision the chain waits on without faulting. A scrap is deliberate,
        # so there is no timeout default (Core §6.11).
        lines += [
            f"Ctx.DecisionId := {step.decision_id};",
            "IF Ctx.DecisionAnswer <> 0 THEN",
            "Ctx.DecisionCount := Ctx.DecisionCount + 1;",
            "IF Ctx.DecisionAnswer = 1 THEN",
        ] + _advance(app, step, index) + [
            "ELSE",
            f"Chart.LastMs[{index}] := Chart.CurrentStepMs;",
            f"Ctx.Step := {step.on_jump};",
            "END_IF;",
            "Ctx.DecisionId := 0;",
            "Ctx.DecisionAnswer := 0;",
            "ELSE",
            f"Chart.StallReason := {app.reasons.get('WAIT_DECISION', 6112)};",
            "END_IF;",
        ]

    elif step.action == decl.MARK:
        for mark in step.marks:
            lines.append(f"{mark};")
        lines += _advance(app, step, index)

    elif step.action == decl.COMPLETE:
        lines += [
            "Ctx.Complete := 1;",
            "Ctx.Running := 0;",
            "Chart.StallReason := 0;",
        ]
        if step.on_advance != -1:
            lines += _advance(app, step, index)

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
        "Ctx.Held := 0;",
        "Ctx.HeldReason := 0;",
        "Chart.StallReason := 0;",
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
        "END_IF;",
        "",
        "IF Ctx.AbortRequest <> 0 THEN",
        "Ctx.Aborted := 1;",
        "Ctx.Running := 0;",
        "Ctx.Step := 0;",
        "Ctx.PrevStep := -1;",
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
        "",
        "IF Ctx.Running <> 0 THEN",
    ]
    for chain in app.chains:
        lines.append(f"IF Ctx.Mode = {chain.mode_ordinal} THEN")
        lines.append(f"Chart.ActiveChain := {chain.mode_ordinal};")
        lines.append("CASE Ctx.Step OF")
        for step in chain.steps:
            index = steps_order.index(step.number)
            lines += step_logic(app, chain, step, index)
        lines += [
            "ELSE",
            f"Chart.StallReason := {app.reasons.get('STEP_STALLED', 6120)};",
            "Ctx.Step := 0;",
            "END_CASE;",
            "END_IF;",
        ]
    lines += ["END_IF;"]
    return tuple(lines)


def unit_parameters(app: decl.Application) -> tuple[str, ...]:
    """InOuts first, then Inputs - the order the ST call site passes them in."""
    params = [
        _parameter("Ctx", unit_context_name(app), "InOut"),
        _parameter("Chart", chart_name(app), "InOut"),
        _parameter("Cfg", app.records[0].name, "InOut"),
    ]
    for module in app.modules:
        params.append(_parameter(_module_ref(app, module.name),
                                 module_context_name(app), "InOut"))
    params.append(_parameter("Scan", "DINT", "Input", radix="Decimal"))
    for tag in app.sim_inputs:
        params.append(_parameter(sim_param(app, tag), "DINT", "Input",
                                 radix="Decimal"))
    return tuple(params)


def unit_aoi(app: decl.Application) -> str:
    return _aoi(
        unit_aoi_name(app),
        f"Generated mode owner for {app.name}: chains {[c.name for c in app.chains]}",
        ENABLE_PARAMETERS + unit_parameters(app),
        unit_logic(app),
        (unit_context_name(app), chart_name(app), module_context_name(app),
         app.records[0].name),
    )


def aoi_definitions(app: decl.Application) -> str:
    blocks = module_aois(app) + [unit_aoi(app)]
    return "<AddOnInstructionDefinitions>\n" + "\n".join(blocks) + "\n</AddOnInstructionDefinitions>"


# --- tags -------------------------------------------------------------------

def _structure_tag(name: str, data_type: str, members: tuple[decl.Member, ...]) -> str:
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
    return f"""<Tag Name="{name}" TagType="Base" DataType="{data_type}" Constant="false" ExternalAccess="Read/Write">
<Data Format="Decorated">
<Structure DataType="{data_type}">
{body}
</Structure>
</Data>
</Tag>"""


def writable_inputs(app: decl.Application) -> tuple[str, ...]:
    names = [
        f"FRK_{app.name}_RunRequest",
        f"FRK_{app.name}_AbortRequest",
        f"FRK_{app.name}_ResetRequest",
        f"FRK_{app.name}_ModeRequest",
        f"FRK_{app.name}_DecisionAnswer",
    ]
    for module in app.modules:
        names.append(f"FRK_{app.name}_Fault{module.name}")
        names.append(f"FRK_{app.name}_Hold{module.name}")
    # Simulated operator and sensor inputs are writable too: the harness drives
    # the plant's world through them, and nothing else may write them.
    names.extend(app.sim_inputs)
    return tuple(names)


def evidence_tags(app: decl.Application) -> tuple[str, ...]:
    return (
        f"FRK_{app.name}_ScanCount",
        f"FRK_{app.name}_OrderFail",
        f"FRK_{app.name}_TaskPeriodMs",
    )


def controller_tags(app: decl.Application) -> str:
    tags: list[str] = []
    for record in app.records:
        tags.append(_structure_tag(f"{record.name}Tag", record.name, record.members))
    module_members = module_context_members()
    for module in app.modules:
        initial = list(module_members)
        initial = tuple(
            m if m.name not in ("Par_Speed", "Par_TimeoutMs")
            else decl.Member(m.name, m.comment, m.kind, m.dimension,
                             module.speed_per_scan if m.name == "Par_Speed" else module.timeout_ms)
            for m in initial
        )
        tags.append(_structure_tag(ctx_tag_for(app, module.name),
                                   module_context_name(app), initial))
    tags.append(_structure_tag(f"FRK_{app.name}_Unit", unit_context_name(app),
                               unit_context_members(app)))
    tags.append(_structure_tag(f"FRK_{app.name}_Chart", chart_name(app),
                               chart_members(app)))
    for name in writable_inputs(app):
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", "Read/Write"))
    for name in evidence_tags(app):
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
    return "<Tags>\n" + "\n".join(tags) + "\n</Tags>"


def routine_logic(app: decl.Application) -> tuple[str, ...]:
    n = app.name
    lines = [
        f"FRK_{n}_ScanCount := FRK_{n}_ScanCount + 1;",
        f"FRK_{n}_TaskPeriodMs := {app.task_period_ms};",
        "",
        "(* Every module runs unconditionally, before any sequence intent *)",
    ]
    for module in app.modules:
        ctx = ctx_tag_for(app, module.name)
        lines += [
            f"{ctx}.FaultRequest := FRK_{n}_Fault{module.name};",
            f"{ctx}.HoldRequest := FRK_{n}_Hold{module.name};",
            f"{module_aoi_name(app, module)}(FRK_{n}_Inst{module.name},{ctx},FRK_{n}_ScanCount);",
        ]
    lines += [
        "",
        "(* Sequence intent second, and it checks the ordering itself *)",
        f"FRK_{n}_Unit.RunRequest := FRK_{n}_RunRequest;",
        f"FRK_{n}_Unit.AbortRequest := FRK_{n}_AbortRequest;",
        f"FRK_{n}_Unit.ResetRequest := FRK_{n}_ResetRequest;",
        f"FRK_{n}_Unit.ModeRequest := FRK_{n}_ModeRequest;",
        f"FRK_{n}_Unit.DecisionAnswer := FRK_{n}_DecisionAnswer;",
        (
            f"{unit_aoi_name(app)}(FRK_{n}_InstUnit,FRK_{n}_Unit,FRK_{n}_Chart,"
            + f"{app.records[0].name}Tag,"
            + "".join(f"{ctx_tag_for(app, m.name)}," for m in app.modules)
            + f"FRK_{n}_ScanCount"
            + "".join(f",{t}" for t in app.sim_inputs)
            + ");"
        ),
        "",
        f"FRK_{n}_OrderFail := FRK_{n}_Unit.OrderFail;",
    ]
    return tuple(lines)


def programs(app: decl.Application) -> str:
    lines = "\n".join(
        f'<Line Number="{i}"><![CDATA[{s}]]></Line>'
        for i, s in enumerate(routine_logic(app))
    )
    return f"""<Programs>
<Program Name="{app.program}" TestEdits="false" MainRoutineName="{app.routine}" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="{app.routine}" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
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

EXCLUDED_SCOPE_TERMS = (
    "Recipe", "ParCfgRecord", "Manifest", "Registry", "Mailbox",
    "Traceability", "ReleaseReport",
)


def all_generated_logic(app: decl.Application) -> str:
    parts: list[str] = []
    for module in app.modules:
        parts.extend(module_logic(app, module))
    parts.extend(unit_logic(app))
    parts.extend(routine_logic(app))
    return "\n".join(parts)


def generate(app: decl.Application, source: Path, output: Path) -> dict[str, object]:
    decl.require_valid(app)
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
    text = replace_once(text, "<Tags/>", controller_tags(app))
    text = replace_once(text, "<Programs/>", programs(app))
    text = replace_once(text, "<Tasks/>", tasks_xml)

    text, inhibited = re.subn(
        r'(<Module Name="Discrete_IO"[^>]*\bInhibited=")false("[^>]*>)',
        r"\1true\2", text, count=1)
    if inhibited != 1:
        raise ValueError("embedded Discrete_IO module was not inhibited exactly once")

    for term in EXCLUDED_SCOPE_TERMS:
        if term in text:
            raise AssertionError(f"out-of-scope construct emitted: {term}")

    output.write_text(text, encoding="utf-8", newline="\n")
    steps = ordered_steps(app)
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Application": app.name,
        "Source": str(source),
        "SourceSha256": sha256(source),
        "Output": str(output),
        "OutputSha256": sha256(output),
        "Controller": app.controller,
        "MajorRevision": app.major_revision,
        "TaskName": app.task_name,
        "TaskPeriodMs": app.task_period_ms,
        "WatchdogMs": app.watchdog_ms,
        "PhysicalIoReferences": 0,
        "EmbeddedIoInhibited": True,
        "TaskOutputUpdatesDisabled": True,
        "BoolMembersInPublicUdt": 0,
        "ContractRecords": [r.name for r in app.records],
        "ModuleTypes": [module_aoi_name(app, m) for m in app.modules],
        "ModeOwner": unit_aoi_name(app),
        "AoiDefinitions": len(app.modules) + 1,
        "Chains": {c.name: [s.number for s in c.steps] for c in app.chains},
        "DistinctSteps": len(steps),
        "ChartSteps": app.chart_steps,
        "WritableInputs": list(writable_inputs(app)),
        "EvidenceTags": list(evidence_tags(app)),
        "Programs": 1,
        "Routines": 1,
        "Tasks": 1,
    }


def main(argv: list[str] | None = None) -> int:
    import fraktal_ab_press_demo

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        evidence = generate(fraktal_ab_press_demo.application(), args.source, args.output)
    except (OSError, ValueError, AssertionError, decl.DeclarationError) as exc:
        print(f"ERROR [generate] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
