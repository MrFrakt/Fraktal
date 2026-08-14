#!/usr/bin/env python3
"""Execute the fixed memory-only S11 sequence-execution fixture vector.

This is not a generic PLC writer. It requires the exact controller serial and
an explicit arm flag, fingerprints the disposable S11 fixture before its first
write, writes only ``FRK_S11_Command`` and ``FRK_S11_ResetRequest``, and
restores both to zero. It has no I/O, clock, mode, download, fault, firmware,
or network-configuration operation, and it accepts no caller-selected tag or
value.

The vector proves the AB §3.5 execution claims the controller itself measures:
the root module AOI runs unconditionally and before sequence intent, the
command/result loop costs exactly one scan, both generated forms walk the same
step trace in the same number of scans, a simultaneous branch runs one numbered
leg per Core branch, and an ``SFR`` reset re-runs the chain identically.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
import time
from typing import Any


COMMAND = "FRK_S11_Command"
RESET = "FRK_S11_ResetRequest"
ST_CTX = "FRK_S11_StCtx"
SFC_CTX = "FRK_S11_SfcCtx"
FORMS = (("st", ST_CTX), ("sfc", SFC_CTX))

BROWSE_TAGS = {
    COMMAND,
    RESET,
    ST_CTX,
    SFC_CTX,
    "FRK_S11_ScanCount",
    "FRK_S11_JsrCount",
    "FRK_S11_SfrCount",
    "FRK_S11_ParityOk",
    "FRK_S11_OrderFail",
    "FRK_S11_Complete",
}
HIDDEN_INSTANCES = ("FRK_S11_StOwner", "FRK_S11_SfcModule")

EXPECTED_TRACE = (10, 1030, 2040, 50)
EXPECTED_LATENCY_SCANS = 1
TRACE_CAPACITY = 12
COMMAND_VECTOR = 1
RESET_VECTOR = 1


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
        "--settle", type=float, default=0.5,
        help="bounded seconds to wait for a run to complete",
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


def _value(controller: Any, tag: str) -> Any:
    reply = controller.Read(tag)
    return getattr(reply, "Value", None) if _success(reply) else None


def _trace(controller: Any, context: str) -> list[Any]:
    count = _value(controller, f"{context}.TraceCount")
    if not isinstance(count, int) or not 0 <= count <= TRACE_CAPACITY:
        return []
    return [
        _value(controller, f"{context}.Trace[{index}]") for index in range(count)
    ]


def _await_done(controller: Any, deadline: float) -> bool:
    while time.monotonic() < deadline:
        if all(_value(controller, f"{context}.Done") == 1 for _, context in FORMS):
            return True
        time.sleep(0.02)
    return False


def _run(controller: Any, label: str, settle: float) -> dict[str, Any]:
    """Drive one bounded run and collect what the controller measured."""
    run: dict[str, Any] = {"label": label, "checks": []}
    sfr_before = _value(controller, "FRK_S11_SfrCount")
    jsr_before = _value(controller, "FRK_S11_JsrCount")

    write = controller.Write(COMMAND, COMMAND_VECTOR)
    run["command_write"] = {"status": _status(write), "passed": _success(write)}
    completed = _await_done(controller, time.monotonic() + settle)
    run["completed_within_budget"] = completed
    controller.Write(COMMAND, 0)

    forms: dict[str, Any] = {}
    for name, context in FORMS:
        forms[name] = {
            "trace": _trace(controller, context),
            "done": _value(controller, f"{context}.Done"),
            "busy": _value(controller, f"{context}.Busy"),
            "scans_to_complete": _value(controller, f"{context}.ScansToComplete"),
            "latency_scans": _value(controller, f"{context}.LatencyScans"),
            "latency_bad": _value(controller, f"{context}.LatencyBad"),
            "module_order": _value(controller, f"{context}.ModuleOrder"),
            "seq_order": _value(controller, f"{context}.SeqOrder"),
            "run_count": _value(controller, f"{context}.RunCount"),
            "trace_overflow": _value(controller, f"{context}.TraceOverflow"),
        }
    run["forms"] = forms

    sfr_after = _value(controller, "FRK_S11_SfrCount")
    jsr_after = _value(controller, "FRK_S11_JsrCount")
    run["sfr_delta"] = (
        sfr_after - sfr_before
        if isinstance(sfr_after, int) and isinstance(sfr_before, int)
        else None
    )
    run["jsr_delta"] = (
        jsr_after - jsr_before
        if isinstance(jsr_after, int) and isinstance(jsr_before, int)
        else None
    )

    checks = [
        ("completed", completed),
        ("parity_ok", _value(controller, "FRK_S11_ParityOk") == 1),
        ("order_never_violated", _value(controller, "FRK_S11_OrderFail") == 0),
        # exactly one SFR for the one reset/start edge this run raised
        ("single_sfr_edge", run["sfr_delta"] == 1),
        ("chart_was_called", isinstance(run["jsr_delta"], int) and run["jsr_delta"] > 0),
        (
            "scan_parity",
            forms["st"]["scans_to_complete"] == forms["sfc"]["scans_to_complete"]
            and isinstance(forms["st"]["scans_to_complete"], int),
        ),
    ]
    for name in ("st", "sfc"):
        form = forms[name]
        checks.extend(
            [
                (f"{name}_trace", tuple(form["trace"]) == EXPECTED_TRACE),
                (f"{name}_done", form["done"] == 1),
                (f"{name}_idle_after_done", form["busy"] == 0),
                (f"{name}_one_scan_latency",
                 form["latency_scans"] == EXPECTED_LATENCY_SCANS),
                (f"{name}_no_late_consumption", form["latency_bad"] == 0),
                (f"{name}_module_ran_first",
                 isinstance(form["module_order"], int)
                 and isinstance(form["seq_order"], int)
                 and form["module_order"] < form["seq_order"]),
                (f"{name}_no_trace_overflow", form["trace_overflow"] == 0),
            ]
        )
    run["checks"] = [{"case": case, "passed": bool(passed)} for case, passed in checks]
    run["passed"] = all(item["passed"] for item in run["checks"])
    return run


def execute_fixture(
    controller: Any, expected_serial: str, settle: float = 0.5
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s11-execution",
        "schema_version": 1,
        "expected_serial": expected_serial,
        "expected_trace": list(EXPECTED_TRACE),
        "fixture_fingerprint": {"passed": False},
        "runs": [],
        "cleanup": {"attempted": False, "verified": False},
        "execution_passed": False,
    }

    identity = controller.GetDeviceProperties()
    if not _success(identity) or getattr(identity, "Value", None) is None:
        evidence["error"] = f"identity read failed: {_status(identity)}"
        return evidence
    device = identity.Value
    actual_serial = _normalize_serial(device.SerialNumber)
    evidence["identity"] = {
        "product_name": device.ProductName,
        "revision": device.Revision,
        "serial_number": actual_serial,
    }
    if actual_serial != expected_serial:
        evidence["error"] = "controller serial did not match; no writes attempted"
        return evidence

    tag_reply = controller.GetTagList(False)
    names = {
        getattr(tag, "TagName", "")
        for tag in (getattr(tag_reply, "Value", None) or [])
    }
    missing = sorted(BROWSE_TAGS - names)
    hidden = [instance for instance in HIDDEN_INSTANCES if instance in names]
    complete = controller.Read("FRK_S11_Complete")
    scan_before = _value(controller, "FRK_S11_ScanCount")
    jsr_idle_before = _value(controller, "FRK_S11_JsrCount")
    module_before = {
        name: _value(controller, f"{context}.ModuleScans") for name, context in FORMS
    }
    time.sleep(0.2)
    scan_after = _value(controller, "FRK_S11_ScanCount")
    jsr_idle_after = _value(controller, "FRK_S11_JsrCount")
    module_after = {
        name: _value(controller, f"{context}.ModuleScans") for name, context in FORMS
    }

    scanning = (
        isinstance(scan_before, int)
        and isinstance(scan_after, int)
        and scan_after > scan_before
    )
    # the root module AOI is unconditional; the chart is called only while BUSY
    module_unconditional = all(
        isinstance(module_before[name], int)
        and isinstance(module_after[name], int)
        and module_after[name] > module_before[name]
        for name, _ in FORMS
    )
    chart_idle = jsr_idle_before == jsr_idle_after
    fingerprint = (
        _success(tag_reply)
        and not missing
        and not hidden
        and _success(complete)
        and getattr(complete, "Value", None) is True
        and scanning
        and module_unconditional
        and chart_idle
    )
    evidence["fixture_fingerprint"] = {
        "passed": fingerprint,
        "tag_list_status": _status(tag_reply),
        "missing_tags": missing,
        "browsable_private_instances": hidden,
        "complete_status": _status(complete),
        "task_scanning": scanning,
        "module_aoi_unconditional_while_idle": module_unconditional,
        "chart_not_called_while_idle": chart_idle,
    }
    if not fingerprint:
        evidence["error"] = "fixture fingerprint failed; no writes attempted"
        return evidence

    try:
        evidence["runs"].append(_run(controller, "first_run", settle))

        # reset/re-entry: the wrapper's SFR must return the chart to its
        # declared initial step and the next run must repeat the trace exactly
        controller.Write(RESET, RESET_VECTOR)
        time.sleep(0.1)
        controller.Write(RESET, 0)
        time.sleep(0.1)
        evidence["after_reset"] = {
            name: {
                "trace_count": _value(controller, f"{context}.TraceCount"),
                "done": _value(controller, f"{context}.Done"),
                "reset_count": _value(controller, f"{context}.ResetCount"),
            }
            for name, context in FORMS
        }
        evidence["runs"].append(_run(controller, "after_reset_run", settle))

        first, second = evidence["runs"]
        evidence["re_entry"] = {
            "traces_identical": (
                first["forms"]["st"]["trace"] == second["forms"]["st"]["trace"]
                and first["forms"]["sfc"]["trace"] == second["forms"]["sfc"]["trace"]
            ),
            "scans_identical": (
                first["forms"]["st"]["scans_to_complete"]
                == second["forms"]["st"]["scans_to_complete"]
            ),
            "run_count_advanced": all(
                isinstance(second["forms"][name]["run_count"], int)
                and isinstance(first["forms"][name]["run_count"], int)
                and second["forms"][name]["run_count"]
                > first["forms"][name]["run_count"]
                for name, _ in FORMS
            ),
        }
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        evidence["error"] = f"fixture execution failed: {type(exc).__name__}: {exc}"
    finally:
        cleanup_writes = [
            {"tag": tag, "status": _status(reply), "passed": _success(reply)}
            for tag, reply in (
                (COMMAND, controller.Write(COMMAND, 0)),
                (RESET, controller.Write(RESET, 0)),
            )
        ]
        time.sleep(0.15)
        cleanup_checks = [
            {"case": f"cleanup_{tag}", "passed": _value(controller, tag) == 0}
            for tag in (COMMAND, RESET)
        ]
        evidence["cleanup"] = {
            "attempted": True,
            "writes": cleanup_writes,
            "checks": cleanup_checks,
            "verified": all(
                item["passed"] for item in cleanup_writes + cleanup_checks
            ),
        }

    evidence["execution_passed"] = (
        "error" not in evidence
        and bool(evidence["runs"])
        and all(run["passed"] for run in evidence["runs"])
        and all(evidence.get("re_entry", {}).values())
        and evidence["cleanup"]["verified"]
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR [s11-execution] install the pinned Phase 0 requirements",
            file=sys.stderr,
        )
        return 2
    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            evidence = execute_fixture(controller, args.expect_serial, args.settle)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [s11-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
