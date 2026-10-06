"""Execute the Structured Text this binding generates, so tests see BEHAVIOUR.

Until now a generated routine was tested by reading its text: that a guard is
present, that a subscript is range-checked. That catches a missing line and
nothing else - a ring that wraps one slot early, or a loop that closes the
wrong event, reads exactly as plausible as the right one. The alarm log (Core
§8.3) is the first routine whose correctness is in its arithmetic rather than
its shape, so it is the first to need running.

This is NOT a Logix emulator. It executes the subset `fraktal_ab_generate`
emits - assignment, IF/ELSIF/ELSE, FOR, CASE, DINT arithmetic and comparison,
AND/OR/XOR/NOT, member access and subscripts - and a call only when the test
supplies it. Anything else is refused rather than guessed, so a construct the
model does not know cannot pass by being skipped.

Where Logix is unforgiving, so is this:

* a subscript out of range is a MAJOR fault on the controller (type 4, code
  20) and halts the program, so here it is an exception, not a clamp;
* an integer divide by zero is an exception (Logix sets a minor fault and
  keeps running, which is worse, so generated code guards every divide);
* DINT results wrap at 32 bits, `/` truncates toward zero and `MOD` takes the
  sign of the dividend, as Logix does;
* an IF/ELSIF condition must be BOOL. A DINT there is a verification error in
  Studio 5000, so it is an error here instead of an implicit `<> 0`;
* reading or writing a tag or member nobody declared is an error.

What it cannot tell you: whether Studio 5000 ACCEPTS the text. That is still
the compile gate (AB Part III, D3). This model answers the other question -
given that it compiles, does it do the right thing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

DINT_MIN, DINT_MAX = -(2 ** 31), 2 ** 31 - 1


class StError(Exception):
    """The text uses something this model does not execute."""


class StFault(Exception):
    """What would fault or misbehave on the controller."""


# --- lexing -----------------------------------------------------------------

_TOKEN = re.compile(r"""
    (?P<comment>\(\*.*?\*\))
  | (?P<ws>\s+)
  | (?P<number>\d+\.\d+|\d+)
  | (?P<name>[A-Za-z_]\w*(?::\w+)*)          # S:FS, Local:1:O
  | (?P<op>:=|<>|<=|>=|\.\.|[=<>+\-*/()\[\].,;:])
