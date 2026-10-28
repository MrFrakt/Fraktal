#!/usr/bin/env python3
"""Phase 5a on the controller: TC3's run styles (Core §3.4.2).

What the model proved and the controller has to show, in every rendition:

* the Unit publishes the styles it offers and the one it runs, where the
  HMI's step toggle reads them;
* a style outside E_RunStyle is refused by TC3's own key, and a Step outside
  a running SINGLE_STEP is refused by name;
* SINGLE_STEP issues nothing until asked and exactly one command per Step
  request, over a whole AUTO cycle - proved by what the plant did (module
  command counts), the lesson of D7, not by the steps the chain entered;
* HOLD_TO_RUN issues nothing until held; letting go mid-motion lets the motion
  finish and stops at the next command; held again, the cycle completes;
* a stop ends a hold, so a hold whose release never arrived cannot run the
  next START unheld (the binding's stricter reading of TC3's rule).

Pacing is NON-SAFETY: the modules' interlocks decide whether anything moves
in every style, and nothing here is a dead-man.

Phase 5c adds TC3's OEE (Core §8.5.1), timed against the wall clock rather
than against the formula, which the projection owns and the model tests:

* RESET_OEE clears the buckets and the trend, and leaves the part counts;
* run time is the time the press runs, and down time the time it is faulted;
* a sample lands one minute after the reset, holding what the accounting
  held then, and the next reset retires it.

Phase 5d adds TC3's MachineState (Core §8.11.3), derived by the gateway from
what the Unit publishes, walked through every state the bench can reach, and
the ReworkCount the controller now counts (§8.11.2).

Phase 5e adds TC3's cycle-time profile (§8.11.4(b)/(f)): one cycle after a
START is profiled step by step - its waterfall, its delays against what they
expected, its wait split from its work - and a cycle stopped part-way is never
published.

Phase 5f adds TC3's command timing (§8.11.4(a)) - every command a module runs,
including one that finds the module already where it was sent, which TC3 itself
never times - and the degradation watch (d): a WORK time past its baseline is
one maintenance event per excursion, never downtime. The row that proves the
watch writes the running model's baseline and always writes it back.

Phase 5g adds TC3's derived state flags (§3.12): at load position, and ready
for a two-hand start - each true right now, never latched, stamped when it
changes.

Phase 5h adds TC3's system-health publisher (§8.12) over S3's subset: the
facet as the HMI reads it, and the one condition this controller always has -
its CPU and memory cannot be read - as a single standing LOW event that never
blocks a start.
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
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection

SCHEMA = "fraktal.ab.phase5-run-styles-on-controller"
SCHEMA_VERSION = 1

APP = px.APP
ROOT = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
COMMANDING = {s.number for s in AUTO.steps
              if s.action in (decl.ISSUE, decl.GUARDED, decl.ADOPT, decl.REPORT)}
# The happy path's commands, one per stop point (test_fraktal_ab_rendition_cycle).
PATH = (110, 130, 150, 180, 200, 240, 242, 244)
DECLARED = len(PATH)
SLIDE_IN = 150                       # a real motion: the slide starts outside
DOOR_CLOSE = 180                     # the next stop point after it


def key(portable: str) -> int:
    return manifest.numeric_key(APP, portable)


def issued(comm: Any) -> int | None:
    counters = parity.module_counters(comm)
    if any(None in pair for pair in counters.values()):
        return None
    return sum(run for run, _ in counters.values())


def at_stop_point(unit: dict[str, int]) -> bool:
    return unit["Step"] in COMMANDING and unit["Issued"] == 0


def begin(comm: Any, rendition: str, style: int, ack: float, settle: float) -> dict:
    """AUTO in one rendition and style, the press home, a cycle started.

    HOME runs first, and CONTINUOUS (px.home idles, which resets the style).
    Once the chain is past its start step the part is withdrawn, as the parity
    harness does, so the loop parks there instead of starting another cycle;
    nothing after the start step reads it."""
    px.home(comm, settle)
    px._idle(comm, ack)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    parity.select(comm, rendition)
    chosen = px.command(comm, mailbox.SET_RUN_STYLE, settle=ack, IntValue=style)
    started = px.start_cycle(comm, settle)
    past, _ = px.await_unit(comm, lambda u: u["Step"] == parity.AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    return {"style": chosen, "start": started,
            "pastStart": past is not None and past["Step"] == parity.AFTER_PARK}


def finish(comm: Any, ack: float, settle: float) -> dict[str, int] | None:
    """Let the loop close and park at the start step, then stop."""
    parked, _ = px.await_unit(comm, lambda u: u["Step"] == parity.PARK_STEP, settle)
    px.command(comm, mailbox.STOP, settle=ack)
    return parked


def stepped_cycle(comm: Any, rendition: str, ack: float, settle: float,
                  idle: float = 0.4) -> dict[str, Any]:
    """SINGLE_STEP: at every stop point wait `idle` seconds, require that
    nothing issued, then give one Step. Each request must issue exactly one
    command, and the cycle must close."""
    opened = begin(comm, rendition, decl.RUN_SINGLE_STEP, ack, settle)
    before = px.read_unit(comm)
    first = issued(comm)
    per_request, refusals, started = [], [], time.monotonic()
    while len(per_request) <= DECLARED:
        unit, _ = px.await_unit(comm, lambda u: at_stop_point(u) or (
            before is not None and u["CycleCount"] > before["CycleCount"]), settle)
        if unit is None or (before is not None and unit["CycleCount"] > before["CycleCount"]):
            break
        time.sleep(idle)
        now = issued(comm)
        per_request.append(None if None in (now, first) else now - first)
        first = now
        answer = px.command(comm, mailbox.STEP_REQUEST, settle=ack)
        if not answer["accepted"]:
            refusals.append({"step": unit["Step"], "answer": answer})
            break
        # Consumed by the issue, and it stays consumed: a level, so a poll
        # cannot miss it. Issued is not - a command that completes at once
        # (the ram already up) holds it for two scans, under one CIP read.
        px.await_unit(comm, lambda u: u["StepPending"] == 0, settle)
    closed, _ = px.await_unit(
        comm, lambda u: before is not None and u["CycleCount"] > before["CycleCount"],
        settle)
    last = issued(comm)
    per_request.append(None if None in (last, first) else last - first)
    parked = finish(comm, ack, settle)
    return {"rendition": rendition, "opened": opened, "perRequest": per_request,
            "refusals": refusals,
            "cycleClosed": bool(closed and before
                                and closed["CycleCount"] > before["CycleCount"]),
            "parkedAt": None if parked is None else parked["Step"],
            "elapsed_ms": round((time.monotonic() - started) * 1000.0, 3)}


def held_cycle(comm: Any, rendition: str, ack: float, settle: float) -> dict[str, Any]:
    """HOLD_TO_RUN: nothing unheld; held to the slide's motion, released
    there, the slide arrives and the door is not commanded; held again, the
    cycle completes."""
    opened = begin(comm, rendition, decl.RUN_HOLD_TO_RUN, ack, settle)
    before = px.read_unit(comm)
    start_count = issued(comm)
    time.sleep(0.6)
    unheld = px.read_unit(comm)
    unheld_issued = issued(comm)
    # Keep the declared simulated motion in progress while the guarded mailbox
    # stages its arguments. Otherwise a slow client can release after the slide
    # and door have already completed, testing transport latency rather than
    # HOLD_TO_RUN. Removing this recoverable hold resumes the existing command.
    if not px.write(comm, px.HOLD["PartSlide"], 1):
        raise AssertionError("could not hold the fixture slide motion")
    try:
        hold = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=1)
        px.await_unit(comm, lambda u: u["Step"] == SLIDE_IN and u["Issued"] != 0, settle)
        motion, _ = px.await_module(comm, "PartSlide", lambda m: m["Busy"] != 0
                                    and m["OutImm_Held"] != 0, settle)
        release = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=0)
    finally:
        if not px.write(comm, px.HOLD["PartSlide"], 0):
            raise AssertionError("could not restore the fixture slide hold")
    stopped, _ = px.await_unit(comm, lambda u: u["Step"] == DOOR_CLOSE, settle)
    time.sleep(0.6)
    waiting = px.read_unit(comm)
    slide = px.read_module(comm, "PartSlide")
    at_release = issued(comm)
    again = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=1)
    closed, _ = px.await_unit(
        comm, lambda u: before is not None and u["CycleCount"] > before["CycleCount"],
        settle)
    total = issued(comm)
    px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=0)
    parked = finish(comm, ack, settle)
    delta = (lambda a, b: None if None in (a, b) else a - b)
    return {
        "rendition": rendition, "opened": opened,
        "unheld": None if unheld is None else {k: unheld[k] for k in ("Step", "Issued")},
        "issuedUnheld": delta(unheld_issued, start_count),
        "answers": {"hold": hold, "release": release, "again": again},
        "motionAtRelease": None if motion is None else {k: motion[k] for k in ("Busy", "OutImm_Held")},
        "releasedAt": None if waiting is None else {k: waiting[k] for k in (
            "Step", "Issued", "HoldRun")},
        "slideArrived": None if slide is None else slide["OutImm_Extended"],
        "issuedBeforeRelease": delta(at_release, start_count),
        "issuedInCycle": delta(total, start_count),
        "cycleClosed": bool(closed and before
                            and closed["CycleCount"] > before["CycleCount"]),
        "parkedAt": None if parked is None else parked["Step"],
        "reachedDoorClose": stopped is not None and stopped["Step"] == DOOR_CLOSE,
    }


def oee_card(comm: Any) -> dict[str, Any]:
    """The OEE card as the gateway publishes it, Unit-relative."""
    values = projection.read_document(comm)["values"]
    prefix = f"{ROOT}/"
    return {k[len(prefix):]: v for k, v in values.items()
            if k.startswith(f"{prefix}Oee")}


def oee_raw(comm: Any) -> dict[str, Any] | None:
    return px.read_layout(comm, gen.oee_tag(APP), gen.oee_members())


def timed_oee_card(comm: Any) -> tuple[dict[str, Any], tuple[float, float]]:
    """Bracket acquisition, then use the owning projection for the card."""
    started = time.monotonic()
    raw = oee_raw(comm)
    finished = time.monotonic()
    return (projection.oee_status(APP, raw, px.read_unit(comm), projection.read_records(comm)),
            (started, finished))


def down_time_row(comm: Any, faulted: dict[str, Any] | None):
    first, first_window = timed_oee_card(comm)
    time.sleep(1.0)
    second, second_window = timed_oee_card(comm)
    # Each native sample was acquired somewhere inside its read window.
    # Include transport/mapping time between samples, with the same 250 ms
    # allowance as the run-time check; a one-second sleep is not their interval.
    bounds = ((second_window[0] - first_window[1]) * 1000,
              (second_window[1] - first_window[0]) * 1000)
    grew = {k: (second.get(k) or 0) - (first.get(k) or 0)
            for k in ("Oee/RunMs", "Oee/DownMs", "Oee/IdleMs")}
    run, down = second.get("Oee/RunMs") or 0, second.get("Oee/DownMs") or 0
    return px.row(
        "down_time_is_the_time_it_is_faulted",
        "the slide sticks: DownMs matches the measured native sample interval "
        "within 250 ms; run and idle do not grow; A = run / (run + down)",
        {"grew": grew, "sampleIntervalMs": [round(n, 3) for n in bounds],
         "availability": second.get("Oee/Availability"),
         "faulted": None if faulted is None else faulted["Error"]},
        (bounds[0] + bounds[1]) / 2,
        faulted is not None and faulted["Error"] == 1
        and bounds[0] - 250 <= grew["Oee/DownMs"] <= bounds[1] + 250
        and grew["Oee/RunMs"] == 0 and grew["Oee/IdleMs"] == 0
        and run + down > 0
        and abs(second.get("Oee/Availability", -1) - run / (run + down)) < 1e-6,
    ), second


def oee_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # HOME is BUSY time too, so the reset comes after it, right before START.
    px.home(comm, settle)
    px._idle(comm, ack)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    parity.select(comm, decl.ST)
    before = oee_raw(comm)
    unit = px.read_unit(comm)
    good_at_reset = None if unit is None else unit["GoodCount"]
    reset = px.command(comm, mailbox.RESET_OEE, settle=ack)
    reset_at = time.monotonic()
    card = oee_card(comm)
    after = oee_raw(comm)
    rows.append(px.row(
        "reset_oee_clears_the_accounting",
        "RESET_OEE is accepted: run and down zero, the ring empty, the epoch "
        "moved, and nothing valid yet (no run, no parts since)",
        {"answer": reset, "card": {k: card.get(k) for k in (
            "Oee/RunMs", "Oee/DownMs", "OeeTrendHead", "Oee/AvailValid",
            "Oee/PerfValid", "Oee/QualValid", "Oee/OeeValid")},
         "epoch": None if None in (before, after) else (before["Epoch"], after["Epoch"])},
        0.0,
        reset["accepted"] and card.get("Oee/RunMs") == 0 and card.get("Oee/DownMs") == 0
        and card.get("OeeTrendHead") == 0 and card.get("Oee/OeeValid") is False
        and before is not None and after is not None
        and after["Epoch"] == before["Epoch"] + 1,
    ))

    # --- run time is the time the press runs ------------------------------------------
    px.start_cycle(comm, settle)
    # Argument staging is before START takes effect. Measure acknowledged
    # command boundaries, keeping the existing 250 ms allowance for read/ack
    # latency, rather than counting guarded setup as controller running time.
    started = time.monotonic()
    px.await_unit(comm, lambda u: u["Step"] == parity.AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    base = px.read_unit(comm)
    closed, _ = px.await_unit(comm, lambda u: base is not None
                              and u["CycleCount"] > base["CycleCount"], settle)
    time.sleep(0.5)
    px.command(comm, mailbox.STOP, settle=ack)
    stopped = time.monotonic()
    px.await_unit(comm, lambda u: u["Running"] == 0, settle)
    card = oee_card(comm)
    unit = px.read_unit(comm)
    wall_ms = (stopped - started) * 1000.0
    parts = None if None in (unit, good_at_reset) else unit["GoodCount"] - good_at_reset
    run_ms = card.get("Oee/RunMs") or 0
    rows.append(px.row(
        "run_time_is_the_time_the_press_runs",
        "one cycle and a wait at the start step: RunMs within 250 ms of the wall "
        "time from START acknowledgement to STOP acknowledgement, no down time, "
        "A and Q 1.0, and P = ideal x "
        "parts / run",
        {"wallMs": round(wall_ms, 1), "parts": parts, "card": {k: card.get(k) for k in (
            "Oee/RunMs", "Oee/DownMs", "Oee/Availability", "Oee/Performance",
            "Oee/Quality", "Oee/Oee", "Oee/PerfValid")}},
        wall_ms,
        bool(closed) and run_ms > 0 and abs(run_ms - wall_ms) <= 250
        and card.get("Oee/DownMs") == 0
        and card.get("Oee/Availability") == 1.0 and card.get("Oee/Quality") == 1.0
        and parts == 1 and card.get("Oee/PerfValid") is True
        and abs(card.get("Oee/Performance", 0) - min(1.0, 950 * parts / run_ms)) < 1e-6,
    ))

    # --- down time is the time it is faulted ------------------------------------------
    px.home(comm, settle)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.write(comm, px.FAULT["PartSlide"], 1)
    px.start_cycle(comm, settle)
    faulted, _ = px.await_unit(comm, lambda u: u["Error"] != 0, settle)
    down_row, second = down_time_row(comm, faulted)
    px.write(comm, px.FAULT["PartSlide"], 0)
    px._idle(comm, ack)
    run2, down2 = second.get("Oee/RunMs") or 0, second.get("Oee/DownMs") or 0
    rows.append(down_row)

    # --- a sample a minute after the reset ----------------------------------------------
    deadline = reset_at + gen.OEE_SAMPLE_MS / 1000.0 + 5.0
    raw = oee_raw(comm)
    while raw is not None and raw["Head"] == 0 and time.monotonic() < deadline:
        time.sleep(0.05)
        raw = oee_raw(comm)
    sampled_after = time.monotonic() - reset_at
    card = oee_card(comm)
    unit = px.read_unit(comm)
    slot = {c: raw[f"Smp{c}"][0] for c, _ in gen.OEE_SAMPLE_COLUMNS} if raw else {}
    rows.append(px.row(
        "a_sample_a_minute_after_the_reset",
        "the first sample lands 60 s after the reset (within a second), in the "
        "current epoch, holding the part made since and the model's ideal cycle, "
        "and the card shows it",
        {"afterS": round(sampled_after, 3), "slot": slot,
         "head": card.get("OeeTrendHead"), "valid": card.get("OeeTrend[1]/OeeValid"),
         "oee": card.get("OeeTrend[1]/Oee")},
        sampled_after * 1000.0,
        raw is not None and raw["Head"] == 1
        and abs(sampled_after - gen.OEE_SAMPLE_MS / 1000.0) <= 1.0
        and slot.get("Epoch") == raw["Epoch"]
        and slot.get("RunS", 0) * 1000 + slot.get("RunMs", 0) == run2
        and slot.get("Good") == parts and slot.get("IdealMs") == 950
        and card.get("OeeTrendHead") == 1 and card.get("OeeTrend[1]/OeeValid") is True,
    ))

    # --- a reset retires the trend and keeps the counts ----------------------------------
    good_before = None if unit is None else unit["GoodCount"]
    again = px.command(comm, mailbox.RESET_OEE, settle=ack)
    card = oee_card(comm)
    unit = px.read_unit(comm)
    rows.append(px.row(
        "a_reset_retires_the_trend_and_keeps_the_counts",
        "RESET_OEE again: the ring is empty and its sample no longer valid; "
        "GoodCount is untouched, since counts reset only on their own logged "
        "action (Core §8.11.2)",
        {"answer": again, "head": card.get("OeeTrendHead"),
         "valid": card.get("OeeTrend[1]/OeeValid"),
         "good": (good_before, None if unit is None else unit["GoodCount"])},
        0.0,
        again["accepted"] and card.get("OeeTrendHead") == 0
        and card.get("OeeTrend[1]/OeeValid") is False
        and unit is not None and unit["GoodCount"] == good_before,
    ))
    return rows


def machine_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    states = {v: k for k, v in projection.MACHINE_STATES.items()}

    def published() -> tuple[Any, Any]:
        values = projection.read_document(comm)["values"]
        return values.get(f"{ROOT}/MachineState"), values.get(f"{ROOT}/ReworkCount")

    seen: list[tuple[str, Any]] = []
    px.home(comm, settle)
    px._idle(comm, ack)
    seen.append(("stopped and reset", published()[0]))
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=demo.MODE_CHANGEOVER)
    px.await_unit(comm, lambda u: u["Mode"] == demo.MODE_CHANGEOVER, settle)
    seen.append(("CHANGEOVER selected", published()[0]))
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    parity.select(comm, decl.ST)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Running"] != 0, settle)
    seen.append(("AUTO running", published()[0]))
    px.command(comm, mailbox.STOP, settle=ack)
    px.await_unit(comm, lambda u: u["Aborted"] != 0, settle)
    seen.append(("after STOP", published()[0]))
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    px.await_unit(comm, lambda u: u["Aborted"] == 0, settle)
    seen.append(("after the reset", published()[0]))
    px.home(comm, settle)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.write(comm, px.FAULT["PartSlide"], 1)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Error"] != 0, settle)
    seen.append(("the slide stuck", published()[0]))
    px.write(comm, px.FAULT["PartSlide"], 0)
    px._idle(comm, ack)
    seen.append(("recovered", published()[0]))
    expected = ["IDLE", "CHANGEOVER", "PRODUCING", "STOPPED", "IDLE", "DOWN", "IDLE"]
    named = [(what, states.get(value, value)) for what, value in seen]
    rows = [px.row(
        "machine_state_follows_the_unit",
        "TC3's classification, read where the HMI reads it: IDLE, CHANGEOVER "
        "selected, PRODUCING while running, STOPPED after STOP, IDLE after the "
        "reset, DOWN while faulted, IDLE once recovered",
        named, 0.0,
        [state for _, state in named] == expected,
    )]
    rework, unit = published()[1], px.read_unit(comm)
    rows.append(px.row(
        "rework_count_is_the_controllers",
        "ReworkCount is published from the Unit's own counter; the press "
        "declares no rework verdict, so both read 0",
        {"published": rework, "controller": None if unit is None else unit["ReworkCount"]},
        0.0,
        unit is not None and rework == unit["ReworkCount"] == 0,
    ))
    return rows


# A START's first cycle, as the model runs it in every rendition: the chain's
# init step, the operator's start, then the happy path to the finish step.
PROFILED = (0, 100, 110, 130, 150, 170, 180, 200, 220, 230, 240, 242, 244, 999)


def profile_raw(comm: Any) -> dict[str, Any] | None:
    return px.read_layout(comm, gen.profiler_tag(APP), gen.profiler_members(APP))


def profiler_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    px.home(comm, settle)
    px._idle(comm, ack)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    parity.select(comm, decl.ST)
    before = profile_raw(comm)
    cfg = px.read_flat(comm, px.CFG, tuple(m.name for m in APP.records[0].members))
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == parity.AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    unit0 = px.read_unit(comm)
    px.await_unit(comm, lambda u: unit0 is not None
                  and u["CycleCount"] > unit0["CycleCount"], settle)
    time.sleep(0.2)
    px.command(comm, mailbox.STOP, settle=ack)
    raw = profile_raw(comm)
    values = projection.read_document(comm)["values"]
    base = f"{ROOT}/Profiler/LastCycle"
    count = values.get(f"{base}/NSteps") or 0
    steps = [{leaf: values.get(f"{base}/Steps[{i}]/{leaf}") for leaf in (
        "StepNo", "StepName", "TimeClass", "Duration", "Expected")}
        for i in range(1, count + 1)]
    numbers = [s["StepNo"] for s in steps]
    by_no = {s["StepNo"]: s for s in steps}
    total = values.get(f"{base}/Total")
    head = values.get(f"{ROOT}/Profiler/HistoryHead") or 0
    trend = {leaf: values.get(f"{ROOT}/Profiler/History[{head}]/{leaf}")
             for leaf in ("CycleNo", "Total", "WorkTime", "WaitTime")}
    split = [values.get(f"{ROOT}/Profiler/History[{head}]/ByClass[{k}]")
             for k in range(len(decl.TIME_CLASSES))]
    row110 = gen.ordered_steps(APP).index(110)
    rows.append(px.row(
        "a_cycle_is_profiled_step_by_step",
        "one cycle after a START, read where the HMI reads it: the init step, "
        "the operator's start and the happy path in order; the total is its "
        "steps and the trend's; the two delays expected their recipe values "
        "and took one scan more; N100 is the only wait; N110 counted once more",
        {"numbers": numbers, "total": total,
         "work": values.get(f"{base}/WorkTime"), "wait": values.get(f"{base}/WaitTime"),
         "delays": {n: by_no.get(n) for n in (170, 220)}, "trend": trend, "split": split,
         "cycleNo": (None if before is None else before["LastCycleNo"],
                     values.get(f"{base}/CycleNo")),
         "n110": (None if before is None else before["StatCount"][row110],
                  None if raw is None else raw["StatCount"][row110])},
        0.0,
        before is not None and raw is not None and cfg is not None
        and tuple(numbers) == PROFILED
        and values.get(f"{base}/CycleNo") == before["LastCycleNo"] + 1
        and all(s["Duration"] > 0 and s["Duration"] % APP.task_period_ms == 0 for s in steps)
        and sum(s["Duration"] for s in steps) == total
        and values.get(f"{ROOT}/Profiler/LastCycleTime") == total
        and by_no[170]["Expected"] == cfg["TransferSettleMs"]
        and by_no[220]["Expected"] == cfg["PressDwellMs"]
        and by_no[170]["Duration"] == cfg["TransferSettleMs"] + APP.task_period_ms
        and by_no[220]["Duration"] == cfg["PressDwellMs"] + APP.task_period_ms
        and by_no[100]["StepName"] == "project.step.awaitTwoHandStart"
        and values.get(f"{base}/WaitTime") == by_no[100]["Duration"]
        and trend["CycleNo"] == values.get(f"{base}/CycleNo") and trend["Total"] == total
        and sum(split) == total
        and split[decl.TIME_CLASSES.index("WAIT_OPERATOR")] == by_no[100]["Duration"]
        and raw["StatCount"][row110] == before["StatCount"][row110] + 1,
    ))

    # --- a cycle stopped part-way is not a cycle ----------------------------------------
    px.home(comm, settle)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    before = profile_raw(comm)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == 150, settle)
    px.command(comm, mailbox.STOP, settle=ack)
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    after = profile_raw(comm)
    rows.append(px.row(
        "a_cycle_stopped_part_way_is_not_published",
        "STOP inside a cycle: the last cycle, its time and the trend are as they "
        "were (TC3's CycleAbandon), and the cycle is closed, not left open",
        None if None in (before, after) else {
            k: (before[k], after[k]) for k in (
                "LastCycleNo", "LastCycleTime", "HistoryHead", "CycleOpen", "Open")},
        0.0,
        before is not None and after is not None
        and all(after[k] == before[k] for k in ("LastCycleNo", "LastCycleTime", "HistoryHead"))
        and after["CycleOpen"] == 0 and after["Open"] == 0,
    ))
    return rows


def module_ctx(comm: Any, name: str) -> dict[str, Any] | None:
    module = next(m for m in APP.modules if m.name == name)
    return px.read_layout(comm, gen.ctx_tag_for(APP, name), gen.module_members(module))


def write_config(comm: Any, key: str, value: int, ack: float) -> dict[str, Any]:
    """WRITE_CONFIG for the running record (model 0), resolved as the gateway
    resolves a client's write key."""
    return px.command(comm, mailbox.WRITE_CONFIG, settle=ack,
                      IntValue=mailbox.config_ordinal(APP, key), BoolValue=value,
                      **{mailbox.CONFIG_MODEL_MEMBER: 0})


