#!/usr/bin/env python3
"""Prove that a post-download L5X differs only by an exact target binding.

This is deliberately separate from the normal L5X canonical comparator.  A
controller download may bind an otherwise controller-neutral project to the
physical serial number and installed firmware minor revision.  Those fields
are accepted only when both their before and after values match command-line
expectations; every other XML field must remain canonically identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from fraktal_ab_l5x_compare import CompareError, VOLATILE_ATTRIBUTES


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def serial_literal(serial: str) -> str:
    compact = serial.replace("_", "").upper()
    if len(compact) != 8 or any(char not in "0123456789ABCDEF" for char in compact):
        raise CompareError("serial must contain exactly eight hexadecimal digits")
    return f"16#{compact[:4].lower()}_{compact[4:].lower()}"


def parse(path: Path) -> ET.Element:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise CompareError(f"cannot parse {path}: {exc}") from exc
    if root.tag != "RSLogix5000Content":
        raise CompareError(f"{path} is not a full-project L5X export")
    return root


def one(root: ET.Element, expression: str, label: str) -> ET.Element:
    matches = root.findall(expression)
    if len(matches) != 1:
        raise CompareError(f"expected exactly one {label}, found {len(matches)}")
    return matches[0]


def expect(element: ET.Element, attribute: str, expected: str, label: str) -> None:
    actual = element.get(attribute)
    if actual != expected:
        raise CompareError(
            f"{label}/@{attribute} expected {expected!r}, found {actual!r}"
        )


def canonical(root: ET.Element) -> bytes:
    for element in root.iter():
        element_name = element.tag.rsplit("}", 1)[-1]
        for attribute in VOLATILE_ATTRIBUTES.get(element_name, ()):
            element.attrib.pop(attribute, None)
    serialized = ET.tostring(root, encoding="unicode")
    return ET.canonicalize(xml_data=serialized).encode("utf-8")


def compare(
    before: Path,
    after: Path,
    *,
    serial: str,
    major_revision: int,
    source_minor: int,
    target_minor: int,
) -> dict[str, object]:
    before_root = parse(before)
    after_root = parse(after)
    before_controller = one(before_root, "./Controller", "Controller")
    after_controller = one(after_root, "./Controller", "Controller")
    before_local = one(
        before_controller, './Modules/Module[@Name="Local"]', "Local module"
    )
    after_local = one(
        after_controller, './Modules/Module[@Name="Local"]', "Local module"
    )

    expected_serial = serial_literal(serial)
    expect(before_controller, "MajorRev", str(major_revision), "before Controller")
    expect(after_controller, "MajorRev", str(major_revision), "after Controller")
    expect(before_controller, "MinorRev", str(source_minor), "before Controller")
    expect(after_controller, "MinorRev", str(target_minor), "after Controller")
    expect(before_controller, "ProjectSN", "16#0000_0000", "before Controller")
    expect(after_controller, "ProjectSN", expected_serial, "after Controller")
    expect(before_local, "Major", str(major_revision), "before Local module")
    expect(after_local, "Major", str(major_revision), "after Local module")
    expect(before_local, "Minor", str(source_minor), "before Local module")
    expect(after_local, "Minor", str(target_minor), "after Local module")

    after_controller.set("MinorRev", str(source_minor))
    after_controller.set("ProjectSN", "16#0000_0000")
    after_local.set("Minor", str(source_minor))
    before_canonical = canonical(before_root)
    after_canonical = canonical(after_root)
    equivalent = before_canonical == after_canonical
    return {
        "Schema": "fraktal.ab.target-binding-comparison",
        "SchemaVersion": 1,
        "Before": str(before.resolve()),
        "After": str(after.resolve()),
        "BeforeRawSha256": sha256(before.read_bytes()),
        "AfterRawSha256": sha256(after.read_bytes()),
        "BeforeNormalizedSha256": sha256(before_canonical),
        "AfterNormalizedSha256": sha256(after_canonical),
        "ExpectedBindingDifferences": [
            f"Controller/@MinorRev: {source_minor} -> {target_minor}",
            f"Controller/@ProjectSN: 16#0000_0000 -> {expected_serial}",
            f"Controller/Modules/Module[@Name='Local']/@Minor: {source_minor} -> {target_minor}",
        ],
        "VolatileAttributesExcluded": [
            "Controller/@LastModifiedDate",
            "Controller/@ProjectCreationDate",
            "RSLogix5000Content/@ExportDate",
        ],
        "EquivalentAfterExactTargetBinding": equivalent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--major-revision", type=int, required=True)
    parser.add_argument("--source-minor", type=int, required=True)
    parser.add_argument("--target-minor", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(
            args.before,
            args.after,
            serial=args.serial,
            major_revision=args.major_revision,
            source_minor=args.source_minor,
            target_minor=args.target_minor,
        )
    except CompareError as exc:
        print(f"ERROR [target-binding-compare] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["EquivalentAfterExactTargetBinding"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
