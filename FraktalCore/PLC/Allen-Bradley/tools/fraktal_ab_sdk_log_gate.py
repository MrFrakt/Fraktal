#!/usr/bin/env python3
"""Gate Logix Designer SDK console logs for clean import and operations."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IMPORT_SUMMARY = re.compile(r'<Summary\s+Warnings="(\d+)"\s+Errors="(\d+)"\s*/>')


def audit_log(
    log: str,
    required_operations: tuple[str, ...] = (),
    require_clean_import: bool = False,
) -> dict[str, object]:
    summaries = [
        {"Warnings": int(warnings), "Errors": int(errors)}
        for warnings, errors in IMPORT_SUMMARY.findall(log)
    ]
    sdk_errors = [line for line in log.splitlines() if "][ERROR][" in line]
    missing_operations = [
        operation for operation in required_operations
        if f"] {operation} succeeded" not in log
    ]
    findings: list[str] = []
    if sdk_errors:
        findings.append(f"SDK emitted {len(sdk_errors)} error event(s)")
    if missing_operations:
        findings.append(
            "required successful operations missing: "
            + ", ".join(missing_operations)
        )
    if require_clean_import and not summaries:
        findings.append("clean import summary was required but none was captured")
    dirty_summaries = [
        summary for summary in summaries
        if summary["Warnings"] or summary["Errors"]
    ]
    if dirty_summaries:
        findings.append(f"non-clean import summary: {dirty_summaries}")
    return {
        "Schema": "fraktal.ab.sdk-log-gate",
        "SchemaVersion": 1,
        "ImportSummaries": summaries,
        "SdkErrorEventCount": len(sdk_errors),
        "RequiredOperations": list(required_operations),
        "MissingOperations": missing_operations,
        "Clean": not findings,
        "Findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", type=Path,
                        help="SDK log file; omit to read standard input")
    parser.add_argument("--require", action="append", default=[],
                        help="operation that must emit '<name> succeeded'")
    parser.add_argument("--require-clean-import", action="store_true")
    args = parser.parse_args(argv)
    try:
        content = (args.log.read_text(encoding="utf-8", errors="replace")
                   if args.log else sys.stdin.read())
    except OSError as exc:
        print(f"ERROR [sdk-log-gate] {exc}", file=sys.stderr)
        return 2
    report = audit_log(
        content,
        tuple(args.require),
        args.require_clean_import,
    )
    print(json.dumps(report, indent=2))
    return 0 if report["Clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
