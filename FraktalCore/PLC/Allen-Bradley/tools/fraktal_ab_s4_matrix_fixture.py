#!/usr/bin/env python3
"""Generate the disposable S4 representative construct-matrix fixture.

S4 asks whether the constructs Fraktal/AB will actually generate survive an
L5X round trip. Earlier evidence covered UDTs, one AOI, tags, RLL, ST, a
program and a task from an *uploaded* application, and S11 added native SFC.
What was never covered was the rest of what a generated project contains:
schedules, nested and tabular record shapes, sized string types, generated
constants, and the AOI scan-flag routines.

This fixture is that matrix, generated from one declaration set:

* two tasks - one periodic, one continuous - with their scheduled programs, so
  the schedule itself is part of the round trip;
* two programs, one carrying ST, RLL and SFC routines side by side;
* a nested UDT and an array of UDTs, the shapes a manifest or mailbox record
  actually takes;
* a `StringFamily` type of non-default length, which bounded manifest tables
  need and which the default `STRING` cannot express;
* a `Constant` tag, the form AB §3.8 gives generated `FRK_K` enum constants;
* an AOI declaring all three `Execute*` scan flags with the matching Prescan,
  Postscan and EnableInFalse routines; and
* descriptions on a data-type member, a tag, a routine and a rung, because
  documentation travels as an export option and can be dropped silently.

Deliberately out of scope: FBD, which Fraktal does not generate; alias and
produced/consumed tags, which the binding does not use; and motion, which S14
gates separately.

This is pre-gate evidence tooling, not a production generator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, sha256


SCHEMA = "fraktal.ab.s4-matrix-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

STRING_TYPE = "FRK_S4_String32"
STRING_LENGTH = 32
INNER_TYPE = "FRK_T_S4Inner"
RECORD_TYPE = "FRK_T_S4Record"
TABLE_LENGTH = 4
AOI_NAME = "FRK_S4_Scan"
PROGRAM_A = "FRK_S4ProgramA"
PROGRAM_B = "FRK_S4ProgramB"
PERIODIC_TASK = "FRK_S4TaskPeriodic"
CONTINUOUS_TASK = "FRK_S4TaskContinuous"


def data_types() -> str:
    return f"""<DataTypes>
<DataType Name="{STRING_TYPE}" Family="StringFamily" Class="User">
<Members>
<Member Name="LEN" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false"/>
<Member Name="DATA" DataType="SINT" Dimension="{STRING_LENGTH}" Radix="ASCII" Hidden="false"/>
</Members>
</DataType>
<DataType Name="{INNER_TYPE}" Family="NoFamily" Class="User">
<Members>
<Member Name="Ordinal" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only">
<Description><![CDATA[Generated Core enum ordinal.]]></Description>
</Member>
<Member Name="Enabled" DataType="BOOL" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
</Members>
</DataType>
<DataType Name="{RECORD_TYPE}" Family="NoFamily" Class="User">
<Members>
<Member Name="SchemaVersion" DataType="INT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="Inner" DataType="{INNER_TYPE}" Dimension="0" Radix="NullType" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="Samples" DataType="DINT" Dimension="4" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="Label" DataType="{STRING_TYPE}" Dimension="0" Radix="NullType" Hidden="false" ExternalAccess="Read Only"/>
</Members>
</DataType>
</DataTypes>"""


def parameter(name: str, data_type: str, usage: str, radix: str | None,
              required: bool, visible: bool, external: str | None) -> str:
    attributes = [f'Name="{name}"', 'TagType="Base"', f'DataType="{data_type}"',
                  f'Usage="{usage}"']
    if radix is not None:
        attributes.append(f'Radix="{radix}"')
    attributes.append(f'Required="{str(required).lower()}"')
    attributes.append(f'Visible="{str(visible).lower()}"')
    if external is not None:
        attributes.append(f'ExternalAccess="{external}"')
    return f"<Parameter {' '.join(attributes)}/>"


def aoi_definition() -> str:
    """An AOI that declares all three scan flags and supplies their routines."""
    parameters = "\n".join(
        [
            parameter("EnableIn", "BOOL", "Input", "Decimal", False, False, "Read Only"),
            parameter("EnableOut", "BOOL", "Output", "Decimal", False, False, "Read Only"),
            parameter("Record", RECORD_TYPE, "InOut", None, True, True, None),
            parameter("Increment", "DINT", "Input", "Decimal", True, True, "Read Only"),
        ]
    )
    routines = {
        "Logic": ("Record.Inner.Ordinal := Record.Inner.Ordinal + Increment;",),
        "Prescan": ("Record.Inner.Ordinal := 0;",),
        "Postscan": ("Record.Inner.Enabled := 0;",),
        "EnableInFalse": ("Record.Inner.Enabled := 0;",),
    }
    bodies = "\n".join(
        "<Routine Name=\"{name}\" Type=\"ST\">\n<STContent>\n{lines}\n</STContent>\n</Routine>".format(
            name=name,
            lines="\n".join(
                f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
                for index, statement in enumerate(statements)
            ),
        )
        for name, statements in routines.items()
    )
    return f"""<AddOnInstructionDefinitions>