""", re.VERBOSE | re.DOTALL)

KEYWORDS = {
    "IF", "THEN", "ELSIF", "ELSE", "END_IF", "FOR", "TO", "BY", "DO",
    "END_FOR", "CASE", "OF", "END_CASE", "AND", "OR", "XOR", "NOT", "MOD",
}


@dataclass(frozen=True)
class Tok:
    kind: str       # number | name | kw | op | eof
    text: str


def tokenize(text: str) -> list[Tok]:
    out: list[Tok] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise StError(f"cannot read ST at: {text[pos:pos + 40]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind in ("comment", "ws"):
            continue
        value = m.group()
        if kind == "number" and "." in value:
            raise StError(f"REAL literal {value} is outside the modeled subset")
        if kind == "name" and value.upper() in KEYWORDS:
            out.append(Tok("kw", value.upper()))
        else:
            out.append(Tok(kind, value))
    out.append(Tok("eof", ""))
    return out


# --- parsing ----------------------------------------------------------------
#
# Nodes are tuples, first element the node type. Small, and printable in a
# failure message, which matters more here than a class hierarchy would.

class _Parser:
    def __init__(self, tokens: list[Tok]):
        self.toks = tokens
        self.i = 0

    def peek(self, ahead: int = 0) -> Tok:
        return self.toks[min(self.i + ahead, len(self.toks) - 1)]

    def next(self) -> Tok:
        tok = self.peek()
        self.i += 1
        return tok

    def accept(self, text: str) -> bool:
        if self.peek().text == text and self.peek().kind in ("kw", "op"):
            self.i += 1
            return True
        return False

    def expect(self, text: str) -> None:
        if not self.accept(text):
            raise StError(f"expected {text!r}, found {self.peek().text!r}")

    # statements

    def block(self, *enders: str) -> list[tuple]:
        body = []
        while not (self.peek().kind == "kw" and self.peek().text in enders):
            if self.peek().kind == "eof":
                if not enders:
                    break
                raise StError(f"unterminated block, expected one of {enders}")
            if self._at_case_label():
                break
            stmt = self.statement()
            if stmt is not None:
                body.append(stmt)
        return body

    def statement(self) -> tuple | None:
        tok = self.peek()
        if tok.text == ";" and tok.kind == "op":
            self.next()
            return None
        if tok.kind == "kw" and tok.text == "IF":
            return self.if_stmt()
        if tok.kind == "kw" and tok.text == "FOR":
            return self.for_stmt()
        if tok.kind == "kw" and tok.text == "CASE":
            return self.case_stmt()
        if tok.kind == "name" and self.peek(1).text == "(":
            return self.call_stmt()
        if tok.kind == "name":
            target = self.lvalue()
            self.expect(":=")
            value = self.expr()
            self.expect(";")
            return ("assign", target, value)
        raise StError(f"unexpected {tok.text!r}")

    def if_stmt(self) -> tuple:
        self.expect("IF")
        arms = []
        cond = self.expr()
        self.expect("THEN")
        arms.append((cond, self.block("ELSIF", "ELSE", "END_IF")))
        otherwise: list[tuple] = []
        while True:
            if self.accept("ELSIF"):
                cond = self.expr()
                self.expect("THEN")
                arms.append((cond, self.block("ELSIF", "ELSE", "END_IF")))
            elif self.accept("ELSE"):
                otherwise = self.block("END_IF")
            else:
                break
        self.expect("END_IF")
        self.expect(";")
        return ("if", arms, otherwise)

    def for_stmt(self) -> tuple:
        self.expect("FOR")
        var = self.lvalue()
        self.expect(":=")
        start = self.expr()
        self.expect("TO")
        stop = self.expr()
        step = self.expr() if self.accept("BY") else ("num", 1)
        self.expect("DO")
        body = self.block("END_FOR")
        self.expect("END_FOR")
        self.expect(";")
        return ("for", var, start, stop, step, body)

    def _at_case_label(self) -> bool:
        i = 0
        if self.peek().text == "-" and self.peek().kind == "op":
            i = 1
        if self.peek(i).kind != "number":
            return False
        return self.peek(i + 1).text in (":", ",", "..")

    def _label_value(self) -> int:
        negative = self.accept("-")
        tok = self.next()
        if tok.kind != "number":
            raise StError(f"CASE label must be an integer, found {tok.text!r}")
        return -int(tok.text) if negative else int(tok.text)

    def case_stmt(self) -> tuple:
        self.expect("CASE")
        selector = self.expr()
        self.expect("OF")
        arms = []
        otherwise: list[tuple] = []
        while True:
            if self._at_case_label():
                labels = []
                while True:
                    low = self._label_value()
                    high = self._label_value() if self.accept("..") else low
                    labels.append((low, high))
                    if not self.accept(","):
                        break
                self.expect(":")
                arms.append((labels, self.block("ELSE", "END_CASE")))
            elif self.accept("ELSE"):
                otherwise = self.block("END_CASE")
            else:
                break
        self.expect("END_CASE")
        self.expect(";")
        return ("case", selector, arms, otherwise)

    def call_stmt(self) -> tuple:
        name = self.next().text
        self.expect("(")
        args: list[tuple | None] = []
        while True:
            if self.peek().text in (",", ")") and self.peek().kind == "op":
                args.append(None)          # an empty argument, as in GSV
            else:
                args.append(self.expr())
            if self.accept(","):
                continue
            self.expect(")")
            break
        self.expect(";")
        return ("call", name, args)

    # expressions, lowest precedence first (IEC 61131-3 table 55)

    def expr(self) -> tuple:
        return self._binary(self._xor, ("OR",))

    def _xor(self) -> tuple:
        return self._binary(self._and, ("XOR",))

    def _and(self) -> tuple:
        return self._binary(self._compare, ("AND",))

    def _compare(self) -> tuple:
        return self._binary(self._add, ("=", "<>", "<", ">", "<=", ">="))

    def _add(self) -> tuple:
        return self._binary(self._mul, ("+", "-"))

    def _mul(self) -> tuple:
        return self._binary(self._unary, ("*", "/", "MOD"))

    def _binary(self, operand: Callable[[], tuple], ops: tuple[str, ...]) -> tuple:
        left = operand()
        while self.peek().text in ops and self.peek().kind in ("kw", "op"):
            op = self.next().text
            left = ("bin", op, left, operand())
        return left

    def _unary(self) -> tuple:
        if self.accept("NOT"):
            return ("not", self._unary())
        if self.accept("-"):
            return ("neg", self._unary())
        return self._primary()

    def _primary(self) -> tuple:
        tok = self.peek()
        if self.accept("("):
            inner = self.expr()
            self.expect(")")
            return inner
        if tok.kind == "number":
            self.next()
            return ("num", int(tok.text))
        if tok.kind == "name":
            if self.peek(1).text == "(":
                raise StError(f"function call {tok.text}() is outside the modeled subset")
            return self.lvalue()
        raise StError(f"unexpected {tok.text!r} in an expression")

    def lvalue(self) -> tuple:
        tok = self.next()
        if tok.kind != "name":
            raise StError(f"expected a tag name, found {tok.text!r}")
        path: list[tuple] = [("tag", tok.text)]
        while True:
            if self.accept("."):
                member = self.next()
                if member.kind != "name":
                    raise StError(f"bit or odd member access .{member.text} is not modeled")
                path.append(("member", member.text))
            elif self.accept("["):
                path.append(("index", self.expr()))
                self.expect("]")
            else:
                return ("ref", tuple(path))


def parse(text: str) -> list[tuple]:
    parser = _Parser(tokenize(text))
    body = parser.block()
    if parser.peek().kind != "eof":
        raise StError(f"unexpected {parser.peek().text!r} at top level")
    return body


# --- state ------------------------------------------------------------------

def structure(members) -> dict[str, Any]:
    """A UDT instance from its declared members: DINT, or DINT[n]."""
    out: dict[str, Any] = {}
    for member in members:
        if member.dimension:
            out[member.name] = [member.initial] * member.dimension
        else:
            out[member.name] = member.initial
    return out


def _wrap(value: int) -> int:
    return (value - DINT_MIN) % 2 ** 32 + DINT_MIN


Call = Callable[["Controller", list], None]


class Controller:
    """Controller-scope tags, and a program run against them."""

    def __init__(self, tags: dict[str, Any], calls: dict[str, Call] | None = None,
                 *, routines: dict[str, str | list] | None = None):
        self.tags = tags
        self.calls = calls or {}
        self.routines = {name: parse(body if isinstance(body, str) else '\n'.join(body))
                         if isinstance(body, str) or (body and isinstance(body[0], str)) else body
                         for name, body in (routines or {}).items()}

    # addressing

    def _container(self, ref: tuple) -> tuple[Any, Any]:
        """The object holding the last path element, and that element's key."""
        path = ref[1]
        kind, name = path[0]
        if name not in self.tags:
            raise StFault(f"tag {name} is not declared")
        holder: Any = self.tags
        key: Any = name
        for step in path[1:]:
            current = holder[key]
            if step[0] == "member":
                if not isinstance(current, dict) or step[1] not in current:
                    raise StFault(f"{self.describe(ref)}: no member {step[1]}")
                holder, key = current, step[1]
            else:
                if not isinstance(current, list):
                    raise StFault(f"{self.describe(ref)}: subscript on a non-array")
                index = self._int(self.eval(step[1]))
                if not 0 <= index < len(current):
                    raise StFault(
                        f"{self.describe(ref)}: index {index} outside "
                        f"0..{len(current) - 1} (Logix major fault 4/20)")
                holder, key = current, index
        return holder, key

    def describe(self, ref: tuple) -> str:
        text = ""
        for step in ref[1]:
            text += (step[1] if step[0] == "tag" else
                     f".{step[1]}" if step[0] == "member" else "[...]")
        return text

    def read(self, ref: tuple) -> Any:
        holder, key = self._container(ref)
        return holder[key]

    def write(self, ref: tuple, value: Any) -> None:
        holder, key = self._container(ref)
        if isinstance(holder[key], (list, dict)):
            raise StFault(f"{self.describe(ref)}: whole-aggregate assignment is not modeled")
        holder[key] = int(value) if isinstance(value, bool) else value

    def element(self, ref: tuple, offset: int) -> tuple[list, int]:
        """For a call that writes consecutive array elements from `ref` on."""
        holder, key = self._container(ref)
        if not isinstance(holder, list) or key + offset >= len(holder):
            raise StFault(f"{self.describe(ref)}: +{offset} is past the array")
        return holder, key + offset

    # evaluation

    @staticmethod
    def _int(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise StFault(f"expected a DINT, got {value!r}")
        return value

    def eval(self, node: tuple) -> Any:
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "bool":
            return node[1]
        if kind == "ref":
            value = self.read(node)
            if isinstance(value, (list, dict)):
                raise StFault(f"{self.describe(node)} is an aggregate, not a value")
            return value
        if kind == "neg":
            return _wrap(-self._int(self.eval(node[1])))
        if kind == "not":
            value = self.eval(node[1])
            return (not value) if isinstance(value, bool) else _wrap(~self._int(value))
        op, left, right = node[1], self.eval(node[2]), self.eval(node[3])
        if op in ("AND", "OR", "XOR"):
            if isinstance(left, bool) and isinstance(right, bool):
                return {"AND": left and right, "OR": left or right,
                        "XOR": left != right}[op]
            a, b = self._int(left), self._int(right)
            return {"AND": a & b, "OR": a | b, "XOR": a ^ b}[op]
        a, b = self._int(left), self._int(right)
        if op == "+":
            return _wrap(a + b)
        if op == "-":
            return _wrap(a - b)
        if op == "*":
            return _wrap(a * b)
        if op in ("/", "MOD"):
            if b == 0:
                raise StFault("integer divide by zero")
            quotient = abs(a) // abs(b) * (1 if (a >= 0) == (b >= 0) else -1)
            return _wrap(quotient) if op == "/" else _wrap(a - quotient * b)
        return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b,
                "<=": a <= b, ">=": a >= b}[op]

    def _condition(self, node: tuple) -> bool:
        value = self.eval(node)
        if not isinstance(value, bool):
            raise StFault("an IF condition must be BOOL; Studio 5000 rejects a DINT there")
        return value

    def run(self, program: list[tuple] | str) -> None:
        if isinstance(program, str):
            program = parse(program)
        for stmt in program:
            self._exec(stmt)

    def _exec(self, stmt: tuple) -> None:
        kind = stmt[0]
        if kind == "assign":
            self.write(stmt[1], self.eval(stmt[2]))
        elif kind == "if":
            for cond, body in stmt[1]:
                if self._condition(cond):
                    self.run(body)
                    return
            self.run(stmt[2])
        elif kind == "for":
            _, var, start, stop, step, body = stmt
            self.write(var, self._int(self.eval(start)))
            last, by = self._int(self.eval(stop)), self._int(self.eval(step))
            if by == 0:
                raise StFault("FOR with BY 0 never ends")
            while (self.read(var) <= last) if by > 0 else (self.read(var) >= last):
                self.run(body)
                self.write(var, _wrap(self.read(var) + by))
        elif kind == "case":
            value = self._int(self.eval(stmt[1]))
            for labels, body in stmt[2]:
                if any(low <= value <= high for low, high in labels):
                    self.run(body)
                    return
            self.run(stmt[3])
        elif kind == "call":
            if stmt[1] == 'JSR' and stmt[2] and stmt[2][0][0] == 'ref':
                name = stmt[2][0][1][0][1]
                if name in self.routines:
                    if len(stmt[2]) != 2 or self.eval(stmt[2][1]) != 0:
                        raise StError('routine model accepts only zero-parameter JSR')
                    self.run(self.routines[name])
                    return
            handler = self.calls.get(stmt[1])
            if handler is None:
                raise StError(f"no model supplied for {stmt[1]}()")
            handler(self, stmt[2])
        else:
            raise StError(f"unknown statement {kind}")


