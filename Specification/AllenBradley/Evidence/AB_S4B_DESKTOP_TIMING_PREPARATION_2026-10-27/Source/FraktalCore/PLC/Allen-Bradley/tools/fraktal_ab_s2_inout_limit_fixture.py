#!/usr/bin/env python3
"""Generate disposable v33 S2 AOI InOut-count boundary fixtures.

The generated controller contains one memory-only AOI with a requested number
of DINT InOut parameters and one unconditional call site.  It exists only to
let the installed Studio 5000 v33 compiler decide the target's 64/65 boundary;
it is not production Fraktal code and is never downloaded to the controller.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256
from fraktal_ab_s2_fixture import parameter


SCHEMA = "fraktal.ab.s2-inout-limit-fixture"
SCHEMA_VERSION = 1
CONTROLLER = "1769-L24ER-QB1B"
REVISION = "33"
DEFAULT_INOUT_COUNT = 64
AOI_NAME = "FRK_S2_InOutLimit"
INSTANCE_NAME = "FRK_S2_InOutInstance"


def reference_names(count: int) -> tuple[str, ...]:
    if not 1 <= count <= 65:
        raise ValueError("InOut count must be between 1 and 65")
    return tuple(f"FRK_S2_Ref{index:03d}" for index in range(1, count + 1))


def aoi_definition(names: tuple[str, ...]) -> str:
    parameters = [
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
    ]
    parameters.extend(parameter(name, "DINT", "InOut") for name in names)
    return f"""<AddOnInstructionDefinition Name="{AOI_NAME}" Revision="1.0" ExecutePrescan="false" ExecutePostscan="false" ExecuteEnableInFalse="false" CreatedDate="2026-08-13T00:00:00.000Z" CreatedBy="Fraktal" EditedDate="2026-08-13T00:00:00.000Z" EditedBy="Fraktal" SoftwareRevision="v33.00">
<RevisionNote><![CDATA[Disposable S2 InOut-count boundary evidence.]]></RevisionNote>
<Parameters>
{chr(10).join(parameters)}
</Parameters>
<LocalTags/>
<Routines>
<Routine Name="Logic" Type="ST">
<STContent>
<Line Number="0"><![CDATA[{names[0]} := {names[0]};]]></Line>
</STContent>
</Routine>
</Routines>
<Dependencies/>
</AddOnInstructionDefinition>"""


def tags(names: tuple[str, ...]) -> str:
    tag_lines = [
        "<Tags>",
        (
            f'<Tag Name="{INSTANCE_NAME}" TagType="Base" '
            f'DataType="{AOI_NAME}" Constant="false" ExternalAccess="None"/>'
        ),
    ]
    tag_lines.extend(
        scalar_tag(name, "DINT", "Decimal", "0", "None") for name in names
    )
    tag_lines.append("</Tags>")
    return "\n".join(tag_lines)


def programs(names: tuple[str, ...]) -> str:
    arguments = ",".join((INSTANCE_NAME, *names))
    return f"""<Programs>
<Program Name="FRK_S2InOutProgram" TestEdits="false" MainRoutineName="FRK_S2InOutMain" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
<Routine Name="FRK_S2InOutMain" Type="ST">
<STContent>
<Line Number="0"><![CDATA[{AOI_NAME}({arguments});]]></Line>
</STContent>
</Routine>
</Routines>
</Program>
</Programs>"""


TASKS = """<Tasks>
<Task Name="FRK_S2InOutTask" Type="PERIODIC" Rate="10" Watchdog="500" Priority="10" DisableUpdateOutputs="true" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="FRK_S2InOutProgram"/>
</ScheduledPrograms>
</Task>
</Tasks>"""


def generate(source: Path, output: Path, inout_count: int) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    names = reference_names(inout_count)
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
        "<AddOnInstructionDefinitions/>",
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected empty v33 fixture: {missing}")

    text = replace_once(
        text,
        "<AddOnInstructionDefinitions/>",
        "<AddOnInstructionDefinitions>\n"
        + aoi_definition(names)
        + "\n</AddOnInstructionDefinitions>",
    )
    text = replace_once(text, "<Tags/>", tags(names))
    text = replace_once(text, "<Programs/>", programs(names))
    text = replace_once(text, "<Tasks/>", TASKS)
    text, inhibit_count = re.subn(
        r'(<Module Name="Discrete_IO"[^>]*\bInhibited=")false("[^>]*>)',
        r"\1true\2",
        text,
        count=1,
    )
    if inhibit_count != 1:
        raise ValueError("embedded Discrete_IO module was not inhibited exactly once")
    if re.search(r"\b(?:Local|Discrete_IO):[IOC]", text):
        raise AssertionError("fixture contains an I/O operand")

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
        "InOutParameters": inout_count,
        "AoiDefinitions": 1,
        "ControllerTags": inout_count + 1,
        "PhysicalIoReferences": 0,
        "EmbeddedIoInhibited": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--inout-count", type=int, default=DEFAULT_INOUT_COUNT
    )
    args = parser.parse_args()
    try:
        evidence = generate(args.source, args.output, args.inout_count)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
