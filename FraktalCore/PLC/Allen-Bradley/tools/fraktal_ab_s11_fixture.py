#!/usr/bin/env python3
"""Generate the disposable v33 S11/S4 sequence-execution fixture.

The input is the same fresh, empty 1769-L24ER-QB1B v33 full-project L5X used by
the Phase 0 data-path and S2 nesting fixtures. One graph declaration generates
both AB §3.5 execution forms over the same context contract:

* the AOI-contained ST reference form (``FRK_S11_SeqSt`` nested by an owner
  AOI that calls the root module AOI first), and
* the program-owned native SFC form (``FRK_S11_SfcChain``) driven by the
  generated JSR/SFR wrapper ``FRK_S11_SfcRunner``.

Both forms record their step trace through the same ``FRK_Seq_Step`` service
AOI, consume intent through the same root module AOI, and are compared in the
controller every scan. The fixture therefore measures scan ordering, the
intentional one-scan command/result latency, simultaneous-branch behavior,
reset/re-entry through ``SFR``, Program->Run initialization, and ST/SFC parity.

This is pre-gate evidence tooling, not a production Fraktal runtime generator.
The output is evidence only after SDK import, Studio v33 Verify Controller,
export, canonical comparison, and (when separately authorized) isolated
execution.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256


SCHEMA = "fraktal.ab.s11-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"
TRACE_CAPACITY = 12

# AB §3.5 requires "Execute current active steps only" so one JSR advances at
# most one active step/group. DontScan keeps Rockwell's automatic postscan from
# becoming a second latch authority; InitialStep is belt-and-braces beside the
# wrapper's own SFR.
SFC_EXECUTION_CONTROL = "CurrentActive"
SFC_RESTART_POSITION = "InitialStep"
SFC_LAST_SCAN = "DontScan"


@dataclass(frozen=True)
class GraphStep:
    """One Core step of the single generated graph declaration."""

    number: int
    branch: int
    what: str

    @property
    def step_tag(self) -> str:
        return f"N{self.number}"

    @property
    def action_tag(self) -> str:
        return f"A{self.number}_{self.what}"

    @property
    def trace_value(self) -> int:
        return self.branch * 1000 + self.number


# The minimal parity graph: one linear step, one simultaneous divergence with
# two numbered legs, one convergence, one terminal step. Do not grow this into
# a production-sized chart - AB_IMPLEMENTATION_PLAN §3 Step C forbids it.
ENTRY_STEP = GraphStep(10, 0, "Issue")
LEG_STEPS = (GraphStep(30, 1, "Leg1"), GraphStep(40, 2, "Leg2"))
FINAL_STEP = GraphStep(50, 0, "Complete")
STEPS = (ENTRY_STEP,) + LEG_STEPS + (FINAL_STEP,)

# The ST reference form needs an explicit fork state; the chart holds the same
# state structurally in its branch. The number is excluded from the parity
# comparison for exactly that reason.
ST_FORK_STATE = 20

ENTRY_TRANSITION = "T10"
JOIN_TRANSITION = "T50"

# Entry intent issued on the start scan, consumed one scan later, legs issued,
# leg results consumed, terminal step run: four scans after the start edge.
PREDICTED_SCANS_TO_COMPLETE = 4

SFC_ROUTINE = "FRK_S11_SfcChain"
MAIN_ROUTINE = "FRK_S11Main"
CONTROL_ROUTINE = "FRK_S11_Control"
RUNNER_ROUTINE = "FRK_S11_SfcRunner"
PARITY_ROUTINE = "FRK_S11_Parity"
PROGRAM = "FRK_S11Program"

CTX_TYPE = "FRK_T_S11Ctx"
ST_CTX = "FRK_S11_StCtx"
SFC_CTX = "FRK_S11_SfcCtx"
SCAN_TAG = "FRK_S11_ScanCount"

# Cleared by every start, reset and Program->Run initialization edge. RunCount
# and ResetCount are the epochs that survive a clear.
CLEARED_MEMBERS = (
    "Busy",
    "Done",
    "Step",
    "Leg1Step",
    "Leg2Step",
    "Intent",
    "Leg1Intent",
    "Leg2Intent",
    "Result",
    "Leg1Result",
    "Leg2Result",
    "IntentScan",
    "ConsumedScan",
    "LatencyScans",
    "ModuleOrder",
    "SeqOrder",
    "StartScan",
    "DoneScan",
    "ScansToComplete",
    "TraceCount",
    "TraceOverflow",
)


def ctx_data_type() -> str:
    scalars = (
        "SchemaVersion",
        "Command",
        "Busy",
        "Done",
        "Step",
        "Leg1Step",
        "Leg2Step",
        "Intent",
        "Leg1Intent",
        "Leg2Intent",
        "Result",
        "Leg1Result",
        "Leg2Result",
        "IntentScan",
        "ConsumedScan",
        "LatencyScans",
        "LatencyBad",
        "StartScan",
        "DoneScan",
        "ScansToComplete",
        "OrderCursor",
        "ModuleOrder",
        "SeqOrder",
        "ModuleScans",
        "RunCount",
        "ResetCount",
        "TraceCount",
        "TraceOverflow",
    )
    members = "\n".join(
        f'<Member Name="{name}" DataType="DINT" Dimension="0" Radix="Decimal" '
        'Hidden="false" ExternalAccess="Read Only"/>'
        for name in scalars
    )
    return f"""<DataTypes>