def gsv(attributes: dict, now: Callable[[], tuple[int, ...]] | None = None) -> Call:
    """GSV(Class,Instance,Attribute,Destination) over a table of DINT
    attributes keyed (class, instance or None, attribute) - a value or a
    callable - plus WallClockTime.DateTime from `now`. An attribute the table
    does not hold is refused, as Studio refuses one the controller lacks."""
    def call(controller: Controller, args: list) -> None:
        if len(args) != 4:
            raise StError("GSV takes (Class,Instance,Attribute,Destination)")
        name = lambda arg: None if arg is None else arg[1][0][1]
        cls, instance, attribute = name(args[0]), name(args[1]), name(args[2])
        if (cls, attribute) == ("WallClockTime", "DateTime") and now is not None:
            for offset, value in enumerate(now()):
                holder, key = controller.element(args[3], offset)
                holder[key] = value
            return
        key = (cls, instance, attribute)
        if key not in attributes:
            raise StError(f"GSV {key} is not modeled")
        value = attributes[key]
        controller.write(args[3], value() if callable(value) else value)
    return call


def cps_structure(controller: Controller, args: list) -> None:
    """CPS(Source,Dest,1) for identical whole-structure fixtures only.

    Copying is independent storage, never an alias. Other CPS shapes and
    mismatched layouts are refused; the model does not emulate task scheduling.
    """
    import copy
    if len(args) != 3 or controller.eval(args[2]) != 1:
        raise StError('only whole-structure CPS length 1 is modeled')
    source, dest = controller.read(args[0]), controller.read(args[1])
    def shape(value):
        if isinstance(value, dict):
            return [(k, shape(v)) for k, v in value.items()]
        if isinstance(value, list):
            return [shape(v) for v in value]
        return type(value)
    if not isinstance(source, dict) or shape(source) != shape(dest):
        raise StFault('CPS structure layouts differ')
    holder, key = controller._container(args[1])
    holder[key] = copy.deepcopy(source)


