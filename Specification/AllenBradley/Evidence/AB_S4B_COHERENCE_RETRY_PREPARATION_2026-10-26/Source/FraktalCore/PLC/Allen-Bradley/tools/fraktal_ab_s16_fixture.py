#!/usr/bin/env python3
"""Generate the disposable v33 S16 command-handshake and mode-execution fixture.

The input is the same fresh, empty 1769-L24ER-QB1B v33 full-project L5X used by
the Phase 0 data-path, S2 nesting and S11 sequence fixtures. One declaration
generates a press-*shaped* rig that is deliberately not a press:

* ``FRK_S16_Axis`` — a Control-Module-shaped AOI carrying a miniature
  ``Par``/``ParCmd``/``OutCmd``/``OutImm`` contract and implementing the Core
  §6.1 PLCopen handshake over a plant simulated entirely in controller tags;
* ``FRK_S16_Mode`` — a mode owner running two chains over that one module: an
  AUTO step chain (§6.2) that cycles until stopped, and a MANUAL behavior.

It measures what S11 measured for §3.5 sequence execution, but for §6.1
commands: the Execute/Busy/Done/Error/ErrorID/Aborted contract, Execute-drop
reset to READY, abort with no self-resume, a HELD condition that is BUSY with a
LOW-severity reason and auto-resumes without raising Error, restart by re-issue
after a fault, mode switching mid-cycle, and the S11 ordering rule that root
module logic runs unconditionally and ahead of sequence intent with a one-scan
command/result loop.

Scope limits are deliberate and enforced by the tests: no recipe, no release
report, no traceability, no HMI contract, no mailbox/registry/manifest, no
reusable module library, no production naming. This is pre-gate evidence
tooling, not a production Fraktal runtime generator. The output is evidence only
after SDK import, Studio v33 Verify Controller, export, canonical comparison,
and — when separately authorized — isolated execution.

Every scalar in the context is a ``DINT``, including the handshake booleans,
which are carried as 0/1. That follows the S11 fixture shape and keeps the CIP
payload inside the layout S12 actually measured; §6.1 semantics are what this
fixture proves, not bit packing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256


SCHEMA = "fraktal.ab.s16-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

PROGRAM = "FRK_S16Program"
MAIN_ROUTINE = "FRK_S16Main"
CTX_TYPE = "FRK_T_S16Ctx"
CTX_TAG = "FRK_S16_Ctx"

AXIS_AOI = "FRK_S16_Axis"
MODE_AOI = "FRK_S16_Mode"
AXIS_INSTANCE = "FRK_S16_AxisInst"
MODE_INSTANCE = "FRK_S16_ModeInst"

# The periodic task rate. S12 removed TIME/TIME32 from this baseline, so every
# duration in this fixture is a range-checked DINT of milliseconds (AB §3.8)
# and elapsed time is integrated from this constant, never from a timer type.
TASK_RATE_MS = 10

# E_ExecState transport ordinals (Core §3.10(a')). These shall not be
# renumbered; Held is deliberately not one of them (Core §6.1).
STATE_READY = 0
STATE_BUSY = 1
STATE_DONE = 2
STATE_ERROR = 3
STATE_ABORTED = 4

# E_Severity ordinals (Core §8): LOW=0, MED=1, HIGH=2.
SEVERITY_LOW = 0
SEVERITY_HIGH = 2

# Fixture-local reason codes. A production binding draws these from E_Reason
# (§8.8); a disposable fixture must not invent entries in that enumeration, so
# these are deliberately fixture-scoped numbers.
REASON_NONE = 0
REASON_HELD_PERMISSIVE = 6101
REASON_DEVICE_FAULT = 6102
REASON_TIMEOUT = 6103
REASON_ABORT_REQUEST = 6104

# Mode ordinals for the two generated chains.
MODE_AUTO = 0
MODE_MANUAL = 1

# The simulated plant. Position integrates toward the latched target by
# SPEED_PER_SCAN each scan, so a full A->B move takes four scans.
POS_MIN = 0
POS_MAX = 100
SPEED_PER_SCAN = 25
TARGET_A = 100
TARGET_B = 0
DEFAULT_TIMEOUT_MS = 500

# AUTO chain step numbers follow the Core §6.5 convention: N000 init, user
# steps in increments, N999 finish, finish loops back so the mode sequence
# cycles until stopped (§6.2). Kept to two command steps on purpose.
STEP_INIT = 0
STEP_MOVE_A = 100
STEP_MOVE_B = 110
STEP_FINISH = 999

# Bounded write surface. The executor may touch these five controller tags and
# nothing else, and restores every one of them.
WRITABLE_INPUTS = (
    "FRK_S16_Command",
    "FRK_S16_Abort",
    "FRK_S16_ModeSelect",
    "FRK_S16_HoldRequest",
    "FRK_S16_FaultRequest",
)


@dataclass(frozen=True)
class Member:
    """One context member. Every scalar is a DINT (see the module docstring)."""

    name: str
    note: str


# The miniature module contract. Grouped by the Core §3.12 role each member
# plays so the record can show the contract shape without shipping the real one.
PAR_MEMBERS = (
    Member("Par_Speed", "plant units advanced per scan"),
    Member("Par_TimeoutMs", "range-checked DINT duration (AB §3.8, S12)"),
)
PARCMD_MEMBERS = (
    Member("ParCmd_Target", "commanded target, sampled by the caller"),
    Member("ParCmd_Latched", "value latched on the Execute rising edge"),
)
OUTCMD_MEMBERS = (
    Member("OutCmd_FinalPos", "valid only while Done"),
    Member("OutCmd_Ok", "1 when the command completed successfully"),
)
OUTIMM_MEMBERS = (
    Member("OutImm_Pos", "live simulated position, published every scan"),
    Member("OutImm_ExecState", "E_ExecState ordinal"),
    Member("OutImm_Held", "Core §6.1 Held flag, orthogonal to ExecState"),
    Member("OutImm_Reason", "first-out condition preventing completion"),
    Member("OutImm_Severity", "E_Severity of OutImm_Reason"),
)
HANDSHAKE_MEMBERS = (
    Member("Execute", "PLCopen Execute input"),
    Member("ExecutePrev", "edge memory for Execute"),
    Member("Abort", "PLCopen Abort input"),
    Member("Busy", "PLCopen Busy output"),
    Member("Done", "PLCopen Done output"),
    Member("Error", "PLCopen Error output"),
    Member("Aborted", "PLCopen Aborted output"),
    Member("ErrorID", "PLCopen numeric reason, promoted from OutImm_Reason"),
    Member("ElapsedMs", "integrated from TASK_RATE_MS; frozen while Held"),
)
EVIDENCE_MEMBERS = (
    Member("RunCount", "accepted Execute edges"),
    Member("DoneCount", "completions"),
    Member("AbortCount", "accepted aborts"),
    Member("ErrorCount", "faults raised"),
    Member("HeldScans", "scans spent Held"),
    Member("ResetCount", "Execute-drop resets to READY"),
    Member("ModuleScan", "scan number in which the module AOI last ran"),
    Member("SeqScan", "scan number in which the mode owner last ran"),
    Member("OrderFail", "times the mode owner ran before the module"),
    Member("CmdIssueScan", "scan in which the chain raised Execute"),
    Member("IntentScan", "scan in which the module accepted the edge"),
    Member("LatencyScans", "IntentScan - CmdIssueScan; shall be exactly 1"),
    Member("LatencyBad", "times LatencyScans was not 1"),
    Member("Step", "current AUTO chain step number"),
    Member("Mode", "active mode ordinal"),
    Member("ModeSwitches", "mode changes observed"),
    Member("CycleCount", "completed AUTO cycles"),
    Member("ManualCount", "completed MANUAL commands"),
)

CTX_MEMBERS = (
    (Member("SchemaVersion", "fixture schema version"),)
    + PAR_MEMBERS
    + PARCMD_MEMBERS
    + OUTCMD_MEMBERS
    + OUTIMM_MEMBERS
    + HANDSHAKE_MEMBERS
    + EVIDENCE_MEMBERS
)

# Cleared on every accepted Execute edge so a re-issue after a fault starts
# from a known state. RunCount and the other epochs deliberately survive.
CLEARED_ON_START = (
    "Done",
    "Error",
    "Aborted",
    "ErrorID",
    "OutCmd_FinalPos",
    "OutCmd_Ok",
    "OutImm_Reason",
    "OutImm_Severity",
    "ElapsedMs",
)


def ctx_data_type() -> str:
    members = "\n".join(
        f'<Member Name="{member.name}" DataType="DINT" Dimension="0" '
        f'Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>'
        for member in CTX_MEMBERS
    )
    return f"""<DataTypes>
