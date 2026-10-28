#!/usr/bin/env python3
"""Measure bounded EtherNet/IP transport behavior on the Phase 0 fixture.

The probe is read-only and fixed to ``FRK_Heartbeat``, ``FRK_TestComplete``, and
``FRK_WriteLargeArray``.  It requires the expected controller serial, caps every
user-selectable workload, closes every client, and reports no tag values.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import string
import sys
import threading
import time
from typing import Any, Callable


LARGE_TAG = "FRK_WriteLargeArray[0]"
HEARTBEAT_TAG = "FRK_Heartbeat"
COMPLETE_TAG = "FRK_TestComplete"
DEFAULT_SIZES = (128, 256, 500, 1000, 2000, 4000)
DEFAULT_LEVELS = (1, 2, 4, 8, 12, 16)


def _serial(value: Any) -> str:
    result = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(result) != 8 or any(character not in string.hexdigits for character in result):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return result


def _csv_ints(value: str, minimum: int, maximum: int) -> tuple[int, ...]:
    try:
        result = tuple(int(item) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not result or len(result) > 16 or any(item < minimum or item > maximum for item in result):
        raise argparse.ArgumentTypeError(
            f"values must contain 1..16 entries between {minimum} and {maximum}"
        )
    return tuple(dict.fromkeys(result))


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="single controller IPv4 address or host name")
    parser.add_argument("--expect-serial", required=True, type=_serial)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--cycles", type=int, default=25)
    parser.add_argument("--required-readers", type=int, default=4)
    parser.add_argument(
        "--connection-sizes",
        type=lambda value: _csv_ints(value, 128, 4002),
        default=DEFAULT_SIZES,
    )
    parser.add_argument(
        "--reader-levels",
        type=lambda value: _csv_ints(value, 1, 32),
        default=DEFAULT_LEVELS,
    )
    args = parser.parse_args(argv)
    if not 0.1 <= args.timeout <= 60:
        parser.error("--timeout must be between 0.1 and 60 seconds")
    if not 1 <= args.cycles <= 200:
        parser.error("--cycles must be between 1 and 200")
    if not 1 <= args.required_readers <= 32:
        parser.error("--required-readers must be between 1 and 32")
    if args.required_readers not in args.reader_levels:
        parser.error("--required-readers must be present in --reader-levels")
    return args


def _success(reply: Any) -> bool:
    return getattr(reply, "Status", None) == "Success"


def _status(reply: Any) -> str:
    return str(getattr(reply, "Status", "missing response"))


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum_ms": None, "median_ms": None, "maximum_ms": None}
    return {
        "minimum_ms": round(min(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "maximum_ms": round(max(values), 3),
    }


def _read_once(plc_factory: Callable[[str], Any], target: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with plc_factory(target) as controller:
            controller.SocketTimeout = timeout
            reply = controller.Read(HEARTBEAT_TAG)
        return {
            "status": _status(reply),
            "passed": _success(reply),
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return {
            "status": f"{type(exc).__name__}: {exc}",
            "passed": False,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }


def _concurrent_level(
    plc_factory: Callable[[str], Any], target: str, timeout: float, level: int
) -> dict[str, Any]:
    barrier = threading.Barrier(level)

    def worker() -> dict[str, Any]:
        started = time.perf_counter()
        try:
            with plc_factory(target) as controller:
                controller.SocketTimeout = timeout
                warmup = controller.Read(HEARTBEAT_TAG)
                if not _success(warmup):
                    return {
                        "status": _status(warmup), "passed": False,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    }
                barrier.wait(timeout=timeout)
                reply = controller.Read(HEARTBEAT_TAG)
            return {
                "status": _status(reply),
                "passed": _success(reply),
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            }
        except (OSError, RuntimeError, TypeError, ValueError, threading.BrokenBarrierError) as exc:
            return {
                "status": f"{type(exc).__name__}: {exc}",
                "passed": False,
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=level) as pool:
        results = list(pool.map(lambda _: worker(), range(level)))
    latencies = [item["elapsed_ms"] for item in results]
    statuses: dict[str, int] = {}
    for item in results:
        statuses[item["status"]] = statuses.get(item["status"], 0) + 1
    return {
        "readers": level,
        "passed": all(item["passed"] for item in results),
        "successful": sum(1 for item in results if item["passed"]),
        "statuses": statuses,
        "latency": _latency_summary(latencies),
    }


def run_probe(
    plc_factory: Callable[[str], Any],
    target: str,
    expected_serial: str,
    timeout: float,
    cycles: int,
    connection_sizes: tuple[int, ...],
    reader_levels: tuple[int, ...],
    required_readers: int,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.transport-budget",
        "schema_version": 1,
        "target": target,
        "expected_serial": expected_serial,
        "values_redacted": True,
        "read_only": True,
        "passed": False,
    }
    with plc_factory(target) as controller:
        controller.SocketTimeout = timeout
        identity = controller.GetDeviceProperties()
        if not _success(identity) or getattr(identity, "Value", None) is None:
            evidence["error"] = f"identity read failed: {_status(identity)}"
            return evidence
        device = identity.Value
        actual_serial = _serial(device.SerialNumber)
        evidence["identity"] = {
            "product_name": device.ProductName,
            "revision": device.Revision,
            "serial_number": actual_serial,
        }
        evidence["serial_matches"] = actual_serial == expected_serial
        if actual_serial != expected_serial:
            evidence["error"] = "controller serial did not match; budget probe stopped"
            return evidence
        complete = controller.Read(COMPLETE_TAG)
        large = controller.Read(LARGE_TAG, 1024)
        fingerprint = (
            _success(complete)
            and getattr(complete, "Value", None) is True
            and _success(large)
            and isinstance(getattr(large, "Value", None), (list, tuple))
            and len(large.Value) == 1024
        )
        evidence["fixture_fingerprint"] = {
            "passed": fingerprint,
            "test_complete_status": _status(complete),
            "large_array_status": _status(large),
            "large_array_elements": len(large.Value) if isinstance(getattr(large, "Value", None), (list, tuple)) else 0,
        }
        if not fingerprint:
            evidence["error"] = "fixture fingerprint failed; budget probe stopped"
            return evidence

    size_results = []
    for connection_size in connection_sizes:
        started = time.perf_counter()
        try:
            with plc_factory(target) as controller:
                controller.SocketTimeout = timeout
                controller.ConnectionSize = connection_size
                reply = controller.Read(LARGE_TAG, 1024)
            value = getattr(reply, "Value", None)
            passed = _success(reply) and isinstance(value, (list, tuple)) and len(value) == 1024
            status = _status(reply)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            passed = False
            status = f"{type(exc).__name__}: {exc}"
        size_results.append({
            "requested_connection_size": connection_size,
            "payload_bytes": 4096,
            "status": status,
            "passed": passed,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        })
    evidence["connection_sizes"] = size_results

    cycle_results = [_read_once(plc_factory, target, timeout) for _ in range(cycles)]
    evidence["reconnect_cycles"] = {
        "requested": cycles,
        "successful": sum(1 for item in cycle_results if item["passed"]),
        "passed": all(item["passed"] for item in cycle_results),
        "latency": _latency_summary([item["elapsed_ms"] for item in cycle_results]),
        "statuses": sorted({item["status"] for item in cycle_results}),
    }

    tiny_timeout = min(0.0001, timeout)
    timeout_result = _read_once(plc_factory, target, tiny_timeout)
    recovery_result = _read_once(plc_factory, target, timeout)
    evidence["timeout_recovery"] = {
        "induced_timeout_seconds": tiny_timeout,
        "induced_status": timeout_result["status"],
        "induced_failed": not timeout_result["passed"],
        "recovery_status": recovery_result["status"],
        "recovery_passed": recovery_result["passed"],
        "recovery_elapsed_ms": recovery_result["elapsed_ms"],
    }

    concurrency = [
        _concurrent_level(plc_factory, target, timeout, level)
        for level in reader_levels
    ]
    evidence["concurrent_readers"] = concurrency
    required_result = next(item for item in concurrency if item["readers"] == required_readers)
    evidence["required_readers"] = required_readers
    evidence["passed"] = (
        all(item["passed"] for item in size_results if item["requested_connection_size"] <= 500)
        and evidence["reconnect_cycles"]["passed"]
        and evidence["timeout_recovery"]["induced_failed"]
        and evidence["timeout_recovery"]["recovery_passed"]
        and required_result["passed"]
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        import pylogix
        from pylogix import PLC
    except ImportError:
        print("ERROR [transport-budget] install the pinned Phase 0 requirements", file=sys.stderr)
        return 2
    evidence = run_probe(
        PLC,
        args.target,
        args.expect_serial,
        args.timeout,
        args.cycles,
        args.connection_sizes,
        args.reader_levels,
        args.required_readers,
    )
    evidence["client"] = f"pylogix {pylogix.__version__}"
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
