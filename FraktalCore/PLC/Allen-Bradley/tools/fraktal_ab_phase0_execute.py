#!/usr/bin/env python3
"""Execute the fixed, memory-only Allen-Bradley Phase 0 conformance vector.

The command is intentionally not a generic PLC writer.  It requires an expected
controller serial and an explicit arming flag, fingerprints the disposable
``FRK_*`` fixture before the first write, writes only the fixed fixture tags,
and restores all writable inputs to zero/empty values before returning.  It has
no I/O, clock, mode, upload, download, reset, fault-clear, or firmware service.
"""
from __future__ import annotations

import argparse
import json
import math
import string
import sys
import time
from typing import Any


EXPECTED_TAGS = (
    "FRK_Heartbeat",
    "FRK_LargeResult",
    "FRK_NoAccess",
    "FRK_ReadOnly",
    "FRK_Result",
    "FRK_ScanCount",
    "FRK_TestComplete",
    "FRK_WriteArray",
    "FRK_WriteDint",
    "FRK_WriteLargeArray",
    "FRK_WriteReal",
    "FRK_WriteString",
    "FRK_WriteUdt",
)
BROWSE_TAGS = tuple(tag for tag in EXPECTED_TAGS if tag != "FRK_NoAccess")
PROGRAM_WRITE_TAG = "Program:FRK_Phase0Program.FRK_ProgramWriteDint"
PROGRAM_RESULT_TAG = "Program:FRK_Phase0Program.FRK_ProgramResult"

ARRAY_VECTOR = [1000 + index for index in range(25)]
LARGE_ARRAY_VECTOR = [2000 + index for index in range(1024)]
UDT_SAMPLES = [7, 11, 13, 17]
STRING_VECTOR = "Fraktal-P0"
WRITE_VECTOR: tuple[tuple[str, Any], ...] = (
    ("FRK_WriteDint", 41001),
    ("FRK_WriteReal", 12.5),
    ("FRK_WriteArray[0]", ARRAY_VECTOR),
    ("FRK_WriteLargeArray[0]", LARGE_ARRAY_VECTOR),
    ("FRK_WriteString", STRING_VECTOR),
    ("FRK_WriteUdt.DintValue", 42001),
    ("FRK_WriteUdt.RealBits", 43),
    ("FRK_WriteUdt.Checksum", 44001),
    ("FRK_WriteUdt.Samples[0]", UDT_SAMPLES),
    (PROGRAM_WRITE_TAG, 45001),
)
CLEANUP_VECTOR: tuple[tuple[str, Any], ...] = (
    ("FRK_WriteDint", 0),
    ("FRK_WriteReal", 0.0),
    ("FRK_WriteArray[0]", [0] * 25),
    ("FRK_WriteLargeArray[0]", [0] * 1024),
    ("FRK_WriteString", ""),
    ("FRK_WriteUdt.DintValue", 0),
    ("FRK_WriteUdt.RealBits", 0),
    ("FRK_WriteUdt.Checksum", 0),
    ("FRK_WriteUdt.Samples[0]", [0] * 4),
    (PROGRAM_WRITE_TAG, 0),
)


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="single controller IPv4 address or host name")
    parser.add_argument(
        "--expect-serial",
        required=True,
        help="required eight-digit hexadecimal CIP serial",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--execute-fixture",
        action="store_true",
        help="arm the fixed FRK_* memory-tag vector",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not args.execute_fixture:
        parser.error("--execute-fixture is required")
    args.expect_serial = _normalize_serial(args.expect_serial)
    return args


def _normalize_serial(value: Any) -> str:
    serial = str(value).removeprefix("0x").removeprefix("0X").upper()
    if len(serial) != 8 or any(character not in string.hexdigits for character in serial):
        raise argparse.ArgumentTypeError("serial must be eight hexadecimal digits")
    return serial


def _success(reply: Any) -> bool:
    return getattr(reply, "Status", None) == "Success"


def _status(reply: Any) -> str:
    return str(getattr(reply, "Status", "missing response"))


def _shape(value: Any) -> dict[str, Any]:
    if value is None:
        return {"kind": "none", "size": 0}
    if isinstance(value, (bytes, bytearray, list, tuple, str)):
        return {"kind": type(value).__name__, "size": len(value)}
    return {"kind": type(value).__name__, "size": 1}


def _equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float):
        return isinstance(actual, (float, int)) and math.isclose(
            float(actual), expected, rel_tol=1e-6, abs_tol=1e-6
        )
    if isinstance(expected, list):
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(
            _equal(observed, wanted) for observed, wanted in zip(actual, expected)
        )
    return actual == expected


