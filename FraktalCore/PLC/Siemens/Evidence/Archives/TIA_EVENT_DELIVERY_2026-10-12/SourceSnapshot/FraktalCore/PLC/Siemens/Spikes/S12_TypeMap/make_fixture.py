"""Generate the complete Core DUT shape and runtime witnesses without narrowing."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import pathlib
import re
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[4]
DUTS = REPO / "FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs"
SPEC = importlib.util.spec_from_file_location("s3_budget_helpers", HERE.parent / "S3_Budget/make_fixture.py")
COMMON = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMMON)
from fraktal_tia_types import enum_values
from fraktal_tia_binding import native_scalar
SCALARS = {"BOOL": ("Bool", "TRUE", True), "BYTE": ("Byte", "BYTE#16#A5", 165),
           "WORD": ("Word", "WORD#16#A55A", 42330), "DWORD": ("DWord", "DWORD#16#DEADBEEF", 3735928559),
           "SINT": ("SInt", "-42", -42), "USINT": ("USInt", "201", 201),
           "INT": ("Int", "-1234", -1234), "UINT": ("UInt", "54321", 54321),
           "DINT": ("DInt", "-123456789", -123456789), "UDINT": ("UDInt", "4000000001", 4000000001),
           "REAL": ("Real", "REAL#1.25", 1.25), "LREAL": ("LReal", "LREAL#1.23456789012345", 1.23456789012345),
           "TIME": ("Time", "T#1S234MS", 1234), "DT": ("DTL", "DTL#2024-02-29-23:59:58.123456789", None),
           "PVOID": ("UDInt", "123", 123)}
DTL_WITNESS = {"YEAR": 2024, "MONTH": 2, "DAY": 29, "WEEKDAY": 5,
               "HOUR": 23, "MINUTE": 59, "SECOND": 58, "NANOSECOND": 123456789}


def native_name(name):
    return "ST_S12" + name.removeprefix("ST_")


def generate(out, timestamp="LDT"):
    if timestamp not in ("DTL", "LDT"):
        raise ValueError("unsupported timestamp representation")
    scalar_map = dict(SCALARS)
    if timestamp == "LDT":
        instant = datetime.datetime(DTL_WITNESS["YEAR"], DTL_WITNESS["MONTH"], DTL_WITNESS["DAY"],
                                    DTL_WITNESS["HOUR"], DTL_WITNESS["MINUTE"], DTL_WITNESS["SECOND"],
                                    tzinfo=datetime.timezone.utc)
        nanos = int(instant.timestamp()) * 1000000000 + DTL_WITNESS["NANOSECOND"]
        scalar_map["DT"] = ("LDT", "DTL_TO_LDT(" + SCALARS["DT"][1] + ")", nanos)
    out.mkdir(parents=True, exist_ok=False)
    caps = COMMON.constants()
    declarations = {p.stem: ET.parse(p).find(".//Declaration").text for p in sorted(DUTS.glob("*.TcDUT"))}
    enums = {name: enum_values(text) for name, text in declarations.items() if name.startswith("E_")}
    members = {name: COMMON.struct_members(text) for name, text in declarations.items() if name.startswith("ST_")}
    structures = {name: [(member["name"], member["type"]) for member in fields] for name, fields in members.items()}
    manifest = {"target": "1516-3 V3.0; runtime version recorded in evidence", "capacities": caps, "enums": enums,
                "timestamp_representation": timestamp, "witness_encodings": {},
                "sources": {}, "types": {}, "witnesses": {}}
    for name in declarations:
        source = DUTS / (name + ".TcDUT")
        manifest["sources"][str(source.relative_to(REPO))] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest["sources"][str(COMMON.PARAMS.relative_to(REPO))] = hashlib.sha256(COMMON.PARAMS.read_bytes()).hexdigest()
    ordered = []
    visiting = set()

    def split_type(raw):
        original = raw.split(":=")[0].strip()
        array = re.fullmatch(r"ARRAY\[(.*?)\.\.(.*?)\]\s+OF\s+(.*)", original, re.I)
        return original, array, array[3].strip() if array else original

    def scalar_type(scalar):
        if scalar in structures:
            build(scalar)
            return '"' + native_name(scalar) + '"'
        return native_scalar(scalar, enums, timestamp)

    def build(name):
        if name in manifest["types"]:
            return
        if name in visiting:
            raise ValueError("recursive value type " + name)
        visiting.add(name)
        fields = []
        for definition in members[name]:
            member, raw = definition["name"], definition["type"]
            original, array, scalar = split_type(raw)
            native = scalar_type(scalar)
            if array:
                native = "Array[%d..%d] of %s" % (COMMON.bound(array[1], caps), COMMON.bound(array[2], caps), native)
            fields.append({"member": member, "core_type": original, "native_type": native,
                           "accessible": definition["accessible"]})
        manifest["types"][name] = fields
        ordered.append(name)
        visiting.remove(name)

    for name in structures:
        build(name)

    def write(name, lines):
        (out / name).write_bytes(("\n".join(lines) + "\n").encode("ascii"))

    def fill(name, prefix, depth=0):
        lines = []
        for member, raw in structures[name]:
            original, array, scalar = split_type(raw)
            target = prefix + '."' + member + '"'
            if array:
                index = "idx%d" % depth
                low, high = COMMON.bound(array[1], caps), COMMON.bound(array[2], caps)
                lines.append("    " * depth + "FOR #%s := %d TO %d DO" % (index, low, high))
                target += "[#" + index + "]"
            inner_depth = depth + bool(array)
            if scalar in structures:
                lines.extend(fill(scalar, target, inner_depth))
            else:
                if scalar in enums:
                    value = list(enums[scalar].values())[-1]
                    literal = str(value)
                elif re.fullmatch(r"STRING\(\d+\)", scalar):
                    literal = ("WSTRING#" if int(re.search(r"\d+", scalar)[0]) > 254 else "") + "'S'"
                    value = "S"
                else:
                    _, literal, value = scalar_map[scalar]
                lines.append("    " * inner_depth + target + " := " + literal + ";")
            if array:
                lines.append("    " * depth + "END_FOR;")
        return lines

    def leaves(name, prefix, accessible=True):
        for definition in members[name]:
            member, raw = definition["name"], definition["type"]
            visible = accessible and definition["accessible"]
            original, array, scalar = split_type(raw)
            suffixes = [""] if not array else ["[%d]" % n for n in sorted({COMMON.bound(array[1], caps), COMMON.bound(array[2], caps)})]
            for suffix in suffixes:
                path = prefix + "." + member + suffix
                if scalar in structures:
                    yield from leaves(scalar, path, visible)
                elif scalar == "DT" and timestamp == "DTL":
                    for member, value in DTL_WITNESS.items():
                        yield path + "." + member, value, visible
                else:
                    value = list(enums[scalar].values())[-1] if scalar in enums else "S" if scalar.startswith("STRING(") else scalar_map[scalar][2]
                    if scalar == "DT":
                        manifest["witness_encodings"][path] = "ldt"
                    yield path, value, visible

    for index, name in enumerate(ordered):
        type_name, db_name = native_name(name), "S12" + name.removeprefix("ST_")
        write("00_%03d_%s.udt" % (index, type_name), ['TYPE "' + type_name + '"', 'VERSION : 0.1', '   STRUCT',
              *['      "%s"%s : %s;' % (f["member"],
                 "" if f["accessible"] else " {ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'}",
                 f["native_type"]) for f in manifest["types"][name]], '   END_STRUCT;', 'END_TYPE'])
        write("05_%03d_%s.db" % (index, db_name), ['DATA_BLOCK "' + db_name + '"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN', '   VAR',
              '      Data : "' + type_name + '";', '   END_VAR', 'BEGIN', 'END_DATA_BLOCK'])
        body = fill(name, '"' + db_name + '"."Data"')
        write("10_%03d_Fill.scl" % index, ['FUNCTION "FC_S12Fill%03d" : Void' % index, "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
              '   VAR_TEMP', *['      idx%d : DInt;' % n for n in range(5)], '   END_VAR', 'BEGIN', *body, 'END_FUNCTION'])
        for path, value, accessible in leaves(name, db_name + ".Data"):
            manifest["witnesses"][path] = value
            if accessible:
                manifest.setdefault("web_witnesses", {})[path] = value
    manifest["ordered_types"] = ordered
    for path in HERE.iterdir():
        if path.suffix in (".scl", ".db", ".udt"):
            (out / path.name).write_bytes(path.read_bytes())
    write("19_LongStrings.scl", ['FUNCTION "FC_S12LongStrings" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN',
          '    "S12Probe".Text254 := \'' + 'a' * 253 + "Z';",
          '    "S12Probe".Text255 := WSTRING#\'' + 'b' * 254 + "Y';",
          '    "S12Probe".Text480 := WSTRING#\'' + 'c' * 479 + "X';", 'END_FUNCTION'])
    constants = [(name + "_" + member, value) for name, values in enums.items() for member, value in values.items()]
    if len({name.casefold() for name, _ in constants}) != len(constants):
        raise ValueError("generated constant names collide")
    manifest["enum_constant_count"] = len(constants)
    constant_source = ['FUNCTION "FC_S12EnumConstants" : DInt', "{ S7_Optimized_Access := 'TRUE' }",
                       'VERSION : 0.1', '   VAR CONSTANT',
                       *['      %s : DInt := %d;' % (name, value) for name, value in constants],
                       '   END_VAR', 'BEGIN', '    #FC_S12EnumConstants := 0;']
    for name, value in constants:
        constant_source.extend(['    IF #%s <> %d THEN' % (name, value),
                                '        #FC_S12EnumConstants := -1;', '        RETURN;', '    END_IF;',
                                '    #FC_S12EnumConstants := #FC_S12EnumConstants + 1;'])
    constant_source.append('END_FUNCTION')
    write("19_EnumConstants.scl", constant_source)
    stages = ['FUNCTION "FC_S12FillNext" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN', '    CASE "S12Probe".Stage OF']
    for index, name in enumerate(ordered):
        stages.extend(['        %d: "FC_S12Fill%03d"();' % (index, index), '            "S12Probe".Stage := %d;' % (index + 1)])
    stages.extend(['        %d: "S12Probe".Ready := TRUE;' % len(ordered), '    END_CASE;', 'END_FUNCTION'])
    write("20_FillNext.scl", stages)
    (out / "manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("ascii"))
    print(json.dumps({"generated": str(out), "structs": len(structures), "enums": len(enums),
                      "witnesses": len(manifest["witnesses"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--timestamp", choices=("DTL", "LDT"), default="LDT")
    args = parser.parse_args()
    generate(args.out, args.timestamp)
