#!/usr/bin/env python3
"""Execute the generated press demo and emit machine-readable rows.

The fixed harness for the press demo. Not a generic PLC writer: it requires the
exact controller serial, an explicit arm flag and the application's fingerprint
before its first write, writes only the declared input tags, and restores every
one of them in a ``finally`` block.

Every structure is read in **one** request. The unit context, the chart and each
module context are single CIP payloads, atomic on the wire. A press demo whose
plant moves every 10 ms cannot be observed member-by-member: that is the tearing
``AB_S9_COHERENCE_EVIDENCE.md`` measured and the S16 harness had to be fixed for.

Tag values are reported as shape and status; the record carries
``values_redacted: true``.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_generate as gen
import fraktal_ab_press_demo as demo


SCHEMA = "fraktal.ab.press-execute"
SCHEMA_VERSION = 1
SUITE = "fraktal.ab.press-demo"

APP = demo.application()
N = APP.name

UNIT = f"FRK_{N}_Unit"
CHART = f"FRK_{N}_Chart"
CFG = f"{APP.records[0].name}Tag"
SCAN_COUNT = f"FRK_{N}_ScanCount"
ORDER_FAIL = f"FRK_{N}_OrderFail"
TASK_PERIOD = f"FRK_{N}_TaskPeriodMs"

RUN = f"FRK_{N}_RunRequest"
ABORT = f"FRK_{N}_AbortRequest"
RESET = f"FRK_{N}_ResetRequest"
MODE = f"FRK_{N}_ModeRequest"
ANSWER = f"FRK_{N}_DecisionAnswer"
TWO_HAND = f"FRK_{N}_TwoHand"
PART_PRESENT = f"FRK_{N}_PartPresent"
AIR_OK = f"FRK_{N}_AirOk"
JOG = f"FRK_{N}_JogCommand"

FAULT = {m.name: f"FRK_{N}_Fault{m.name}" for m in APP.modules}
HOLD = {m.name: f"FRK_{N}_Hold{m.name}" for m in APP.modules}
MODULE_CTX = {m.name: gen.ctx_tag_for(APP, m.name) for m in APP.modules}

WRITABLE = tuple(gen.writable_inputs(APP))

UNIT_MEMBERS = tuple(m.name for m in gen.unit_context_members(APP))
MODULE_MEMBERS = tuple(m.name for m in gen.module_context_members())
CHART_LAYOUT = gen.chart_members(APP)

MODE_MANUAL, MODE_AUTO, MODE_HOME = demo.MODE_MANUAL, demo.MODE_AUTO, demo.MODE_HOME
R = demo.REASONS


def _unpack_flat(payload: bytes, names: tuple[str, ...]) -> dict[str, int] | None:
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < len(names) * 4:
        return None
    values = struct.unpack_from(f"<{len(names)}i", payload, 0)
    return dict(zip(names, values))


def read_flat(comm: Any, tag: str, names: tuple[str, ...]) -> dict[str, int] | None:
    reply = comm.Read(tag)
    if not _success(reply):
        return None
    return _unpack_flat(_value(reply), names)


def read_chart(comm: Any) -> dict[str, Any] | None:
    """The §3.13 chart, including its per-step arrays, in one request."""
    reply = comm.Read(CHART)
    if not _success(reply):
        return None
    payload = _value(reply)
    total = sum(m.dimension or 1 for m in CHART_LAYOUT)
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < total * 4:
        return None
    values = struct.unpack_from(f"<{total}i", payload, 0)
    out: dict[str, Any] = {}
    i = 0
    for member in CHART_LAYOUT:
        if member.dimension:
            out[member.name] = list(values[i:i + member.dimension])
            i += member.dimension
        else:
            out[member.name] = values[i]
            i += 1
    return out


def read_unit(comm: Any) -> dict[str, int] | None:
    return read_flat(comm, UNIT, UNIT_MEMBERS)


def read_module(comm: Any, name: str) -> dict[str, int] | None:
    return read_flat(comm, MODULE_CTX[name], MODULE_MEMBERS)


def read_scalar(comm: Any, tag: str) -> int | None:
    reply = comm.Read(tag)
    if not _success(reply):
        return None
    value = _value(reply)
    return value if isinstance(value, int) else None


def write(comm: Any, tag: str, value: int) -> bool:
    if tag not in WRITABLE:
        raise AssertionError(f"tag outside the declared write surface: {tag}")
    return _success(comm.Write(tag, value))


def await_unit(comm: Any, predicate: Any, settle: float):
    deadline = time.monotonic() + settle
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        observed = read_unit(comm)
        if observed is None:
            return None, (time.monotonic() - started) * 1000.0
        last = observed
        if predicate(observed):
            return observed, (time.monotonic() - started) * 1000.0
        time.sleep(0.005)
    return last, (time.monotonic() - started) * 1000.0


def row(name: str, expectation: str, observed, elapsed_ms: float, holds: bool):
    return {
        "test": name,
        "suite": SUITE,
        "expectation": expectation,
        "passed": bool(holds),
        "elapsed_ms": round(elapsed_ms, 3),
        "observed": observed,
    }


def fingerprint(comm: Any) -> dict[str, Any]:
    """Prove this is the generated press demo before writing anything."""
    readings: dict[str, Any] = {}
    unit = read_unit(comm)
    if unit is None:
        return {"passed": False, "failed_tag": UNIT, "status": "unreadable"}
    cfg = read_flat(comm, CFG, tuple(m.name for m in APP.records[0].members))
    if cfg is None:
        return {"passed": False, "failed_tag": CFG, "status": "unreadable"}
    for tag in (SCAN_COUNT, TASK_PERIOD, ORDER_FAIL):
        value = read_scalar(comm, tag)
        if value is None:
            return {"passed": False, "failed_tag": tag, "status": "unreadable"}
        readings[tag] = value
    readings["Unit.SchemaVersion"] = unit["SchemaVersion"]
    readings["Unit.Par_TaskPeriodMs"] = unit["Par_TaskPeriodMs"]
    readings["Cfg.SchemaVersion"] = cfg["SchemaVersion"]
    checks = {
        "unit_schema": unit["SchemaVersion"] == gen.SCHEMA_VERSION,
        "cfg_schema": cfg["SchemaVersion"] == APP.records[0].schema_version,
        # The task period is part of the contract: the timeouts were converted
        # from it, so a project running on another period is a different machine.
        "task_period": readings[TASK_PERIOD] == APP.task_period_ms
        and unit["Par_TaskPeriodMs"] == APP.task_period_ms,
        "scan_running": bool(readings[SCAN_COUNT]),
    }
    return {"passed": all(checks.values()), "checks": checks, "readings": readings}


def disarm(comm: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for tag in WRITABLE:
        ok = _success(comm.Write(tag, 0))
        if ok:
            reply = comm.Read(tag)
            ok = _success(reply) and _value(reply) == 0
        result[tag] = "cleared" if ok else "FAILED"
    return result


def _idle(comm: Any, settle: float) -> None:
    """Return the unit to a clean, stopped state between rows."""
    for tag in (RUN, ABORT, ANSWER, JOG):
        write(comm, tag, 0)
    for name in FAULT:
        write(comm, FAULT[name], 0)
        write(comm, HOLD[name], 0)
    write(comm, RESET, 1)
    time.sleep(min(settle, 0.15))
    write(comm, RESET, 0)


def run(comm: Any, settle: float) -> dict[str, Any]:
    """The fixed press-demo matrix."""
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    steps = gen.ordered_steps(APP)

    def index_of(number: int) -> int:
        return steps.index(number)

    # World inputs the plant needs to run at all.
    write(comm, PART_PRESENT, 1)
    write(comm, AIR_OK, 1)
    write(comm, TWO_HAND, 1)
    _idle(comm, settle)

    # 1 - a full AUTO cycle.
    write(comm, MODE, MODE_AUTO)
    base = read_unit(comm)
    write(comm, RUN, 1)
    observed, elapsed = await_unit(
        comm, lambda o: base is not None and o["CycleCount"] > base["CycleCount"], settle)
    chart = read_chart(comm)
    rows.append(row(
        "auto_full_cycle",
        "the AUTO chain completes a cycle with no adopted fault",
        {"unit": observed, "visited": None if chart is None else sum(chart["Visited"])},
        elapsed,
        observed is not None and base is not None
        and observed["CycleCount"] > base["CycleCount"]
        and observed["Error"] == 0 and observed["Aborted"] == 0
        and observed["OrderFail"] == 0,
    ))

    # 2 - two-hand released mid door close: HELD, LOW, no fault, then self-resume.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, RUN, 1)
    # Arm the hold during the transfer settle (a declared 200 ms window) rather
    # than during the door close itself, which is four scans wide. Racing a
    # 40 ms window would make this row flaky rather than wrong.
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, TWO_HAND, 0)
    held_observed, elapsed = await_unit(comm, lambda o: o["Held"] != 0, settle)
    chart_held = read_chart(comm)
    door_held = read_module(comm, "Door")
    rows.append(row(
        "held_two_hand_released_during_door_close",
        "released mid-close: Held with a LOW named reason, no Error, no advance",
        {"unit": held_observed,
         "stall_reason": None if chart_held is None else chart_held["StallReason"],
         "door_state": None if door_held is None else door_held["OutImm_ExecState"]},
        elapsed,
        held_observed is not None
        and held_observed["Held"] != 0
        and held_observed["HeldReason"] == R["TWO_HAND_RELEASED"]
        and held_observed["HeldSeverity"] == gen.SEVERITY_LOW
        and held_observed["Error"] == 0
        and held_observed["Step"] == 180
        and chart_held is not None
        and chart_held["StallReason"] == R["TWO_HAND_RELEASED"],
    ))

    # 3 - the hold releases on its own when the condition returns.
    write(comm, TWO_HAND, 1)
    resumed, elapsed = await_unit(
        comm, lambda o: o["Held"] == 0 and o["Step"] != 180, settle)
    rows.append(row(
        "held_self_resumes_without_reissue",
        "restoring the two-hand resumes the close with no fresh command",
        resumed, elapsed,
        resumed is not None and resumed["Held"] == 0
        and resumed["Step"] != 180 and resumed["Error"] == 0,
    ))

    # 4 - an awaited child's fault is adopted first-out, verbatim, and stops the chain.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, FAULT["PartSlide"], 1)
    write(comm, RUN, 1)
    faulted, elapsed = await_unit(comm, lambda o: o["Error"] != 0, settle)
    chart_fault = read_chart(comm)
    slide = read_module(comm, "PartSlide")
    rows.append(row(
        "awaited_child_fault_adopted_first_out",
        "the unit adopts the child's ErrorID verbatim and stops on that step",
        {"unit": faulted,
         "child_error_id": None if slide is None else slide["ErrorID"],
         "stall_reason": None if chart_fault is None else chart_fault["StallReason"]},
        elapsed,
        faulted is not None and slide is not None
        and faulted["Error"] != 0
        and faulted["ErrorID"] == slide["ErrorID"]
        and faulted["ErrorID"] == R["DEVICE_FAULT"]
        and faulted["Step"] == 150
        and faulted["Running"] == 0,
    ))

    # 5 - restart by re-issue after clearing the fault.
    write(comm, FAULT["PartSlide"], 0)
    write(comm, RUN, 0)
    write(comm, RESET, 1)
    time.sleep(min(settle, 0.15))
    write(comm, RESET, 0)
    write(comm, RUN, 1)
    restarted, elapsed = await_unit(
        comm, lambda o: o["Error"] == 0 and o["Running"] != 0 and o["Step"] != 150, settle)
    rows.append(row(
        "restart_by_reissue_after_adopted_fault",
        "clearing the fault and re-issuing restarts the chain",
        restarted, elapsed,
        restarted is not None and restarted["Error"] == 0 and restarted["Running"] != 0,
    ))

    # 6 - the reported-not-adopted child condition, then the decision, answered 'scrap'.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, RUN, 1)
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, FAULT["PressRam"], 1)
    reported, elapsed = await_unit(comm, lambda o: o["Step"] == 210, settle)
    chart_dec = read_chart(comm)
    rows.append(row(
        "child_condition_reported_not_adopted",
        "a ram failure is reported as a message and the chain reaches the decision "
        "without the unit faulting",
        {"unit": reported,
         "stall_reason": None if chart_dec is None else chart_dec["StallReason"]},
        elapsed,
        reported is not None
        and reported["Step"] == 210
        and reported["Error"] == 0
        and reported["ReportedReason"] == R["DEVICE_FAULT"]
        and reported["ReportedCount"] >= 1,
    ))

    # 7 - the chain waits on the decision without faulting, and the stall reason says so.
    waiting = read_unit(comm)
    chart_wait = read_chart(comm)
    rows.append(row(
        "decision_step_waits_without_faulting",
        "the decision is published and the chain waits with a named stall reason",
        {"unit": waiting,
         "stall_reason": None if chart_wait is None else chart_wait["StallReason"]},
        0.0,
        waiting is not None and chart_wait is not None
        and waiting["DecisionId"] == demo.DECISION_PRESS_NOT_REACHED
        and waiting["Error"] == 0
        and chart_wait["StallReason"] == R["WAIT_DECISION"],
    ))

    # 8 - answer 'scrap' (1): the part is dispositioned NOK.
    write(comm, FAULT["PressRam"], 0)
    before_scrap = read_unit(comm)
    write(comm, ANSWER, 1)
    scrapped, elapsed = await_unit(
        comm, lambda o: before_scrap is not None and o["ScrapCount"] > before_scrap["ScrapCount"],
        settle)
    write(comm, ANSWER, 0)
    rows.append(row(
        "decision_answer_scrap",
        "answering scrap dispositions the part NOK and the chain continues",
        scrapped, elapsed,
        scrapped is not None and before_scrap is not None
        and scrapped["ScrapCount"] > before_scrap["ScrapCount"]
        and scrapped["Error"] == 0,
    ))

    # 9 - the other answer (2): return without scrapping.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, RUN, 1)
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, FAULT["PressRam"], 1)
    await_unit(comm, lambda o: o["Step"] == 210, settle)
    write(comm, FAULT["PressRam"], 0)
    before_return = read_unit(comm)
    write(comm, ANSWER, 2)
    returned, elapsed = await_unit(
        comm, lambda o: o["Step"] not in (210,) and o["DecisionId"] == 0, settle)
    write(comm, ANSWER, 0)
    rows.append(row(
        "decision_answer_return",
        "the other answer leaves the scrap count alone and rejoins the chain",
        returned, elapsed,
        returned is not None and before_return is not None
        and returned["ScrapCount"] == before_return["ScrapCount"]
        and returned["Error"] == 0,
    ))

    # 10 - MANUAL jog.
    _idle(comm, settle)
    write(comm, MODE, MODE_MANUAL)
    write(comm, RUN, 1)
    before_jog = read_module(comm, "PartSlide")
    write(comm, JOG, 1)
    jogged, elapsed = await_unit(comm, lambda o: o["Step"] in (10, 20), settle)
    slide_jog = read_module(comm, "PartSlide")
    write(comm, JOG, 0)
    rows.append(row(
        "manual_jog",
        "MANUAL moves the selected module one command per request",
        {"unit": jogged,
         "slide_runs": None if slide_jog is None else slide_jog["RunCount"]},
        elapsed,
        jogged is not None and slide_jog is not None and before_jog is not None
        and slide_jog["RunCount"] > before_jog["RunCount"]
        and jogged["Error"] == 0,
    ))

    # 11 - HOME completes and stops, rather than looping.
    _idle(comm, settle)
    write(comm, MODE, MODE_HOME)
    write(comm, RUN, 1)
    homed, elapsed = await_unit(comm, lambda o: o["Complete"] != 0, settle)
    rows.append(row(
        "home_completes_and_stops",
        "HOME establishes the load-safe position, completes, and does not loop",
        homed, elapsed,
        homed is not None and homed["Complete"] != 0
        and homed["Running"] == 0 and homed["Error"] == 0,
    ))

    # 12 - a mode switch mid-cycle stands the chain down.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, RUN, 1)
    await_unit(comm, lambda o: o["Step"] not in (0,), settle)
    before_switch = read_unit(comm)
    write(comm, MODE, MODE_MANUAL)
    switched, elapsed = await_unit(comm, lambda o: o["Mode"] == MODE_MANUAL, settle)
    rows.append(row(
        "mode_switch_midcycle_stands_the_chain_down",
        "the chain returns to its init step and does not resume by itself",
        switched, elapsed,
        switched is not None and before_switch is not None
        and switched["Mode"] == MODE_MANUAL
        and switched["ModeSwitches"] > before_switch["ModeSwitches"]
        and switched["Step"] == 0,
    ))

    # 13 - an aborted AUTO stays aborted.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, TWO_HAND, 1)
    write(comm, RUN, 1)
    await_unit(comm, lambda o: o["Running"] != 0, settle)
    write(comm, ABORT, 1)
    aborted, elapsed = await_unit(comm, lambda o: o["Aborted"] != 0, settle)
    time.sleep(min(settle, 0.2))
    after_abort = read_unit(comm)
    write(comm, ABORT, 0)
    rows.append(row(
        "auto_abort_does_not_self_resume",
        "an aborted AUTO stands down and stays down while the request is held",
        after_abort, elapsed,
        aborted is not None and after_abort is not None
        and aborted["Aborted"] != 0 and after_abort["Running"] == 0,
    ))

    # 14 - a blocked condition publishes a named stall reason, not a fault.
    _idle(comm, settle)
    write(comm, MODE, MODE_AUTO)
    write(comm, PART_PRESENT, 0)
    write(comm, RUN, 1)
    blocked, elapsed = await_unit(comm, lambda o: o["Step"] == 100, settle)
    chart_block = read_chart(comm)
    write(comm, PART_PRESENT, 1)
    rows.append(row(
        "blocked_condition_publishes_a_stall_reason",
        "a step waiting on a missing condition names why, and raises no fault",
        {"unit": blocked,
         "stall_reason": None if chart_block is None else chart_block["StallReason"]},
        elapsed,
        blocked is not None and chart_block is not None
        and blocked["Step"] == 100 and blocked["Error"] == 0
        and chart_block["StallReason"] == R["PART_NOT_PRESENT"],
    ))

    # 15 - the §3.13 marks: a cursor, visited steps and last durations.
    _idle(comm, settle)
    chart_final = read_chart(comm)
    order_fail = read_scalar(comm, ORDER_FAIL)
    visited = 0 if chart_final is None else sum(1 for v in chart_final["Visited"] if v)
    durations = 0 if chart_final is None else sum(
        1 for d in chart_final["LastMs"] if d > 0)
    rows.append(row(
        "chart_marks_and_ordering",
        "the chart carries a cursor, visited marks and last durations; ordering held",
        {"visited_steps": visited, "steps_with_durations": durations,
         "cursor": None if chart_final is None else chart_final["StepCursor"],
         "OrderFail": order_fail},
        0.0,
        chart_final is not None and order_fail == 0
        and visited >= 10 and durations >= 5,
    ))

    duration_ms = (time.monotonic() - started) * 1000.0
    successful = sum(1 for r in rows if r["passed"])
    return {
        "suites": 1,
        "tests": len(rows),
        "successful": successful,
        "failed": len(rows) - successful,
        "duration_ms": round(duration_ms, 3),
        "declared_task_period_ms": APP.task_period_ms,
        "passed": successful == len(rows),
        "rows": rows,
    }


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True, type=_normalize_serial)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--settle", type=float, default=3.0)
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute_fixture:
        parser.error("--execute-fixture is required")
    if not 0 < args.settle <= 5:
        parser.error("--settle must be greater than zero and at most five seconds")
    return args


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    from pylogix import PLC

    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "target": args.target,
        "expected_serial": args.expect_serial,
        "client": "pylogix 1.1.5",
        "suite": SUITE,
        "application": APP.name,
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

        print_ready = fingerprint(comm)
        evidence["fingerprint"] = print_ready
        if not print_ready.get("passed"):
            evidence["error"] = "press-demo fingerprint failed; nothing was written"
            evidence["wrote"] = False
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1

        evidence["wrote"] = True
        evidence["write_surface"] = list(WRITABLE)
        try:
            evidence["result"] = run(comm, args.settle)
        finally:
            evidence["disarm"] = disarm(comm)

    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values())
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
