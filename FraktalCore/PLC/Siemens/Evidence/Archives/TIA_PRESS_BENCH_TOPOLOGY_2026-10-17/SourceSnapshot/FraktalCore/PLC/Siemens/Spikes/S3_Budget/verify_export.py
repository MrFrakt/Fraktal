"""Compare the generated memory fixture's complete field/type lists with TIA XML."""
import argparse
import json
import pathlib
import re
import xml.etree.ElementTree as ET


def normalized(value):
    return re.sub(r"\s+", "", value.replace('"', '')).lower()


def verify(source, exported):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    for original, info in manifest["types"].items():
        name = "ST_S3" + original.removeprefix("ST_")
        root = ET.parse(exported / (name + ".type.xml")).getroot()
        section = next(element for element in root.iter() if element.tag.endswith("Section") and element.get("Name") == "None")
        actual = [(element.get("Name"), normalized(element.get("Datatype")))
                  for element in section if element.tag.endswith("Member")]
        expected = [(field["member"], normalized(field["native_type"])) for field in info["fields"]]
        if actual != expected:
            raise ValueError(f"type read-back mismatch {name}: expected {expected}, got {actual}")
    for storage in manifest["storage"]:
        name = "S3" + storage["name"]
        root = ET.parse(exported / (name + ".xml")).getroot()
        section = next(element for element in root.iter() if element.tag.endswith("Section") and element.get("Name") == "Static")
        members = [element for element in section if element.tag.endswith("Member")]
        expected = normalized(f'Array[1..{storage["count"]}] of "{storage["type"]}"')
        if (len(members) != 1 or members[0].get("Name") != "Data"
                or members[0].get("Remanence") != "NonRetain"
                or normalized(members[0].get("Datatype")) != expected):
            raise ValueError("storage read-back mismatch: " + name)
        layouts = [element.text for element in root.iter() if element.tag.endswith("MemoryLayout")]
        if layouts != ["Optimized"]:
            raise ValueError("storage is not optimized: " + name)
        attributes = {element.get("Name"): element.text for element in members[0].iter()
                      if element.tag.endswith("BooleanAttribute")}
        if any(attributes.get(flag) != "false" for flag in ("ExternalAccessible", "ExternalVisible", "ExternalWritable")):
            raise ValueError("storage unexpectedly published: " + name)
    print(json.dumps({"type_readback": "PASS", "types": len(manifest["types"]),
                      "storage_arrays": len(manifest["storage"]),
                      "group": manifest["group"], "profile": manifest["profile"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("exported", type=pathlib.Path)
    args = parser.parse_args()
    verify(args.source, args.exported)
