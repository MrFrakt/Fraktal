#!/usr/bin/env python3
"""Phase 3's first step on the controller: TC3's reasons, watchdog and rollup.

Three things the model proved and the controller has to show:

* a stuck cylinder is found by its timeout, raised as TC3's CYL_NOT_EXTENDED
  and naming the sensor that never reported - the Phase 1 gap, now reachable
  through the declared write surface because a fault injection holds the
  plant still;
* a held child rolls up into the Unit's own diagnostic (TC3 _M_RollupHold),
  and a hold is a declared wait, so the stall watchdog stays disarmed;
* a step that waits unheld past StallTime is timed out, and the Unit says
  STEP_STALLED, LOW, pending - not a fault;
* a dwell released part-way stands still and, pressed again, presses the
  part for the declared dwell in total (TC3's N220).

The last row waits a real StallTime (30 s), because the watchdog is a
controller value this harness does not write.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection

SCHEMA = "fraktal.ab.phase3-reasons-on-controller"
SCHEMA_VERSION = 1

APP = px.APP
ROOT = APP.name
R = demo.REASONS


def document(comm: Any) -> dict[str, Any]:
    return projection.read_document(comm)["values"]


def diag(values: dict[str, Any], base: str = ROOT) -> dict[str, Any]:
    return {k: values.get(f"{base}/Status/Diagnostic/{k}")
            for k in ("ReasonCode", "Description", "IoTag", "IoAddress", "Since")}


def observe_stall(comm: Any, settle: float):
    """Include command/setup reads while the PLC's watchdog is already running."""
    started = time.monotonic()
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == 100, settle)
    early = document(comm).get(f"{ROOT}/CurrentStepTimedOut")
    unit, _ = px.await_unit(comm, lambda u: u["StepTimedOut"] != 0,
                            APP.stall_time_ms / 1000.0 + settle)
    return unit, (time.monotonic() - started) * 1000.0, early


