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

  1. `python -m unittest tools.test_ld_rung_gen` - the golden test regenerates
     the template rung from itself and asserts the bytes are identical. If the
     emitter drifts, that fails before any real file is touched.
  2. `tools/Invoke-TwinCatBuild.ps1` after EVERY rung. One rung at a time. A
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
    if re.match(r"<o>\s", donor_text):
        donor_text = donor_text.replace("<o>", '<o t="BoxTreeBox">', 1)
    elif not re.match(r'<o\s+t="', donor_text):
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
