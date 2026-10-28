#!/usr/bin/env python3
"""Phase 2 on the controller: the §3.13 flow chart, as TC3 builds it.

Rows are discovered by visit, numbered in the order the chain first entered
each step, kept per mode session, and a §6.9(e) report marks the row of the
step that reported. Each row here drives the press through the declared write
surface only and reads the result twice - off the controller's chart and
through the projection a client reads.

The expected order of a clean cycle is not written down here: it is walked
from the declaration, following each step's on_advance from the chain's first
step until the loop closes, which is the path a cycle with no fault takes.
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

SCHEMA = "fraktal.ab.phase2-on-controller"
SCHEMA_VERSION = 1

APP = px.APP
ROOT = APP.name
AUTO = next(c for c in APP.chains if c.name == "AUTO")
ORDER = gen.ordered_steps(APP)
DEVICE_FAULT = demo.REASONS["CYL_NOT_EXTENDED"]   # the ram sticks extending


def clean_path(chain) -> list[int]:
    """The steps a fault-free cycle enters, in order, from the declaration."""
    by_number = {s.number: s for s in chain.steps}
    path, step = [], min(by_number)
    while step in by_number and step not in path:
        path.append(step)
        step = by_number[step].on_advance
    return path


def chart_rows(chart: dict[str, Any]) -> list[int]:
    found = sorted(
        (chart["RowOf"][i], number) for i, number in enumerate(ORDER)
        if chart["RowEpochOf"][i] == chart["RowEpoch"]
        and 1 <= chart["RowOf"][i] <= chart["RowCount"])
    return [number for _, number in found]


def published_rows(values: dict[str, Any]) -> list[int]:
    count = values.get(f"{ROOT}/SequenceStepCount", 0)
    return [values.get(f"{ROOT}/SequenceSteps[{i}]/StepNo")
            for i in range(1, count + 1)]


def row_field(values: dict[str, Any], step: int, field: str) -> Any:
    count = values.get(f"{ROOT}/SequenceStepCount", 0)
    for i in range(1, count + 1):
        if values.get(f"{ROOT}/SequenceSteps[{i}]/StepNo") == step:
            return values.get(f"{ROOT}/SequenceSteps[{i}]/{field}")
    return None


def document(comm: Any) -> dict[str, Any]:
    return projection.read_document(comm)["values"]


def fresh_auto(comm: Any, ack: float) -> None:
    """A new mode session: MANUAL then AUTO, each a mode change."""
    px._idle(comm, ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)


def one_parked_cycle(comm: Any, settle: float, ack: float) -> dict[str, int] | None:
    """One clean cycle that parks on N100, as the parity harness runs it."""
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    before = px.read_unit(comm)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == parity.AFTER_PARK, settle)
    px.write(comm, px.PART_PRESENT, 0)
    px.await_unit(comm, lambda u: before is not None
                  and u["CycleCount"] > before["CycleCount"], settle)
    parked, _ = px.await_unit(comm, lambda u: u["Step"] == parity.PARK_STEP, settle)
    time.sleep(0.2)
    return parked


def run(comm: Any, settle: float) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ack = parity.ack(settle)
    parity.select(comm, "ST")
    expected = clean_path(AUTO)
    settle_ms = next(m.initial for m in APP.records[0].members
                     if m.name == "TransferSettleMs")

    # --- 1. rows in the order a clean cycle entered them -------------------
    fresh_auto(comm, ack)
    started = time.monotonic()
    one_parked_cycle(comm, settle, ack)
    chart = px.read_chart(comm)
    unit = px.read_unit(comm)
    values = document(comm)
    on_chart = chart_rows(chart) if chart else []
    published = published_rows(values)
    rows.append(px.row(
        "rows_in_first_entry_order",
        "a fresh AUTO session's rows are the clean path's steps, in the order "
        "they were first entered, on the controller and as published",
        {"expected": expected, "controller": on_chart, "published": published,
         "rowCount": None if chart is None else chart["RowCount"]},
        (time.monotonic() - started) * 1000.0,
        on_chart == expected and published == expected,
    ))
    last_settle = row_field(values, 170, "LastDuration")
    cursor = values.get(f"{ROOT}/ActiveSteps[1]/RowIdx")
    rows.append(px.row(
        "a_row_keeps_its_duration_and_the_cursor_its_step",
        "the settle row records at least its declared delay; parked at N100 "
        "the cursor points at N100's row",
        {"settleLastDuration": last_settle, "declaredSettleMs": settle_ms,
         "cursor": cursor, "n100Row": expected.index(100) + 1,
         "running": None if unit is None else unit["Running"]},
        0.0,
        isinstance(last_settle, int) and last_settle >= settle_ms
        and cursor == expected.index(100) + 1,
    ))

    # --- 2. a second cycle adds nothing -------------------------------------
    count = chart["RowCount"] if chart else None
    px.command(comm, mailbox.STOP, settle=ack)
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    one_parked_cycle(comm, settle, ack)
    chart = px.read_chart(comm)
    rows.append(px.row(
        "a_second_cycle_adds_no_rows",
        "within one mode session a re-run keeps its rows",
        {"before": count, "after": None if chart is None else chart["RowCount"],
         "rows": chart_rows(chart) if chart else None},
        0.0, chart is not None and chart["RowCount"] == count
        and chart_rows(chart) == expected,
    ))

    # --- 3. a mode change starts a new chart --------------------------------
    epoch = chart["RowEpoch"] if chart else None
    px.command(comm, mailbox.STOP, settle=ack)
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_MANUAL)
    chart, elapsed = px.await_chart(comm, lambda c: c["RowCount"] == 0, settle)
    values = document(comm)
    rows.append(px.row(
        "a_mode_change_starts_a_new_chart",
        "MANUAL starts a new session: no rows, the epoch moved, nothing published",
        {"epochBefore": epoch, "epochAfter": None if chart is None else chart["RowEpoch"],
         "rowCount": None if chart is None else chart["RowCount"],
         "published": values.get(f"{ROOT}/SequenceStepCount")},
        elapsed,
        chart is not None and chart["RowCount"] == 0
        and epoch is not None and chart["RowEpoch"] == epoch + 1
        and values.get(f"{ROOT}/SequenceStepCount") == 0,
    ))

    # --- 4. a report marks its row, and the next visit starts clean ---------
    px.command(comm, mailbox.SET_MODE, settle=ack, IntValue=px.MODE_AUTO)
    px.command(comm, mailbox.OPERATOR_RESET, settle=ack)
    px.write(comm, px.PART_PRESENT, 1)
    px.write(comm, px.AIR_OK, 1)
    px.write(comm, px.TWO_HAND, 0)
    px.start_cycle(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == 170, settle)
    px.write(comm, px.FAULT["PressRam"], 1)
    unit, elapsed = px.await_unit(comm, lambda u: u["Step"] == 210, settle)
    time.sleep(0.1)
    chart = px.read_chart(comm)
    values = document(comm)
    index = ORDER.index(200)
    notes = values.get(f"{ROOT}/SequenceAnnotationCount", 0)
    note = {k: values.get(f"{ROOT}/SequenceAnnotations[1]/{k}")
            for k in ("RowIdx", "Key", "SourcePath", "IsError")}
    row_200 = published_rows(values).index(200) + 1 if 200 in published_rows(values) else None
    rows.append(px.row(
        "a_report_marks_its_row",
        "the ram failing at N200 marks N200's row as a warning, with a note "
        "naming the reason and the ram; no row is an error",
        {"warnReason": None if chart is None else chart["WarnReason"][index],
         "warnSource": None if chart is None else chart["WarnSource"][index],
         "warningActive": row_field(values, 200, "WarningActive"),
         "errorRows": [row_field(values, s, "ErrorActive") for s in published_rows(values)],
         "annotations": notes, "note": note, "row200": row_200},
        elapsed,
        chart is not None and chart["WarnReason"][index] == DEVICE_FAULT
        and chart["WarnSource"][index] == gen.module_source(APP, "PressRam")
        and row_field(values, 200, "WarningActive") is True
        and not any(row_field(values, s, "ErrorActive") for s in published_rows(values))
        and notes == 1 and note["RowIdx"] == row_200
        and note["Key"] == f"std.reason.{DEVICE_FAULT}"
        and note["SourcePath"] == f"{ROOT}.PressRam" and note["IsError"] is False,
    ))
    px.write(comm, px.FAULT["PressRam"], 0)
    px.command(comm, mailbox.DECISION_ANSWER, settle=ack, IntValue=1)
    # The next cycle passes N200 cleanly; that visit starts clean. It needs a
    # fresh two-hand press at N100: the cycle end dropped the latched start.
    px.await_unit(comm, lambda u: u["Step"] == 100, settle * 2)
    px.two_hand_press(comm, settle)
    px.await_unit(comm, lambda u: u["Step"] == 220, settle * 2)
    chart = px.read_chart(comm)
    values = document(comm)
    rows.append(px.row(
        "the_next_visit_starts_clean",
        "re-entering N200 without a fault clears its mark and its note",
        {"warnReason": None if chart is None else chart["WarnReason"][index],
         "warningActive": row_field(values, 200, "WarningActive"),
         "annotations": values.get(f"{ROOT}/SequenceAnnotationCount")},
        0.0,
        chart is not None and chart["WarnReason"][index] == 0
        and row_field(values, 200, "WarningActive") is False
        and values.get(f"{ROOT}/SequenceAnnotationCount") == 0,
    ))
    px.write(comm, px.PART_PRESENT, 0)
    px.await_unit(comm, lambda u: u["Step"] == parity.PARK_STEP, settle * 2)
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
