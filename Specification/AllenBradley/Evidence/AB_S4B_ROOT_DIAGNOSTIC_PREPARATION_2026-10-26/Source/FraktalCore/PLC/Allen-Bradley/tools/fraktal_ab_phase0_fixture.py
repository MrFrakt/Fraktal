#!/usr/bin/env python3
"""Generate the disposable v33 memory-only Fraktal/AB Phase 0 fixture.

The input must be a full-project L5X exported by Studio/SDK from a newly
created, empty 1769-L24ER-QB1B v33 project. The output contains only controller
memory tags and one periodic Structured Text routine. It inhibits the embedded
discrete-I/O module and never references an I/O operand.

This is pre-gate evidence tooling, not production Fraktal runtime generation.
The generated L5X must still pass Studio import and Verify Controller before a
download is considered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCHEMA = "fraktal.ab.phase0-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"


DATA_TYPES = """<DataTypes>
<DataType Name="FRK_T_Phase0Probe" Family="NoFamily" Class="User">
<Members>
<Member Name="DintValue" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
<Member Name="RealBits" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
<Member Name="Checksum" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
<Member Name="Samples" DataType="DINT" Dimension="4" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
</Members>
</DataType>
</DataTypes>"""


def scalar_tag(
    name: str,
    data_type: str,
    radix: str,
    value: str,
    external_access: str,
) -> str:
    return f"""<Tag Name="{name}" TagType="Base" DataType="{data_type}" Radix="{radix}" Constant="false" ExternalAccess="{external_access}">
<Data Format="L5K"><![CDATA[{value}]]></Data>
<Data Format="Decorated"><DataValue DataType="{data_type}" Radix="{radix}" Value="{value}"/></Data>
</Tag>"""


def dint_array_tag(name: str, size: int, external_access: str) -> str:
    raw = " ".join("00" for _ in range(size * 4))
    elements = "\n".join(
        f'<Element Index="[{index}]" Value="0"/>' for index in range(size)
    )
    return f"""<Tag Name="{name}" TagType="Base" DataType="DINT" Dimensions="{size}" Radix="Decimal" Constant="false" ExternalAccess="{external_access}">
<Data>{raw}</Data>
<Data Format="Decorated"><Array DataType="DINT" Dimensions="{size}" Radix="Decimal">
{elements}
</Array></Data>
</Tag>"""


def string_tag(name: str, external_access: str) -> str:
    empty_data = "$00" * 82
    return f"""<Tag Name="{name}" TagType="Base" DataType="STRING" Constant="false" ExternalAccess="{external_access}">
<Data Format="L5K"><![CDATA[[0,'{empty_data}']]]></Data>
<Data Format="String" Length="0"><![CDATA['']]></Data>
</Tag>"""


def udt_tag(name: str, external_access: str) -> str:
    samples = "\n".join(
        f'<Element Index="[{index}]" Value="0"/>' for index in range(4)
    )
    return f"""<Tag Name="{name}" TagType="Base" DataType="FRK_T_Phase0Probe" Constant="false" ExternalAccess="{external_access}">
