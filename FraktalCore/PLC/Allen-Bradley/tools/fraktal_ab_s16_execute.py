#!/usr/bin/env python3
"""Execute the fixed memory-only S16 command-handshake fixture vector.

This is not a generic PLC writer. It requires the exact controller serial and an
explicit arm flag, fingerprints the disposable S16 fixture before its first
write, writes only the five named command tags below, and restores every one of
them to zero before returning. It has no I/O, clock, mode, download, fault,
firmware, or network-configuration operation, and it accepts no caller-selected
tag or value.

The vector proves the Core §6.1 claims the controller itself measures:

* a full AUTO cycle completes through Execute -> Busy -> Done;
* abort mid-step raises Aborted and never self-resumes;
* dropping Execute mid-BUSY returns the module to READY and it restarts;
* a held condition is BUSY with a LOW-severity named reason, raises no Error,
  and resumes on its own when the condition clears;
* a faulted command raises Error with ErrorID and restarts by re-issue;
* a mode switch mid-cycle stands the chain down cleanly; and
* the module AOI ran unconditionally ahead of sequence intent every scan, with
  a command/result latency of exactly one scan.

Tag values are reported as shape and status, never as raw process values.
"""

from __future__ import annotations

import argparse
import json
import string
import struct
import sys
import time
from typing import Any


CTX = "FRK_S16_Ctx"
COMMAND = "FRK_S16_Command"
ABORT = "FRK_S16_Abort"
MODE_SELECT = "FRK_S16_ModeSelect"
HOLD = "FRK_S16_HoldRequest"
FAULT = "FRK_S16_FaultRequest"

# The complete write surface. Nothing outside this tuple is ever written, and
# every member is restored to zero by _disarm().
WRITABLE = (COMMAND, ABORT, MODE_SELECT, HOLD, FAULT)

# Read-only fingerprint tags. Their presence identifies the S16 fixture and
# distinguishes it from the S1/S2/S9/S11 fixtures that have held this
# controller before.
FINGERPRINT_TAGS = (
    f"{CTX}.SchemaVersion",
    f"{CTX}.Par_Speed",
    f"{CTX}.Par_TimeoutMs",
    f"{CTX}.OutImm_ExecState",
    f"{CTX}.Step",
    "FRK_S16_ScanCount",
    "FRK_S16_OrderFail",
)

EXPECTED_SCHEMA_VERSION = 1
EXPECTED_SPEED = 25
EXPECTED_TIMEOUT_MS = 500

STATE_READY = 0
STATE_BUSY = 1
STATE_DONE = 2
STATE_ERROR = 3
STATE_ABORTED = 4

REASON_HELD_PERMISSIVE = 6101
REASON_DEVICE_FAULT = 6102
REASON_ABORT_REQUEST = 6104

SEVERITY_LOW = 0

MODE_AUTO = 0
MODE_MANUAL = 1

# The context UDT exactly as FRK_T_S16Ctx declares it: 39 DINT members, in
# declaration order. A structured read returns the whole record as one CIP
# payload, so this table is what turns those 156 bytes back into members.
CTX_MEMBERS = (
    "SchemaVersion",
    "Par_Speed",
    "Par_TimeoutMs",
    "ParCmd_Target",
    "ParCmd_Latched",
    "OutCmd_FinalPos",
    "OutCmd_Ok",
    "OutImm_Pos",
    "OutImm_ExecState",
    "OutImm_Held",
    "OutImm_Reason",
    "OutImm_Severity",
    "Execute",
    "ExecutePrev",
    "Abort",
    "Busy",
    "Done",
    "Error",
    "Aborted",
    "ErrorID",
    "ElapsedMs",
    "RunCount",
    "DoneCount",
    "AbortCount",
    "ErrorCount",
    "HeldScans",
    "ResetCount",
    "ModuleScan",
    "SeqScan",
    "OrderFail",
    "CmdIssueScan",
    "IntentScan",
    "LatencyScans",
    "LatencyBad",
    "Step",
    "Mode",
    "ModeSwitches",
    "CycleCount",
    "ManualCount",
)

