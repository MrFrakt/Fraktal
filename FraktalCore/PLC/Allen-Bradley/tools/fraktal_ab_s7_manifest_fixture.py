#!/usr/bin/env python3
"""Generate the disposable S7 manifest size-and-read-cost fixture.

S7 asks whether **one bounded manifest fits the read budget**, or whether the
binding must split it per root with a per-root revision. That cannot be argued
from a table of estimated row widths: it needs a manifest of realistic shape
resident in the controller and read over CIP.

This fixture materialises the frozen R3 manifest contract
([`AB_FROZEN_CONTRACTS_V1.json`](../../../../Specification/AB_FROZEN_CONTRACTS_V1.json))
as real Logix types: a header UDT plus one array-of-UDT per table, sized by the
capacity symbols S7 owns. Capacities are parameters, not constants, so the same
declaration can be generated at several sizes and the cost curve measured
rather than guessed.

Two properties make the measurement meaningful:

* the header carries `ConfigRevision` and `ContentHash`, so a reader can be
  required to prove it saw a *coherent* manifest rather than a torn one; and
* one writable input bumps `ConfigRevision` on a rising edge, which is how a
  real configuration change looks to the gateway - the cheap revision poll is
  what a gateway actually runs, and its cost is the number that matters at
  steady state.

Row contents are representative shapes, not real application data: S7 measures
size and read cost, and the field *meanings* are already frozen by R3.

This is pre-gate evidence tooling, not a production manifest generator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256


SCHEMA = "fraktal.ab.s7-manifest-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

PROGRAM = "FRK_S7Program"
ROUTINE = "FRK_S7Main"
KEY_STRING_TYPE = "FRK_S7_Key32"
KEY_STRING_LENGTH = 32

# The controller has finite user memory, and a manifest that will not download
# is not evidence about read cost. The generator refuses a declaration whose
# estimated data size exceeds this share of the L24ER's 750 KB.
MEMORY_BUDGET_BYTES = 300_000


@dataclass(frozen=True)
class Table:
    """One manifest table: a capacity symbol and the row type behind it."""

    name: str
    symbol: str
    tag: str
    row_type: str
    members: tuple[tuple[str, str], ...]
    default_capacity: int

    def row_bytes(self) -> int:
        total = 0
        for _, data_type in self.members:
            total += KEY_STRING_LENGTH + 4 if data_type == KEY_STRING_TYPE else 4
        # every row observed on this target padded to a four-byte multiple
        return total + (-total % 4)


TABLES: tuple[Table, ...] = (
    Table(
        "Roots", "FRK_MAX_ROOTS", "FRK_S7_Roots", "FRK_T_S7Root",
        (
            ("RootId", "DINT"), ("ModuleIndex", "DINT"), ("RepositoryScope", "DINT"),
            ("MailboxId", "DINT"), ("HostEventId", "DINT"),
        ),
        4,
    ),
    Table(
        "Modules", "FRK_MAX_MODULES", "FRK_S7_Modules", "FRK_T_S7Module",
        (
            ("ModuleId", "DINT"), ("ParentModuleId", "DINT"), ("RootId", "DINT"),
            ("RegistryIndex", "DINT"), ("Tier", "DINT"), ("TypeId", "DINT"),
            ("LocalNameKey", "DINT"), ("CanonicalPathKey", "DINT"),
            ("Capabilities", "DINT"), ("ContractAddress", "DINT"),
        ),
        128,
    ),
    Table(
        "Nameplates", "FRK_MAX_MODULES", "FRK_S7_Nameplates", "FRK_T_S7Nameplate",
        (
            ("ModuleId", "DINT"), ("ManufacturerKey", "DINT"), ("ProductKey", "DINT"),
            ("ModelKey", "DINT"), ("SerialKey", "DINT"), ("HardwareRevision", "DINT"),
            ("SoftwareRevision", "DINT"), ("AssetKey", "DINT"), ("LocationKey", "DINT"),
        ),
        128,
    ),
    Table(
        "Fields", "FRK_MAX_FIELDS", "FRK_S7_Fields", "FRK_T_S7Field",
        (
            ("ModuleId", "DINT"), ("PathKey", "DINT"), ("LogicalType", "DINT"),
            ("Dimensions", "DINT"), ("ReadTier", "DINT"), ("AccessClass", "DINT"),
            ("QualitySource", "DINT"), ("WriteCapabilityIndex", "DINT"),
        ),
        512,
    ),
    Table(
        "Operations", "FRK_MAX_OPERATIONS", "FRK_S7_Operations", "FRK_T_S7Operation",
        (
            ("OperationId", "DINT"), ("TargetScope", "DINT"), ("ParameterType", "DINT"),
            ("ResultType", "DINT"), ("GatedAction", "DINT"), ("Minimum", "DINT"),
            ("Maximum", "DINT"), ("OperationKind", "DINT"),
        ),
        128,
    ),
    Table(
        "Localization", "FRK_MAX_LOCALIZATION_KEYS", "FRK_S7_Localization",
        "FRK_T_S7Localization",
        (("NumericKey", "DINT"), ("PortableKey", KEY_STRING_TYPE)),
        256,
    ),
    Table(
        "Rationalization", "FRK_MAX_REASONS", "FRK_S7_Rationalization",
        "FRK_T_S7Reason",
        (
            ("ReasonCode", "DINT"), ("Priority", "DINT"), ("Category", "DINT"),
            ("ActionKey", "DINT"), ("ConsequenceKey", "DINT"), ("Shelvable", "DINT"),
        ),
        128,
    ),
    Table(
        "OptionalProfiles", "FRK_MAX_OPTIONAL_PROFILES", "FRK_S7_Profiles",
        "FRK_T_S7Profile",
        (
            ("ProfileId", "DINT"), ("ProfileVersion", "DINT"),
            ("CapabilityMask", "DINT"), ("ProjectionMask", "DINT"),
        ),
        8,
    ),
)

HEADER_TYPE = "FRK_T_S7Header"
HEADER_SCALARS = (
    "Magic", "SchemaMajor", "SchemaMinor", "CoreVersion", "BindingVersion",
    "FrameworkVersion", "ConfigRevision", "Valid", "Truncated",
)


def default_capacities() -> dict[str, int]:
    return {table.symbol: table.default_capacity for table in TABLES}


def estimated_bytes(capacities: dict[str, int]) -> dict[str, int]:
    """Estimate the manifest's data size before asking the controller to hold it."""
    per_table = {
        table.name: table.row_bytes() * capacities[table.symbol] for table in TABLES
    }
    per_table["Header"] = len(HEADER_SCALARS) * 4 + len(TABLES) * 8 + 2 * (
        KEY_STRING_LENGTH + 4
    )
    per_table["Total"] = sum(
        value for key, value in per_table.items() if key != "Total"
    )
    return per_table