<DataType Name="{CTX_TYPE}" Family="NoFamily" Class="User">
<Members>
{members}
<Member Name="Trace" DataType="DINT" Dimension="{TRACE_CAPACITY}" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
</Members>
</DataType>
</DataTypes>"""


def parameter(
    name: str,
    data_type: str,
    usage: str,
    *,
    radix: str | None = None,
    required: bool = True,
    visible: bool = True,
    constant: bool | None = False,
    external_access: str | None = None,
) -> str:
    attributes = [
        f'Name="{name}"',
        'TagType="Base"',
        f'DataType="{data_type}"',
        f'Usage="{usage}"',
    ]
    if radix is not None:
        attributes.append(f'Radix="{radix}"')
    attributes.extend(
        [
            f'Required="{str(required).lower()}"',
            f'Visible="{str(visible).lower()}"',
        ]
    )
    if constant is not None:
        attributes.append(f'Constant="{str(constant).lower()}"')
    if external_access is not None:
        attributes.append(f'ExternalAccess="{external_access}"')
    return f"<Parameter {' '.join(attributes)}/>"


ENABLE_PARAMETERS = (
    parameter(
        "EnableIn", "BOOL", "Input", radix="Decimal",
        required=False, visible=False, constant=None,
        external_access="Read Only",
    ),
    parameter(
        "EnableOut", "BOOL", "Output", radix="Decimal",
        required=False, visible=False, constant=None,
        external_access="Read Only",
    ),
)


def dint_local(name: str) -> str:
    return f"""<LocalTag Name="{name}" DataType="DINT" Radix="Decimal" ExternalAccess="None">
<DefaultData>00 00 00 00</DefaultData>
<DefaultData Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</DefaultData>
</LocalTag>"""


def instance_local(name: str, data_type: str) -> str:
    return f'<LocalTag Name="{name}" DataType="{data_type}" ExternalAccess="None"/>'


def aoi_definition(
    name: str,
    note: str,
    parameters: tuple[str, ...],
    local_tags: tuple[str, ...],
    logic: tuple[str, ...],
    dependencies: tuple[str, ...],
) -> str:
    parameter_block = "\n".join(parameters)
    local_block = (
        "<LocalTags/>"
        if not local_tags
        else "<LocalTags>\n" + "\n".join(local_tags) + "\n</LocalTags>"
    )
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(logic)
    )
    dependency_block = "\n".join(dependencies)
    return f"""<AddOnInstructionDefinition Name="{name}" Revision="1.0" ExecutePrescan="false" ExecutePostscan="false" ExecuteEnableInFalse="false" CreatedDate="2026-08-13T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-08-13T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
