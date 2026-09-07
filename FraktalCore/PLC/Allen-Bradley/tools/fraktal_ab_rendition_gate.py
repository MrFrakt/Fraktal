#!/usr/bin/env python3
"""Require every emitted rendition to be the graph the declaration declared.

The AB analogue of the TC3 three-rendition consistency rule. A chain carried in
more than one language has exactly one graph; each rendition is an emission of
it. This gate reads the **emitted L5X back**, recovers the step set and the
transition set from each rendition in that rendition's own language, and
requires all of them to equal the declaration.

Reading back matters more than it sounds. A generator that emits three
renditions from one declaration is only trustworthy while all three actually
say the same thing, and the way that breaks is silent: an emitter grows a case,
one language gets it, the others do not, and nothing complains because nothing
ever compared them. **A rendition that cannot be parsed back fails the build** -
"the parser found nothing, so nothing was wrong" is exactly the failure mode
this exists to remove.

What is compared is the graph, not the text: the set of step numbers, and for
each step the set of steps it can reach. Languages are free to say that
differently - ST with a CASE, ladder with EQU rung-ins and MOVs, SFC with
directed links - and the point is that they mean the same thing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fraktal_ab_declaration as decl
from fraktal_ab_generate import MARKER_CASE_ELSE


SCHEMA = "fraktal.ab.rendition-gate"
SCHEMA_VERSION = 1


class RenditionError(RuntimeError):
    """A rendition could not be read back. Silence is not parity."""


def declared_graph(chain: decl.Chain) -> dict[int, set[int]]:
    """The graph as declared: every step, and everywhere it can go."""
    graph: dict[int, set[int]] = {}
    for step in chain.steps:
        targets = {t for t in (step.on_advance, step.on_jump) if t != -1}
        graph[step.number] = targets
    return graph


def _routine_text(root: ET.Element, name: str) -> ET.Element:
    for routine in root.findall(".//Program/Routines/Routine"):
        if routine.get("Name") == name:
            return routine
    raise RenditionError(f"routine {name!r} is not in the emitted project")


def st_graph(root: ET.Element, name: str, unit_tag: str) -> dict[int, set[int]]:
    """Recover the graph from an ST rendition's CASE."""
    routine = _routine_text(root, name)
    if routine.get("Type") != "ST":
        raise RenditionError(f"{name} is {routine.get('Type')}, expected ST")
    lines = [(line.text or "") for line in routine.findall(".//STContent/Line")]
    graph: dict[int, set[int]] = {}
    current: int | None = None
    assign = re.compile(rf"{re.escape(unit_tag)}\.Step\s*:=\s*(-?\d+)\s*;")
    label = re.compile(r"^(\d+):$")
    for line in lines:
        stripped = line.strip()
        matched = label.match(stripped)
        if matched:
            current = int(matched.group(1))
            graph.setdefault(current, set())
            continue
        if MARKER_CASE_ELSE in stripped:
            # Everything past the CASE ELSE is the stall fallback. It assigns a
            # step number but it is not an edge of the declared graph, and the
            # emitter says so in the text rather than leaving it to be guessed.
            break
        if current is None:
            continue
        for target in assign.findall(line):
            graph[current].add(int(target))
    if not graph:
        raise RenditionError(f"{name}: no steps recovered from the ST rendition")
    return graph


def ld_graph(root: ET.Element, name: str, unit_tag: str) -> dict[int, set[int]]:
    """Recover the graph from a ladder rendition's rungs.

    One rung per step, gated on EQU(Step,N); the transitions are the MOVs that
    write the step tag.
    """
    routine = _routine_text(root, name)
    if routine.get("Type") != "RLL":
        raise RenditionError(f"{name} is {routine.get('Type')}, expected RLL")
    rungs = [(rung.find("Text").text or "")
             for rung in routine.findall(".//RLLContent/Rung")]
    graph: dict[int, set[int]] = {}
    order: list[int] = []
    gate = re.compile(rf"^EQU\({re.escape(unit_tag)}\.Step,(\d+)\)")
    move = re.compile(rf"MOV\((-?\d+),{re.escape(unit_tag)}\.Step\)")
    for rung in rungs:
        text = rung.strip()
        matched = gate.match(text)
        if not matched:
            continue
        number = int(matched.group(1))
        if number in graph:
            raise RenditionError(f"{name}: step {number} has more than one rung")
        order.append(number)
        graph[number] = {int(t) for t in move.findall(text)}
    if not graph:
        raise RenditionError(f"{name}: no step rungs recovered from the ladder")
    if order != sorted(order):
        # Rung order is execution order; emitting them out of step order would
        # make the text read in a different order than it runs.
        raise RenditionError(f"{name}: rungs are not in ascending step order: {order}")
    return graph