<DataType Name="{CTX_TYPE}" Family="NoFamily" Class="User">
<Members>
{members}
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


def aoi_definition(
    name: str,
    note: str,
    parameters: tuple[str, ...],
    logic: tuple[str, ...],
    ctx_type: str | None = None,
) -> str:
    """Emit one AOI definition.

    ``ctx_type`` names the context UDT this AOI declares a dependency on. It is
    a parameter so the reference suite can reuse this machinery verbatim under
    its own type name rather than growing a second copy of it.
    """
    ctx_type = ctx_type or CTX_TYPE
    parameter_block = "\n".join(parameters)
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(logic)
    )
    return f"""<AddOnInstructionDefinition Name="{name}" Revision="1.0" ExecutePrescan="false" ExecutePostscan="false" ExecuteEnableInFalse="false" CreatedDate="2026-09-06T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-09-06T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
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
<Dependency Type="DataType" Name="{ctx_type}"/>
</Dependencies>
</AddOnInstructionDefinition>"""


def axis_logic() -> tuple[str, ...]:
    """Core §6.1 handshake over a simulated plant.

    Ordering matters and is asserted by the fixture itself: this AOI records the
    scan in which it ran, and the mode owner faults if it ever runs first.
    """
    return (
        "(* S16 module AOI - runs unconditionally, ahead of any sequence *)",
        "Ctx.ModuleScan := Scan;",
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
        "END_IF;",
        "",
        "(* Rising edge accepts the command and latches ParCmd *)",
        "IF (Ctx.Execute <> 0) AND (Ctx.ExecutePrev = 0) THEN",
        "Ctx.ParCmd_Latched := Ctx.ParCmd_Target;",
        "Ctx.Busy := 1;",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.RunCount := Ctx.RunCount + 1;",
        "Ctx.IntentScan := Scan;",
        "Ctx.LatencyScans := Scan - Ctx.CmdIssueScan;",
        "IF Ctx.LatencyScans <> 1 THEN",
        "Ctx.LatencyBad := Ctx.LatencyBad + 1;",
        "END_IF;",
    ) + tuple(
        f"Ctx.{member} := 0;" for member in CLEARED_ON_START
    ) + (
        "END_IF;",
        "Ctx.ExecutePrev := Ctx.Execute;",
        "",
        "(* Abort wins over progress and never self-resumes *)",
        "IF (Ctx.Abort <> 0) AND (Ctx.Busy <> 0) THEN",
        "Ctx.Busy := 0;",
        "Ctx.Aborted := 1;",
        f"Ctx.OutImm_ExecState := {STATE_ABORTED};",
        f"Ctx.OutImm_Reason := {REASON_ABORT_REQUEST};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        "Ctx.AbortCount := Ctx.AbortCount + 1;",
        "END_IF;",
        "",
        "(* While BUSY: fault beats hold, hold beats progress *)",
        "IF Ctx.Busy <> 0 THEN",
        "IF Fault <> 0 THEN",
        "Ctx.Busy := 0;",
        "Ctx.Error := 1;",
        f"Ctx.ErrorID := {REASON_DEVICE_FAULT};",
        f"Ctx.OutImm_Reason := {REASON_DEVICE_FAULT};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        "ELSIF Hold <> 0 THEN",
        "(* HELD: BUSY, named LOW reason, no Error, no progress, no timeout *)",
        "Ctx.OutImm_Held := 1;",
        f"Ctx.OutImm_Reason := {REASON_HELD_PERMISSIVE};",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.OutImm_ExecState := {STATE_BUSY};",
        "Ctx.HeldScans := Ctx.HeldScans + 1;",
        "ELSE",
        "Ctx.OutImm_Held := 0;",
        "Ctx.OutImm_Reason := 0;",
        f"Ctx.OutImm_Severity := {SEVERITY_LOW};",
        f"Ctx.ElapsedMs := Ctx.ElapsedMs + {TASK_RATE_MS};",
        "IF Ctx.OutImm_Pos < Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.OutImm_Pos + Ctx.Par_Speed;",
        "IF Ctx.OutImm_Pos > Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.ParCmd_Latched;",
        "END_IF;",
        "ELSIF Ctx.OutImm_Pos > Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.OutImm_Pos - Ctx.Par_Speed;",
        "IF Ctx.OutImm_Pos < Ctx.ParCmd_Latched THEN",
        "Ctx.OutImm_Pos := Ctx.ParCmd_Latched;",
        "END_IF;",
        "END_IF;",
        "IF Ctx.OutImm_Pos = Ctx.ParCmd_Latched THEN",
        "Ctx.Busy := 0;",
        "Ctx.Done := 1;",
        "Ctx.OutCmd_FinalPos := Ctx.OutImm_Pos;",
        "Ctx.OutCmd_Ok := 1;",
        f"Ctx.OutImm_ExecState := {STATE_DONE};",
        "Ctx.DoneCount := Ctx.DoneCount + 1;",
        "ELSIF Ctx.ElapsedMs > Ctx.Par_TimeoutMs THEN",
        "Ctx.Busy := 0;",
        "Ctx.Error := 1;",
        f"Ctx.ErrorID := {REASON_TIMEOUT};",
        f"Ctx.OutImm_Reason := {REASON_TIMEOUT};",
        f"Ctx.OutImm_Severity := {SEVERITY_HIGH};",
        f"Ctx.OutImm_ExecState := {STATE_ERROR};",
        "Ctx.ErrorCount := Ctx.ErrorCount + 1;",
        "END_IF;",
        "END_IF;",
        "END_IF;",
    )


