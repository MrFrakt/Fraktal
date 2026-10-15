"""Generate isolated S3 fixtures from S2/S11 and authoritative Core DUTs.

The compact widths/capacities are measurement candidates, not a released profile.
Memory-only types retain every field; enums become DInt, DT becomes DTL and the
two configuration pointers become logical UDInt indices. Initial values are
omitted because this fixture measures allocation, not those types' algorithms.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[4]
SPIKES = HERE.parent
DUTS = REPO / "FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs"
PARAMS = REPO / "FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL"
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from fraktal_tia_types import bound, plain, struct_fields, struct_members

GROUPS = {
    "module": [("Modules", "ST_ModuleStatus", 16), ("States", "ST_StateFlag", "16*MAX_STATE_FLAGS")],
    "alarm": [("Active", "ST_AlarmEvent", "MAX_ALARM_ACTIVE"), ("Ring", "ST_AlarmEvent", "MAX_ALARM_RING"),
              ("Meta", "ST_AlarmMeta", "MAX_ALARM_META")],
    "sequence": [("Steps", "ST_SequenceStep", "MAX_SEQUENCE_STEPS"), ("Definitions", "ST_SequenceStepDef", "MAX_SEQUENCE_STEPS"),
                 ("Cursors", "ST_SequenceCursor", "1+MAX_PARALLEL_BRANCHES"),
                 ("Annotations", "ST_SequenceAnnotation", "MAX_SEQUENCE_ANNOTATIONS"), ("Current", "ST_StepRecord", 1)],
    "config": [("Page", "ST_ConfigPage", 1), ("Snapshot", "ST_ConfigRecord", "MAX_SET_RECORDS"),
               ("Sets", "ST_ConfigSetInfo", "MAX_CONFIG_SETS"), ("Writes", "ST_ConfigWriteDef", "MAX_CONFIG_WRITES")],
}
GROUPS["all"] = [row for group in GROUPS.values() for row in group]
GROUPS["writes"] = [("Writes", "ST_ConfigWriteDef", "MAX_CONFIG_WRITES")]
COMPACT_CAPS = {"MAX_STATE_FLAGS": 6, "MAX_ALARM_ACTIVE": 8, "MAX_ALARM_RING": 16, "MAX_ALARM_META": 8,
                "MAX_SEQUENCE_STEPS": 64, "MAX_SEQUENCE_ANNOTATIONS": 4, "MAX_PARALLEL_BRANCHES": 3,
                "MAX_STEP_CONDS": 4, "MAX_CONFIG_PAGE": 4, "MAX_SET_RECORDS": 32, "MAX_CONFIG_SETS": 4,
                "MAX_CONFIG_WRITES": 8}
COMPACT_WIDTHS = {"Name": 96, "SourcePath": 96, "Scope": 96, "RootIdentity": 96, "AwaitsPath": 96,
                  "Description": 96, "Key": 96, "WriteKey": 96, "DisplayNameKey": 96, "DescriptionKey": 96,
                  "TypeKey": 96, "StepName": 96, "AwaitingLabel": 96, "LabelKey": 96, "EnumLabelKey": 96,
                  "IoTag": 32, "IoAddress": 32, "Item": 160, "ValueText": 80, "EnumDomain": 128}


def constants():
    text = plain(ET.parse(PARAMS).getroot().find("GVL/Declaration").text)
    return {name: int(value) for name, value in re.findall(r"(MAX_\w+)\s*:\s*\w+\s*:=\s*(\d+)", text)}


def native_name(name):
    return "ST_S3" + name.removeprefix("ST_")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("source anchor drift: " + old)
    return text.replace(old, new, 1)


def unit_guard():
    cm = (SPIKES / "S2_Shape/30_CylinderCM.scl").read_text(encoding="ascii")
    guard = re.search(r"IF (NOT \(#Core.Initialized.*?\)) THEN", cm, re.S).group(1)
    guard = guard.replace("#Execute", "#RunReq").replace("#Abort", "#AbortReq")
    # AbortPrev belongs to Core; replace only the standalone input token.
    guard = guard.replace("#Core.AbortReqPrev", "#Core.AbortPrev")
    return guard


def unit_full(text):
    """Remove only the known quiet frame, retaining the measured full variant."""
    if "LifecycleActive" not in text:
        return text
    text = replace_once(text, "      instancePath : WString;\n      LifecycleActive : Bool;", "      instancePath : WString;")
    text = replace_once(text, '\t#LifecycleActive := ' + unit_guard() + ';\n\tIF #LifecycleActive THEN\n', '')
    text = replace_once(text, '\tEND_IF;\n\n\t// ---- GENERATED: children, each exactly once, unconditionally -----------',
                        '\t// ---- GENERATED: children, each exactly once, unconditionally -----------')
    text = replace_once(text, '\tIF #LifecycleActive THEN\n\t// ---- GENERATED: lifecycle end -----------------------------------------',
                        '\t// ---- GENERATED: lifecycle end -----------------------------------------')
    text = replace_once(text, '          Aborted => #Aborted, ErrorID => #ErrorID);\n\tEND_IF;\nEND_FUNCTION_BLOCK',
                        '          Aborted => #Aborted, ErrorID => #ErrorID);\nEND_FUNCTION_BLOCK')
    if "LifecycleActive" in text:
        raise ValueError("unrecognized Unit quiet frame")
    return text


def unit_quiet(text):
    text = unit_full(text)
    guard = unit_guard()
    text = replace_once(text, "      instancePath : WString;", "      instancePath : WString;\n      LifecycleActive : Bool;")
    anchor = '\t// ---- GENERATED: lifecycle begin ---------------------------------------'
    text = replace_once(text, anchor, '\t#LifecycleActive := ' + guard + ';\n\tIF #LifecycleActive THEN\n' + anchor)
    anchor = '\t// ---- GENERATED: children, each exactly once, unconditionally -----------'
    text = replace_once(text, anchor, '\tEND_IF;\n\n' + anchor)
    anchor = '\t// ---- GENERATED: lifecycle end -----------------------------------------'
    text = replace_once(text, anchor, '\tIF #LifecycleActive THEN\n' + anchor)
    text = replace_once(text, '          Aborted => #Aborted, ErrorID => #ErrorID);\nEND_FUNCTION_BLOCK',
                        '          Aborted => #Aborted, ErrorID => #ErrorID);\n\tEND_IF;\nEND_FUNCTION_BLOCK')
    return text


def generate(out, group, profile, quiet, units):
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"group": group, "profile": profile, "unit_quiet": quiet, "extra_units": units,
                "sources": {}, "types": {}, "storage": []}
    for source_dir in (SPIKES / "S2_Shape", SPIKES / "S11_Scl"):
        for path in source_dir.iterdir():
            if path.suffix not in (".scl", ".udt", ".db"):
                continue
            payload = path.read_bytes()
            manifest["sources"][str(path.relative_to(REPO))] = hashlib.sha256(payload).hexdigest()
            target_name = path.name if source_dir.name == "S2_Shape" else "90_" + path.name
            (out / target_name).write_bytes(payload)
    path = out / "50_Unit.scl"
    frame = unit_quiet if quiet else unit_full
    path.write_bytes(frame(path.read_text(encoding="ascii")).encode("ascii"))
    if units:
        declarations = []
        calls = []
        for index in range(1, units + 1):
            declarations += [f'      Unit{index:02} : "FB_SpkUnit";', f'      Hal{index:02} : "ST_SpkUnitHal";']
            calls.append(f'\t#Unit{index:02}(Hal := #Hal{index:02});')
        block = ['FUNCTION_BLOCK "FB_S3Units"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
                 '   VAR', *declarations, '   END_VAR', 'BEGIN', *calls, 'END_FUNCTION_BLOCK', '']
        (out / "81_Units.scl").write_bytes("\n".join(block).encode("ascii"))
        (out / "82_Units.db").write_bytes(('DATA_BLOCK "S3Units"\n{ S7_Optimized_Access := \'TRUE\' }\nVERSION : 0.1\nNON_RETAIN\n"FB_S3Units"\nBEGIN\nEND_DATA_BLOCK\n').encode("ascii"))
        path = out / "80_OB1.scl"
        path.write_bytes(replace_once(path.read_text(encoding="ascii"), '\t"SpkMain"();', '\t"SpkMain"();\n\t"S3Units"();').encode("ascii"))
        path = out / "60_Harness.scl"
        text = replace_once(path.read_text(encoding="ascii"), '"FRK_Registry".Count = 3', f'"FRK_Registry".Count = {3 + units * 3}')
        text = replace_once(text, 'Expected := 3, Actual := "FRK_Registry".Count', f'Expected := {3 + units * 3}, Actual := "FRK_Registry".Count')
        path.write_bytes(text.encode("ascii"))

    caps = constants()
    if profile == "compact":
        caps.update(COMPACT_CAPS)
    manifest["capacities"] = caps
    manifest["width_overrides"] = COMPACT_WIDTHS if profile == "compact" else {}
    generated = []

    def datatype(name):
        if name in manifest["types"]:
            return
        source = DUTS / (name + ".TcDUT")
        declaration = plain(ET.parse(source).getroot().find("DUT/Declaration").text)
        fields = struct_fields(declaration)
        converted = []
        rows = []
        for member, raw_type in fields:
            original = raw_type.split(":=")[0].strip()
            scalar = original
            array = re.fullmatch(r"ARRAY\[(.*?)\.\.(.*?)\]\s+OF\s+(.*)", scalar, re.I)
            if array:
                scalar = array[3].strip()
            if scalar.startswith("ST_"):
                datatype(scalar)
                scalar = '"' + native_name(scalar) + '"'
            elif scalar.startswith("E_"):
                scalar = "DInt"
            elif scalar == "DT":
                scalar = "DTL"
            elif scalar == "PVOID" and name == "ST_ConfigWriteDef":
                member = {"pTarget": "TargetIndex", "pCapture": "CaptureIndex"}[member]
                scalar = "UDInt"
            elif re.fullmatch(r"STRING\((\d+)\)", scalar):
                width = int(re.fullmatch(r"STRING\((\d+)\)", scalar)[1])
                width = COMPACT_WIDTHS.get(member, width) if profile == "compact" else width
                scalar = f"String[{min(width, 254)}]"
            elif not re.fullmatch(r"BOOL|BYTE|WORD|DWORD|SINT|USINT|INT|UINT|DINT|UDINT|REAL|LREAL|TIME", scalar, re.I):
                raise ValueError(f"unsupported physical type {name}.{member}: {scalar}")
            if array:
                scalar = f"Array[{bound(array[1], caps)}..{bound(array[2], caps)}] of {scalar}"
            converted.append(f'      "{member}" : {scalar};')
            rows.append({"member": member, "core_type": original, "native_type": scalar})
        manifest["types"][name] = {"source": str(source.relative_to(REPO)), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "fields": rows}
        generated.append((native_name(name), converted))

    for field, name, count in GROUPS.get(group, []):
        datatype(name)
        count = bound(count, caps)
        manifest["storage"].append({"name": field, "type": native_name(name), "count": count})
        # Separate DBs avoid the 1200's per-block size ceiling distorting a group.
        payload = [f'DATA_BLOCK "S3{field}"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
                   '   VAR', f'      Data {{ ExternalAccessible := \'False\'; ExternalVisible := \'False\'; ExternalWritable := \'False\'}} : Array[1..{count}] of "{native_name(name)}";',
                   '   END_VAR', 'BEGIN', 'END_DATA_BLOCK', '']
        (out / f"06_{field}.db").write_bytes("\n".join(payload).encode("ascii"))
    for index, (name, fields) in enumerate(generated, 50):
        payload = [f'TYPE "{name}"', 'VERSION : 0.1', '   STRUCT', *fields, '   END_STRUCT;', 'END_TYPE', '']
        (out / f"00_{index:02}_{name}.udt").write_bytes("\n".join(payload).encode("ascii"))
    (out / "manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"generated": str(out), "group": group, "profile": profile, "types": len(generated), "extra_units": units, "quiet": quiet}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--group", choices=("none", *GROUPS), default="none")
    parser.add_argument("--profile", choices=("wide", "compact"), default="wide")
    parser.add_argument("--unit-quiet", action="store_true")
    parser.add_argument("--units", type=int, choices=range(5), default=0)
    args = parser.parse_args()
    generate(args.out, args.group, args.profile, args.unit_quiet, args.units)
