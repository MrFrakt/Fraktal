#!/usr/bin/env python3
"""Generate `<NWL>` ladder rungs for a Fraktal LD sequence from a worked example.

WHY THIS EXISTS
---------------
An LD chain body is not text: it is a serialized object graph of
`BoxTreeBox` / `BoxTreeOperand` / `BoxTreeDemux` / `BoxTreeAssign` nodes with
`Id` identities and `VarId` power-rail nodes, ~40 kB per rung. Hand-writing one
is not viable and regex-cutting nodes out of one has already produced a file
that stayed plausible while ceasing to be well-formed XML.

What IS viable, and what this module does, is *cloning a rung that already
compiles* and rewriting only its leaf operands. Every structural node, every
attribute and the exact byte layout come from the template, so the generated
rung is structurally identical to one XAE itself produced. Only three classes of
thing change:

  * `Id` / `VarId` numbers, renumbered into a fresh range so the clone cannot
    collide with the rung it came from (a duplicated Id silently shadows a node);
  * leaf operand text and type (`_pressRam` -> `_door`, `110` -> `130`, ...);
  * whole optional sub-blocks, spliced at an anchor that is matched, never
    guessed.

EVERY substitution asserts its expected hit count. A rewrite that matches
nothing is the documented failure mode here - it reports success and changes
nothing - so `subst()` raises instead of returning quietly.

VERIFICATION IS NOT OPTIONAL
----------------------------
Two gates, in order, and both are cheap:

  1. `python -m unittest test_ld_rung_gen` (from this directory) - the golden
     test regenerates
     the template rung from itself and asserts the bytes are identical. If the
     emitter drifts, that fails before any real file is touched.
  2. `FraktalCore/PLC/TwinCAT/tools/Invoke-TwinCatBuild.ps1` after EVERY rung. One rung at a time. A
     batch of twelve that fails tells you nothing about which one is wrong,
     and `ImpVar<BoxId>_<n>` in an error message maps directly to the
     `<v n="Id">…L</v>` of the offending node, which is only useful if you
     know which rung you just added.

See `FraktalCore/PLC/TwinCAT/README.md` for the rung shapes themselves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# A network is a direct <o> child of <l2 n="NetworkList" cet="Network">.
NETWORK_LIST_OPEN = '<l2 n="NetworkList"'
O_TAG = re.compile(r"<(/?)o\b[^>]*?(/?)>")
ID_VALUE = re.compile(r'(<v n="Id">)(\d+)(L</v>)')
VARID_VALUE = re.compile(r'(<v n="VarId">)(\d+)(</v>)')
BRANCH_COUNTER = re.compile(r'(<v n="BranchCounter">)(\d+)(</v>)')


class RungError(RuntimeError):
    """A substitution or splice did not match what the caller asserted."""


def split_networks(source: str) -> tuple[str, list[str], str, str]:
    """Return (prefix, [raw network blocks], separator, suffix).

    Scans bracket depth over <o> tags rather than parsing, because the archive
    carries xml:space="preserve" and an ElementTree round-trip would rewrite the
    indentation that sits inside those preserved elements.

    The separator between two networks (a newline plus the list's indent) is
    returned rather than assumed: it is real content under xml:space="preserve",
    so rejoining without it produces `</o><o>` on one line - still valid XML,
    which is precisely why it would go unnoticed.
    """
    start = source.index(NETWORK_LIST_OPEN)
    body_start = source.index(">", start) + 1
    blocks: list[tuple[int, int]] = []
    depth = 0
    opened_at = 0
    end_of_list = len(source)
    for match in O_TAG.finditer(source, body_start):
        if match.group(2):            # self-closing <o ... />
            continue
        if not match.group(1):        # opening <o>
            if depth == 0:
                opened_at = match.start()
            depth += 1
        else:                         # closing </o>
            depth -= 1
            if depth == 0:
                blocks.append((opened_at, match.end()))
            elif depth < 0:           # the </o> that closes NetworkList's parent
                end_of_list = match.start()
                break
    if not blocks:
        raise RungError("no networks found; is this an <NWL> body?")
    separators = {source[blocks[i][1]:blocks[i + 1][0]]
                  for i in range(len(blocks) - 1)}
    if len(separators) > 1:
        raise RungError(f"networks are not uniformly separated: {separators!r}")
    separator = separators.pop() if separators else "\n" + " " * 16
    prefix = source[:blocks[0][0]]
    suffix = source[blocks[-1][1]:]
    return prefix, [source[a:b] for a, b in blocks], separator, suffix


def max_identifiers(source: str) -> tuple[int, int]:
    """Highest Id and VarId anywhere in the body - the base for a fresh range."""
    ids = [int(m.group(2)) for m in ID_VALUE.finditer(source)]
    varids = [int(m.group(2)) for m in VARID_VALUE.finditer(source)]
    return (max(ids) if ids else 0, max(varids) if varids else 0)


@dataclass
class Rung:
    """One cloned network, renumbered, awaiting operand substitution."""

    text: str
    log: list[str] = field(default_factory=list)

    def subst(self, old: str, new: str, *, new_type: str | None = None,
              count: int = 1) -> "Rung":
        """Rewrite an operand's text (and optionally its type), asserting count.

        Targets the `<v n="Operand">"x"</v>` + following `<v n="Type">` pair so a
        bare identifier cannot match a longer name that contains it, and so the
        type never silently disagrees with the value (that mismatch is exactly
        what `Cannot convert type 'BOOL' to type 'E_VERDICT'` was).
        """
        pattern = re.compile(
            r'(<v n="Operand">)"' + re.escape(old) + r'"(</v>\s*<v n="Type">)"([^"]*)"')

        def replace(match: re.Match[str]) -> str:
            kept = match.group(3) if new_type is None else new_type
            return f'{match.group(1)}"{new}"{match.group(2)}"{kept}"'

        text, hits = pattern.subn(replace, self.text)
        if hits != count:
            raise RungError(
                f"operand {old!r} -> {new!r}: expected {count} replacement(s), made {hits}")
        self.text = text
        self.log.append(f"operand {old!r} -> {new!r} x{hits}")
        return self

    def subst_string(self, old: str, new: str, *, count: int = 1) -> "Rung":
        """Rewrite an IEC string literal and its STRING(INT#n) declared length.

        The archive stores `'project.step.pressRamUp'` with type
        `STRING(INT#23)` - the length of the literal WITHOUT its quotes. Deriving
        it here is what stops a renamed step from carrying the previous name's
        length.
        """
        return self.subst(f"'{old}'", f"'{new}'",
                          new_type=f"STRING(INT#{len(new)})", count=count)

    def set_input(self, box_type: str, index: int, new: str, *,
                  new_type: str | None = None, occurrence: int = 0) -> "Rung":
        """Set the operand on a box's `index`-th DIRECT input pin.

        Text substitution cannot address a rung reliably: `"0"` is the gate
        constant, the `Awaits` argument AND the `Branch` argument of one N0-shaped
        rung, so `subst("0", "230")` correctly refuses. Pins are positional and
        match `InputParam.Names` one-for-one, so addressing them by index says
        what was actually meant.

        Only direct children count. A nested box occupying pin 0 (the EN chain)
        is one child however deep it goes.
        """
        start, end = find_box(self.text, box_type, occurrence)
        box = self.text[start:end]
        items_at = box.index('<l2 n="InputItems"')
        cursor = box.index(">", items_at) + 1
        span = None
        for pin in range(index + 1):
            span = subtree(box, cursor)
            cursor = span[1]
        child = box[span[0]:span[1]]
        if "BoxTreeOperand" not in (child[:60]) and '<v n="Operand">' not in child:
            raise RungError(f"{box_type} pin {index} is not a plain operand")
        pattern = re.compile(r'(<v n="Operand">)"[^"]*"(</v>\s*<v n="Type">)"([^"]*)"')
        replaced, hits = pattern.subn(
            lambda m: f'{m.group(1)}"{new}"{m.group(2)}'
                      f'"{m.group(3) if new_type is None else new_type}"',
            child, count=1)
        if hits != 1:
            raise RungError(f"{box_type} pin {index}: no operand to set")
        box = box[:span[0]] + replaced + box[span[1]:]
        self.text = self.text[:start] + box + self.text[end:]
        self.log.append(f"{box_type}[{index}] := {new!r}")
        return self

    def splice_after(self, anchor: str, block: str, *, count: int = 1) -> "Rung":
        """Insert raw node XML immediately after a matched anchor."""
        hits = self.text.count(anchor)
        if hits != count:
            raise RungError(
                f"splice anchor {anchor[:60]!r}: expected {count} match(es), found {hits}")
        self.text = self.text.replace(anchor, anchor + block, count)
        self.log.append(f"spliced {len(block)} bytes after anchor")
        return self


def clone(template: str, *, id_base: int, var_base: int) -> tuple[Rung, int, int]:
    """Copy a network and move every Id/VarId into a fresh contiguous range.

    Returns the rung plus the next free Id and VarId, so a caller generating
    several rungs threads the allocator through and no two clones collide.
    """
    ids = sorted({int(m.group(2)) for m in ID_VALUE.finditer(template)})
    varids = sorted({int(m.group(2)) for m in VARID_VALUE.finditer(template)})
    id_map = {old: id_base + index for index, old in enumerate(ids)}
    var_map = {old: var_base + index for index, old in enumerate(varids)}

    text = ID_VALUE.sub(lambda m: f"{m.group(1)}{id_map[int(m.group(2))]}{m.group(3)}",
                        template)
    text = VARID_VALUE.sub(lambda m: f"{m.group(1)}{var_map[int(m.group(2))]}{m.group(3)}",
                           text)
    return Rung(text), id_base + len(ids), var_base + len(varids)


BOX_TYPE = re.compile(r'<v n="BoxType">"([^"]+)"</v>')


def iter_boxes(text: str):
    """Yield (start, end, box_type) for every BoxTreeBox, outermost-first.

    A box's extent is found by <o> depth from the `<o …>` that opens it, so a
    nested box (an AND feeding a method's EN, say) is returned in its own right
    and never confused with its parent.
    """
    for match in BOX_TYPE.finditer(text):
        start = text.rindex("<o", 0, match.start())
        depth = 0
        for tag in O_TAG.finditer(text, start):
            if tag.group(2):
                continue
            depth += 1 if not tag.group(1) else -1
            if depth == 0:
                yield start, tag.end(), match.group(1)
                break


def _indent_of(text: str, index: int) -> str:
    line_start = text.rindex("\n", 0, index) + 1
    return text[line_start:index]


def to_en_form(box: str, *, base_name: str, returns_value: bool,
               eno_operand_id: int) -> str:
    """Rewrite one `…Ld` box (a `Run : BOOL` facade call) into an EN/ENO call.

    `FB_SequenceBaseLd`'s facades were reinventing the EN pin XAE gives every
    method box, and a facade cannot scale: a project may define or extend module
    types freely and no library can ship an `…Ld` twin per method per type. The
    EN form calls the real method, so ANY FB's methods are rung-callable.

    The five differences, all of them mechanical:

      BoxType        "M_StepLd"        -> "M_Step"
      InputParam[0]  Run               -> EN
      OutputParam    (empty)           -> ENO : BOOL
                     M_AwaitLd : BOOL  -> ENO : BOOL, M_Await : BOOL
      OutputItems    (empty)           -> <n /> placeholder
                     one operand       -> an empty "" ENO slot, THEN that operand
      EN / ENO       false             -> true

    The ENO slot is why a converted value-returning box has TWO outputs with the
    return value SECOND. Wiring a variable into slot 0 puts it on ENO and strands
    the intended one - it compiles clean, so nothing catches it but a review.
    """
    if '<v n="EN">true</v>' in box:
        return box                                     # already converted

    text = BOX_TYPE.sub(lambda m: f'<v n="BoxType">"{base_name}"</v>', box, count=1)

    # InputParam's first name is the power pin.
    text, hits = re.subn(r"(<l2 n=\"Names\" cet=\"String\">\s*<v>)Run(</v>)",
                         r"\1EN\2", text, count=1)
    if hits != 1:
        raise RungError(f"{base_name}: no Run input to rename")

    marker = '<o n="OutputParam" t="ParamList">'
    out_at = text.rindex(marker)
    head, tail = text[:out_at], text[out_at:]
    indent = _indent_of(text, out_at)
    inner, deeper = indent + "  ", indent + "    "

    if returns_value:
        # Prepend ENO to both parameter lists, keeping the return value second.
        tail, hits = re.subn(r"(<l2 n=\"Names\" cet=\"String\">\s*)(<v>)",
                             r"\1<v>ENO</v>\n" + deeper + r"\2", tail, count=1)
        if hits != 1:
            raise RungError(f"{base_name}: could not add the ENO output name")
        tail = re.sub(r"(<v>)" + re.escape(f"{base_name}Ld") + r"(</v>)",
                      rf"\1{base_name}\2", tail, count=1)
        tail, hits = re.subn(r"(<l2 n=\"Types\" cet=\"String\">\s*)(<v>)",
                             r"\1<v>BOOL</v>\n" + deeper + r"\2", tail, count=1)
        if hits != 1:
            raise RungError(f"{base_name}: could not add the ENO output type")
    else:
        tail, hits = re.subn(
            r'<l2 n="Names" />\s*<l2 n="Types" />',
            f'<l2 n="Names" cet="String">\n{deeper}<v>ENO</v>\n{inner}</l2>\n'
            f'{inner}<l2 n="Types" cet="String">\n{deeper}<v>BOOL</v>\n{inner}</l2>',
            tail, count=1)
        if hits != 1:
            raise RungError(f"{base_name}: could not add the ENO output param")
    text = head + tail

    # OutputItems must gain a slot for ENO.
    if returns_value:
        eno_slot = (
            f'<o>\n{deeper}<v n="Operand">""</v>\n'
            f'{deeper}<v n="Type">"BOOL"</v>\n'
            f'{deeper}<v n="Comment">""</v>\n'
            f'{deeper}<v n="SymbolComment">""</v>\n'
            f'{deeper}<v n="Address">""</v>\n'
            f'{deeper}<o n="Flags" t="Flags">\n'
            f'{deeper}  <v n="Flags">0</v>\n'
            f'{deeper}  <v n="Fixed">false</v>\n'
            f'{deeper}  <v n="Extensible">false</v>\n'
            f'{deeper}</o>\n'
            f'{deeper}<v n="LValue">true</v>\n'
            f'{deeper}<v n="Boolean">false</v>\n'
            f'{deeper}<v n="IsInstance">false</v>\n'
            f'{deeper}<v n="Id">{eno_operand_id}L</v>\n'
            f'{inner}</o>\n{inner}')
        text, hits = re.subn(r'(<l2 n="OutputItems" cet="Operand">\s*)(<o>)',
                             lambda m: m.group(1) + eno_slot + m.group(2),
                             text, count=1)
    else:
        text, hits = re.subn(
            r'<l2 n="OutputItems" />',
            f'<l2 n="OutputItems">\n{deeper}<n />\n{inner}</l2>', text, count=1)
    if hits != 1:
        raise RungError(f"{base_name}: could not add the ENO output slot")

    text = text.replace('<v n="EN">false</v>', '<v n="EN">true</v>', 1)
    text = text.replace('<v n="ENO">false</v>', '<v n="ENO">true</v>', 1)
    return text


def convert_ld_boxes(source: str, *, id_base: int) -> tuple[str, int, list[str]]:
    """Convert every `…Ld` facade box in a body to its EN/ENO base-method call."""
    converted: list[str] = []
    next_id = id_base
    while True:
        target = None
        for start, end, box_type in iter_boxes(source):
            if box_type.endswith("Ld"):
                target = (start, end, box_type)
                break
        if target is None:
            return source, next_id, converted
        start, end, box_type = target
        box = source[start:end]
        base_name = box_type[:-2]
        returns_value = f"<v>{box_type}</v>" in box
        new_box = to_en_form(box, base_name=base_name, returns_value=returns_value,
                             eno_operand_id=next_id)
        next_id += 1
        source = source[:start] + new_box + source[end:]
        converted.append(f"{box_type} -> {base_name}"
                         f"{' (value)' if returns_value else ''}")


def subtree(text: str, start: int) -> tuple[int, int]:
    """Span of the `<o …>` element beginning at or after `start`."""
    open_at = text.index("<o", start)
    depth = 0
    for tag in O_TAG.finditer(text, open_at):
        if tag.group(2):
            continue
        depth += 1 if not tag.group(1) else -1
        if depth == 0:
            return open_at, tag.end()
    raise RungError("unterminated <o> element")


def find_box(text: str, box_type: str, occurrence: int = 0) -> tuple[int, int]:
    matches = [(a, b) for a, b, t in iter_boxes(text) if t == box_type]
    if len(matches) <= occurrence:
        raise RungError(
            f"box {box_type!r} #{occurrence} not found (have {len(matches)})")
    return matches[occurrence]


def _en_slot(box: str) -> tuple[int, int]:
    """Span of a box's FIRST InputItems child - its EN/power source."""
    items = box.index('<l2 n="InputItems"')
    if box[items:items + 40].rstrip().endswith("/>"):
        raise RungError("box has no InputItems children to graft onto")
    return subtree(box, box.index(">", items) + 1)


def graft_before(rung: str, host_type: str, donor: str, *, id_base: int,
                 var_base: int, occurrence: int = 0) -> tuple[str, int, int]:
    """Insert `donor` into `rung`'s power chain so it runs BEFORE `host_type`.

    Power flow in the EN form is nesting, not sibling order:

        MOVE(EN := M_Step(EN := EQ(…)))

    so adding a box means re-parenting, not appending. The donor takes over the
    host's EN slot and the slot's previous occupant becomes the donor's own EN
    source, which is exactly `host(EN := donor(EN := previous))`.

    The donor is renumbered into a fresh Id/VarId range first: it is normally
    cloned out of another network, where its Ids are already in use.
    """
    donor_rung, next_id, next_var = clone(donor, id_base=id_base, var_base=var_base)
    donor_text = donor_rung.text

    # A node lifted out of a `<l2 … cet="BoxTreeBox">` list carries NO t= of its
    # own: the list typed it collectively. Dropped into a list without a cet it
    # becomes an untyped `<o>`, which still parses and still COMPILES - the box
    # is simply not there. Restore the type explicitly.
    stripped = donor_text.lstrip()
    if stripped.startswith("<o>"):
        donor_text = donor_text.replace("<o>", '<o t="BoxTreeBox">', 1)
    elif not re.match(r'<o\s+t="', stripped):
        raise RungError("donor node has no recognisable element type")

    host_start, host_end = find_box(rung, host_type, occurrence)
    host = rung[host_start:host_end]
    slot_start, slot_end = _en_slot(host)
    previous = host[slot_start:slot_end]

    # Give the donor the host's old EN source.
    donor_slot_start, donor_slot_end = _en_slot(donor_text)
    donor_text = (donor_text[:donor_slot_start] + previous
                  + donor_text[donor_slot_end:])

    host = host[:slot_start] + donor_text + host[slot_end:]
    return rung[:host_start] + host + rung[host_end:], next_id, next_var


# ---------------------------------------------------------------------------
# Synthesis - declare a node instead of finding a donor to clone
# ---------------------------------------------------------------------------
#
# Cloning has one hard limit: it can only produce box types that already exist
# somewhere in the file. Every rung needing `M_Delay`, `M_AskDecision`, a
# child's `WithdrawOutputs` - anything with no instance to copy - stalled on
# "draw one in XAE first".
#
# It does not have to. A `BoxTreeBox` is fully determined by the DECLARATION of
# the method it calls: `InputParam.Names` is `EN` followed by the `VAR_INPUT`
# names, `Types` is `BOOL` followed by their types, and `OutputParam` is `ENO`
# plus - only for a value-returning method - the method's own name and return
# type. Nothing in it is copied from anywhere. The same is true of the operator
# boxes, the power rails and the coils, so a whole rung can be written down.
#
# The one thing synthesis must never do is emit an untyped `<o>`. A node lifted
# out of a `<l2 … cet="BoxTreeBox">` list loses the type the list gave it
# collectively, and an untyped `<o>` parses AND compiles while the box is simply
# absent. Every node here carries its own `t=`, and `network()` writes
# `<l2 n="NetworkItems">` with no `cet` so it stays that way. Dump the result
# (`ld_dump.py`) - that is the check, not the compiler.

PLAIN, SET, RESET = 0, 2, 3          # BoxTreeAssign coil flags


class Allocator:
    """Hands out `Id` and `VarId` numbers above everything a body already uses.

    A duplicated `Id` does not fail to parse - it silently shadows a node - so
    every synthesised node draws from one allocator, and `Allocator.above()`
    starts it past the highest number in the file being edited.
    """

    def __init__(self, next_id: int, next_var: int) -> None:
        self.next_id = next_id
        self.next_var = next_var

    @classmethod
    def above(cls, source: str) -> "Allocator":
        highest_id, highest_var = max_identifiers(source)
        return cls(highest_id + 1, highest_var + 1)

    def take_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1

    def take_var(self) -> int:
        self.next_var += 1
        return self.next_var - 1


def _flags(indent: str, flags: int = 0, fixed: bool = False) -> str:
    return (f'{indent}<o n="Flags" t="Flags">\n'
            f'{indent}  <v n="Flags">{flags}</v>\n'
            f'{indent}  <v n="Fixed">{str(fixed).lower()}</v>\n'
            f'{indent}  <v n="Extensible">false</v>\n'
            f'{indent}</o>\n')


def _operand(alloc: Allocator, indent: str, operand: str | None, type_name: str,
             *, flags: int = 0, fixed: bool = False, lvalue: bool = False,
             boolean: bool = False, instance: bool = False,
             element: str = "<o>") -> str:
    """The `Operand` record every operand, coil and output slot is made of."""
    head = (f'{indent}  <v n="Operand">"{operand}"</v>\n' if operand is not None
            else f'{indent}  <n n="Operand" />\n')
    return (f'{indent}{element}\n'
            f'{head}'
            f'{indent}  <v n="Type">"{type_name}"</v>\n'
            f'{indent}  <v n="Comment">""</v>\n'
            f'{indent}  <v n="SymbolComment">""</v>\n'
            f'{indent}  <v n="Address">""</v>\n'
            + _flags(indent + "  ", flags, fixed) +
            f'{indent}  <v n="LValue">{str(lvalue).lower()}</v>\n'
            f'{indent}  <v n="Boolean">{str(boolean).lower()}</v>\n'
            f'{indent}  <v n="IsInstance">{str(instance).lower()}</v>\n'
            f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
            f'{indent}</o>\n')


class Node:
    """One serialized `<o>` of an `<NWL>` network."""

    ELEMENT = ""

    def render(self, alloc: Allocator, indent: str = "",
               name: str | None = None) -> str:
        raise NotImplementedError

    def _open(self, name: str | None) -> str:
        attribute = ' n="%s"' % name if name else ""
        return '<o%s t="%s">' % (attribute, self.ELEMENT)


@dataclass
class Term(Node):
    """The left power rail - what a gate hangs from when nothing precedes it."""

    ELEMENT = "BoxTreeTerminator"

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                f'{indent}  <n n="Input" />\n'
                + _flags(indent + "  ") +
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Contact(Node):
    """A BOOL read as power flow: `--| |--`, or `--|/|--` when negated.

    Distinct from `Value` on purpose. Both are `BoxTreeOperand`s, but XAE marks
    a contact `Boolean`/`Fixed` and a plain BOOL *argument* (`Steppable := TRUE`)
    not - so the type alone cannot tell them apart, and in ladder they are not
    the same thing anyway.
    """

    ELEMENT = "BoxTreeOperand"
    operand: str
    negated: bool = False

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                + _operand(alloc, indent + "  ", self.operand, "BOOL",
                           flags=1 if self.negated else 0, fixed=True,
                           boolean=True, element='<o n="Operand" t="Operand">') +
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Value(Node):
    """An argument operand - a literal, an enum member, an FB instance, an expr."""

    ELEMENT = "BoxTreeOperand"
    operand: str
    type_name: str

    @classmethod
    def text(cls, literal: str) -> "Value":
        """An IEC string literal, with the `STRING(INT#n)` its own length implies.

        The declared form (`STRING(120)`) belongs in a parameter list; an operand
        carries the literal's length. Mixing them is a silent type mismatch.
        """
        return cls(f"'{literal}'", f"STRING(INT#{len(literal)})")

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                + _operand(alloc, indent + "  ", self.operand, self.type_name,
                           element='<o n="Operand" t="Operand">') +
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Rail(Node):
    """A tap on a power node defined elsewhere in the same network."""

    ELEMENT = "BoxTreeDemux"
    var_id: int

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                f'{indent}  <v n="VarId">{self.var_id}</v>\n'
                f'{indent}  <n n="Input" />\n'
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Wire(Node):
    """Defines the power node `var_id`, driven by `source`.

    This is how a rung branches: define the wire once, then hang any number of
    `Rail(var_id)` taps off it. Power flow in the nested EN form is *nesting*,
    so without a wire a rung can only be a single chain.
    """

    ELEMENT = "BoxTreeDemux"
    var_id: int
    source: Node

    def tap(self) -> Rail:
        return Rail(self.var_id)

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                f'{indent}  <v n="VarId">{self.var_id}</v>\n'
                + self.source.render(alloc, indent + "  ", "Input") +
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Coil(Node):
    """`(S)`, `(R)` or a plain coil: `kind` is `SET`, `RESET` or `PLAIN`.

    A plain coil writes the rail's value, so `x := FALSE` inside a step that is
    active is a RESET coil, never a plain one driven from the step's own rail -
    that would write TRUE.
    """

    ELEMENT = "BoxTreeAssign"
    operand: str
    source: Node
    kind: int = PLAIN

    def render(self, alloc, indent="", name=None):
        return (f'{indent}{self._open(name)}\n'
                f'{indent}  <o n="OutputItems" t="OutputItemList">\n'
                f'{indent}    <l2 n="OutputItems" cet="Operand">\n'
                + _operand(alloc, indent + "      ", self.operand, "BOOL",
                           flags=self.kind, fixed=True, lvalue=True,
                           boolean=True) +
                f'{indent}    </l2>\n'
                f'{indent}  </o>\n'
                + _flags(indent + "  ")
                + self.source.render(alloc, indent + "  ", "RValue") +
                f'{indent}  <v n="Id">{alloc.take_id()}L</v>\n'
                f'{indent}</o>\n')


@dataclass
class Box(Node):
    """A `BoxTreeBox`. Use `method`/`compare`/`move`/`logic` rather than this."""

    ELEMENT = "BoxTreeBox"
    box_type: str
    call_type: str
    inputs: list[Node]
    param_names: list[str]
    param_types: list[str]
    output_names: list[str]
    output_types: list[str]
    outputs: list[tuple[str, str] | None]
    en: bool | None = True
    eno: bool | None = True
    instance: str | None = ""      # None -> `<n n="Operand" />`, as operators use
    fixed: bool = True

    def _param_list(self, indent: str, name: str, names: list[str],
                    types: list[str]) -> str:
        if not names:
            return (f'{indent}<o n="{name}" t="ParamList">\n'
                    f'{indent}  <l2 n="Names" />\n'
                    f'{indent}  <l2 n="Types" />\n'
                    f'{indent}</o>\n')
        rows = lambda items: "".join(  # noqa: E731
            f'{indent}    <v>{item}</v>\n' for item in items)
        return (f'{indent}<o n="{name}" t="ParamList">\n'
                f'{indent}  <l2 n="Names" cet="String">\n{rows(names)}'
                f'{indent}  </l2>\n'
                f'{indent}  <l2 n="Types" cet="String">\n{rows(types)}'
                f'{indent}  </l2>\n'
                f'{indent}</o>\n')

    def _output_items(self, alloc: Allocator, indent: str) -> str:
        if not self.outputs:
            body = f'{indent}  <l2 n="OutputItems" />\n'
        elif all(slot is None for slot in self.outputs):
            body = (f'{indent}  <l2 n="OutputItems">\n'
                    f'{indent}    <n />\n'
                    f'{indent}  </l2>\n')
        else:
            slots = "".join(
                f'{indent}    <n />\n' if slot is None else
                _operand(alloc, indent + "    ", slot[0], slot[1], lvalue=True)
                for slot in self.outputs)
            body = (f'{indent}  <l2 n="OutputItems" cet="Operand">\n{slots}'
                    f'{indent}  </l2>\n')
        return (f'{indent}<o n="OutputItems" t="OutputItemList">\n{body}'
                f'{indent}</o>\n')

    def render(self, alloc, indent="", name=None):
        inner = indent + "  "
        pin = "".join(node.render(alloc, inner + "  ") for node in self.inputs)
        flag = lambda value, tag: (  # noqa: E731
            f'{inner}<n n="{tag}" />\n' if value is None else
            f'{inner}<v n="{tag}">{str(value).lower()}</v>\n')
        return (
            f'{indent}{self._open(name)}\n'
            f'{inner}<v n="BoxType">"{self.box_type}"</v>\n'
            + _operand(alloc, inner, self.instance, "", instance=True,
                       element='<o n="Instance" t="Operand">')
            + self._output_items(alloc, inner)
            + _flags(inner, 0, self.fixed) +
            f'{inner}<n n="InputFlags" />\n'
            f'{inner}<l2 n="InputItems">\n{pin}{inner}</l2>\n'
            + self._param_list(inner, "InputParam", self.param_names,
                               self.param_types)
            + self._param_list(inner, "OutputParam", self.output_names,
                               self.output_types) +
            f'{inner}<v n="CallType" t="Operator">{self.call_type}</v>\n'
            + flag(self.en, "EN") + flag(self.eno, "ENO") +
            f'{inner}<n n="STSnippet" />\n'
            f'{inner}<v n="ContainsExtensibleInputs">false</v>\n'
            f'{inner}<v n="ProvidesSTSnippet">false</v>\n'
            f'{inner}<v n="Id">{alloc.take_id()}L</v>\n'
            f'{indent}</o>\n')


def method(box_type: str, en: Node, args: list[tuple[str, str, Node]] = (),
           *, returns: tuple[str, str] | None = None,
           result: str | None = None) -> Box:
    """A method call, derived entirely from the method's declaration.

    `args` are `(VAR_INPUT name, type, node)` in declaration order; `returns` is
    `(method name, return type)` for a value-returning method and `result` the
    variable its value lands in.

    An `EN`-gated value-returning box has TWO outputs and the return is the
    SECOND: `ENO` always takes slot 0. Wiring a variable into slot 0 puts it on
    `ENO`, compiles clean, and strands the one you meant - that defect already
    left `_partReady` unwritten and a chain unable to leave step 100. Passing
    `result` here is what makes that unrepresentable.

    Another FB's method folds the instance into the box type:
    `method("_pressRam.WithdrawOutputs", …)`.
    """
    names = ["EN"] + [name for name, _, _ in args]
    types = ["BOOL"] + [type_name for _, type_name, _ in args]
    inputs = [en] + [node for _, _, node in args]
    if returns is None:
        if result is not None:
            raise RungError(f"{box_type}: a void method has no value to land in "
                            f"{result!r}")
        return Box(box_type, "Method", inputs, names, types, ["ENO"], ["BOOL"],
                   [None])
    return_name, return_type = returns
    return Box(box_type, "Method", inputs, names, types,
               ["ENO", return_name], ["BOOL", return_type],
               [("", "BOOL"), (result or "", return_type)])


def call(fb_type: str, instance: str, en: Node,
         args: list[tuple[str, str, Node]] = ()) -> Box:
    """Call an FB INSTANCE from a rung: `ModeStart();`.

    Different from `method()` in exactly one way - the box names the FB TYPE and
    carries the INSTANCE in its `Instance` operand, where a method box names the
    method and leaves the instance empty (or folds it into the box type for
    another FB's method).

    Inputs left unwired keep whatever the instance already holds, which is what
    a bare `ModeStart();` after `ModeStart.Cond[1] := …` means. Pass `args` only
    for inputs the rung actually drives.
    """
    names = ["EN"] + [name for name, _, _ in args]
    types = ["BOOL"] + [type_name for _, type_name, _ in args]
    return Box(fb_type, "FunctionBlock", [en] + [node for _, _, node in args],
               names, types, ["ENO"], ["BOOL"], [None], instance=instance)


def compare(operator: str, en: Node, left: Node, right: Node) -> Box:
    """`EQ(left, right)` and friends: the gate. Its output IS the power flow.

    It has one unnamed BOOL output rather than an `ENO`, which is why a rung
    reads `M_Step(EN := EQ(_step, 215))`.
    """
    return Box(operator, operator.capitalize(), [en, left, right], ["EN"],
               ["BOOL"], [""], ["BOOL"], [None], eno=False, instance=None,
               fixed=False)


def move(en: Node, value: Node, target: str, target_type: str) -> Box:
    """`MOVE` - how a rung writes the next state into `_step`, and any other value."""
    return Box("MOVE", "Move", [en, value], ["EN"], ["BOOL"], ["ENO", ""],
               ["BOOL", ""], [None, (target, target_type)], instance=None,
               fixed=False)


def logic(operator: str, inputs: list[Node]) -> Box:
    """`AND` / `OR` of contacts and rails - series and parallel, in one box."""
    return Box(operator, operator.capitalize(), list(inputs), [], [], [], [], [],
               en=None, eno=None, instance=None, fixed=False)


NETWORK_INDENT = " " * 16


def network(items: list[Node], alloc: Allocator, *, comment: str = "",
            indent: str = NETWORK_INDENT) -> str:
    """One complete `<o>` network, ready to hand to `rebuild()`.

    `NetworkItems` is written WITHOUT a `cet`, so every item states its own
    type. A list that types its children collectively is how a node loses its
    type in the first place.
    """
    if '"' in comment:
        raise RungError("a network comment is stored quoted; it cannot contain "
                        'a " character')
    inner = indent + "  "
    body = "".join(item.render(alloc, inner + "  ") for item in items)
    escaped = comment.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # No leading indent: `split_networks` hands back blocks that begin at `<o`,
    # and the separator it preserves is what puts each one in column `indent`.
    return ('<o>\n'
            f'{inner}<v n="ILActive">false</v>\n'
            f'{inner}<v n="FBDValid">false</v>\n'
            f'{inner}<v n="ILValid">false</v>\n'
            f'{inner}<l2 n="ILLines" />\n'
            f'{inner}<v n="Comment">"{escaped}"</v>\n'
            f'{inner}<v n="Title">""</v>\n'
            f'{inner}<v n="Label">""</v>\n'
            f'{inner}<v n="OutCommented">false</v>\n'
            f'{inner}<l2 n="NetworkItems">\n{body}{inner}</l2>\n'
            f'{inner}<l2 n="Connectors" />\n'
            f'{inner}<v n="Id">{alloc.take_id()}L</v>\n'
            f'{indent}</o>')


ARCHIVE_TYPES = [
    ("Boolean", "System.Boolean"),
    ("BoxTreeAssign", "{9873c309-1f09-4ebf-9078-42d8057ef11b}"),
    ("BoxTreeBox", "{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"),
    ("BoxTreeDemux", "{b1d55618-017c-4bc5-990a-55c2f27d9d3a}"),
    ("BoxTreeOperand", "{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"),
    ("BoxTreeTerminator", "{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}"),
    ("Flags", "{668066f2-6069-46b3-8962-8db8d13d7db2}"),
    ("Int32", "System.Int32"),
    ("Int64", "System.Int64"),
    ("Network", "{d9a99d73-b633-47db-b876-a752acb25871}"),
    ("NWLImplementationObject", "{25e509de-33d4-4447-93f8-c9e4ea381c8b}"),
    ("Operand", "{c9b2f165-48a2-4a45-8326-3952d8a3d708}"),
    ("Operator", "{bffb3c53-f105-4e85-aba2-e30df579d75f}"),
    ("OutputItemList", "{f40d3e09-c02c-4522-a88c-dac23558cfc4}"),
    ("ParamList", "{71496971-9e0c-4677-a832-b9583b571130}"),
    ("String", "System.String"),
]


def body(networks: list[str], *, indent: str = "    ") -> str:
    """A complete `<Implementation><NWL>…</NWL></Implementation>` block.

    `rebuild()` edits a body that already exists; this makes one, which is what
    a NEW ladder POU or a ladder METHOD needs. `indent` is the column of
    `<Implementation>` - four spaces for a POU body, six for a method's - and the
    networks must have been rendered at `indent + 10` to line up.

    `xml:space="preserve"` and the `TypeList` are not decoration: the archive
    will not load without the type table, and the GUIDs are XAE's, not ours.
    """
    inner = indent + " " * 10
    separator = "\n" + inner + "  "
    _, highest_var = max_identifiers("".join(networks))
    types = "".join(f'{indent}    <Type n="{name}">{value}</Type>\n'
                    for name, value in ARCHIVE_TYPES)
    return (f'{indent}<Implementation>\n'
            f'{indent}  <NWL>\n'
            f'{indent}    <XmlArchive>\n'
            f'{indent}      <Data>\n'
            f'{indent}        <o xml:space="preserve" t="NWLImplementationObject">\n'
            f'{inner}<v n="NetworkListComment">""</v>\n'
            f'{inner}<v n="DefaultViewMode">"Ld"</v>\n'
            f'{inner}<l2 n="NetworkList" cet="Network">\n'
            f'{inner}  ' + separator.join(networks) + '\n'
            f'{inner}</l2>\n'
            f'{inner}<v n="BranchCounter">{highest_var + 1}</v>\n'
            f'{inner}<v n="ValidIds">true</v>\n'
            f'{indent}        </o>\n'
            f'{indent}      </Data>\n'
            f'{indent}      <TypeList>\n{types}'
            f'{indent}      </TypeList>\n'
            f'{indent}    </XmlArchive>\n'
            f'{indent}  </NWL>\n'
            f'{indent}</Implementation>')


def rebuild(source: str, networks: list[str]) -> str:
    """Reassemble the body from a new network list, fixing BranchCounter.

    BranchCounter is the archive's monotonic VarId allocator. Leaving it below a
    VarId that now exists lets XAE hand out a duplicate power-rail id the next
    time someone edits the chart in the editor.
    """
    prefix, _, separator, suffix = split_networks(source)
    rebuilt = prefix + separator.join(networks) + suffix
    _, highest_var = max_identifiers(rebuilt)
    rebuilt, hits = BRANCH_COUNTER.subn(
        lambda m: f"{m.group(1)}{highest_var + 1}{m.group(3)}", rebuilt)
    if hits != 1:
        raise RungError(f"expected exactly one BranchCounter, found {hits}")
    return rebuilt