def string_type() -> str:
    return f"""<DataType Name="{KEY_STRING_TYPE}" Family="StringFamily" Class="User">
<Members>
<Member Name="LEN" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false"/>
<Member Name="DATA" DataType="SINT" Dimension="{KEY_STRING_LENGTH}" Radix="ASCII" Hidden="false"/>
</Members>
</DataType>"""


def member(name: str, data_type: str) -> str:
    radix = "NullType" if data_type == KEY_STRING_TYPE else "Decimal"
    return (
        f'<Member Name="{name}" DataType="{data_type}" Dimension="0" '
        f'Radix="{radix}" Hidden="false" ExternalAccess="Read Only"/>'
    )


def header_type() -> str:
    members = [member(name, "DINT") for name in HEADER_SCALARS]
    members.append(member("ContentHash", KEY_STRING_TYPE))
    members.append(member("ControllerIdentity", KEY_STRING_TYPE))
    for table in TABLES:
        members.append(member(f"{table.name}Count", "DINT"))
        members.append(member(f"{table.name}Capacity", "DINT"))
    body = "\n".join(members)
    return f"""<DataType Name="{HEADER_TYPE}" Family="NoFamily" Class="User">
<Members>
{body}
</Members>
</DataType>"""


def row_type(table: Table) -> str:
    body = "\n".join(member(name, data_type) for name, data_type in table.members)
    return f"""<DataType Name="{table.row_type}" Family="NoFamily" Class="User">
<Members>
{body}
</Members>
</DataType>"""


def data_types() -> str:
    parts = [string_type()]
    parts.extend(row_type(table) for table in TABLES)
    parts.append(header_type())
    return "<DataTypes>\n" + "\n".join(parts) + "\n</DataTypes>"


def tags(capacities: dict[str, int]) -> str:
    entries = ["<Tags>"]
    entries.append(
        f'<Tag Name="FRK_S7_Header" TagType="Base" DataType="{HEADER_TYPE}" '
        'Constant="false" ExternalAccess="Read Only"/>'
    )
    for table in TABLES:
        entries.append(
            f'<Tag Name="{table.tag}" TagType="Base" DataType="{table.row_type}" '
            f'Dimensions="{capacities[table.symbol]}" Constant="false" '
            'ExternalAccess="Read Only"/>'
        )
    entries.append(
        scalar_tag("FRK_S7_BumpRevision", "DINT", "Decimal", "0", "Read/Write")
    )
    for name in ("FRK_S7_ScanCount", "FRK_S7_RevisionBumps"):
        entries.append(scalar_tag(name, "DINT", "Decimal", "0", "Read Only"))
    entries.append(scalar_tag("FRK_S7_Complete", "BOOL", "Decimal", "0", "Read Only"))
    entries.append("</Tags>")
    return "\n".join(entries)


