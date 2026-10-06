#!/usr/bin/env python3
"""Compare the executable SFC content of two full-project L5X documents.

The ordinary canonical comparator
([`fraktal_ab_l5x_compare.py`](fraktal_ab_l5x_compare.py)) answers "did this
document change at all", which is the right question for an export/export pair.
It cannot answer the S4 chart question, because a generated declaration and the
Studio/SDK export derived from it may legitimately differ in element ID
numbering and sibling order while describing the same chart.

This tool therefore builds an ID-independent model of every SFC routine - steps
and their initial flag, actions with their qualifiers and bodies, transition
condition text, branch type/flow, and the link topology re-expressed over step,
transition and branch names - plus the controller's SFC execution settings, and
requires the two documents to agree. Layout coordinates are deliberately out of
scope: they are presentation, not executable content.

A branch has no name of its own in the L5X, so one is derived from the names of
its resolved neighbours. If a chart nests branches so deeply that no branch can
be resolved this way, the comparison fails closed rather than reporting a
comparison it did not actually make.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


SCHEMA = "fraktal.ab.sfc-roundtrip-comparison"
SCHEMA_VERSION = 1

SFC_SETTINGS = ("SFCExecutionControl", "SFCRestartPosition", "SFCLastScan")


class ChartError(ValueError):
    """The document cannot be modelled, so no comparison is claimed."""


def _lines(container: ElementTree.Element | None) -> list[str]:
    if container is None:
        return []
    return [(line.text or "").strip() for line in container.iter("Line")]


def _step_model(step: ElementTree.Element) -> dict[str, object]:
    return {
        "InitialStep": (step.get("InitialStep") or "false").lower(),
        "Actions": [
            {
                "Operand": action.get("Operand"),
                "Qualifier": action.get("Qualifier"),
                "IsBoolean": (action.get("IsBoolean") or "false").lower(),
                "Body": _lines(action.find("Body")),
            }
            for action in step.findall("Action")
        ],
    }


def _resolve_names(content: ElementTree.Element) -> dict[int, str]:
    """Map every element ID to an ID-independent name."""
    names: dict[int, str] = {}
    branches: list[ElementTree.Element] = []
    leg_owner: dict[int, tuple[ElementTree.Element, int]] = {}

    for element in content:
        if element.tag in {"Step", "Transition"}:
            operand = element.get("Operand")
            if not operand:
                raise ChartError(f"{element.tag} without an operand")
            names[int(element.get("ID"))] = operand
        elif element.tag == "Branch":
            branches.append(element)
            for index, leg in enumerate(element.findall("Leg")):
                leg_owner[int(leg.get("ID"))] = (element, index)

    neighbours: dict[int, set[int]] = {}
    for link in content.findall("DirectedLink"):
        source = int(link.get("FromID"))
        target = int(link.get("ToID"))
        neighbours.setdefault(source, set()).add(target)
        neighbours.setdefault(target, set()).add(source)

    unresolved = {int(branch.get("ID")): branch for branch in branches}
    while unresolved:
        progressed = False
        for branch_id, branch in list(unresolved.items()):
            known: list[str] = []
            for leg in branch.findall("Leg"):
                for neighbour in neighbours.get(int(leg.get("ID")), ()):
                    if neighbour in names:
                        known.append(names[neighbour])
            for neighbour in neighbours.get(branch_id, ()):
                if neighbour in names:
                    known.append(names[neighbour])
            if not known:
                continue
            names[branch_id] = "branch({};{};{})".format(
                branch.get("BranchType"),
                branch.get("BranchFlow"),
                ",".join(sorted(set(known))),
            )
            for leg_id, (owner, index) in leg_owner.items():
                if owner is branch:
                    names[leg_id] = f"{names[branch_id]}#leg{index}"
            del unresolved[branch_id]
            progressed = True
        if not progressed:
            raise ChartError(
                "branch names are not resolvable from named neighbours: "
                + ", ".join(str(branch_id) for branch_id in sorted(unresolved))
            )

    return names


def chart_model(path: Path) -> dict[str, object]:
    root = ElementTree.parse(path).getroot()
    controller = root.find("Controller")
    if controller is None:
        raise ChartError(f"{path} is not a full-project L5X document")

    charts: dict[str, object] = {}
    for program in controller.iter("Program"):
        for routine in program.findall("Routines/Routine"):
            if routine.get("Type") != "SFC":
                continue
            content = routine.find("SFCContent")
            if content is None:
                raise ChartError(
                    f"SFC routine {routine.get('Name')} has no SFCContent"
                )
            names = _resolve_names(content)
            steps = {
                step.get("Operand"): _step_model(step)
                for step in content.findall("Step")
            }
            transitions = {
                transition.get("Operand"): _lines(transition.find("Condition"))
                for transition in content.findall("Transition")
            }
            branches = sorted(
                names[int(branch.get("ID"))] for branch in content.findall("Branch")
            )
            edges = sorted(
                (names[int(link.get("FromID"))], names[int(link.get("ToID"))])
                for link in content.findall("DirectedLink")
            )
            charts[f"{program.get('Name')}/{routine.get('Name')}"] = {
                "Steps": steps,
                "Transitions": transitions,
                "Branches": branches,
                "Edges": [list(edge) for edge in edges],
            }

    return {
        "Settings": {name: controller.get(name) for name in SFC_SETTINGS},
        "Charts": charts,
    }


def differences(first: dict[str, object], second: dict[str, object]) -> list[str]:
    found: list[str] = []
    for name in SFC_SETTINGS:
        left = first["Settings"][name]
        right = second["Settings"][name]
        if left != right:
            found.append(f"controller {name}: {left!r} vs {right!r}")

    left_charts: dict[str, object] = first["Charts"]
    right_charts: dict[str, object] = second["Charts"]
    for missing in sorted(set(left_charts) - set(right_charts)):
        found.append(f"chart only in the first document: {missing}")
    for added in sorted(set(right_charts) - set(left_charts)):
        found.append(f"chart only in the second document: {added}")

    for name in sorted(set(left_charts) & set(right_charts)):
        left = left_charts[name]
        right = right_charts[name]
        for part in ("Steps", "Transitions", "Branches", "Edges"):
            if left[part] != right[part]:
                found.append(f"{name}: {part.lower()} differ")
    return found


def compare(first: Path, second: Path) -> dict[str, object]:
    first_model = chart_model(first)
    second_model = chart_model(second)
    found = differences(first_model, second_model)
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "First": str(first),
        "Second": str(second),
        "Settings": first_model["Settings"],
        "ChartsCompared": sorted(first_model["Charts"]),
        "StepsCompared": sum(
            len(chart["Steps"]) for chart in first_model["Charts"].values()
        ),
        "Differences": found,
        "Equivalent": not found,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument(
        "--require-charts",
        type=int,
        default=1,
        help="minimum number of SFC routines both documents must contain",
    )
    args = parser.parse_args(argv)
    try:
        report = compare(args.first, args.second)
    except (OSError, ChartError, ElementTree.ParseError) as exc:
        print(f"ERROR [sfc-roundtrip-compare] {exc}", file=sys.stderr)
        return 2
    if len(report["ChartsCompared"]) < args.require_charts:
        report["Equivalent"] = False
        report["Differences"].append(
            f"expected at least {args.require_charts} SFC routine(s), "
            f"found {len(report['ChartsCompared'])}"
        )
    print(json.dumps(report, indent=2))
    return 0 if report["Equivalent"] else 1


if __name__ == "__main__":
    sys.exit(main())
