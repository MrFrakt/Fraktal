#!/usr/bin/env python3
"""Measure manifest size, read cost and revision-change detection (S7).

S7 decides whether one bounded manifest fits the read budget or whether the
binding must split it per root. The decision needs three numbers from the real
controller, not from a spreadsheet:

* **cold read cost** - how long a gateway takes to pull the whole manifest at a
  given connected-message size, which is what a client pays on connect and
  after every configuration change;
* **steady-state poll cost** - how long the header alone takes, which is what a
  gateway actually pays per cycle once it holds a valid manifest; and
* **coherence** - whether a manifest read while the controller is running can be
  shown to be a single consistent snapshot rather than a torn one.

The vector is read-only apart from one input: `FRK_S7_BumpRevision`, which
raises `ConfigRevision` exactly as a configuration change would, so
revision-change detection is measured rather than assumed. That input is
restored before the tool returns.

Coherence is checked the way a gateway must do it: read the header, read the
tables, read the header again, and accept the snapshot only if `ConfigRevision`
did not move across the whole window.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
import time
from typing import Any


HEADER = "FRK_S7_Header"
BUMP = "FRK_S7_BumpRevision"

# name, tag, capacity-member prefix
TABLES: tuple[tuple[str, str], ...] = (
    ("Roots", "FRK_S7_Roots"),
    ("Modules", "FRK_S7_Modules"),
    ("Nameplates", "FRK_S7_Nameplates"),
    ("Fields", "FRK_S7_Fields"),
    ("Operations", "FRK_S7_Operations"),
    ("Localization", "FRK_S7_Localization"),
    ("Rationalization", "FRK_S7_Rationalization"),
    ("OptionalProfiles", "FRK_S7_Profiles"),
)

BROWSE_TAGS = {HEADER, BUMP, "FRK_S7_ScanCount", "FRK_S7_RevisionBumps",
               "FRK_S7_Complete"} | {tag for _, tag in TABLES}

DEFAULT_CONNECTION_SIZES = (500, 4000)


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
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--connection-sizes", default=",".join(str(x) for x in DEFAULT_CONNECTION_SIZES),
        help="comma-separated connected-message sizes to measure",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 1 <= args.repeats <= 10:
        parser.error("--repeats must be between 1 and 10")
    try:
        sizes = tuple(int(item) for item in args.connection_sizes.split(","))
    except ValueError:
        parser.error("--connection-sizes must be a comma-separated integer list")
    if not sizes or any(not 100 <= size <= 4000 for size in sizes):
        parser.error("every connection size must be between 100 and 4000")
    args.sizes = sizes
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


def _payload_length(value: Any) -> int:
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, list):
        return sum(_payload_length(item) for item in value)
    return 0


def read_header(controller: Any) -> dict[str, Any]:
    started = time.perf_counter()
    reply = controller.Read(HEADER)
    elapsed = (time.perf_counter() - started) * 1000.0
    value = getattr(reply, "Value", None) if _success(reply) else None
    return {
        "status": _status(reply),
        "elapsedMs": round(elapsed, 3),
        "bytes": _payload_length(value),
    }


def read_manifest(
    controller: Any, capacities: dict[str, int]
) -> dict[str, Any]:
    """Read every table once and report per-table cost and payload size."""
    tables: dict[str, Any] = {}
    total_bytes = 0
    total_ms = 0.0
    complete = True
    for name, tag in TABLES:
        count = capacities.get(name, 0)
        started = time.perf_counter()
        reply = controller.Read(tag, count) if count > 1 else controller.Read(tag)
        elapsed = (time.perf_counter() - started) * 1000.0
        value = getattr(reply, "Value", None) if _success(reply) else None
        payload = _payload_length(value)
        if not _success(reply) or payload == 0:
            complete = False
        tables[name] = {
            "elements": count,
            "status": _status(reply),
            "elapsedMs": round(elapsed, 3),
            "bytes": payload,
        }
        total_bytes += payload
        total_ms += elapsed
    return {
        "tables": tables,
        "totalBytes": total_bytes,
        "totalMs": round(total_ms, 3),
        "complete": complete,
    }


def coherent_snapshot(
    controller: Any, capacities: dict[str, int]
) -> dict[str, Any]:
    """Read header, tables, header again; accept only a stable ConfigRevision."""
    before = _value(controller, f"{HEADER}.ConfigRevision")
    manifest = read_manifest(controller, capacities)
    after = _value(controller, f"{HEADER}.ConfigRevision")
    return {
        "revisionBefore": before,
        "revisionAfter": after,
        "stable": before is not None and before == after,
        "read": manifest,
    }


def execute_fixture(
    controller_factory: Any,
    target: str,
    expected_serial: str,
    sizes: tuple[int, ...],
    repeats: int,
    timeout: float,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s7-execution",
        "schema_version": 1,
        "expected_serial": expected_serial,
        "fixture_fingerprint": {"passed": False},
        "connectionSizes": list(sizes),
        "measurements": [],
        "checks": [],
        "cleanup": {"attempted": False, "verified": False},
        "execution_passed": False,
    }

    with controller_factory(target) as controller:
        controller.SocketTimeout = timeout
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
            evidence["error"] = "controller serial did not match; nothing measured"
            return evidence

        tag_reply = controller.GetTagList(False)
        names = {
            getattr(tag, "TagName", "")
            for tag in (getattr(tag_reply, "Value", None) or [])
        }
        missing = sorted(BROWSE_TAGS - names)
        complete = controller.Read("FRK_S7_Complete")
        capacities = {
            name: _value(controller, f"{HEADER}.{name}Capacity")
            for name, _ in TABLES
        }
        usable = all(isinstance(value, int) and value > 0 for value in capacities.values())
        fingerprint = (
            _success(tag_reply)
            and not missing
            and _success(complete)
            and getattr(complete, "Value", None) is True
            and usable
        )
        evidence["fixture_fingerprint"] = {
            "passed": fingerprint,
            "missing_tags": missing,
            "complete_status": _status(complete),
            "capacities": capacities,
        }
        if not fingerprint:
            evidence["error"] = "fixture fingerprint failed; nothing measured"
            return evidence
        evidence["capacities"] = capacities

    # Each connection size needs its own session, because the size is
    # negotiated when the connection is opened.
    for size in sizes:
        with controller_factory(target) as controller:
            controller.SocketTimeout = timeout
            controller.ConnectionSize = size
            header = read_header(controller)
            runs = [
                coherent_snapshot(controller, evidence["capacities"])
                for _ in range(repeats)
            ]
            reads = [run["read"] for run in runs]
            evidence["measurements"].append(
                {
                    "connectionSize": size,
                    "headerOnly": header,
                    "manifestBytes": reads[0]["totalBytes"],
                    "coldReadMs": [read["totalMs"] for read in reads],
                    "medianColdReadMs": sorted(read["totalMs"] for read in reads)[
                        len(reads) // 2
                    ],
                    "perTable": reads[0]["tables"],
                    "allComplete": all(read["complete"] for read in reads),
                    "allCoherent": all(run["stable"] for run in runs),
                }
            )

    # revision-change detection: bump once and require the header to move
    with controller_factory(target) as controller:
        controller.SocketTimeout = timeout
        before = _value(controller, f"{HEADER}.ConfigRevision")
        bumps_before = _value(controller, "FRK_S7_RevisionBumps")
        controller.Write(BUMP, 1)
        time.sleep(0.3)
        after = _value(controller, f"{HEADER}.ConfigRevision")
        bumps_after = _value(controller, "FRK_S7_RevisionBumps")
        cleanup = controller.Write(BUMP, 0)
        time.sleep(0.2)
        restored = _value(controller, BUMP)
        evidence["revisionChange"] = {
            "before": before,
            "after": after,
            "detected": isinstance(before, int) and isinstance(after, int)
            and after == before + 1,
            "bumpsBefore": bumps_before,
            "bumpsAfter": bumps_after,
        }
        evidence["cleanup"] = {
            "attempted": True,
            "write": {"tag": BUMP, "status": _status(cleanup)},
            "verified": _success(cleanup) and restored == 0,
        }

    checks = [
        ("every_table_read_completely",
         all(item["allComplete"] for item in evidence["measurements"])),
        ("every_snapshot_coherent",
         all(item["allCoherent"] for item in evidence["measurements"])),
        ("revision_change_detected", evidence["revisionChange"]["detected"]),
        ("header_poll_cheaper_than_full_read", all(
            item["headerOnly"]["elapsedMs"] < item["medianColdReadMs"]
            for item in evidence["measurements"]
        )),
        ("cleanup_verified", evidence["cleanup"]["verified"]),
    ]
    evidence["checks"] = [
        {"case": case, "passed": bool(passed)} for case, passed in checks
    ]
    evidence["execution_passed"] = all(
        item["passed"] for item in evidence["checks"]
    ) and "error" not in evidence
    return evidence


def main() -> int:
    args = _arguments()
    try:
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR [s7-execution] install the pinned Phase 0 requirements",
            file=sys.stderr,
        )
        return 2
    try:
        evidence = execute_fixture(
            PLC, args.target, args.expect_serial, args.sizes,
            args.repeats, args.timeout,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [s7-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