<RevisionNote><![CDATA[{note}]]></RevisionNote>
<Parameters>
{parameter_block}
</Parameters>
{local_block}
<Routines>
<Routine Name="Logic" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
<Dependencies>
{dependency_block}
</Dependencies>
</AddOnInstructionDefinition>"""


CTX_DEPENDENCY = f'<Dependency Type="DataType" Name="{CTX_TYPE}"/>'


def seq_step_aoi() -> str:
    """The FRK_Seq_Step publication service both forms call (AB §3.5)."""
    logic = (
        "Ctx.OrderCursor := Ctx.OrderCursor + 1;",
        "Ctx.SeqOrder := Ctx.OrderCursor;",
        "IF Branch = 0 THEN",
        "Ctx.Step := StepNo;",
        "ELSIF Branch = 1 THEN",
        "Ctx.Leg1Step := StepNo;",
        "ELSE",
        "Ctx.Leg2Step := StepNo;",
        "END_IF;",
        "IF RecordedRun <> Ctx.RunCount THEN",
        f"IF Ctx.TraceCount < {TRACE_CAPACITY} THEN",
        "Ctx.Trace[Ctx.TraceCount] := Branch * 1000 + StepNo;",
        "Ctx.TraceCount := Ctx.TraceCount + 1;",
        "ELSE",
        "Ctx.TraceOverflow := Ctx.TraceOverflow + 1;",
        "END_IF;",
        "RecordedRun := Ctx.RunCount;",
        "END_IF;",
    )
    return aoi_definition(
        "FRK_Seq_Step",
        "Disposable S11 step publication service.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("StepNo", "DINT", "Input", radix="Decimal",
                      external_access="Read Only"),
            parameter("Branch", "DINT", "Input", radix="Decimal",
                      external_access="Read Only"),
        ),
        (dint_local("RecordedRun"),),
        logic,
        (CTX_DEPENDENCY,),
    )


def module_aoi() -> str:
    """The root module AOI: unconditional once per scan, consumes intent."""
    logic = (
        "Ctx.OrderCursor := Ctx.OrderCursor + 1;",
        "Ctx.ModuleOrder := Ctx.OrderCursor;",
        "Ctx.ModuleScans := Ctx.ModuleScans + 1;",
        "IF Ctx.Intent <> 0 THEN",
        "Ctx.Result := Ctx.Intent;",
        "Ctx.ConsumedScan := ScanNo;",
        "Ctx.LatencyScans := ScanNo - Ctx.IntentScan;",
        "IF Ctx.LatencyScans <> 1 THEN",
        "Ctx.LatencyBad := Ctx.LatencyBad + 1;",
        "END_IF;",
        "Ctx.Intent := 0;",
        "END_IF;",
        "IF Ctx.Leg1Intent <> 0 THEN",
        "Ctx.Leg1Result := Ctx.Leg1Intent;",
        "Ctx.Leg1Intent := 0;",
        "END_IF;",
        "IF Ctx.Leg2Intent <> 0 THEN",
        "Ctx.Leg2Result := Ctx.Leg2Intent;",
        "Ctx.Leg2Intent := 0;",
        "END_IF;",
    )
    return aoi_definition(
        "FRK_S11_Module",
        "Disposable S11 root module AOI.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("ScanNo", "DINT", "Input", radix="Decimal",
                      external_access="Read Only"),
        ),
        (),
        logic,
        (CTX_DEPENDENCY,),
    )


def st_sequence_logic() -> tuple[str, ...]:
    """Generate the CASE Seq.Step skeleton from the shared graph declaration."""
    leg1, leg2 = LEG_STEPS
    return (
        "IF Ctx.Busy <> 0 THEN",
        "CASE Ctx.Step OF",
        f"{ENTRY_STEP.number}:",
        f"FRK_Seq_Step(Svc{ENTRY_STEP.number},Ctx,{ENTRY_STEP.number},"
        f"{ENTRY_STEP.branch});",
        f"Ctx.Intent := {ENTRY_STEP.number};",
        "Ctx.IntentScan := ScanNo;",
        f"IF Ctx.Result = {ENTRY_STEP.number} THEN",
        f"Ctx.Step := {ST_FORK_STATE};",
        f"Ctx.Leg1Step := {leg1.number};",
        f"Ctx.Leg2Step := {leg2.number};",
        "END_IF;",
        f"{ST_FORK_STATE}:",
        f"IF Ctx.Leg1Step = {leg1.number} THEN",
        f"FRK_Seq_Step(Svc{leg1.number},Ctx,{leg1.number},{leg1.branch});",
        f"Ctx.Leg1Intent := {leg1.number};",
        f"IF Ctx.Leg1Result = {leg1.number} THEN",
        "Ctx.Leg1Step := 0;",
        "END_IF;",
        "END_IF;",
        f"IF Ctx.Leg2Step = {leg2.number} THEN",
        f"FRK_Seq_Step(Svc{leg2.number},Ctx,{leg2.number},{leg2.branch});",
        f"Ctx.Leg2Intent := {leg2.number};",
        f"IF Ctx.Leg2Result = {leg2.number} THEN",
        "Ctx.Leg2Step := 0;",
        "END_IF;",
        "END_IF;",
        "IF (Ctx.Leg1Step = 0) AND (Ctx.Leg2Step = 0) THEN",
        f"Ctx.Step := {FINAL_STEP.number};",
        "END_IF;",
        f"{FINAL_STEP.number}:",
        f"FRK_Seq_Step(Svc{FINAL_STEP.number},Ctx,{FINAL_STEP.number},"
        f"{FINAL_STEP.branch});",
        "IF Ctx.Done = 0 THEN",
        "Ctx.DoneScan := ScanNo;",
        "Ctx.ScansToComplete := ScanNo - Ctx.StartScan;",
        "END_IF;",
        "Ctx.Done := 1;",
        "Ctx.Busy := 0;",
        "ELSE",
        "Ctx.Step := 0;",
        "Ctx.Busy := 0;",
        "END_CASE;",
        "END_IF;",
    )


def st_sequence_aoi() -> str:
    return aoi_definition(
        "FRK_S11_SeqSt",
        "Disposable S11 ST reference-form sequence AOI.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("ScanNo", "DINT", "Input", radix="Decimal",
                      external_access="Read Only"),
        ),
        tuple(
            instance_local(f"Svc{step.number}", "FRK_Seq_Step") for step in STEPS
        ),
        st_sequence_logic(),
        (CTX_DEPENDENCY, '<Dependency Type="AddOnInstruction" Name="FRK_Seq_Step"/>'),
    )


def owner_aoi() -> str:
    """The owner AOI: root module AOI first, then the nested sequence AOI."""
    logic = (
        "FRK_S11_Module(Module,Ctx,ScanNo);",
        "FRK_S11_SeqSt(Seq,Ctx,ScanNo);",
    )
    return aoi_definition(
        "FRK_S11_Owner",
        "Disposable S11 owner AOI for the ST reference form.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("ScanNo", "DINT", "Input", radix="Decimal",
                      external_access="Read Only"),
        ),
        (
            instance_local("Module", "FRK_S11_Module"),
            instance_local("Seq", "FRK_S11_SeqSt"),
        ),
        logic,
        (
            CTX_DEPENDENCY,
            '<Dependency Type="AddOnInstruction" Name="FRK_S11_Module"/>',
            '<Dependency Type="AddOnInstruction" Name="FRK_S11_SeqSt"/>',
        ),
    )


def aoi_definitions() -> str:
    return (
        "<AddOnInstructionDefinitions>\n"
        + "\n".join(
            [seq_step_aoi(), module_aoi(), st_sequence_aoi(), owner_aoi()]
        )
        + "\n</AddOnInstructionDefinitions>"
    )


def base_tag(name: str, data_type: str, external_access: str | None) -> str:
    access = (
        "" if external_access is None else f' ExternalAccess="{external_access}"'
    )
    return (
        f'<Tag Name="{name}" TagType="Base" DataType="{data_type}" '
        f'Constant="false"{access}/>'
    )


def controller_tags() -> str:
    return "\n".join(
        [
            "<Tags>",
            scalar_tag("FRK_S11_Command", "DINT", "Decimal", "0", "Read/Write"),
            scalar_tag("FRK_S11_ResetRequest", "DINT", "Decimal", "0", "Read/Write"),
            base_tag(ST_CTX, CTX_TYPE, "Read Only"),
            base_tag(SFC_CTX, CTX_TYPE, "Read Only"),
            base_tag("FRK_S11_StOwner", "FRK_S11_Owner", "None"),
            base_tag("FRK_S11_SfcModule", "FRK_S11_Module", "None"),
            scalar_tag(SCAN_TAG, "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S11_JsrCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S11_SfrCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S11_FirstScanCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S11_ParityOk", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag(
                "FRK_S11_ParityFirstMismatch", "DINT", "Decimal", "-1", "Read Only"
            ),
            scalar_tag("FRK_S11_OrderFail", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S11_Complete", "BOOL", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


def program_tags() -> str:
    # External Access is stated explicitly on every tag. An omitted attribute is
    # not preserved: Studio writes its default on export, so the generated
    # document would differ from its own export and a later comparison would
    # read that as drift.
    entries = ["<Tags>"]
    for step in STEPS:
        entries.append(base_tag(step.step_tag, "SFC_STEP", "Read/Write"))
        entries.append(base_tag(step.action_tag, "SFC_ACTION", "Read/Write"))
    for name in (ENTRY_TRANSITION, JOIN_TRANSITION):
        entries.append(
            f'<Tag Name="{name}" TagType="Base" DataType="BOOL" Radix="Decimal" '
            'Constant="false" ExternalAccess="Read/Write"/>'
        )
    for step in STEPS:
        entries.append(
            base_tag(f"FRK_S11_Svc{step.number}", "FRK_Seq_Step", "None")
        )
    for name in (
        "FRK_S11_CommandPrev",
        "FRK_S11_ResetPrev",
        "FRK_S11_StartEdge",
        "FRK_S11_ResetEdge",
        "FRK_S11_InitEdge",
        "FRK_S11_ParityIndex",
    ):
        entries.append(scalar_tag(name, "DINT", "Decimal", "0", "Read Only"))
    entries.append("</Tags>")
    return "\n".join(entries)


def main_routine_logic() -> tuple[str, ...]:
    return (
        f"{SCAN_TAG} := {SCAN_TAG} + 1;",
        f"{ST_CTX}.SchemaVersion := {SCHEMA_VERSION};",
        f"{SFC_CTX}.SchemaVersion := {SCHEMA_VERSION};",
        f"{ST_CTX}.OrderCursor := 0;",
        f"{SFC_CTX}.OrderCursor := 0;",
        f"{ST_CTX}.Command := FRK_S11_Command;",
        f"{SFC_CTX}.Command := FRK_S11_Command;",
        f"JSR({CONTROL_ROUTINE},0);",
        f"FRK_S11_Owner(FRK_S11_StOwner,{ST_CTX},{SCAN_TAG});",
        f"FRK_S11_Module(FRK_S11_SfcModule,{SFC_CTX},{SCAN_TAG});",
        f"JSR({RUNNER_ROUTINE},0);",
        f"JSR({PARITY_ROUTINE},0);",
        "FRK_S11_Complete := 1;",
    )


def control_routine_logic() -> tuple[str, ...]:
    clear = tuple(
        statement
        for member in CLEARED_MEMBERS
        for statement in (
            f"{ST_CTX}.{member} := 0;",
            f"{SFC_CTX}.{member} := 0;",
        )
    )
    return (
        "IF (FRK_S11_Command = 1) AND (FRK_S11_CommandPrev = 0) THEN",
        "FRK_S11_StartEdge := 1;",
        "ELSE",
        "FRK_S11_StartEdge := 0;",
        "END_IF;",
        "FRK_S11_CommandPrev := FRK_S11_Command;",
        "IF (FRK_S11_ResetRequest = 1) AND (FRK_S11_ResetPrev = 0) THEN",
        "FRK_S11_ResetEdge := 1;",
        "ELSE",
        "FRK_S11_ResetEdge := 0;",
        "END_IF;",
        "FRK_S11_ResetPrev := FRK_S11_ResetRequest;",
        "FRK_S11_InitEdge := 0;",
        "IF S:FS THEN",
        "FRK_S11_InitEdge := 1;",
        "FRK_S11_FirstScanCount := FRK_S11_FirstScanCount + 1;",
        "END_IF;",
        "IF (FRK_S11_StartEdge = 1) OR (FRK_S11_ResetEdge = 1) "
        "OR (FRK_S11_InitEdge = 1) THEN",
    ) + clear + (
        f"{ST_CTX}.ResetCount := {ST_CTX}.ResetCount + 1;",
        f"{SFC_CTX}.ResetCount := {SFC_CTX}.ResetCount + 1;",
        "END_IF;",
        "IF FRK_S11_StartEdge = 1 THEN",
        f"{ST_CTX}.RunCount := {ST_CTX}.RunCount + 1;",
        f"{SFC_CTX}.RunCount := {SFC_CTX}.RunCount + 1;",
        f"{ST_CTX}.StartScan := {SCAN_TAG};",
        f"{SFC_CTX}.StartScan := {SCAN_TAG};",
        f"{ST_CTX}.Busy := 1;",
        f"{ST_CTX}.Step := {ENTRY_STEP.number};",
        f"{SFC_CTX}.Busy := 1;",
        "END_IF;",
    )


def runner_routine_logic() -> tuple[str, ...]:
    """The generated JSR/SFR wrapper of AB §3.5."""
    return (
        "IF (FRK_S11_StartEdge = 1) OR (FRK_S11_ResetEdge = 1) "
        "OR (FRK_S11_InitEdge = 1) THEN",
        f"SFR({SFC_ROUTINE},{ENTRY_STEP.step_tag});",
        "FRK_S11_SfrCount := FRK_S11_SfrCount + 1;",
        "END_IF;",
        f"IF {SFC_CTX}.Busy <> 0 THEN",
        "FRK_S11_JsrCount := FRK_S11_JsrCount + 1;",
        f"JSR({SFC_ROUTINE},0);",
        "END_IF;",
    )


def parity_routine_logic() -> tuple[str, ...]:
    compared = ("Done", "Busy", "Result", "Leg1Result", "Leg2Result",
                "TraceCount", "LatencyBad", "TraceOverflow", "ScansToComplete")
    checks = tuple(
        statement
        for member in compared
        for statement in (
            f"IF {ST_CTX}.{member} <> {SFC_CTX}.{member} THEN",
            "FRK_S11_ParityOk := 0;",
            "END_IF;",
        )
    )
    return (
        "FRK_S11_ParityOk := 1;",
        "FRK_S11_ParityFirstMismatch := -1;",
        f"FOR FRK_S11_ParityIndex := 0 TO {TRACE_CAPACITY - 1} DO",
        f"IF {ST_CTX}.Trace[FRK_S11_ParityIndex] <> "
        f"{SFC_CTX}.Trace[FRK_S11_ParityIndex] THEN",
        "FRK_S11_ParityOk := 0;",
        "IF FRK_S11_ParityFirstMismatch = -1 THEN",
        "FRK_S11_ParityFirstMismatch := FRK_S11_ParityIndex;",
        "END_IF;",
        "END_IF;",
        "END_FOR;",
    ) + checks + (
        f"IF ({ST_CTX}.Busy <> 0) AND ({ST_CTX}.SeqOrder <= {ST_CTX}.ModuleOrder) THEN",
        "FRK_S11_OrderFail := FRK_S11_OrderFail + 1;",
        "END_IF;",
        f"IF ({SFC_CTX}.Busy <> 0) AND ({SFC_CTX}.SeqOrder <= {SFC_CTX}.ModuleOrder) THEN",
        "FRK_S11_OrderFail := FRK_S11_OrderFail + 1;",
        "END_IF;",
    )


def st_routine(name: str, logic: tuple[str, ...]) -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(logic)
    )
    return f"""<Routine Name="{name}" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>"""


def action_logic(step: GraphStep) -> tuple[str, ...]:
    call = (
        f"FRK_Seq_Step(FRK_S11_Svc{step.number},{SFC_CTX},"
        f"{step.number},{step.branch});",
    )
    if step is ENTRY_STEP:
        return call + (
            f"{SFC_CTX}.Intent := {step.number};",
            f"{SFC_CTX}.IntentScan := {SCAN_TAG};",
        )
    if step is FINAL_STEP:
        return call + (
            f"IF {SFC_CTX}.Done = 0 THEN",
            f"{SFC_CTX}.DoneScan := {SCAN_TAG};",
            f"{SFC_CTX}.ScansToComplete := {SCAN_TAG} - {SFC_CTX}.StartScan;",
            "END_IF;",
            f"{SFC_CTX}.Done := 1;",
            f"{SFC_CTX}.Busy := 0;",
        )
    return call + (f"{SFC_CTX}.Leg{step.branch}Intent := {step.number};",)


def transition_condition(name: str) -> str:
    if name == ENTRY_TRANSITION:
        return f"{SFC_CTX}.Result = {ENTRY_STEP.number}"
    leg1, leg2 = LEG_STEPS
    return (
        f"({SFC_CTX}.Leg{leg1.branch}Result = {leg1.number}) AND "
        f"({SFC_CTX}.Leg{leg2.branch}Result = {leg2.number})"
    )


def sfc_routine() -> str:
    """Serialize the chart from the same graph declaration as the ST form.

    Element order and ID assignment follow Studio's own export order: steps
    sorted by operand with their actions interleaved, then transitions, then
    branches, then directed links sorted by source.
    """
    layout = {
        ENTRY_STEP.step_tag: (240, 60),
        LEG_STEPS[0].step_tag: (140, 300),
        LEG_STEPS[1].step_tag: (400, 300),
        FINAL_STEP.step_tag: (240, 600),
    }
    identifiers: dict[str, int] = {}
    body: list[str] = []
    next_id = 0

    for step in sorted(STEPS, key=lambda item: item.step_tag):
        x, y = layout[step.step_tag]
        step_id = next_id
        action_id = next_id + 1
        next_id += 2
        identifiers[step.step_tag] = step_id
        lines = "\n".join(
            f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
            for index, statement in enumerate(action_logic(step))
        )
        body.append(
            f'<Step ID="{step_id}" X="{x}" Y="{y}" Operand="{step.step_tag}" '
            f'HideDesc="true" DescX="{x + 54}" DescY="{y - 15}" DescWidth="0" '
            f'InitialStep="{str(step is ENTRY_STEP).lower()}" '
            'PresetUsesExpr="false" LimitHighUsesExpr="false" '
            'LimitLowUsesExpr="false" ShowActions="true">\n'
            f'<Action ID="{action_id}" Operand="{step.action_tag}" '
            'Qualifier="NonStored" IsBoolean="false" PresetUsesExpr="false">\n'
            "<Body>\n<STContent>\n"
            f"{lines}\n"
            "</STContent>\n</Body>\n</Action>\n</Step>"
        )

    transition_layout = {ENTRY_TRANSITION: (240, 160), JOIN_TRANSITION: (240, 500)}
    for name in sorted(transition_layout):
        x, y = transition_layout[name]
        identifiers[name] = next_id
        body.append(
            f'<Transition ID="{next_id}" X="{x}" Y="{y}" Operand="{name}" '
            f'HideDesc="true" DescX="{x + 35}" DescY="{y - 15}" DescWidth="0">\n'
            "<Condition>\n<STContent>\n"
            f'<Line Number="0"><![CDATA[{transition_condition(name)}]]></Line>\n'
            "</STContent>\n</Condition>\n</Transition>"
        )
        next_id += 1

    diverge_id = next_id
    diverge_legs = (next_id + 1, next_id + 2)
    next_id += 3
    body.append(
        f'<Branch ID="{diverge_id}" Y="240" BranchType="Simultaneous" '
        'BranchFlow="Diverge">\n'
        + "\n".join(f'<Leg ID="{leg}"/>' for leg in diverge_legs)
        + "\n</Branch>"
    )
    converge_id = next_id
    converge_legs = (next_id + 1, next_id + 2)
    next_id += 3
    body.append(
        f'<Branch ID="{converge_id}" Y="420" BranchType="Simultaneous" '
        'BranchFlow="Converge">\n'
        + "\n".join(f'<Leg ID="{leg}"/>' for leg in converge_legs)
        + "\n</Branch>"
    )

    links = [
        (identifiers[ENTRY_STEP.step_tag], identifiers[ENTRY_TRANSITION]),
        (identifiers[ENTRY_TRANSITION], diverge_id),
        (identifiers[JOIN_TRANSITION], identifiers[FINAL_STEP.step_tag]),
        (converge_id, identifiers[JOIN_TRANSITION]),
    ]
    for leg_step, diverge_leg, converge_leg in zip(
        LEG_STEPS, diverge_legs, converge_legs
    ):
        links.append((diverge_leg, identifiers[leg_step.step_tag]))
        links.append((identifiers[leg_step.step_tag], converge_leg))
    body.extend(
        f'<DirectedLink FromID="{source}" ToID="{target}" Show="true"/>'
        for source, target in sorted(links)
    )

    content = "\n".join(body)
    return f"""<Routine Name="{SFC_ROUTINE}" Type="SFC">
