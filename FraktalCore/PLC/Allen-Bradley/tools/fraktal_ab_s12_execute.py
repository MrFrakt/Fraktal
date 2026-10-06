#!/usr/bin/env python3
"""Execute the fixed memory-only S12 type-map fixture vector.

This is not a generic PLC writer. It requires the exact controller serial and
an explicit arm flag, fingerprints the disposable S12 fixture before its first
write, writes only the fixture's own declared inputs with values hard-coded
here, and restores every one of them.

The interesting measurement is the public UDT's layout **as CIP delivers it**,
because that is the image the gateway decodes. Reading the structured tag
returns the raw payload directly, so the measurement needs no support inside
the fixture at all.

It is taken differentially rather than by pattern search: each member is
written twice, with two values whose encodings differ in every byte, and the
payload is read after each. The bytes that changed between the two reads are
that member's storage. A pattern search cannot do this safely, because a
one-byte sentinel collides with any other member holding the same byte; and
diffing a single sentinel against a zeroed baseline is no better, because any
zero byte inside the sentinel is invisible and the field appears to start late.

The type's *padded* size is measured the same honest way: two adjacent
instances carry the same sentinel and the distance between them is the stride.
Trailing padding is invisible on a single instance, so reading one could not
report a size at all.
"""

from __future__ import annotations

import argparse
import json
import math
import string
import struct
import sys
import time
from typing import Any


LAYOUT = "FRK_S12_Layout"
PAIR = "FRK_S12_LayoutPair"
LAYOUT_BYTES = "FRK_S12_LayoutBytes"
PAIR_BYTES = "FRK_S12_PairBytes"
LAYOUT_BYTE_CAPACITY = 128
PAIR_BYTE_CAPACITY = 256
ARRAY = "FRK_S12_Array"
ARRAY_LENGTH = 10

# Each member is probed with a PAIR of values whose encodings differ in every
# byte. Diffing the two images, rather than one image against a zeroed
# baseline, is what makes the measured offset the true start of the field: a
# sentinel that happens to contain a zero byte is indistinguishable from the
# zero baseline in that position, and the field would be reported as starting
# late. `Ratio` is the case that proves it - 2.5 encodes as 00 00 20 40, so
# two of its four bytes would simply vanish.
def _real(pattern: int) -> float:
    return struct.unpack("<f", struct.pack("<I", pattern))[0]


SENTINEL_PAIRS: tuple[tuple[str, int | float, int | float], ...] = (
    ("Flag", 0, 1),
    ("Small", 0x5A, -0x5B),
    ("Medium", 0x1234, -0x1235),
    ("Count", 0x11223344, -0x11223345),
    ("Wide", 0x0102030405060708, -0x0102030405060709),
    ("Ratio", _real(0x44332211), _real(0xBBCCDDEE)),
)
SENTINELS = tuple((name, second) for name, _first, second in SENTINEL_PAIRS)
ZEROES: dict[str, int | float] = {
    "Flag": 0, "Small": 0, "Medium": 0, "Count": 0, "Wide": 0, "Ratio": 0.0,
}

NAN_BITS = 0x7FC00000
TEXT_VECTOR = "Fraktal-S12"
DURATION_VALID_MS = 250
DURATION_INVALID_MS = -1
ARRAY_LOW_VECTOR = 101
ARRAY_HIGH_VECTOR = 909

BROWSE_TAGS = {
    LAYOUT, PAIR, LAYOUT_BYTES, PAIR_BYTES, ARRAY,
    "FRK_S12_Text", "FRK_S12_NanBits", "FRK_S12_NanReal", "FRK_S12_NanIsNan",
    "FRK_S12_RatioResult", "FRK_S12_SmallWrap", "FRK_S12_MediumWrap", "FRK_S12_TextLen",
    "FRK_S12_ArrayEdgeSum", "FRK_S12_DurationMs", "FRK_S12_DurationOk",
    "FRK_S12_ScanCount", "FRK_S12_Complete",
}


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


def _value(controller: Any, tag: str) -> Any:
    reply = controller.Read(tag)
    return getattr(reply, "Value", None) if _success(reply) else None


