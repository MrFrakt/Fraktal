#!/usr/bin/env python3
"""Walk the AUTO graph in every rendition and require identical traces.

S11 proved ST and native SFC walk the same graph on this controller. This
extends that method to the third language: the same declared AUTO graph is
walked in ST, in the SFC chart and in the ladder state machine, and the three
traces must be identical.

**How equality is decided, and why it is not sampling.** Polling a 10 ms task
over a link that costs about 3 ms a read cannot promise to catch a step that
lasts one scan, so a sampled sequence is evidence of what was *seen*, not of
what *ran*. The chart the application already publishes is the trace: per-step
visit counts and per-step durations, written by the running logic itself. One
cycle from a reset state gives a deterministic per-step entry count, and two
renditions that walked the same graph produce the same vector. The sampled
sequence is recorded alongside it as corroboration, never as the claim.

Three things are compared for each rendition:

* the **entry-count vector** over all declared steps, after exactly one cycle;
* the **step set actually entered**, which must be the declared set for the
  path taken; and
* the **ordering evidence** the application keeps itself - ``OrderFail`` zero,
  meaning every child module ran before sequence intent on every scan.

The held condition is then exercised in each rendition, because a language that
walks the same steps but mishandles a hold has not reproduced the behaviour.

Values are reported as shape and status; the record carries
``values_redacted: true``.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo
import fraktal_ab_press_execute as px


SCHEMA = "fraktal.ab.press-parity"
SCHEMA_VERSION = 1

APP = px.APP
AUTO = next(c for c in APP.chains if c.name == "AUTO")
RENDITION = gen.rendition_tag(APP)
STEPS_ORDER = gen.ordered_steps(APP)
AUTO_INDEXES = {s.number: STEPS_ORDER.index(s.number) for s in AUTO.steps}

# Where the chain goes when it closes its loop: the terminal step's advance.
_TERMINAL = max(AUTO.steps, key=lambda s: s.number)
LOOP_TARGET = _TERMINAL.on_advance if AUTO.loops else None
# Withdrawing the part lets the chain park on its own start-await step, which is
# where the loop closes - so every rendition ends its window on the same step.
PARK_STEP = LOOP_TARGET
# The step the chain reaches once it has genuinely passed the start step. Waiting
# for "not the start step" would be satisfied by the init step the chain begins
# on, and the condition would be withdrawn before the cycle ever started.
AFTER_PARK = next((s.on_advance for s in AUTO.steps if s.number == PARK_STEP), None)


def select(comm: Any, rendition: str) -> bool:
    return px.write(comm, RENDITION, gen.rendition_ordinal(rendition))


def reset_chart(comm: Any, settle: float) -> None:
    """Zero the marks so each rendition's cycle is counted from the same start."""
    px.write(comm, px.RUN, 0)
    px.write(comm, px.RESET, 1)
    time.sleep(min(settle, 0.2))
    px.write(comm, px.RESET, 0)


def entry_vector(chart: dict[str, Any]) -> dict[int, int]:
    """Per-declared-step entry counts, keyed by step number."""
    return {number: chart["EnterCount"][index]
            for number, index in sorted(AUTO_INDEXES.items())}


def sampled_trace(comm: Any, settle: float, until: Any) -> list[int]:
    """Corroborating sample of the live step, in order, without repeats."""
    deadline = time.monotonic() + settle
    seen: list[int] = []
    while time.monotonic() < deadline:
        unit = px.read_unit(comm)
        if unit is None:
            break
        step = unit["Step"]
        if not seen or seen[-1] != step:
            seen.append(step)
        if until(unit):
            break
        time.sleep(0.002)
    return seen


