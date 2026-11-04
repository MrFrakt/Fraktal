"""Offline executed-ST bench over the emitted L5X sections.

The controller's tags are built from the generated data types and the tag
initializers a download would carry. Its ST routines are the generated ones,
parsed only when a JSR first reaches them. A test therefore runs exactly the
emitted text against exactly the emitted initial data, not a fixture's copy of
either. The bench executes what fraktal_ab_st_model executes: ST routines.
Ladder, SFC and AOI bodies are not run; a test that needs their effect
writes it into the tags, as the existing fragment tests do.
"""
import copy
import xml.etree.ElementTree as ET

import fraktal_ab_st_model as st

NUMERIC = {'SINT', 'INT', 'DINT', 'LINT', 'USINT', 'UINT', 'UDINT', 'ULINT', 'BIT',
           'LDT', 'DT', 'TIME', 'LTIME', 'TIME32'}
# Predefined structures the emitted code declares, with the members it reads.
BUILTIN = {
    'TIMER': (('PRE', 'DINT', 0), ('ACC', 'DINT', 0), ('EN', 'BOOL', 0), ('TT', 'BOOL', 0), ('DN', 'BOOL', 0)),
    'FBD_TIMER': tuple((n, 'BOOL' if n not in ('PRE', 'ACC', 'Status') else 'DINT', 0) for n in
                       ('EnableIn', 'TimerEnable', 'PRE', 'Reset', 'EnableOut', 'ACC', 'EN', 'TT', 'DN',
                        'Status', 'InstructFault', 'PresetInv')),
    'COUNTER': (('PRE', 'DINT', 0), ('ACC', 'DINT', 0), ('CU', 'BOOL', 0), ('CD', 'BOOL', 0),
                ('DN', 'BOOL', 0), ('OV', 'BOOL', 0), ('UN', 'BOOL', 0)),
}


def _ascii(text):
    """Logix ASCII data: quoted, with $-escapes (fraktal_ab_manifest.ascii_literal)."""
    text = (text or '').strip()
    if not (len(text) >= 2 and text[0] == text[-1] == "'"):
        raise ValueError('ASCII string data is not a quoted literal')
    body, out, i = text[1:-1], [], 0
    escapes = {'$': 36, "'": 39, 'L': 10, 'N': 10, 'P': 12, 'R': 13, 'T': 9}
    while i < len(body):
        ch = body[i]
        if ch != '$':
            out.append(ord(ch))
            i += 1
        elif body[i + 1] in escapes:
            out.append(escapes[body[i + 1]])
            i += 2
        else:
            out.append(int(body[i + 1:i + 3], 16))
            i += 3
    # SINT storage: a byte above 127 reads back negative, as on the controller.
    return [b - 256 if b > 127 else b for b in out]


