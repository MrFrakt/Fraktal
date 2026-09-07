#!/usr/bin/env python3
"""Execute the disposable Fraktal/AB reference suite and emit machine-readable rows.

This is the R5 harness. It is not a generic PLC writer: it requires the exact
controller serial and an explicit arm flag, fingerprints the reference suite
before its first write, writes only the six named command tags below, and
restores every one of them before returning.

It reports **one row per test**, plus the five summary fields AB §5.7 names for
the controller-resident harness it mirrors - suites, tests, successful, failed
and duration - so the output converts to JUnit the same way TC3's does.

Two things this proves that the S16 vector could not:

* the **module reference type is instantiated twice** and the instances are
  independent - driving A leaves B untouched, and driving B alone works; and
* the suite's own **cross-talk counter** stayed at zero, so independence is a
  controller-side measurement rather than a host-side inference.

Observations are read **coherently**. The context is 39 ``DINT``s, so one
structured read returns the whole record in a single CIP payload, atomic on the
wire. Assembling an observation from per-member reads is what made the first S16
runs unrepeatable: the task mutates every 10 ms, so a multi-request sweep spans
tens of scans and reports a state the controller never held - the tearing
``AB_S9_COHERENCE_EVIDENCE.md`` measured. That mistake is not repeated here.

Tag values are reported as shape and status, never as raw process values.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_reference_suite as suite


SCHEMA = "fraktal.ab.reference-execute"
SCHEMA_VERSION = 1

CTX_A = suite.CTX_A
CTX_B = suite.CTX_B

COMMAND_A = "FRK_Ref_CommandA"
ABORT_A = "FRK_Ref_AbortA"
MODE_SELECT_A = "FRK_Ref_ModeSelectA"
HOLD_A = "FRK_Ref_HoldA"
FAULT_A = "FRK_Ref_FaultA"
COMMAND_B = "FRK_Ref_CommandB"

WRITABLE = (COMMAND_A, ABORT_A, MODE_SELECT_A, HOLD_A, FAULT_A, COMMAND_B)

SCAN_COUNT = "FRK_Ref_ScanCount"
ORDER_FAIL = "FRK_Ref_OrderFail"
LATENCY_BAD = "FRK_Ref_LatencyBad"
CROSS_TALK = "FRK_Ref_CrossTalk"

FINGERPRINT_TAGS = (
    f"{CTX_A}.SchemaVersion",
    f"{CTX_A}.Par_Speed",
    f"{CTX_A}.Par_TimeoutMs",
    f"{CTX_B}.SchemaVersion",
    SCAN_COUNT,
    CROSS_TALK,
)

CTX_MEMBERS = tuple(member.name for member in suite.CTX_MEMBERS)
CTX_MEMBER_COUNT = len(CTX_MEMBERS)
CTX_PAYLOAD_BYTES = CTX_MEMBER_COUNT * 4

EXPECTED_SCHEMA_VERSION = suite.declaration.SCHEMA_VERSION
EXPECTED_SPEED = suite.declaration.SPEED_PER_SCAN
EXPECTED_TIMEOUT_MS = suite.declaration.DEFAULT_TIMEOUT_MS

STATE_READY = suite.declaration.STATE_READY
STATE_BUSY = suite.declaration.STATE_BUSY
STATE_ERROR = suite.declaration.STATE_ERROR
STATE_ABORTED = suite.declaration.STATE_ABORTED
SEVERITY_LOW = suite.declaration.SEVERITY_LOW
SEVERITY_HIGH = suite.declaration.SEVERITY_HIGH
REASON_HELD = suite.declaration.REASON_HELD_PERMISSIVE
REASON_FAULT = suite.declaration.REASON_DEVICE_FAULT
MODE_AUTO = suite.declaration.MODE_AUTO

SUITE_NAME = "fraktal.ab.reference"


def read_context(comm: Any, tag: str) -> dict[str, Any] | None:
    """Read one whole context in a single request, or fail closed."""
    reply = comm.Read(tag)
    if not _success(reply):
        return None
    payload = _value(reply)
    if not isinstance(payload, (bytes, bytearray)):
        return None
    if len(payload) < CTX_PAYLOAD_BYTES:
        return None
    values = struct.unpack_from(f"<{CTX_MEMBER_COUNT}i", payload, 0)
    return dict(zip(CTX_MEMBERS, values))


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


def await_state(comm: Any, tag: str, predicate: Any, settle: float):
    deadline = time.monotonic() + settle
    started = time.monotonic()
    last = None
    while time.monotonic() < deadline:
        observed = read_context(comm, tag)
        if observed is None:
            return None, (time.monotonic() - started) * 1000.0
        last = observed
        if predicate(observed):
            return observed, (time.monotonic() - started) * 1000.0
        time.sleep(0.01)
    return last, (time.monotonic() - started) * 1000.0


def row(name: str, expectation: str, observed, elapsed_ms: float, holds: bool):
    return {
        "test": name,
        "suite": SUITE_NAME,
        "expectation": expectation,
        "passed": bool(holds),
        "elapsed_ms": round(elapsed_ms, 3),
        "observed": observed,
    }


def fingerprint(comm: Any) -> dict[str, Any]:
    """Prove this is the reference suite before writing anything."""
    readings: dict[str, Any] = {}
    for tag in FINGERPRINT_TAGS:
        reply = comm.Read(tag)
        if not _success(reply):
            return {"passed": False, "failed_tag": tag, "status": _status(reply)}
        readings[tag] = _value(reply)
    checks = {
        "schema_version_a": readings[f"{CTX_A}.SchemaVersion"] == EXPECTED_SCHEMA_VERSION,
        "schema_version_b": readings[f"{CTX_B}.SchemaVersion"] == EXPECTED_SCHEMA_VERSION,
        "speed": readings[f"{CTX_A}.Par_Speed"] == EXPECTED_SPEED,
        "timeout_ms": readings[f"{CTX_A}.Par_TimeoutMs"] == EXPECTED_TIMEOUT_MS,
        "scan_running": bool(readings[SCAN_COUNT]),
    }
    return {"passed": all(checks.values()), "checks": checks, "readings": readings}


def disarm(comm: Any) -> dict[str, str]:
    """Restore every writable input, reporting a failed restore rather than hiding it."""
    result: dict[str, str] = {}
    for tag in WRITABLE:
        ok = _success(comm.Write(tag, 0))
        if ok:
            reply = comm.Read(tag)
            ok = _success(reply) and _value(reply) == 0
        result[tag] = "cleared" if ok else "FAILED"
    return result


def run(comm: Any, settle: float) -> dict[str, Any]:
    """The fixed reference-suite vector. Every row leaves the suite disarmed."""
    rows: list[dict[str, Any]] = []
    started = time.monotonic()

    write(comm, MODE_SELECT_A, MODE_AUTO)

    # 1 - both reference types are present and scanning.
    base_a = read_context(comm, CTX_A)
    base_b = read_context(comm, CTX_B)
    rows.append(row(
        "reference_types_scanning",
        "both contexts read coherently and the task is scanning",
        {"a": base_a is not None, "b": base_b is not None},
        0.0,
        base_a is not None and base_b is not None,
    ))

    # 2 - module instance A completes a further cycle.
    write(comm, COMMAND_A, 1)
    observed, elapsed = await_state(
        comm, CTX_A,
        lambda o: base_a is not None and o["CycleCount"] > base_a["CycleCount"],
        settle,
    )
    rows.append(row(
        "module_a_completes_cycle",
        "instance A completes a further cycle with no Error and no Aborted",
        observed, elapsed,
        observed is not None and base_a is not None
        and observed["CycleCount"] > base_a["CycleCount"]
        and observed["ErrorCount"] == base_a["ErrorCount"]
        and observed["AbortCount"] == base_a["AbortCount"],
    ))

    # 3 - instance B was not disturbed while A ran.
    after_b = read_context(comm, CTX_B)
    cross = read_scalar(comm, CROSS_TALK)
    rows.append(row(
        "module_b_undisturbed_while_a_runs",
        "instance B keeps its run count and stays READY while A is driven",
        {"cross_talk": cross},
        0.0,
        after_b is not None and base_b is not None
        and after_b["RunCount"] == base_b["RunCount"]
        and after_b["OutImm_ExecState"] == STATE_READY
        and cross == 0,
    ))
    write(comm, COMMAND_A, 0)

    # 4 - held is BUSY at LOW severity with a named reason and no Error.
    write(comm, HOLD_A, 1)
    write(comm, COMMAND_A, 1)
    observed, elapsed = await_state(
        comm, CTX_A, lambda o: o["OutImm_Held"] != 0, settle
    )
    rows.append(row(
        "module_a_held_is_low_and_not_an_error",
        "held: BUSY + reason 6101 at LOW severity + Error clear",
        observed, elapsed,
        observed is not None
        and observed["OutImm_Held"] != 0
        and observed["OutImm_ExecState"] == STATE_BUSY
        and observed["OutImm_Reason"] == REASON_HELD
        and observed["OutImm_Severity"] == SEVERITY_LOW
        and observed["Error"] == 0,
    ))

    # 5 - clearing the condition resumes with no re-issue.
    write(comm, HOLD_A, 0)
    observed, elapsed = await_state(
        comm, CTX_A, lambda o: o["OutImm_Held"] == 0, settle
    )
    rows.append(row(
        "module_a_resumes_without_reissue",
        "clearing the hold resumes progress with no fresh Execute edge",
        observed, elapsed,
        observed is not None and observed["OutImm_Held"] == 0,
    ))
    write(comm, COMMAND_A, 0)

    # 6 - a fault raises Error with the device ErrorID at HIGH severity.
    write(comm, FAULT_A, 1)
    write(comm, COMMAND_A, 1)
    observed, elapsed = await_state(
        comm, CTX_A, lambda o: o["Error"] != 0, settle
    )
    rows.append(row(
        "module_a_fault_carries_error_id",
        "fault: Error + ErrorID 6102 + ERROR state at HIGH severity",
        observed, elapsed,
        observed is not None
        and observed["Error"] != 0
        and observed["ErrorID"] == REASON_FAULT
        and observed["OutImm_ExecState"] == STATE_ERROR
        and observed["OutImm_Severity"] == SEVERITY_HIGH,
    ))
    write(comm, COMMAND_A, 0)
    write(comm, FAULT_A, 0)
    await_state(comm, CTX_A, lambda o: o["OutImm_ExecState"] == STATE_READY, settle)

    # 7 - abort is terminal and does not self-resume.
    write(comm, COMMAND_A, 1)
    await_state(comm, CTX_A, lambda o: o["Busy"] != 0, settle)
    write(comm, ABORT_A, 1)
    observed, elapsed = await_state(
        comm, CTX_A, lambda o: o["Aborted"] != 0, settle
    )
    time.sleep(min(settle, 0.2))
    after_abort = read_context(comm, CTX_A)
    rows.append(row(
        "module_a_abort_does_not_self_resume",
        "abort raises Aborted, reaches ABORTED, and Busy stays clear",
        after_abort, elapsed,
        observed is not None and after_abort is not None
        and observed["Aborted"] != 0
        and after_abort["Busy"] == 0,
    ))
    write(comm, ABORT_A, 0)
    write(comm, COMMAND_A, 0)

    # 8 - the second instance runs on its own.
    before_b = read_context(comm, CTX_B)
    before_a = read_context(comm, CTX_A)
    write(comm, COMMAND_B, 1)
    observed, elapsed = await_state(
        comm, CTX_B,
        lambda o: before_b is not None and o["RunCount"] > before_b["RunCount"],
        settle,
    )
    settled_a = read_context(comm, CTX_A)
    rows.append(row(
        "module_b_runs_independently",
        "instance B accepts its own command while A is left idle and unaffected",
        observed, elapsed,
        observed is not None and before_b is not None
        and observed["RunCount"] > before_b["RunCount"]
        and settled_a is not None and before_a is not None
        and settled_a["RunCount"] == before_a["RunCount"],
    ))
    write(comm, COMMAND_B, 0)

    # 9 - ordering, latency and cross-talk across the whole run.
    order_fail = read_scalar(comm, ORDER_FAIL)
    latency_bad = read_scalar(comm, LATENCY_BAD)
    cross_talk = read_scalar(comm, CROSS_TALK)
    final_a = read_context(comm, CTX_A)
    rows.append(row(
        "ordering_latency_and_cross_talk",
        "OrderFail 0, LatencyBad 0, one-scan latency, and no cross-talk",
        {
            "OrderFail": order_fail, "LatencyBad": latency_bad,
            "CrossTalk": cross_talk,
            "LatencyScans": None if final_a is None else final_a["LatencyScans"],
        },
        0.0,
        order_fail == 0 and latency_bad == 0 and cross_talk == 0
        and final_a is not None and final_a["LatencyScans"] == 1,
    ))

    duration_ms = (time.monotonic() - started) * 1000.0
    successful = sum(1 for r in rows if r["passed"])
    return {
        "suites": 1,
        "tests": len(rows),
        "successful": successful,
        "failed": len(rows) - successful,
        "duration_ms": round(duration_ms, 3),
        "passed": successful == len(rows),
        "rows": rows,
    }


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True, type=_normalize_serial)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--settle", type=float, default=2.0)
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
        "suite": SUITE_NAME,
        "disposable": True,
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
            evidence["error"] = "reference-suite fingerprint failed; nothing was written"
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
