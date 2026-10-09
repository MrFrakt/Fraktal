"""Fraktal/TIA S7-GRAPH writer and reader (Part IV §3.5, S11).

    python fraktal_tia_graph.py generate <chain.json> <reference.xml> <out.xml>
    python fraktal_tia_graph.py dump <graph-fb.xml>                  canonical chart as JSON
    python fraktal_tia_graph.py parity <graph-fb.xml> <chain.scl>    same steps and edges?

A GRAPH chart is a serialized object graph, so it is never written by hand: it is
GENERATED from a chain declaration, with a block TIA itself exported as the
template (the GRAPH interface, block attributes, step times and the empty
supervision and interlock networks all come from that export), and READ BACK to
prove the result. `dump` reads TIA's own re-export the same way, so the check
covers what TIA stored, not only what was sent.

Every form used here was first compiled by TIA V20 (S11 evidence): actions are
token streams with a qualifier and an optional event (S1 = step activated, S0 =
deactivated); CALL parameters are newline-separated, not comma-separated; InOut
struct and InOut FB-instance members are readable and writable in actions;
transitions are FBD networks (an AND box) ending in a TrCoil.

A GRAPH action holds an assignment of one operand or a CALL - TIA refuses an IF
("Tag IF not defined") and a Boolean expression ("The operand is missing or has
an incorrect data type") - so a step's exit decision is the transition network,
and a conditional wait is a service taking the condition as an operand
(FRK_Seq_AwaitPending). Generated step pattern for a
step that commands children ("issue"). GRAPH runs the old step's S0 and the new
step's S1 in one cycle, so an Execute dropped on exit and raised on entry would
never show the child the drop (Core §6.1). The pattern keeps Execute low for the
step's first active scan:
    S1  N  #Seq.Issued := FALSE          re-arm the step's issue latch
    S1  N  #<Child>.Command := <cmd>
        N  CALL "FRK_Seq_Step"(...)      Core §6.5 step record (and S11 trace)
        N  #<Child>.Execute := #Seq.Issued
        N  CALL "FRK_Seq_Await..."(...)  names the awaited child (Core §6.9)
        N  #Seq.Issued := TRUE
    S0  N  #<Child>.Execute := FALSE
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

GRAPH_NS = "http://www.siemens.com/automation/Openness/SW/NetworkSource/Graph/v5"
NS = {"g": GRAPH_NS}

TOKEN_RE = re.compile(r"\n|[ \t]+|'[^']*'|\"[^\"]*\"|:=|#?[A-Za-z_][\w.\[\]]*|\d+|.")


def tokenize(statement: str) -> list[str]:
    """One token per lexeme, newline on its own, as TIA serializes action text."""
    return [m.group(0) for m in TOKEN_RE.finditer(statement)]


def call_text(fc: str, params: list[tuple[str, str]]) -> str:
    """A CALL in the layout TIA emits: one parameter per line, no commas."""
    lines = ['CALL "%s" ' % fc, "    (%s := %s" % params[0]]
    lines += ["     %s := %s" % p for p in params[1:]]
    return "\n".join(lines) + "\n    )"


def xml_attr(text: str) -> str:
    return (text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "&#xA;"))


def action_xml(text: str, event: str = "", qualifier: str = "N") -> str:
    attrs = (' Event="%s"' % event if event else "") + ' Qualifier="%s"' % qualifier
    tokens = "".join('            <Token Text="%s" />\n' % xml_attr(t) for t in tokenize(text + "\n"))
    return "          <Action%s>\n%s          </Action>\n" % (attrs, tokens)


def step_actions(step: dict) -> list[str]:
    """The Core step behaviour as GRAPH actions (pattern in the module doc)."""
    issue = step.get("issue", [])
    out = []
    if issue:
        out.append(action_xml("#Seq.Issued := FALSE", "S1"))
        out += [action_xml("#%s.Command := %d" % (child, cmd), "S1") for child, cmd in issue]
    out.append(action_xml(call_text("FRK_Seq_Step", [("StepNo", str(step["no"])),
                                                     ("StepName", "'%s'" % step["label"]), ("Seq", "#Seq")])))
    out += [action_xml("#%s.Execute := #Seq.Issued" % child) for child, _ in issue]
    for wait in step.get("await", []):
        params = [("ChildIdx", str(wait["idx"])), ("Label", "'%s'" % wait["label"])]
        if "pending_until" in wait:   # named only while that condition is false
            out.append(action_xml(call_text("FRK_Seq_AwaitPending",
                                            params + [("Done", wait["pending_until"]), ("Seq", "#Seq")])))
        else:
            out.append(action_xml(call_text("FRK_Seq_Await", params + [("Seq", "#Seq")])))
    if issue:
        out.append(action_xml("#Seq.Issued := TRUE"))
        out += [action_xml("#%s.Execute := FALSE" % child, "S0") for child, _ in issue]
    return out


def operand_xml(uid: int, operand: str) -> str:
    if operand.upper() in ("TRUE", "FALSE"):
        return ('            <Access Scope="LiteralConstant" UId="%d">\n              <Constant>\n'
                '                <ConstantType>Bool</ConstantType>\n'
                '                <ConstantValue>%s</ConstantValue>\n              </Constant>\n'
                '            </Access>\n' % (uid, operand.upper()))
    if not re.fullmatch(r"#[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", operand):
        raise ValueError("transition operand %r is not a local symbol or Bool literal" % operand)
    comps = "".join('                <Component Name="%s" />\n' % c for c in operand[1:].split("."))
    return ('            <Access Scope="LocalVariable" UId="%d">\n              <Symbol>\n%s'
            '              </Symbol>\n            </Access>\n' % (uid, comps))


def transition_xml(number: int, condition: list[str]) -> str:
    """FBD, no power rail: the operands through an AND box into the TrCoil."""
    if not condition:
        raise ValueError("transition %d has no condition (TIA refuses it)" % number)
    parts, wires, uid = [], [], 21
    ops = []
    for op in condition:
        parts.append(operand_xml(uid, op))
        ops.append(uid)
        uid += 1
    box, coil = uid, uid + 1
    parts.append('            <Part Name="A" UId="%d">\n'
                 '              <TemplateValue Name="Card" Type="Cardinality">%d</TemplateValue>\n'
                 '            </Part>\n' % (box, len(ops)))
    parts.append('            <Part Name="TrCoil" UId="%d" />\n' % coil)
    uid += 2
    for i, op in enumerate(ops, start=1):
        wires.append((uid, '<IdentCon UId="%d" />' % op, '<NameCon UId="%d" Name="in%d" />' % (box, i)))
        uid += 1
    wires.append((uid, '<NameCon UId="%d" Name="out" />' % box, '<NameCon UId="%d" Name="in" />' % coil))
    wire_xml = "".join('            <Wire UId="%d">\n              %s\n              %s\n            </Wire>\n' % w
                       for w in wires)
    return ('      <Transition IsMissing="false" Name="T%d" Number="%d" ProgrammingLanguage="FBD">\n'
            '        <FlgNet>\n          <Parts>\n%s          </Parts>\n          <Wires>\n%s'
            '          </Wires>\n        </FlgNet>\n      </Transition>\n' % (number, number, "".join(parts), wire_xml))


def connection_xml(frm: str, to: str, link: str) -> str:
    return ("      <Connection>\n        <NodeFrom>\n          %s\n        </NodeFrom>\n"
            "        <NodeTo>\n          %s\n        </NodeTo>\n        <LinkType>%s</LinkType>\n"
            "      </Connection>\n" % (frm, to, link))


def once(text: str, pattern: str, repl, flags=0) -> str:
    out, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        raise ValueError("template anchor not found: %s" % pattern[:70])
    return out


def generate(chain: dict, reference: str) -> str:
    ref = reference.lstrip("﻿").replace("\r\n", "\n")
    steps = chain["steps"]
    graph_no = {s["no"]: i for i, s in enumerate(steps, start=1)}   # GRAPH numbers steps 1..n
    if len(graph_no) != len(steps):
        raise ValueError("duplicate step number")
    step_attrs = re.search(r'<Step Number="\d+" Init="\w+" Name="[^"]*"( [^>]*)>', ref).group(1)
    sv_il = re.search(r"\n(        <Supervisions>\n.*?        </Interlocks>\n)", ref, re.S).group(1)

    step_xml, trans_xml, conns = [], [], []
    for i, s in enumerate(steps, start=1):
        step_xml.append('      <Step Number="%d" Init="%s" Name="N%03d"%s>\n        <Actions>\n%s'
                        '          <Action />\n        </Actions>\n%s      </Step>\n'
                        % (i, "true" if i == 1 else "false", s["no"], step_attrs, "".join(step_actions(s)), sv_il))
        trans_xml.append(transition_xml(i, s["when"]))
        if s["next"] not in graph_no:
            raise ValueError("step %d advances to undeclared step %d" % (s["no"], s["next"]))
        target = graph_no[s["next"]]
        conns.append(connection_xml('<StepRef Number="%d" />' % i, '<TransitionRef Number="%d" />' % i, "Direct"))
        # the step drawn next is reached directly; any other target is a jump
        conns.append(connection_xml('<TransitionRef Number="%d" />' % i, '<StepRef Number="%d" />' % target,
                                    "Direct" if target == i + 1 else "Jump"))

    out = once(ref, r"    <Steps>\n.*?    </Connections>\n",
               lambda m: "    <Steps>\n" + "".join(step_xml) + "    </Steps>\n    <Transitions>\n" + "".join(trans_xml)
               + "    </Transitions>\n    <Branches />\n    <Connections>\n" + "".join(conns) + "    </Connections>\n", re.S)

    # interface: the chain's InOut parameters in; the template's own statics and temps out
    inout = "".join('    <Member Name="%s" Datatype="&quot;%s&quot;" Accessibility="Public" />\n' % (n, t)
                    for n, t in chain["inout"])
    out = once(out, r'\n  <Section Name="InOut" />\n', lambda m: '\n  <Section Name="InOut">\n' + inout + "  </Section>\n")
    static = re.search(r'\n  <Section Name="Static">\n(.*?)\n  </Section>\n', out, re.S)
    kept = re.findall(r'    <Member Name="RT_DATA" .*?\n    </Member>', static.group(1), re.S)
    if len(kept) != 1:
        raise ValueError("template has no GRAPH RT_DATA static")
    out = out[:static.start(1)] + kept[0] + out[static.end(1):]
    out = once(out, r'\n  <Section Name="Temp">\n.*?\n  </Section>\n', '\n  <Section Name="Temp" />\n', re.S)
    out = once(out, r"<Name>[^<]+</Name>", "<Name>%s</Name>" % chain["name"])
    out = once(out, r"<Number>\d+</Number>", "<Number>%d</Number>" % chain["number"])
    ET.fromstring(out.encode("utf-8"))                       # well-formed, or fail here
    return out


# ------------------------------------------------------------------ reader

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def dump(xml_text: str) -> dict:
    """Canonical chart: steps by Fraktal step number, their actions, and the
    edges with the operands and boxes of each transition."""
    root = ET.fromstring(xml_text.lstrip("﻿").encode("utf-8"))
    seq = root.find(".//g:Graph/g:Sequence", NS)
    steps, by_number = [], {}
    for st in seq.findall("g:Steps/g:Step", NS):
        name = st.get("Name")
        no = int(name[1:]) if re.fullmatch(r"N\d+", name) else name
        by_number[st.get("Number")] = no
        actions = []
        for a in st.findall("g:Actions/g:Action", NS):
            text = "".join(t.get("Text") for t in a.findall("g:Token", NS)).strip()
            if text:
                actions.append({"event": a.get("Event", ""), "qualifier": a.get("Qualifier", ""),
                                "text": re.sub(r"\s+", " ", text)})
        steps.append({"step": no, "init": st.get("Init") == "true", "actions": actions})
    conditions = {}
    for t in seq.findall("g:Transitions/g:Transition", NS):
        operands = []
        for acc in (e for e in t.iter() if _local(e.tag) == "Access"):
            comps = [c.get("Name") for c in acc.iter() if _local(c.tag) == "Component"]
            const = [c.text for c in acc.iter() if _local(c.tag) == "ConstantValue"]
            operands.append("#" + ".".join(comps) if comps else const[0])
        boxes = [p.get("Name") for p in t.iter() if _local(p.tag) == "Part" and p.get("Name") != "TrCoil"]
        conditions[t.get("Number")] = {"language": t.get("ProgrammingLanguage"), "operands": operands, "boxes": boxes}
    source, edges = {}, []
    links = [(c.find("g:NodeFrom/*", NS), c.find("g:NodeTo/*", NS), c.find("g:LinkType", NS).text)
             for c in seq.findall("g:Connections/g:Connection", NS)]
    for frm, to, _ in links:
        if _local(frm.tag) == "StepRef" and _local(to.tag) == "TransitionRef":
            source[to.get("Number")] = by_number[frm.get("Number")]
    for frm, to, link in links:
        if _local(frm.tag) == "TransitionRef" and _local(to.tag) == "StepRef":
            t = frm.get("Number")
            edges.append({"from": source.get(t), "to": by_number[to.get("Number")], "link": link,
                          "when": conditions.get(t)})
    edges.sort(key=lambda e: (str(e["from"]), str(e["to"])))
    return {"steps": steps, "edges": edges}


def scl_edges(scl: str) -> set[tuple[int, int]]:
    """Edges of an SCL `CASE #Seq.Step OF` chain: each label's FRK_Seq_Advance targets."""
    body = re.sub(r"//[^\n]*", "", scl)
    labels = list(re.finditer(r"^\s*(\d+)\s*:(?!=)", body, re.M))
    edges = set()
    for i, lab in enumerate(labels):
        branch = body[lab.end(): labels[i + 1].start() if i + 1 < len(labels) else len(body)]
        for adv in re.finditer(r'"FRK_Seq_Advance"\s*\(\s*OnAdvance\s*:=\s*(-?\d+)\s*,\s*OnJump1\s*:=\s*(-?\d+)', branch):
            edges |= {(int(lab.group(1)), int(t)) for t in adv.groups() if int(t) >= 0}
    return edges