CTX_MEMBER_COUNT = len(CTX_MEMBERS)
CTX_PAYLOAD_BYTES = CTX_MEMBER_COUNT * 4

# Observation members read back after each phase.
OBSERVED = (
    "OutImm_ExecState",
    "OutImm_Held",
    "OutImm_Reason",
    "OutImm_Severity",
    "Busy",
    "Done",
    "Error",
    "Aborted",
    "ErrorID",
    "ParCmd_Latched",
    "OutCmd_Ok",
    "RunCount",
    "DoneCount",
    "AbortCount",
    "ErrorCount",
    "HeldScans",
    "ResetCount",
    "OrderFail",
    "LatencyScans",
    "LatencyBad",
    "Step",
    "Mode",
    "ModeSwitches",
    "CycleCount",
    "ManualCount",
)


def _normalize_serial(value: Any) -> str:
    serial = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(serial) != 8 or any(
        character not in string.hexdigits for character in serial
    ):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return serial


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--settle",
        type=float,
        default=0.5,
        help="bounded seconds to wait for a phase to reach its state",
    )
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 0 < args.settle <= 5:
        parser.error("--settle must be greater than zero and at most five seconds")
    if not args.execute_fixture:
        parser.error("--execute-fixture is required")
    args.expect_serial = _normalize_serial(args.expect_serial)
    return args


def _success(reply: Any) -> bool:
    return getattr(reply, "Status", None) == "Success"


def _status(reply: Any) -> str:
    return str(getattr(reply, "Status", "missing response"))


def _value(reply: Any) -> Any:
    return getattr(reply, "Value", None)


def _read_context(comm: Any) -> dict[str, Any] | None:
    """Read the whole context in ONE request, returning None if it fails.

    Reading the members one at a time cannot produce evidence about this
    fixture. The task runs at 10 ms and every counter in the record moves on
    its own, so a 25-request sweep spans tens of scans and returns a state the
    controller never held - the tearing AB_S9_COHERENCE_EVIDENCE.md measured,
    where a mutation interval shorter than the read window never converges.
    The context is 39 DINTs, so one structured read carries the entire record
    in a single CIP payload and is atomic on the wire; S9's own rule is that a
    row small enough for one request needs no retry at all.
    """
    reply = comm.Read(CTX)
    if not _success(reply):
        return None
    payload = _value(reply)
    if not isinstance(payload, (bytes, bytearray)):
        return None
    if len(payload) < CTX_PAYLOAD_BYTES:
        return None
    values = struct.unpack_from(f"<{CTX_MEMBER_COUNT}i", payload, 0)
    record = dict(zip(CTX_MEMBERS, values))
    return {member: record[member] for member in OBSERVED}


def _fingerprint(comm: Any) -> dict[str, Any]:
    """Prove this is the S16 fixture before writing anything."""
    readings: dict[str, Any] = {}
    for tag in FINGERPRINT_TAGS:
        reply = comm.Read(tag)
        if not _success(reply):
            return {"passed": False, "failed_tag": tag, "status": _status(reply)}
        readings[tag] = _value(reply)

    checks = {
        "schema_version": readings[f"{CTX}.SchemaVersion"] == EXPECTED_SCHEMA_VERSION,
        "speed": readings[f"{CTX}.Par_Speed"] == EXPECTED_SPEED,
        "timeout_ms": readings[f"{CTX}.Par_TimeoutMs"] == EXPECTED_TIMEOUT_MS,
        "scan_running": bool(readings["FRK_S16_ScanCount"]),
    }
    return {"passed": all(checks.values()), "checks": checks, "readings": readings}


def _write(comm: Any, tag: str, value: int) -> bool:
    if tag not in WRITABLE:
        raise AssertionError(f"tag outside the declared write surface: {tag}")
    return _success(comm.Write(tag, value))


def _disarm(comm: Any) -> dict[str, str]:
    """Restore every writable input. Reported even when a phase failed."""
    return {tag: ("cleared" if _write(comm, tag, 0) else "FAILED") for tag in WRITABLE}


