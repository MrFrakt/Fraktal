#!/usr/bin/env python3
"""Generate the disposable v33 S12 physical type-map fixture.

The type-acceptance probes answer which Logix spellings the target compiles.
This fixture answers what those types actually *do* on the controller, which is
what AB §3.8 needs before a public UDT is generated: exact CIP round trip for
every integer width, float behavior including NaN, deterministic overflow,
string length semantics, array indexing, and — the one that cannot be inferred
from a manual — the byte layout Logix gives a mixed-member public UDT.

Layout is made self-describing rather than assumed. The fixture `COP`s the
public UDT into a `SINT` array, so the controller publishes its own wire image
and the probe locates each member's sentinel inside it. That turns member
offsets, padding and total size into a measurement instead of a prediction.

Safety: the generated logic performs **no division and no variable array
index**, because an integer divide by zero or an out-of-range subscript is a
Logix major fault, and clearing a fault is not in scope for an evidence run.
Overflow is provoked only by addition and multiplication on a controller whose
`ReportMinorOverflow` is false, and NaN is produced by copying a bit pattern,
never by computing one.

This is pre-gate evidence tooling, not a production Fraktal runtime generator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256, string_tag


SCHEMA = "fraktal.ab.s12-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

LAYOUT_TYPE = "FRK_T_S12Layout"
LAYOUT_TAG = "FRK_S12_Layout"
LAYOUT_BYTES = "FRK_S12_LayoutBytes"
LAYOUT_BYTE_CAPACITY = 128
# Two adjacent instances are copied as well, because the distance between them
# is the only way to observe the type's *padded* size: trailing padding on a
# single instance is invisible, since it reads as zero either way.
PAIR_TAG = "FRK_S12_LayoutPair"
PAIR_BYTES = "FRK_S12_PairBytes"
PAIR_BYTE_CAPACITY = 256
ARRAY_TAG = "FRK_S12_Array"
ARRAY_LENGTH = 10
PROGRAM = "FRK_S12Program"
ROUTINE = "FRK_S12Main"

# Sentinels are byte-distinctive so the probe can locate each member inside the
# copied wire image without being told the layout in advance.
SENTINELS: dict[str, int | float] = {
    "Flag": 1,
    "Small": 0x5A,
    "Medium": 0x1234,
    "Count": 0x11223344,
    "Wide": 0x0102030405060708,
    "Ratio": 2.5,
}

# 0x7FC00000 is a quiet NaN. It is copied into a REAL rather than computed.
NAN_BITS = 0x7FC00000

# LREAL is absent because Studio v33 rejects it outright on this controller
# type ("The LREAL data type is not supported by this controller type"), even
# though the SDK imported it without complaint. LINT is present as a carried
# member only: its declaration verifies, but every arithmetic form tested was
# rejected, so the fixture transports it and never computes on it.
LAYOUT_MEMBERS = (
    ("Flag", "BOOL", "Decimal"),
    ("Small", "SINT", "Decimal"),
    ("Medium", "INT", "Decimal"),
    ("Count", "DINT", "Decimal"),
    ("Wide", "LINT", "Decimal"),
    ("Ratio", "REAL", "Float"),
)


def layout_data_type() -> str:
    members = "\n".join(
        f'<Member Name="{name}" DataType="{data_type}" Dimension="0" '
        f'Radix="{radix}" Hidden="false" ExternalAccess="Read/Write"/>'
        for name, data_type, radix in LAYOUT_MEMBERS
    )
    return f"""<DataTypes>
<DataType Name="{LAYOUT_TYPE}" Family="NoFamily" Class="User">
<Members>
{members}
</Members>
</DataType>
</DataTypes>"""


def sint_array_tag(name: str, size: int, external_access: str) -> str:
    raw = " ".join("00" for _ in range(size))
    elements = "\n".join(
        f'<Element Index="[{index}]" Value="0"/>' for index in range(size)
    )
    return f"""<Tag Name="{name}" TagType="Base" DataType="SINT" Dimensions="{size}" Radix="Decimal" Constant="false" ExternalAccess="{external_access}">
<Data>{raw}</Data>
<Data Format="Decorated"><Array DataType="SINT" Dimensions="{size}" Radix="Decimal">
{elements}
</Array></Data>
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


def layout_tag() -> str:
    return (
        f'<Tag Name="{LAYOUT_TAG}" TagType="Base" DataType="{LAYOUT_TYPE}" '
        'Constant="false" ExternalAccess="Read/Write"/>'
    )