def _expected_checksum() -> int:
    return (
        41001
        + len(STRING_VECTOR)
        + 42001
        + 43
        + sum(UDT_SAMPLES)
        + ARRAY_VECTOR[0]
        + ARRAY_VECTOR[1]
        + ARRAY_VECTOR[23]
        + ARRAY_VECTOR[24]
    )


def _expected_large_checksum() -> int:
    return (
        45001
        + LARGE_ARRAY_VECTOR[0]
        + LARGE_ARRAY_VECTOR[1]
        + LARGE_ARRAY_VECTOR[1022]
        + LARGE_ARRAY_VECTOR[1023]
    )


def _read_check(controller: Any, name: str, tag: str, expected: Any) -> dict[str, Any]:
    count = len(expected) if isinstance(expected, list) else 1
    reply = controller.Read(tag, count) if count > 1 else controller.Read(tag)
    return {
        "case": name,
        "status": _status(reply),
        **_shape(getattr(reply, "Value", None)),
        "passed": _success(reply) and _equal(getattr(reply, "Value", None), expected),
    }


def _write_cases(controller: Any, vector: tuple[tuple[str, Any], ...]) -> list[dict[str, Any]]:
    return [
        {"tag": tag, "status": _status(reply), "passed": _success(reply)}
        for tag, value in vector
        for reply in (controller.Write(tag, value),)
    ]


