#!/usr/bin/env python3
"""Generate offline-only L81E/v38 native health/time compiler probes.

Reuse S12's guarded, empty-seed project generator, including its inert periodic
task and disabled output updates. Each case has one owning record and no HMI,
mailbox, account, plant or physical-I/O logic. MODULE reads name only Local,
the CPU in the seed; their compilation cannot qualify an external I/O module.

This tool never opens a connection or downloads anything. Compile acceptance
does not establish runtime clock behavior, Echo time scaling or module health.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from fraktal_ab_phase0_fixture import replace_once, sha256
import fraktal_ab_s12_type_probe as s12


SCHEMA = "fraktal.ab.v38-native-probe"
TASK = "FRK_S12Task"
RECORD = "FRK_T_V38NativeProbe"
TAG = s12.TAG
PROFILE = s12.ProbeProfile(
    key="v38-5580-native-health-exploratory",
    controller="1756-L81E", revision="38",
    status="exploratory-not-runtime-accepted", candidates=(),
)


@dataclass(frozen=True)
class Attribute:
    field: str
    object_class: str
    instance: str
    attribute: str
    data_type: str
    elements: int = 0

    @property
    def statement(self) -> str:
        destination = f"{TAG}.{self.field}" + ("[0]" if self.elements else "")
        return f"GSV({self.object_class},{self.instance},{self.attribute},{destination});"


MODULE_ATTRIBUTES = (
    Attribute("EntryStatus", "MODULE", "Local", "EntryStatus", "INT"),
    Attribute("FaultCode", "MODULE", "Local", "FaultCode", "INT"),
    Attribute("FaultInfo", "MODULE", "Local", "FaultInfo", "DINT"),
    Attribute("ModuleMode", "MODULE", "Local", "Mode", "INT"),
    # The v38 compiler requires an empty instance for this controller-wide
    # forcing status; Local is correct only for the four per-module reads.
    Attribute("ForceStatus", "MODULE", "", "ForceStatus", "INT"),
)
TASK_ATTRIBUTES = (
    Attribute("LastScanUs", "TASK", TASK, "LastScanTime", "DINT"),
    Attribute("MaxScanUs", "TASK", TASK, "MaxScanTime", "DINT"),
    Attribute("OverlapCount", "TASK", TASK, "OverlapCount", "DINT"),
    Attribute("RateUs", "TASK", TASK, "Rate", "DINT"),
    Attribute("MaxIntervalWords", "TASK", TASK, "MaxInterval", "DINT", 2),
    Attribute("MinIntervalWords", "TASK", TASK, "MinInterval", "DINT", 2),
    Attribute("MaxIntervalTime", "TASK", TASK, "MaxInterval", "TIME"),
    Attribute("MinIntervalTime", "TASK", TASK, "MinInterval", "TIME"),
    Attribute("StartWords", "TASK", TASK, "StartTime", "DINT", 2),
    Attribute("StartLint", "TASK", TASK, "StartTime", "LINT"),
)
CLOCK_ATTRIBUTES = (
    Attribute("CstCurrent", "CST", "", "CurrentValue", "LINT"),
    Attribute("CstWords", "CST", "", "CurrentValue", "DINT", 2),
    Attribute("WallClockCurrent", "WallClockTime", "", "CurrentValue", "LINT"),
)


@dataclass(frozen=True)
class Case:
    key: str
    attributes: tuple[Attribute, ...]
    expected_build: str = "pass"
    extra_members: tuple[tuple[str, str], ...] = ()
    extra_statements: tuple[str, ...] = ()


CASES = (
    Case("module_local", MODULE_ATTRIBUTES),
    Case("task_intervals", TASK_ATTRIBUTES),
    Case("clock_arithmetic", CLOCK_ATTRIBUTES, extra_members=(
        ("PreviousCst", "LINT"), ("DeltaCst", "LINT"),
    ), extra_statements=(
        f"{TAG}.DeltaCst := {TAG}.CstCurrent - {TAG}.PreviousCst;",
        f"{TAG}.PreviousCst := {TAG}.CstCurrent;",
    )),
    # A compiler witness: success here must invalidate the acceptance run.
    Case("invalid_attribute", (
        Attribute("Invalid", "TASK", TASK, "FRK_NotAnAttribute", "DINT"),
    ), expected_build="fail"),
    # Another help table spells this MaximumInterval. Record whether it is an
    # accepted alias; never guess from prose or use it in the production path.
    Case("maximum_interval_spelling", (
        Attribute("Interval", "TASK", TASK, "MaximumInterval", "TIME"),
    ), expected_build="observe"),
)


def _record(case: Case) -> str:
    root = ET.Element("DataType", Name=RECORD, Family="NoFamily", Class="User")
    members = ET.SubElement(root, "Members")
    fields = [(a.field, a.data_type, a.elements) for a in case.attributes]
    fields += [(name, data_type, 0) for name, data_type in case.extra_members]
    for name, data_type, elements in fields:
        ET.SubElement(members, "Member", Name=name, DataType=data_type,
                      Dimension=str(elements), Radix="Decimal", Hidden="false",
                      ExternalAccess="Read Only")
    return ET.tostring(root, encoding="unicode")


def generate_all(source: Path, directory: Path, *, split_attributes: bool = False) -> dict[str, object]:
    directory = directory.resolve()
    cases = CASES
    if split_attributes:
        cases = tuple(
            Case(f"read_{attribute.object_class.lower()}_{attribute.field.lower()}",
                 (attribute,), expected_build="observe")
            for attribute in MODULE_ATTRIBUTES + TASK_ATTRIBUTES + CLOCK_ATTRIBUTES
        ) + (next(case for case in CASES if case.key == "invalid_attribute"),)
    # Check the entire output set before creating any case. Retried evidence
    # collection must not overwrite an earlier successful or failed run.
    outputs = [directory / f"native_{case.key}.L5X" for case in cases]
    report_path = directory / "generation.json"
    existing = [str(path) for path in (*outputs, report_path) if path.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite outputs: {existing}")
    directory.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    results = []
    for case, output in zip(cases, outputs):
        statements = tuple(a.statement for a in case.attributes) + case.extra_statements
        candidate = s12.Candidate(case.key, "native health/time compiler probe",
                                  RECORD, _record(case), 0, "\n".join(statements))
        s12.generate_case(source, output, candidate, "use", profile=PROFILE)
        # S12 permits writable fixture stimuli; these cases need no external
        # writes. Only its one top-level probe tag carries that access marker.
        text = replace_once(output.read_text(encoding="utf-8"),
                            'ExternalAccess="Read/Write"',
                            'ExternalAccess="Read Only"')
        output.write_text(text, encoding="utf-8", newline="\n")
        results.append({
            "Case": case.key, "ExpectedBuild": case.expected_build,
            "Output": str(output), "OutputSha256": sha256(output),
            "Statements": list(statements),
        })
    if sha256(source) != source_hash:
        raise ValueError("input seed changed during generation")
    report = {
        "Schema": SCHEMA, "SchemaVersion": 1,
        "Profile": PROFILE.key, "ProfileStatus": PROFILE.status,
        "Controller": PROFILE.controller, "MajorRevision": PROFILE.revision,
        "SourceSha256": source_hash, "InputUnchanged": True,
        "RuntimeAccepted": False, "ExternalModuleAccepted": False,
        "SplitAttributes": split_attributes,
        "Cases": results,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="empty 1756-L81E/v38 seed L5X")
    parser.add_argument("directory", type=Path, help="new disposable output directory")
    parser.add_argument("--split-attributes", action="store_true",
                        help="one GSV per case to isolate a rejected attribute/type")
    args = parser.parse_args()
    try:
        report = generate_all(args.source, args.directory,
                              split_attributes=args.split_attributes)
    except (OSError, ValueError) as exc:
        print(f"ERROR [v38-native-probe] {exc}")
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