def run(comm: Any, settle: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ack = parity.ack(settle)
    parity.select(comm, "ST")

    # --- 0. the part-present sensor is a module, and follows its source ----
    px._idle(comm, ack)
    observed = {}
    for part in (0, 1, 0):
        px.write(comm, px.PART_PRESENT, part)
        sensor, _ = px.await_module(
            comm, "PartPresentSensor",
            lambda c, p=part: c["OutImm_Value"] == p and c["ModuleScan"] > 0, settle)
        observed[f"part={part}"] = None if sensor is None else {
            k: sensor[k] for k in ("OutImm_Value", "OutImm_Quality", "Error")}
    values = document(comm)
    base = f"{ROOT}/PartPresentSensor"
    published = {k: values.get(f"{base}/Status/{k}")
                  for k in ("TypeKey", "DisplayNameKey", "State", "FaultActive")}
    rows.append(px.row(
        "the_part_present_sensor_follows_its_source",
        "TC3's FB_DigitalInputCM on the controller: Value follows the part "
        "stimulus both ways at good Quality, published as a digital input",
        {"sensor": observed, "published": published}, 0.0,
        observed.get("part=1") == {"OutImm_Value": 1, "OutImm_Quality": 1, "Error": 0}
        and observed.get("part=0", {}).get("OutImm_Value") == 0
        and published["TypeKey"] == "std.moduleType.digitalInput"
        and published["DisplayNameKey"] == "project.module.partpresentsensor"
        and published["FaultActive"] is False,
    ))

    # --- 1. a stuck slide times out extending, and names its sensor --------
    px.home(comm, settle)      # the slide must have somewhere to go
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.write(comm, px.FAULT["PartSlide"], 1)
    px.start_cycle(comm, settle)
    started = time.monotonic()
    unit, _ = px.await_unit(comm, lambda u: u["Error"] != 0, settle)
    elapsed = (time.monotonic() - started) * 1000.0
    slide = px.read_module(comm, "PartSlide")
    values = document(comm)
    unit_diag, slide_diag = diag(values), diag(values, f"{ROOT}/PartSlide")
    # The fault's own slot, as the controller records it: since §8.12 the
    # active list can hold other events (a standing health event among them),
    # so "the first open slot" is no longer the fault.
    log = px.read_layout(comm, gen.alarm_active_tag(APP), gen.alarm_active_members())
    slot = 0 if log is None else log["FaultEvt"]
    event = {k: values.get(f"{ROOT}/AlarmLog/Active[{slot}]/{k}")
             for k in ("ReasonCode", "IoTag", "SourcePath", "Description")}
    rows.append(px.row(
        "a_stuck_slide_times_out_and_names_its_sensor",
        "held still by the fault injection, the slide times out extending: "
        "TC3's CYL_NOT_EXTENDED on the Unit, the slide and the alarm, naming "
        "_101B301A, after the declared 500 ms and not before",
        {"unit": None if unit is None else {k: unit[k] for k in (
            "Error", "ErrorID", "ErrorSource", "DiagReason", "DiagIoRoles")},
         "slidePosition": None if slide is None else slide["OutImm_Pos"],
         "unitDiagnostic": unit_diag, "event": event, "elapsedMs": round(elapsed)},
        elapsed,
        unit is not None and unit["ErrorID"] == R["CYL_NOT_EXTENDED"]
        and unit_diag["ReasonCode"] == R["CYL_NOT_EXTENDED"]
        and unit_diag["Description"] == f"std.reason.{R['CYL_NOT_EXTENDED']}"
        and unit_diag["IoTag"] == "_101B301A"
        and event["IoTag"] == "_101B301A" and event["SourcePath"] == f"{ROOT}.PartSlide"
        and elapsed >= 500,
    ))
    px.write(comm, px.FAULT["PartSlide"], 0)
    px._idle(comm, ack)

    # --- 2. a held child rolls up, and a hold is not a stall ----------------
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.write(comm, px.HOLD["PressRam"], 1)
    px.start_cycle(comm, settle)
    unit, elapsed = px.await_unit(
        comm, lambda u: u["DiagReason"] == R["INTERLOCK_DROPPED"], settle)
    values = document(comm)
    rows.append(px.row(
        "a_held_child_rolls_up_into_the_unit",
        "the ram held at N110: the Unit's own diagnostic is the ram's "
        "INTERLOCK_DROPPED (TC3 _M_RollupHold), no error, not timed out",
        {"unit": None if unit is None else {k: unit[k] for k in (
            "Step", "Error", "DiagReason", "StallMs", "StepTimedOut")},
         "unitDiagnostic": diag(values),
         "timedOut": values.get(f"{ROOT}/CurrentStepTimedOut")},
        elapsed,
        unit is not None and unit["Step"] == 110 and unit["Error"] == 0
        and unit["DiagReason"] == R["INTERLOCK_DROPPED"] and unit["StallMs"] == 0
        and diag(values)["ReasonCode"] == R["INTERLOCK_DROPPED"]
        and values.get(f"{ROOT}/CurrentStepTimedOut") is False,
    ))
    px.write(comm, px.HOLD["PressRam"], 0)
    px._idle(comm, ack)

    # --- 2b. air lost mid-stroke holds the cylinder; air back resumes it ---
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.start_cycle(comm, settle)
    # Withdrawn during the declared 200 ms settle, not racing a four-scan
    # stroke: the door then starts its close at N180 with no air.
    px.await_unit(comm, lambda u: u["Step"] == 170, settle)
    px.write(comm, px.AIR_OK, 0)
    unit, elapsed = px.await_unit(
        comm, lambda u: u["DiagReason"] == R["INTERLOCK_DROPPED"], settle)
    time.sleep(0.8)                       # longer than the door's 500 ms timeout
    door = px.read_module(comm, "Door")
    monitor = px.read_module(comm, "AirPressureMonitor")
    unit = px.read_unit(comm)
    held = {"unit": None if unit is None else {k: unit[k] for k in (
                "Step", "Error", "DiagReason", "StepTimedOut")},
            "door": None if door is None else {k: door[k] for k in (
                "OutImm_Held", "OutImm_Reason", "Error", "OutImm_Pos")},
            "monitor": None if monitor is None else {k: monitor[k] for k in (
                "OutImm_PressureOk", "OutImm_LowPressure", "OutImm_OperatingPressure")}}
    px.write(comm, px.AIR_OK, 1)
    resumed, _ = px.await_unit(comm, lambda u: u["Step"] > 180, settle)
    rows.append(px.row(
        "air_lost_mid_stroke_holds_and_resumes",
        "TC3's SetAreaSafe: the door holds on INTERLOCK_DROPPED when air goes, "
        "does not time out or fault while held, the press reports it, and the "
        "stroke completes when air returns",
        {"held": held, "resumedTo": None if resumed is None else resumed["Step"]},
        elapsed,
        door is not None and door["OutImm_Held"] == 1 and door["Error"] == 0
        and door["OutImm_Reason"] == R["INTERLOCK_DROPPED"]
        and unit is not None and unit["Error"] == 0
        and unit["DiagReason"] == R["INTERLOCK_DROPPED"]
        and monitor is not None and monitor["OutImm_PressureOk"] == 0
        and monitor["OutImm_LowPressure"] == 1
        and unit["Step"] == 180
        and resumed is not None and resumed["Step"] > 180,
    ))
    px.write(comm, px.PART_PRESENT, 0)
    px.await_unit(comm, lambda u: u["Step"] == 100, settle * 2)
    px._idle(comm, ack)

    # --- 2c. released mid-dwell, the press finishes only what remained ----
    # The parity walk releases as soon as the ram presses, so its dwell is
    # paused from the first scan. This releases once some dwell has run - the
    # operator's case - which is the only one that shows the remainder.
    dwell = parity.DWELL
    dwell_ms = (px.read_layout(comm, px.CFG, APP.records[0].members) or {}).get(
        dwell.duration_member)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    for tag in (px.PART_PRESENT, px.AIR_OK):
        px.write(comm, tag, 1)
    px.start_cycle(comm, settle)
    px.await_chart(comm, lambda c: c["ActiveStepNumber"] == dwell.number
                   and c["DelayMs"] > 0, settle)
    px.write(comm, px.TWO_HAND, 0)
    paused, elapsed = px.await_chart(
        comm, lambda c: c["StallReason"] == R["WAIT_CONDITION"], settle)
    time.sleep(parity.DWELL_PAUSE_S)
    still = px.read_chart(comm)
    values = document(comm)
    unit = px.read_unit(comm)
    px.write(comm, px.TWO_HAND, 1)
    resumed, _ = px.await_unit(comm, lambda u: u["Step"] != dwell.number, settle)
    after = px.read_chart(comm)
    ran = None if paused is None else paused["DelayMs"]
    record = {k: values.get(f"{ROOT}/CurrentStep/Conds[1]/{k}") for k in ("Label", "Ok")}
    rows.append(px.row(
        "a_release_mid_dwell_finishes_only_what_remained",
        "TC3's N220: released part-way through the dwell, the dwell stands "
        "still on its named condition with no fault; past its expected time it "
        "is reported stalled; pressed again, the part is pressed for the "
        "declared dwell in total, not the dwell plus the pause",
        {"dwellMs": dwell_ms, "pausedAtMs": ran,
         "stillAtMs": None if still is None else still["DelayMs"],
         "publishedCondition": record,
         "unit": None if unit is None else {k: unit[k] for k in (
             "Step", "Error", "DiagReason")},
         "resumedTo": None if resumed is None else resumed["Step"],
         "servedMs": None if after is None else after["DelayMs"]},
        elapsed,
        dwell_ms is not None and ran is not None and 0 < ran < dwell_ms
        and still is not None and still["DelayMs"] == ran
        and record == {"Label": "project.condition.twoHandHeldDuringPress", "Ok": False}
        and unit is not None and unit["Step"] == dwell.number
        and unit["Error"] == 0 and unit["DiagReason"] == R["STEP_STALLED"]
        and resumed is not None and resumed["Step"] != dwell.number
        and after is not None
        and dwell_ms <= after["DelayMs"] < dwell_ms + APP.task_period_ms,
    ))
    px.write(comm, px.PART_PRESENT, 0)
    px.await_unit(comm, lambda u: u["Step"] == 100, settle * 2)
    px._idle(comm, ack)

    # --- 3. a real stall: N100 waits past StallTime -------------------------
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    px.write(comm, px.PART_PRESENT, 0)
    px.write(comm, px.AIR_OK, 1)
    # START and a two-hand press with no part: TC3's latch refuses it, so
    # N100 waits - on the part, and then on a fresh press.
    stall_s = APP.stall_time_ms / 1000.0
    unit, elapsed, early = observe_stall(comm, settle)
    values = document(comm)
    rows.append(px.row(
        "a_step_that_waits_past_stall_time_is_stalled",
        "N100 waiting for a part: not timed out while it merely waits, then at "
        "StallTime timed out, with the Unit saying STEP_STALLED, LOW, no error",
        {"timedOutEarly": early,
         "unit": None if unit is None else {k: unit[k] for k in (
             "Step", "Error", "DiagReason", "StallMs", "StepTimedOut")},
         "unitDiagnostic": diag(values),
         "timedOut": values.get(f"{ROOT}/CurrentStepTimedOut"),
         "secondsToStall": round(elapsed / 1000.0, 2)},
        elapsed,
        early is False and unit is not None and unit["StepTimedOut"] == 1
        and unit["StallMs"] >= APP.stall_time_ms
        and unit["Error"] == 0 and unit["DiagReason"] == R["STEP_STALLED"]
        and values.get(f"{ROOT}/CurrentStepTimedOut") is True
        and diag(values)["Description"] == f"std.reason.{R['STEP_STALLED']}"
        and elapsed / 1000.0 >= stall_s - 1.0,
    ))
    px.write(comm, px.PART_PRESENT, 1)
    time.sleep(0.5)
    waiting = px.read_unit(comm)
    rows.append(px.row(
        "a_press_before_the_part_never_starts_the_stroke",
        "TC3's start latch: the part arriving after the two-hand press does "
        "not start the stroke - N100 still waits, nothing latched",
        None if waiting is None else {k: waiting[k] for k in (
            "Step", "StartLatched", "Running")},
        500.0,
        waiting is not None and waiting["Step"] == 100
        and waiting["StartLatched"] == 0 and waiting["Running"] == 1,
    ))
    px.two_hand_press(comm, settle)
    unit, elapsed = px.await_unit(comm, lambda u: u["Step"] != 100, settle)
    rows.append(px.row(
        "a_stall_clears_when_the_step_moves",
        "a fresh press with the part there: the step moves, the stall and its "
        "diagnostic clear",
        None if unit is None else {k: unit[k] for k in (
            "Step", "StepTimedOut", "DiagReason")},
        elapsed,
        unit is not None and unit["Step"] != 100 and unit["StepTimedOut"] == 0
        and unit["DiagReason"] != R["STEP_STALLED"],
    ))
    px.write(comm, px.PART_PRESENT, 0)
    px.await_unit(comm, lambda u: u["Step"] == 100, settle * 2)
    px.command(comm, mailbox.STOP, settle=ack)
    px._idle(comm, ack)

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
            evidence["disarm"] = px.disarm(comm)
    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values()))
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
