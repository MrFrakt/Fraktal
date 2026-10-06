#!/usr/bin/env python3
"""Read selected Logix tags and report transport evidence without values.

This Phase 0 probe contains no write, clock-set, mode, upload, or download call.
It reports only status, value shape, and elapsed time for explicitly named tags.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReadCase:
    label: str
    tag: str
    elements: int | None = None


def _parse_case(value: str, array: bool = False) -> ReadCase:
    try:
        label, request = value.split("=", 1)
        if not label or not request:
            raise ValueError
        if not array:
            return ReadCase(label, request)
        tag, count_text = request.rsplit(",", 1)
        count = int(count_text)
        if not tag or count <= 0:
            raise ValueError
        return ReadCase(label, tag, count)
    except ValueError as exc:
        expected = "LABEL=TAG,COUNT" if array else "LABEL=TAG"
        raise argparse.ArgumentTypeError(f"expected {expected}") from exc


def _shape(value: Any) -> dict[str, Any]:
    if value is None:
        return {"kind": "none", "size": 0}
    if isinstance(value, (bytes, bytearray, list, tuple, str)):
        return {"kind": type(value).__name__, "size": len(value)}
    return {"kind": type(value).__name__, "size": 1}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="single controller IPv4 address or host name")
    parser.add_argument("--expect-serial", help="eight-digit hexadecimal CIP serial")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--connection-size", type=int)
    parser.add_argument(
        "--tag", action="append", default=[],
        type=lambda value: _parse_case(value), metavar="LABEL=TAG",
    )
    parser.add_argument(
        "--array", action="append", default=[],
        type=lambda value: _parse_case(value, array=True), metavar="LABEL=TAG,COUNT",
    )
    args = parser.parse_args()
    if not args.tag and not args.array:
        parser.error("at least one --tag or --array is required")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.connection_size is not None and not 128 <= args.connection_size <= 4002:
        parser.error("--connection-size must be between 128 and 4002")
    return args


def main() -> int:
    args = _arguments()
    try:
        import pylogix
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR [symbolic-read-probe] install the pinned Phase 0 requirements",
            file=sys.stderr,
        )
        return 2

    cases: list[ReadCase] = [*args.tag, *args.array]
    results: list[dict[str, Any]] = []
    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            if args.connection_size is not None:
                controller.ConnectionSize = args.connection_size

            device_reply = controller.GetDeviceProperties()
            if device_reply.Status != "Success" or device_reply.Value is None:
                raise RuntimeError(f"identity read failed: {device_reply.Status}")
            device = device_reply.Value
            serial = str(device.SerialNumber).removeprefix("0x").upper().zfill(8)
            expected = args.expect_serial.upper() if args.expect_serial else None

            clock_reply = controller.GetPLCTime()
            clock_value = clock_reply.Value
            clock_iso = clock_value.isoformat() if isinstance(clock_value, dt.datetime) else None
            clock_delta_seconds = None
            if isinstance(clock_value, dt.datetime):
                clock_delta_seconds = round(
                    (dt.datetime.now() - clock_value).total_seconds(), 3
                )

            for case in cases:
                started = time.perf_counter()
                reply = (
                    controller.Read(case.tag)
                    if case.elements is None
                    else controller.Read(case.tag, case.elements)
                )
                results.append({
                    "case": case.label,
                    "elements_requested": case.elements or 1,
                    "status": reply.Status,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    **_shape(reply.Value),
                })

        serial_matches = expected is None or serial == expected
        all_reads_succeeded = all(item["status"] == "Success" for item in results)
        evidence = {
            "schema": "fraktal.ab.symbolic-read-probe",
            "schema_version": 1,
            "client": f"pylogix {pylogix.__version__}",
            "target": args.target,
            "identity": {
                "product_name": device.ProductName,
                "revision": device.Revision,
                "serial_number": serial,
            },
            "expected_serial": expected,
            "serial_matches": serial_matches,
            "connection_size": args.connection_size,
            "clock": {
                "status": clock_reply.Status,
                "controller_local": clock_iso,
                "host_minus_controller_seconds": clock_delta_seconds,
            },
            "values_redacted": True,
            "reads": results,
            "all_reads_succeeded": all_reads_succeeded,
        }
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0 if serial_matches and all_reads_succeeded else 1
    except (OSError, RuntimeError) as exc:
        print(f"ERROR [symbolic-read-probe] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