def auto_cycle(comm: Any, ack: float, settle: float) -> bool:
    """One AUTO cycle from a START, parked at N100, then stopped."""
    px._idle(comm, ack)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == parity.AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    base = px.read_unit(comm)
    closed, _ = px.await_unit(comm, lambda u: base is not None
                              and u["CycleCount"] > base["CycleCount"], settle)
    px.command(comm, mailbox.STOP, settle=ack)
    return closed is not None and base is not None and closed["CycleCount"] > base["CycleCount"]


def timing_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # --- every command is timed, the one already there included --------------------
    px.home(comm, settle)                     # ram up, door open, slide outside
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    slide0, door0 = module_ctx(comm, "PartSlide"), module_ctx(comm, "Door")
    answers = []
    for name, command in (("PartSlide", 1), ("PartSlide", 2), ("Door", 2)):
        answers.append(px.manual(comm, name, command, settle=ack))
        px.await_module(comm, name, lambda c: c["Busy"] == 0 and c["Execute"] == 0, settle)
    slide1, door1 = module_ctx(comm, "PartSlide"), module_ctx(comm, "Door")
    values = projection.read_document(comm)["values"]
    period = APP.task_period_ms

    def delta(before, after, ordinal):
        i = ordinal - 1
        return None if None in (before, after) else (
            after["TimCount"][i] - before["TimCount"][i], after["TimLast"][i])

    seen = {"slideExtend": delta(slide0, slide1, 1), "slideRetract": delta(slide0, slide1, 2),
            "doorRetractAlreadyOpen": delta(door0, door1, 2)}
    published = {leaf: values.get(f"{ROOT}/PartSlide/Timing/Rows[1]/{leaf}")
                 for leaf in ("Id", "Label", "Count", "Last", "Minimum", "Maximum", "Avg")}
    rows.append(px.row(
        "every_command_is_timed",
        "manual commands in MANUAL: the slide's extend and retract each counted "
        "once at 40 ms (four 25-unit scans), and the door sent open while open "
        "counted once at one scan - the command TC3 never times; the slide's "
        "row published as the HMI reads it",
        {"answers": answers, "seen": seen, "published": published}, 0.0,
        all(a["accepted"] for a in answers)
        and seen["slideExtend"] == (1, 4 * period) and seen["slideRetract"] == (1, 4 * period)
        and seen["doorRetractAlreadyOpen"] == (1, period)
        and published["Id"] == 1 and published["Label"] == "std.command.extend"
        and slide1 is not None and published["Count"] == slide1["TimCount"][0]
        and published["Last"] == 4 * period
        and published["Minimum"] <= published["Avg"] <= published["Maximum"],
    ))

    # --- degradation: one maintenance event per excursion ---------------------------
    key = "press.recipe.baselineWorkMs"
    cfg = px.read_flat(comm, px.CFG, tuple(m.name for m in APP.records[0].members))
    original = None if cfg is None else cfg["BaselineWorkMs"]
    observed: dict[str, Any] = {"original": original}
    holds = False
    try:
        px._idle(comm, ack)
        observed["write"] = write_config(comm, key, 300, ack)
        prof0 = profile_raw(comm)
        log0 = px.read_layout(comm, gen.alarm_active_tag(APP), gen.alarm_active_members())
        observed["first"] = auto_cycle(comm, ack, settle)
        prof1 = profile_raw(comm)
        observed["second"] = auto_cycle(comm, ack, settle)
        prof2 = profile_raw(comm)
        log2 = px.read_layout(comm, gen.alarm_active_tag(APP), gen.alarm_active_members())
        ring = px.read_layout(comm, gen.alarm_ring_tag(APP), gen.alarm_ring_members())
        values = projection.read_document(comm)["values"]
        head = None if log2 is None else log2["RingHead"]
        entry = {} if ring is None or not head else {
            c: ring[f"Ring{c}"][head - 1] for c in (
                "ReasonCode", "Severity", "ResetClass", "SourceModuleId")}
        observed.update({
            "count": None if None in (prof0, prof1, prof2) else (
                prof0["DegradedCount"], prof1["DegradedCount"], prof2["DegradedCount"]),
            "work": None if prof1 is None else prof1["DegradedWorkMs"],
            "ringHead": None if None in (log0, log2) else (log0["RingHead"], log2["RingHead"]),
            "entry": entry,
            "published": {k: values.get(f"{ROOT}/AlarmLog/Ring[{head}]/{k}")
                          for k in ("ReasonCode", "SourcePath")} if head else {}})
        holds = (observed["write"]["accepted"] and observed["first"] and observed["second"]
                 and observed["count"] is not None
                 and observed["count"][1] == observed["count"][0] + 1
                 and observed["count"][2] == observed["count"][1]
                 and observed["work"] > 300 + 300 * 20 // 100
                 and entry == {"ReasonCode": 2007, "Severity": 0,
                               "ResetClass": gen.RESET_AUTO, "SourceModuleId": 1}
                 and observed["published"].get("ReasonCode") == 2007)
    finally:
        px._idle(comm, ack)
        if original is not None:
            observed["restore"] = write_config(comm, key, original, ack)
        restored = px.read_flat(comm, px.CFG, tuple(m.name for m in APP.records[0].members))
        observed["restored"] = None if restored is None else restored["BaselineWorkMs"]
    rows.append(px.row(
        "a_degraded_cycle_is_one_maintenance_event",
        "the running model's baseline written to 300 ms: the first cycle's ~970 ms "
        "of WORK passes 360 and raises ONE CYCLE_TIME_DEGRADED (2007) occurrence, "
        "LOW, AUTO_RESET, from the Unit; the second, still degraded, raises none; "
        "the baseline is written back",
        observed, 0.0,
        holds and observed.get("restored") == original,
    ))
    return rows


