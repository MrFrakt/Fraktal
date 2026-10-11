"""Reference-1500 value types derived from Core and application declarations."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from fraktal_tia_types import bound, enum_values, plain, struct_members

REPO = Path(__file__).resolve().parents[4]
CORE = REPO / "FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core"
SCALARS = {name: name.title() for name in
           ("BOOL", "BYTE", "WORD", "DWORD", "SINT", "USINT", "INT", "UINT",
            "DINT", "UDINT", "LINT", "ULINT", "REAL", "LREAL", "TIME")}
SCALARS.update({"BOOL": "Bool", "DWORD": "DWord", "DINT": "DInt", "UDINT": "UDInt",
                "SINT": "SInt", "USINT": "USInt", "UINT": "UInt", "LINT": "LInt",
                "ULINT": "ULInt", "LREAL": "LReal", "DT": "LDT", "PVOID": "UDInt"})
PRIVATE = " {ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'}"
READONLY = " {ExternalWritable := 'False'}"


def literal(value):
    if not value.isascii():
        raise ValueError("SCL string must be ASCII")
    return "'" + value.replace("$", "$$").replace("'", "$'") + "'"


def split_type(raw):
    pieces = raw.split(":=", 1)
    original = pieces[0].strip()
    array = re.fullmatch(r"ARRAY\s*\[(.*?)\.\.(.*?)\]\s+OF\s+(.*)", original, re.I)
    return original, array, array[3].strip() if array else original, pieces[1].strip() if len(pieces) == 2 else ""


def native_scalar(scalar, enums, timestamp="LDT"):
    if scalar in enums:
        return "DInt"
    string = re.fullmatch(r"STRING\((\d+)\)", scalar, re.I)
    if string:
        width = int(string[1])
        if not 1 <= width <= 16382:
            raise ValueError("unsupported reference string width: " + scalar)
        return ("String" if width <= 254 else "WString") + "[%d]" % width
    if scalar.upper() == "DT":
        if timestamp not in ("LDT", "DTL"):
            raise ValueError("unsupported timestamp representation")
        return timestamp
    if scalar.upper() not in SCALARS:
        raise ValueError("unmapped reference type: " + scalar)
    return SCALARS[scalar.upper()]


@dataclass
class Catalog:
    records: dict
    enums: dict
    capacities: dict
    inputs: dict

    @classmethod
    def read(cls, application=()):
        records, enums, inputs = {}, {}, {}
        for path in sorted((CORE / "DUTs").glob("*.TcDUT")):
            data = path.read_bytes()
            text = ET.fromstring(data).findtext(".//Declaration")
            inputs[path.relative_to(REPO).as_posix()] = hashlib.sha256(data).hexdigest()
            if path.stem.startswith("ST_"):
                records[path.stem] = struct_members(text)
            elif path.stem.startswith("E_"):
                enums[path.stem] = enum_values(text)
        params = CORE / "Params/PL_Fraktal.TcGVL"
        data = params.read_bytes()
        inputs[params.relative_to(REPO).as_posix()] = hashlib.sha256(data).hexdigest()
        text = plain(ET.fromstring(data).findtext(".//Declaration"))
        capacities = {name: int(value) for name, value in
                      re.findall(r"(MAX_\w+)\s*:\s*\w+\s*:=\s*(\d+)", text)}
        for name, text in application:
            if name.casefold() in {key.casefold() for key in records}:
                raise ValueError("application record collides with Core: " + name)
            records[name] = struct_members(text)
        return cls(records, enums, capacities, inputs)

    def resolve(self, requested):
        """Dependency order and physical fields; reject unresolved/recursive types."""
        result, visiting = {}, set()

        def scalar_type(scalar):
            if scalar in self.records:
                build(scalar)
                return '"' + scalar + '"'
            return native_scalar(scalar, self.enums)

        def build(name):
            if name in result:
                return
            if name in visiting:
                raise ValueError("recursive value type: " + name)
            if name not in self.records:
                raise ValueError("unknown record: " + name)
            visiting.add(name)
            fields = []
            for member in self.records[name]:
                original, array, scalar, initial = split_type(member["type"])
                native = scalar_type(scalar)
                if array:
                    low, high = bound(array[1], self.capacities), bound(array[2], self.capacities)
                    if type(low) is not int or type(high) is not int or high < low:
                        raise ValueError("invalid array bounds: " + original)
                    native = "Array[%d..%d] of %s" % (low, high, native)
                if initial:
                    if scalar.upper() == 'TIME' and initial.upper() == 'T#0S':
                        initial = 'T#0ms'  # TIA's native source spelling of zero TIME.
                    if scalar in self.enums:
                        enum = re.fullmatch(re.escape(scalar) + r"\.(\w+)", initial)
                        if not enum or enum[1] not in self.enums[scalar]:
                            raise ValueError("unsupported enum initializer: " + initial)
                        initial = str(self.enums[scalar][enum[1]])
                    elif not re.fullmatch(r"TRUE|FALSE|-?\d+|T#[\dA-Z]+|'(?:\$.|[^'])*'", initial, re.I):
                        raise ValueError("unsupported initializer: " + initial)
                fields.append({"member": member["name"], "core_type": original,
                               "native_type": native, "accessible": member["accessible"], "initial": initial})
            result[name] = fields
            visiting.remove(name)

        for name in requested:
            build(name)
        return result


def type_source(name, fields):
    lines = ['TYPE "' + name + '"', 'VERSION : 0.1', '   STRUCT']
    for field in fields:
        lines.append('      "%s"%s : %s%s;' %
                     (field["member"], "" if field["accessible"] else PRIVATE,
                      field["native_type"], " := " + field["initial"] if field["initial"] else ""))
    return "\n".join(lines + ['   END_STRUCT;', 'END_TYPE', ''])