<SFCContent SheetSize="Letter - 8.5 x 11 in" SheetOrientation="Landscape" StepName="Step" TransitionName="Tran" ActionName="Action" StopName="Stop">
{content}
</SFCContent>
</Routine>"""


def programs() -> str:
    routines = "\n".join(
        [
            st_routine(CONTROL_ROUTINE, control_routine_logic()),
            st_routine(MAIN_ROUTINE, main_routine_logic()),
            st_routine(PARITY_ROUTINE, parity_routine_logic()),
            sfc_routine(),
            st_routine(RUNNER_ROUTINE, runner_routine_logic()),
        ]
    )
    return f"""<Programs>
<Program Name="{PROGRAM}" TestEdits="false" MainRoutineName="{MAIN_ROUTINE}" Disabled="false" UseAsFolder="false">
{program_tags()}
<Routines>
{routines}
</Routines>
</Program>
</Programs>"""


TASKS = f"""<Tasks>
<Task Name="FRK_S11Task" Type="PERIODIC" Rate="10" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def expected_trace() -> tuple[int, ...]:
    return tuple(step.trace_value for step in STEPS)


def all_generated_logic() -> str:
    statements: list[str] = []
    for producer in (
        main_routine_logic,
        control_routine_logic,
        runner_routine_logic,
        parity_routine_logic,
        st_sequence_logic,
    ):
        statements.extend(producer())
    for step in STEPS:
        statements.extend(action_logic(step))
    for name in (ENTRY_TRANSITION, JOIN_TRANSITION):
        statements.append(transition_condition(name))
    return "\n".join(statements)


