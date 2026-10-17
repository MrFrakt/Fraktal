"""Typed Line engine and owner/mirror composition (Core §3.8e / §8.5.2).

The engine has no module identity, HAL, registry row or command lifecycle. Its
caller supplies a complete source image and clock quality; it never trusts a
source to write the working values. Uses the existing config codec and metadata.
"""
from dataclasses import dataclass
from pathlib import Path

from fraktal_tia_binding import Catalog, PRIVATE, literal, type_source
from fraktal_tia_config import (assign_value, definition_source, fields_for_records,
                                function, read_value, record_targets, validate_definition, width)
from fraktal_tia_declaration import DeclarationError, object_fields, items, identifier

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/line_services.scl.in'


def calendar_contract(catalog, *, label=None):
    """One flat V3 binding for projects and fixtures; Core owns row defaults."""
    count=catalog.capacities['MAX_WEEKLY_SHIFTS']
    members=dict(utc_offset='UtcOffsetMin',start_min='ShiftStartMin',
                 duration_min='ShiftDurationMin',active_days='ShiftActiveDays',target='ShiftTarget')
    fields='UtcOffsetMin : DINT; '+' '.join('%s : ARRAY[1..%d] OF DINT;'%(members[key],count)
        for key in ('start_min','duration_min','active_days','target'))
    values=[dict(member='Line.UtcOffsetMin',key='line.shift.utcOffsetMin',revision=1,
        label=label or 'std.config.shiftUtcOffset',minimum=-840,maximum=840)]
    for row in range(1,count+1):
        for kind,key,suffix,minimum,maximum in (
            ('start_min','startMin','start',-1,1439),('duration_min','durationMin','duration',1,1440),
            ('active_days','activeDays','days',0,127),('target','target','target',0,2147483647)):
            values.append(dict(member='Line.%s[%d]'%(members[kind],row),key='line.shift.%d.%s'%(row,key),
                revision=1,label=label or 'std.config.shift.%d.%s'%(row,suffix),minimum=minimum,maximum=maximum))
    return fields,values,members


