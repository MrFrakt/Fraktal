#!/usr/bin/env python3
"""Census the constructs in a full-project L5X and compare two documents.

This closes a real hole in the S4 evidence. The canonical comparator
([`fraktal_ab_l5x_compare.py`](fraktal_ab_l5x_compare.py)) compares an export
against a later export, and both of those have already been through Studio. A
construct that Studio silently dropped or rewrote during the *first* import
would be equally absent from both passes, and the canonical comparison would
happily report "equivalent".

So the question S4 actually asks — does a generated construct survive the round
trip — can only be answered by comparing the **generated declaration** against
the **first export**. That comparison cannot be textual: Studio reorders
siblings, renumbers chart elements, and fills in default attributes. This tool
therefore builds an order-independent census of what a project contains:

* user data types, their family and member list;
* Add-On Instruction definitions, their parameters, local tags, routines and
  the three `Execute*` scan flags;
* controller and program tags with type, dimensions, constant flag and
  External Access;
* programs, their main routine, and every routine with its type and body size;
* tasks with type, rate, priority, watchdog and scheduled programs; and
* how many elements carry a description, since documentation is an export
  option and can be lost silently.

Attributes Studio is known to normalize are deliberately not compared. What is
compared is identity and executable shape.

An **absent** attribute is compared as absent, not as its default. That is
intentional: Studio writes the default on export, so a generator that omits an
attribute produces a document that differs from its own export. Flagging it
here is what forces the generator to be explicit, instead of leaving a
difference that a later diff would misread as drift.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


SCHEMA = "fraktal.ab.l5x-inventory"
SCHEMA_VERSION = 1


class InventoryError(ValueError):
    """The document cannot be censused, so no comparison is claimed."""


def _description_count(element: ElementTree.Element) -> int:
    return sum(1 for _ in element.iter("Description"))


def _members(data_type: ElementTree.Element) -> list[dict[str, str | None]]:
    return [
        {
            "name": member.get("Name"),
            "dataType": member.get("DataType"),
            "dimension": member.get("Dimension"),
            "radix": member.get("Radix"),
        }
        for member in data_type.findall("Members/Member")
        # Logix materialises a hidden backing member for BOOL packing; it is an
        # implementation detail of the same declaration, not a construct.
        if (member.get("Hidden") or "false").lower() != "true"
    ]


def _tags(container: ElementTree.Element | None) -> dict[str, dict[str, str | None]]:
    if container is None:
        return {}
    return {
        tag.get("Name"): {
            "dataType": tag.get("DataType"),
            "dimensions": tag.get("Dimensions"),
            "constant": (tag.get("Constant") or "false").lower(),
            "externalAccess": tag.get("ExternalAccess"),
        }
        for tag in container.findall("Tag")
    }


def _routine_body(routine: ElementTree.Element) -> dict[str, object]:
    kind = routine.get("Type")
    body: dict[str, object] = {"type": kind}
    if kind == "ST":
        body["lines"] = len(routine.findall("STContent/Line"))
    elif kind == "RLL":
        body["rungs"] = len(routine.findall("RLLContent/Rung"))
    elif kind == "SFC":
        content = routine.find("SFCContent")
        body["steps"] = len(content.findall("Step")) if content is not None else 0
        body["transitions"] = (
            len(content.findall("Transition")) if content is not None else 0
        )
        body["branches"] = len(content.findall("Branch")) if content is not None else 0
    return body


def inventory(path: Path) -> dict[str, object]:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as exc:
        raise InventoryError(f"cannot parse {path}: {exc}") from exc
    controller = root.find("Controller")
    if controller is None:
        raise InventoryError(f"{path} is not a full-project L5X document")

    data_types = {
        data_type.get("Name"): {
            "family": data_type.get("Family"),
            "class": data_type.get("Class"),
            "members": _members(data_type),
        }
        for data_type in controller.findall("DataTypes/DataType")
    }

    add_on_instructions = {}
    for definition in controller.findall(
        "AddOnInstructionDefinitions/AddOnInstructionDefinition"
    ):
        add_on_instructions[definition.get("Name")] = {
            "revision": definition.get("Revision"),
            "executePrescan": (definition.get("ExecutePrescan") or "false").lower(),
            "executePostscan": (definition.get("ExecutePostscan") or "false").lower(),
            "executeEnableInFalse": (
                definition.get("ExecuteEnableInFalse") or "false"
            ).lower(),
            "parameters": [
                {
                    "name": parameter.get("Name"),
                    "dataType": parameter.get("DataType"),
                    "usage": parameter.get("Usage"),
                    "required": (parameter.get("Required") or "false").lower(),
                }
                for parameter in definition.findall("Parameters/Parameter")
            ],
            "localTags": sorted(
                local.get("Name")
                for local in definition.findall("LocalTags/LocalTag")
            ),
            "routines": {
                routine.get("Name"): _routine_body(routine)
                for routine in definition.findall("Routines/Routine")
            },
        }

    programs = {}
    for program in controller.findall("Programs/Program"):
        programs[program.get("Name")] = {
            "mainRoutine": program.get("MainRoutineName"),
            "tags": _tags(program.find("Tags")),
            "routines": {
                routine.get("Name"): _routine_body(routine)
                for routine in program.findall("Routines/Routine")
            },
        }

    tasks = {
        task.get("Name"): {
            "type": task.get("Type"),
            "rate": task.get("Rate"),
            "priority": task.get("Priority"),
            "watchdog": task.get("Watchdog"),
            "scheduled": sorted(
                scheduled.get("Name")
                for scheduled in task.findall("ScheduledPrograms/ScheduledProgram")
            ),
        }
        for task in controller.findall("Tasks/Task")
    }

    return {
        "DataTypes": data_types,
        "AddOnInstructions": add_on_instructions,
        "ControllerTags": _tags(controller.find("Tags")),
        "Programs": programs,
        "Tasks": tasks,
        "DescriptionCount": _description_count(controller),
    }


def _compare_mapping(
    kind: str, first: dict[str, object], second: dict[str, object]
) -> list[str]:
    found: list[str] = []
    for missing in sorted(set(first) - set(second)):
        found.append(f"{kind} lost in the second document: {missing}")
    for added in sorted(set(second) - set(first)):
        found.append(f"{kind} only in the second document: {added}")
    for name in sorted(set(first) & set(second)):
        if first[name] != second[name]:
            found.append(f"{kind} differs: {name}")
    return found


def differences(first: dict[str, object], second: dict[str, object]) -> list[str]:
    found: list[str] = []
    for kind in ("DataTypes", "AddOnInstructions", "ControllerTags", "Programs", "Tasks"):
        found.extend(_compare_mapping(kind, first[kind], second[kind]))
    if first["DescriptionCount"] != second["DescriptionCount"]:
        found.append(
            "description count differs: "
            f"{first['DescriptionCount']} vs {second['DescriptionCount']}"
        )
    return found


def compare(first: Path, second: Path) -> dict[str, object]:
    first_inventory = inventory(first)
    second_inventory = inventory(second)
    found = differences(first_inventory, second_inventory)
    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "First": str(first),
        "Second": str(second),
        "Counts": {
            kind: len(first_inventory[kind])
            for kind in ("DataTypes", "AddOnInstructions", "ControllerTags",
                         "Programs", "Tasks")
        },
        "DescriptionCount": first_inventory["DescriptionCount"],
        "Differences": found,
        "Equivalent": not found,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path, nargs="?")
    parser.add_argument(
        "--dump", action="store_true",
        help="print the census of the first document instead of comparing",
    )
    args = parser.parse_args(argv)
    try:
        if args.dump or args.second is None:
            print(json.dumps(inventory(args.first), indent=2, sort_keys=True))
            return 0
        report = compare(args.first, args.second)
    except (OSError, InventoryError) as exc:
        print(f"ERROR [l5x-inventory] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["Equivalent"] else 1


if __name__ == "__main__":
    sys.exit(main())