def walk_one_cycle(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Run exactly one AUTO cycle in one rendition and return its trace."""
    px.write(comm, px.MODE, px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 1)
    for name in px.FAULT:
        px.write(comm, px.FAULT[name], 0)
    select(comm, rendition)
    reset_chart(comm, settle)

    before = px.read_unit(comm)
    # The marks are cumulative and nothing clears them, so a rendition's trace
    # is the delta over its own window.
    chart_before = px.read_chart(comm)
    started = time.monotonic()
    px.write(comm, px.RUN, 1)
    # Withdraw the start condition as soon as the chain has left the start step,
    # not after the cycle finishes. Withdrawing late is a race: if the write
    # lands after the loop has already re-armed the step, the chain runs a whole
    # further traversal and the window holds two cycles instead of one. Nothing
    # after the start step reads this condition, so removing it here cannot
    # affect the cycle being measured - it only guarantees the loop closes into
    # a parked step.
    px.await_unit(comm, lambda u: u["Step"] == AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    trace = sampled_trace(
        comm, settle,
        lambda u: before is not None and u["CycleCount"] > before["CycleCount"])
    observed, _ = px.await_unit(
        comm, lambda u: before is not None and u["CycleCount"] > before["CycleCount"],
        settle)
    elapsed = (time.monotonic() - started) * 1000.0

    # Close the window with the machine, not with the observer. A looping chain
    # closes its loop the scan after it finishes, and a read plus a write costs
    # more than one 10 ms period - so stopping it by hand caught each rendition
    # at whatever step its own speed had reached, and the trace window was
    # ragged rather than wrong. Withdrawing the start condition instead makes
    # every rendition park on the same declared step, whatever its speed, and
    # the window is then closed by the graph itself.
    parked, _ = px.await_unit(
        comm, lambda u: u["Step"] == PARK_STEP, settle)
    time.sleep(min(settle, 0.2))
    resting = px.read_unit(comm)
    px.write(comm, px.RUN, 0)
    px.write(comm, px.PART_PRESENT, 1)

    chart = px.read_chart(comm)
    order_fail = px.read_scalar(comm, px.ORDER_FAIL)
    after = entry_vector(chart) if chart else {}
    baseline = entry_vector(chart_before) if chart_before else {}
    counts = {n: after.get(n, 0) - baseline.get(n, 0) for n in after}

    return {
        "rendition": rendition,
        "elapsed_ms": round(elapsed, 3),
        "cycleCompleted": bool(observed and before
                               and observed["CycleCount"] > before["CycleCount"]),
        "entryCounts": counts,
        "parkedAt": None if resting is None else resting["Step"],
        "parkedAsExpected": bool(resting and resting["Step"] == PARK_STEP),
        "stepsEntered": sorted(n for n, c in counts.items() if c),
        "sampledTrace": trace,
        "orderFail": order_fail,
        "error": None if observed is None else observed["Error"],
    }


def walk_held(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Exercise the held condition at the door-close step in one rendition."""
    held_step = next(s for s in AUTO.steps if s.action == decl.HELD_AWAIT)
    px.write(comm, px.MODE, px.MODE_AUTO)
    px.write(comm, px.TWO_HAND, 1)
    select(comm, rendition)
    reset_chart(comm, settle)
    px.write(comm, px.RUN, 1)
    # Arm during the declared settle rather than racing the four-scan close.
    px.await_unit(comm, lambda u: u["Step"] == 170, settle)
    px.write(comm, px.TWO_HAND, 0)
    held, elapsed = px.await_unit(comm, lambda u: u["Held"] != 0, settle)
    chart, _ = px.await_chart(
        comm, lambda c: c["StallReason"] == demo.REASONS["TWO_HAND_RELEASED"], settle)
    px.write(comm, px.TWO_HAND, 1)
    resumed, _ = px.await_unit(
        comm, lambda u: u["Held"] == 0 and u["Step"] != held_step.number, settle)
    px.write(comm, px.RUN, 0)
    return {
        "rendition": rendition,
        "elapsed_ms": round(elapsed, 3),
        "heldStep": None if held is None else held["Step"],
        "heldReason": None if held is None else held["HeldReason"],
        "heldSeverity": None if held is None else held["HeldSeverity"],
        "errorWhileHeld": None if held is None else held["Error"],
        "stallReason": None if chart is None else chart["StallReason"],
        "resumedTo": None if resumed is None else resumed["Step"],
        "selfResumed": bool(resumed and resumed["Held"] == 0
                            and resumed["Step"] != held_step.number),
    }


def walk_abort(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Abort a running cycle in one rendition and require it to stay down."""
    px.write(comm, px.MODE, px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.TWO_HAND, 1)
    select(comm, rendition)
    reset_chart(comm, settle)
    px.write(comm, px.RUN, 1)
    px.await_unit(comm, lambda u: u["Step"] == AFTER_PARK, settle)
    px.write(comm, px.ABORT, 1)
    aborted, elapsed = px.await_unit(comm, lambda u: u["Aborted"] != 0, settle)
    time.sleep(min(settle, 0.25))
    after = px.read_unit(comm)
    px.write(comm, px.ABORT, 0)
    px.write(comm, px.RUN, 0)
    return {
        "rendition": rendition,
        "elapsed_ms": round(elapsed, 3),
        "aborted": None if aborted is None else aborted["Aborted"],
        "stepAfter": None if after is None else after["Step"],
        "runningAfter": None if after is None else after["Running"],
        "errorAfter": None if after is None else after["Error"],
        "stoodDown": bool(after and after["Running"] == 0 and after["Step"] == 0),
    }


def run(comm: Any, settle: float) -> dict[str, Any]:
    started = time.monotonic()
    renditions = list(AUTO.renditions)
    cycles = [walk_one_cycle(comm, r, settle) for r in renditions]
    helds = [walk_held(comm, r, settle) for r in renditions]

    aborts = [walk_abort(comm, r, settle) for r in renditions]
    reference = cycles[0]
    rows: list[dict[str, Any]] = []

    for cycle in cycles:
        rows.append(px.row(
            f"cycle_completes_{cycle['rendition'].lower()}",
            f"the {cycle['rendition']} rendition completes one AUTO cycle cleanly",
            cycle, cycle["elapsed_ms"],
            cycle["cycleCompleted"] and cycle["error"] == 0
            and cycle["orderFail"] == 0 and cycle["parkedAsExpected"],
        ))

    for cycle in cycles[1:]:
        same_counts = cycle["entryCounts"] == reference["entryCounts"]
        rows.append(px.row(
            f"trace_matches_st_{cycle['rendition'].lower()}",
            f"{cycle['rendition']} walks the same steps the same number of times "
            f"as ST, over one cycle",
            {"reference": reference["entryCounts"], "observed": cycle["entryCounts"],
             "differences": {n: (reference["entryCounts"].get(n), c)
                             for n, c in cycle["entryCounts"].items()
                             if reference["entryCounts"].get(n) != c}},
            0.0, same_counts,
        ))
        rows.append(px.row(
            f"step_set_matches_st_{cycle['rendition'].lower()}",
            f"{cycle['rendition']} entered exactly the steps ST entered",
            {"reference": reference["stepsEntered"], "observed": cycle["stepsEntered"]},
            0.0, cycle["stepsEntered"] == reference["stepsEntered"],
        ))

    for held in helds:
        rows.append(px.row(
            f"held_behaves_identically_{held['rendition'].lower()}",
            f"{held['rendition']}: the door-close hold is BUSY at a LOW named "
            f"reason with no Error, and self-resumes",
            held, held["elapsed_ms"],
            held["heldStep"] == 180
            and held["heldReason"] == demo.REASONS["TWO_HAND_RELEASED"]
            and held["heldSeverity"] == gen.SEVERITY_LOW
            and held["errorWhileHeld"] == 0
            and held["stallReason"] == demo.REASONS["TWO_HAND_RELEASED"]
            and held["selfResumed"],
        ))

    held_reference = helds[0]
    for held in helds[1:]:
        rows.append(px.row(
            f"held_matches_st_{held['rendition'].lower()}",
            f"{held['rendition']} holds at the same step with the same reason "
            f"and severity as ST",
            {"reference": held_reference, "observed": held},
            0.0,
            held["heldStep"] == held_reference["heldStep"]
            and held["heldReason"] == held_reference["heldReason"]
            and held["heldSeverity"] == held_reference["heldSeverity"]
            and held["stallReason"] == held_reference["stallReason"],
        ))

    for abort in aborts:
        rows.append(px.row(
            f"abort_stands_the_chain_down_{abort['rendition'].lower()}",
            f"{abort['rendition']}: an aborted cycle stands down to the init step "
            f"and does not resume by itself",
            abort, abort["elapsed_ms"],
            abort["aborted"] not in (None, 0) and abort["stoodDown"],
        ))
    abort_reference = aborts[0]
    for abort in aborts[1:]:
        rows.append(px.row(
            f"abort_matches_st_{abort['rendition'].lower()}",
            f"{abort['rendition']} stands down exactly as ST does",
            {"reference": abort_reference, "observed": abort},
            0.0,
            abort["stepAfter"] == abort_reference["stepAfter"]
            and abort["runningAfter"] == abort_reference["runningAfter"]
            and abort["errorAfter"] == abort_reference["errorAfter"],
        ))

    successful = sum(1 for r in rows if r["passed"])
    return {
        "suites": 1,
        "tests": len(rows),
        "successful": successful,
        "failed": len(rows) - successful,
        "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
        "declared_task_period_ms": APP.task_period_ms,
        "renditions": renditions,
        "cycles": cycles,
        "held": helds,
        "abort": aborts,
        "passed": successful == len(rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True, type=_normalize_serial)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--settle", type=float, default=4.0)
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute_fixture:
        parser.error("--execute-fixture is required")
    if not 0 < args.settle <= 5:
        parser.error("--settle must be greater than zero and at most five seconds")

    from pylogix import PLC

    evidence: dict[str, Any] = {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "target": args.target, "expected_serial": args.expect_serial,
        "client": "pylogix 1.1.5", "application": APP.name,
        "values_redacted": True,
    }

    with PLC() as comm:
        comm.IPAddress = args.target
        comm.SocketTimeout = args.timeout

        identity = comm.GetModuleProperties(0)
        if not _success(identity):
            evidence["error"] = f"identity read failed: {_status(identity)}"
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1
        device = _value(identity)
        serial = _normalize_serial(getattr(device, "SerialNumber", 0))
        evidence["identity"] = {
            "product_name": getattr(device, "ProductName", ""),
            "revision": getattr(device, "Revision", ""),
            "serial_number": serial,
        }
        evidence["serial_matches"] = serial == args.expect_serial
        if not evidence["serial_matches"]:
            evidence["error"] = "controller serial does not match --expect-serial"
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1

        ready = px.fingerprint(comm)
        evidence["fingerprint"] = ready
        if not ready.get("passed"):
            evidence["error"] = "press-demo fingerprint failed; nothing was written"
            evidence["wrote"] = False
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1

        evidence["wrote"] = True
        evidence["write_surface"] = list(px.WRITABLE)
        try:
            evidence["result"] = run(comm, args.settle)
        finally:
            evidence["disarm"] = px.disarm(comm)

    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values()))
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
