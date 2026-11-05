"""Locate BOOL operands in arithmetic or comparison context among the ST lines V6.11 adds.

Resolves each dotted operand through the L5X's tags, data types and AOI
parameters/locals. A BOOL is legal as an assignment target, an IF condition
and an AND/OR/XOR/NOT operand; next to + - * / MOD or = <> < > <= >= it is
what the v38 compiler refuses as RxSTX_E_BOOLOPND_UNEXPECTED.
"""
import difflib, json, re, sys
import xml.etree.ElementTree as ET

OLD, NEW = sys.argv[1], sys.argv[2]


def load(path):
    root = ET.parse(path).getroot()
    types = {}
    for dt in root.iter('DataType'):
        members = {}
        for m in dt.iter('Member'):
            members[m.get('Name')] = m.get('DataType')
        types[dt.get('Name')] = members
    aois = {}
    for aoi in root.iter('AddOnInstructionDefinition'):
        scope = {}
        for p in aoi.iter('Parameter'):
            scope[p.get('Name')] = p.get('DataType')
        for t in aoi.iter('LocalTag'):
            scope[t.get('Name')] = t.get('DataType')
        types[aoi.get('Name')] = dict(scope)
        aois[aoi.get('Name')] = (scope, {r.get('Name'): [l.text or '' for l in r.iter('Line')] for r in aoi.iter('Routine')})
    tags = {t.get('Name'): t.get('DataType') for t in root.iter('Tag')}
    routines = {}
    for program in root.iter('Program'):
        for r in program.iter('Routine'):
            routines[r.get('Name')] = [l.text or '' for l in r.iter('Line')]
    return types, tags, routines, aois


def resolve(path, scope, types):
    parts = re.split(r'\.', re.sub(r'\[[^\]]*\]', '', path))
    kind = scope.get(parts[0])
    for part in parts[1:]:
        if kind is None:
            return None
        if re.fullmatch(r'\d+', part):  # bit of an integer
            return 'BOOL'
        kind = types.get(kind, {}).get(part)
    return kind


NAME = r'[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?(?:\.[A-Za-z0-9_]+(?:\[[^\]]*\])?)*'
ARITH = r'(\+|-|\*|/|\bMOD\b|=|<>|<=|>=|<|>)'


def suspicious(line, scope, types):
    found = []
    code = re.sub(r'//.*$|\(\*.*?\*\)', '', line)
    code = re.sub(r"'[^']*'", "''", code)
    for m in re.finditer(NAME, code):
        name = m.group(0)
        if name.upper() in ('AND', 'OR', 'XOR', 'NOT', 'IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF', 'MOD', 'TRUE', 'FALSE',
                            'FOR', 'TO', 'DO', 'BY', 'END_FOR', 'WHILE', 'END_WHILE', 'CASE', 'OF', 'END_CASE',
                            'RETURN', 'EXIT', 'REPEAT', 'UNTIL', 'END_REPEAT'):
            continue
        if resolve(name, scope, types) != 'BOOL':
            continue
        before, after = code[:m.start()], code[m.end():]
        if re.match(r'\s*:=', after):
            continue  # assignment target
        prev = re.search(ARITH + r'\s*$', before)
        nxt = re.match(r'\s*' + ARITH, after)
        if (prev and not before.rstrip().endswith(':=')) or (nxt and not re.match(r'\s*:=', after)):
            found.append(name)
    return found


old_types, old_tags, old_routines, old_aois = load(OLD)
types, tags, routines, aois = load(NEW)
report = []
for name, lines in routines.items():
    added = [l for l in difflib.ndiff(old_routines.get(name, []), lines) if l.startswith('+ ')]
    for line in added:
        hits = suspicious(line[2:], tags, types)
        if hits:
            report.append(dict(routine=name, line=line[2:].strip()[:220], bool_operands=hits))
for name, (scope, bodies) in aois.items():
    for rname, lines in bodies.items():
        old = old_aois.get(name, ({}, {}))[1].get(rname, [])
        for line in (l for l in difflib.ndiff(old, lines) if l.startswith('+ ')):
            hits = suspicious(line[2:], {**tags, **scope}, types)
            if hits:
                report.append(dict(routine=name + '/' + rname, line=line[2:].strip()[:220], bool_operands=hits))
print(json.dumps(report, indent=1))
print(len(report), 'suspicious added lines')
