#!/usr/bin/env python3
"""Validate the frozen Fraktal/AB R3 contracts and hold them to Part III.

`Specification/AB_FROZEN_CONTRACTS_V1.json` is the machine-readable freeze of
the six R3 logical contracts. `Fraktal_AB_Part_III.md` remains the normative
prose. Two representations of one fact is exactly the duplication objective O9
warns about, so this gate makes drift between them a build failure rather than
something a reader has to notice.

It enforces:

* every contract declares a version and its Part III marker string, and that
  marker occurs in Part III exactly once;
* every field name in the freeze appears in Part III, so a rename or typo in
  either representation is caught;
* every field's logical type is declared in `logicalTypes`;
* **no field uses a type the baseline marks unavailable** - this is the
  machine-checkable half of AB §3.8's ban on silent narrowing, so adding a
  `float64` field to a contract fails the build instead of quietly becoming a
  `REAL` somewhere downstream;
* every capacity symbol referenced by a contract is declared, and an unresolved
  symbol carries the spike that owns it; and
* a capacity claiming to be resolved supplies a value and its evidence, so a
  number can never appear without a measurement behind it.

Usage:
    python tools/check_ab_contracts.py

Exit status: 0 clean, 1 findings, 2 the inputs could not be read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CONTRACTS_PATH = Path("Specification/AB_FROZEN_CONTRACTS_V1.json")
PART_PATH = Path("Specification/Fraktal_AB_Part_III.md")

REQUIRED_CONTRACTS = (
    "registry",
    "manifest",
    "valueEnvelope",
    "mailbox",
    "repositoryNegotiation",
    "hostEvents",
)


def _iter_fields(contract: dict[str, object]):
    """Yield every field mapping in a contract, whatever shape it uses."""
    for key, value in contract.items():
        if key in {"version", "partIIIMarker", "capacity", "qualityValues",
                   "commitRule", "orderRule", "readOnly", "tables"}:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "name" in item:
                    yield item
        elif isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, list):
                    for item in nested:
                        if isinstance(item, dict) and "name" in item:
                            yield item


def audit(contracts: dict[str, object], part: str) -> list[str]:
    findings: list[str] = []

    logical_types: dict[str, dict] = contracts.get("logicalTypes", {})
    unavailable = {
        name for name, spec in logical_types.items()
        if not spec.get("available", False)
    }

    declared_capacities = {
        entry["symbol"]: entry for entry in contracts.get("capacities", [])
    }
    for symbol, entry in declared_capacities.items():
        if entry.get("resolved"):
            if "value" not in entry:
                findings.append(f"capacity {symbol} claims resolved with no value")
            if "evidence" not in entry:
                findings.append(f"capacity {symbol} claims resolved with no evidence")
        elif not entry.get("owner"):
            findings.append(f"unresolved capacity {symbol} names no owning spike")

    contract_set: dict[str, dict] = contracts.get("contracts", {})
    for name in REQUIRED_CONTRACTS:
        if name not in contract_set:
            findings.append(f"frozen contract missing: {name}")

    for name, contract in contract_set.items():
        if "version" not in contract:
            findings.append(f"contract {name} declares no version")
        marker = contract.get("partIIIMarker")
        if not marker:
            findings.append(f"contract {name} declares no Part III marker")
        elif part.count(marker) != 1:
            findings.append(
                f"contract {name} marker {marker!r} occurs "
                f"{part.count(marker)} times in Part III, expected exactly one"
            )

        for field in _iter_fields(contract):
            field_name = field["name"]
            field_type = field.get("type")
            if field_type not in logical_types:
                findings.append(
                    f"{name}.{field_name} uses undeclared logical type {field_type!r}"
                )
            elif field_type in unavailable:
                findings.append(
                    f"{name}.{field_name} uses logical type {field_type!r}, which "
                    "the baseline records as unavailable; silent narrowing is "
                    "forbidden by AB §3.8"
                )
            if field_name not in part:
                findings.append(
                    f"{name}.{field_name} does not appear in Part III; the freeze "
                    "and the prose have drifted"
                )

        used = [contract.get("capacity")] + [
            table.get("capacity") for table in contract.get("tables", [])
        ]
        for symbol in filter(None, used):
            if symbol not in declared_capacities:
                findings.append(
                    f"contract {name} references undeclared capacity {symbol}"
                )

    return findings


def main(argv: list[str] | None = None) -> int:
    root = Path(argv[0]) if argv else Path(".")
    contracts_path = root / CONTRACTS_PATH
    part_path = root / PART_PATH
    try:
        contracts = json.loads(contracts_path.read_text(encoding="utf-8-sig"))
        part = part_path.read_text(encoding="utf-8-sig")
    except (OSError, ValueError) as exc:
        print(f"ERROR [ab-contracts] {exc}", file=sys.stderr)
        return 2

    findings = audit(contracts, part)
    if findings:
        print("Fraktal/AB frozen-contract gate: findings")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Fraktal/AB frozen-contract gate: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
