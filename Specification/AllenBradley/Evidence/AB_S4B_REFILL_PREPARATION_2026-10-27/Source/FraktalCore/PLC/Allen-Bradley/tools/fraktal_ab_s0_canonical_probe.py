#!/usr/bin/env python3
"""Generate the S0 type probe for canonical CIP publication (L81E/v38, Echo).

AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19 decides D2-D7 by measurement: which
native types a generic CIP client can discover through the Template object and
decode without station knowledge. Each family below is one split case, so a
compiler rejection names exactly one type. The combined case carries every
family that compiled, in one record, for a single guarded Echo download and a
read-only measurement (fraktal_ab_s0_canonical_measure.py).

Logic assigns every probed member a known value with a typed literal on every
scan. The measurement therefore compares bytes against expected values instead
of describing whatever happened to be in memory. Reuses S12's empty-seed
project: inert periodic task, output updates disabled, no I/O, no mailbox.
This tool never opens a connection or downloads anything.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from fraktal_ab_phase0_fixture import replace_once, sha256
import fraktal_ab_s12_type_probe as s12


SCHEMA = "fraktal.ab.s0-canonical-probe"
RECORD = "FRK_T_S0Probe"
CHILD = "FRK_T_S0Child"
TAG = s12.TAG
P = TAG
PROFILE = s12.ProbeProfile(
    key="v38-5580-s0-canonical-exploratory",
    controller="1756-L81E", revision="38",
    status="exploratory-not-runtime-accepted", candidates=(),
)
STRING_WIDTHS = (2, 80, 160, 255, 480)
BOOL_PATTERN = (1, 0, 1, 1, 0, 0, 1, 0, 1, 1)


def string_type(width: int) -> str:
    # The exact StringFamily form the press generator already emits and the SDK
    # imports (FRK_T_PressStr160): LEN DINT, DATA SINT[n].
    return (f'<DataType Name="FRK_T_S0Str{width}" Family="StringFamily" Class="User">\n'
            "<Members>\n"
            '<Member Name="LEN" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
            f'<Member Name="DATA" DataType="SINT" Dimension="{width}" Radix="ASCII" Hidden="false" ExternalAccess="Read Only"/>\n'
            "</Members>\n"
            "</DataType>")


def child_type() -> str:
    return (f'<DataType Name="{CHILD}" Family="NoFamily" Class="User">\n'
            "<Members>\n"
            '<Member Name="Flag" DataType="BOOL" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
            '<Member Name="Value" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read Only"/>\n'
            "</Members>\n"
            "</DataType>")


@dataclass(frozen=True)
class Family:
    key: str
    members: tuple[tuple[str, str, int], ...]   # (name, data type, dimension)
    statements: tuple[str, ...]
    expected: dict
    types: tuple[str, ...] = ()                 # DataType XML, dependencies first
    observe: bool = False                       # literal syntax not yet documented here


def _bools() -> Family:
    members = tuple((f"B{i}", "BOOL", 0) for i in range(len(BOOL_PATTERN)))
    members += (("After", "DINT", 0), ("Flags", "BOOL", 32))
    statements = tuple(f"{P}.B{i} := {v};" for i, v in enumerate(BOOL_PATTERN))
    statements += (f"{P}.After := 123456789;",
                   f"{P}.Flags[0] := 1;", f"{P}.Flags[5] := 1;", f"{P}.Flags[31] := 1;")
    expected = {f"B{i}": bool(v) for i, v in enumerate(BOOL_PATTERN)}
    expected.update(After=123456789, FlagsSet=[0, 5, 31])
    return Family("bools", members, statements, expected)


def _numbers() -> Family:
    # 0x0102030405060708 built from DINT literals: a LINT literal wider than 32
    # bits is a separate syntax question this probe does not need to answer.
    statements = (f"{P}.Big := 16909060;", f"{P}.Big := {P}.Big * 65536;",
                  f"{P}.Big := {P}.Big * 65536;", f"{P}.Big := {P}.Big + 84281096;",
                  f"{P}.Negative := 0;", f"{P}.Negative := {P}.Negative - 2;",
                  f"{P}.Wide := 3.141592653589793;", f"{P}.Single := 1.5;",
                  f"{P}.Words[0] := 10;", f"{P}.Words[4] := 14;",
                  f"{P}.Kids[0].Flag := 1;", f"{P}.Kids[0].Value := 7;",
                  f"{P}.Kids[2].Flag := 0;", f"{P}.Kids[2].Value := -9;")
    members = (("Big", "LINT", 0), ("Negative", "LINT", 0), ("Wide", "LREAL", 0),
               ("Single", "REAL", 0), ("Words", "DINT", 5), ("Kids", CHILD, 3))
    expected = dict(Big=0x0102030405060708, Negative=-2, Wide=3.141592653589793,
                    Single=1.5, Words={0: 10, 4: 14},
                    Kids={0: {"Flag": True, "Value": 7}, 2: {"Flag": False, "Value": -9}})
    return Family("numbers", members, statements, expected, types=(child_type(),))


def _strings() -> Family:
    members = tuple((f"S{w}", f"FRK_T_S0Str{w}", 0) for w in STRING_WIDTHS)
    members += (("Std", "STRING", 0),)
    statements = (f"{P}.S2.LEN := 2;", f"{P}.S2.DATA[0] := 79;", f"{P}.S2.DATA[1] := 75;",
                  # 'A' then U+00E9 as UTF-8 (C3 A9): byte-counted LEN = 3.
                  f"{P}.S80.LEN := 3;", f"{P}.S80.DATA[0] := 65;",
                  f"{P}.S80.DATA[1] := -61;", f"{P}.S80.DATA[2] := -87;",
                  f"{P}.S160.LEN := 160;", f"{P}.S160.DATA[0] := 65;", f"{P}.S160.DATA[159] := 90;",
                  f"{P}.S255.LEN := 255;", f"{P}.S255.DATA[0] := 65;", f"{P}.S255.DATA[254] := 90;",
                  f"{P}.S480.LEN := 480;", f"{P}.S480.DATA[0] := 65;", f"{P}.S480.DATA[479] := 90;",
                  f"{P}.Std.LEN := 1;", f"{P}.Std.DATA[0] := 88;")
    expected = {"S2": [2, {0: 79, 1: 75}], "S80": [3, {0: 65, 1: 0xC3, 2: 0xA9}],
                "S160": [160, {0: 65, 159: 90}], "S255": [255, {0: 65, 254: 90}],
                "S480": [480, {0: 65, 479: 90}], "Std": [1, {0: 88}]}
    return Family("strings", members, statements, expected,
                  types=tuple(string_type(w) for w in STRING_WIDTHS))


def _time(key: str, name: str, data_type: str, literal: str, expected: int,
          observe: bool) -> Family:
    # Never name a member after its type: TIME, DT, LDT ... are reserved, and
    # `Probe.Time := ...` fails as RxSTX_E_UNEXPECTED_TOKEN (measured 10-19).
    return Family(key, ((name, data_type, 0),), (f"{P}.{name} := {literal};",),
                  {name: expected}, observe=observe)


def _from_lint(key: str, name: str, data_type: str, raw: int) -> Family:
    # Rockwell: LINT is the one non-time type allowed to move into an absolute
    # time type. The raw value is built from DINT literals as in _numbers.
    high, low = divmod(raw, 1 << 32)
    middle, tail = divmod(low, 1 << 16)
    # Keep each low half positive: a signed low DINT would subtract 2^32
    # whenever bit 31 is set, corrupting the stimulus before conversion.
    statements = (f"{P}.{name}Raw := {high};", f"{P}.{name}Raw := {P}.{name}Raw * 65536;",
                  f"{P}.{name}Raw := {P}.{name}Raw + {middle};",
                  f"{P}.{name}Raw := {P}.{name}Raw * 65536;",
                  f"{P}.{name}Raw := {P}.{name}Raw + {tail};",
                  # ST has no MOV (RxSTX_E_INVALID_FUNC, measured); assignment
                  # is the ST form of the documented LINT-to-time move.
                  f"{P}.{name} := {P}.{name}Raw;")
    return Family(key, ((f"{name}Raw", "LINT", 0), (name, data_type, 0)), statements,
                  {f"{name}Raw": raw, name: raw}, observe=True)


# 2026-10-19 12:34:56.123456789 UTC
STAMP_US = 1_792_413_296_123_456
STAMP_NS = 1_792_413_296_123_456_789

FAMILIES = (
    _bools(), _numbers(), _strings(),
    # Rockwell v37 help: TIME 64-bit us, TIME32 32-bit us, LTIME 64-bit ns.
    # A literal component may not exceed its unit: T#1500ms is
    # RxSTX_E_UNEXPECTED_TOKEN while T#1s500ms compiles, and the TIME#
    # prefix is rejected outright (measured 2026-10-20).
    _time("time", "DurUs", "TIME", "T#1s500ms", 1_500_000, observe=False),
    _time("time32", "Dur32", "TIME32", "T32#1s500ms", 1_500_000, observe=False),
    _time("ltime", "DurNs", "LTIME", "LT#1s500ms", 1_500_000_000, observe=True),
    # DT 64-bit us and LDT 64-bit ns, absolute. Literal syntax is not yet
    # documented in this repository, so each literal has a LINT fallback.
    _time("dt", "StampUs", "DT", "DT#2026-10-19-12:34:56.123456", STAMP_US, observe=True),
    _time("ldt", "StampNs", "LDT", "LDT#2026-10-19-12:34:56.123456789", STAMP_NS, observe=True),
    _from_lint("dt_from_lint", "StampUsFromLint", "DT", STAMP_US),
    _from_lint("ldt_from_lint", "StampNsFromLint", "LDT", STAMP_NS),
)
BY_KEY = {family.key: family for family in FAMILIES}


ATOMIC_TYPES = {"BOOL", "SINT", "INT", "DINT", "LINT", "REAL", "LREAL",
                "TIME", "TIME32", "LTIME", "DT", "LDT"}


def _radix(data_type: str) -> str:
    # Studio's read-back canonical form: a structured member (user record,
    # StringFamily, STRING) carries NullType, so emitting Decimal there makes
    # the actual read-back differ from the source.
    if data_type in ("REAL", "LREAL"):
        return "Float"
    return "Decimal" if data_type in ATOMIC_TYPES else "NullType"


def _record(families: tuple[Family, ...]) -> str:
    root = ET.Element("DataType", Name=RECORD, Family="NoFamily", Class="User")
    members = ET.SubElement(root, "Members")
    for family in families:
        for name, data_type, dimension in family.members:
            ET.SubElement(members, "Member", Name=name, DataType=data_type,
                          Dimension=str(dimension), Radix=_radix(data_type),
                          Hidden="false", ExternalAccess="Read Only")
    return ET.tostring(root, encoding="unicode")


def case_text(families: tuple[Family, ...]) -> tuple[str, str]:
    seen, types = set(), []
    for family in families:
        for xml in family.types:
            if xml not in seen:
                seen.add(xml)
                types.append(xml)
    statements = tuple(s for family in families for s in family.statements)
    return "\n".join(types + [_record(families)]), "\n".join(statements)


def generate(source: Path, output: Path, families: tuple[Family, ...]) -> dict:
    user_types, statements = case_text(families)
    candidate = s12.Candidate("+".join(f.key for f in families), "S0 canonical type probe",
                              RECORD, user_types, 0, statements)
    s12.generate_case(source, output, candidate, "use", profile=PROFILE)
    # The probe tag is only ever read; S12's writable stimulus marker is removed.
    text = replace_once(output.read_text(encoding="utf-8"),
                        'ExternalAccess="Read/Write"', 'ExternalAccess="Read Only"')
    output.write_text(text, encoding="utf-8", newline="\n")
    return {"Output": str(output), "OutputSha256": sha256(output),
            "Families": [f.key for f in families],
            "Expected": {f.key: f.expected for f in families},
            "Statements": statements.splitlines()}


def generate_all(source: Path, directory: Path, combine: tuple[str, ...] = ()) -> dict:
    directory = directory.resolve()
    report_path = directory / ("combined.json" if combine else "generation.json")
    if combine:
        families = tuple(BY_KEY[key] for key in combine)
        plan = [("combined", families)]
    else:
        plan = [(family.key, (family,)) for family in FAMILIES]
    outputs = [directory / f"s0_{name}.L5X" for name, _ in plan]
    existing = [str(p) for p in (*outputs, report_path) if p.exists()]
    if existing:
        raise ValueError(f"refusing to overwrite outputs: {existing}")
    directory.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    cases = []
    for (name, families), output in zip(plan, outputs):
        row = generate(source, output, families)
        row.update(Case=name, ExpectedBuild="observe" if any(f.observe for f in families) else "pass")
        cases.append(row)
    if sha256(source) != source_hash:
        raise ValueError("input seed changed during generation")
    report = {"Schema": SCHEMA, "SchemaVersion": 1, "Profile": PROFILE.key,
              "ProfileStatus": PROFILE.status, "Controller": PROFILE.controller,
              "MajorRevision": PROFILE.revision, "SourceSha256": source_hash,
              "RuntimeAccepted": False, "Tag": TAG, "Record": RECORD, "Cases": cases}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="empty 1756-L81E/v38 seed L5X")
    parser.add_argument("directory", type=Path, help="output directory (no file is overwritten)")
    parser.add_argument("--combine", nargs="+", choices=sorted(BY_KEY),
                        help="emit one image carrying exactly these families")
    args = parser.parse_args()
    try:
        report = generate_all(args.source, args.directory, tuple(args.combine or ()))
    except (OSError, ValueError) as exc:
        print(f"ERROR [s0-canonical-probe] {exc}")
        return 1
    print(json.dumps({"Cases": [(c["Case"], c["ExpectedBuild"]) for c in report["Cases"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
