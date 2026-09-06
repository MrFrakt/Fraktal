#!/usr/bin/env python3
"""Generate the disposable S12 type-acceptance probe projects.

AB §3.8 needs a complete Core->Logix->repository type table before any public
UDT is generated, and it forbids silent narrowing. The first question is simply
which candidate Logix types the pinned v33 target accepts at all: Part III
cannot assume a native `TIME`/`TIME32` exists, and controller families and
revisions differ on the wider atomics.

This tool emits one minimal full-project L5X per probe case from a named target
profile. The accepted v33 profile remains the default used by the Phase 0 gate;
other profiles are explicit and carry their acceptance status in the result.
Each case is deliberately tiny so an import or Verify failure names exactly one
type. Every base candidate is emitted twice:

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
import re
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, sha256


SCHEMA = "fraktal.ab.s12-type-probe"
SCHEMA_VERSION = 2
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


@dataclass(frozen=True)
class ProbeProfile:
    """A target-bound case set whose status cannot be mistaken for acceptance."""

    key: str
    controller: str
    revision: str
    status: str
    candidates: tuple[Candidate, ...]
    # These are operation-only discriminator cases. Their declarations are
    # already covered by the corresponding base candidate.
    supplemental_uses: tuple[Candidate, ...] = ()


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

V38_DURATION_USES: tuple[Candidate, ...] = (
    Candidate(
        "time_typed_literal",
        "duration, native TIME with typed literal",
        "TIME",
        None,
        0,
        f"{TAG} := {TAG} + T#1ms;",
    ),
    Candidate(
        "time32_typed_literal",
        "duration, native TIME32 with typed literal",
        "TIME32",
        None,
        0,
        f"{TAG} := {TAG} + T32#1ms;",
    ),
    Candidate(
        "time_matched",
        "duration, native TIME with matched operands",
        "TIME",
        None,
        0,
        f"{TAG} := {TAG} + {TAG};",
    ),
    Candidate(
        "time32_matched",
        "duration, native TIME32 with matched operands",
        "TIME32",
        None,
        0,
        f"{TAG} := {TAG} + {TAG};",
    ),
)

V33_PROFILE = ProbeProfile(
    key="v33-5370",
    controller=CONTROLLER,
    revision=REVISION,
    status="accepted-baseline",
    candidates=CANDIDATES,
)

V38_EXPLORATORY_PROFILE = ProbeProfile(
    key="v38-5380-exploratory",
    controller="5069-L310ER",
    revision="38",
    status="exploratory-not-accepted",
    candidates=CANDIDATES,
    supplemental_uses=V38_DURATION_USES,
)

PROFILES = {
    profile.key: profile
    for profile in (V33_PROFILE, V38_EXPLORATORY_PROFILE)
}


def _empty(element: ElementTree.Element | None) -> bool:
    return (
        element is not None
        and len(element) == 0
        and not (element.text or "").strip()
    )


def _studio_default_programs(programs: ElementTree.Element) -> bool:
    if len(programs) != 1:
        return False
    program = programs[0]
    if (
        program.tag != "Program"
        or program.get("Name") != "MainProgram"
        or program.get("MainRoutineName") != "MainRoutine"
    ):
        return False
    if [child.tag for child in program] != ["Tags", "Routines"]:
        return False
    tags = program.find("Tags")
    routines = program.find("Routines")
    if not _empty(tags) or routines is None or len(routines) != 1:
        return False
    routine = routines[0]
    return (
        routine.tag == "Routine"
        and routine.get("Name") == "MainRoutine"
        and routine.get("Type") == "RLL"
        and _empty(routine)
    )


def _studio_default_tasks(tasks: ElementTree.Element) -> bool:
    if len(tasks) != 1:
        return False
    task = tasks[0]
    if (
        task.tag != "Task"
        or task.get("Name") != "MainTask"
        or task.get("Type") != "CONTINUOUS"
    ):
        return False
    if [child.tag for child in task] != ["ScheduledPrograms"]:
        return False
    scheduled = task.find("ScheduledPrograms")
    return (
        scheduled is not None
        and len(scheduled) == 1
        and scheduled[0].tag == "ScheduledProgram"
        and scheduled[0].get("Name") == "MainProgram"
        and _empty(scheduled[0])
    )


def _replace_container(text: str, name: str) -> str:
    pattern = re.compile(rf"<{name}(?:\s[^>]*)?>.*?</{name}>", re.DOTALL)
    matches = tuple(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"source has {len(matches)} expanded <{name}> containers")
    match = matches[0]
    return text[:match.start()] + f"<{name}/>" + text[match.end():]


def normalize_empty_seed(text: str) -> str:
    """Normalize only Studio's exact inert default program/task seed shape."""

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ValueError(f"source is not well-formed XML: {exc}") from exc
    controller = root.find("Controller")
    if controller is None:
        raise ValueError("source has no Controller element")

    programs = controller.find("Programs")
    tasks = controller.find("Tasks")
    if programs is None or tasks is None:
        return text

    if len(programs) > 0:
        if not _studio_default_programs(programs):
            raise ValueError("source Programs are not the inert Studio default")
        text = _replace_container(text, "Programs")
    if len(tasks) > 0:
        if not _studio_default_tasks(tasks):
            raise ValueError("source Tasks are not the inert Studio default")
        text = _replace_container(text, "Tasks")
    return text


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
    source: Path,
    output: Path,
    candidate: Candidate,
    mode: str,
    *,
    profile: ProbeProfile = V33_PROFILE,
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

    text = normalize_empty_seed(source.read_text(encoding="utf-8-sig"))
    required = (
        f'ProcessorType="{profile.controller}"',
        f'MajorRev="{profile.revision}"',
        "<DataTypes/>",
        "<Tags/>",
        "<Programs/>",
        "<Tasks/>",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(
            f"source is not the expected empty {profile.key} seed: {missing}"
        )

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
        "Profile": profile.key,
        "ProfileStatus": profile.status,
        "Controller": profile.controller,
        "MajorRevision": profile.revision,
        "Case": f"{candidate.key}-{mode}",
        "CoreConcept": candidate.core_concept,
        "DataType": candidate.data_type,
        "Dimensions": candidate.dimensions,
        "Mode": mode,
        "UseStatement": candidate.use_statement if mode == "use" else None,
        "Output": str(output),
        "OutputSha256": sha256(output),
    }


def generate_all(
    source: Path,
    directory: Path,
    profile: ProbeProfile = V33_PROFILE,
) -> list[dict[str, object]]:
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for candidate in profile.candidates:
        for mode in MODES:
            output = directory / f"s12_{candidate.key}_{mode}.L5X"
            results.append(
                generate_case(source, output, candidate, mode, profile=profile)
            )
    for candidate in profile.supplemental_uses:
        output = directory / f"s12_{candidate.key}_use.L5X"
        results.append(
            generate_case(source, output, candidate, "use", profile=profile)
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="empty target seed L5X")
    parser.add_argument("directory", type=Path, help="output directory")
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        default=V33_PROFILE.key,
        help=f"target profile (default: {V33_PROFILE.key})",
    )
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    try:
        results = generate_all(args.source, args.directory, profile)
    except (OSError, ValueError) as exc:
        print(f"ERROR [s12-type-probe] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(
        {
            "Schema": SCHEMA,
            "SchemaVersion": SCHEMA_VERSION,
            "Profile": profile.key,
            "ProfileStatus": profile.status,
            "Controller": profile.controller,
            "MajorRevision": profile.revision,
            "Candidates": len(profile.candidates),
            "SupplementalUseCases": len(profile.supplemental_uses),
            "Cases": results,
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
