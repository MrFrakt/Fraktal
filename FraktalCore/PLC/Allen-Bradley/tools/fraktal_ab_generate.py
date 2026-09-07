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



def _mark_step(app: decl.Application, index: int, names: Names) -> list[str]:
    """Enter the step: move the cursor, mark it visited, restart its clock."""
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
        "END_IF;",
        f"{c}.CurrentStepMs := ({names.scan} - {u}.StepScan) * {app.task_period_ms};",
    ]


def _advance(app: decl.Application, step: decl.Step, index: int,
             names: Names) -> list[str]:
    return [
        f"{names.chart}.LastMs[{index}] := {names.chart}.CurrentStepMs;",
        f"{names.unit}.Step := {step.on_advance};",
    ]



def _entry_reset(ctx: str, names: "Names") -> list[str]:
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
               index: int, names: Names | None = None) -> list[str]:
    """Emit one step's body. Every branch marks the chart before it decides."""
    names = names or Names(app, in_aoi=True)
    u, c = names.unit, names.chart
    lines: list[str] = [f"{step.number}:", f"(* {step.name}: {step.comment} *)"]
    lines += _mark_step(app, index, names)
    adv = _advance(app, step, index, names)

    def commanded(action_name: str) -> tuple[str, list[str]]:
        module = next(m for m in app.modules if m.name == action_name)
        command = next(cm for cm in module.commands if cm.name == step.command)
        ctx = names.module(step.module)
        return ctx, [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
        ]

    if step.action == decl.ISSUE:
        ctx, issue = commanded(step.module)
        lines += _entry_reset(ctx, names) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + adv + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            f"{c}.StallReason := {ctx}.ErrorID;",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.ADOPT:
        # An awaited child: its first-out is adopted verbatim and the chain stops
        # on this step. This is the rollup - the parent does not invent a reason.
        ctx, issue = commanded(step.module)
        source = [m.name for m in app.modules].index(step.module) + 1
        lines += _entry_reset(ctx, names) + issue + [
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
        lines += _entry_reset(ctx, names) + issue + [
            f"IF {ctx}.Done <> 0 THEN",
            f"{ctx}.Execute := 0;",
        ] + adv + [
            f"ELSIF {ctx}.Error <> 0 THEN",
            "(* Report the child's own first-out; do NOT adopt it *)",
            f"{u}.ReportedReason := {ctx}.ErrorID;",
            f"{u}.ReportedCount := {u}.ReportedCount + 1;",
            f"{ctx}.Execute := 0;",
            f"{c}.LastMs[{index}] := {c}.CurrentStepMs;",
            f"{u}.Step := {step.on_jump};",
            "END_IF;",
            "END_IF;",
        ]

    elif step.action == decl.DELAY:
        lines += [
            f"IF {c}.CurrentStepMs >= {names.cfg}.{step.duration_member} THEN",
        ] + adv + [
            "ELSE",
            f"{c}.StallReason := {app.reasons.get('WAIT_DELAY', 6110)};",
            "END_IF;",
        ]

    elif step.action == decl.AWAIT:
        condition = " AND ".join(
            f"({names.sim(x)} <> 0)" for x in step.conditions) or "(1 = 1)"
        lines += [f"IF {condition} THEN"] + adv + [
            "ELSE",
            f"{c}.StallReason := "
            f"{step.hold_reason or app.reasons.get('WAIT_CONDITION', 6111)};",
            "END_IF;",
        ]

    elif step.action == decl.HELD_AWAIT:
        # The S16 held rule, restated for a chain step: BUSY, a LOW named reason,
        # no Error, and progress resumes on its own when the condition returns.
        ctx, issue = commanded(step.module) if step.module else ("", [])
        lines += ([f"IF {names.scan} = {u}.StepScan THEN", f"{ctx}.Execute := 0;",
                   "END_IF;"] if ctx else []) + [
            f"IF ({names.sim(step.hold_condition)} <> 0) THEN",
            f"{u}.Held := 0;",
            f"{u}.HeldReason := 0;",
            f"{u}.HeldSeverity := {SEVERITY_LOW};",
            f"{c}.StallReason := 0;",
        ] + issue + [
            f"IF {ctx}.Done <> 0 THEN" if ctx else "IF 1 = 1 THEN",
            f"{ctx}.Execute := 0;" if ctx else "",
        ] + adv + [
            "END_IF;",
            "ELSE",
            "(* Held: the motion stands still, a LOW named reason is published, *)",
            "(* no Error is raised, and nothing times out. It self-resumes. *)",
            f"{u}.Held := 1;",
            f"{u}.HeldReason := {step.hold_reason};",
            f"{u}.HeldSeverity := {SEVERITY_LOW};",
            f"{c}.StallReason := {step.hold_reason};",
        ] + ([f"{ctx}.Execute := 0;"] if ctx else []) + [
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
            f"{c}.StallReason := {app.reasons.get('WAIT_DECISION', 6112)};",
            "END_IF;",
        ]

    elif step.action == decl.MARK:
        for mark in step.marks:
            lines.append(mark.replace("Ctx.", f"{u}.") + ";")
        lines += adv

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
        if chain.multi_rendition:
            # Hosted in program routines instead: an AOI cannot contain an SFC
            # routine, so a chain carried in three languages cannot live here.
            # The owner still owns the latches and the ordering check for it.
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
        f"{names.chart}.StallReason := {app.reasons.get('STEP_STALLED', 6120)};",
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

    if step.action in (decl.ISSUE, decl.ADOPT, decl.REPORT):
        ctx, issue = commanded(step.module)
        legs.append(_leg(fresh, f"MOV(0,{ctx}.Execute)"))
        legs.append(_leg(entered, issue))
        legs.append(_leg(entered, f"NEQ({ctx}.Done,0)", f"MOV(0,{ctx}.Execute)",
                         _ld_advance(app, step, index, names, step.on_advance)))
        if step.action == decl.ISSUE:
            legs.append(_leg(entered, f"NEQ({ctx}.Error,0)",
                             f"MOV({ctx}.ErrorID,{c}.StallReason)"))
        elif step.action == decl.ADOPT:
            source = [m.name for m in app.modules].index(step.module) + 1
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
                f"ADD({u}.ReportedCount,1,{u}.ReportedCount)",
                f"MOV(0,{ctx}.Execute)",
                _ld_advance(app, step, index, names, step.on_jump)))

    elif step.action == decl.DELAY:
        member = f"{names.cfg}.{step.duration_member}"
        legs.append(_leg(f"GEQ({c}.CurrentStepMs,{member})",
                         _ld_advance(app, step, index, names, step.on_advance)))
        legs.append(_leg(f"LES({c}.CurrentStepMs,{member})",
                         f"MOV({app.reasons.get('WAIT_DELAY', 6110)},{c}.StallReason)"))

    elif step.action == decl.AWAIT:
        ready = "".join(f"NEQ({names.sim(x)},0)" for x in step.conditions)
        legs.append(_leg(ready, _ld_advance(app, step, index, names, step.on_advance)))
        missing = ",".join(f"EQU({names.sim(x)},0)" for x in step.conditions)
        reason = step.hold_reason or app.reasons.get("WAIT_CONDITION", 6111)
        legs.append(f"[{missing}]MOV({reason},{c}.StallReason)")

    elif step.action == decl.HELD_AWAIT:
        ctx, issue = commanded(step.module)
        held = names.sim(step.hold_condition)
        legs.append(_leg(fresh, f"MOV(0,{ctx}.Execute)"))
        legs.append(_leg(f"NEQ({held},0)", entered, f"MOV(0,{u}.Held)",
                         f"MOV(0,{u}.HeldReason)",
                         f"MOV({SEVERITY_LOW},{u}.HeldSeverity)",
                         f"MOV(0,{c}.StallReason)", issue))
        legs.append(_leg(f"NEQ({held},0)", entered, f"NEQ({ctx}.Done,0)",
                         f"MOV(0,{ctx}.Execute)",
                         _ld_advance(app, step, index, names, step.on_advance)))
        legs.append(_leg(f"EQU({held},0)", f"MOV(1,{u}.Held)",
                         f"MOV({step.hold_reason},{u}.HeldReason)",
                         f"MOV({SEVERITY_LOW},{u}.HeldSeverity)",
                         f"MOV({step.hold_reason},{c}.StallReason)",
                         f"MOV(0,{ctx}.Execute)"))

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
                         f"MOV({app.reasons.get('WAIT_DECISION', 6112)},"
                         f"{c}.StallReason)"))

    elif step.action == decl.MARK:
        outputs = []
        for mark in step.marks:
            target, expression = [part.strip() for part in mark.split(":=")]
            target = target.replace("Ctx.", f"{u}.")
            if "+" in expression:
                base = expression.split("+")[0].strip().replace("Ctx.", f"{u}.")
                outputs.append(f"ADD({base},1,{target})")
            else:
                outputs.append(f"MOV({expression.strip()},{target})")
        legs.append(_leg(*outputs,
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


def st_program_routine(name: str, logic) -> str:
    lines = "\n".join(
        f'<Line Number="{i}"><![CDATA[{statement}]]></Line>'
        for i, statement in enumerate(logic)
    )
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
    return [c for c in app.chains if c.multi_rendition]


def rendition_ordinal(rendition: str) -> int:
    return decl.RENDITIONS.index(rendition)


def chain_routines(app: decl.Application) -> list[str]:
    """Every rendition of every multi-rendition chain, as program routines."""
    out: list[str] = []
    for chain in multi_chains(app):
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
    """JSR exactly one rendition of the active multi-rendition chain.

    The owner AOI has already run, so the latches and the ordering check are
    settled before any rendition executes - sequence intent still comes second.
    """
    lines: list[str] = []
    unit = f"FRK_{app.name}_Unit"
    select = rendition_tag(app)
    for chain in multi_chains(app):
        lines.append(f"(* {chain.name}: one rendition runs, chosen by {select} *)")
        lines.append(f"IF ({unit}.Mode = {chain.mode_ordinal}) "
                     f"AND ({unit}.Running <> 0) THEN")
        for rendition in chain.renditions:
            target = (sfc_runner_name(app, chain) if rendition == decl.SFC
                      else chain_routine_name(app, chain, rendition))
            lines.append(f"IF {select} = {rendition_ordinal(rendition)} THEN")
            lines.append(f"JSR({target},0);")
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
    if step.action in (decl.ISSUE, decl.ADOPT):
        return f"{ctx}.Done <> 0"
    if step.action == decl.REPORT:
        return f"{ctx}.Done <> 0" if kind == "A" else f"{ctx}.Error <> 0"
    if step.action == decl.DELAY:
        return f"{c}.CurrentStepMs >= {names.cfg}.{step.duration_member}"
    if step.action == decl.AWAIT:
        return " AND ".join(f"({names.sim(x)} <> 0)" for x in step.conditions) or "1=1"
    if step.action == decl.HELD_AWAIT:
        return f"({names.sim(step.hold_condition)} <> 0) AND ({ctx}.Done <> 0)"
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
    # The chart advances on its transition, so the duration is published every
    # scan; the last value written is the duration of the visit.
    lines.append(f"{c}.LastMs[{index}] := {c}.CurrentStepMs;")

    if step.module and step.command:
        module = next(m for m in app.modules if m.name == step.module)
        command = next(cm for cm in module.commands if cm.name == step.command)
        ctx = names.module(step.module)
        issue = [
            f"{ctx}.ParCmd_Command := {command.ordinal};",
            f"{ctx}.ParCmd_Target := {command.target_position};",
            f"{ctx}.Execute := 1;",
        ]
        if step.action == decl.HELD_AWAIT:
            lines += [
                f"IF ({names.sim(step.hold_condition)} <> 0) THEN",
                f"{u}.Held := 0;",
                f"{u}.HeldReason := 0;",
                f"{u}.HeldSeverity := {SEVERITY_LOW};",
                f"{c}.StallReason := 0;",
            ] + issue + [
                "ELSE",
                "(* Held: stand still, publish a LOW named reason, raise no Error *)",
                f"{u}.Held := 1;",
                f"{u}.HeldReason := {step.hold_reason};",
                f"{u}.HeldSeverity := {SEVERITY_LOW};",
                f"{c}.StallReason := {step.hold_reason};",
                f"{ctx}.Execute := 0;",
                "END_IF;",
            ]
        else:
            lines += [f"IF {names.scan} = {u}.StepScan THEN", f"{ctx}.Execute := 0;",
                      "ELSE"] + issue + ["END_IF;"]
            if step.action == decl.ADOPT:
                source = [m.name for m in app.modules].index(step.module) + 1
                lines += [
                    f"IF {ctx}.Error <> 0 THEN",
                    "(* Adopt the child's first-out verbatim *)",
                    f"{u}.Error := 1;",
                    f"{u}.ErrorID := {ctx}.ErrorID;",
                    f"{u}.ErrorSource := {source};",
                    f"{c}.StallReason := {ctx}.ErrorID;",
                    f"{u}.Running := 0;",
                    f"{ctx}.Execute := 0;",
                    "END_IF;",
                ]
            elif step.action == decl.REPORT:
                lines += [
                    f"IF {ctx}.Error <> 0 THEN",
                    "(* Report the child's own first-out; do NOT adopt it *)",
                    f"{u}.ReportedReason := {ctx}.ErrorID;",
                    f"{u}.ReportedCount := {u}.ReportedCount + 1;",
                    f"{ctx}.Execute := 0;",
                    "END_IF;",
                ]
            else:
                lines += [
                    f"IF {ctx}.Error <> 0 THEN",
                    f"{c}.StallReason := {ctx}.ErrorID;",
                    "END_IF;",
                ]

    elif step.action == decl.DELAY:
        lines += [
            f"IF {c}.CurrentStepMs < {names.cfg}.{step.duration_member} THEN",
            f"{c}.StallReason := {app.reasons.get('WAIT_DELAY', 6110)};",
            "END_IF;",
        ]
    elif step.action == decl.AWAIT:
        ready = " AND ".join(f"({names.sim(x)} <> 0)" for x in step.conditions)
        reason = step.hold_reason or app.reasons.get("WAIT_CONDITION", 6111)
        lines += [f"IF NOT ({ready}) THEN", f"{c}.StallReason := {reason};", "END_IF;"]
    elif step.action == decl.DECISION:
        lines += [
            f"{u}.DecisionId := {step.decision_id};",
            f"IF {u}.DecisionAnswer = 0 THEN",
            f"{c}.StallReason := {app.reasons.get('WAIT_DECISION', 6112)};",
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
        lines = "\n".join(
            f'<Line Number="{i}"><![CDATA[{statement}]]></Line>'
            for i, statement in enumerate(
                sfc_action_logic(app, chain, step, steps_order.index(step.number), names))
        )
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
            f'<Line Number="0"><![CDATA[{sfc_condition(app, step, kind, names)}]]></Line>\n'
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
    if multi_chains(app):
        # Which rendition of a multi-rendition chain runs. Writable so the
        # harness can walk one graph in each language in a single session.
        names.append(rendition_tag(app))
    return tuple(names)


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

    Nothing publishes a manifest yet - that is owed work, and the blocking one
    for the gateway. This exists so the rule is enforceable when it does, rather
    than being a sentence someone has to remember.
    """
    excluded = set(harness_only_tags(app))
    published: list[str] = []
    for record in app.records:
        published.append(f"{record.name}Tag")
    for module in app.modules:
        published.append(ctx_tag_for(app, module.name))
    published.append(f"FRK_{app.name}_Unit")
    published.append(f"FRK_{app.name}_Chart")
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
    dispatch = dispatch_logic(app)
    if dispatch:
        lines += [""] + dispatch
    return tuple(lines)


def program_tags(app: decl.Application) -> str:
    tags = sfc_program_tags(app)
    return "<Tags>\n" + "\n".join(tags) + "\n</Tags>" if tags else "<Tags/>"


def programs(app: decl.Application) -> str:
    routines = "\n".join(
        [st_program_routine(app.routine, routine_logic(app))] + chain_routines(app)
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
        "HarnessOnlyTags": list(harness_only_tags(app)),
        "PublishableTags": list(publishable_tags(app)),
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
