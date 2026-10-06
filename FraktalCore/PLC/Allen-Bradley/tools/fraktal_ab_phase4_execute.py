#!/usr/bin/env python3
"""Phase 4a on the controller: TC3's manual commands and collision interlocks.

What the model proved and the controller has to show:

* MANUAL has no sequence: Start is refused there by TC3's own reason, and a
  module takes a command from its catalogue directly, which completes and
  releases;
* the press's directional permits (TC3's SetDirectionalPermits): the door does
  not close over a slide that is outside, the slide does not move under a
  closed door, and the ram names its first missing condition - each a HOLD
  on INTERLOCK_DROPPED, published with the interlock's own text, never a
  fault, and released by itself when the condition returns;
* a manual command outside MANUAL, to a module that takes none, or outside
  the catalogue is refused by name;
* the published tree carries each module's catalogue, as the HMI renders it;
* (4b) TC3's Core §7.8 release reports, read where the HMI reads them: START
  refused names its reason and answers with the full list, the start report
  lists every reason at once, a manual query names the blocked direction's
  interlock and its module, and a reset with nothing to reset says so.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest
import fraktal_ab_press_demo as demo
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity
import fraktal_ab_projection as projection

SCHEMA = "fraktal.ab.phase4-manual-on-controller"
SCHEMA_VERSION = 1

APP = px.APP
ROOT = APP.name
R = demo.REASONS
EXTEND, RETRACT = 1, 2


def document(comm: Any) -> dict[str, Any]:
    return projection.read_document(comm)["values"]


def key(portable: str) -> int:
    return manifest.numeric_key(APP, portable)


def entry_conditions(mode, app=APP):
    """The declaration owns scope; a fixture must not repeat the old policy."""
    return [(permit.key, gen.RELEASE_KINDS["INTERLOCK"])
            for permit in app.start_permits if not permit.modes or mode in permit.modes]


def described(values: dict[str, Any], module: str) -> dict[str, Any]:
    base = f"{ROOT}/{module}/Status/Diagnostic"
    return {k: values.get(f"{base}/{k}") for k in ("ReasonCode", "Description")}


def report(values: dict[str, Any]) -> list[tuple]:
    """The HmiResponse.Report the HMI reads: (text, reason, owner, kind)."""
    base = f"{ROOT}/HmiResponse/Report"
    count = values.get(f"{base}/Count") or 0
    return [tuple(values.get(f"{base}/Reasons/Reasons[{i}]/{leaf}")
                  for leaf in ("Description", "ReasonCode", "SourcePath", "Kind"))
            for i in range(1, count + 1)]


def report_released(values: dict[str, Any]) -> Any:
    return values.get(f"{ROOT}/HmiResponse/Report/Released")


def settle_module(comm: Any, module: str, settle: float) -> dict[str, int] | None:
    """The module once it has finished whatever it was asked."""
    observed, _ = px.await_module(
        comm, module, lambda c: c["Busy"] == 0 and c["Execute"] == 0, settle)
    return observed


def run(comm: Any, settle: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ack = parity.ack(settle)
    for tag in (px.PART_PRESENT, px.AIR_OK, px.TWO_HAND):
        px.write(comm, tag, 1)
    px.home(comm, settle)                      # ram up, door open, slide outside
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)

    # --- 1. MANUAL has no sequence ----------------------------------------------
    start = px.command(comm, mailbox.START, settle=ack)
    unit = px.read_unit(comm)
    rows.append(px.row(
        "start_has_nothing_to_run_in_manual",
        "START in MANUAL is refused by TC3's reason, manualHasNoAutoSequence, "
        "and nothing runs",
        {"answer": start, "running": None if unit is None else unit["Running"]},
        0.0,
        not start["accepted"]
        and start["diagnosticKey"] == key(mailbox.MANUAL_HAS_NO_SEQUENCE_KEY)
        and unit is not None and unit["Running"] == 0,
    ))

    # --- 2. the catalogue is published ------------------------------------------
    values = document(comm)
    catalogue = {m: [(values.get(f"{ROOT}/{m}/Catalog[{i}]/Value"),
                      values.get(f"{ROOT}/{m}/Catalog[{i}]/Label")) for i in (1, 2)]
                 for m in ("PressRam", "Door", "PartSlide")}
    rows.append(px.row(
        "each_cylinder_publishes_its_catalogue",
        "TC3's catalogue on every cylinder: EXTEND 1 and RETRACT 2, with "
        "std.command labels; a sensor publishes none",
        {"cylinders": catalogue,
         "sensorCount": values.get(f"{ROOT}/PartPresentSensor/CatalogCount")},
        0.0,
        all(entries == [(EXTEND, "std.command.extend"), (RETRACT, "std.command.retract")]
            for entries in catalogue.values())
        and values.get(f"{ROOT}/PartPresentSensor/CatalogCount") == 0,
    ))

    # --- 3. the door does not close over a slide outside --------------------------
    answer = px.manual(comm, "Door", EXTEND, settle=ack)
    door, elapsed = px.await_module(comm, "Door", lambda c: c["OutImm_Held"] != 0, settle)
    time.sleep(0.8)                            # past the door's 500 ms timeout
    door = px.read_module(comm, "Door")
    held = described(document(comm), "Door")
    rows.append(px.row(
        "the_door_does_not_close_over_a_slide_outside",
        "a manual close with the slide outside is accepted and HELD on "
        "INTERLOCK_DROPPED, named doorCloseRequiresSlideInside, without moving "
        "and without timing out",
        {"answer": answer, "held": held,
         "door": None if door is None else {k: door[k] for k in (
             "Busy", "OutImm_Held", "Error", "OutImm_Pos", "Permit")}},
        elapsed,
        answer["accepted"] and door is not None and door["OutImm_Held"] == 1
        and door["Error"] == 0 and door["OutImm_Pos"] == 0
        and held == {"ReasonCode": R["INTERLOCK_DROPPED"],
                     "Description": "project.interlock.doorCloseRequiresSlideInside"},
    ))

    # --- 4. a busy module refuses another command; a reset releases it -----------
    busy = px.manual(comm, "Door", RETRACT, settle=ack)
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    released = settle_module(comm, "Door", settle)
    rows.append(px.row(
        "a_held_command_is_released_by_a_reset",
        "a second command to the held door is refused as busy; OPERATOR_RESET "
        "drops the held command rather than resuming it",
        {"busy": busy, "door": None if released is None else {k: released[k] for k in (
            "Busy", "Execute", "ManualCmd", "OutImm_Pos")}},
        0.0,
        not busy["accepted"] and busy["diagnosticKey"] == key(mailbox.MANUAL_BUSY_KEY)
        and released is not None and released["ManualCmd"] == 0
        and released["OutImm_Pos"] == 0,
    ))

    # --- 5. slide in, door closed, then the slide is held under the door ---------
    px.manual(comm, "PartSlide", EXTEND, settle=ack)
    settle_module(comm, "PartSlide", settle)
    px.manual(comm, "Door", EXTEND, settle=ack)
    closed = settle_module(comm, "Door", settle)
    px.manual(comm, "PartSlide", RETRACT, settle=ack)
    slide, elapsed = px.await_module(comm, "PartSlide",
                                     lambda c: c["OutImm_Held"] != 0, settle)
    held = described(document(comm), "PartSlide")
    px.manual(comm, "Door", RETRACT, settle=ack)
    resumed, _ = px.await_module(comm, "PartSlide",
                                 lambda c: c["OutImm_Pos"] == 0 and c["Busy"] == 0, settle)
    rows.append(px.row(
        "the_slide_waits_for_the_door_and_resumes_by_itself",
        "with the door closed (by a manual command, over the slide inside) the "
        "slide's way out is HELD, named slideOutsideRequiresDoorOpen; opening "
        "the door lets it finish without a fault",
        {"doorClosed": None if closed is None else closed["OutImm_Pos"], "held": held,
         "slideHeld": None if slide is None else slide["OutImm_Held"],
         "resumed": None if resumed is None else {k: resumed[k] for k in (
             "OutImm_Pos", "Error", "ManualCmd")}},
        elapsed,
        closed is not None and closed["OutImm_Pos"] == 100
        and slide is not None and slide["OutImm_Held"] == 1
        and held == {"ReasonCode": R["INTERLOCK_DROPPED"],
                     "Description": "project.interlock.slideOutsideRequiresDoorOpen"}
        and resumed is not None and resumed["Error"] == 0 and resumed["ManualCmd"] == 0,
    ))
    settle_module(comm, "Door", settle)

    # --- 6. the ram names its first missing condition -----------------------------
    px.manual(comm, "PressRam", EXTEND, settle=ack)
    ram, elapsed = px.await_module(comm, "PressRam", lambda c: c["OutImm_Held"] != 0, settle)
    first = described(document(comm), "PressRam")
    px.write(comm, px.AIR_OK, 0)
    px.await_module(comm, "AirPressureMonitor", lambda c: c["OutImm_PressureOk"] == 0, settle)
    time.sleep(0.1)
    then = described(document(comm), "PressRam")
    px.write(comm, px.AIR_OK, 1)
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    settle_module(comm, "PressRam", settle)
    rows.append(px.row(
        "the_ram_names_its_first_missing_condition",
        "with the guard open the ram's press is HELD on pressRequiresGuardClosed; "
        "air lost as well, it names air - TC3's first-out order",
        {"guardOpen": first, "airLost": then,
         "ramPos": None if ram is None else ram["OutImm_Pos"]},
        elapsed,
        ram is not None and ram["OutImm_Pos"] == 0
        and first["Description"] == "project.interlock.pressRequiresGuardClosed"
        and then["Description"] == "project.interlock.pressRequiresAirPressure",
    ))

    # --- 7. the refusals ------------------------------------------------------------
    sensor = px.manual(comm, "PartPresentSensor", 1, settle=ack)
    unknown = px.manual(comm, "Door", 3, settle=ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    auto = px.manual(comm, "Door", RETRACT, settle=ack)
    rows.append(px.row(
        "manual_commands_are_refused_by_name",
        "a module that takes no commands, a command outside the catalogue, and "
        "any manual command outside MANUAL are each refused with its reason",
        {"sensor": sensor, "unknown": unknown, "auto": auto},
        0.0,
        not sensor["accepted"] and sensor["diagnosticKey"] == key(mailbox.TARGET_KEY)
        and not unknown["accepted"]
        and unknown["diagnosticKey"] == key(mailbox.MANUAL_COMMAND_UNKNOWN_KEY)
        and not auto["accepted"]
        and auto["diagnosticKey"] == key(mailbox.MANUAL_MODE_REQUIRED_KEY),
    ))

    # --- 8. (4b) a START refused names its reason and carries the report ---
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    px.write(comm, px.AIR_OK, 0)
    px.await_module(comm, "AirPressureMonitor", lambda c: c["OutImm_PressureOk"] == 0, settle)
    time.sleep(0.1)
    refused = px.command(comm, mailbox.START, settle=ack)
    no_air = report(document(comm))
    px.write(comm, px.AIR_OK, 1)
    px.await_module(comm, "AirPressureMonitor", lambda c: c["OutImm_PressureOk"] == 1, settle)
    time.sleep(0.1)
    query = px.command(comm, mailbox.RELEASE_START, settle=ack)
    values = document(comm)
    clear = (report_released(values), report(values))
    started = px.command(comm, mailbox.START, settle=ack)
    air = ("project.condition.airPressureOk", R["PERMISSIVE_NOT_MET"], ROOT,
           gen.RELEASE_KINDS["INTERLOCK"])
    rows.append(px.row(
        "a_refused_start_explains_itself",
        "TC3's Start consumes its release report: without air START is refused "
        "naming airPressureOk (PERMISSIVE_NOT_MET, the Unit's, an interlock) and "
        "answers with that report; with air back the report is released and "
        "START is taken",
        {"refused": refused, "report": no_air, "query": query, "clear": clear,
         "started": started},
        0.0,
        not refused["accepted"] and refused["diagnosticKey"] == key(air[0])
        and no_air == [air] and query["accepted"] and clear == (True, [])
        and started["accepted"],
    ))
    px._idle(comm, ack)

    # --- 9. (4b) every reason at once -----------------------------------------------
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    px.command(comm, mailbox.STOP, settle=ack)              # Aborted: not ready
    px.write(comm, px.AIR_OK, 0)
    px.await_module(comm, "AirPressureMonitor", lambda c: c["OutImm_PressureOk"] == 0, settle)
    time.sleep(0.1)
    px.command(comm, mailbox.RELEASE_START, settle=ack)
    every = report(document(comm))
    px.write(comm, px.AIR_OK, 1)
    kind = gen.RELEASE_KINDS
    expected = [(mailbox.MANUAL_HAS_NO_SEQUENCE_KEY, kind["MODE"]),
                (gen.UNIT_NOT_READY_KEY, kind["MODE"]),
                *entry_conditions(px.MODE_MANUAL)]
    rows.append(px.row(
        "the_start_report_lists_every_reason",
        "MANUAL, aborted and without air: all missing reasons in order, "
        "including only entry conditions declared for MANUAL",
        every, 0.0,
        [(r[0], r[3]) for r in every] == expected,
    ))
    px._idle(comm, ack)

    # The requested Changeover exception must not remove the AUTO/HOME permit.
    px.write(comm, px.AIR_OK, 0)
    px.await_module(comm, "AirPressureMonitor", lambda c: c["OutImm_PressureOk"] == 0, settle)
    mode_reports = {}
    for mode in (px.MODE_MANUAL, demo.MODE_HOME, demo.MODE_AUTO, demo.MODE_CHANGEOVER):
        px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=mode)
        px.command(comm, mailbox.RELEASE_START, settle=ack)
        mode_reports[mode] = report(document(comm))
    air_key = "project.condition.airPressureOk"
    rows.append(px.row(
        "air_start_entry_is_scoped_by_mode",
        "the air Start reason follows the declared modes; cylinder pressure permits remain",
        mode_reports, 0.0,
        all(any(reason[0] == air_key for reason in mode_reports[mode])
            == any(reason[0] == air_key for reason in entry_conditions(mode))
            for mode in mode_reports),
    ))
    px.write(comm, px.AIR_OK, 1)
    px._idle(comm, ack)

    # --- 10. (4b) a manual query names the blocked direction --------------------------
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    blocked = px.command(comm, mailbox.RELEASE_MANUAL, settle=ack, TargetPath=f"{ROOT}.Door",
                         IntValue=EXTEND, **{mailbox.MANUAL_TARGET_MEMBER:
                                             mailbox.manual_target(APP, f"{ROOT}.Door")})
    door_close = report(document(comm))
    px.command(comm, mailbox.RELEASE_MANUAL, settle=ack, TargetPath=f"{ROOT}.Door",
               IntValue=RETRACT, **{mailbox.MANUAL_TARGET_MEMBER:
                                    mailbox.manual_target(APP, f"{ROOT}.Door")})
    values = document(comm)
    door_open = (report_released(values), report(values))
    rows.append(px.row(
        "a_manual_query_names_the_blocked_direction",
        "the door's close, asked about with the slide outside, is explained by "
        "doorCloseRequiresSlideInside (INTERLOCK_DROPPED, owned by Press.Door); "
        "its opening is released",
        {"answer": blocked, "close": door_close, "open": door_open},
        0.0,
        blocked["accepted"]
        and door_close == [("project.interlock.doorCloseRequiresSlideInside",
                            R["INTERLOCK_DROPPED"], f"{ROOT}.Door", kind["INTERLOCK"])]
        and door_open == (True, []),
    ))

    # --- 11. (4b) a reset with nothing to reset -----------------------------------------
    px.command(comm, mailbox.RELEASE_ACTION, settle=ack, IntValue=gen.GATED_ALARM_RESET)
    nothing = report(document(comm))
    rows.append(px.row(
        "a_reset_with_nothing_to_reset_says_so",
        "TC3's ReleaseReportAction for ALARM_RESET with no blocking alarm: "
        "noBlockingAlarm",
        nothing, 0.0,
        nothing == [(gen.NO_BLOCKING_ALARM_KEY, 0, ROOT, kind["OTHER"])],
    ))

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
