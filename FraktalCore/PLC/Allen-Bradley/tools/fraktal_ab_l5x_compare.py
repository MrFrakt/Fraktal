#!/usr/bin/env python3
"""Compare two full-project L5X exports after narrow volatile-field removal.

Rockwell rewrites project/export timestamps during a valid import/build/export
cycle. Those timestamps are not executable project semantics. Everything else,
including software/controller revisions, names, options, routines, tags, data
types, and serialized values, remains in the comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


VOLATILE_ATTRIBUTES = {
    "RSLogix5000Content": frozenset({"ExportDate"}),
    "Controller": frozenset({"ProjectCreationDate", "LastModifiedDate"}),
}


class CompareError(RuntimeError):
    """Raised when an L5X input cannot be safely compared."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_l5x(path: Path) -> tuple[bytes, list[str]]:
    """Return C14N bytes and the exact excluded attribute paths."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise CompareError(f"cannot parse {path}: {exc}") from exc

    if root.tag != "RSLogix5000Content":
        raise CompareError(
            f"{path} is not a full-project RSLogix5000Content export"
        )

    excluded: list[str] = []
    for element in root.iter():
        element_name = element.tag.rsplit("}", 1)[-1]
        for attribute in VOLATILE_ATTRIBUTES.get(element_name, ()):
            if attribute in element.attrib:
                del element.attrib[attribute]
                excluded.append(f"{element_name}/@{attribute}")

    serialized = ET.tostring(root, encoding="unicode")
    canonical = ET.canonicalize(xml_data=serialized)
    return canonical.encode("utf-8"), sorted(excluded)


def canonical_sha256(path: Path) -> str:
    """Return the timestamp-normalized canonical hash of one L5X document.

    `compare` answers "are these two the same". A single document's canonical
    hash is what an evidence record cites for one artifact, so callers do not
    have to fabricate a comparison against itself to obtain it.
    """
    canonical, _ = canonical_l5x(path)
    return _sha256(canonical)


def compare(first: Path, second: Path) -> dict[str, object]:
    """Return a deterministic comparison report for two L5X paths."""
    first_raw = first.read_bytes()
    second_raw = second.read_bytes()
    first_canonical, first_excluded = canonical_l5x(first)
    second_canonical, second_excluded = canonical_l5x(second)
    exclusions_match = first_excluded == second_excluded
    equivalent = exclusions_match and first_canonical == second_canonical
    return {
        "Schema": "fraktal.ab.l5x-comparison",
        "SchemaVersion": 1,
        "First": str(first.resolve()),
        "Second": str(second.resolve()),
        "FirstRawSha256": _sha256(first_raw),
        "SecondRawSha256": _sha256(second_raw),
        "FirstCanonicalSha256": _sha256(first_canonical),
        "SecondCanonicalSha256": _sha256(second_canonical),
        "ExcludedAttributes": first_excluded if exclusions_match else {
            "First": first_excluded,
            "Second": second_excluded,
        },
        "Equivalent": equivalent,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args(argv)
    try:
        report = compare(args.first, args.second)
    except (OSError, CompareError) as exc:
        print(f"ERROR [l5x-compare] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["Equivalent"] else 1


if __name__ == "__main__":
    sys.exit(main())