<AddOnInstructionDefinition Name="{AOI_NAME}" Revision="1.0" ExecutePrescan="true" ExecutePostscan="true" ExecuteEnableInFalse="true" CreatedDate="2026-08-13T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-08-13T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
<Description><![CDATA[Disposable S4 construct-matrix instruction.]]></Description>
<RevisionNote><![CDATA[Disposable S4 construct-matrix evidence.]]></RevisionNote>
<Parameters>
{parameters}
</Parameters>
<LocalTags>
<LocalTag Name="ScanMarker" DataType="DINT" Radix="Decimal" ExternalAccess="None">
<DefaultData>00 00 00 00</DefaultData>
<DefaultData Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/>
</DefaultData>
</LocalTag>
</LocalTags>
<Routines>
{bodies}
</Routines>
<Dependencies>
<Dependency Type="DataType" Name="{RECORD_TYPE}"/>
</Dependencies>
</AddOnInstructionDefinition>
</AddOnInstructionDefinitions>"""


def controller_tags() -> str:
    return f"""<Tags>
<Tag Name="FRK_S4_Record" TagType="Base" DataType="{RECORD_TYPE}" Constant="false" ExternalAccess="Read/Write">
<Description><![CDATA[Generated public record.]]></Description>
</Tag>
<Tag Name="FRK_S4_Table" TagType="Base" DataType="{RECORD_TYPE}" Dimensions="{TABLE_LENGTH}" Constant="false" ExternalAccess="Read Only"/>
<Tag Name="FRK_S4_Label" TagType="Base" DataType="{STRING_TYPE}" Constant="false" ExternalAccess="Read/Write"/>
<Tag Name="FRK_S4_Instance" TagType="Base" DataType="{AOI_NAME}" Constant="false" ExternalAccess="None"/>
<Tag Name="FRK_K_ModeAuto" TagType="Base" DataType="DINT" Radix="Decimal" Constant="true" ExternalAccess="Read Only">
<Description><![CDATA[Generated Core enum constant.]]></Description>
<Data Format="L5K"><![CDATA[2]]></Data>
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="2"/></Data>
</Tag>
<Tag Name="FRK_S4_ScanA" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read Only">
<Data Format="L5K"><![CDATA[0]]></Data>
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/></Data>
</Tag>
<Tag Name="FRK_S4_ScanB" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read Only">
<Data Format="L5K"><![CDATA[0]]></Data>
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/></Data>
</Tag>
<Tag Name="FRK_S4_Rung" TagType="Base" DataType="BOOL" Radix="Decimal" Constant="false" ExternalAccess="Read Only">
<Data Format="L5K"><![CDATA[0]]></Data>
<Data Format="Decorated"><DataValue DataType="BOOL" Radix="Decimal" Value="0"/></Data>
</Tag>
</Tags>"""


# Every generated routine is reached from the main routine. Studio v33 raises
# "Routine cannot be reached by the main routine" as a Verify *warning* for an
# orphan, so a generator that emits a routine without wiring it produces a
# project that passes an errors-only gate and still carries dead code. The gate
# therefore requires zero warnings, not just zero errors.
ST_LINES_A = (
    "FRK_S4_ScanA := FRK_S4_ScanA + 1;",
    "FRK_S4_Record.SchemaVersion := 1;",
    f"{AOI_NAME}(FRK_S4_Instance,FRK_S4_Record,1);",
    "FRK_S4_Table[0].SchemaVersion := 1;",
    f"FRK_S4_Table[{TABLE_LENGTH - 1}].SchemaVersion := 1;",
    "FRK_S4_Record.Label.LEN := 0;",
    "JSR(FRK_S4Ladder,0);",
    "JSR(FRK_S4Chart,0);",
)

ST_LINES_B = (
    "FRK_S4_ScanB := FRK_S4_ScanB + 1;",
)

# One rung, in the neutral text form Logix serializes. A generated Ladder
# sequence is an integer state machine over the same contract; this proves the
# construct round-trips, not the sequence semantics, which S11 owns.
RUNG_TEXT = "XIC(FRK_S4_Record.Inner.Enabled)OTE(FRK_S4_Rung);"


def program_a() -> str:
    st_lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(ST_LINES_A)
    )
    return f"""<Program Name="{PROGRAM_A}" TestEdits="false" MainRoutineName="FRK_S4MainA" Disabled="false" UseAsFolder="false">