def mode_logic() -> tuple[str, ...]:
    """The mode owner: an AUTO step chain and a MANUAL behavior over one module.

    The AUTO chain follows Core §6.2/§6.5 - N000 init, two command steps, N999
    finish looping back so the sequence cycles until stopped.
    """
    return (
        "(* S16 mode owner - runs only after the module AOI, and checks it *)",
        "Ctx.SeqScan := Scan;",
        "IF Ctx.ModuleScan <> Scan THEN",
        "Ctx.OrderFail := Ctx.OrderFail + 1;",
        "END_IF;",
        "",
        "(* Mode change stands the chain down; it never resumes by itself *)",
        "IF Sel <> Ctx.Mode THEN",
        "Ctx.ModeSwitches := Ctx.ModeSwitches + 1;",
        "Ctx.Mode := Sel;",
        "Ctx.Execute := 0;",
        f"Ctx.Step := {STEP_INIT};",
        "END_IF;",
        "",
        f"IF Ctx.Mode = {MODE_AUTO} THEN",
        "(* Done advances the step and drops Execute (Core §6.1/§6.5) *)",
        f"IF Ctx.Step = {STEP_INIT} THEN",
        "IF Run <> 0 THEN",
        f"Ctx.ParCmd_Target := {TARGET_A};",
        "Ctx.Execute := 1;",
        "Ctx.CmdIssueScan := Scan;",
        f"Ctx.Step := {STEP_MOVE_A};",
        "END_IF;",
        f"ELSIF Ctx.Step = {STEP_MOVE_A} THEN",
        "IF Ctx.Done <> 0 THEN",
        "Ctx.Execute := 0;",
        f"Ctx.Step := {STEP_MOVE_B};",
        "ELSIF (Ctx.Error <> 0) OR (Ctx.Aborted <> 0) THEN",
        "Ctx.Execute := 0;",
        f"Ctx.Step := {STEP_INIT};",
        "END_IF;",
        f"ELSIF Ctx.Step = {STEP_MOVE_B} THEN",
        "IF Ctx.Execute = 0 THEN",
        f"Ctx.ParCmd_Target := {TARGET_B};",
        "Ctx.Execute := 1;",
        "Ctx.CmdIssueScan := Scan;",
        "ELSIF Ctx.Done <> 0 THEN",
        "Ctx.Execute := 0;",
        f"Ctx.Step := {STEP_FINISH};",
        "ELSIF (Ctx.Error <> 0) OR (Ctx.Aborted <> 0) THEN",
        "Ctx.Execute := 0;",
        f"Ctx.Step := {STEP_INIT};",
        "END_IF;",
        f"ELSIF Ctx.Step = {STEP_FINISH} THEN",
        "Ctx.CycleCount := Ctx.CycleCount + 1;",
        f"Ctx.Step := {STEP_INIT};",
        "END_IF;",
        "ELSE",
        "(* MANUAL: one command per request, no cycling *)",
        "IF (Run <> 0) AND (Ctx.Execute = 0) AND (Ctx.Done = 0) THEN",
        f"Ctx.ParCmd_Target := {TARGET_A};",
        "Ctx.Execute := 1;",
        "Ctx.CmdIssueScan := Scan;",
        "ELSIF Ctx.Done <> 0 THEN",
        "Ctx.Execute := 0;",
        "Ctx.ManualCount := Ctx.ManualCount + 1;",
        "ELSIF (Ctx.Error <> 0) OR (Ctx.Aborted <> 0) THEN",
        "Ctx.Execute := 0;",
        "END_IF;",
        "END_IF;",
    )


