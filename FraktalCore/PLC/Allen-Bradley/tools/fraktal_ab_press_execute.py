#!/usr/bin/env python3
"""Execute the generated press demo and emit machine-readable rows.

The fixed harness for the press demo. Not a generic PLC writer: it requires the
exact controller serial, an explicit arm flag and the application's fingerprint
before its first write, writes only the declared input tags, and restores every
one of them in a ``finally`` block.

Legacy structures are read in one request. Collapsed profiles read canonical
leaves and accounted O10 facts under one progressing scan proof, and command
through O11's supervised gateway. Their reads never fall back to old contexts.

Tag values are reported as shape and status; the record carries
``values_redacted: true``.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from functools import partial
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_station as station
import fraktal_ab_fixture_reads as fixture_reads


SCHEMA = "fraktal.ab.press-execute"
SCHEMA_VERSION = 1
SUITE = "fraktal.ab.press-demo"

# The readers below serve the selected station (fraktal_ab_station); the
# harness rows are the press's and its fingerprint refuses any other.
APP = station.application()
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

FAULT = {m.name: gen.injection_tag(APP, m, "Fault") for m in APP.modules
         if "Fault" in library.type_of(m).injections}
HOLD = {m.name: gen.injection_tag(APP, m, "Hold") for m in APP.modules
        if "Hold" in library.type_of(m).injections}
MODULE_CTX = {m.name: gen.ctx_tag_for(APP, m.name) for m in APP.modules}

# The plant only. Every command tag is ExternalAccess None on the closed
# build (AB 11.2.1), so the matrix commands through the mailbox and keeps
# writing sensors directly - a sensor is not a command.
WRITABLE = tuple(gen.externally_writable(APP))

# The declared layouts, arrays included: a structure is read against its
# members, never its member NAMES. A names-only read assumes every member is
# one DINT, and the first array a type gained (Phase 5f's command timing)
# shifted every member after it - the gateway refused the station rather than
# publish the shifted values, which is the only reason it was not worse.
MODULE_LAYOUT = {m.name: gen.module_members(m) for m in APP.modules}
CHART_LAYOUT = gen.chart_members(APP)

MODE_MANUAL, MODE_AUTO, MODE_HOME = demo.MODE_MANUAL, demo.MODE_AUTO, demo.MODE_HOME
R = demo.REASONS


def _unpack_flat(payload: bytes, names: tuple[str, ...]) -> dict[str, int] | None:
    """Scalar-only structures (the configuration records). Anything with an
    array is read with `_read_record`; test_fraktal_ab_readers holds every
    caller to that."""
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < len(names) * 4:
        return None
    values = struct.unpack_from(f"<{len(names)}i", payload, 0)
    return dict(zip(names, values))


def read_flat(comm: Any, tag: str, names: tuple[str, ...]) -> dict[str, int] | None:
    reply = comm.Read(tag)
    if not _success(reply):
        return None
    return _unpack_flat(_value(reply), names)


unit_surface = partial(fixture_reads.unit_surface, app=APP)
chart_surface = partial(fixture_reads.chart_surface, app=APP)
module_surface = partial(fixture_reads.module_surface, app=APP)


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


_SEQUENCE = {"value": 0}


def seed_sequence(comm: Any) -> int:
    """Seed the uint32 bit pattern from this controller's committed input.

    The mailbox refuses a sequence it has already answered, and a harness that
    restarted at 1 would have its first command ignored as a replay.
    """
    if APP.canonical_collapse:
        _SEQUENCE['value'] = fixture_reads.controls(comm, app=APP)['sequence']
        return _SEQUENCE['value']
    request = read_scalar(comm, f"{mailbox.request_tag_name(APP)}.Sequence")
    if request is None:
        raise AssertionError("mailbox sequence read failed; nothing written")
    _SEQUENCE["value"] = request & 0xffffffff
    return _SEQUENCE["value"]


def command(comm: Any, kind: int, settle: float = 2.0,
            **arguments: Any) -> dict[str, Any]:
    """Issue one command and independently wait for its PLC acknowledgement."""
    return fixture_reads.command(comm, kind, app=APP, settle=settle, **arguments)


def await_response(comm: Any, sequence: int, settle: float = 2.0) -> dict[str, Any]:
    """Read the complete response only after its final acknowledgement."""
    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        row = fixture_reads.controls(comm, app=APP)
        if row['ack'] == (sequence & 0xffffffff):
            return dict(sequence=sequence, accepted=row['accepted'], diagnosticKey=row['diagnosticKey'])
        time.sleep(0.02)
    raise AssertionError(f"no acknowledgement of sequence {sequence}")


def manual(comm: Any, module: str, value: int, settle: float = 2.0) -> dict[str, Any]:
    """TC3's ManualCommandTo over the mailbox, resolved as the gateway does:
    the module's identity in TargetPath, its ordinal where the controller
    reads it, the catalogue command in IntValue."""
    identity = f"{APP.name}.{module}"
    if APP.canonical_collapse:
        return command(comm, mailbox.MANUAL_COMMAND, settle=settle, TargetPath=identity, IntValue=value)
    return command(comm, mailbox.MANUAL_COMMAND, settle=settle, TargetPath=identity,
                   IntValue=value,
                   **{mailbox.MANUAL_TARGET_MEMBER: mailbox.manual_target(APP, identity)})


def await_unit(comm: Any, predicate: Any, settle: float):
    deadline = time.monotonic() + settle
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        observed = unit_surface(comm)
        if observed is None:
            return None, (time.monotonic() - started) * 1000.0
        last = observed
        if predicate(observed):
            return observed, (time.monotonic() - started) * 1000.0
        time.sleep(0.005)
    return last, (time.monotonic() - started) * 1000.0


def await_chart(comm: Any, predicate: Any, settle: float):
    """Poll the chart until it settles. Step entry zeroes the marks, so a single
    read taken the moment a step is reached can catch that scan and report a
    cleared stall reason that was never the steady state."""
    deadline = time.monotonic() + settle
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        observed = chart_surface(comm)
        if observed is None:
            return None, (time.monotonic() - started) * 1000.0
        last = observed
        if predicate(observed):
            return observed, (time.monotonic() - started) * 1000.0
        time.sleep(0.005)
    return last, (time.monotonic() - started) * 1000.0


def await_module(comm: Any, name: str, predicate: Any, settle: float):
    deadline = time.monotonic() + settle
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        observed = module_surface(comm, name)
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


def fingerprint(comm: Any, *, expect_serial=None) -> dict[str, Any]:
    """Prove this is the generated press demo before writing anything."""
    readings: dict[str, Any] = {}
    if APP.canonical_collapse:
        fixture_reads.bind(comm, APP, expect_serial)
    unit = unit_surface(comm)
    if unit is None:
        return {"passed": False, "failed_tag": UNIT, "status": "unreadable"}
    cfg = (fixture_reads.surface(comm, 'Cfg0', app=APP) if APP.canonical_collapse else
           read_flat(comm, CFG, tuple(m.name for m in APP.records[0].members)))
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


def _idle(comm: Any, settle: float, command_fn=None) -> None:
    """Return the unit to a clean, stopped state between rows.

    STOP lowers the run level and raises the abort; OPERATOR_RESET clears it
    again. The harness supplies no deassert for either: the mailbox handler
    lowers its own one-shots on the following scan, which is the whole point of
    the 2026-09-22 fix.

    It also returns the run style to CONTINUOUS: a row that left the press in
    SINGLE_STEP would stall every later cycle at its first command, and the
    style is a mailbox setting the disarm's tag writes cannot reach. A build
    without run styles refuses it, and the refusal is acknowledged all the same.
    """
    issue = command if command_fn is None else command_fn
    for name in FAULT:
        write(comm, FAULT[name], 0)
        write(comm, HOLD[name], 0)
    issue(comm, mailbox.STOP)
    issue(comm, mailbox.OPERATOR_RESET)
    issue(comm, mailbox.SET_RUN_STYLE, IntValue=decl.RUN_CONTINUOUS)


def two_hand_press(comm: Any, settle: float) -> None:
    """Release the two-hand, wait until it arms, then press it.

    TC3's FB_TwoHandStartCM starts on an edge and arms only on a release
    between starts, so holding the stimulus high is not a start.
    """
    write(comm, TWO_HAND, 0)
    await_module(comm, "TwoHand", lambda c: c["OutImm_Armed"] != 0, settle)
    write(comm, TWO_HAND, 1)


def start_cycle(comm: Any, settle: float) -> dict[str, Any]:
    """START, then a fresh two-hand press - the latched start N100 waits on.

    Released first, so the START finds the press ready rather than started
    by a press left high; then the press latches the start, with the part
    and air the caller has already set.
    """
    write(comm, TWO_HAND, 0)
    answer = command(comm, mailbox.START, settle=min(settle, 1.0))
    two_hand_press(comm, settle)
    return answer


def home(comm: Any, settle: float) -> dict[str, int] | None:
    """Run the declared HOME chain to completion: every module at its safe end.

    A row that injects a stuck cylinder needs the cylinder to have somewhere
    to go. A cylinder already at its target completes at once, stuck or not -
    which is right - so a row that follows an abort, which leaves the press
    wherever it stopped, must start from home, as a TC3 station would.
    """
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_HOME)
    command(comm, mailbox.START)
    homed, _ = await_unit(comm, lambda o: o["Complete"] != 0 and o["Running"] == 0,
                          settle)
    command(comm, mailbox.STOP)
    command(comm, mailbox.OPERATOR_RESET)
    return homed


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
    write(comm, TWO_HAND, 0)      # released: start_cycle presses it
    _idle(comm, settle)

    # 1 - a full AUTO cycle.
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    base = unit_surface(comm)
    start_cycle(comm, settle)
    observed, elapsed = await_unit(
        comm, lambda o: base is not None and o["CycleCount"] > base["CycleCount"], settle)
    chart = chart_surface(comm)
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

    # 2 - two-hand released at the door close: TC3's N180 abandons it.
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    base = unit_surface(comm)
    start_cycle(comm, settle)
    # Released during the transfer settle (a declared 200 ms window) rather
    # than during the door close itself, which is four scans wide. Racing a
    # 40 ms window would make this row flaky rather than wrong.
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, TWO_HAND, 0)
    abandoned, elapsed = await_unit(
        comm, lambda o: base is not None and o["ReportedCount"] > base["ReportedCount"],
        settle)
    rows.append(row(
        "two_hand_released_at_the_door_close_abandons_it",
        "released at the close: one LOW warning (TWO_HAND_RELEASED) from the "
        "Unit itself, and no Error",
        abandoned, elapsed,
        abandoned is not None and base is not None
        and abandoned["ReportedReason"] == R["TWO_HAND_RELEASED"]
        and abandoned["ReportedSource"] == 0
        and abandoned["ReportedCount"] == base["ReportedCount"] + 1
        and abandoned["Error"] == 0,
    ))

    # 3 - the abandoned cycle recovers to the start and waits for a fresh press.
    back, elapsed = await_unit(comm, lambda o: o["Step"] == 100, settle)
    time.sleep(0.25)
    resting = unit_surface(comm)
    rows.append(row(
        "the_abandoned_cycle_waits_for_a_fresh_start",
        "the door reopens, the part slides out, and the chain waits at N100 "
        "with the start latch dropped - it does not restart by itself",
        resting, elapsed,
        back is not None and resting is not None and resting["Step"] == 100
        and resting["StartLatched"] == 0 and resting["Error"] == 0,
    ))

    # 4 - an awaited child's fault is adopted first-out, verbatim, and stops the chain.
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    write(comm, FAULT["PartSlide"], 1)
    start_cycle(comm, settle)
    faulted, elapsed = await_unit(comm, lambda o: o["Error"] != 0, settle)
    chart_fault, _ = await_chart(
        comm, lambda c: c["StallReason"] == R["CYL_NOT_EXTENDED"], settle)
    slide = module_surface(comm, "PartSlide")
    slide_index = [m.name for m in APP.modules].index("PartSlide") + 1
    # The child's live ErrorID is deliberately NOT the place to check "verbatim":
    # adopting releases the child (Execute drops) so it resets to READY, which is
    # the behaviour that makes the fault clearable at all. What must hold is that
    # the parent republished the child's own first-out code rather than inventing
    # one, that it names which child it came from, and that the child was freed.
    rows.append(row(
        "awaited_child_fault_adopted_first_out",
        "the unit adopts the child's first-out verbatim, names the source, "
        "stops on that step, and releases the child",
        {"unit": faulted,
         "child_error_id_after_release": None if slide is None else slide["ErrorID"],
         "child_exec_state": None if slide is None else slide["OutImm_ExecState"],
         "stall_reason": None if chart_fault is None else chart_fault["StallReason"]},
        elapsed,
        faulted is not None and slide is not None
        and faulted["Error"] != 0
        and faulted["ErrorID"] == R["CYL_NOT_EXTENDED"]
        and faulted["ErrorSource"] == slide_index
        and faulted["Step"] == 150
        and faulted["Running"] == 0
        and chart_fault is not None
        and chart_fault["StallReason"] == R["CYL_NOT_EXTENDED"]
        and slide["Execute"] == 0,
    ))

    # 5 - restart by re-issue after clearing the fault.
    write(comm, FAULT["PartSlide"], 0)
    command(comm, mailbox.STOP)
    command(comm, mailbox.OPERATOR_RESET)
    time.sleep(min(settle, 0.15))
    command(comm, mailbox.START)
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
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    start_cycle(comm, settle)
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, FAULT["PressRam"], 1)
    reported, elapsed = await_unit(comm, lambda o: o["Step"] == 210, settle)
    chart_dec = chart_surface(comm)
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
        and reported["ReportedReason"] == R["CYL_NOT_EXTENDED"]
        and reported["ReportedCount"] >= 1,
    ))

    # 7 - the chain waits on the decision without faulting, and the stall reason says so.
    # Each structure is read coherently, but a unit read and a chart read are two
    # separate requests and can land on different scans - single-request coherence
    # buys a coherent structure, not a coherent pair. Wait for the steady state.
    waiting, _ = await_unit(
        comm, lambda o: o["DecisionId"] == demo.DECISION_PRESS_NOT_REACHED, settle)
    chart_wait, _ = await_chart(
        comm, lambda c: c["StallReason"] == R["WAIT_DECISION"], settle)
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
    before_scrap = unit_surface(comm)
    command(comm, mailbox.DECISION_ANSWER, IntValue=1)
    scrapped, elapsed = await_unit(
        comm, lambda o: before_scrap is not None and o["ScrapCount"] > before_scrap["ScrapCount"],
        settle)
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
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    start_cycle(comm, settle)
    await_unit(comm, lambda o: o["Step"] == 170, settle)
    write(comm, FAULT["PressRam"], 1)
    await_unit(comm, lambda o: o["Step"] == 210, settle)
    write(comm, FAULT["PressRam"], 0)
    before_return = unit_surface(comm)
    command(comm, mailbox.DECISION_ANSWER, IntValue=2)
    returned, elapsed = await_unit(
        comm, lambda o: o["Step"] not in (210,) and o["DecisionId"] == 0, settle)
    rows.append(row(
        "decision_answer_return",
        "the other answer leaves the scrap count alone and rejoins the chain",
        returned, elapsed,
        returned is not None and before_return is not None
        and returned["ScrapCount"] == before_return["ScrapCount"]
        and returned["Error"] == 0,
    ))

    # 10 - MANUAL: one module, one catalogue command (TC3's ManualCommandTo).
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_MANUAL)
    before_door = module_surface(comm, "Door")
    answer = manual(comm, "Door", 2)                  # RETRACT: opening is always permitted
    door, elapsed = await_module(
        comm, "Door",
        lambda o: before_door is not None and o["DoneCount"] > before_door["DoneCount"]
        and o["Execute"] == 0, settle)
    rows.append(row(
        "manual_command",
        "MANUAL commands one module from its own catalogue; the command "
        "completes and releases",
        {"answer": answer,
         "door": None if door is None else {k: door[k] for k in (
             "RunCount", "DoneCount", "Execute", "ManualCmd", "OutImm_Pos", "Error")}},
        elapsed,
        answer["accepted"] and door is not None and before_door is not None
        and door["DoneCount"] == before_door["DoneCount"] + 1
        and door["Execute"] == 0 and door["ManualCmd"] == 0
        and door["OutImm_Pos"] == 0 and door["Error"] == 0,
    ))

    # 11 - HOME completes and stops, rather than looping.
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_HOME)
    command(comm, mailbox.START)
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
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    start_cycle(comm, settle)
    await_unit(comm, lambda o: o["Step"] not in (0,), settle)
    before_switch = unit_surface(comm)
    command(comm, mailbox.SET_MODE, IntValue=MODE_MANUAL)
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
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    start_cycle(comm, settle)
    await_unit(comm, lambda o: o["Running"] != 0, settle)
    command(comm, mailbox.STOP)
    aborted, elapsed = await_unit(comm, lambda o: o["Aborted"] != 0, settle)
    time.sleep(min(settle, 0.2))
    after_abort = unit_surface(comm)
    rows.append(row(
        "auto_abort_does_not_self_resume",
        "an aborted AUTO stands down and stays down while the request is held",
        after_abort, elapsed,
        aborted is not None and after_abort is not None
        and aborted["Aborted"] != 0 and after_abort["Running"] == 0,
    ))

    # 14 - a blocked condition publishes a named stall reason, not a fault.
    _idle(comm, settle)
    command(comm, mailbox.SET_MODE, IntValue=MODE_AUTO)
    write(comm, PART_PRESENT, 0)
    command(comm, mailbox.START)
    await_unit(comm, lambda o: o["Step"] == 100, settle)
    chart_block, elapsed = await_chart(
        comm, lambda c: c["StallReason"] == R["PART_NOT_PRESENT"], settle)
    blocked = unit_surface(comm)
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
    chart_final = chart_surface(comm)
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

        print_ready = fingerprint(comm, expect_serial=args.expect_serial)
        evidence["fingerprint"] = print_ready
        if not print_ready.get("passed"):
            evidence["error"] = "press-demo fingerprint failed; nothing was written"
            evidence["wrote"] = False
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1

        evidence["wrote"] = True
        evidence["write_surface"] = list(WRITABLE)
        # Seed above what this controller has already acknowledged, before the
        # first command. Starting from zero would have the mailbox refuse the
        # first request as a replay of one it answered on an earlier run.
        evidence["sequenceSeed"] = seed_sequence(comm)
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
