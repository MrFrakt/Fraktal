#!/usr/bin/env python3
"""Print the object graph of an LD (`<NWL>`) body in a `.TcPOU`.

WHY THIS IS A GATE, NOT A CONVENIENCE
-------------------------------------
A clean compile does NOT prove a generated node exists. A node lifted out of a
`<l2 … cet="BoxTreeBox">` list loses the type the list gave it collectively;
dropped somewhere without a `cet` it becomes an untyped `<o>`, which still
parses, still compiles, and is simply **not there** at runtime. The same is true
of a gate that reads `EQ(215, 0)` instead of `EQ(_step, 215)`: perfectly legal
IEC, constantly FALSE, and no tool will say a word.

So after generating a rung, dump it and read the graph back. That is the step
that catches those, and it costs one command:

    python tools/ld_dump.py <file.TcPOU>

`tools/sfc_dump.py` is the same idea for an `<SFC>` chart.

The grammar you will see:

    DEMUX var=N (DEF)  a power node - its <o n="Input"> is what drives it
    DEMUX var=N (ref)  every later tap on that same rail
    OPERAND "x" : "T"  Flags 1 = negated contact, 0 = plain
    ASSIGN -> "x"{flags=N}   2 = Set coil (S), 3 = Reset coil (R), 0 = plain
    BOX "M_Step" params=[EN, StepNo, …] returns=[ENO, …]->[…]
                       InputItems match params POSITIONALLY; a value-returning
                       box has ENO in output slot 0 and its return in slot 1
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def _value(node: ET.Element, name: str) -> str | None:
    hit = node.find(f"./v[@n='{name}']")
    return hit.text if hit is not None else None


def _children(node: ET.Element, list_name: str) -> list[tuple[ET.Element, str]]:
    """Children of a `<l2>`, each with its effective type.

    A `<l2 … cet="X">` types its children collectively and they carry no `t=` of
    their own, so the list's `cet` has to be carried down or every child is
    reported as untyped - which is exactly the failure this dumper exists to
    make visible.
    """
    l2 = node.find(f"./l2[@n='{list_name}']")
    if l2 is None:
        return []
    cet = l2.get("cet")
    return [(child, child.get("t") or cet or "") for child in l2]


def describe(node: ET.Element, depth: int = 0, label: str = "",
             forced: str = "", *, show_ids: bool = True) -> list[str]:
    """One node and everything under it, as indented lines."""
    kind = node.get("t") or forced or ""
    pad = "  " * depth
    ident = f" id={_value(node, 'Id')}" if show_ids else ""
    lines: list[str] = []

    if kind == "BoxTreeBox":
        names = [v.text for v in
                 node.findall("./o[@n='InputParam']/l2[@n='Names']/v")]
        outs = [v.text for v in
                node.findall("./o[@n='OutputParam']/l2[@n='Names']/v")]
        wired = [_value(o, "Operand") for o in
                 node.findall("./o[@n='OutputItems']/l2[@n='OutputItems']/o")]
        lines.append(f"{pad}{label}BOX {_value(node, 'BoxType')}{ident} "
                     f"params={names} returns={outs}->{wired}")
        for child, child_type in _children(node, "InputItems"):
            lines += describe(child, depth + 1, forced=child_type,
                              show_ids=show_ids)
    elif kind == "BoxTreeOperand":
        operand = node.find("./o[@n='Operand']")
        flags = _value(operand.find("./o[@n='Flags']"), "Flags")
        negated = " NEG" if flags == "1" else ""
        lines.append(f"{pad}{label}OPERAND {_value(operand, 'Operand')} : "
                     f"{_value(operand, 'Type')}{negated}{ident}")
    elif kind == "BoxTreeDemux":
        driver = node.find("./o[@n='Input']")
        lines.append(f"{pad}{label}DEMUX var={_value(node, 'VarId')} "
                     f"({'DEF' if driver is not None else 'ref'}){ident}")
        if driver is not None:
            lines += describe(driver, depth + 1, "from ", show_ids=show_ids)
    elif kind == "BoxTreeAssign":
        targets = node.findall("./o[@n='OutputItems']/l2[@n='OutputItems']/o")
        coils = ", ".join(
            "{}{{flags={}}}".format(_value(o, "Operand"),
                                    _value(o.find("./o[@n='Flags']"), "Flags"))
            for o in targets)
        lines.append(f"{pad}{label}ASSIGN -> {coils}{ident}")
        rvalue = node.find("./o[@n='RValue']")
        if rvalue is not None:
            lines += describe(rvalue, depth + 1, "rvalue ", show_ids=show_ids)
    elif kind == "BoxTreeTerminator":
        lines.append(f"{pad}{label}TERMINATOR{ident}")
    else:
        lines.append(f"{pad}{label}<{kind}>{ident}")
    return lines


def network_lines(network: ET.Element, *, show_ids: bool = True) -> list[str]:
    """Every item of one network, in order."""
    lines: list[str] = []
    for l2 in network.findall("./l2"):
        if l2.get("n") in ("ILLines", "Connectors"):
            continue
        cet = l2.get("cet")
        for child in l2:
            lines += describe(child, 1, forced=child.get("t") or cet or "",
                              show_ids=show_ids)
    return lines


def body_lines(source: str, *, show_ids: bool = True) -> list[str]:
    """The whole `<NWL>` body: header, then every network."""
    root = ET.fromstring(source)
    body = root.find(".//NWL/XmlArchive/Data/o")
    if body is None:
        raise ValueError("no <NWL> body in this object - is it an LD POU?")
    networks = body.findall("./l2[@n='NetworkList']/o")
    lines = [f"networks={len(networks)} "
             f"BranchCounter={_value(body, 'BranchCounter')} "
             f"ValidIds={_value(body, 'ValidIds')} "
             f"view={_value(body, 'DefaultViewMode')}"]
    for index, network in enumerate(networks):
        ident = f" id={_value(network, 'Id')}" if show_ids else ""
        lines.append("")
        lines.append(f"=== network {index}{ident}")
        lines += network_lines(network, show_ids=show_ids)
    return lines


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        print("usage: python tools/ld_dump.py <file.TcPOU> [--no-ids]")
        return 2
    source = open(argv[1], encoding="utf-8-sig").read()
    show_ids = "--no-ids" not in argv[2:]
    print("\n".join(body_lines(source, show_ids=show_ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