def flags(comm: Any) -> list[dict[str, Any]]:
    """The Unit's StateFlags as the gateway publishes them."""
    values = projection.read_document(comm)["values"]
    count = values.get(f"{ROOT}/StateFlagCount") or 0
    return [{leaf: values.get(f"{ROOT}/StateFlags[{i}]/{leaf}")
             for leaf in ("Key", "Value", "Since", "Stale")} for i in range(1, count + 1)]


def flag_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # --- at load position, and not latched --------------------------------------
    px.home(comm, settle)
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    seen = [("home", flags(comm)[0])]
    px.manual(comm, "PartSlide", 1, settle=ack)
    px.await_module(comm, "PartSlide", lambda c: c["Busy"] == 0 and c["Execute"] == 0, settle)
    seen.append(("slide in", flags(comm)[0]))
    px.manual(comm, "PartSlide", 2, settle=ack)
    px.await_module(comm, "PartSlide", lambda c: c["Busy"] == 0 and c["Execute"] == 0, settle)
    seen.append(("slide out", flags(comm)[0]))
    values = [f["Value"] for _, f in seen]
    since = [f["Since"] for _, f in seen]
    rows.append(px.row(
        "at_load_position_follows_the_cylinders",
        "TC3's pressAtLoadPosition: true at home, false the moment the slide "
        "goes in under a MANUAL command - no sequence runs to clear it - and true "
        "again when it comes out, each change stamped later than the last",
        seen, 0.0,
        seen[0][1]["Key"] == "project.state.pressAtLoadPosition"
        and values == [True, False, True]
        and all(isinstance(s, str) and s for s in since) and since[0] < since[1] < since[2]
        and all(f["Stale"] is False for _, f in seen),
    ))

    # --- ready for a two-hand start ---------------------------------------------
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    px.await_module(comm, "TwoHand", lambda c: c["OutImm_Armed"] != 0, settle)
    readiness = []
    for part in (1, 0, 1):
        px.write(comm, px.PART_PRESENT, part)
        px.await_module(comm, "PartPresentSensor", lambda c: c["OutImm_Value"] == part, settle)
        readiness.append((part, flags(comm)[1]["Value"]))
    rows.append(px.row(
        "two_hand_ready_follows_its_conditions",
        "TC3's pressTwoHandStartReady: armed, air and a part make it true; the "
        "part withdrawn makes it false at once, and back makes it true",
        {"key": flags(comm)[1]["Key"], "readiness": readiness}, 0.0,
        readiness == [(1, True), (0, False), (1, True)],
    ))
    px._idle(comm, ack)
    return rows