def _bytes(controller: Any, tag: str, count: int) -> list[int] | None:
    reply = controller.Read(tag, count)
    values = getattr(reply, "Value", None) if _success(reply) else None
    if not isinstance(values, list) or len(values) != count:
        return None
    return [int(item) & 0xFF for item in values]


def _udt_bytes(controller: Any, tag: str, count: int | None = None) -> list[int] | None:
    """Return the raw CIP payload of a structured tag.

    This is the measurement that matters: it is the byte image the gateway
    receives, not the controller's internal copy. It also needs no support
    inside the fixture, which is why it replaced the `COP`-to-`SINT` approach.

    A structured array must be read with an explicit element count; without one
    the controller returns only the first element, which would silently make a
    two-instance stride measurement look like a one-instance read.
    """
    reply = controller.Read(tag) if count is None else controller.Read(tag, count)
    value = getattr(reply, "Value", None) if _success(reply) else None
    if isinstance(value, (bytes, bytearray)):
        return list(value)
    if isinstance(value, list) and value and all(
        isinstance(item, (bytes, bytearray)) for item in value
    ):
        return list(b"".join(value))
    return None


def _wrap(value: int, bits: int) -> int:
    """Two's-complement wrap, so expectations are derived rather than guessed."""
    span = 1 << bits
    return ((value + (span >> 1)) % span) - (span >> 1)


def _settle(controller: Any, delay: float = 0.1) -> None:
    time.sleep(delay)


def discover_layout(controller: Any, settle: float = 0.1) -> dict[str, Any]:
    """Measure each member's storage in the CIP payload by differential reads."""
    for member, value in ZEROES.items():
        controller.Write(f"{LAYOUT}.{member}", value)
    _settle(controller, settle)
    baseline = _udt_bytes(controller, LAYOUT)
    if baseline is None:
        return {"measured": False, "reason": "CIP payload unreadable"}

    members: dict[str, Any] = {}
    measured = True
    for member, low, high in SENTINEL_PAIRS:
        controller.Write(f"{LAYOUT}.{member}", low)
        _settle(controller, settle)
        first = _udt_bytes(controller, LAYOUT)
        controller.Write(f"{LAYOUT}.{member}", high)
        _settle(controller, settle)
        second = _udt_bytes(controller, LAYOUT)
        controller.Write(f"{LAYOUT}.{member}", ZEROES[member])
        if first is None or second is None:
            members[member] = {"located": False}
            measured = False
            continue
        changed = [
            index for index, (before, after) in enumerate(zip(first, second))
            if before != after
        ]
        members[member] = {
            "located": bool(changed),
            "offset": min(changed) if changed else None,
            "width": (max(changed) - min(changed) + 1) if changed else None,
            "contiguous": (
                bool(changed) and changed == list(range(min(changed), max(changed) + 1))
            ),
        }
    _settle(controller, settle)
    return {
        "measured": measured,
        "payloadBytes": len(baseline),
        "members": members,
    }


def discover_stride(controller: Any, settle: float = 0.1) -> dict[str, Any]:
    """Measure the padded size of the type from two adjacent instances."""
    pattern = [0x44, 0x33, 0x22, 0x11]
    for index in (0, 1):
        controller.Write(f"{PAIR}[{index}].Count", 0x11223344)
    _settle(controller, settle)
    image = _udt_bytes(controller, PAIR, 2)
    for index in (0, 1):
        controller.Write(f"{PAIR}[{index}].Count", 0)
    if image is None:
        return {"measured": False, "reason": "pair payload unreadable"}
    positions = [
        index for index in range(len(image) - len(pattern) + 1)
        if image[index:index + len(pattern)] == pattern
    ]
    return {
        "measured": len(positions) == 2,
        "pairPayloadBytes": len(image),
        "positions": positions,
        "strideBytes": (positions[1] - positions[0]) if len(positions) == 2 else None,
    }


