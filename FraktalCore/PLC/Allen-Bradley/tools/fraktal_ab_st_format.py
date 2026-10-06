"""Token-preserving layout for the Structured Text emitted by Fraktal/AB.

This is a presentation pass, not an optimizer or a Logix syntax validator.
Keep literals, operand names and token order intact. Refuse malformed block
structure instead of publishing plausibly indented, silently changed code.
"""
from dataclasses import dataclass
import re


class FormatError(ValueError):
    pass


_TOKEN = re.compile(r"""
    (?P<comment>\(\*.*?\*\))
  | (?P<ws>\s+)
  | (?P<string>'(?:\$.|''|[^'])*')
  | (?P<number>(?:2|8|16)\#[0-9A-Fa-f_]+|\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)
  | (?P<name>[A-Za-z_]\w*(?::\w+)*)
  | (?P<op>:=|<>|<=|>=|\.\.|[=<>+\-*/()\[\].,;:])
""", re.VERBOSE | re.DOTALL)


def tokens(text, *, comments=False):
    """Exact executable tokens, also used to prove layout is non-mutating."""
    result, position = [], 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise FormatError(f'unrecognized ST near {text[position:position + 40]!r}')
        position = match.end()
        kind, value = match.lastgroup, match.group()
        if kind != 'ws' and (comments or kind != 'comment'):
            result.append((kind, value))
    return result


@dataclass
class _Block:
    kind: str
    indent: int
    has_label: bool = False


_PREFIX = {'IF', 'ELSIF', 'THEN', 'CASE', 'FOR', 'TO', 'BY', 'DO', 'OF',
           'AND', 'OR', 'XOR', 'NOT', 'MOD'}
_BINARY = {':=', '=', '<>', '<', '>', '<=', '>=', '+', '-', '*', '/', '..'}


def _pieces(items):
    pieces, previous, unary = [], '', False
    for kind, value in items:
        no_space = (not previous or value in {'.', ',', ';', ':', ')', ']'}
                    or previous in {'.', '(', '['} or unary
                    or value == '['
                    or (value == '(' and previous not in _PREFIX | _BINARY
                        and re.match(r'[A-Za-z_]', previous)))
        pieces.append(('' if no_space else ' ') + value)
        unary = value in {'-', '+'} and (not previous or previous in _PREFIX | _BINARY | {'(', '[', ','})
        previous = value
    return pieces


def _wrap(items, indent, width):
    """Wrap at arguments/logical operators, never inside an operand/literal."""
    pieces = _pieces(items)
    result, start = [], 0
    while start < len(pieces):
        prefix = '    ' * (indent + int(start > 0))
        stop, boundary, used = start, None, len(prefix)
        while stop < len(pieces):
            if stop > start and (items[stop - 1][1] == ',' or items[stop][1] in {'AND', 'OR', 'XOR'}):
                boundary = stop
            used += len(pieces[stop].lstrip() if stop == start else pieces[stop])
            if used > width and boundary is not None:
                stop = boundary
                break
            stop += 1
        result.append(prefix + ''.join(pieces[start:stop]).lstrip())
        start = stop
    return result


def format_lines(logic, *, width=120):
    source = logic if isinstance(logic, str) else '\n'.join(logic)
    items = tokens(source, comments=True)
    output, pending, blocks = [], [], []
    indent, brackets = 0, []
    branch = False

    def flush():
        if pending:
            output.extend(_wrap(pending, indent, width))
            pending.clear()

    def current(kind=None):
        if not blocks or (kind is not None and blocks[-1].kind != kind):
            raise FormatError(f'unmatched {kind or "branch"} block')
        return blocks[-1]

    for kind, value in items:
        if kind == 'comment':
            # A comment inside an expression cannot split its header.
            # Standalone wrapped comments align their text with the opener.
            if pending:
                pending.append((kind, value))
            else:
                lines = value.split('\n')
                output.append('    ' * indent + lines[0])
                output.extend(('    ' * indent + '   ' + line.strip()).rstrip()
                              if line.strip() else '' for line in lines[1:])
            continue
        if kind == 'name' and value in {'END_IF', 'END_FOR', 'END_CASE'}:
            flush()
            block = current({'END_IF': 'IF', 'END_FOR': 'FOR', 'END_CASE': 'CASE'}[value])
            blocks.pop()
            indent = block.indent
        elif kind == 'name' and value in {'ELSE', 'ELSIF'}:
            flush()
            block = current()
            if block.kind not in {'IF', 'CASE'} or (value == 'ELSIF' and block.kind != 'IF'):
                raise FormatError('branch outside IF/CASE')
            indent = block.indent + int(block.kind == 'CASE')
            if value == 'ELSE':
                pending.append((kind, value))
                flush()
                indent += 1
                continue
            branch = True
        pending.append((kind, value))
        if kind == 'op' and value in {'(', '['}:
            brackets.append(value)
        elif kind == 'op' and value in {')', ']'}:
            if not brackets or brackets.pop() != {')': '(', ']': '['}[value]:
                raise FormatError('unbalanced ST expression')
        if kind == 'name' and value in {'THEN', 'DO', 'OF'} and not brackets:
            expected = {'THEN': 'IF', 'DO': 'FOR', 'OF': 'CASE'}[value]
            if not pending or pending[0][1] != ('ELSIF' if branch else expected):
                raise FormatError(f'bad {value} header')
            flush()
            if not branch:
                blocks.append(_Block(expected, indent))
            branch = False
            indent += 1
        elif kind == 'op' and value == ':' and not brackets:
            block = current('CASE')
            indent = block.indent + 1
            if block.has_label:
                output.append('')
            flush()
            block.has_label = True
            indent += 1
        elif kind == 'op' and value == ';' and not brackets:
            flush()
    flush()
    if blocks or brackets:
        raise FormatError('unterminated ST block/expression')
    # SFC transition expressions intentionally have no terminating semicolon.
    if tokens(source) != tokens('\n'.join(output)):
        raise FormatError('layout changed executable ST tokens')
    return tuple(output)
