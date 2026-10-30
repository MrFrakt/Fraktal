#!/usr/bin/env python3
"""Explicitly executed, bounded effective-access vector on the inert S0 probe.

Requires current owner authorization before use. Only four fixed DINT leaf
paths may be written, and every changed value is restored in finally. Never
imports a station or exposes an arbitrary tag, value, controller or operation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from fraktal_ab_s0_supplementary_measure import guard
from fraktal_ab_s0_supplementary_probe import WRITE_PATHS


def execute(comm):
    report = dict(schema="fraktal.ab.s0-supplementary-access", schemaVersion=1,
                  capturedUtc=datetime.now(timezone.utc).isoformat(), serial="601FC87B",
                  allowedPaths=list(WRITE_PATHS), writes=[], restoration=[], passed=False)
    touched = []
    try:
        guard(comm)
        for path in WRITE_PATHS:
            before = comm.Read(path)
            if before.Status != "Success" or type(before.Value) is not int:
                raise ValueError(f"fixture leaf unavailable: {path}")
            unsigned = (before.Value & 0xFFFFFFFF) ^ 0x13579BDF
            marker = unsigned - (1 << 32) if unsigned >= (1 << 31) else unsigned
            # Record before issuing: a lost response leaves an uncertain write.
            touched.append((path, before.Value))
            guard(comm)
            result = comm.Write(path, marker, 0xC4)
            after = comm.Read(path)
            report["writes"].append(dict(path=path, before=before.Value, stimulus=marker,
                                        writeStatus=result.Status, accepted=result.Status == "Success",
                                        readStatus=after.Status, after=after.Value))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        for path, original in reversed(touched):
            row = dict(path=path, original=original, restored=False)
            try:
                guard(comm)
                current = comm.Read(path)
                if current.Status != "Success":
                    raise ValueError("cannot read original-value restoration target")
                if current.Value != original:
                    guard(comm)
                    row["writeStatus"] = comm.Write(path, original, 0xC4).Status
                checked = comm.Read(path)
                row["restored"] = checked.Status == "Success" and checked.Value == original
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
            report["restoration"].append(row)
    writes = report["writes"]
    report["passed"] = (not report.get("error") and len(writes) == len(WRITE_PATHS)
                        and all(row["restored"] for row in report["restoration"])
                        and all(not row["accepted"] for row in writes if row["path"].endswith(".Readback"))
                        and any(row["path"] == "FRK_S0S_AccessRW.HmiRequest" and row["accepted"]
                                and row["readStatus"] == "Success" and row["after"] == row["stimulus"]
                                for row in writes))
    # RO-parent/RW-child behavior is an observation, not a presumed outcome.
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-serial", required=True, choices=("601FC87B",))
    parser.add_argument("--execute-fixture", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing existing output")
    from pylogix import PLC
    with PLC("127.0.0.1") as comm:
        comm.ProcessorSlot, comm.ConnectionSize, comm.SocketTimeout = 0, 4000, 5
        report = execute(comm)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(passed=report["passed"], writes=len(report["writes"]),
                          restored=all(row["restored"] for row in report["restoration"]))))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
