#!/usr/bin/env python3
"""Generate the disposable S9 snapshot-coherence fixture.

S7 measured manifest reads and found every snapshot coherent — but only because
nothing changed the manifest mid-read. That left the real question open: **when
data does change under a reader, does the coherence token actually catch it?**
A detector that never fires is indistinguishable from a detector that works, and
S7's evidence explicitly recorded that gap.

AB §3.10/§11.2 specify the reader's obligation as retry-until-stable: read the
revision, read the data, read the revision again, and accept only if it did not
move. This fixture is built to put that rule under load and answer two things
the gateway design depends on:

1. **Does the guard fire?** With data mutating faster than a read completes, a
   revision-guarded read must reject, and an *unguarded* read of the same array
   must be observably inconsistent — otherwise the experiment proved nothing.
2. **Is retry-until-stable viable, or is a PLC-side double buffer required?**
   The mutation rate is a writable parameter, so the probe can sweep it and
   measure how often a guarded read succeeds. If a plausible mutation rate makes
   coherent reads impossible, retry is not a strategy and the snapshot needs
   double buffering.

The payload is a `DINT[1024]` whose every element carries the current
generation, so a coherent snapshot is trivially checkable — all elements equal —
and a torn one names the two generations it straddles. The array is the size S1
already proved as a fragmented 4 KiB read, so read duration is known ground.

This is pre-gate evidence tooling, not a production snapshot implementation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import (
    dint_array_tag,
    replace_once,
    scalar_tag,
    sha256,
)


SCHEMA = "fraktal.ab.s9-coherence-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"

PROGRAM = "FRK_S9Program"
ROUTINE = "FRK_S9Main"
DATA_TAG = "FRK_S9_Data"
DATA_LENGTH = 1024
TASK_RATE_MS = 10

# Bounds on the writable mutation period, in task scans. One means "every
# scan"; the ceiling keeps a mistyped value from parking the fixture in a state
# that looks like a hung mutator.
MIN_PERIOD = 1
MAX_PERIOD = 1000
DEFAULT_PERIOD = 10


def tags() -> str:
    return "\n".join(
        [
            "<Tags>",
            dint_array_tag(DATA_TAG, DATA_LENGTH, "Read Only"),
            # the coherence token: a reader brackets its read with this
            scalar_tag("FRK_S9_DataRevision", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S9_Generation", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S9_Mutations", "DINT", "Decimal", "0", "Read Only"),
            # the two writable inputs
            scalar_tag("FRK_S9_Freeze", "DINT", "Decimal", "0", "Read/Write"),
            scalar_tag(
                "FRK_S9_MutationPeriod", "DINT", "Decimal", str(DEFAULT_PERIOD),
                "Read/Write",
            ),
            scalar_tag("FRK_S9_PeriodInUse", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S9_ScanCount", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S9_Complete", "BOOL", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


def program_tags() -> str:
    return "\n".join(
        [
            "<Tags>",
            scalar_tag("FRK_S9_Countdown", "DINT", "Decimal", "0", "Read Only"),
            scalar_tag("FRK_S9_Index", "DINT", "Decimal", "0", "Read Only"),
            "</Tags>",
        ]
    )


def routine_lines() -> tuple[str, ...]:
    return (
        "FRK_S9_ScanCount := FRK_S9_ScanCount + 1;",
        # the requested period is range-checked before use, never trusted
        f"FRK_S9_PeriodInUse := {DEFAULT_PERIOD};",
        f"IF (FRK_S9_MutationPeriod >= {MIN_PERIOD}) AND "
        f"(FRK_S9_MutationPeriod <= {MAX_PERIOD}) THEN",
        "FRK_S9_PeriodInUse := FRK_S9_MutationPeriod;",
        "END_IF;",
        "IF FRK_S9_Freeze = 0 THEN",
        "FRK_S9_Countdown := FRK_S9_Countdown - 1;",
        "IF FRK_S9_Countdown <= 0 THEN",
        "FRK_S9_Countdown := FRK_S9_PeriodInUse;",
        "FRK_S9_Generation := FRK_S9_Generation + 1;",
        "FRK_S9_Mutations := FRK_S9_Mutations + 1;",
        # the whole payload moves to the new generation inside one scan, so a
        # reader can only ever straddle a scan boundary - which is exactly the
        # tearing a CIP reader is exposed to
        f"FOR FRK_S9_Index := 0 TO {DATA_LENGTH - 1} DO",
        f"{DATA_TAG}[FRK_S9_Index] := FRK_S9_Generation;",
        "END_FOR;",
        # the token is published after the payload it describes
        "FRK_S9_DataRevision := FRK_S9_DataRevision + 1;",
        "END_IF;",
        "END_IF;",
        "FRK_S9_Complete := 1;",
    )


def program_block() -> str:
    lines = "\n".join(
        f'<Line Number="{index}"><![CDATA[{statement}]]></Line>'
        for index, statement in enumerate(routine_lines())
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
<Task Name="FRK_S9Task" Type="PERIODIC" Rate="{TASK_RATE_MS}" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
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
    if "/" in logic:
        raise AssertionError("fixture logic contains a division")
    # the loop index is the one permitted variable subscript, and it is bounded
    # by the FOR itself; anything else would risk an out-of-range major fault
    subscripts = set(re.findall(r"\[([A-Za-z_][A-Za-z_0-9]*)\]", logic))
    if subscripts - {"FRK_S9_Index"}:
        raise AssertionError(f"unexpected variable subscript: {sorted(subscripts)}")

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
        "DataElements": DATA_LENGTH,
        "DataBytes": DATA_LENGTH * 4,
        "TaskRateMs": TASK_RATE_MS,
        "MutationPeriodBounds": [MIN_PERIOD, MAX_PERIOD],
        "DefaultMutationPeriod": DEFAULT_PERIOD,
        "WritableInputs": ["FRK_S9_Freeze", "FRK_S9_MutationPeriod"],
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
        print(f"ERROR [s9-coherence-fixture] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
