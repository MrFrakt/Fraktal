#!/usr/bin/env python3
"""Validate a TcUnit summary log and emit a small JUnit gate result."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SUMMARY_FIELDS = {
    "successful": re.compile(r"\bSuccessful tests:\s*(\d+)\b"),
    "failed": re.compile(r"\bFailed tests:\s*(\d+)\b"),
    "tests": re.compile(r"(?<!Successful )(?<!Failed )\bTests:\s*(\d+)\b"),
    "suites": re.compile(r"\bTest suites:\s*(\d+)\b"),
    "duration": re.compile(r"\bDuration:\s*([0-9.eE+-]+)\b"),
}
RUNNER_PATTERN = re.compile(r"\bTest class name=([A-Za-z_][A-Za-z0-9_]*)\.")

# XML 1.0 permits only tab/LF/CR below U+0020, plus a few excluded ranges.
# ElementTree does not reject the rest, it writes them through - which yields a
# JUnit artifact the CI consumer cannot parse, i.e. a gate result that silently
# reports nothing. XAE event text is raw controller output, so sanitize it here.
_XML_ILLEGAL = re.compile(
    "[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]"
)


def xml_safe(text: str) -> str:
    """Replace characters XML 1.0 forbids so the emitted report stays parseable."""
    return _XML_ILLEGAL.sub("\ufffd", text)


def parse_summary(text: str) -> dict[str, int | float]:
    """Parse the one TcUnit summary block in `text`.

    Fields are matched independently, so a log holding more than one summary
    must be rejected rather than reduced to its first hit: a capture window that
    caught a green run followed by a red re-run would otherwise report the green
    counts and pass the gate. A gate may not guess which run it is grading.
    """
    values: dict[str, int | float] = {}
    missing: list[str] = []
    duplicated: list[str] = []
    for name, pattern in SUMMARY_FIELDS.items():
        matches = pattern.findall(text)
        if not matches:
            missing.append(name)
            continue
        if len(matches) > 1:
            duplicated.append(f"{name} x{len(matches)}")
            continue
        values[name] = float(matches[0]) if name == "duration" else int(matches[0])
    if missing:
        raise ValueError(f"missing TcUnit summary field(s): {', '.join(missing)}")
    if duplicated:
        raise ValueError(
            "ambiguous log: more than one TcUnit summary "
            f"({', '.join(duplicated)}); capture exactly one run"
        )
    return values


def parse_runners(text: str) -> set[str]:
    """Return the PLC program names observed in TcUnit test-class paths."""
    return set(RUNNER_PATTERN.findall(text))


def write_junit(
    output: Path,
    gate_name: str,
    summary: dict[str, int | float] | None,
    errors: list[str],
    source_text: str,
) -> None:
    duration = float(summary["duration"]) if summary else 0.0
    suite = ET.Element(
        "testsuite",
        {
            "name": gate_name,
            "tests": "1",
            "failures": "1" if errors else "0",
            "errors": "0",
            "time": f"{duration:.9g}",
        },
    )
    case = ET.SubElement(
        suite,
        "testcase",
        {"classname": "TcUnit", "name": "runtime summary", "time": f"{duration:.9g}"},
    )
    if errors:
        failure = ET.SubElement(
            case, "failure", {"message": xml_safe("; ".join(errors))}
        )
        failure.text = xml_safe("\n".join(errors))
    if summary:
        properties = ET.SubElement(suite, "properties")
        for name in ("tests", "successful", "failed", "suites"):
            ET.SubElement(
                properties,
                "property",
                {"name": name, "value": str(summary[name])},
            )
    system_out = ET.SubElement(case, "system-out")
    system_out.text = xml_safe(source_text[-100_000:])
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(output, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gate-name", required=True)
    parser.add_argument("--expected-tests", type=int, required=True)
    parser.add_argument("--expected-suites", type=int, required=True)
    parser.add_argument("--expected-runner", required=True)
    args = parser.parse_args()

    source_text = args.input.read_text(encoding="utf-8-sig", errors="replace")
    summary: dict[str, int | float] | None = None
    errors: list[str] = []
    try:
        summary = parse_summary(source_text)
        if summary["tests"] != args.expected_tests:
            errors.append(f"expected {args.expected_tests} tests, got {summary['tests']}")
        if summary["suites"] != args.expected_suites:
            errors.append(f"expected {args.expected_suites} suites, got {summary['suites']}")
        runners = parse_runners(source_text)
        if not runners:
            errors.append("missing TcUnit test-class runner identity")
        elif runners != {args.expected_runner}:
            errors.append(
                f"expected runner {args.expected_runner}, got {', '.join(sorted(runners))}"
            )
        if summary["failed"] != 0:
            errors.append(f"TcUnit reported {summary['failed']} failed test(s)")
        if summary["successful"] + summary["failed"] != summary["tests"]:
            errors.append("successful + failed does not equal total tests")
    except ValueError as error:
        errors.append(str(error))

    write_junit(args.output, args.gate_name, summary, errors, source_text)
    if errors:
        print(f"{args.gate_name}: FAIL: {'; '.join(errors)}", file=sys.stderr)
        return 1
    print(
        f"{args.gate_name}: PASS: {summary['successful']}/{summary['tests']} tests "
        f"across {summary['suites']} suites"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
