#!/usr/bin/env python3
"""Read or explicitly commission the Phase 0 controller wall clock.

The only state-changing operation is pylogix ``SetPLCTime(dst=0)``, armed by
``--set-to-host`` after exact serial and fixture checks.  The command has no tag
write, mode, download, fault, firmware, or network-configuration operation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import string
import sys
import time
from typing import Any, Callable


def _serial(value: Any) -> str:
    result = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(result) != 8 or any(character not in string.hexdigits for character in result):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return result


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="single controller IPv4 address or host name")
    parser.add_argument("--expect-serial", required=True, type=_serial)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--set-to-host",
        action="store_true",
        help="arm the one fixed WallClockTime set from the current host UTC clock",
    )
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args(argv)
    if not 0.1 <= args.timeout <= 60:
        parser.error("--timeout must be between 0.1 and 60 seconds")
    if not 1 <= args.samples <= 50:
        parser.error("--samples must be between 1 and 50")
    return args


def _success(reply: Any) -> bool:
    return getattr(reply, "Status", None) == "Success"


def _status(reply: Any) -> str:
    return str(getattr(reply, "Status", "missing response"))


def _iso(raw_microseconds: Any) -> str | None:
    if not isinstance(raw_microseconds, int):
        return None
    return (
        dt.datetime.fromtimestamp(raw_microseconds / 1_000_000, tz=dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def run_probe(
    plc_factory: Callable[[str], Any],
    target: str,
    expected_serial: str,
    timeout: float,
    set_to_host: bool,
    samples: int,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.wall-clock",
        "schema_version": 1,
        "target": target,
        "expected_serial": expected_serial,
        "set_requested": set_to_host,
        "set_performed": False,
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
            evidence["error"] = "controller serial did not match; clock was not set"
            return evidence

        phase0_fixture = controller.Read("FRK_TestComplete")
        s2_fixture = controller.Read("FRK_S2_Complete")
        fixture_candidates = (
            ("phase0-data-path", phase0_fixture),
            ("s2-nested-aoi", s2_fixture),
        )
        matching_fixtures = [
            (name, reply) for name, reply in fixture_candidates
            if _success(reply) and getattr(reply, "Value", None) is True
        ]
        if len(matching_fixtures) != 1:
            evidence["error"] = "fixture fingerprint failed; clock was not set"
            return evidence
        fixture_name, fixture = matching_fixtures[0]
        evidence["fixture_fingerprint"] = {
            "passed": True,
            "fixture": fixture_name,
            "status": _status(fixture),
        }

        before = controller.GetPLCTime(raw=True)
        evidence["before"] = {
            "status": _status(before),
            "utc": _iso(getattr(before, "Value", None)),
        }
        if not _success(before):
            evidence["error"] = "initial WallClockTime read failed"
            return evidence

        if set_to_host:
            set_reply = controller.SetPLCTime(dst=0)
            evidence["set_status"] = _status(set_reply)
            evidence["set_performed"] = _success(set_reply)
            if not _success(set_reply):
                evidence["error"] = "WallClockTime set failed"
                return evidence

        offsets_ms: list[float] = []
        statuses: list[str] = []
        after_raw = None
        for _ in range(samples):
            host_before_us = time.time_ns() / 1000.0
            reply = controller.GetPLCTime(raw=True)
            host_after_us = time.time_ns() / 1000.0
            statuses.append(_status(reply))
            if _success(reply) and isinstance(reply.Value, int):
                after_raw = reply.Value
                host_midpoint_us = (host_before_us + host_after_us) / 2.0
                offsets_ms.append((reply.Value - host_midpoint_us) / 1000.0)
            time.sleep(0.02)
        all_reads_succeeded = len(offsets_ms) == samples
        evidence["after"] = {
            "statuses": sorted(set(statuses)),
            "samples": samples,
            "successful": len(offsets_ms),
            "utc": _iso(after_raw),
            "controller_minus_host_ms": {
                "minimum": round(min(offsets_ms), 3) if offsets_ms else None,
                "maximum": round(max(offsets_ms), 3) if offsets_ms else None,
            },
        }
        evidence["passed"] = all_reads_succeeded and (not set_to_host or evidence["set_performed"])
    return evidence


def main() -> int:
    args = _arguments()
    try:
        import pylogix
        from pylogix import PLC
    except ImportError:
        print("ERROR [wall-clock] install the pinned Phase 0 requirements", file=sys.stderr)
        return 2
    evidence = run_probe(
        PLC, args.target, args.expect_serial, args.timeout, args.set_to_host, args.samples
    )
    evidence["client"] = f"pylogix {pylogix.__version__}"
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
