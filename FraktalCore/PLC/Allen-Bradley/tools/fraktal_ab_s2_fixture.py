#!/usr/bin/env python3
"""Generate the disposable v33 S2 AOI-parameter/nesting fixture.

The input is the same fresh, empty 1769-L24ER-QB1B v33 full-project L5X used
by the Phase 0 data-path fixture. One declaration generates an eight-level AOI
chain whose contract exercises a UDT InOut, a standard STRING InOut, atomic
Input/Output parameters, nested AOI instance locals, member External Access,
and unconditional periodic execution.

This is pre-gate evidence tooling, not a production Fraktal runtime generator.
The output is evidence only after SDK import, Studio v33 Verify Controller,
export, canonical comparison, and (when authorized) isolated execution.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256, string_tag


SCHEMA = "fraktal.ab.s2-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"
NESTING_DEPTH = 8


DATA_TYPES = """<DataTypes>
<DataType Name="FRK_T_S2Ctx" Family="NoFamily" Class="User">
<Members>
<Member Name="SchemaVersion" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="Command" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
<Member Name="Result" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="DepthSeen" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="TextEchoLength" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>
<Member Name="PrivateMarker" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="None"/>
</Members>
</DataType>
</DataTypes>"""


@dataclass(frozen=True)
class AoiDeclaration:
    name: str
    nested_type: str | None
    level: int


def declarations(depth: int) -> tuple[AoiDeclaration, ...]:
    if not 1 <= depth <= 17:
        raise ValueError("nesting depth must be between 1 and 17")
    return tuple(
        AoiDeclaration(
            name=f"FRK_S2_Level{level:02d}",
            nested_type=None if level == 1 else f"FRK_S2_Level{level - 1:02d}",
            level=level,
        )
        for level in range(1, depth + 1)
    )


AOIS = declarations(NESTING_DEPTH)


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


def aoi_definition(declaration: AoiDeclaration) -> str:
    parameters = "\n".join(
        [
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
            parameter("Ctx", "FRK_T_S2Ctx", "InOut"),
            parameter("Text", "STRING", "InOut"),
            parameter(
                "ScalarIn", "DINT", "Input", radix="Decimal",
                external_access="Read Only",
            ),
            parameter(
                "ScalarOut", "DINT", "Output", radix="Decimal",
                external_access="Read Only",
            ),
        ]
    )
    if declaration.nested_type is None:
        local_tags = "<LocalTags/>"
        logic = [
            "Ctx.Result := Ctx.Command + ScalarIn;",
            "Ctx.TextEchoLength := Text.LEN;",
            "Ctx.PrivateMarker := Ctx.Result + Text.LEN;",
            "ScalarOut := Ctx.Result + Text.LEN;",
        ]
        dependencies = '<Dependency Type="DataType" Name="FRK_T_S2Ctx"/>'
    else:
        local_tags = (
            "<LocalTags>"
            f'<LocalTag Name="Child" DataType="{declaration.nested_type}" '
            'ExternalAccess="None"/>'
            "</LocalTags>"
        )
        logic = [
            f"{declaration.nested_type}(Child,Ctx,Text,ScalarIn,ScalarOut);",
            f"Ctx.DepthSeen := {declaration.level};",
        ]
        dependencies = "\n".join(
            [
                '<Dependency Type="DataType" Name="FRK_T_S2Ctx"/>',
                f'<Dependency Type="AddOnInstruction" Name="{declaration.nested_type}"/>',
            ]
        )
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(logic)
    )
    return f"""<AddOnInstructionDefinition Name="{declaration.name}" Revision="1.0" ExecutePrescan="false" ExecutePostscan="false" ExecuteEnableInFalse="false" CreatedDate="2026-08-13T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-08-13T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
<RevisionNote><![CDATA[Disposable S2 parameter and nesting evidence.]]></RevisionNote>
<Parameters>
{parameters}
</Parameters>
{local_tags}
<Routines>
<Routine Name="Logic" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
<Dependencies>
{dependencies}
</Dependencies>
</AddOnInstructionDefinition>"""


def aoi_definitions(aois: tuple[AoiDeclaration, ...]) -> str:
    return "<AddOnInstructionDefinitions>\n" + "\n".join(
        aoi_definition(declaration) for declaration in aois
    ) + "\n</AddOnInstructionDefinitions>"


def base_tag(name: str, data_type: str, external_access: str) -> str:
    return (
        f'<Tag Name="{name}" TagType="Base" DataType="{data_type}" '
        f'Constant="false" ExternalAccess="{external_access}"/>'
    )


def tags(aois: tuple[AoiDeclaration, ...]) -> str:
    return "\n".join(
        [
            "<Tags>",
            base_tag("FRK_S2_Ctx", "FRK_T_S2Ctx", "Read/Write"),
            string_tag("FRK_S2_Text", "Read/Write"),
            base_tag("FRK_S2_Instance", aois[-1].name, "None"),
            scalar_tag("FRK_S2_Output", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S2_ScanCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S2_Complete", "BOOL", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


def program_lines(aois: tuple[AoiDeclaration, ...]) -> tuple[str, ...]:
    return (
        "FRK_S2_ScanCount := FRK_S2_ScanCount + 1;",
        f"{aois[-1].name}(FRK_S2_Instance,FRK_S2_Ctx,FRK_S2_Text,7,FRK_S2_Output);",
        "FRK_S2_Ctx.SchemaVersion := 1;",
        "FRK_S2_Complete := 1;",
    )


PROGRAM_LINES = program_lines(AOIS)


def programs(lines_source: tuple[str, ...]) -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(lines_source)
    )
    return f"""<Programs>
<Program Name="FRK_S2Program" TestEdits="false" MainRoutineName="FRK_S2Main" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="FRK_S2Main" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
</Program>
</Programs>"""


TASKS = """<Tasks>
<Task Name="FRK_S2Task" Type="PERIODIC" Rate="10" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="FRK_S2Program"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def generate(
    source: Path, output: Path, nesting_depth: int = NESTING_DEPTH
) -> dict[str, object]:
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

    aois = declarations(nesting_depth)
    generated_program_lines = program_lines(aois)
    generated_logic = "\n".join(
        generated_program_lines
        + tuple(
            statement
            for declaration in aois
            for statement in (
                (
                    "Ctx.Result := Ctx.Command + ScalarIn;",
                    "Ctx.TextEchoLength := Text.LEN;",
                    "Ctx.PrivateMarker := Ctx.Result + Text.LEN;",
                    "ScalarOut := Ctx.Result + Text.LEN;",
                )
                if declaration.nested_type is None
                else (
                    f"{declaration.nested_type}(Child,Ctx,Text,ScalarIn,ScalarOut);",
                    f"Ctx.DepthSeen := {declaration.level};",
                )
            )
        )
    )
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", generated_logic):
        raise AssertionError("fixture logic contains an I/O operand")

    text = replace_once(text, "<DataTypes/>", DATA_TYPES)
    text = replace_once(
        text, "<AddOnInstructionDefinitions/>", aoi_definitions(aois)
    )
    text = replace_once(text, "<Tags/>", tags(aois))
    text = replace_once(text, "<Programs/>", programs(generated_program_lines))
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
        "AoiDefinitions": len(aois),
        "NestedAoiDepth": nesting_depth,
        "ControllerTags": 6,
        "Programs": 1,
        "Tasks": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--nesting-depth", type=int, default=NESTING_DEPTH)
    args = parser.parse_args()
    try:
        evidence = generate(args.source, args.output, args.nesting_depth)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
