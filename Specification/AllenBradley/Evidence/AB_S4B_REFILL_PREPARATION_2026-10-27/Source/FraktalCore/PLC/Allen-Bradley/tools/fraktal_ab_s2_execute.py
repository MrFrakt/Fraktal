#!/usr/bin/env python3
"""Execute the fixed memory-only S2 nested-AOI fixture vector.

This is not a generic PLC writer. It requires the exact controller serial and
an explicit arm flag, fingerprints the disposable fixture before its first
write, writes only ``FRK_S2_Ctx.Command`` and ``FRK_S2_Text``, and restores both
to zero/empty. It has no I/O, clock, mode, download, fault, reset, firmware, or
network-configuration operation.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
import time
from typing import Any


BROWSE_TAGS = {
    "FRK_S2_Complete",
    "FRK_S2_Ctx",
    "FRK_S2_Output",
    "FRK_S2_ScanCount",
    "FRK_S2_Text",
}
HIDDEN_INSTANCE = "FRK_S2_Instance"
COMMAND = "FRK_S2_Ctx.Command"
TEXT = "FRK_S2_Text"
STRING_VECTOR = "Fraktal-S2"
COMMAND_VECTOR = 42000


def _normalize_serial(value: Any) -> str:
    serial = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(serial) != 8 or any(character not in string.hexdigits for character in serial):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return serial


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not args.execute_fixture:
        parser.error("--execute-fixture is required")
    args.expect_serial = _normalize_serial(args.expect_serial)
    return args


def _success(reply: Any) -> bool:
    return getattr(reply, "Status", None) == "Success"


def _status(reply: Any) -> str:
    return str(getattr(reply, "Status", "missing response"))


def _check(controller: Any, case: str, tag: str, expected: Any) -> dict[str, Any]:
    reply = controller.Read(tag)
    return {
        "case": case,
        "status": _status(reply),
        "passed": _success(reply) and getattr(reply, "Value", None) == expected,
    }


def execute_fixture(controller: Any, expected_serial: str, settle: float = 0.12) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s2-execution",
        "schema_version": 1,
        "expected_serial": expected_serial,
        "values_redacted": True,
        "fixture_fingerprint": {"passed": False},
        "writes": [],
        "checks": [],
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
    complete = controller.Read("FRK_S2_Complete")
    scan = controller.Read("FRK_S2_ScanCount")
    depth = controller.Read("FRK_S2_Ctx.DepthSeen")
    private = controller.Read("FRK_S2_Ctx.PrivateMarker")
    instance = controller.Read(HIDDEN_INSTANCE)
    missing = sorted(BROWSE_TAGS - names)
    fingerprint = (
        _success(tag_reply)
        and not missing
        and HIDDEN_INSTANCE not in names
        and _success(complete)
        and getattr(complete, "Value", None) is True
        and _success(scan)
        and _success(depth)
        and getattr(depth, "Value", None) == 8
        and not _success(private)
        and not _success(instance)
    )
    evidence["fixture_fingerprint"] = {
        "passed": fingerprint,
        "tag_list_status": _status(tag_reply),
        "missing_tags": missing,
        "instance_hidden": HIDDEN_INSTANCE not in names,
        "complete_status": _status(complete),
        "depth_status": _status(depth),
        "private_read_status": _status(private),
        "instance_read_status": _status(instance),
    }
    if not fingerprint:
        evidence["error"] = "fixture fingerprint failed; no writes attempted"
        return evidence

    scan_before = getattr(scan, "Value", None)
    try:
        negative = {
            "result_write": controller.Write("FRK_S2_Ctx.Result", 90001),
            "depth_write": controller.Write("FRK_S2_Ctx.DepthSeen", 90002),
            "text_length_write": controller.Write("FRK_S2_Ctx.TextEchoLength", 90003),
            "private_write": controller.Write("FRK_S2_Ctx.PrivateMarker", 90004),
            "instance_write": controller.Write(HIDDEN_INSTANCE, 90005),
        }
        evidence["access_controls"] = {
            name: {"status": _status(reply), "rejected": not _success(reply)}
            for name, reply in negative.items()
        }

        writes = [
            controller.Write(COMMAND, COMMAND_VECTOR),
            controller.Write(TEXT, STRING_VECTOR),
        ]
        evidence["writes"] = [
            {"tag": tag, "status": _status(reply), "passed": _success(reply)}
            for tag, reply in zip((COMMAND, TEXT), writes)
        ]
        time.sleep(settle)
        checks = [
            _check(controller, "command_roundtrip", COMMAND, COMMAND_VECTOR),
            _check(controller, "string_roundtrip", TEXT, STRING_VECTOR),
            _check(controller, "schema_version", "FRK_S2_Ctx.SchemaVersion", 1),
            _check(controller, "nested_result", "FRK_S2_Ctx.Result", 42007),
            _check(controller, "nested_depth", "FRK_S2_Ctx.DepthSeen", 8),
            _check(
                controller, "nested_text_length",
                "FRK_S2_Ctx.TextEchoLength", len(STRING_VECTOR),
            ),
            _check(
                controller, "atomic_output", "FRK_S2_Output",
                42007 + len(STRING_VECTOR),
            ),
        ]
        scan_after = controller.Read("FRK_S2_ScanCount")
        checks.append(
            {
                "case": "scan_advancing",
                "status": _status(scan_after),
                "passed": (
                    _success(scan_after)
                    and isinstance(scan_before, int)
                    and isinstance(getattr(scan_after, "Value", None), int)
                    and scan_after.Value > scan_before
                ),
            }
        )
        evidence["checks"] = checks
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        evidence["error"] = f"fixture execution failed: {type(exc).__name__}: {exc}"
    finally:
        cleanup_replies = [controller.Write(COMMAND, 0), controller.Write(TEXT, "")]
        time.sleep(settle)
        cleanup_checks = [
            _check(controller, "cleanup_command", COMMAND, 0),
            _check(controller, "cleanup_text", TEXT, ""),
            _check(controller, "cleanup_result", "FRK_S2_Ctx.Result", 7),
            _check(controller, "cleanup_text_length", "FRK_S2_Ctx.TextEchoLength", 0),
            _check(controller, "cleanup_output", "FRK_S2_Output", 7),
        ]
        cleanup_writes = [
            {"tag": tag, "status": _status(reply), "passed": _success(reply)}
            for tag, reply in zip((COMMAND, TEXT), cleanup_replies)
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
        all(item["passed"] for item in evidence["writes"])
        and all(
            item["rejected"]
            for item in evidence.get("access_controls", {}).values()
        )
        and all(item["passed"] for item in evidence["checks"])
        and evidence["cleanup"]["verified"]
        and "error" not in evidence
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        from pylogix import PLC
    except ImportError:
        print("ERROR [s2-execution] install the pinned Phase 0 requirements", file=sys.stderr)
        return 2
    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            evidence = execute_fixture(controller, args.expect_serial)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [s2-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
