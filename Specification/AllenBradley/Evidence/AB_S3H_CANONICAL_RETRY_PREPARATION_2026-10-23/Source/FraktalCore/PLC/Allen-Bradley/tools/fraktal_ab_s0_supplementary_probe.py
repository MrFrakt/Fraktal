#!/usr/bin/env python3
"""Generate S0's inert L81E/v38 size/access/naming/precision probe.

No connection or download. Reuses the empty-seed S12 generator. Offline boundary
cases isolate the documented 2 MiB UDT limit; the combined image carries that
single-UDT tag plus smaller records and a separate access matrix. Access tags
are disposable data, with no application consumer or physical output. They are
the only proposed external-write targets; measurement itself stays read-only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from fraktal_ab_phase0_fixture import replace_once, scalar_tag, sha256
import fraktal_ab_s0_canonical_probe as original
import fraktal_ab_s12_type_probe as seed

SCHEMA = "fraktal.ab.s0-supplementary-probe"
PROFILE = seed.ProbeProfile("v38-5580-s0-supplementary", "1756-L81E", "38",
                            "exploratory-not-runtime-accepted", ())
PREFIX = "FRK_T_S0S_"
BLOCK_WORDS = 1024
BLOCK_BYTES = BLOCK_WORDS * 4
UDT_LIMIT_BYTES = 2 * 1024 * 1024
MAGIC = 0x53305332
ROOT = "Press"
IDENTITY = "FRK_S0S_Identity"
STATS = "FRK_S0S_Stats"
SIZES = (("Page", 1), ("Medium", 16), ("Largest", UDT_LIMIT_BYTES // BLOCK_BYTES))
PI_TEXT = "3.141592653589793"
NEXT_TEXT = "1.0000000000000002"
PI = float(PI_TEXT)
NEXT = float(NEXT_TEXT)
TASK = "FRK_S12Task"
ACCESS_TAGS = {"FRK_S0S_AccessRO": "Read Only", "FRK_S0S_AccessRW": "Read/Write",
               "FRK_S0S_AccessPrivate": "Read/Write", "FRK_S0S_AccessNone": "None"}
WRITE_PATHS = tuple(f"{tag}.{member}" for tag in ("FRK_S0S_AccessRO", "FRK_S0S_AccessRW")
                    for member in ("Readback", "HmiRequest"))
SENTINELS = (0x11223344, -123456789, 0x55667788)


def data_type(name, members):
    node = ET.Element("DataType", Name=PREFIX + name, Family="NoFamily", Class="User")
    container = ET.SubElement(node, "Members")
    for member, kind, count, access in members:
        ET.SubElement(container, "Member", Name=member, DataType=kind, Dimension=str(count),
                      Radix="Float" if kind in ("REAL", "LREAL") else
                            "Decimal" if kind in ("DINT", "SINT") else "NullType",
                      Hidden="false", ExternalAccess=access)
    return ET.tostring(node, encoding="unicode")


def record_tag(name, kind, access):
    return f'<Tag Name="{name}" TagType="Base" DataType="{kind}" Constant="false" ExternalAccess="{access}"/>'


def precision_tag(name, value):
    tag = ET.Element("Tag", Name=name, TagType="Base", DataType="LREAL", Radix="Float",
                     Constant="false", ExternalAccess="Read Only")
    data = ET.SubElement(tag, "Data", Format="Decorated")
    ET.SubElement(data, "DataValue", DataType="LREAL", Radix="Float", Value=value)
    return ET.tostring(tag, encoding="unicode")


def _base_types():
    ro, rw = "Read Only", "Read/Write"
    text = ET.fromstring(original.string_type(16))
    text.set("Name", PREFIX + "Text16")
    return [ET.tostring(text, encoding="unicode"),
            data_type("Status", (("Name", PREFIX + "Text16", 0, ro), ("ModuleType", "DINT", 0, ro),
                                 ("State", "DINT", 0, ro))),
            data_type("Root", (("Status", PREFIX + "Status", 0, ro), ("WideTyped", "LREAL", 0, ro),
                               ("WideNext", "LREAL", 0, ro), ("WideUntyped", "LREAL", 0, ro))),
            data_type("Stats", tuple((name, "DINT", 0, ro) for name in
                                      ("Scan", "LastScanUs", "MaxScanUs", "OverlapCount"))),
            data_type("Access", (("Readback", "DINT", 0, ro), ("HmiRequest", "DINT", 0, rw))),
            data_type("PrivateAccess", (("Readback", "DINT", 0, ro), ("HmiRequest", "DINT", 0, rw),
                                        ("Private", "DINT", 0, "None"))),
            data_type("Block", (("Words", "DINT", BLOCK_WORDS, ro),))]


def _size_type(name, blocks, *, extra_word=False):
    members = [("Blocks", PREFIX + "Block", blocks, "Read Only")]
    if extra_word:
        members.append(("Extra", "DINT", 0, "Read Only"))
    return data_type(name, members)


def render_case(source, output, *, case="combined"):
    """Every byte of L5X is emitted from declarations; no authored L5X input."""
    if case not in ("combined", "under_limit", "limit", "over_limit", "literal", "literal_st"):
        raise ValueError("unknown supplementary case")
    types = _base_types()
    statements, tags = [], []
    boundary_blocks = UDT_LIMIT_BYTES // BLOCK_BYTES - (1 if case == "under_limit" else 0)
    if case in ("under_limit", "limit", "over_limit"):
        types = types[-1:]
        types += [_size_type("Boundary", boundary_blocks, extra_word=case != "limit")]
        kind = PREFIX + "Boundary"
        statements = [f"{seed.TAG}.Blocks[0].Words[0] := {SENTINELS[0]};"]
    else:
        if case != "combined":
            types = types[:3]
        kind = PREFIX + "Root"
        statements = [f"{seed.TAG}.Status.Name.LEN := {len(ROOT)};",
                      *(f"{seed.TAG}.Status.Name.DATA[{i}] := {b};" for i, b in enumerate(ROOT.encode())),
                      f"{seed.TAG}.Status.ModuleType := 1;", f"{seed.TAG}.Status.State := 0;",
                      f"{seed.TAG}.WideTyped := {PI_TEXT}L;",
                      f"{seed.TAG}.WideNext := {NEXT_TEXT}L;",
                      f"{seed.TAG}.WideUntyped := {PI_TEXT};"]
        if case != "literal_st":
            tags += [precision_tag("FRK_S0S_WideInit", PI_TEXT),
                     precision_tag("FRK_S0S_NextInit", NEXT_TEXT)]
        if case == "combined":
            for name, blocks in SIZES:
                types += [_size_type(name, blocks)]
                tag = "FRK_S0S_" + name
                tags += [record_tag(tag, PREFIX + name, "Read Only")]
                statements += [f"{tag}.Blocks[0].Words[0] := {SENTINELS[0]};",
                               f"{tag}.Blocks[{blocks // 2}].Words[17] := {SENTINELS[1]};",
                               f"{tag}.Blocks[{blocks - 1}].Words[{BLOCK_WORDS - 1}] := {SENTINELS[2]};"]
            for name, access in ACCESS_TAGS.items():
                tags += [record_tag(name, PREFIX + ("PrivateAccess" if name.endswith("Private") else "Access"), access)]
            tags += [record_tag(STATS, PREFIX + "Stats", "Read Only"),
                     scalar_tag(IDENTITY, "DINT", "Decimal", str(MAGIC), "Read Only")]
            statements += [f"{STATS}.Scan := FRK_S12_Scan;",
                           f"GSV(TASK,{TASK},LastScanTime,{STATS}.LastScanUs);",
                           f"GSV(TASK,{TASK},MaxScanTime,{STATS}.MaxScanUs);",
                           f"GSV(TASK,{TASK},OverlapCount,{STATS}.OverlapCount);"]
    candidate = seed.Candidate("s0s_" + case, "canonical supplementary compiler/runtime questions",
                               kind, "\n".join(types), 0, "\n".join(statements))
    seed.generate_case(source, output, candidate, "use", profile=PROFILE)
    text = output.read_text(encoding="utf-8")
    if case == "combined":
        # Only the generated main probe tag/operands are renamed. Dependencies
        # carry no occurrence of this token. Assert the tag declaration once.
        marker = f'<Tag Name="{seed.TAG}"'
        if text.count(marker) != 1:
            raise ValueError("probe tag marker count changed")
        text = text.replace(seed.TAG, ROOT)
    text = replace_once(text, f'Constant="false" ExternalAccess="Read/Write"/>',
                        'Constant="false" ExternalAccess="Read Only"/>')
    if tags:
        text = replace_once(text, "</Tags>", "\n".join(tags) + "\n</Tags>")
    output.write_text(text, encoding="utf-8", newline="\n")
    return dict(case=case, output=str(output), sha256=sha256(output),
                expectedBuild="reject-size" if case == "over_limit" else "pass",
                structureBytes=boundary_blocks * BLOCK_BYTES + (0 if case == "limit" else 4)
                if case in ("under_limit", "limit", "over_limit") else None)


def generate(source, directory):
    directory = directory.resolve()
    if directory.exists():
        raise ValueError("refusing existing supplementary output directory")
    directory.mkdir(parents=True)
    before = sha256(source)
    cases = [render_case(source, directory / ("s0s_" + key + ".L5X"), case=key)
             for key in ("literal_st", "literal", "under_limit", "limit", "over_limit", "combined")]
    if sha256(source) != before:
        raise ValueError("empty seed changed")
    report = dict(schema=SCHEMA, schemaVersion=1, sourceSha256=before, cases=cases,
                  runtimeAccepted=False, root=ROOT, identityTag=IDENTITY, identityMagic=MAGIC,
                  expectedSizes={"FRK_S0S_" + name: blocks * BLOCK_BYTES for name, blocks in SIZES},
                  accessTags=ACCESS_TAGS, proposedWritePaths=list(WRITE_PATHS),
                  note="Compile/read-back is not runtime or Capacity acceptance. No application consumes access stimuli.")
    with (directory / "generation.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    report = generate(args.source, args.directory)
    print(json.dumps(dict(cases=len(report["cases"]), runtimeAccepted=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