def execute_fixture(controller: Any, expected_serial: str, settle_seconds: float = 0.12) -> dict[str, Any]:
    """Run the fixed vector against an already-created pylogix PLC object."""
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.phase0-execution",
        "schema_version": 1,
        "expected_serial": expected_serial,
        "values_redacted": True,
        "fixture_fingerprint": {"passed": False},
        "writes": [],
        "access_controls": {},
        "checks": [],
        "cleanup": {"attempted": False, "verified": False},
        "execution_passed": False,
    }

    device_reply = controller.GetDeviceProperties()
    if not _success(device_reply) or getattr(device_reply, "Value", None) is None:
        evidence["error"] = f"identity read failed: {_status(device_reply)}"
        return evidence
    device = device_reply.Value
    actual_serial = _normalize_serial(device.SerialNumber)
    evidence["identity"] = {
        "product_name": device.ProductName,
        "revision": device.Revision,
        "serial_number": actual_serial,
    }
    evidence["serial_matches"] = actual_serial == expected_serial
    if actual_serial != expected_serial:
        evidence["error"] = "controller serial did not match; no writes attempted"
        return evidence

    tag_reply = controller.GetTagList(False)
    tag_names = {
        getattr(tag, "TagName", "") for tag in (getattr(tag_reply, "Value", None) or [])
    }
    missing = sorted(set(BROWSE_TAGS) - tag_names)
    no_access_hidden = "FRK_NoAccess" not in tag_names
    complete_reply = controller.Read("FRK_TestComplete")
    array_reply = controller.Read("FRK_WriteArray[0]", 25)
    large_array_reply = controller.Read("FRK_WriteLargeArray[0]", 1024)
    result_reply = controller.Read("FRK_Result")
    large_result_reply = controller.Read("FRK_LargeResult")
    program_write_reply = controller.Read(PROGRAM_WRITE_TAG)
    program_result_reply = controller.Read(PROGRAM_RESULT_TAG)
    no_access_reply = controller.Read("FRK_NoAccess")
    fingerprint_passed = (
        _success(tag_reply)
        and not missing
        and no_access_hidden
        and _success(complete_reply)
        and getattr(complete_reply, "Value", None) is True
        and _success(array_reply)
        and _shape(getattr(array_reply, "Value", None))["size"] == 25
        and _success(large_array_reply)
        and _shape(getattr(large_array_reply, "Value", None))["size"] == 1024
        and _success(result_reply)
        and _shape(getattr(result_reply, "Value", None))["size"] == 28
        and _success(large_result_reply)
        and _shape(getattr(large_result_reply, "Value", None))["size"] == 28
        and _success(program_write_reply)
        and _success(program_result_reply)
        and not _success(no_access_reply)
    )
    evidence["fixture_fingerprint"] = {
        "passed": fingerprint_passed,
        "tag_list_status": _status(tag_reply),
        "missing_tags": missing,
        "no_access_hidden": no_access_hidden,
        "test_complete_status": _status(complete_reply),
        "array_shape": _shape(getattr(array_reply, "Value", None)),
        "large_array_shape": _shape(getattr(large_array_reply, "Value", None)),
        "result_shape": _shape(getattr(result_reply, "Value", None)),
        "large_result_shape": _shape(getattr(large_result_reply, "Value", None)),
        "program_write_status": _status(program_write_reply),
        "program_result_status": _status(program_result_reply),
        "no_access_read_status": _status(no_access_reply),
    }
    if not fingerprint_passed:
        evidence["error"] = "fixture fingerprint failed; no writes attempted"
        return evidence

    scan_before = controller.Read("FRK_ScanCount")
    heartbeat_before = controller.Read("FRK_Heartbeat")
    try:
        read_only_write = controller.Write("FRK_ReadOnly", 90001)
        no_access_write = controller.Write("FRK_NoAccess", 90002)
        evidence["access_controls"] = {
            "read_only_write_status": _status(read_only_write),
            "read_only_write_rejected": not _success(read_only_write),
            "no_access_write_status": _status(no_access_write),
            "no_access_write_rejected": not _success(no_access_write),
        }

        evidence["writes"] = _write_cases(controller, WRITE_VECTOR)
        time.sleep(settle_seconds)
        checks = [
            _read_check(controller, "dint_roundtrip", "FRK_WriteDint", 41001),
            _read_check(controller, "real_roundtrip", "FRK_WriteReal", 12.5),
            _read_check(controller, "array_roundtrip", "FRK_WriteArray[0]", ARRAY_VECTOR),
            _read_check(controller, "large_array_roundtrip", "FRK_WriteLargeArray[0]", LARGE_ARRAY_VECTOR),
            _read_check(controller, "string_roundtrip", "FRK_WriteString", STRING_VECTOR),
            _read_check(controller, "udt_dint_roundtrip", "FRK_WriteUdt.DintValue", 42001),
            _read_check(controller, "udt_real_bits_roundtrip", "FRK_WriteUdt.RealBits", 43),
            _read_check(controller, "udt_checksum_roundtrip", "FRK_WriteUdt.Checksum", 44001),
            _read_check(controller, "udt_array_roundtrip", "FRK_WriteUdt.Samples[0]", UDT_SAMPLES),
            _read_check(controller, "result_dint", "FRK_Result.DintValue", 41001),
            _read_check(controller, "result_real_bits", "FRK_Result.RealBits", 43),
            _read_check(controller, "result_samples", "FRK_Result.Samples[0]", [1000, 1001, 1023, 1024]),
            _read_check(controller, "result_checksum", "FRK_Result.Checksum", _expected_checksum()),
            _read_check(controller, "program_dint_roundtrip", PROGRAM_WRITE_TAG, 45001),
            _read_check(controller, "program_result", PROGRAM_RESULT_TAG, 45101),
            _read_check(controller, "large_result_dint", "FRK_LargeResult.DintValue", 45001),
            _read_check(controller, "large_result_samples", "FRK_LargeResult.Samples[0]", [2000, 2001, 3022, 3023]),
            _read_check(controller, "large_result_checksum", "FRK_LargeResult.Checksum", _expected_large_checksum()),
            _read_check(controller, "read_only_derivation", "FRK_ReadOnly", 41002),
            _read_check(controller, "test_complete", "FRK_TestComplete", True),
        ]
        scan_after = controller.Read("FRK_ScanCount")
        heartbeat_after = controller.Read("FRK_Heartbeat")
        scan_advancing = (
            _success(scan_before)
            and _success(scan_after)
            and isinstance(scan_before.Value, int)
            and isinstance(scan_after.Value, int)
            and scan_after.Value > scan_before.Value
        )
        heartbeat_advancing = (
            _success(heartbeat_before)
            and _success(heartbeat_after)
            and isinstance(heartbeat_before.Value, int)
            and isinstance(heartbeat_after.Value, int)
            and heartbeat_after.Value > heartbeat_before.Value
        )
        checks.extend([
            {"case": "scan_count_advancing", "status": _status(scan_after), "passed": scan_advancing},
            {"case": "heartbeat_advancing", "status": _status(heartbeat_after), "passed": heartbeat_advancing},
        ])
        evidence["checks"] = checks
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        evidence["error"] = f"fixture execution failed: {type(exc).__name__}: {exc}"
    finally:
        cleanup_writes = _write_cases(controller, CLEANUP_VECTOR)
        time.sleep(settle_seconds)
        cleanup_checks = [
            _read_check(controller, "cleanup_dint", "FRK_WriteDint", 0),
            _read_check(controller, "cleanup_real", "FRK_WriteReal", 0.0),
            _read_check(controller, "cleanup_array", "FRK_WriteArray[0]", [0] * 25),
            _read_check(controller, "cleanup_large_array", "FRK_WriteLargeArray[0]", [0] * 1024),
            _read_check(controller, "cleanup_string", "FRK_WriteString", ""),
            _read_check(controller, "cleanup_udt_dint", "FRK_WriteUdt.DintValue", 0),
            _read_check(controller, "cleanup_udt_real_bits", "FRK_WriteUdt.RealBits", 0),
            _read_check(controller, "cleanup_udt_checksum", "FRK_WriteUdt.Checksum", 0),
            _read_check(controller, "cleanup_udt_samples", "FRK_WriteUdt.Samples[0]", [0] * 4),
            _read_check(controller, "cleanup_program_dint", PROGRAM_WRITE_TAG, 0),
            _read_check(controller, "cleanup_program_result", PROGRAM_RESULT_TAG, 100),
            _read_check(controller, "cleanup_result_checksum", "FRK_Result.Checksum", 0),
            _read_check(controller, "cleanup_large_result_checksum", "FRK_LargeResult.Checksum", 0),
        ]
        evidence["cleanup"] = {
            "attempted": True,
            "writes": cleanup_writes,
            "checks": cleanup_checks,
            "verified": all(item["passed"] for item in cleanup_writes + cleanup_checks),
        }

    evidence["execution_passed"] = (
        all(item["passed"] for item in evidence["writes"])
        and all(evidence["access_controls"].get(key, False) for key in (
            "read_only_write_rejected", "no_access_write_rejected"
        ))
        and all(item["passed"] for item in evidence["checks"])
        and evidence["cleanup"]["verified"]
        and "error" not in evidence
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        import pylogix
        from pylogix import PLC
    except ImportError:
        print("ERROR [phase0-execution] install the pinned Phase 0 requirements", file=sys.stderr)
        return 2

    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            evidence = execute_fixture(controller, args.expect_serial)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [phase0-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    evidence["client"] = f"pylogix {pylogix.__version__}"
    evidence["target"] = args.target
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