def tags() -> str:
    return "\n".join(
        [
            "<Tags>",
            layout_tag(),
            f'<Tag Name="{PAIR_TAG}" TagType="Base" DataType="{LAYOUT_TYPE}" '
            'Dimensions="2" Constant="false" ExternalAccess="Read/Write"/>',
            sint_array_tag(LAYOUT_BYTES, LAYOUT_BYTE_CAPACITY, "Read Only"),
            sint_array_tag(PAIR_BYTES, PAIR_BYTE_CAPACITY, "Read Only"),
            dint_array_tag(ARRAY_TAG, ARRAY_LENGTH, "Read/Write"),
            string_tag("FRK_S12_Text", "Read/Write"),
            scalar_tag("FRK_S12_NanBits", "DINT", "Decimal", "0", "Read/Write"),
            scalar_tag("FRK_S12_NanReal", "REAL", "Float", "0.0", "Read Only"),
            scalar_tag("FRK_S12_NanIsNan", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_RatioResult", "REAL", "Float", "0.0", "Read Only"),
            scalar_tag("FRK_S12_SmallWrap", "SINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_MediumWrap", "INT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_TextLen", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_ArrayEdgeSum", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_DurationMs", "DINT", "Decimal", "0", "Read/Write"),
            scalar_tag("FRK_S12_DurationOk", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_ScanCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S12_Complete", "BOOL", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


# The Core duration contract is integer milliseconds; with no native TIME on
# this target the binding uses a range-checked DINT, so the fixture performs
# that range check rather than assuming it.
DURATION_MAX_MS = 86_400_000


def routine_lines() -> tuple[str, ...]:
    return (
        "FRK_S12_ScanCount := FRK_S12_ScanCount + 1;",
        # publish the controller's own wire image of the public UDT, and of two
        # adjacent instances so the padded stride is measurable
        f"COP({LAYOUT_TAG},{LAYOUT_BYTES}[0],1);",
        f"COP({PAIR_TAG}[0],{PAIR_BYTES}[0],2);",
        # float behaviour; there is deliberately no LINT arithmetic here
        f"FRK_S12_RatioResult := {LAYOUT_TAG}.Ratio * 2.0;",
        # deterministic overflow by addition/multiplication only
        f"FRK_S12_SmallWrap := {LAYOUT_TAG}.Small + {LAYOUT_TAG}.Small;",
        f"FRK_S12_MediumWrap := {LAYOUT_TAG}.Medium * 8;",
        # NaN is copied in, never computed
        "COP(FRK_S12_NanBits,FRK_S12_NanReal,1);",
        "FRK_S12_NanIsNan := 0;",
        "IF FRK_S12_NanReal <> FRK_S12_NanReal THEN",
        "FRK_S12_NanIsNan := 1;",
        "END_IF;",
        # string length semantics
        "FRK_S12_TextLen := FRK_S12_Text.LEN;",
        # array indexing with constant subscripts only
        f"FRK_S12_ArrayEdgeSum := {ARRAY_TAG}[0] + {ARRAY_TAG}[{ARRAY_LENGTH - 1}];",
        # range-checked duration in place of a native TIME
        "FRK_S12_DurationOk := 0;",
        f"IF (FRK_S12_DurationMs >= 0) AND (FRK_S12_DurationMs <= {DURATION_MAX_MS}) THEN",
        "FRK_S12_DurationOk := 1;",
        "END_IF;",
        "FRK_S12_Complete := 1;",
    )


def program_block() -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(routine_lines())
    )
    return f"""<Programs>
<Program Name="{PROGRAM}" TestEdits="false" MainRoutineName="{ROUTINE}" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="{ROUTINE}" Type="ST">
<STContent>
{lines}
</STContent>
</Routine>
</Routines>
</Program>
</Programs>"""


TASKS = f"""<Tasks>
<Task Name="FRK_S12Task" Type="PERIODIC" Rate="10" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


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
        raise ValueError(f"source is not the expected empty v33 seed: {missing}")

    logic = "\n".join(routine_lines())
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", logic):
        raise AssertionError("fixture logic contains an I/O operand")
    # A faulting instruction must never reach the controller: integer divide by
    # zero and an out-of-range subscript are major faults, and this evidence run
    # carries no authorization to clear one.
    if "/" in logic or re.search(r"\[[A-Za-z_]", logic):
        raise AssertionError("fixture logic contains a division or variable index")

    text = replace_once(text, "<DataTypes/>", layout_data_type())
    text = replace_once(text, "<Tags/>", tags())
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
        "LayoutMembers": [name for name, _, _ in LAYOUT_MEMBERS],
        "LayoutByteCapacity": LAYOUT_BYTE_CAPACITY,
        "PairByteCapacity": PAIR_BYTE_CAPACITY,
        "Sentinels": {name: value for name, value in SENTINELS.items()},
        "NanBits": NAN_BITS,
        "DurationMaxMs": DURATION_MAX_MS,
        "ArrayLength": ARRAY_LENGTH,
        "WritableInputs": [
            f"{LAYOUT_TAG}.{name}" for name, _, _ in LAYOUT_MEMBERS
        ] + [ARRAY_TAG, "FRK_S12_Text", "FRK_S12_NanBits", "FRK_S12_DurationMs"],
        "Programs": 1,
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
        print(f"ERROR [s12-fixture] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
