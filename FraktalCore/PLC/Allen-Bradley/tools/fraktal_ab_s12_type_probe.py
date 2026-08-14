#!/usr/bin/env python3
"""Generate the disposable S12 type-acceptance probe projects.

AB §3.8 needs a complete Core->Logix->repository type table before any public
UDT is generated, and it forbids silent narrowing. The first question is simply
which candidate Logix types the pinned v33 target accepts at all: Part III
cannot assume a native `TIME`/`TIME32` exists, and controller families and
revisions differ on the wider atomics.

This tool emits one minimal full-project L5X per probe case from the same empty
v33 seed the other fixtures use. Each case is deliberately tiny so an import or
Verify failure names exactly one type. Every candidate is emitted twice:

* ``declare`` puts the tag in the project and nothing else, so a failure means
  the target does not accept the data type; and
* ``use`` adds one type-appropriate statement, so a failure *after* ``declare``
  passed means the type exists but that operation does not compile.

Separating the two is the whole point. A single combined fixture that failed
would only prove "something in here is unsupported", which is not a type table.

These are offline compiler probes. They are never downloaded: acceptance is a
Studio Verify result, not a runtime result.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, sha256


SCHEMA = "fraktal.ab.s12-type-probe"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

TAG = "FRK_S12_Probe"
PROGRAM = "FRK_S12Program"
ROUTINE = "FRK_S12Main"


@dataclass(frozen=True)
class Candidate:
    """One Core concept and the Logix spelling being tested for it."""

    key: str
    core_concept: str
    data_type: str
    # None means the type needs no extra declaration; a string is emitted into
    # the project's <DataTypes> section first.
    user_type: str | None
    dimensions: int
    # The operation a generated Fraktal contract would actually perform.
    use_statement: str


def _udt(name: str) -> str:
    return (
        f'<DataType Name="{name}" Family="NoFamily" Class="User">\n'
        "<Members>\n"
        '<Member Name="SchemaVersion" DataType="INT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
        '<Member Name="Flag" DataType="BOOL" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
        '<Member Name="Count" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
        '<Member Name="Ratio" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read Only"/>\n'
        "</Members>\n"
        "</DataType>"
    )


CANDIDATES: tuple[Candidate, ...] = (
    Candidate("sint", "8-bit signed integer", "SINT", None, 0,
              f"{TAG} := {TAG} + 1;"),
    Candidate("int", "16-bit signed integer", "INT", None, 0,
              f"{TAG} := {TAG} + 1;"),
    Candidate("dint", "32-bit signed integer", "DINT", None, 0,
              f"{TAG} := {TAG} + 1;"),
    Candidate("lint", "64-bit signed integer", "LINT", None, 0,
              f"{TAG} := {TAG} + 1;"),
    # v33 rejected `LINT + <literal>` with "Argument must match parameter data
    # type", which does not by itself prove LINT arithmetic is unavailable -
    # only that the DINT literal is not promoted. This case separates the two,
    # and the answer decides whether LINT is usable or transport-only.
    Candidate("lintmatched", "64-bit integer, matched operands", "LINT", None, 0,
              f"{TAG} := {TAG} + {TAG};"),
    Candidate("real", "32-bit float", "REAL", None, 0,
              f"{TAG} := {TAG} * 1.5;"),
    Candidate("lreal", "64-bit float", "LREAL", None, 0,
              f"{TAG} := {TAG} * 1.5;"),
    Candidate("bool", "boolean", "BOOL", None, 0,
              f"{TAG} := NOT {TAG};"),
    Candidate("bitstring", "32-bit bit string", "DINT", None, 0,
              f"{TAG} := {TAG} AND 16#0000_FFFF;"),
    Candidate("time", "duration, native TIME", "TIME", None, 0,
              f"{TAG} := {TAG} + 1;"),
    Candidate("time32", "duration, native TIME32", "TIME32", None, 0,
              f"{TAG} := {TAG} + 1;"),
    Candidate("string", "Logix STRING(82)", "STRING", None, 0,
              f"{TAG}.LEN := 0;"),
    Candidate("array", "DINT array, lower bound", "DINT", None, 10,
              f"{TAG}[0] := {TAG}[9] + 1;"),
    Candidate("udt", "mixed-member public UDT", "FRK_T_S12Layout",
              _udt("FRK_T_S12Layout"), 0,
              f"{TAG}.Count := {TAG}.Count + 1;"),
)

MODES = ("declare", "use")


def tag_element(candidate: Candidate) -> str:
    dimensions = (
        "" if candidate.dimensions == 0 else f' Dimensions="{candidate.dimensions}"'
    )
    return (
        f'<Tag Name="{TAG}" TagType="Base" DataType="{candidate.data_type}"'
        f'{dimensions} Constant="false" ExternalAccess="Read/Write"/>'
    )


def statements(candidate: Candidate, mode: str) -> tuple[str, ...]:
    # A probe always carries one statement that is certainly valid, so an empty
    # routine can never be the reason a case fails.
    baseline = ("FRK_S12_Scan := FRK_S12_Scan + 1;",)
    if mode == "declare":
        return baseline
    return baseline + (candidate.use_statement,)


def program_block(candidate: Candidate, mode: str) -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(statements(candidate, mode))
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


def generate_case(
    source: Path, output: Path, candidate: Candidate, mode: str
) -> dict[str, object]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    if source.suffix.lower() != ".l5x" or output.suffix.lower() != ".l5x":
        raise ValueError("source and output must use the .L5X extension")
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

    if candidate.user_type is not None:
        text = replace_once(
            text, "<DataTypes/>", f"<DataTypes>\n{candidate.user_type}\n</DataTypes>"
        )
    tags = "\n".join(
        [
            "<Tags>",
            tag_element(candidate),
            '<Tag Name="FRK_S12_Scan" TagType="Base" DataType="DINT" '
            'Radix="Decimal" Constant="false" ExternalAccess="Read Only"/>',
            "</Tags>",
        ]
    )
    text = replace_once(text, "<Tags/>", tags)
    text = replace_once(text, "<Programs/>", program_block(candidate, mode))
    text = replace_once(text, "<Tasks/>", TASKS)

    output.write_text(text, encoding="utf-8", newline="\n")
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Case": f"{candidate.key}-{mode}",
        "CoreConcept": candidate.core_concept,
        "DataType": candidate.data_type,
        "Dimensions": candidate.dimensions,
        "Mode": mode,
        "UseStatement": candidate.use_statement if mode == "use" else None,
        "Output": str(output),
        "OutputSha256": sha256(output),
    }


def generate_all(source: Path, directory: Path) -> list[dict[str, object]]:
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for candidate in CANDIDATES:
        for mode in MODES:
            output = directory / f"s12_{candidate.key}_{mode}.L5X"
            results.append(generate_case(source, output, candidate, mode))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="empty v33 seed L5X")
    parser.add_argument("directory", type=Path, help="output directory")
    args = parser.parse_args()
    try:
        results = generate_all(args.source, args.directory)
    except (OSError, ValueError) as exc:
        print(f"ERROR [s12-type-probe] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(
        {
            "Schema": SCHEMA,
            "SchemaVersion": SCHEMA_VERSION,
            "Candidates": len(CANDIDATES),
            "Cases": results,
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
