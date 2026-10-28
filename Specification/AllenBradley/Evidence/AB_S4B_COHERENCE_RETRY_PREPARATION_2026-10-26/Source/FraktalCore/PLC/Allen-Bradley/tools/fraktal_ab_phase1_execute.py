#!/usr/bin/env python3
"""Phase 1 on the controller: the alarm log, step conditions and diagnostics.

The ST model proves what the generated logic does given that it compiles;
this reads what the downloaded logic actually does. Each row drives the press
through the declared write surface only - simulated inputs, fault and hold
injections, and the command mailbox - and reads the result twice: off the
controller's own tags, and through the projection a client reads, so the
join between them is on the record too.

A fault injection is a cylinder that does not move (since the §8.8 reason
move): it is found the way a real stuck cylinder is, by the timeout at the end
that never reported. So the injected slide fault is TC3's CYL_NOT_EXTENDED and
names the slide's extended sensor - on the controller, not only on the model.
"""

from __future__ import annotations

import argparse
import datetime
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

SCHEMA = "fraktal.ab.phase1-on-controller"
SCHEMA_VERSION = 1

APP = px.APP
N = APP.name
ROOT = APP.name
# the slide and the ram are both EXTENDING where they are made to stick
DEVICE_FAULT = demo.REASONS["CYL_NOT_EXTENDED"]
EXTENDED_FB = 1 << __import__("fraktal_ab_library").CYLINDER.io_roles.index("extendedFb")
ACTIVE, RING = gen.alarm_active_tag(APP), gen.alarm_ring_tag(APP)


def read_log(comm: Any) -> tuple[dict | None, dict | None]:
    return (px.read_layout(comm, ACTIVE, gen.alarm_active_members()),
            px.read_layout(comm, RING, gen.alarm_ring_members()))


def document(comm: Any) -> dict[str, Any]:
    return projection.read_document(comm)["values"]


def utc_today() -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.year * 10000 + now.month * 100 + now.day


def since_delta_s(iso: Any) -> float | None:
    """How far a published onset is from this host's clock, in seconds."""
    if not isinstance(iso, str) or not iso:
        return None
    stamp = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return round((datetime.datetime.now(datetime.timezone.utc) - stamp)
                 .total_seconds(), 3)


def start_conditions(comm: Any, part: int, air: int, two_hand: int) -> None:
    px.write(comm, px.PART_PRESENT, part)
    px.write(comm, px.AIR_OK, air)
    px.write(comm, px.TWO_HAND, two_hand)


