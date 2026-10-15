"""Compare S12 compiled interfaces and source round-trips without hiding code."""
import argparse
import json
import pathlib
import re
import xml.etree.ElementTree as ET

TOKEN = re.compile(r"//[^\n]*|\(\*.*?\*\)|\s+|'(?:\$.|[^'])*'|\"[^\"]*\"|[A-Za-z_]\w*|\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?|:=|<>|<=|>=|\.\.|.", re.S)


def canonical(source):
    # TIA adds this native DTL library annotation when generating a source.
    source = re.sub(r"\{\s*InstructionName\s*:=\s*'DTL';\s*LibVersion\s*:=\s*'1\.0'\s*\}", "", source)
    source = re.sub(r'^TITLE\s*=\s*"Main Program Sweep \(Cycle\)"\s*$', '', source, flags=re.M)
    if re.match(r'\s*ORGANIZATION_BLOCK\b', source):
        source = re.sub(r'VAR_INPUT\s+Initial_Call\s*:\s*Bool;\s+Remanence\s*:\s*Bool;\s+END_VAR', '', source, flags=re.I)
    tokens = []
    for match in TOKEN.finditer(source.lstrip("\ufeff")):
        token = match[0]
        if token.isspace() or token.startswith("//") or token.startswith("(*"):
            continue
        if token.startswith('"') and re.fullmatch(r'"[A-Za-z_]\w*"', token):
            token = token[1:-1]
        tokens.append(token if token.startswith("'") else token.upper())
    return tokens


def type_fields(path):
    root = ET.parse(path)
    members = root.findall(".//Interface/{*}Sections/{*}Section/{*}Member")
    if not members:
        raise ValueError("no compiled fields: " + str(path))
    return [(m.attrib["Name"], m.attrib["Datatype"]) for m in members]


def verify_types(generated, exported):
    manifest = json.loads((generated / "manifest.json").read_text())
    result = {}
    for name, fields in manifest["types"].items():
        native = "ST_S12" + name.removeprefix("ST_")
        actual = type_fields(exported / "xml" / (native + ".type.xml"))
        expected = [(f["member"], f["native_type"]) for f in fields]
        if [(n, re.sub(r"\s+", "", t).upper()) for n, t in actual] != [(n, re.sub(r"\s+", "", t).upper()) for n, t in expected]:
            raise ValueError("compiled type differs: " + name)
        native_members = ET.parse(exported / "xml" / (native + ".type.xml")).findall(".//Interface/{*}Sections/{*}Section/{*}Member")
        for field, member in zip(fields, native_members):
            if "accessible" not in field:
                continue  # Historical allocation manifests predate publication mapping.
            attributes = {item.attrib["Name"]: item.text.lower() == "true"
                          for item in member.findall("./{*}AttributeList/{*}BooleanAttribute")}
            for attribute in ("ExternalAccessible", "ExternalVisible"):
                if attributes.get(attribute, True) != field["accessible"]:
                    raise ValueError("compiled publication differs: %s.%s %s" % (name, field["member"], attribute))
            if not field["accessible"] and attributes.get("ExternalWritable", True):
                raise ValueError("private field is writable: %s.%s" % (name, field["member"]))
        result[name] = {"fields": len(actual), "equal": True}
    return result


def compare_sources(first, second):
    result = {}
    files = sorted(p for p in first.iterdir() if p.suffix in (".scl", ".udt", ".db"))
    for path in files:
        next_path = second / path.name
        if not next_path.exists():
            raise ValueError("source missing: " + path.name)
        a, b = canonical(path.read_text(encoding="utf-8-sig")), canonical(next_path.read_text(encoding="utf-8-sig"))
        if a != b:
            index = next((n for n, pair in enumerate(zip(a, b)) if pair[0] != pair[1]), min(len(a), len(b)))
            raise ValueError("source differs: %s token%d %r vs %r" % (path.name, index, a[index:index+8], b[index:index+8]))
        result[path.name] = {"tokens": len(a), "equal": True}
    other = {p.name for p in second.iterdir() if p.suffix in (".scl", ".udt", ".db")}
    if {p.name for p in files} != other:
        raise ValueError("export source inventories differ")
    return result


def compare_authored(generated, exported):
    result = {}
    for path in sorted(generated.iterdir()):
        if path.suffix not in (".scl", ".udt", ".db"):
            continue
        source = path.read_text(encoding="ascii")
        name = re.search(r'\b(?:TYPE|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\s+"([^"]+)"', source)[1]
        target = exported / "scl" / (name + path.suffix)
        a, b = canonical(source), canonical(target.read_text(encoding="utf-8-sig"))
        if a != b:
            index = next((n for n, pair in enumerate(zip(a, b)) if pair[0] != pair[1]), min(len(a), len(b)))
            raise ValueError("authored source differs: %s token%d %r vs %r" % (path.name, index, a[index:index+8], b[index:index+8]))
        result[name] = {"tokens": len(a), "equal": True}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated", type=pathlib.Path)
    parser.add_argument("exported", type=pathlib.Path)
    parser.add_argument("--second", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = {"types": verify_types(args.generated, args.exported), "authored_source": compare_authored(args.generated, args.exported)}
    if args.second:
        result["source_roundtrip"] = compare_sources(args.exported / "scl", args.second / "scl")
    with args.out.open("x", encoding="ascii", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: len(value) for key, value in result.items()}))
