#!/usr/bin/env python3
"""AB spike S3 on the controller: what it says about its own health and timing.

Part III marks §8.11 task timing and §8.12 system health PROVISIONAL S3:
"GSV and module objects supply health and timing", reduced to a declared
subset. This harness is the measurement. It is READ-ONLY - it writes no tag and
issues no command - and samples the generated health probe (Core §8.12's
input, TC3's FB_TcSystemHealthProbe) for a few seconds:

* the TASK object's execution time, its maximum and its overlap count;
* the task's real period and jitter, from the wall clock between scans;
* the TimeSynchronize object's IsSynchronized and PTPEnable;
* the FaultLog object's major and minor fault bits.

That the build imported at all is the first answer: Studio refuses a GSV
attribute the controller does not have.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from typing import Any

from fraktal_ab_s16_execute import _normalize_serial, _status, _success, _value
import fraktal_ab_generate as gen
import fraktal_ab_press_execute as px

SCHEMA = "fraktal.ab.s3-health-and-timing"
SCHEMA_VERSION = 1
APP = px.APP


def sample(comm: Any, seconds: float, every: float) -> list[dict[str, Any]]:
    out = []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        probe = px.read_layout(comm, gen.health_probe_tag(APP), gen.health_probe_members())
        if probe is not None:
            probe["at"] = time.monotonic()
            out.append(probe)
        time.sleep(every)
    return out


def run(comm: Any, seconds: float) -> dict[str, Any]:
    period_us = APP.task_period_ms * 1000
    rows: list[dict[str, Any]] = []
    samples = sample(comm, seconds, 0.1)
    first, last = (samples[0], samples[-1]) if samples else ({}, {})

    def row(name, expectation, observed, holds):
        rows.append({"test": name, "suite": SCHEMA, "expectation": expectation,
                     "passed": bool(holds), "observed": observed})

    elapsed = (last.get("at", 0) - first.get("at", 0)) if samples else 0
    scans = (last.get("Samples", 0) - first.get("Samples", 0)) if samples else 0
    rate = scans / elapsed if elapsed > 0 else 0
    row("the_probe_runs_every_scan",
        f"the probe answers and counts one sample per scan: about {1000 // APP.task_period_ms} a second",
        {"reads": len(samples), "seconds": round(elapsed, 3), "scans": scans,
         "scansPerSecond": round(rate, 1)},
        len(samples) >= 10 and abs(rate - 1000 / APP.task_period_ms) <= 0.05 * 1000 / APP.task_period_ms)

    last_scans = [s["TaskLastScanUs"] for s in samples]
    row("task_execution_time",
        "GSV TASK LastScanTime is the routine's execution in us: above zero and inside the period; "
        "MaxScanTime is at least every last scan seen",
        {"lastScanUs": {"min": min(last_scans, default=None), "median":
                        statistics.median(last_scans) if last_scans else None,
                        "max": max(last_scans, default=None)},
         "maxScanUs": last.get("TaskMaxScanUs"), "periodUs": period_us},
        last_scans and 0 < min(last_scans) and max(last_scans) < period_us
        and last.get("TaskMaxScanUs", 0) >= max(last_scans))

    windows = sorted({(s["MaxIntervalUs"], s["MinIntervalUs"], s["MaxJitterUs"]) for s in samples})
    row("task_period_and_jitter",
        "the real period between scans, from the wall clock, published per 1 s window: "
        "the shortest and longest period bracket the declared one",
        {"windows": windows[:20], "periodUs": period_us},
        windows and all(0 < mn <= period_us <= mx for mx, mn, _ in windows if mx))

    overlaps = sorted({s["TaskOverlapCount"] for s in samples})
    row("no_task_overruns",
        "GSV TASK OverlapCount: no overrun while sampled",
        {"overlapCount": overlaps}, len(overlaps) == 1)

    sync = sorted({(s["TimeIsSynchronized"], s["TimePtpEnable"]) for s in samples})
    row("time_quality",
        "GSV TimeSynchronize IsSynchronized and PTPEnable answer, steadily; this bench runs "
        "without PTP (S1, S9), so both are expected 0",
        {"isSynchronizedPtpEnable": sync}, sync == [(0, 0)])

    faults = sorted({(s["MajorFaultBits"], s["MinorFaultBits"]) for s in samples})
    row("controller_fault_bits",
        "GSV FaultLog: no major fault on a running controller; the minor bits are recorded",
        {"majorMinor": faults}, faults and all(major == 0 for major, _ in faults))

    successful = sum(1 for r in rows if r["passed"])
    return {"tests": len(rows), "successful": successful, "failed": len(rows) - successful,
            "passed": successful == len(rows), "rows": rows,
            "first": {k: v for k, v in first.items() if k != "at"},
            "last": {k: v for k, v in last.items() if k != "at"}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--expect-serial", required=True, type=_normalize_serial)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    from pylogix import PLC

    evidence: dict[str, Any] = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                                "target": args.target, "expected_serial": args.expect_serial,
                                "application": APP.name, "wrote": False}
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
        evidence["identity"] = {"product_name": getattr(device, "ProductName", ""),
                                "revision": getattr(device, "Revision", ""),
                                "serial_number": serial}
        evidence["serial_matches"] = serial == args.expect_serial
        if not evidence["serial_matches"]:
            evidence["error"] = "controller serial does not match --expect-serial"
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return 1
        evidence["result"] = run(comm, args.seconds)
    evidence["passed"] = bool(evidence["result"]["passed"])
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