def run(comm: Any, settle: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ack = parity.ack(settle)
    parity.select(comm, "ST")

    # --- 1. What N100 waits for, and that the record is the step's own -----
    px._idle(comm, settle)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    start_conditions(comm, part=0, air=1, two_hand=0)
    px.command(comm, mailbox.START, settle=ack)
    chart, elapsed = px.await_chart(
        comm, lambda c: c["ActiveStepNumber"] == 100, settle)
    time.sleep(0.1)
    chart = px.read_chart(comm)
    values = document(comm)
    conds = [(values.get(f"{ROOT}/CurrentStep/Conds[{i}]/Label"),
              values.get(f"{ROOT}/CurrentStep/Conds[{i}]/Ok")) for i in (1, 2, 3, 4)]
    rows.append(px.row(
        "conditions_at_n100",
        "waiting at N100 with part absent, air ok, two-hand released: the step "
        "records [0, 1, 0] and the client reads TC3's three labels with them",
        {"condOk": None if chart is None else chart["CondOk"][:4],
         "activeStep": None if chart is None else chart["ActiveStepNumber"],
         "published": conds},
        elapsed,
        chart is not None and chart["CondOk"][:3] == [0, 1, 0]
        and conds[:3] == [("project.condition.partPresent", False),
                          ("project.condition.airPressureOk", True),
                          ("project.condition.twoHandStart", False)]
        and conds[3] == ("", False),
    ))
    px.write(comm, px.PART_PRESENT, 1)
    chart, elapsed = px.await_chart(comm, lambda c: c["CondOk"][0] == 1, settle)
    unit = px.read_unit(comm)
    rows.append(px.row(
        "a_condition_follows_its_input",
        "a part arriving turns record 1 on; two-hand still released holds N100",
        {"condOk": None if chart is None else chart["CondOk"][:3],
         "step": None if unit is None else unit["Step"]},
        elapsed,
        chart is not None and chart["CondOk"][:3] == [1, 1, 0]
        and unit is not None and unit["Step"] == 100,
    ))

    # --- 2. An adopted fault is a blocking MANUAL_RESET alarm ---------------
    px.home(comm, settle)      # the slide must have somewhere to go
    active0, ring0 = read_log(comm)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    start_conditions(comm, part=1, air=1, two_hand=0)
    px.write(comm, px.FAULT["PartSlide"], 1)
    px.start_cycle(comm, settle)
    unit, elapsed = px.await_unit(comm, lambda u: u["Error"] != 0, settle)
    active, _ = read_log(comm)
    values = document(comm)
    slot = (active or {}).get("FaultEvt", 0) - 1
    source = gen.module_source(APP, "PartSlide")
    since = values.get(f"{ROOT}/Status/Diagnostic/Since")
    observed = {
        "unit": None if unit is None else {k: unit[k] for k in (
            "Error", "ErrorID", "ErrorSource", "DiagReason", "DiagIoRoles")},
        "slot": slot,
        "event": None if active is None or slot < 0 else {
            c: active[f"Act{c}"][slot] for c, _ in gen.ALARM_COLUMNS},
        "blocking": None if active is None else active["Blocking"],
        "published": {k: values.get(f"{ROOT}/{k}") for k in (
            "Status/Diagnostic/ReasonCode", "Status/Diagnostic/Description",
            "Status/Diagnostic/IoTag", "AlarmLog/Blocking")},
        "publishedEvent": {k: values.get(f"{ROOT}/AlarmLog/Active[{slot + 1}]/{k}")
                           for k in ("ReasonCode", "Description", "SourcePath",
                                     "ResetClass", "ComeAt", "IoTag")},
        "sinceMinusHostSeconds": since_delta_s(since),
    }
    event = observed["event"] or {}
    rows.append(px.row(
        "adopted_fault_raises_a_blocking_manual_alarm",
        "the slide sticks and times out extending: one MANUAL_RESET alarm "
        "sourced to the slide, dated today, blocking; the Unit's diagnostic is "
        "TC3's CYL_NOT_EXTENDED and names the slide's extended sensor",
        observed, elapsed,
        unit is not None and unit["Error"] == 1 and unit["DiagReason"] == DEVICE_FAULT
        and active is not None and active["Blocking"] == 1
        and active["NActive"] == (active0 or {}).get("NActive", 0) + 1
        and event.get("State") == gen.ALARM_OPEN
        and event.get("ReasonCode") == DEVICE_FAULT
        and event.get("ResetClass") == gen.RESET_MANUAL
        and event.get("SourceModuleId") == source + 1
        and event.get("ComeDate") == utc_today()
        and event.get("IoRoles") == EXTENDED_FB
        and observed["published"]["Status/Diagnostic/Description"]
        == f"std.reason.{DEVICE_FAULT}"
        and observed["published"]["Status/Diagnostic/IoTag"] == "_101B301A"
        and observed["publishedEvent"]["IoTag"] == "_101B301A"
        and observed["publishedEvent"]["SourcePath"] == f"{ROOT}.PartSlide"
        and observed["sinceMinusHostSeconds"] is not None,
    ))

    # --- 3. START is refused while it waits for a reset ---------------------
    px.write(comm, px.FAULT["PartSlide"], 0)
    answer = px.command(comm, mailbox.START, settle=ack)
    report = px.read_layout(comm, gen.release_report_tag(APP), gen.release_report_members())
    listed = ([] if report is None else
              [(report["Key"][i], report["Kind"][i]) for i in range(report["Count"])])
    blocked = (mailbox._key(APP, gen.MANUAL_RESET_KEY), gen.RELEASE_KINDS["ALARM"])
    rows.append(px.row(
        "start_refused_while_an_alarm_waits",
        "§8.3(b): START is refused, and its release report (TC3's) lists the "
        "unreset alarm beside the Unit's own fault; the refusal names the first",
        {"answer": answer, "report": listed, "expected": blocked}, 0.0,
        answer["accepted"] is False and blocked in listed
        and answer["diagnosticKey"] == (listed[0][0] if listed else None),
    ))

    # --- 4. The operator reset closes it into the ring ----------------------
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    active, elapsed = px.await_unit(comm, lambda u: u["Error"] == 0, settle)
    time.sleep(0.1)
    active, ring = read_log(comm)
    unit = px.read_unit(comm)
    head = (active or {}).get("RingHead", 0) - 1
    entry = {} if ring is None or head < 0 else {
        c: ring[f"Ring{c}"][head] for c, _ in gen.ALARM_COLUMNS}
    rows.append(px.row(
        "reset_closes_it_into_the_ring",
        "one operator reset: the event is closed into the ring with its gone "
        "time, nothing blocks, the Unit has no diagnostic - and, as TC3's "
        "OperatorReset releases its run command, the press is not running",
        {"ringHead": None if active is None else active["RingHead"],
         "entry": entry, "blocking": None if active is None else active["Blocking"],
         "diagReason": None if unit is None else unit["DiagReason"],
         "running": None if unit is None else unit["Running"]},
        elapsed,
        active is not None and active["Blocking"] == 0
        and active["NActive"] == (active0 or {}).get("NActive", 0)
        and active["RingHead"] == ((active0 or {}).get("RingHead", 0)
                                   % gen.ALARM_RING) + 1
        and entry.get("State") == gen.ALARM_CLOSED
        and entry.get("ReasonCode") == DEVICE_FAULT
        and entry.get("GoneDate") == utc_today()
        and unit is not None and unit["DiagReason"] == 0 and unit["Running"] == 0,
    ))
    answer = px.command(comm, mailbox.START, settle=ack)
    rows.append(px.row(
        "start_accepted_after_the_reset",
        "the same START is accepted once nothing blocks",
        answer, 0.0, answer["accepted"] is True,
    ))
    px.command(comm, mailbox.STOP, settle=ack)

    # --- 5. A report is an occurrence, never a standing fault --------------
    px._idle(comm, settle)
    active0, ring0 = read_log(comm)
    unit0 = px.read_unit(comm)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    start_conditions(comm, part=1, air=1, two_hand=0)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == 170, settle)
    px.write(comm, px.FAULT["PressRam"], 1)
    unit, elapsed = px.await_unit(comm, lambda u: u["Step"] == 210, settle)
    time.sleep(0.1)
    active, ring = read_log(comm)
    unit = px.read_unit(comm)
    values = document(comm)
    head = (active or {}).get("RingHead", 0) - 1
    entry = {} if ring is None or head < 0 else {
        c: ring[f"Ring{c}"][head] for c, _ in gen.ALARM_COLUMNS}
    source = gen.module_source(APP, "PressRam")
    rows.append(px.row(
        "report_is_an_occurrence",
        "the ram failing at N200 is reported, not adopted: one closed AUTO_RESET "
        "ring entry sourced to the ram, nothing blocks, and the Unit's own "
        "diagnostic stays clear while the operator decides",
        {"entry": entry,
         "reported": None if unit is None or unit0 is None else
         unit["ReportedCount"] - unit0["ReportedCount"],
         "blocking": None if active is None else active["Blocking"],
         "unit": None if unit is None else {k: unit[k] for k in (
             "Step", "Error", "DiagReason", "ReportedReason", "ReportedSource")},
         "publishedReason": values.get(f"{ROOT}/Status/Diagnostic/ReasonCode"),
         "publishedEntry": {k: values.get(f"{ROOT}/AlarmLog/Ring[{head + 1}]/{k}")
                            for k in ("ReasonCode", "SourcePath", "ResetClass")}},
        elapsed,
        unit is not None and unit["Step"] == 210 and unit["Error"] == 0
        and unit["DiagReason"] == 0 and unit["ReportedSource"] == source
        and active is not None and active["Blocking"] == 0
        and active["RingHead"] == ((active0 or {}).get("RingHead", 0)
                                   % gen.ALARM_RING) + 1
        and entry.get("ResetClass") == gen.RESET_AUTO
        and entry.get("ReasonCode") == DEVICE_FAULT
        and entry.get("SourceModuleId") == source + 1
        and entry.get("ComeTime") == entry.get("GoneTime")
        and values.get(f"{ROOT}/Status/Diagnostic/ReasonCode") == 0,
    ))
    px.write(comm, px.FAULT["PressRam"], 0)
    px.command(comm, mailbox.DECISION_ANSWER, settle=ack, IntValue=1)
    px.await_unit(comm, lambda u: u["Step"] == 100, settle * 2)
    px.command(comm, mailbox.STOP, settle=ack)
    px._idle(comm, settle)

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
        header = projection.read_document(comm)["values"]
        evidence["wrote"] = True
        evidence["write_surface"] = list(px.WRITABLE) + ["mailbox"]
        evidence["sequence_seed"] = px.seed_sequence(comm)
        try:
            evidence["result"] = run(comm, args.settle)
        finally:
            evidence["disarm"] = px.disarm(comm)
        evidence["projected_root"] = bool(header)
    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values()))
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
