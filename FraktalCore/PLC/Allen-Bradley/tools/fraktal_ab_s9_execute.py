#!/usr/bin/env python3
"""Measure snapshot coherence under concurrent mutation (S9).

S7 found every manifest snapshot coherent, but nothing was changing the
manifest at the time. This vector supplies the missing half: it makes data
change *under* the reader and then asks whether the coherence guard AB §3.10
specifies — read the revision, read the data, read the revision again, accept
only if it did not move — actually catches it.

Three questions, in the order that makes the answers mean something:

1. **Does the guard produce false rejections?** With the fixture frozen, a
   guarded read must succeed and the payload must be internally consistent. A
   guard that rejects a quiet controller is useless.
2. **Does tearing actually occur?** With fast mutation, an *unguarded* read must
   be observably inconsistent. If it never tears, the rest of the experiment
   proves nothing and the tool says so rather than reporting a passing guard.
3. **Is retry-until-stable viable?** Sweeping the mutation period measures how
   often a guarded read succeeds. If a plausible rate makes coherent reads
   impossible, retry is not a gateway strategy and the snapshot needs PLC-side
   double buffering.

The safety property that matters most is checked on every accepted read: **an
accepted snapshot shall never be internally inconsistent.** A guard that accepts
a torn read is worse than no guard, because it launders bad data as good.

Writes are limited to the fixture's two declared inputs, both restored.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
import time
from typing import Any


DATA = "FRK_S9_Data"
DATA_LENGTH = 1024
REVISION_TAG = "FRK_S9_DataRevision"
FREEZE = "FRK_S9_Freeze"
PERIOD = "FRK_S9_MutationPeriod"
DEFAULT_PERIOD = 10

BROWSE_TAGS = {
    DATA, REVISION_TAG, FREEZE, PERIOD, "FRK_S9_Generation", "FRK_S9_Mutations",
    "FRK_S9_PeriodInUse", "FRK_S9_ScanCount", "FRK_S9_Complete",
}

# Mutation periods in task scans; the task is 10 ms, so 1 -> every 10 ms and
# 100 -> every second. A 4 KiB read takes a few hundred ms at the conservative
# connection size, so the fast end must tear and the slow end must not.
DEFAULT_SWEEP = (1, 5, 20, 100)


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
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument(
        "--sweep", default=",".join(str(x) for x in DEFAULT_SWEEP),
        help="comma-separated mutation periods in task scans",
    )
    parser.add_argument("--execute-fixture", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 1 <= args.attempts <= 50:
        parser.error("--attempts must be between 1 and 50")
    try:
        sweep = tuple(int(item) for item in args.sweep.split(","))
    except ValueError:
        parser.error("--sweep must be a comma-separated integer list")
    if not sweep or any(not 1 <= item <= 1000 for item in sweep):
        parser.error("every sweep period must be between 1 and 1000")
    args.sweep = sweep
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


def _read_payload(controller: Any) -> list[int] | None:
    reply = controller.Read(DATA, DATA_LENGTH)
    values = getattr(reply, "Value", None) if _success(reply) else None
    if not isinstance(values, list) or len(values) != DATA_LENGTH:
        return None
    return values


def _consistent(payload: list[int]) -> bool:
    """A coherent snapshot has every element on the same generation."""
    return len(set(payload)) == 1


def guarded_read(controller: Any) -> dict[str, Any]:
    """The AB §3.10 reader rule: revision, payload, revision, accept if equal."""
    before = _value(controller, REVISION_TAG)
    started = time.perf_counter()
    payload = _read_payload(controller)
    elapsed = (time.perf_counter() - started) * 1000.0
    after = _value(controller, REVISION_TAG)
    if payload is None or before is None or after is None:
        return {"accepted": False, "reason": "read failed", "elapsedMs": round(elapsed, 3)}
    accepted = before == after
    return {
        "accepted": accepted,
        "revisionBefore": before,
        "revisionAfter": after,
        "elapsedMs": round(elapsed, 3),
        "generations": sorted(set(payload)),
        "internallyConsistent": _consistent(payload),
    }


def unguarded_read(controller: Any) -> dict[str, Any]:
    payload = _read_payload(controller)
    if payload is None:
        return {"read": False}
    return {
        "read": True,
        "generations": sorted(set(payload)),
        "internallyConsistent": _consistent(payload),
    }


def execute_fixture(
    controller: Any,
    expected_serial: str,
    sweep: tuple[int, ...],
    attempts: int,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "fraktal.ab.s9-coherence-execution",
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
    complete = controller.Read("FRK_S9_Complete")
    fingerprint = (
        _success(tag_reply)
        and not missing
        and _success(complete)
        and getattr(complete, "Value", None) is True
    )
    evidence["fixture_fingerprint"] = {
        "passed": fingerprint,
        "missing_tags": missing,
        "complete_status": _status(complete),
    }
    if not fingerprint:
        evidence["error"] = "fixture fingerprint failed; no writes attempted"
        return evidence

    try:
        # 1. frozen: the guard must not reject a quiet controller
        controller.Write(FREEZE, 1)
        time.sleep(0.5)
        frozen = [guarded_read(controller) for _ in range(3)]
        evidence["frozen"] = {
            "reads": frozen,
            "allAccepted": all(item.get("accepted") for item in frozen),
            "allConsistent": all(
                item.get("internallyConsistent") for item in frozen
            ),
        }

        # 2. tearing must be real, or nothing below means anything
        controller.Write(PERIOD, 1)
        controller.Write(FREEZE, 0)
        time.sleep(0.3)
        unguarded = [unguarded_read(controller) for _ in range(5)]
        torn = [item for item in unguarded if item.get("internallyConsistent") is False]
        evidence["unguardedUnderFastMutation"] = {
            "reads": unguarded,
            "tornReadsObserved": len(torn),
            "tearingDemonstrated": bool(torn),
        }

        # 3. does retry-until-stable converge, and at what rate
        sweep_results = []
        for period in sweep:
            controller.Write(PERIOD, period)
            time.sleep(0.3)
            reads = [guarded_read(controller) for _ in range(attempts)]
            accepted = [item for item in reads if item.get("accepted")]
            laundered = [
                item for item in accepted
                if item.get("internallyConsistent") is False
            ]
            sweep_results.append(
                {
                    "mutationPeriodScans": period,
                    "mutationIntervalMs": period * 10,
                    "attempts": len(reads),
                    "accepted": len(accepted),
                    "successRate": round(len(accepted) / len(reads), 3),
                    "medianReadMs": sorted(
                        item.get("elapsedMs", 0.0) for item in reads
                    )[len(reads) // 2],
                    "acceptedButInconsistent": len(laundered),
                }
            )
        evidence["sweep"] = sweep_results

        checks = [
            ("frozen_reads_accepted", evidence["frozen"]["allAccepted"]),
            ("frozen_reads_consistent", evidence["frozen"]["allConsistent"]),
            (
                "tearing_demonstrated",
                evidence["unguardedUnderFastMutation"]["tearingDemonstrated"],
            ),
            # the property that matters: the guard never launders a torn read
            (
                "no_accepted_read_was_inconsistent",
                all(item["acceptedButInconsistent"] == 0 for item in sweep_results),
            ),
            (
                "retry_converges_at_slow_mutation",
                any(
                    item["successRate"] > 0.0
                    for item in sweep_results
                    if item["mutationPeriodScans"] >= 20
                ),
            ),
        ]
        evidence["checks"] = [
            {"case": case, "passed": bool(passed)} for case, passed in checks
        ]
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        evidence["error"] = f"fixture execution failed: {type(exc).__name__}: {exc}"
    finally:
        writes = [
            (FREEZE, controller.Write(FREEZE, 0)),
            (PERIOD, controller.Write(PERIOD, DEFAULT_PERIOD)),
        ]
        time.sleep(0.3)
        evidence["cleanup"] = {
            "attempted": True,
            "writes": [
                {"tag": tag, "status": _status(reply), "passed": _success(reply)}
                for tag, reply in writes
            ],
            "verified": all(_success(reply) for _, reply in writes)
            and _value(controller, FREEZE) == 0
            and _value(controller, PERIOD) == DEFAULT_PERIOD,
        }

    evidence["execution_passed"] = (
        "error" not in evidence
        and bool(evidence["checks"])
        and all(item["passed"] for item in evidence["checks"])
        and evidence["cleanup"]["verified"]
    )
    return evidence


def main() -> int:
    args = _arguments()
    try:
        from pylogix import PLC
    except ImportError:
        print(
            "ERROR [s9-execution] install the pinned Phase 0 requirements",
            file=sys.stderr,
        )
        return 2
    try:
        with PLC(args.target) as controller:
            controller.SocketTimeout = args.timeout
            evidence = execute_fixture(
                controller, args.expect_serial, args.sweep, args.attempts
            )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR [s9-execution] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["execution_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