def aoi_definitions() -> str:
    axis = aoi_definition(
        AXIS_AOI,
        "S16 disposable module AOI: Core §6.1 handshake over a simulated plant.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("Scan", "DINT", "Input", radix="Decimal"),
            parameter("Hold", "DINT", "Input", radix="Decimal"),
            parameter("Fault", "DINT", "Input", radix="Decimal"),
        ),
        axis_logic(),
    )
    mode = aoi_definition(
        MODE_AOI,
        "S16 disposable mode owner: AUTO step chain and MANUAL behavior.",
        ENABLE_PARAMETERS
        + (
            parameter("Ctx", CTX_TYPE, "InOut"),
            parameter("Scan", "DINT", "Input", radix="Decimal"),
            parameter("Sel", "DINT", "Input", radix="Decimal"),
            parameter("Run", "DINT", "Input", radix="Decimal"),
        ),
        mode_logic(),
    )
    return (
        "<AddOnInstructionDefinitions>\n"
        + axis
        + "\n"
        + mode
        + "\n</AddOnInstructionDefinitions>"
    )


def ctx_tag() -> str:
    members = "\n".join(
        f'<DataValueMember Name="{member.name}" DataType="DINT" '
        f'Radix="Decimal" Value="{_initial_value(member.name)}"/>'
        for member in CTX_MEMBERS
    )
    return f"""<Tag Name="{CTX_TAG}" TagType="Base" DataType="{CTX_TYPE}" Constant="false" ExternalAccess="Read/Write">
<Data Format="Decorated">
<Structure DataType="{CTX_TYPE}">
{members}
</Structure>
</Data>
</Tag>"""


