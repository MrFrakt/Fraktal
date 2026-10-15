"""P1 typed line engine. Composition/mailbox/LOAD_DB integration is separate.

The engine has no module identity, HAL, registry row or command lifecycle. Its
caller supplies a complete source image and clock quality; it never trusts a
source to write the working values. Uses the existing config codec and metadata.
"""
from dataclasses import dataclass
from pathlib import Path

from fraktal_tia_binding import Catalog, PRIVATE, literal, type_source
from fraktal_tia_config import (assign_value, definition_source, fields_for_records,
                                function, read_value, record_targets, validate_definition, width)
from fraktal_tia_declaration import DeclarationError, object_fields, items

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/line_services.scl.in'


@dataclass(frozen=True)
class Line:
    line_id: str
    owner: str
    role: str
    roots: tuple[str, ...]
    record: str
    values: tuple[dict, ...]
    stale_after_ms: int

    @classmethod
    def read(cls, value, roots):
        object_fields(value, ('id', 'owner', 'role', 'roots', 'record', 'values', 'stale_after_ms'), (), 'line')
        facts = Catalog.read()
        for key, maximum in (('id', width(facts, 'ST_LineStatus', 'LineId')),
                             ('owner', width(facts, 'ST_LineStatus', 'Owner'))):
            text = value[key]
            if (not isinstance(text, str) or not text.isascii() or not 1 <= len(text) <= maximum
                    or any(ord(c) < 32 or ord(c) == 127 for c in text)):
                raise DeclarationError('T-WIDTH', 'line.'+key, 'expected bounded printable ASCII')
        if value['role'] not in ('OWNER', 'MIRROR'):
            raise DeclarationError('T-GEN', 'line.role', 'expected OWNER or MIRROR')
        references = items(value['roots'], 'line.roots')
        if (not references or any(not isinstance(n, str) or n not in roots for n in references)
                or len(set(references)) != len(references)):
            raise DeclarationError('T-GEN', 'line.roots', 'expected distinct deployed root names')
        if not isinstance(value['record'], str):
            raise DeclarationError('T-GEN', 'line.record', 'expected a typed config record')
        values = tuple(items(value['values'], 'line.values'))
        validate_definition(values, 'line', roles=('Line',), line=True)
        stale = value['stale_after_ms']
        # Elapsed arithmetic is modular UDInt; keep the declared window unambiguous.
        if type(stale) is not int or not 1 <= stale <= 2147483647:
            raise DeclarationError('T-WIDTH', 'line.stale_after_ms', 'expected 1..2147483647 ms')
        return cls(value['id'], value['owner'], value['role'], tuple(references),
                   value['record'], values, stale)


class Engine:
    def __init__(self, line, catalog):
        self.line, self.catalog = line, catalog
        capacity = catalog.capacities['MAX_LINE_RECORDS']
        if not 1 <= len(line.values) <= capacity:
            raise DeclarationError('T-WIDTH', 'line.values', 'expected 1..MAX_LINE_RECORDS capabilities')
        self.fields = fields_for_records(line.values, {'Line': line.record}, catalog,
                                         {'Line': 'LINE_CFG'}, 'line', capacity)
        expected = set(record_targets(catalog, line.record, capacity)) - {'SchemaVersion'}
        if expected != {f.member.split('.')[1] for f in self.fields}:
            raise DeclarationError('T-GEN', 'line.values', 'line replication requires the complete config record')

    def sources(self):
        from fraktal_tia_generate import db
        fields = self.fields
        catalog = self.catalog
        # This type is infrastructure, never a Unit child. External writes cannot
        # bypass the mailbox or mutate the source/working image.
        state = [('Values', '"'+self.line.record+'"'), ('Status', '"ST_LineStatus"'),
                 ('Image', '"ST_LineImage"'), ('Applied', 'Bool'), ('HaveSuccess', 'Bool'),
                 ('LastSuccessMs', 'UDInt'), ('StartedMs', 'UDInt'), ('BuiltRevision', 'UDInt'),
                 ('Dirty', 'Bool'), ('StaleSlot', 'Int')]
        sources = {'02_FRK_LineState.udt': type_source('FRK_LineState', [
            dict(member=n, native_type=t, accessible=False, initial='') for n, t in state])}
        sources['05_FRK_LineDefaults.db'] = db('FRK_LineDefaults', [
            'Values'+PRIVATE+' : "'+self.line.record+'";',
            'Image'+PRIVATE+' : "ST_LineImage";', 'Status'+PRIVATE+' : "ST_LineStatus";'])
        text = definition_source(fields, 'FRK_LineDef')
        # Typed encoders/decoders are shared with station/model config. No second
        # string-to-number parser, enum table, range rule or rounding rule exists.
        body = ['    CASE #FieldIndex OF']
        for index, f in enumerate(fields, 1):
            body += ['        %d:' % index, *read_value(f, '#Values.')]
        body += ['        ELSE "FRK_ConfigScratch".Entry.ValueText := WSTRING#\'\';', '    END_CASE;']
        # Strip the semantic role prefix: Values is the line's typed record.
        body = [s.replace('#Values.Line.', '#Values.') for s in body]
        text += function('FRK_LineValue', ['FieldIndex : Int;'], ['Values : "'+self.line.record+'";'], [], body)
        body = ['    CASE #FieldIndex OF']
        for index, f in enumerate(fields, 1):
            body += ['        %d:' % index, assign_value(f, '#Values.'+f.member.split('.')[1])]
        body += ['        ELSE RETURN;', '    END_CASE;']
        text += function('FRK_LineAssign', ['FieldIndex : Int;'], ['Values : "'+self.line.record+'";'], [], body)
        template = TEMPLATE.read_text('ascii')
        constants = {'COUNT': len(fields), 'RECORD': self.line.record,
                     'LINE_ID': literal(self.line.line_id), 'OWNER': literal(self.line.owner),
                     'STALE_AFTER_MS': self.line.stale_after_ms,
                     'VALUE_WIDTH': width(catalog, 'ST_LineRecord', 'ValueText'),
                     'OWNER_ROLE': catalog.enums['E_LineRole']['OWNER'],
                     'MIRROR_ROLE': catalog.enums['E_LineRole']['MIRROR'],
                     'WRITE_CONFIG': catalog.enums['E_HmiRequestKind']['WRITE_CONFIG'],
                     'REASON_NONE': catalog.enums['E_Reason']['NONE'],
                     'SEVERITY_LOW': catalog.enums['E_Severity']['LOW'],
                     'CATEGORY_SYSTEM': catalog.enums['E_Category']['SYSTEM'],
                     'AUTO_RESET': catalog.enums['E_ResetClass']['AUTO_RESET']}
        for key, value in constants.items():
            template = template.replace('@'+key+'@', str(value))
        assert '@' not in template
        text += template
        sources['17_Line.scl'] = text
        return sources