def btdt(controller: Controller, args: list) -> None:
    """Native FBD_BIT_FIELD_DISTRIBUTE instruction, not a SHA shortcut."""
    if len(args) != 1:
        raise StError('BTDT takes one FBD_BIT_FIELD_DISTRIBUTE record')
    record = controller.read(args[0])
    if not record['EnableIn']:
        record['EnableOut'] = 0
        return
    start, dest, length = record['SourceBit'], record['DestBit'], record['Length']
    if not 0 <= start <= 31 or not 0 <= dest <= 31 or not 1 <= length <= 32:
        raise StFault('invalid BTDT bit range')
    mask = ((1 << length) - 1) << dest
    source = (record['Source'] & 0xffffffff) >> start
    record['Dest'] = _wrap((record['Target'] & ~mask) | ((source << dest) & mask))
    record['EnableOut'] = 1


def wall_clock(now: Callable[[], tuple[int, ...]]) -> Call:
    """GSV(WallClockTime,,DateTime,dest[0]) as Logix does it: seven DINTs -
    year, month, day, hour, minute, second, microsecond - from `dest` on."""
    def gsv(controller: Controller, args: list) -> None:
        if len(args) != 4 or args[1] is not None:
            raise StError("GSV takes (Class,,Attribute,Destination)")
        cls, attribute = args[0], args[2]
        if not (cls[0] == "ref" and cls[1] == (("tag", "WallClockTime"),)
                and attribute[0] == "ref" and attribute[1] == (("tag", "DateTime"),)):
            raise StError("only GSV(WallClockTime,,DateTime,...) is modeled")
        values = now()
        if len(values) != 7:
            raise StError("DateTime is seven DINTs")
        for offset, value in enumerate(values):
            holder, key = controller.element(args[3], offset)
            holder[key] = value
    return gsv