<Data Format="L5K"><![CDATA[[0,0,0,[0,0,0,0]]]]></Data>
<Data Format="Decorated"><Structure DataType="FRK_T_Phase0Probe">
<DataValueMember Name="DintValue" DataType="DINT" Radix="Decimal" Value="0"/>
<DataValueMember Name="RealBits" DataType="DINT" Radix="Decimal" Value="0"/>
<DataValueMember Name="Checksum" DataType="DINT" Radix="Decimal" Value="0"/>
<ArrayMember Name="Samples" DataType="DINT" Dimensions="4" Radix="Decimal">
{samples}
</ArrayMember>
</Structure></Data>
</Tag>"""


TAGS = "\n".join(
    [
        "<Tags>",
        scalar_tag("FRK_WriteDint", "DINT", "Decimal", "0", "Read/Write"),
        scalar_tag("FRK_WriteReal", "REAL", "Float", "0.0", "Read/Write"),
        dint_array_tag("FRK_WriteArray", 25, "Read/Write"),
        dint_array_tag("FRK_WriteLargeArray", 1024, "Read/Write"),
        string_tag("FRK_WriteString", "Read/Write"),
        udt_tag("FRK_WriteUdt", "Read/Write"),
        scalar_tag("FRK_ReadOnly", "DINT", "Decimal", "0", "Read Only"),
        scalar_tag("FRK_NoAccess", "DINT", "Decimal", "0", "None"),
        scalar_tag("FRK_ScanCount", "DINT", "Decimal", "0", "Read Only"),
        scalar_tag("FRK_Heartbeat", "DINT", "Decimal", "0", "Read Only"),
        scalar_tag("FRK_TestComplete", "BOOL", "Decimal", "0", "Read Only"),
        udt_tag("FRK_Result", "Read Only"),
        udt_tag("FRK_LargeResult", "Read Only"),
        "</Tags>",
    ]
)


PROGRAM_TAGS = "\n".join(
    [
        "<Tags>",
        scalar_tag("FRK_ProgramWriteDint", "DINT", "Decimal", "0", "Read/Write"),
        scalar_tag("FRK_ProgramResult", "DINT", "Decimal", "0", "Read Only"),
        "</Tags>",
    ]
)


ST_LINES = [
    "FRK_ScanCount := FRK_ScanCount + 1;",
    "FRK_Heartbeat := FRK_Heartbeat + 1;",
    "FRK_ReadOnly := FRK_WriteDint + 1;",
    "FRK_NoAccess := FRK_WriteDint + 2;",
    "FRK_Result.DintValue := FRK_WriteDint;",
    "FRK_Result.RealBits := FRK_WriteUdt.RealBits;",
    "FRK_Result.Samples[0] := FRK_WriteArray[0];",
    "FRK_Result.Samples[1] := FRK_WriteArray[1];",
    "FRK_Result.Samples[2] := FRK_WriteArray[23];",
    "FRK_Result.Samples[3] := FRK_WriteArray[24];",
    "FRK_Result.Checksum := FRK_WriteDint + FRK_WriteString.LEN + FRK_WriteUdt.DintValue + FRK_WriteUdt.RealBits + FRK_WriteUdt.Samples[0] + FRK_WriteUdt.Samples[1] + FRK_WriteUdt.Samples[2] + FRK_WriteUdt.Samples[3] + FRK_WriteArray[0] + FRK_WriteArray[1] + FRK_WriteArray[23] + FRK_WriteArray[24];",
    "FRK_ProgramResult := FRK_ProgramWriteDint + 100;",
    "FRK_LargeResult.DintValue := FRK_ProgramWriteDint;",
    "FRK_LargeResult.Samples[0] := FRK_WriteLargeArray[0];",
    "FRK_LargeResult.Samples[1] := FRK_WriteLargeArray[1];",
    "FRK_LargeResult.Samples[2] := FRK_WriteLargeArray[1022];",
    "FRK_LargeResult.Samples[3] := FRK_WriteLargeArray[1023];",
    "FRK_LargeResult.Checksum := FRK_ProgramWriteDint + FRK_WriteLargeArray[0] + FRK_WriteLargeArray[1] + FRK_WriteLargeArray[1022] + FRK_WriteLargeArray[1023];",
    "FRK_TestComplete := 1;",
]


def program_block() -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{line}]]></Line>'
        for index, line in enumerate(ST_LINES)
    )
    return f"""<Programs>
<Program Name="FRK_Phase0Program" TestEdits="false" MainRoutineName="FRK_Phase0Main" Disabled="false" UseAsFolder="false">
{PROGRAM_TAGS}
<Routines>
<Routine Name="FRK_Phase0Main" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
</Program>
</Programs>"""


TASKS = """<Tasks>
<Task Name="FRK_Phase0Task" Type="PERIODIC" Rate="10" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="FRK_Phase0Program"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {old!r}, found {count}")
    return text.replace(old, new, 1)


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
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 fixture: {missing}")

    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", "\n".join(ST_LINES)):
        raise AssertionError("fixture logic contains an I/O operand")

    text = replace_once(text, "<DataTypes/>", DATA_TYPES)
    text = replace_once(text, "<Tags/>", TAGS)
    text = replace_once(text, "<Programs/>", program_block())
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
        "ControllerTags": 13,
        "ProgramTags": 2,
        "Programs": 1,
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