def _await_state(
    comm: Any, predicate: Any, settle: float
) -> tuple[dict[str, Any] | None, float]:
    """Poll the context until predicate holds or the bounded settle expires."""
    deadline = time.monotonic() + settle
    last: dict[str, Any] | None = None
    started = time.monotonic()
    while time.monotonic() < deadline:
        observed = _read_context(comm)
        if observed is None:
            return None, (time.monotonic() - started) * 1000.0
        last = observed
        if predicate(observed):
            return observed, (time.monotonic() - started) * 1000.0
        time.sleep(0.01)
    return last, (time.monotonic() - started) * 1000.0


def _phase(
    name: str, expectation: str, observed: dict[str, Any] | None, elapsed_ms: float,
    holds: bool,
) -> dict[str, Any]:
    return {
        "phase": name,
        "expectation": expectation,
        "passed": bool(holds),
        "elapsed_ms": round(elapsed_ms, 3),
        "observed": observed,
    }


def run(comm: Any, settle: float) -> dict[str, Any]:
    """The fixed seven-phase vector. Every phase leaves the fixture disarmed."""
    phases: list[dict[str, Any]] = []

    # Phase 1 - a full AUTO cycle completes.
    # Measured against a baseline taken now, not against zero. The fixture free
    # runs from the moment it is downloaded and nothing here resets it, so its
    # lifetime counters are only zero on the first vector after a download:
    # comparing them with zero makes this phase unpassable ever after, while
    # "CycleCount >= 1" would equally pass on history alone without a single
    # cycle completing during the phase. The claim is about this cycle.
    _write(comm, MODE_SELECT, MODE_AUTO)
    baseline = _read_context(comm)
    _write(comm, COMMAND, 1)
    observed, elapsed = _await_state(
        comm,
        lambda o: baseline is not None and o["CycleCount"] > baseline["CycleCount"],
        settle,
    )
    phases.append(
        _phase(
            "auto_cycle",
            "AUTO chain completes a further cycle with no Error and no Aborted",
            observed,
            elapsed,
            observed is not None
            and baseline is not None
            and observed["CycleCount"] > baseline["CycleCount"]
            and observed["ErrorCount"] == baseline["ErrorCount"]
            and observed["AbortCount"] == baseline["AbortCount"],
        )
    )

    # Phase 2 - abort mid-step raises Aborted and does not self-resume.
    _write(comm, ABORT, 1)
    observed, elapsed = _await_state(
        comm, lambda o: o["Aborted"] != 0 or o["AbortCount"] >= 1, settle
    )
    aborted_at = observed["AbortCount"] if observed else 0
    time.sleep(min(settle, 0.2))
    after = _read_context(comm)
    phases.append(
        _phase(
            "abort_no_resume",
            "Aborted raised, ABORTED state, and Busy stays clear afterwards",
            after,
            elapsed,
            observed is not None
            and after is not None
            and aborted_at >= 1
            and after["Busy"] == 0,
        )
    )
    _write(comm, ABORT, 0)
    _write(comm, COMMAND, 0)

    # Phase 3 - dropping Execute mid-BUSY returns the module to READY.
    _write(comm, COMMAND, 1)
    _await_state(comm, lambda o: o["Busy"] != 0, settle)
    _write(comm, COMMAND, 0)
    observed, elapsed = _await_state(
        comm,
        lambda o: o["OutImm_ExecState"] == STATE_READY and o["Busy"] == 0,
        settle,
    )
    phases.append(
        _phase(
            "execute_drop_ready",
            "Execute drop returns ExecState to READY with Busy clear",
            observed,
            elapsed,
            observed is not None
            and observed["OutImm_ExecState"] == STATE_READY
            and observed["Busy"] == 0,
        )
    )

    # Phase 4 - held is BUSY with a LOW reason, no Error, and auto-resumes.
    _write(comm, HOLD, 1)
    _write(comm, COMMAND, 1)
    observed, elapsed = _await_state(
        comm, lambda o: o["OutImm_Held"] != 0, settle
    )
    held_ok = (
        observed is not None
        and observed["OutImm_Held"] != 0
        and observed["OutImm_ExecState"] == STATE_BUSY
        and observed["OutImm_Reason"] == REASON_HELD_PERMISSIVE
        and observed["OutImm_Severity"] == SEVERITY_LOW
        and observed["Error"] == 0
    )
    held_view = observed
    _write(comm, HOLD, 0)
    resumed, resume_elapsed = _await_state(
        comm, lambda o: o["OutImm_Held"] == 0 and o["DoneCount"] >= 1, settle
    )
    phases.append(
        _phase(
            "held_low_reason",
            "Held: BUSY + LOW named reason + no Error",
            held_view,
            elapsed,
            held_ok,
        )
    )
    phases.append(
        _phase(
            "held_auto_resume",
            "clearing the condition resumes progress with no re-issue",
            resumed,
            resume_elapsed,
            resumed is not None and resumed["OutImm_Held"] == 0,
        )
    )
    _write(comm, COMMAND, 0)

    # Phase 5 - a fault raises Error + ErrorID and restarts by re-issue.
    _write(comm, FAULT, 1)
    _write(comm, COMMAND, 1)
    observed, elapsed = _await_state(
        comm, lambda o: o["Error"] != 0, settle
    )
    faulted = (
        observed is not None
        and observed["Error"] != 0
        and observed["ErrorID"] == REASON_DEVICE_FAULT
        and observed["OutImm_ExecState"] == STATE_ERROR
    )
    fault_view = observed
    _write(comm, COMMAND, 0)
    _write(comm, FAULT, 0)
    _await_state(comm, lambda o: o["OutImm_ExecState"] == STATE_READY, settle)
    _write(comm, COMMAND, 1)
    restarted, restart_elapsed = _await_state(
        comm, lambda o: o["Busy"] != 0 or o["DoneCount"] >= 1, settle
    )
    phases.append(
        _phase(
            "fault_error_id",
            "fault raises Error with the device ErrorID and ERROR state",
            fault_view,
            elapsed,
            faulted,
        )
    )
    phases.append(
        _phase(
            "restart_by_reissue",
            "a fresh Execute edge restarts the command after the fault",
            restarted,
            restart_elapsed,
            restarted is not None and restarted["Error"] == 0,
        )
    )

    # Phase 6 - a mode switch mid-cycle stands the chain down.
    _write(comm, MODE_SELECT, MODE_MANUAL)
    observed, elapsed = _await_state(
        comm, lambda o: o["Mode"] == MODE_MANUAL, settle
    )
    phases.append(
        _phase(
            "mode_switch_midcycle",
            "mode change is observed and the chain stands down to its init step",
            observed,
            elapsed,
            observed is not None
            and observed["Mode"] == MODE_MANUAL
            and observed["ModeSwitches"] >= 1,
        )
    )
    _write(comm, COMMAND, 0)
    _write(comm, MODE_SELECT, MODE_AUTO)

    # Phase 7 - ordering and one-scan latency held throughout.
    final = _read_context(comm)
    phases.append(
        _phase(
            "ordering_and_latency",
            "module ran ahead of sequence every scan; latency was one scan",
            final,
            0.0,
            final is not None
            and final["OrderFail"] == 0
            and final["LatencyBad"] == 0,
        )
    )
    return {"phases": phases, "passed": all(phase["passed"] for phase in phases)}


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR: pylogix is required; install the hash-pinned "
            "requirements-phase0.txt into a virtual environment outside the "
            "repository",
            file=sys.stderr,
        )
        return 2

    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s16-execute",
        "schema_version": 1,
        "target": args.target,
        "expected_serial": args.expect_serial,
        "client": "pylogix 1.1.5",
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

        fingerprint = _fingerprint(comm)
        evidence["fingerprint"] = fingerprint
        if not fingerprint.get("passed"):
            evidence["error"] = "fixture fingerprint failed; nothing was written"
            evidence["wrote"] = False
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1

        evidence["wrote"] = True
        evidence["write_surface"] = list(WRITABLE)
        try:
            evidence["result"] = run(comm, args.settle)
        finally:
            evidence["disarm"] = _disarm(comm)

    evidence["passed"] = bool(
        evidence.get("result", {}).get("passed")
        and all(state == "cleared" for state in evidence["disarm"].values())
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