<Tags>
<Tag Name="FRK_S4_LocalCount" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read Only">
<Data Format="L5K"><![CDATA[0]]></Data>
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/></Data>
</Tag>
<Tag Name="N100" TagType="Base" DataType="SFC_STEP" Constant="false" ExternalAccess="Read/Write"/>
<Tag Name="A100_Mark" TagType="Base" DataType="SFC_ACTION" Constant="false" ExternalAccess="Read/Write"/>
</Tags>
<Routines>
<Routine Name="FRK_S4MainA" Type="ST">
<Description><![CDATA[Generated main routine.]]></Description>
<STContent>
{st_lines}
</STContent>
</Routine>
<Routine Name="FRK_S4Ladder" Type="RLL">
<RLLContent>
<Rung Number="0" Type="N">
<Comment><![CDATA[Generated rung comment.]]></Comment>
<Text><![CDATA[{RUNG_TEXT}]]></Text>
</Rung>
</RLLContent>
</Routine>
<Routine Name="FRK_S4Chart" Type="SFC">
<SFCContent SheetSize="Letter - 8.5 x 11 in" SheetOrientation="Landscape" StepName="Step" TransitionName="Tran" ActionName="Action" StopName="Stop">
<Step ID="0" X="240" Y="60" Operand="N100" HideDesc="true" DescX="294" DescY="45" DescWidth="0" InitialStep="true" PresetUsesExpr="false" LimitHighUsesExpr="false" LimitLowUsesExpr="false" ShowActions="true">
<Action ID="1" Operand="A100_Mark" Qualifier="NonStored" IsBoolean="false" PresetUsesExpr="false">
<Body>
<STContent>
<Line Number="0"><![CDATA[FRK_S4_LocalCount := FRK_S4_LocalCount + 1;]]></Line>
</STContent>
</Body>
</Action>
</Step>
</SFCContent>
</Routine>
</Routines>
</Program>"""


def program_b() -> str:
    st_lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(ST_LINES_B)
    )
    return f"""<Program Name="{PROGRAM_B}" TestEdits="false" MainRoutineName="FRK_S4MainB" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="FRK_S4MainB" Type="ST">
<STContent>
{st_lines}
</STContent>
</Routine>
</Routines>
</Program>"""


def programs() -> str:
    return f"<Programs>\n{program_a()}\n{program_b()}\n</Programs>"


TASKS = f"""<Tasks>
<Task Name="{PERIODIC_TASK}" Type="PERIODIC" Rate="20" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM_A}"/>
</ScheduledPrograms>
</Task>
<Task Name="{CONTINUOUS_TASK}" Type="CONTINUOUS" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM_B}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def all_generated_logic() -> str:
    return "\n".join(ST_LINES_A + ST_LINES_B + (RUNG_TEXT,))


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
        "<DataTypes/>",
        "<AddOnInstructionDefinitions/>",
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 seed: {missing}")

    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", all_generated_logic()):
        raise AssertionError("fixture logic contains an I/O operand")

    text = replace_once(text, "<DataTypes/>", data_types())
    text = replace_once(text, "<AddOnInstructionDefinitions/>", aoi_definition())
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
        "UserDataTypes": 3,
        "StringFamilyTypes": 1,
        "StringLength": STRING_LENGTH,
        "NestedUdt": True,
        "UdtArrayLength": TABLE_LENGTH,
        "ConstantTags": 1,
        "AoiScanRoutines": ["Logic", "Prescan", "Postscan", "EnableInFalse"],
        "Programs": 2,
        "RoutineTypes": ["ST", "RLL", "SFC"],
        "Tasks": {"periodic": PERIODIC_TASK, "continuous": CONTINUOUS_TASK},
        "OutOfScope": ["FBD", "alias tags", "produced/consumed tags", "motion"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        evidence = generate(args.source, args.output)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR [s4-matrix-fixture] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