def _initial_value(name: str) -> int:
    if name == "SchemaVersion":
        return SCHEMA_VERSION
    if name == "Par_Speed":
        return SPEED_PER_SCAN
    if name == "Par_TimeoutMs":
        return DEFAULT_TIMEOUT_MS
    return 0


def controller_tags() -> str:
    tags = [ctx_tag()]
    for name in WRITABLE_INPUTS:
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", "Read/Write"))
    for name in ("FRK_S16_ScanCount", "FRK_S16_OrderFail", "FRK_S16_LatencyBad"):
        tags.append(scalar_tag(name, "DINT", "Decimal", "0", "Read Only"))
    tags.append(
        f'<Tag Name="{AXIS_INSTANCE}" TagType="Base" DataType="{AXIS_AOI}" '
        f'Constant="false" ExternalAccess="None"/>'
    )
    tags.append(
        f'<Tag Name="{MODE_INSTANCE}" TagType="Base" DataType="{MODE_AOI}" '
        f'Constant="false" ExternalAccess="None"/>'
    )
    return "<Tags>\n" + "\n".join(tags) + "\n</Tags>"


def main_routine_logic() -> tuple[str, ...]:
    """The one non-optional cyclic path (Core §1.1 O1 ordering rule).

    Module first, unconditionally; sequence intent second. S11 proved this
    ordering for §3.5 and the same rule binds §6.1 commands.
    """
    return (
        "FRK_S16_ScanCount := FRK_S16_ScanCount + 1;",
        "(* Unconditional call: the module runs every scan, before any intent *)",
        (
            f"{AXIS_AOI}({AXIS_INSTANCE},{CTX_TAG},FRK_S16_ScanCount,"
            "FRK_S16_HoldRequest,FRK_S16_FaultRequest);"
        ),
        (
            f"{MODE_AOI}({MODE_INSTANCE},{CTX_TAG},FRK_S16_ScanCount,"
            "FRK_S16_ModeSelect,FRK_S16_Command);"
        ),
        f"{CTX_TAG}.Abort := FRK_S16_Abort;",
        f"FRK_S16_OrderFail := {CTX_TAG}.OrderFail;",
        f"FRK_S16_LatencyBad := {CTX_TAG}.LatencyBad;",
    )


