"""Offline gate: no BOOL operand in an arithmetic or comparison expression of emitted ST.

Studio v38 refuses `Flag <> (Count <> 0)` or `Flag + 1` with
RxSTX_E_BOOLOPND_UNEXPECTED, naming no routine or line, while the executed-ST
model accepts it because Python's bool is an int. A BOOL is legal as an
assignment target, a condition, and an AND/OR/XOR/NOT operand; its inequality
is XOR. This resolves each dotted operand through the image's own tags, data
types and AOI parameters and locals, and reports a BOOL found beside
+ - * / MOD = <> < > <= >=. A bit of an integer (`Word.3`) is a BOOL too.

Validated on the accepted V6.10 owner image (0 of 14,109 lines) and on the
V6.11 image v38 refused (exactly the refused line), 2026-11-04.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

KEYWORDS = {'AND', 'OR', 'XOR', 'NOT', 'IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF', 'MOD', 'TRUE', 'FALSE', 'FOR',
            'TO', 'DO', 'BY', 'END_FOR', 'WHILE', 'END_WHILE', 'CASE', 'OF', 'END_CASE', 'RETURN', 'EXIT',
            'REPEAT', 'UNTIL', 'END_REPEAT'}
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_:]*(?:\[[^\]]*\])?(?:\.[A-Za-z0-9_]+(?:\[[^\]]*\])?)*')
OPERATOR = r'(\+|-|\*|/|\bMOD\b|=|<>|<=|>=|<|>)'


def _types(root):
    types = {dt.get('Name'): {m.get('Name'): m.get('DataType') for m in dt.iter('Member')}
             for dt in root.iter('DataType')}
    for aoi in root.iter('AddOnInstructionDefinition'):
        types[aoi.get('Name')] = {**{p.get('Name'): p.get('DataType') for p in aoi.iter('Parameter')},
                                  **{t.get('Name'): t.get('DataType') for t in aoi.iter('LocalTag')}}
    return types


def resolve(path, scope, types):
    """The declared type of a dotted operand, or None when it is not resolvable."""
    parts = re.sub(r'\[[^\]]*\]', '', path).split('.')
    kind = scope.get(parts[0])
    for part in parts[1:]:
        if kind is None:
            return None
        if part.isdigit():
            return 'BOOL'
        kind = types.get(kind, {}).get(part)
    return kind


def bool_operands(line, scope, types):
    """The BOOL operands a line uses next to an arithmetic or comparison operator."""
    code = re.sub(r"'[^']*'", "''", re.sub(r'//.*$|\(\*.*?\*\)', '', line))
    found = []
    for match in NAME.finditer(code):
        name = match.group(0)
        if name.upper() in KEYWORDS or resolve(name, scope, types) != 'BOOL':
            continue
        before, after = code[:match.start()], code[match.end():]
        if re.match(r'\s*:=', after):
            continue  # an assignment target
        # The `=` of an assignment `:=` is no comparison.
        if ((re.search(OPERATOR + r'\s*$', before) and not before.rstrip().endswith(':='))
                or re.match(r'\s*' + OPERATOR, after)):
            found.append(name)
    return found


def statements(lines):
    """Join formatter-split continuation lines, so an operator and its operand meet."""
    text = '\n'.join(lines)
    return [s for s in re.split(r';|\bTHEN\b|\bELSE\b|\bDO\b|\bOF\b', text) if s.strip()]


def findings(root):
    types = _types(root)
    tags = {t.get('Name'): t.get('DataType') for t in root.iter('Tag')}
    result = []
    for program in root.iter('Program'):
        local = {**tags, **{t.get('Name'): t.get('DataType') for t in program.iter('Tag')}}
        for routine in program.iter('Routine'):
            for statement in statements([l.text or '' for l in routine.iter('Line')]):
                for operand in bool_operands(statement.replace('\n', ' '), local, types):
                    result.append(dict(routine=routine.get('Name'), operand=operand,
                                       statement=' '.join(statement.split())[:240]))
    for aoi in root.iter('AddOnInstructionDefinition'):
        scope = {**tags, **types[aoi.get('Name')]}
        for routine in aoi.iter('Routine'):
            for statement in statements([l.text or '' for l in routine.iter('Line')]):
                for operand in bool_operands(statement.replace('\n', ' '), scope, types):
                    result.append(dict(routine=aoi.get('Name') + '/' + routine.get('Name'), operand=operand,
                                       statement=' '.join(statement.split())[:240]))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('project')
    args = parser.parse_args(argv)
    found = findings(ET.parse(args.project).getroot())
    print(json.dumps(dict(passed=not found, findings=found), indent=1))
    return 0 if not found else 1


if __name__ == '__main__':
    raise SystemExit(main())
