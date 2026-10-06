"""Execute the ladder this binding generates, so a rung is tested by what it DOES.

The ST model (`fraktal_ab_st_model`) runs the structured text; until now a
ladder rendition was tested only by reading its text. That proves a leg is
present, not that the legs together do the right thing - and a ladder fault
otherwise first shows itself on the controller, one download later.

This is NOT a Logix emulator either. It runs the subset `fraktal_ab_generate`
emits for a chain: series instructions, parallel branches, the comparisons
EQU NEQ GRT GEQ LES LEQ, and MOV ADD SUB MUL. Anything else is refused rather
than guessed. Operands are parsed and evaluated by the ST model, so the two
models agree on tags, members, subscripts, faults and DINT wraparound.

Logix semantics it keeps:

* instructions execute left to right, and a branch's legs top to bottom, so a
  MOV in one leg is seen by a comparison in the next;
* every leg of a branch starts from the rung condition at the branch, and the
  branch passes on the OR of its legs;
* an output instruction does nothing on a false rung (MOV, ADD, SUB and MUL
  have no false-rung action).
"""

from __future__ import annotations

import re
from typing import Any

import fraktal_ab_st_model as st

COMPARE = {
    "EQU": lambda a, b: a == b,
    "NEQ": lambda a, b: a != b,
    "GRT": lambda a, b: a > b,
    "GEQ": lambda a, b: a >= b,
    "LES": lambda a, b: a < b,
    "LEQ": lambda a, b: a <= b,
}
MATH = {
    "ADD": lambda a, b: a + b,
    "SUB": lambda a, b: a - b,
    "MUL": lambda a, b: a * b,
}

_NAME = re.compile(r"[A-Z][A-Z0-9]*\(")


def _split_args(text: str) -> list[str]:
    args, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(text[start:i])
            start = i + 1
    args.append(text[start:])
    return args


def _series(text: str, pos: int, enders: str) -> tuple[list, int]:
    elements: list = []
    while pos < len(text) and text[pos] not in enders:
        if text[pos] == "[":
            legs, pos = [], pos + 1
            while True:
                leg, pos = _series(text, pos, ",]")
                legs.append(leg)
                if pos >= len(text):
                    raise st.StError("unterminated branch")
                if text[pos] == ",":
                    pos += 1
                    continue
                pos += 1
                break
            elements.append(("branch", legs))
            continue
        m = _NAME.match(text, pos)
        if not m:
            raise st.StError(f"cannot read a rung at: {text[pos:pos + 40]!r}")
        name, depth, i = m.group()[:-1], 1, m.end()
        while depth:
            if i >= len(text):
                raise st.StError(f"unterminated {name}(")
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        elements.append(("instr", name, _split_args(text[m.end():i - 1])))
        pos = i
    return elements, pos


def parse_rung(text: str) -> list:
    body = "".join(text.split()).rstrip(";")
    elements, pos = _series(body, 0, "")
    if pos != len(body):
        raise st.StError(f"trailing text in rung: {body[pos:]!r}")
    return elements


def _operand(text: str) -> tuple:
    parser = st._Parser(st.tokenize(text))
    node = parser.expr()
    if parser.peek().kind != "eof":
        raise st.StError(f"cannot read operand {text!r}")
    return node


def _destination(text: str) -> tuple:
    parser = st._Parser(st.tokenize(text))
    node = parser.lvalue()
    if parser.peek().kind != "eof":
        raise st.StError(f"cannot read destination {text!r}")
    return node


def _run(plc: st.Controller, elements: list, power: bool) -> bool:
    for element in elements:
        if element[0] == "branch":
            power = any([_run(plc, leg, power) for leg in element[1]])
            continue
        _, name, args = element
        if name in COMPARE:
            if len(args) != 2:
                raise st.StError(f"{name} takes two operands")
            if power:
                a = plc._int(plc.eval(_operand(args[0])))
                b = plc._int(plc.eval(_operand(args[1])))
                power = COMPARE[name](a, b)
        elif name == "MOV":
            if len(args) != 2:
                raise st.StError("MOV takes (Source,Dest)")
            if power:
                plc.write(_destination(args[1]), plc._int(plc.eval(_operand(args[0]))))
        elif name in MATH:
            if len(args) != 3:
                raise st.StError(f"{name} takes (SourceA,SourceB,Dest)")
            if power:
                a = plc._int(plc.eval(_operand(args[0])))
                b = plc._int(plc.eval(_operand(args[1])))
                plc.write(_destination(args[2]), st._wrap(MATH[name](a, b)))
        else:
            raise st.StError(f"{name} is outside the modeled ladder subset")
    return power


def run_rung(plc: st.Controller, rung: str | list) -> bool:
    """Scan one rung; return its rung-condition-out."""
    elements = parse_rung(rung) if isinstance(rung, str) else rung
    return _run(plc, elements, True)


def run_rungs(plc: st.Controller, rungs: Any) -> None:
    """Scan a routine's rungs in order, as one routine scan."""
    for rung in rungs:
        run_rung(plc, rung)