@dataclass(frozen=True)
class Line:
    line_id: str
    owner: str
    role: str
    roots: tuple[str, ...]
    record: str
    values: tuple[dict, ...]
    stale_after_ms: int
    source: str = ''
    shifts: tuple = ()

    def require_complete(self):
        if not self.shifts:
            raise DeclarationError('T-GEN','line','Core 1.5 Line profile requires the complete V3 calendar; partial engine work needs line_workbench')

    def definition(self):
        return dict(id=self.line_id, owner=self.owner, role=self.role, roots=list(self.roots),
                    record=self.record, values=list(self.values), stale_after_ms=self.stale_after_ms,
                    **({'source': self.source} if self.source else {}),
                    **({'shifts':dict(self.shifts)} if self.shifts else {}))

    @classmethod
    def read(cls, value, roots):
        object_fields(value, ('id', 'owner', 'role', 'roots', 'record', 'values', 'stale_after_ms'), ('source','shifts'), 'line')
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
        source = value.get('source', '')
        if source:
            identifier(source, 'line.source')
            if not source.startswith('F_') or value['role'] != 'MIRROR':
                raise DeclarationError('T-GEN', 'line.source', 'only a mirror binds a separate F_ image provider')
        elif not isinstance(source, str):
            raise DeclarationError('T-GEN', 'line.source', 'expected an F_ image provider')
        shifts=value.get('shifts',{})
        if shifts:
            object_fields(shifts,('utc_offset','start_min','duration_min','active_days','target'),(),'line.shifts')
            for name in shifts.values():identifier(name,'line.shifts')
            if len(set(shifts.values()))!=len(shifts):raise DeclarationError('T-GEN','line.shifts','calendar members are distinct')
        elif not isinstance(shifts,dict):raise DeclarationError('T-GEN','line.shifts','expected a V3 calendar binding')
        return cls(value['id'], value['owner'], value['role'], tuple(references),
                   value['record'], values, stale, source,tuple(shifts.items()))


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
        if line.shifts:
            targets=record_targets(catalog,line.record,capacity);count=catalog.capacities['MAX_WEEKLY_SHIFTS']
            keys={f.member:f.key for f in self.fields}
            for kind,member in line.shifts:
                leaves=[member] if kind=='utc_offset' else [member+'[%d]'%i for i in range(1,count+1)]
                for i,leaf in enumerate(leaves,1):
                    key='line.shift.utcOffsetMin' if kind=='utc_offset' else 'line.shift.%d.'%i+{'start_min':'startMin','duration_min':'durationMin','active_days':'activeDays','target':'target'}[kind]
                    if targets.get(leaf,'').split(':=')[0].strip().upper()!='DINT' or keys.get('Line.'+leaf)!=key:
                        raise DeclarationError('T-GEN','line.shifts','V3 requires bounded DInt arrays and canonical line.shift.* keys')

    def boot_call(self):
        role = str(self.line.role == 'OWNER').upper()
        return '    IF #Startup THEN "FRK_LineBoot"(OwnerRole := '+role+', NowMs := "FRK_Clock".NowMs, State := "FRK_Line".Data); END_IF;'

    def production_sources(self):
        from fraktal_tia_generate import db
        sources = self.sources()
        sources['05_FRK_Line.db'] = db('FRK_Line', ['Data'+PRIVATE+' : "FRK_LineState";',
                                                  'Ready'+PRIVATE+' : Bool;'])
        body = ['    #FRK_LineScope := '+' OR '.join('#Scope = '+literal(n) for n in self.line.roots)+';']
        sources['17_Line.scl'] += function('FRK_LineScope', ['Scope : String;'], [], [], body, 'Bool')
        if self.line.source:
            sources['05_FRK_LineSource.db'] = db('FRK_LineSource', ['Image'+PRIVATE+' : "ST_LineImage";'])
            body = ['    #SourceError := 0; #Stamp := LDT#1970-01-01-00:00:00; #Synchronized := FALSE;',
                    '    #Available := "'+self.line.source+'"(Image := "FRK_LineSource".Image, SourceError => #SourceError, Stamp => #Stamp, TimeSynchronized => #Synchronized);',
                    '    IF #Available AND #SourceError = 0 THEN',
                    '        #Applied := "FRK_LineApply"(Image := "FRK_LineSource".Image, Restore := FALSE, NowMs := "FRK_Clock".NowMs, Stamp := #Stamp, TimeSynchronized := #Synchronized, State := "FRK_Line".Data);',
                    '    END_IF;',
                    '    "FRK_LineTick"(NowMs := "FRK_Clock".NowMs, SourceError := #SourceError, State := "FRK_Line".Data);']
            sources['17_Line.scl'] += function('FRK_LineSourceTick', [], [],
                ['Available : Bool;', 'Applied : Bool;', 'SourceError : DInt;', 'Stamp : LDT;', 'Synchronized : Bool;'], body)
        body = ['    IF NOT "FRK_LineScope"(Scope := #Scope) THEN RETURN; END_IF;',
                '    IF #Scope = '+literal(self.line.roots[0])+' THEN',
                ('        "FRK_LineSourceTick"();' if self.line.source else
                 '        "FRK_LineTick"(NowMs := "FRK_Clock".NowMs, SourceError := 0, State := "FRK_Line".Data);'),
                '        "FRK_LineAnnounce"(Scope := #Scope, State := "FRK_Line".Data, AlarmLog := #AlarmLog);',
                '    END_IF;',
                '    #Published := "FRK_Line".Data.Status;',
                '    IF #Startup OR #Seen <> #Published.Revision THEN',
                '        #Seen := #Published.Revision;',
                '        #ConfigRevision := "FRK_ConfigRevision"(Previous := #ConfigRevision);',
                '    END_IF;']
        sources['17_Line.scl'] += function('FRK_LineFrame', ['Scope : String;', 'Startup : Bool;'],
            ['Seen : UDInt;', 'ConfigRevision : UDInt;', 'Published : "ST_LineStatus";', 'AlarmLog : "FRK_AlarmLog";'], [], body)
        return sources

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
        if self.line.shifts:
            members=dict(self.line.shifts)
            defaults={f['member']:f['initial'] for f in catalog.resolve(['ST_ShiftRowV3'])['ST_ShiftRowV3']}
            initial=[]
            for key,field in (('start_min','StartMin'),('duration_min','DurationMin')):
                for i in range(1,catalog.capacities['MAX_WEEKLY_SHIFTS']+1):
                    initial+=['    Values.'+members[key]+'[%d] := '%i+defaults[field]+';']
            sources['05_FRK_LineDefaults.db']=sources['05_FRK_LineDefaults.db'].replace('BEGIN\nEND_DATA_BLOCK','BEGIN\n'+'\n'.join(initial)+'\nEND_DATA_BLOCK')
        text = definition_source(fields, 'FRK_LineDef')
        if self.line.shifts:
            members=dict(self.line.shifts);count=catalog.capacities['MAX_WEEKLY_SHIFTS']
            body=['    #Calendar.SchemaVersion := 3;','    #Calendar.UtcOffsetMin := #Values.'+members['utc_offset']+';']
            for i in range(1,count+1):
                for key,field in (('start_min','StartMin'),('duration_min','DurationMin'),('active_days','ActiveDays'),('target','ProductionTarget')):
                    body+=['    #Calendar.Rows[%d].%s := #Values.%s[%d];'%(i,field,members[key],i)]
            text+=function('FRK_LineCalendar',[],['Values : "'+self.line.record+'";','Calendar : "ST_ShiftCalendarV3";'],[],body)
            text+=function('FRK_LineValid',[],['Values : "'+self.line.record+'";'],['Calendar : "ST_ShiftCalendarV3";'],[
                '    "FRK_LineCalendar"(Values := #Values, Calendar := #Calendar);',
                '    #FRK_LineValid := "FRK_ShiftValidate"(Calendar := #Calendar);'],'Bool')
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
        template=template.replace('@LINE_BUILD_VALIDATE@',
            '    IF NOT "FRK_LineValid"(Values := #State.Values) THEN #State.Status.SourceError := 2; RETURN; END_IF;' if self.line.shifts else '')
        template=template.replace('@LINE_APPLY_VALIDATE@',
            '    IF NOT "FRK_LineValid"(Values := #Stage) THEN RETURN; END_IF;' if self.line.shifts else '')
        template=template.replace('@LINE_WRITE_STAGE@','    Stage : "'+self.line.record+'";' if self.line.shifts else '')
        template=template.replace('@LINE_WRITE_ASSIGN@',
            '            #Stage := #State.Values;\n            "FRK_LineAssign"(FieldIndex := #FieldIndex, Values := #Stage);\n            IF NOT "FRK_LineValid"(Values := #Stage) THEN RETURN; END_IF;\n            #State.Values := #Stage;'
            if self.line.shifts else '            "FRK_LineAssign"(FieldIndex := #FieldIndex, Values := #State.Values);')
        constants = {'COUNT': len(fields), 'RECORD': self.line.record,
                     'LINE_ID': literal(self.line.line_id), 'OWNER': literal(self.line.owner),
                     'STALE_AFTER_MS': self.line.stale_after_ms,
                     'VALUE_WIDTH': width(catalog, 'ST_LineRecord', 'ValueText'),
                     'OWNER_ROLE': catalog.enums['E_LineRole']['OWNER'],
                     'MIRROR_ROLE': catalog.enums['E_LineRole']['MIRROR'],
                     'WRITE_CONFIG': catalog.enums['E_HmiRequestKind']['WRITE_CONFIG'],
                     'REASON_NONE': catalog.enums['E_Reason']['NONE'],
                     'E_Reason.PERMISSIVE_NOT_MET': catalog.enums['E_Reason']['PERMISSIVE_NOT_MET'],
                     'SEVERITY_LOW': catalog.enums['E_Severity']['LOW'],
                     'CATEGORY_SYSTEM': catalog.enums['E_Category']['SYSTEM'],
                     'AUTO_RESET': catalog.enums['E_ResetClass']['AUTO_RESET']}
        for key, value in constants.items():
            template = template.replace('@'+key+'@', str(value))
        assert '@' not in template
        text += template
        sources['17_Line.scl'] = text
        return sources

    def set_sources(self, record_capacity):
        """The ordinary root set walk delegates line records to their owner."""
        from fraktal_tia_generate import db
        state = '"FRK_Line".Data'
        work = '"FRK_SetRuntime".Work[#RootIndex]'
        payload = work+'.Payload'
        stage = '"FRK_LineSetStage".Values'
        body = ['    #FRK_LineSetWalk := FALSE;',
                '    '+work+'.RejectScope := '+literal(self.line.owner)+';',
                '    IF NOT "FRK_LineScope"(Scope := #Scope) OR NOT '+state+'.Applied',
                '        OR '+state+'.Status.Role <> %d THEN RETURN; END_IF;'%self.catalog.enums['E_LineRole']['OWNER'],
                '    IF #Phase = 2 THEN',
                '        '+state+'.Values := '+stage+';',
                '        "FRK_LineCommit"(State := '+state+');',
                '        #FRK_LineSetWalk := TRUE; RETURN;', '    END_IF;',
                '    IF #Phase = 1 OR #Phase = 4 THEN '+stage+' := '+state+'.Values; END_IF;']
        for index, field in enumerate(self.fields, 1):
            body += ['    "FRK_LineDef"(FieldIndex := %d);'%index,
                     '    '+work+'.RejectScope := #Scope; '+work+'.RejectKey := "FRK_ConfigScratch".Entry.WriteKey;',
                     '    IF #Phase = 0 OR #Phase = 5 THEN',
                     '        IF #Phase = 5 AND NOT "FRK_ConfigDataAllowed"(Access := #Access, ForWrite := FALSE, Scope := #Scope) THEN RETURN; END_IF;',
                     '        "FRK_LineValue"(FieldIndex := %d, Values := '%index+state+'.Values);',
                     '        IF NOT "FRK_ConfigValidate"(Text := "FRK_ConfigScratch".Entry.ValueText)',
                     '            OR '+payload+'.Info.RecordCount >= %d THEN RETURN; END_IF;'%record_capacity,
                     '        #Slot := '+payload+'.Info.RecordCount + 1;',
                     '        '+payload+'.Records[#Slot].Scope := #Scope;']
            for member, source in (('WriteKey','WriteKey'),('Revision','WriteRevision'),('Kind','ConfigKind'),('ValueType','ValueType')):
                body += ['        '+payload+'.Records[#Slot].'+member+' := "FRK_ConfigScratch".Entry.'+source+';']
            body += ['        '+payload+'.Records[#Slot].ValueText := WSTRING_TO_STRING("FRK_ConfigScratch".Entry.ValueText);',
                     '        '+payload+'.Info.RecordCount := #Slot;',
                     '    ELSE',
                     '        #Slot := "FRK_SetCheck"(RootIndex := #RootIndex, Scope := #Scope, Access := #Access, Ready := #Ready AND (#Phase = 4 OR "FRK_Line".Ready), WriteAccess := #Phase <> 3, ReserveTarget := FALSE);',
                     '        IF #Slot = 0 THEN RETURN; END_IF;',
                     '        IF #Phase = 1 OR #Phase = 4 THEN', assign_value(field, stage+'.'+field.member.split('.')[1]),
                     '        END_IF;', '    END_IF;']
        if self.line.shifts:body+=['    IF (#Phase = 1 OR #Phase = 4) AND NOT "FRK_LineValid"(Values := '+stage+') THEN RETURN; END_IF;']
        body += ['    #FRK_LineSetWalk := TRUE;']
        return {'05_FRK_LineSetStage.db': db('FRK_LineSetStage', ['Values'+PRIVATE+' : "'+self.line.record+'";']),
                '18_LineSets.scl': function('FRK_LineSetWalk', ['RootIndex : Int;', 'Scope : String;', 'Phase : Int;', 'Access : "FRK_Access";', 'Ready : Bool;'],
                                           [], ['Slot : Int;'], body, 'Bool')}