def program_tags() -> str:
    return "\n".join(
        [
            "<Tags>",
            scalar_tag("FRK_S7_BumpPrev", "DINT", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


def routine_lines(capacities: dict[str, int]) -> tuple[str, ...]:
    lines = [
        "FRK_S7_ScanCount := FRK_S7_ScanCount + 1;",
        "FRK_S7_Header.Magic := 1179207246;",
        "FRK_S7_Header.SchemaMajor := 1;",
        "FRK_S7_Header.SchemaMinor := 0;",
        "FRK_S7_Header.Valid := 1;",
        "FRK_S7_Header.Truncated := 0;",
    ]
    for table in TABLES:
        capacity = capacities[table.symbol]
        lines.append(f"FRK_S7_Header.{table.name}Capacity := {capacity};")
        lines.append(f"FRK_S7_Header.{table.name}Count := {capacity};")
    # a rising edge on the one writable input is what a configuration change
    # looks like to the gateway
    lines.extend(
        [
            "IF (FRK_S7_BumpRevision = 1) AND (FRK_S7_BumpPrev = 0) THEN",
            "FRK_S7_Header.ConfigRevision := FRK_S7_Header.ConfigRevision + 1;",
            "FRK_S7_RevisionBumps := FRK_S7_RevisionBumps + 1;",
            "END_IF;",
            "FRK_S7_BumpPrev := FRK_S7_BumpRevision;",
            "FRK_S7_Complete := 1;",
        ]
    )
    return tuple(lines)


def program_block(capacities: dict[str, int]) -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(routine_lines(capacities))
    )
    return f"""<Programs>
<Program Name="{PROGRAM}" TestEdits="false" MainRoutineName="{ROUTINE}" Disabled="false" UseAsFolder="false">
{program_tags()}
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
<Task Name="FRK_S7Task" Type="PERIODIC" Rate="50" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="{PROGRAM}"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def generate(
    source: Path, output: Path, capacities: dict[str, int] | None = None
) -> dict[str, object]:
    capacities = {**default_capacities(), **(capacities or {})}
    for table in TABLES:
        value = capacities[table.symbol]
        if not 1 <= value <= 4096:
            raise ValueError(
                f"{table.symbol} must be between 1 and 4096, got {value}"
            )

    estimate = estimated_bytes(capacities)
    if estimate["Total"] > MEMORY_BUDGET_BYTES:
        raise ValueError(
            f"estimated manifest data {estimate['Total']} bytes exceeds the "
            f"{MEMORY_BUDGET_BYTES}-byte generator budget; a manifest that will "
            "not download measures nothing"
        )

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
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 seed: {missing}")

    logic = "\n".join(routine_lines(capacities))
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", logic):
        raise AssertionError("fixture logic contains an I/O operand")
    if "/" in logic:
        raise AssertionError("fixture logic contains a division")

    text = replace_once(text, "<DataTypes/>", data_types())
    text = replace_once(text, "<Tags/>", tags(capacities))
    text = replace_once(text, "<Programs/>", program_block(capacities))
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
        "Capacities": capacities,
        "EstimatedBytes": estimate,
        "RowBytes": {table.name: table.row_bytes() for table in TABLES},
        "Tables": [table.name for table in TABLES],
        "WritableInputs": ["FRK_S7_BumpRevision"],
        "Programs": 1,
        "Tasks": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    # Symbols are deduplicated: Modules and Nameplates are both bounded by
    # FRK_MAX_MODULES, because a nameplate belongs to a module and a manifest
    # that could hold more of one than the other would be incoherent.
    for symbol in dict.fromkeys(table.symbol for table in TABLES):
        parser.add_argument(
            f"--{symbol.lower().replace('_', '-')}",
            type=int,
            default=None,
            help=f"capacity for {symbol}",
        )
    args = parser.parse_args()
    overrides = {}
    for symbol in dict.fromkeys(table.symbol for table in TABLES):
        value = getattr(args, symbol.lower())
        if value is not None:
            overrides[symbol] = value
    try:
        evidence = generate(args.source, args.output, overrides)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR [s7-manifest-fixture] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