class Bench:
    """One application's emitted tags and routines, ready to scan in the model."""

    def __init__(self, data_types, aoi_definitions, controller_tags, programs, *, calls=None):
        self.types = {}
        for node in ET.fromstring(f'<Root>{data_types}</Root>').iter('DataType'):
            members = node.find('Members')
            self.types[node.get('Name')] = [(m.get('Name'), m.get('DataType'), int(m.get('Dimension') or 0))
                                            for m in members if m.get('Hidden') != 'true']
        if aoi_definitions and aoi_definitions.strip() not in ('', '<AddOnInstructionDefinitions/>'):
            for node in ET.fromstring(aoi_definitions).iter('AddOnInstructionDefinition'):
                fields = [(p.get('Name'), p.get('DataType'), int(p.get('Dimensions') or 0))
                          for p in node.iter('Parameter')]
                fields += [(t.get('Name'), t.get('DataType'), int(t.get('Dimensions') or 0))
                           for t in node.iter('LocalTag')]
                self.types[node.get('Name')] = fields
        self.tags = {'S:FS': False}
        self.sources = {}
        for node in ET.fromstring(controller_tags).iter('Tag'):
            self._tag(node)
        project = ET.fromstring(f'<Root>{programs}</Root>')
        for program in project.iter('Program'):
            for node in program.iter('Tag'):
                self._tag(node)
            for routine in program.iter('Routine'):
                if routine.get('Type') == 'ST':
                    self.sources[routine.get('Name')] = [line.text or '' for line in routine.iter('Line')]
        # GSV: the wall clock from `clock`, any other attribute from `attributes` or zero.
        self.clock = [2026, 11, 4, 12, 0, 0, 0]
        self.attributes = {}
        self.plc = _Typed(self.tags, calls={'CPS': st.cps_structure, 'GSV': self._gsv, **(calls or {})})
        self.plc.routines = _Lazy(self.sources)

    def zero(self, kind, count=0):
        if count:
            return [self.zero(kind) for _ in range(count)]
        if kind == 'BOOL':
            return False
        if kind in ('REAL', 'LREAL'):
            return 0.0
        if kind in NUMERIC:
            return 0
        # Other predefined structures (SFC_STEP, MESSAGE, ...) belong to bodies
        # the bench does not run: an empty record makes any read of one fail loudly.
        fields = self.types[kind] if kind in self.types else BUILTIN.get(kind, ())
        return {name: self.zero(member, n) for name, member, n in fields}

    def _tag(self, node):
        kind, dimensions = node.get('DataType'), node.get('Dimensions')
        count = int(dimensions.split()[0]) if dimensions else 0
        value = self.zero(kind, count)
        data = node.find("Data[@Format='Decorated']")
        if data is not None and len(data):
            value = _overlay(value, data[0])
        self.tags[node.get('Name')] = value

    def _gsv(self, controller, args):
        name = lambda arg: None if arg is None else arg[1][0][1]
        cls, attribute = name(args[0]), name(args[2])
        if (cls, attribute) == ('WallClockTime', 'DateTime'):
            for offset, value in enumerate(self.clock):
                holder, key = controller.element(args[3], offset)
                holder[key] = value
            return
        controller.write(args[3], self.attributes.get((cls, attribute), 0))

    def run(self, name):
        """Execute one emitted routine, with its JSRs, once."""
        self.plc.run(self.plc.routines[name])

    def text(self, value):
        return bytes(b & 0xff for b in value['DATA'][:value['LEN']]).decode('latin-1')

    def put(self, target, text):
        raw = text.encode('latin-1')
        if len(raw) > len(target['DATA']):
            raise ValueError('text exceeds the string width')
        target['LEN'] = len(raw)
        target['DATA'][:] = [b - 256 if b > 127 else b for b in raw] + [0] * (len(target['DATA']) - len(raw))

    def snapshot(self, name):
        return copy.deepcopy(self.tags[name])


class _Typed(st.Controller):
    """A BOOL member stays a BOOL, as controller storage does, whatever is written to it."""

    def write(self, ref, value):
        holder, key = self._container(ref)
        if isinstance(holder[key], bool):
            holder[key] = value != 0
            return
        super().write(ref, value)


class _Lazy(dict):
    def __init__(self, sources):
        super().__init__()
        self.sources = sources

    def __contains__(self, name):
        return name in self.sources

    def __missing__(self, name):
        program = st.parse('\n'.join(self.sources[name]))
        self[name] = program
        return program


def _scalar(node, kind):
    value = node.get('Value')
    if kind == 'BOOL':
        return value not in ('0', 'false', None)
    if kind in ('REAL', 'LREAL'):
        return float(value)
    return int(value)


def _overlay(value, node):
    """Write one Decorated element onto its zero-initialized shape."""
    tag = node.tag
    if tag in ('DataValue', 'DataValueMember'):
        if node.get('Radix') == 'ASCII':
            raw = _ascii(node.text)
            return raw + value[len(raw):] if isinstance(value, list) else raw
        return _scalar(node, node.get('DataType'))
    if tag in ('Structure', 'StructureMember'):
        for child in node:
            value[child.get('Name')] = _overlay(value[child.get('Name')], child)
        return value
    if tag in ('Array', 'ArrayMember'):
        for element in node:
            index = int(element.get('Index').strip('[]').split(',')[0])
            if element.get('Value') is not None:
                value[index] = _scalar(element, node.get('DataType'))
            else:
                value[index] = _overlay(value[index], element[0])
        return value
    raise ValueError('unsupported Decorated element ' + tag)


def for_application(app, **options):
    import fraktal_ab_generate as gen
    return Bench(gen.data_types(app), gen.aoi_definitions(app), gen.controller_tags(app), gen.programs(app), **options)