def generate(source: Path, output: Path) -> dict[str, object]:
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
        f'ProcessorType="{CONTROLLER}"',
        f'MajorRev="{REVISION}"',
        '<Controller Use="Target" Name="FraktalPhase0"',
        "<DataTypes/>",
        "<AddOnInstructionDefinitions/>",
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 fixture: {missing}")

    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", all_generated_logic()):
        raise AssertionError("fixture logic contains an I/O operand")

    text = replace_once(text, "<DataTypes/>", ctx_data_type())
    text = replace_once(text, "<AddOnInstructionDefinitions/>", aoi_definitions())
    text = replace_once(text, "<Tags/>", controller_tags())
    text = replace_once(text, "<Programs/>", programs())
    text = replace_once(text, "<Tasks/>", TASKS)

    for attribute, value in (
        ("SFCExecutionControl", SFC_EXECUTION_CONTROL),
        ("SFCRestartPosition", SFC_RESTART_POSITION),
        ("SFCLastScan", SFC_LAST_SCAN),
    ):
        text, count = re.subn(
            rf'{attribute}="[A-Za-z]+"', f'{attribute}="{value}"', text, count=1
        )
        if count != 1:
            raise ValueError(f"source did not carry exactly one {attribute}")

    text, inhibit_count = re.subn(
        r'(<Module Name="Discrete_IO"[^>]*\bInhibited=")false("[^>]*>)',
        r"\1true\2",
        text,
        count=1,
    )
    if inhibit_count != 1:
        raise ValueError("embedded Discrete_IO module was not inhibited exactly once")

    output.write_text(text, encoding="utf-8", newline="\n")
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Source": str(source),
        "SourceSha256": sha256(source),
        "Output": str(output),
        "OutputSha256": sha256(output),
        "Controller": CONTROLLER,
        "MajorRevision": int(REVISION),
        "PhysicalIoReferences": 0,
        "EmbeddedIoInhibited": True,
        "SfcExecutionControl": SFC_EXECUTION_CONTROL,
        "SfcRestartPosition": SFC_RESTART_POSITION,
        "SfcLastScan": SFC_LAST_SCAN,
        "AoiDefinitions": 4,
        "SfcRoutines": 1,
        "SfcSteps": len(STEPS),
        "SfcActions": len(STEPS),
        "SfcTransitions": 2,
        "SfcSimultaneousBranches": 2,
        "ExpectedTrace": list(expected_trace()),
        "ExpectedLatencyScans": 1,
        # Derived from the generated order, not yet measured: one scan to issue
        # the entry intent, one per consumed result, one to run the terminal
        # step. The controller records the real number in ScansToComplete.
        "PredictedScansToComplete": PREDICTED_SCANS_TO_COMPLETE,
        "WritableInputs": ["FRK_S11_Command", "FRK_S11_ResetRequest"],
        "Programs": 1,
        "Routines": 5,
        "Tasks": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        evidence = generate(args.source, args.output)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