def sfc_graph(root: ET.Element, name: str) -> dict[int, set[int]]:
    """Recover the graph from an SFC rendition's steps and directed links."""
    routine = _routine_text(root, name)
    if routine.get("Type") != "SFC":
        raise RenditionError(f"{name} is {routine.get('Type')}, expected SFC")
    content = routine.find(".//SFCContent")
    if content is None:
        raise RenditionError(f"{name}: no SFCContent")

    step_number: dict[str, int] = {}
    for element in content.findall("./Step"):
        operand = element.get("Operand") or ""
        matched = re.search(r"S(\d+)$", operand)
        if not matched:
            raise RenditionError(f"{name}: step operand {operand!r} carries no number")
        step_number[element.get("ID")] = int(matched.group(1))

    successors: dict[str, list[str]] = {}
    for link in content.findall("./DirectedLink"):
        successors.setdefault(link.get("FromID"), []).append(link.get("ToID"))
    # A branch and its legs are joined by XML containment, not by a directed
    # link, so the walk has to follow that edge too - otherwise a branch looks
    # like a dead end and the chart reads as having no transitions at all. The
    # direction depends on the flow: a divergence fans out from the branch into
    # its legs, a convergence gathers its legs back into the branch.
    for branch in content.findall("./Branch"):
        diverging = (branch.get("BranchFlow") or "").lower() == "diverge"
        for leg in branch.findall("./Leg"):
            if diverging:
                successors.setdefault(branch.get("ID"), []).append(leg.get("ID"))
            else:
                successors.setdefault(leg.get("ID"), []).append(branch.get("ID"))

    def reachable_steps(start: str, seen: set[str] | None = None) -> set[int]:
        """Walk forward through transitions and branch legs to the next steps."""
        seen = seen or set()
        found: set[int] = set()
        for target in successors.get(start, []):
            if target in seen:
                continue
            seen.add(target)
            if target in step_number:
                found.add(step_number[target])
            else:
                found |= reachable_steps(target, seen)
        return found

    graph = {number: set() for number in step_number.values()}
    for element_id, number in step_number.items():
        graph[number] = reachable_steps(element_id)
    if not graph:
        raise RenditionError(f"{name}: no steps recovered from the chart")
    return graph


def compare(app: decl.Application, project: Path) -> dict[str, object]:
    """Read every rendition back and require equality with the declaration."""
    import fraktal_ab_generate as gen

    root = ET.parse(project).getroot()
    unit_tag = f"FRK_{app.name}_Unit"
    findings: list[str] = []
    chains: dict[str, object] = {}

    for chain in app.chains:
        if not chain.multi_rendition:
            continue
        declared = declared_graph(chain)
        recovered: dict[str, dict[int, set[int]]] = {}
        for rendition in chain.renditions:
            name = gen.chain_routine_name(app, chain, rendition)
            try:
                if rendition == decl.ST:
                    recovered[rendition] = st_graph(root, name, unit_tag)
                elif rendition == decl.LD:
                    recovered[rendition] = ld_graph(root, name, unit_tag)
                elif rendition == decl.SFC:
                    recovered[rendition] = sfc_graph(root, name)
                else:
                    raise RenditionError(f"unknown rendition {rendition!r}")
            except RenditionError as exc:
                findings.append(f"{chain.name}/{rendition}: {exc}")
                continue

        detail: dict[str, object] = {
            "renditions": list(chain.renditions),
            "declaredSteps": sorted(declared),
            "declaredTransitions": sum(len(v) for v in declared.values()),
        }
        for rendition, graph in recovered.items():
            if set(graph) != set(declared):
                missing = sorted(set(declared) - set(graph))
                extra = sorted(set(graph) - set(declared))
                findings.append(
                    f"{chain.name}/{rendition}: step set differs "
                    f"(missing {missing}, extra {extra})"
                )
            for number in sorted(set(graph) & set(declared)):
                if graph[number] != declared[number]:
                    findings.append(
                        f"{chain.name}/{rendition}: N{number} goes to "
                        f"{sorted(graph[number])}, declared {sorted(declared[number])}"
                    )
            detail[rendition] = {
                "steps": len(graph),
                "transitions": sum(len(v) for v in graph.values()),
                "equalsDeclaration": graph == declared,
            }
        missing_renditions = [r for r in chain.renditions if r not in recovered]
        if missing_renditions:
            detail["unreadable"] = missing_renditions
        chains[chain.name] = detail

    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "Project": str(project),
        "Application": app.name,
        "Chains": chains,
        "Findings": findings,
        "Equal": not findings,
    }


def main(argv: list[str] | None = None) -> int:
    import fraktal_ab_press_demo

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="the emitted full-project L5X")
    args = parser.parse_args(argv)
    try:
        report = compare(fraktal_ab_press_demo.application(), args.project)
    except (OSError, ET.ParseError, RenditionError) as exc:
        print(f"ERROR [rendition-gate] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["Equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
