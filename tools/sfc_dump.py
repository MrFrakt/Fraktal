#!/usr/bin/env python3
"""Print the structure of an SFC (`<SFC>`) chart in a `.TcPOU`, and its GUID table.

The companion of `tools/ld_dump.py`, and a gate for the same reason: a chart
that parses and compiles can still be wrong in ways nothing reports. The two
that have actually cost time here:

  * the body hung on `EntryAction` instead of `MainAction` - it runs once and
    the chart stalls on its first step forever;
  * a step naming an action object that was since renamed - the step attribute
    holds only the action's NAME as a string, so both halves parse and neither
    warns.

Unlike a ladder rung, an SFC chart is a FLAT record of GUID-keyed attributes,
so this resolves the GUIDs through the archive's OWN descriptor dictionary
(`<d2 n="Attributes" ckt="Guid" cvt="SFCAttributeDescription">`) rather than a
remembered list. Two shapes in that archive mislead a reader:

  * the descriptor `d2` is a DICTIONARY - alternating `<v>` key and `<o>` value
    children, and the values are typed collectively by `cvt`, so none of them
    carries a `t=` of its own;
  * an attribute's value is a typed wrapper (`StringValue`, `BoolValue`, or
    `EnumValue`, the last carrying a `TemplateGuid` BEFORE its `Value`), and a
    transition stores its CONDITION expression in its `Name` attribute.

    python tools/sfc_dump.py <file.TcPOU>
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def _value(node: ET.Element, name: str) -> str | None:
    hit = node.find(f"./v[@n='{name}']")
    return hit.text if hit is not None else None


def _inner_list(node: ET.Element) -> list[ET.Element]:
    """A chart element's own child elements (a branch leg, a nested segment)."""
    holder = node.find("./o[@n='ElementList']/l2[@n='InnerList']")
    return list(holder) if holder is not None else []


def descriptor_table(body: ET.Element) -> dict[str, str]:
    """`{guid}` -> Identifier, read out of the archive's own dictionary."""
    table: dict[str, str] = {}
    dictionary = body.find("./d2[@n='Attributes']")
    if dictionary is None:
        return table
    for entry in dictionary:
        if entry.tag != "o":
            continue                       # the alternating <v> key; the value
        guid = _value(entry, "Id")         # carries the same guid, in braces
        identifier = (_value(entry, "Identifier") or "").strip('"')
        if guid:
            table[guid] = identifier
    return table


def _attribute_lines(node: ET.Element, pad: str, table: dict[str, str],
                     *, all_attributes: bool = False) -> list[str]:
    lines = []
    holder = node.find("./l2[@n='Attributes']")
    for attribute in list(holder) if holder is not None else []:
        guid = _value(attribute, "AttributeId")
        value = attribute.find("./o[@n='Value']")
        text = _value(value, "Value") if value is not None else None
        if not all_attributes and text in (None, '""', '"FALSE"', ""):
            continue
        lines.append(f"{pad}  @{table.get(guid, guid)} = {text}")
    return lines


def _walk(node: ET.Element, table: dict[str, str], depth: int = 0) -> list[str]:
    kind = node.get("t") or "?"
    pad = "  " * depth
    ident = f" id={_value(node, 'Id')}"
    lines = [f"{pad}{kind.replace('SFC', '').upper()}{ident}"]
    lines += _attribute_lines(node, pad, table)
    for child in _inner_list(node):
        lines += _walk(child, table, depth + 1)
    for segments in node.findall("./l2[@n='Segments']"):
        for segment in segments:
            lines += _walk(segment, table, depth + 1)
    return lines


def chart_lines(source: str) -> list[str]:
    root = ET.fromstring(source)
    body = root.find(".//SFC/XmlArchive/Data/o")
    if body is None:
        raise ValueError("no <SFC> body in this object - is it an SFC POU?")
    table = descriptor_table(body)
    lines = ["=== attribute descriptors (GUID -> name) ==="]
    lines += [f"  {guid}  {name}" for guid, name in sorted(table.items(),
                                                           key=lambda kv: kv[1])]
    lines += ["", "=== chart ==="]
    segment = body.find("./o[@n='Root']")
    if segment is not None:
        for element in _inner_list(segment):
            lines += _walk(element, table, 1)

    lines += ["", "=== actions declared on the POU ==="]
    lines += [f"  {action.get('Name')}" for action in root.iter("Action")]
    return lines


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    source = open(argv[1], encoding="utf-8-sig").read()
    print("\n".join(chart_lines(source)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
