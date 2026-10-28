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

Four things are compared for each rendition:

* the **entry-count vector** over all declared steps, after exactly one cycle;
* the **step set actually entered**, which must be the declared set for the
  path taken;
* the **commands each module ran and completed**, which must be the declared
  ones - entering a step is not the same as moving the plant, and the SFC
  rendition entered N180 and N200 for months without closing the door or
  pressing (found 2026-10-01); and
* the **ordering evidence** the application keeps itself - ``OrderFail`` zero,
  meaning every child module ran before sequence intent on every scan.

The door close's release (TC3's N180) is then exercised in each rendition,
because a language that walks the same steps but abandons differently has not
reproduced the behaviour. So is the dwell's pause (TC3's N220), because each
rendition emits the delay's clock separately and a pause that one of them
counts would press a part short.

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
import fraktal_ab_mailbox as mailbox
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


# px.command's `settle` is the acknowledgement DEADLINE, not a linger: the loop
# returns on the first matching AckSequence, so this costs one round trip and
# only bounds how long a lost command is allowed to look like a slow one. A
# zero window can never observe an ack and fails every command by construction.
ACK_WINDOW = 1.0


def ack(settle: float) -> float:
    return min(settle, ACK_WINDOW)


def select(comm: Any, rendition: str) -> bool:
    # A chain carried in one language has no selector: that one always runs.
    if not AUTO.multi_rendition:
        return True
    return px.write(comm, RENDITION, gen.rendition_ordinal(rendition))


def reset_chart(comm: Any, settle: float) -> None:
    """Zero the marks so each rendition's cycle is counted from the same start.

    Through the mailbox, not by writing the request tags. Those became
    ExternalAccess None when AB 11.2.1 was closed on 2026-09-23, so the direct
    writes this used to make are refused by px.write's own guard - the guard
    working, not a fault. The mailbox lowers a one-shot itself, so the
    raise/lower pair written by hand here is gone with it.
    """
    px.command(comm, mailbox.STOP, settle=ack(settle))
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack(settle))


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


COMMANDED = sorted({s.module for s in AUTO.steps if s.module})


def declared_commands(counts: dict[int, int]) -> dict[str, int]:
    """The commands the declaration issues for the steps a cycle entered."""
    by = {s.number: s for s in AUTO.steps}
    out = {name: 0 for name in COMMANDED}
    for number, entered in counts.items():
        step = by.get(number)
        if step is not None and step.module and step.command:
            out[step.module] += entered
    return out


def module_counters(comm: Any) -> dict[str, tuple[int, int]]:
    out = {}
    for name in COMMANDED:
        ctx = px.read_module(comm, name)
        out[name] = (None, None) if ctx is None else (ctx["RunCount"], ctx["DoneCount"])
    return out