def execute_fixture(
    controller: Any, expected_serial: str, settle: float = 0.1
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s12-execution",
        "schema_version": 1,
        "expected_serial": expected_serial,
        "fixture_fingerprint": {"passed": False},
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
    missing = sorted(BROWSE_TAGS - names)
    complete = controller.Read("FRK_S12_Complete")
    scan_before = _value(controller, "FRK_S12_ScanCount")
    _settle(controller, 0.2)
    scan_after = _value(controller, "FRK_S12_ScanCount")
    scanning = (
        isinstance(scan_before, int)
        and isinstance(scan_after, int)
        and scan_after > scan_before
    )
    fingerprint = (
        _success(tag_reply)
        and not missing
        and _success(complete)
        and getattr(complete, "Value", None) is True
        and scanning
    )
    evidence["fixture_fingerprint"] = {
        "passed": fingerprint,
        "tag_list_status": _status(tag_reply),
        "missing_tags": missing,
        "complete_status": _status(complete),
        "task_scanning": scanning,
    }
    if not fingerprint:
        evidence["error"] = "fixture fingerprint failed; no writes attempted"
        return evidence

    checks: list[dict[str, Any]] = []
    try:
        evidence["layout"] = discover_layout(controller, settle)
        evidence["stride"] = discover_stride(controller, settle)

        # exact CIP round trip for every declared width
        roundtrip: dict[str, Any] = {}
        for member, sentinel in SENTINELS:
            controller.Write(f"{LAYOUT}.{member}", sentinel)
        _settle(controller, settle)
        for member, sentinel in SENTINELS:
            observed = _value(controller, f"{LAYOUT}.{member}")
            exact = (
                abs(observed - sentinel) < 1e-9
                if isinstance(sentinel, float) and isinstance(observed, (int, float))
                else observed == sentinel
            )
            roundtrip[member] = {"expected": sentinel, "exact": bool(exact)}
            checks.append({"case": f"roundtrip_{member}", "passed": bool(exact)})
        evidence["roundtrip"] = roundtrip

        # Documented overflow behaviour, provoked only by add/multiply. The
        # expectation is derived from the sentinel actually left in the tag,
        # never hard-coded: the members still hold the second sentinel of each
        # pair from the round-trip writes above.
        small_input = dict(SENTINELS)["Small"]
        medium_input = dict(SENTINELS)["Medium"]
        expected_small = _wrap(small_input * 2, 8)
        expected_medium = _wrap(medium_input * 8, 16)
        small_wrap = _value(controller, "FRK_S12_SmallWrap")
        medium_wrap = _value(controller, "FRK_S12_MediumWrap")
        evidence["overflow"] = {
            "sintInput": small_input, "sintDoubled": small_wrap,
            "sintExpected": expected_small,
            "intInput": medium_input, "intTimesEight": medium_wrap,
            "intExpected": expected_medium,
            "wrapsTwosComplement": (
                small_wrap == expected_small and medium_wrap == expected_medium
            ),
        }
        checks.append({
            "case": "sint_overflow_wraps_twos_complement",
            "passed": small_wrap == expected_small,
        })
        checks.append({
            "case": "int_overflow_wraps_twos_complement",
            "passed": medium_wrap == expected_medium,
        })

        # NaN is copied in, never computed. The contract question is whether
        # the bit pattern survives the round trip; whether Logix ST can *detect*
        # it by self-comparison is a separate observation, and on this target
        # the answer is no, so Fraktal must test the bit pattern instead.
        controller.Write("FRK_S12_NanBits", NAN_BITS)
        _settle(controller, settle)
        nan_flag = _value(controller, "FRK_S12_NanIsNan")
        nan_real = _value(controller, "FRK_S12_NanReal")
        nan_survived = isinstance(nan_real, float) and math.isnan(nan_real)
        evidence["nan"] = {
            "bits": NAN_BITS,
            "readBackIsNan": nan_survived,
            "stSelfCompareDetectsNan": nan_flag == 1,
        }
        checks.append({
            "case": "nan_bit_pattern_survives_cip", "passed": nan_survived,
        })

        # string length semantics
        controller.Write("FRK_S12_Text", TEXT_VECTOR)
        _settle(controller, settle)
        text_len = _value(controller, "FRK_S12_TextLen")
        evidence["string"] = {
            "writtenCharacters": len(TEXT_VECTOR), "reportedLen": text_len,
        }
        checks.append({
            "case": "string_len_counts_bytes",
            "passed": text_len == len(TEXT_VECTOR),
        })

        # zero-based array indexing at both edges
        controller.Write(f"{ARRAY}[0]", ARRAY_LOW_VECTOR)
        controller.Write(f"{ARRAY}[{ARRAY_LENGTH - 1}]", ARRAY_HIGH_VECTOR)
        _settle(controller, settle)
        edge_sum = _value(controller, "FRK_S12_ArrayEdgeSum")
        evidence["array"] = {
            "length": ARRAY_LENGTH, "lowerBound": 0, "edgeSum": edge_sum,
        }
        checks.append({
            "case": "array_zero_based_edges",
            "passed": edge_sum == ARRAY_LOW_VECTOR + ARRAY_HIGH_VECTOR,
        })

        # duration as a range-checked DINT, because the target has no TIME
        controller.Write("FRK_S12_DurationMs", DURATION_VALID_MS)
        _settle(controller, settle)
        accepted = _value(controller, "FRK_S12_DurationOk")
        controller.Write("FRK_S12_DurationMs", DURATION_INVALID_MS)
        _settle(controller, settle)
        rejected = _value(controller, "FRK_S12_DurationOk")
        evidence["duration"] = {
            "validMs": DURATION_VALID_MS, "validAccepted": accepted,
            "invalidMs": DURATION_INVALID_MS, "invalidAccepted": rejected,
        }
        checks.append({"case": "duration_in_range_accepted", "passed": accepted == 1})
        checks.append({"case": "duration_out_of_range_rejected", "passed": rejected == 0})

        evidence["checks"] = checks
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        evidence["error"] = f"fixture execution failed: {type(exc).__name__}: {exc}"
        evidence["checks"] = checks
    finally:
        cleanup_writes = []
        for member, value in ZEROES.items():
            cleanup_writes.append(
                (f"{LAYOUT}.{member}", controller.Write(f"{LAYOUT}.{member}", value))
            )
        for index in (0, 1):
            cleanup_writes.append(
                (f"{PAIR}[{index}].Count",
                 controller.Write(f"{PAIR}[{index}].Count", 0))
            )
        cleanup_writes.append((f"{ARRAY}[0]", controller.Write(f"{ARRAY}[0]", 0)))
        cleanup_writes.append(
            (f"{ARRAY}[{ARRAY_LENGTH - 1}]",
             controller.Write(f"{ARRAY}[{ARRAY_LENGTH - 1}]", 0))
        )
        cleanup_writes.append(
            ("FRK_S12_Text", controller.Write("FRK_S12_Text", ""))
        )
        cleanup_writes.append(
            ("FRK_S12_NanBits", controller.Write("FRK_S12_NanBits", 0))
        )
        cleanup_writes.append(
            ("FRK_S12_DurationMs", controller.Write("FRK_S12_DurationMs", 0))
        )
        _settle(controller, 0.2)
        cleanup_checks = [
            {"case": "cleanup_count", "passed": _value(controller, f"{LAYOUT}.Count") == 0},
            {"case": "cleanup_text", "passed": _value(controller, "FRK_S12_TextLen") == 0},
            {"case": "cleanup_array", "passed": _value(controller, "FRK_S12_ArrayEdgeSum") == 0},
            {"case": "cleanup_nan_bits", "passed": _value(controller, "FRK_S12_NanBits") == 0},
            {"case": "cleanup_duration", "passed": _value(controller, "FRK_S12_DurationMs") == 0},
        ]
        evidence["cleanup"] = {
            "attempted": True,
            "writes": [
                {"tag": tag, "status": _status(reply), "passed": _success(reply)}
                for tag, reply in cleanup_writes
            ],
            "checks": cleanup_checks,
            "verified": all(_success(reply) for _, reply in cleanup_writes)
            and all(item["passed"] for item in cleanup_checks),
        }

    evidence["execution_passed"] = (
        "error" not in evidence
        and bool(evidence["checks"])
        and all(item["passed"] for item in evidence["checks"])
        and evidence.get("layout", {}).get("measured", False)
        and evidence.get("stride", {}).get("measured", False)
        and evidence["cleanup"]["verified"]
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR [s12-execution] install the pinned Phase 0 requirements",
            file=sys.stderr,
        )
        return 2
    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            evidence = execute_fixture(controller, args.expect_serial)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [s12-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