def health_rows(comm: Any, ack: float, settle: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    px._idle(comm, ack)
    time.sleep(1.2)                            # a full probe window
    values = projection.read_document(comm)["values"]
    facet = {k[len(f"{ROOT}/SystemHealth/"):]: v for k, v in values.items()
             if k.startswith(f"{ROOT}/SystemHealth/")}
    period = APP.task_period_ms * 1000
    rows.append(px.row(
        "system_health_is_published",
        "TC3's SystemHealth over S3's subset: evaluated, the task measured near its "
        "10 ms period with low jitter; CPU and memory unavailable, so not healthy; "
        "no fieldbus or distributed clock; the clock available and unsynchronized",
        facet, 0.0,
        facet.get("Present") is True and facet.get("TaskAvailable") is True
        and abs((facet.get("TaskCycleUs") or 0) - period) <= period // 10
        and (facet.get("TaskJitterUs") or 0) < APP.system_health.max_task_jitter_us
        and facet.get("Healthy") is False and facet.get("ControllerAvailable") is False
        and facet.get("FieldbusAvailable") is False and facet.get("DcAvailable") is False
        and facet.get("TimeQuality/Available") is True
        and facet.get("TimeQuality/Synchronized") is False,
    ))
    log = px.read_layout(comm, gen.alarm_active_tag(APP), gen.alarm_active_members())
    open_events = [] if log is None else [
        {c: log[f"Act{c}"][s] for c in ("ReasonCode", "Severity", "ResetClass", "SourceModuleId")}
        for s in range(len(log["ActState"])) if log["ActState"][s] != 0]
    health_codes = {APP.reasons[n] for n in gen.HEALTH_EVENTS}
    held = [e for e in open_events if e["ReasonCode"] in health_codes]
    rows.append(px.row(
        "unreadable_metrics_are_one_standing_event",
        "CONTROLLER_METRICS_UNAVAILABLE (21) is open once - LOW, AUTO_RESET, from the "
        "Unit - and nothing blocks a start; no overrun or jitter event is open",
        {"held": held, "blocking": None if log is None else log["Blocking"]}, 0.0,
        held == [{"ReasonCode": 21, "Severity": 0, "ResetClass": gen.RESET_AUTO,
                  "SourceModuleId": 1}]
        and log is not None and log["Blocking"] == 0,
    ))
    return rows


def run(comm: Any, settle: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ack = parity.ack(settle)
    for tag in (px.PART_PRESENT, px.AIR_OK, px.TWO_HAND):
        px.write(comm, tag, 1)
    px._idle(comm, ack)

    # --- 1. what the step toggle reads ----------------------------------------------
    values = projection.read_document(comm)["values"]
    offered = [values.get(f"{ROOT}/SupportedRunStylesPublished[{s + 1}]")
               for s in decl.RUN_STYLES]
    rows.append(px.row(
        "the_unit_publishes_its_run_styles",
        "TC3's SupportedRunStylesPublished: all three offered, CONTINUOUS running",
        {"offered": offered, "runStyle": values.get(f"{ROOT}/RunStyle")}, 0.0,
        offered == [True, True, True] and values.get(f"{ROOT}/RunStyle") == 0,
    ))

    # --- 2. refusals by name ---------------------------------------------------------
    outside = px.command(comm, mailbox.SET_RUN_STYLE, settle=ack, IntValue=3)
    px.command(comm, mailbox.SET_RUN_STYLE, settle=ack, IntValue=decl.RUN_SINGLE_STEP)
    stopped_step = px.command(comm, mailbox.STEP_REQUEST, settle=ack)
    hold_wrong = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=1)
    release = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=0)
    unit = px.read_unit(comm)
    rows.append(px.row(
        "outside_its_style_each_request_is_refused_by_name",
        "a style outside E_RunStyle: std.error.unsupportedRunStyleRequest, the "
        "style kept; a Step while stopped and a hold outside HOLD_TO_RUN refused "
        "by name; a release always taken",
        {"outside": outside, "stepWhileStopped": stopped_step, "holdInSingleStep": hold_wrong,
         "release": release, "runStyle": None if unit is None else unit["RunStyle"]},
        0.0,
        not outside["accepted"]
        and outside["diagnosticKey"] == key(mailbox.RUN_STYLE_REFUSED_KEY)
        and not stopped_step["accepted"]
        and stopped_step["diagnosticKey"] == key(mailbox.STEP_REFUSED_KEY)
        and not hold_wrong["accepted"]
        and hold_wrong["diagnosticKey"] == key(mailbox.HOLD_RUN_REFUSED_KEY)
        and release["accepted"]
        and unit is not None and unit["RunStyle"] == decl.RUN_SINGLE_STEP,
    ))
    px._idle(comm, ack)

    # --- 3. SINGLE_STEP, one command per request, in every rendition -----------------
    for rendition in AUTO.renditions:
        cycle = stepped_cycle(comm, rendition, ack, settle)
        rows.append(px.row(
            f"single_step_issues_one_command_per_request_{rendition.lower()}",
            f"{rendition}: nothing before the first Step, then exactly one command "
            f"per Step - {DECLARED} for the cycle - and the cycle closes",
            cycle, cycle["elapsed_ms"],
            cycle["perRequest"] == [0] + [1] * DECLARED
            and not cycle["refusals"] and cycle["cycleClosed"]
            and cycle["opened"]["style"]["accepted"],
        ))
        px._idle(comm, ack)

    # --- 4. HOLD_TO_RUN, in every rendition ---------------------------------------------
    for rendition in AUTO.renditions:
        cycle = held_cycle(comm, rendition, ack, settle)
        rows.append(px.row(
            f"hold_to_run_issues_only_while_held_{rendition.lower()}",
            f"{rendition}: nothing unheld; released during the slide's motion the "
            f"slide arrives and the door close waits un-issued; held again the "
            f"cycle completes with its {DECLARED} commands",
            cycle, 0.0,
            cycle["issuedUnheld"] == 0
            and cycle["unheld"] == {"Step": PATH[0], "Issued": 0}
            and all(a["accepted"] for a in cycle["answers"].values())
            and cycle["motionAtRelease"] == {"Busy": 1, "OutImm_Held": 1}
            and cycle["reachedDoorClose"]
            and cycle["releasedAt"] == {"Step": DOOR_CLOSE, "Issued": 0, "HoldRun": 0}
            and cycle["slideArrived"] == 1
            and cycle["issuedBeforeRelease"] == PATH.index(DOOR_CLOSE)
            and cycle["issuedInCycle"] == DECLARED and cycle["cycleClosed"],
        ))
        px._idle(comm, ack)

    # --- 5. a stop ends the hold ----------------------------------------------------------
    # STOP alone, read before any reset: the hold ends because the Unit stopped.
    begin(comm, decl.ST, decl.RUN_HOLD_TO_RUN, ack, settle)
    held = px.command(comm, mailbox.SET_HOLD_RUN, settle=ack, BoolValue=1)
    holding = px.read_unit(comm)
    px.command(comm, mailbox.STOP, settle=ack)
    after_stop, _ = px.await_unit(comm, lambda u: u["Running"] == 0, settle)
    begin(comm, decl.ST, decl.RUN_HOLD_TO_RUN, ack, settle)
    count = issued(comm)
    time.sleep(0.6)
    restarted = px.read_unit(comm)
    unheld = issued(comm)
    rows.append(px.row(
        "a_stop_ends_the_hold",
        "held, then stopped: HoldRun is 0, and the next START in HOLD_TO_RUN "
        "issues nothing until held again",
        {"held": held, "holding": None if holding is None else holding["HoldRun"],
         "afterStop": None if after_stop is None else after_stop["HoldRun"],
         "restarted": None if restarted is None else {k: restarted[k] for k in (
             "Running", "Step", "Issued")},
         "issuedAfterRestart": None if None in (unheld, count) else unheld - count},
        0.0,
        held["accepted"] and holding is not None and holding["HoldRun"] == 1
        and after_stop is not None and after_stop["HoldRun"] == 0
        and restarted is not None and restarted["Running"] == 1
        and restarted["Step"] == PATH[0] and restarted["Issued"] == 0
        and unheld is not None and count is not None and unheld == count,
    ))

    # --- 6. (5c) OEE ---------------------------------------------------------------------
    rows.extend(oee_rows(comm, ack, settle))

    # --- 7. (5d) machine state and rework ----------------------------------------------
    rows.extend(machine_rows(comm, ack, settle))

    # --- 8. (5e) the cycle-time profile --------------------------------------------------
    rows.extend(profiler_rows(comm, ack, settle))

    # --- 9. (5f) command timing and the degradation watch --------------------------------
    rows.extend(timing_rows(comm, ack, settle))

    # --- 10. (5g) derived state flags -----------------------------------------------------
    rows.extend(flag_rows(comm, ack, settle))

    # --- 11. (5h) system health ---------------------------------------------------------
    rows.extend(health_rows(comm, ack, settle))

    px._idle(comm, ack)
    back = px.read_unit(comm)
    rows.append(px.row(
        "the_press_is_left_continuous",
        "the harness leaves the press as it found it: CONTINUOUS, stopped",
        None if back is None else {k: back[k] for k in ("RunStyle", "Running")}, 0.0,
        back is not None and back["RunStyle"] == decl.RUN_CONTINUOUS and back["Running"] == 0,
    ))
    successful = sum(1 for r in rows if r["passed"])
    return {"tests": len(rows), "successful": successful,
            "failed": len(rows) - successful, "passed": successful == len(rows),
            "rows": rows}


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

    from pylogix import PLC

    evidence: dict[str, Any] = {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "target": args.target, "expected_serial": args.expect_serial,
        "application": APP.name,
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
        evidence["identity"] = {"product_name": getattr(device, "ProductName", ""),
                                "revision": getattr(device, "Revision", ""),
                                "serial_number": serial}
        evidence["serial_matches"] = serial == args.expect_serial
        if not evidence["serial_matches"]:
            evidence["error"] = "controller serial does not match --expect-serial"
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1
        ready = px.fingerprint(comm)
        evidence["fingerprint"] = ready
        if not ready.get("passed"):
            evidence["error"] = "press-demo fingerprint failed; nothing was written"
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1
        evidence["wrote"] = True
        evidence["write_surface"] = list(px.WRITABLE) + ["mailbox"]
        evidence["sequence_seed"] = px.seed_sequence(comm)
        try:
            evidence["result"] = run(comm, args.settle)
        finally:
            # A row that died mid-way must not leave the press paced.
            try:
                px._idle(comm, parity.ack(args.settle))
            finally:
                evidence["disarm"] = px.disarm(comm)
    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values()))
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