def programs() -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(main_routine_logic())
    )
    return f"""<Programs>
<Program Name="{PROGRAM}" TestEdits="false" MainRoutineName="{MAIN_ROUTINE}" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="{MAIN_ROUTINE}" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
</Program>
</Programs>"""


TASKS = f"""<Tasks>
<Task Name="FRK_S16Task" Type="PERIODIC" Rate="{TASK_RATE_MS}" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def all_generated_logic() -> str:
    return "\n".join(
        list(axis_logic()) + list(mode_logic()) + list(main_routine_logic())
    )


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

    logic = all_generated_logic()
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", logic):
        raise AssertionError("fixture logic contains an I/O operand")
    for forbidden in ("TIME", "TIME32", "LREAL", "LINT"):
        if re.search(rf'DataType="{forbidden}"', ctx_data_type()):
            raise AssertionError(f"context uses a type S12 excluded: {forbidden}")

    text = replace_once(text, "<DataTypes/>", ctx_data_type())
    text = replace_once(text, "<AddOnInstructionDefinitions/>", aoi_definitions())
    text = replace_once(text, "<Tags/>", controller_tags())
    text = replace_once(text, "<Programs/>", programs())
    text = replace_once(text, "<Tasks/>", TASKS)

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
        "TaskOutputUpdatesDisabled": True,
        "AoiDefinitions": 2,
        "ContextMembers": len(CTX_MEMBERS),
        "TaskRateMs": TASK_RATE_MS,
        "DurationCarrier": "DINT milliseconds (AB §3.8; S12 excluded TIME)",
        "ExecStateOrdinals": {
            "READY": STATE_READY,
            "BUSY": STATE_BUSY,
            "DONE": STATE_DONE,
            "ERROR": STATE_ERROR,
            "ABORTED": STATE_ABORTED,
        },
        "ReasonCodes": {
            "HELD_PERMISSIVE": REASON_HELD_PERMISSIVE,
            "DEVICE_FAULT": REASON_DEVICE_FAULT,
            "TIMEOUT": REASON_TIMEOUT,
            "ABORT_REQUEST": REASON_ABORT_REQUEST,
        },
        "AutoChainSteps": [STEP_INIT, STEP_MOVE_A, STEP_MOVE_B, STEP_FINISH],
        "ExpectedLatencyScans": 1,
        "ScansPerMove": (POS_MAX - POS_MIN) // SPEED_PER_SCAN,
        "WritableInputs": list(WRITABLE_INPUTS),
        "Programs": 1,
        "Routines": 1,
        "Tasks": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