def walk_one_cycle(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Run exactly one AUTO cycle in one rendition and return its trace."""
    px.command(comm, mailbox.SET_MODE, settle=ack(settle), IntValue=px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    for name in px.FAULT:
        px.write(comm, px.FAULT[name], 0)
    select(comm, rendition)
    reset_chart(comm, settle)

    before = px.read_unit(comm)
    # The marks are cumulative and nothing clears them, so a rendition's trace
    # is the delta over its own window. So are the modules' command counters.
    chart_before = px.read_chart(comm)
    counters_before = module_counters(comm)
    # START, then a fresh two-hand press: N100 waits on TC3's latched start.
    # t0 is after the press, which is when the cycle can begin.
    px.start_cycle(comm, settle)
    started = time.monotonic()
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
    px.command(comm, mailbox.STOP, settle=ack(settle))
    px.write(comm, px.PART_PRESENT, 1)

    chart = px.read_chart(comm)
    order_fail = px.read_scalar(comm, px.ORDER_FAIL)
    after = entry_vector(chart) if chart else {}
    baseline = entry_vector(chart_before) if chart_before else {}
    counts = {n: after.get(n, 0) - baseline.get(n, 0) for n in after}
    counters_after = module_counters(comm)
    commands = {name: {"run": counters_after[name][0] - counters_before[name][0],
                       "done": counters_after[name][1] - counters_before[name][1]}
                if None not in counters_after[name] + counters_before[name] else None
                for name in COMMANDED}

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
        "commands": commands,
        "declaredCommands": declared_commands(counts),
    }


CLOSE = next(s for s in AUTO.steps if s.action == decl.GUARDED)
REOPEN = next(s for s in AUTO.steps if s.number == CLOSE.on_jump)
RECOVERY = (CLOSE.number, REOPEN.number, REOPEN.on_advance, CLOSE.on_advance)


def walk_abandon(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Release the two-hand at the door close in one rendition: TC3's N180.

    The close is abandoned with one LOW warning and no fault, the door
    reopens, the part slides out, and the chain waits at the start step for a
    fresh press - the latch dropped, so it does not start again by itself.
    """
    px.command(comm, mailbox.SET_MODE, settle=ack(settle), IntValue=px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    select(comm, rendition)
    reset_chart(comm, settle)
    before = px.read_unit(comm)
    chart_before = px.read_chart(comm)
    px.start_cycle(comm, settle)
    # Released during the declared settle rather than racing the four-scan
    # close: the close then starts with the buttons already released.
    px.await_unit(comm, lambda u: u["Step"] == 170, settle)
    px.write(comm, px.TWO_HAND, 0)
    back, elapsed = px.await_unit(
        comm, lambda u: before is not None and u["Step"] == PARK_STEP
        and u["ReportedCount"] > before["ReportedCount"], settle)
    time.sleep(min(settle, 0.25))            # it must stay there by itself
    unit = px.read_unit(comm)
    chart = px.read_chart(comm)
    px.command(comm, mailbox.STOP, settle=ack(settle))
    entered = ({n: chart["EnterCount"][AUTO_INDEXES[n]]
                - chart_before["EnterCount"][AUTO_INDEXES[n]] for n in RECOVERY}
               if chart and chart_before else {})
    return {
        "rendition": rendition,
        "elapsed_ms": round(elapsed, 3),
        "reportedReason": None if unit is None else unit["ReportedReason"],
        "reportedSource": None if unit is None else unit["ReportedSource"],
        "reports": (None if unit is None or before is None
                    else unit["ReportedCount"] - before["ReportedCount"]),
        "rowWarning": None if chart is None else chart["WarnReason"][AUTO_INDEXES[CLOSE.number]],
        "error": None if unit is None else unit["Error"],
        "startLatched": None if unit is None else unit["StartLatched"],
        "restingAt": None if unit is None else unit["Step"],
        "entered": entered,
    }


DWELL = next(s for s in AUTO.steps if s.action == decl.DELAY and s.conditions)
# Long enough that a dwell still counting would have finished several times
# over while released.
DWELL_PAUSE_S = 1.5


def walk_dwell(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Release the two-hand inside the dwell in one rendition: TC3's N220.

    The dwell must stand still on its named condition, with no fault and no
    hold, and pressing again must finish only the time that remained. What
    proves the second half is the delay's own clock after the step: the full
    dwell, not the dwell plus the pause.
    """
    cfg = px.read_layout(comm, px.CFG, APP.records[0].members) or {}
    dwell_ms = cfg.get(DWELL.duration_member)
    px.command(comm, mailbox.SET_MODE, settle=ack(settle), IntValue=px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    select(comm, rendition)
    reset_chart(comm, settle)
    px.start_cycle(comm, settle)
    # Release once the dwell has begun. The stroke before it now needs the
    # buttons too - TC3's ram permit, pressRequiresTwoHandHeld - so a release
    # during N200 holds the ram instead, which is the permit's own row.
    px.await_chart(comm, lambda c: c["ActiveStepNumber"] == DWELL.number, settle)
    px.write(comm, px.TWO_HAND, 0)
    paused, elapsed = px.await_chart(
        comm, lambda c: c["ActiveStepNumber"] == DWELL.number
        and c["StallReason"] == demo.REASONS["WAIT_CONDITION"], settle)
    time.sleep(DWELL_PAUSE_S)
    still = px.read_chart(comm)
    unit = px.read_unit(comm)
    px.write(comm, px.TWO_HAND, 1)
    resumed, _ = px.await_unit(comm, lambda u: u["Step"] != DWELL.number, settle)
    after = px.read_chart(comm)
    px.command(comm, mailbox.STOP, settle=ack(settle))
    index = AUTO_INDEXES[DWELL.number]
    ran = None if paused is None else paused["DelayMs"]
    served = None if after is None else after["DelayMs"]
    return {
        "rendition": rendition,
        "elapsed_ms": round(elapsed, 3),
        "dwellMs": dwell_ms,
        "pausedAtMs": ran,
        "stillAtMs": None if still is None else still["DelayMs"],
        "pausedStep": None if still is None else still["ActiveStepNumber"],
        "condOk": None if still is None else still["CondOk"][0],
        "stallReason": None if still is None else still["StallReason"],
        "errorWhilePaused": None if unit is None else unit["Error"],
        # TC3 times the step against its ExpectedTime, the dwell: a release
        # that outlasts it is reported stalled - a pending LOW, not a fault.
        "timedOutWhilePaused": None if unit is None else unit["StepTimedOut"],
        "diagWhilePaused": None if unit is None else unit["DiagReason"],
        "resumedTo": None if resumed is None else resumed["Step"],
        "servedMs": served,
        "stepMs": None if after is None else after["LastMs"][index],
        "paused": bool(still and paused and still["DelayMs"] == ran
                       and dwell_ms is not None and ran < dwell_ms),
        "servedTheDwell": bool(served is not None and dwell_ms is not None
                               and dwell_ms <= served < dwell_ms + APP.task_period_ms),
    }


def walk_abort(comm: Any, rendition: str, settle: float) -> dict[str, Any]:
    """Abort a running cycle in one rendition and require it to stay down."""
    px.command(comm, mailbox.SET_MODE, settle=ack(settle), IntValue=px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.TWO_HAND, 0)
    select(comm, rendition)
    reset_chart(comm, settle)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == AFTER_PARK, settle)
    # STOP is the abort path here: one accepted command raises AbortRequest and
    # lowers RunRequest together, deliberately, so a latched Aborted is never
    # fighting a run level that is still trying to set Running. The mailbox
    # lowers its own one-shot, so the raise/lower pair written by hand here is
    # gone with it - and so is the separate stop that used to follow.
    #
    # What that costs, stated rather than hidden: the hand-written form held
    # AbortRequest up while RunRequest stayed high, which tested the latch under
    # pressure. That shape is not reachable through the permitted surface. The
    # no-self-resume property is still tested, by stoodDown below: after the
    # abort and a settle with no further input, Running is 0 and the chain sits
    # on its init step.
    px.command(comm, mailbox.STOP, settle=ack(settle))
    aborted, elapsed = px.await_unit(comm, lambda u: u["Aborted"] != 0, settle)
    time.sleep(min(settle, 0.25))
    after = px.read_unit(comm)
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
    abandons = [walk_abandon(comm, r, settle) for r in renditions]
    dwells = [walk_dwell(comm, r, settle) for r in renditions]

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
        rows.append(px.row(
            f"commands_complete_{cycle['rendition'].lower()}",
            f"the {cycle['rendition']} rendition runs and completes every command "
            f"its entered steps declare, module by module - the plant moves",
            {"observed": cycle["commands"], "declared": cycle["declaredCommands"]},
            0.0,
            cycle["commands"] == {name: {"run": n, "done": n}
                                  for name, n in cycle["declaredCommands"].items()},
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

    for abandon in abandons:
        rows.append(px.row(
            f"release_abandons_the_close_{abandon['rendition'].lower()}",
            f"{abandon['rendition']}: a two-hand release at the door close is one "
            f"LOW warning and no fault; the door reopens, the part slides out, "
            f"and the chain waits at the start with the latch dropped",
            abandon, abandon["elapsed_ms"],
            abandon["reportedReason"] == demo.REASONS["TWO_HAND_RELEASED"]
            and abandon["reportedSource"] == 0
            and abandon["reports"] == 1
            and abandon["rowWarning"] == demo.REASONS["TWO_HAND_RELEASED"]
            and abandon["error"] == 0
            and abandon["startLatched"] == 0
            and abandon["restingAt"] == PARK_STEP
            and abandon["entered"] == {CLOSE.number: 1, REOPEN.number: 1,
                                       REOPEN.on_advance: 1, CLOSE.on_advance: 0},
        ))

    abandon_reference = abandons[0]
    for abandon in abandons[1:]:
        rows.append(px.row(
            f"abandon_matches_st_{abandon['rendition'].lower()}",
            f"{abandon['rendition']} abandons the close exactly as ST does",
            {"reference": abandon_reference, "observed": abandon},
            0.0,
            all(abandon[k] == abandon_reference[k] for k in (
                "reportedReason", "reportedSource", "reports", "rowWarning",
                "error", "startLatched", "restingAt", "entered")),
        ))

    for dwell in dwells:
        rows.append(px.row(
            f"dwell_pauses_{dwell['rendition'].lower()}",
            f"{dwell['rendition']}: releasing the two-hand in the dwell pauses it "
            f"on its named condition, with no fault; past the dwell's expected "
            f"time it is reported stalled, and pressing again finishes only the "
            f"time that remained",
            dwell, dwell["elapsed_ms"],
            dwell["paused"]
            and dwell["pausedStep"] == DWELL.number
            and dwell["condOk"] == 0
            and dwell["stallReason"] == demo.REASONS["WAIT_CONDITION"]
            and dwell["errorWhilePaused"] == 0
            and dwell["timedOutWhilePaused"] == 1
            and dwell["diagWhilePaused"] == demo.REASONS["STEP_STALLED"]
            and dwell["resumedTo"] not in (None, DWELL.number)
            and dwell["servedTheDwell"]
            and dwell["stepMs"] is not None
            and dwell["stepMs"] >= DWELL_PAUSE_S * 1000,
        ))
    dwell_reference = dwells[0]
    for dwell in dwells[1:]:
        rows.append(px.row(
            f"dwell_matches_st_{dwell['rendition'].lower()}",
            f"{dwell['rendition']} pauses the dwell on the same condition and "
            f"serves the same dwell as ST",
            {"reference": dwell_reference, "observed": dwell},
            0.0,
            dwell["pausedStep"] == dwell_reference["pausedStep"]
            and dwell["stallReason"] == dwell_reference["stallReason"]
            and dwell["condOk"] == dwell_reference["condOk"]
            and dwell["servedMs"] == dwell_reference["servedMs"],
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
        "abandon": abandons,
        "dwell": dwells,
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
        # Start above whatever this controller has already answered. The
        # handler dispatches on Sequence CHANGING, not on it increasing, so a
        # harness restarting at 1 is ignored - silently, with no ack - for
        # exactly as long as it takes to walk past the retained value.
        evidence["sequence_seed"] = px.seed_sequence(comm)
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