def parity(graph_xml: str, scl: str) -> tuple[bool, set, set]:
    """The rendition gate (Part IV §3.5, §5.3): identical step graphs."""
    g = {(e["from"], e["to"]) for e in dump(graph_xml)["edges"]}
    s = scl_edges(scl)
    return g == s, g - s, s - g


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "generate" and len(argv) == 4:
        chain = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
        out = generate(chain, pathlib.Path(argv[2]).read_text(encoding="utf-8-sig"))
        target = pathlib.Path(argv[3])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(out.encode("utf-8"))
        print("generated %s: %s, %d steps" % (argv[3], chain["name"], len(chain["steps"])))
        return 0
    if cmd == "dump" and len(argv) == 2:
        print(json.dumps(dump(pathlib.Path(argv[1]).read_text(encoding="utf-8-sig")), indent=1))
        return 0
    if cmd == "parity" and len(argv) == 3:
        ok, only_g, only_s = parity(pathlib.Path(argv[1]).read_text(encoding="utf-8-sig"),
                                    pathlib.Path(argv[2]).read_text(encoding="utf-8"))
        print("parity %s; only in GRAPH %s; only in SCL %s" % ("OK" if ok else "FAILED", sorted(only_g), sorted(only_s)))
        return 0 if ok else 1
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
