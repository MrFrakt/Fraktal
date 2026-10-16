"""Typed editable config definitions; station/model persistence owns keyed values."""
from dataclasses import dataclass,replace
import math
from pathlib import Path
import re

from fraktal_tia_binding import Catalog, FLOAT_LIMITS, PRIVATE, READONLY, literal, type_source, split_type
from fraktal_tia_types import bound

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/config_services.scl.in'
DECIMAL_TEMPLATE = TEMPLATE.with_name('config_decimal.scl.in')
DECIMAL_EXPONENT_LIMIT = 400
INTEGER = {'INT': (-32768, 32767), 'DINT': (-2147483648, 2147483647),
           'UDINT': (0, 4294967295), 'TIME': (-2147483648, 2147483647),
           'SINT': (-128, 127), 'USINT': (0, 255), 'UINT': (0, 65535)}
FLOAT = {name: (-limit, limit) for name, (_, limit) in FLOAT_LIMITS.items()}


def record_targets(catalog, record, capacity=None):
    """Resolve explicit scalar/array-element capabilities from the owning type."""
    result = {}
    for member in catalog.records.get(record, []):
        _, array, scalar, _ = split_type(member['type'])
        if array:
            low, high = bound(array[1], catalog.capacities), bound(array[2], catalog.capacities)
            # A malformed or enormous record must fail before allocating a list.
            if high < low or high - low + 1 > (capacity or catalog.capacities['MAX_CONFIG_WRITES']):
                from fraktal_tia_declaration import DeclarationError
                raise DeclarationError('T-WIDTH', record, 'config array exceeds the per-module capability bound')
            result.update((member['name']+'['+str(i)+']', scalar) for i in range(low, high+1))
        else:
            result[member['name']] = scalar
    return result


def width(catalog, record, member):
    native = next(f['native_type'] for f in catalog.resolve([record])[record] if f['member'] == member)
    return int(re.fullmatch(r'(?:W)?String\[(\d+)\]', native, re.I)[1])


def validate_definition(fields, location, *, roles=('ParCfg', 'StationCfg'), line=False):
    from fraktal_tia_declaration import DeclarationError, object_fields
    facts = Catalog.read() if fields else None
    for field in fields:
        object_fields(field, ('member', 'key', 'revision', 'label'),
                      ('minimum', 'maximum', 'requires_ready', 'min_read', 'min_write', 'capture', 'class_id'), location + '.config')
        class_id = field.get('class_id', '')
        if not isinstance(class_id, str) or not class_id.isascii() or len(class_id) > width(facts, 'ST_DataClassPolicy', 'ClassId') or any(ord(c) < 32 for c in class_id):
            raise DeclarationError('T-WIDTH', location, 'data class identity exceeds the Core bound')
        if 'capture' in field and (line or not isinstance(field['capture'],str) or not re.fullmatch(r'(OutImm|OutCmd)\.[A-Za-z_][A-Za-z0-9_]*(?:\[(?:0|-?[1-9][0-9]*)\])?',field['capture'])):
            raise DeclarationError('T-GEN',location,'capture binds a scalar published by the owning module')
        if not isinstance(field['member'], str) or not re.fullmatch('('+'|'.join(map(re.escape, roles))+r')\.[A-Za-z_][A-Za-z0-9_]*(?:\[(?:0|-?[1-9][0-9]*)\])?', field['member']):
            raise DeclarationError('T-GEN', location, 'config member selects '+ ' or '.join(roles))
        for name in ('key', 'label'):
            maximum_width = width(facts, 'ST_ConfigWriteDef', 'Key' if name == 'key' else 'LabelKey')
            if not isinstance(field[name], str) or not field[name].isascii() or not 1 <= len(field[name]) <= maximum_width or any(ord(c) < 32 for c in field[name]):
                raise DeclarationError('T-WIDTH', location, 'config key/label exceeds Core width')
        if field['key'].startswith('line.') != line:
            raise DeclarationError('T-GEN', location, 'line.* keys belong exclusively to LINE_CFG capabilities')
        if type(field['revision']) is not int or not 1 <= field['revision'] <= 4294967295:
            raise DeclarationError('T-GEN', location, 'config revision must be a nonzero UDInt')
        if type(field.get('requires_ready', True)) is not bool:
            raise DeclarationError('T-GEN', location, 'config readiness must be Boolean')
        for name in ('min_read', 'min_write'):
            if type(field.get(name, 0)) is not int or not 0 <= field.get(name, 0) <= 4:
                raise DeclarationError('T-GEN', location, 'config access minimum must be a Core access level')
        for name in ('minimum', 'maximum'):
            if name in field and (type(field[name]) not in (int, float) or not math.isfinite(field[name])):
                raise DeclarationError('T-GEN', location, 'config bounds must be finite numbers')
    if len({f['key'] for f in fields}) != len(fields) or len({f['member'].casefold() for f in fields}) != len(fields):
        raise DeclarationError('T-GEN', location, 'config keys and targets must be unique per type')


@dataclass(frozen=True)
class Field:
    member: str
    key: str
    revision: int
    label: str
    scalar: str
    schema: int
    kind: int
    storage: int
    value_type: int
    minimum: float
    maximum: float
    has_minimum: bool
    has_maximum: bool
    requires_ready: bool
    min_read: int
    min_write: int
    length: int
    enum_values: tuple[int, ...]
    capture: str = ''
    class_id: str = ''


def fields_for(t, catalog):
    from fraktal_tia_declaration import DeclarationError
    if len(t.config) > catalog.capacities['MAX_CONFIG_WRITES']:
        raise DeclarationError('T-WIDTH', t.name, 'editable config exceeds Core per-module capacity')
    for field in t.config:
        if field.get('capture'):
            role,leaf=field['capture'].split('.')
            source=record_targets(catalog,dict(t.contract)[role]).get(leaf)
            target_role,target=field['member'].split('.')
            record=dict(t.contract)['ParCfg'] if target_role=='ParCfg' else t.station_config
            destination=record_targets(catalog,record).get(target)
            if source is None or destination is None or source.split(':=')[0].strip().upper()!=destination.split(':=')[0].strip().upper():
                raise DeclarationError('T-GEN',t.name,'capture source must exist in the public contract and match target storage type')
    return fields_for_records(t.config, {'ParCfg': dict(t.contract).get('ParCfg', ''), 'StationCfg': t.station_config},
                              catalog, {'ParCfg': 'PAR_CFG', 'StationCfg': 'STATION_CFG'}, t.name)


def fields_for_records(values, records, catalog, kinds, location, capacity=None):
    """One typed capability resolver for module config and orthogonal line config."""
    from fraktal_tia_declaration import DeclarationError
    result = []
    for value in values:
        role, name = value['member'].split('.')
        record = records[role]
        members = catalog.records.get(record, [])
        if not members or members[0]['name'] != 'SchemaVersion' or members[0]['type'].split(':=')[0].strip().upper() != 'UINT':
            raise DeclarationError('T-GEN', location, 'config must start with SchemaVersion : UINT')
        schema = re.search(r':=\s*(\d+)\s*$', members[0]['type'])
        if not schema or not 1 <= int(schema[1]) <= 65535:
            raise DeclarationError('T-GEN', location, 'editable config needs a nonzero declared schema')
        scalar_type = record_targets(catalog, record, capacity).get(name)
        if scalar_type is None or name == 'SchemaVersion':
            raise DeclarationError('T-GEN', location, 'editable config target is missing or is its schema')
        enum_values = tuple(sorted(set(catalog.enums.get(scalar_type, {}).values())))
        if len('|'.join(map(str, enum_values))) > width(catalog, 'ST_ConfigEntry', 'EnumDomain'):
            raise DeclarationError('T-WIDTH', location, 'enum domain exceeds the Core manifest width')
        scalar = 'DINT' if enum_values else scalar_type.upper()
        string = re.fullmatch(r'STRING\((\d+)\)', scalar)
        length = int(string[1]) if string else 0
        # The current Core set-record value contract is 80 characters. Reject
        # wider targets before generation; never truncate accepted live values.
        if string and not 1 <= length <= width(catalog, 'ST_ConfigRecord', 'ValueText'):
            raise DeclarationError('T-WIDTH', location, 'config text exceeds the Core persistence value width')
        if scalar not in INTEGER and scalar not in FLOAT and scalar != 'BOOL' and not string:
            raise DeclarationError('T-GEN', location, 'unsupported config scalar or non-scalar target')
        low, high = (min(enum_values), max(enum_values)) if enum_values else {**INTEGER, **FLOAT}.get(scalar, (0, 1))
        minimum, maximum = value.get('minimum', low), value.get('maximum', high)
        if not low <= minimum <= maximum <= high or (scalar not in INTEGER and scalar not in FLOAT and ('minimum' in value or 'maximum' in value)):
            raise DeclarationError('T-GEN', location, 'config range is incompatible with its native storage')
        storage = 'AS_STRING' if string else 'AS_' + ('DINT' if scalar in ('SINT', 'USINT', 'UINT') else scalar)
        value_type = 'TEXT' if string else ('BOOLEAN' if scalar == 'BOOL' else ('DURATION' if scalar == 'TIME' else 'NUMBER'))
        result.append(Field(value['member'], value['key'], value['revision'], value['label'], scalar,
                            int(schema[1]), catalog.enums['E_ConfigKind'][kinds[role]],
                            catalog.enums['E_ConfigStorage'][storage], catalog.enums['E_ConfigValueType'][value_type],
                            minimum, maximum, 'minimum' in value, 'maximum' in value,
                            value.get('requires_ready', True), value.get('min_read', 0), value.get('min_write', 0), length, enum_values,value.get('capture',''),value.get('class_id','')))
    return tuple(result)


def function(name, inputs, inouts, temps, body, result='Void'):
    lines = ['FUNCTION "'+name+'" : '+result, "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1']
    for section, declarations in (('VAR_INPUT', inputs), ('VAR_IN_OUT', inouts), ('VAR_TEMP', temps)):
        if declarations:
            lines += [section, *['    '+d for d in declarations], 'END_VAR']
    return '\n'.join([*lines, 'BEGIN', *body, 'END_FUNCTION', ''])


def name(t, operation):
    return 'FRK_Cfg'+operation+'_'+t.name.removeprefix('FB_')


def read_value(field, prefix='#Module.'):
    source = prefix + field.member
    if field.scalar == 'BOOL':
        return ['    IF '+source+' THEN "FRK_ConfigScratch".Entry.ValueText := WSTRING#\'true\'; ELSE "FRK_ConfigScratch".Entry.ValueText := WSTRING#\'false\'; END_IF;']
    if field.length:
        value = 'STRING_TO_WSTRING('+source+')'
    elif field.enum_values:
        value = '"FRK_ConfigEnumText"(Number := '+source+')'
    elif field.scalar in FLOAT:
        value = '"FRK_ConfigDecimalText"(Number := '+('REAL_TO_LREAL('+source+')' if field.scalar == 'REAL' else source)+')'
    elif field.scalar == 'TIME':
        value = 'DINT_TO_WSTRING(TIME_TO_DINT('+source+'))'
    else:
        value = field.scalar+'_TO_WSTRING('+source+')'
    return ['    "FRK_ConfigScratch".Entry.ValueText := '+value+';']


def assign_value(field, target):
    value = '"FRK_ConfigScratch".Value'
    expression = value+'.Text' if field.length else (value+'.Flag' if field.scalar == 'BOOL' else 'LINT_TO_'+('TIME' if field.scalar == 'TIME' else field.scalar)+'('+value+'.Number)')
    if field.scalar == 'TIME':
        expression = 'DINT_TO_TIME(LINT_TO_DINT('+value+'.Number))'
    elif field.scalar in FLOAT:
        expression = value+'.Decimal' if field.scalar == 'LREAL' else 'LREAL_TO_REAL('+value+'.Decimal)'
    return '    '+target+' := '+expression+';'


def definition_source(fields, function_name):
    if not fields:
        return function(function_name, ['FieldIndex : Int;'], [], [],
                        ['    "FRK_ConfigScratch".Entry := "FRK_ConfigScratch".Blank;'])
    body = ['    "FRK_ConfigScratch".Entry := "FRK_ConfigScratch".Blank;',
            '    "FRK_ConfigScratch".EnumCount := 0;', '    CASE #FieldIndex OF']
    for index, f in enumerate(fields, 1):
        body += ['        %d:'%index]
        facts = {'WriteKey': literal(f.key), 'WriteRevision': 'UDINT#'+str(f.revision), 'ClassId': literal(f.class_id),
                 'EnumDomain': 'WSTRING#'+literal('|'.join(map(str, f.enum_values))),
                 'Item': 'WSTRING#'+literal(f.member.replace('.', '/')), 'ConfigKind': str(f.kind),
                 'ValueType': str(f.value_type), 'Writable': 'TRUE', 'RequiresReady': str(f.requires_ready).upper(),
                 'HasMinimum': str(f.has_minimum).upper(), 'HasMaximum': str(f.has_maximum).upper(),
                 'Minimum': str(float(f.minimum)), 'Maximum': str(float(f.maximum)), 'LabelKey': literal(f.label)}
        body += ['            "FRK_ConfigScratch".Entry.'+n+' := '+v+';' for n, v in facts.items()]
        body += ['            "FRK_ConfigScratch".'+n+' := '+v+';' for n, v in (
            ('Storage', str(f.storage)), ('Schema', str(f.schema)), ('Minimum', str(float(f.minimum))),
            ('Maximum', str(float(f.maximum))), ('MaxLength', str(f.length)),
            ('MinRead', str(f.min_read)), ('MinWrite', str(f.min_write)))]
        body += ['            "FRK_ConfigScratch".EnumCount := %d;'%len(f.enum_values)]
        body += ['            "FRK_ConfigScratch".EnumValues[%d] := %d;'%(i, v)
                 for i, v in enumerate(f.enum_values, 1)]
    body += ['        ELSE RETURN;', '    END_CASE;']
    return function(function_name, ['FieldIndex : Int;'], [], [], body)


class Layout:
    def __init__(self, model, catalog):
        from fraktal_tia_declaration import DeclarationError
        self.model, self.catalog = model, catalog
        self.scope_width = width(catalog, 'ST_ConfigRecord', 'Scope')
        self.value_width = width(catalog, 'ST_ConfigRecord', 'ValueText')
        self.model_width = width(catalog, 'ST_ModelId', 'ModelCode')
        self.lookup = {t.name.casefold(): t for t in model.types}
        self.line = None
        self.line_types = set()
        if model.line:
            from fraktal_tia_line import Engine
            self.line = Engine(model.line, catalog)
            self.line_types = {self.lookup[r.type_name.casefold()].name for r in model.roots if r.name in model.line.roots}
        self.fields = {t.name: fields_for(t, catalog) for t in model.types}
        self.roots = {self.lookup[r.type_name.casefold()].name for r in model.roots}
        self.models = model.model_config or ('',)
        self.root_map = {}
        ordinal = 0
        for instance in model.instances:
            if instance.parent_index == 0:
                ordinal += 1
            self.root_map[instance.index] = ordinal
            if self.fields[instance.type_name] and len(instance.path) > self.scope_width:
                raise DeclarationError('T-WIDTH', instance.path, 'canonical config scope exceeds the Core persistence record width')
        model_members = {f.member for name in self.roots for f in self.fields[name] if f.member.startswith('ParCfg.')}
        for code, member, _ in model.model_seeds:
            if member not in model_members:
                raise DeclarationError('T-GEN', 'model_config.seeds.' + code, member + ' is not declared root model config')
        self.capacity = sum((len(self.models) if f.kind == catalog.enums['E_ConfigKind']['PAR_CFG'] else 1)
                            for i in model.instances for f in self.fields[i.type_name])
        if self.line:
            self.capacity = max(1, self.capacity)
        self.required = {}
        self.texts = {}
        self.sets = None
        if model.config_set_capacity:
            from fraktal_tia_config_sets import Sets
            self.sets = Sets(self)
        if not self.capacity or self.capacity > 32767:
            raise DeclarationError('T-WIDTH', 'config', 'retained config pool must fit an Int index')
        for t in model.types:
            if model.model_config:
                expected = set(record_targets(catalog, dict(t.contract)['ParCfg'])) - {'SchemaVersion'}
                provided = {f.member.split('.')[1] for f in self.fields[t.name] if f.member.startswith('ParCfg.')}
                # A type opts into model data by registering ParCfg members, and then
                # registers all of them; one that registers none keeps its fixed
                # type defaults (TC3: a module set up with no recipe).
                if provided and expected != provided:
                    raise DeclarationError('T-GEN', t.name, 'model provider requires the complete ParCfg record to be registered')

    def components(self, t):
        fields = {'Core': '"FRK_Core"', 'Status': '"ST_ModuleStatus"',
                  'OutImm':'"'+dict(t.contract)['OutImm']+'"','OutCmd':'"'+dict(t.contract)['OutCmd']+'"',
                  'ParCfg': '"'+dict(t.contract)['ParCfg']+'"',
                  'ModePolicy': 'Array[0..%d] of "ST_ModePolicy"'%(len(self.catalog.enums['E_Mode'])-1),
                  'Access': '"FRK_Access"', 'Unit': '"FRK_Unit"',
                  'HmiResponse': '"ST_HmiResponse"', 'AlarmLog':'"FRK_AlarmLog"', 'ConfigPersist': '"ST_ConfigPersistStatus"',
                  'ConfigCursor': '"FRK_ConfigCursor"', 'ConfigRev': 'UDInt',
                  'Model': '"ST_ModelId"', 'AvailableModelCount': 'Int', 'ConfigStaged': 'Bool'}
        if t.sequence_view:
            fields.update({'SequenceStepDef': 'Array[1..%d] of "ST_SequenceStepDef"'%t.sequence_view[0], 'SequenceStepCount': 'Int'})
        if t.name in self.line_types:
            fields.update({'Line': '"ST_LineStatus"', 'LineRevisionSeen': 'UDInt'})
        if self.sets:
            fields.update({'ConfigSets': 'Array[1..%d] of "ST_ConfigSetInfo"'%self.sets.capacity,
                           'ConfigSetCount': 'Int', 'ConfigSetDocument': 'WString',
                           'ConfigSetDocumentLine': 'Int', 'ConfigSetDocumentLines': 'Int'})
        fields['SupportedModesPublished'] = 'Array[0..%d] of Bool'%(len(self.catalog.enums['E_Mode'])-1)
        if t.station_config:
            fields['StationCfg'] = '"'+t.station_config+'"'
        for role in sorted({f.member.split('.')[0] for f in self.fields[t.name]}):
            fields['ConfigStage'+role] = fields[role]
            fields['ConfigDefault'+role] = fields[role]
        fields.update({child.name: '"'+child.type_name+'"' for child in t.children})
        return fields

    def render(self, t, operation, inputs, inouts, temps, body, result='Void', function_name=None):
        # An FB cannot pass itself as a parameter instance. Own-frame services
        # take exactly the components they use; a parent's walk uses its child FB.
        if operation == 'Restore' or t.name in self.roots:
            used = set(re.findall(r'#Module\.(\w+)', '\n'.join(body)))
            fields = self.components(t)
            unknown = used - fields.keys()
            if unknown:
                raise ValueError('unknown config owner component: '+str(unknown))
            required = tuple(n for n in fields if n in used)
            self.required[(t.name, operation)] = required
            body = [line.replace('#Module.', '#') for line in body]
            inouts = [n+' : '+fields[n]+';' for n in required] + [d for d in inouts if not d.startswith('Module :')]
        else:
            self.required[(t.name, operation)] = None
        return function(function_name or name(t, operation), inputs, inouts, temps, body, result)

    def call(self, t, operation, prefix, **args):
        required = self.required[(t.name, operation)]
        values = {'Module': prefix.rstrip('.')} if required is None else {n: prefix+n for n in required}
        values.update(args)
        from fraktal_tia_generate import config_name
        target = config_name(t) if operation == 'Read' else name(t, operation)
        return '"'+target+'"('+', '.join(k+' := '+v for k, v in values.items())+')'

    def prepare(self, ordered):
        for t in ordered:
            self.texts[t.name] = self.definitions(t) + self.restore(t) + self.read(t) + self.write(t) + self.recipe(t)
            if self.sets:
                self.texts[t.name] += self.sets.walk(t)
            if t.name in self.roots:
                self.texts[t.name] += self.operations(t)
                if self.sets:
                    self.texts[t.name] += self.sets.operation(t)

    def declarations(self, t):
        result = []
        if t.name in self.line_types:
            result += ['    Line'+READONLY+' : "ST_LineStatus";',
                       '    LineRevisionSeen'+PRIVATE+' : UDInt;']
        if t.station_config:
            result.append('    StationCfg'+READONLY+' : "'+t.station_config+'";')
        roles = {f.member.split('.')[0] for f in self.fields[t.name]}
        for role in sorted(roles):
            record = dict(t.contract)['ParCfg'] if role == 'ParCfg' else t.station_config
            result += ['    ConfigStage'+role+PRIVATE+' : "'+record+'";',
                       '    ConfigDefault'+role+PRIVATE+' : "'+record+'";']
        if roles:
            result += ['    ConfigStaged'+PRIVATE+' : Bool;']
        if t.name in self.roots:
            result += ['    ConfigPersist'+READONLY+' : "ST_ConfigPersistStatus";',
                       '    Model'+READONLY+' : "ST_ModelId";',
                       '    AvailableModelCount'+READONLY+' : Int;',
                       '    AvailableModels'+READONLY+' : Array[1..%d] of "ST_ModelId";'%len(self.models)]
        if self.sets:
            result += self.sets.declarations(t)
        return result

    def definitions(self, t):
        return definition_source(self.fields[t.name], name(t, 'Def'))

    def restore(self, t):
        fields = self.fields[t.name]
        if not fields:
            return ''
        body = ['    #RootIndex := "FRK_ConfigRoot"(RegIndex := #Module.Core.RegIndex);',
                '    IF #RootIndex = 0 THEN RETURN; END_IF;']
        # Each owning record is an independent restore transaction. A rejected
        # model config must not discard valid station config on the same module.
        for role in sorted({f.member.split('.')[0] for f in fields}):
            group = [(i, f) for i, f in enumerate(fields, 1) if f.member.startswith(role+'.')]
            body += ['    #Ok := TRUE;', '    #Module.ConfigStage'+role+' := #Module.ConfigDefault'+role+';']
            for index, f in group:
                body += ['    "'+name(t, 'Def')+'"(FieldIndex := %d);'%index]
                models = self.models if role == 'ParCfg' else ('',)
                for code in models:
                    seed = self.seed(code, f.member) if role == 'ParCfg' else None
                    body += ['    IF "FRK_ConfigFind"(Scope := #Module.Status.Name, Key := "FRK_ConfigScratch".Entry.WriteKey, ModelCode := '+literal(code)+') = 0 THEN',
                             # A seeded model starts from its declared value, staged
                             # through the same text encoder, then the stage is reset.
                             *(['        #Module.ConfigStage'+f.member+' := '+seed+';', *read_value(f, '#Module.ConfigStage'),
                                '        #Module.ConfigStage'+f.member+' := #Module.ConfigDefault'+f.member+';']
                               if seed else read_value(f, '#Module.ConfigDefault')),
                             '        #Stored := "FRK_ConfigPut"(Scope := #Module.Status.Name, ModelCode := '+literal(code)+', Text := "FRK_ConfigScratch".Entry.ValueText, RootIndex := #RootIndex);',
                             ('        IF NOT "FRK_ConfigRuntime".Fresh AND NOT "FRK_PersistVirginConfig"(Scope := #Module.Status.Name, ModelCode := '+literal(code)+', Kind := %d) THEN'%f.kind if self.model.persistence_min_write_ms else '        IF NOT "FRK_ConfigRuntime".Fresh THEN'),
                             '            '+('IF "FRK_ConfigStore".ActiveModels[#RootIndex] = '+literal(code)+' THEN #Ok := FALSE; END_IF;' if role == 'ParCfg' else '#Ok := FALSE;'),
                             '            "FRK_ConfigLoss"(RootIndex := #RootIndex, Scope := #Module.Status.Name);', '        END_IF;', '    END_IF;']
                code = '"FRK_ConfigStore".ActiveModels[#RootIndex]' if role == 'ParCfg' else "''"
                body += ['    #Stored := "FRK_ConfigGet"(Scope := #Module.Status.Name, ModelCode := '+code+');',
                         '    #Ok := #Ok AND #Stored;', '    IF #Stored THEN',
                         assign_value(f, '#Module.ConfigStage'+f.member), '    END_IF;']
            body += ['    IF #Ok THEN', '        #Module.'+role+' := #Module.ConfigStage'+role+';',
                     '    ELSE', '        #Module.'+role+' := #Module.ConfigDefault'+role+';',
                     '        "FRK_ConfigLoss"(RootIndex := #RootIndex, Scope := #Module.Status.Name);']
            for index, f in group:
                code = '"FRK_ConfigStore".ActiveModels[#RootIndex]' if role == 'ParCfg' else "''"
                body += ['        "'+name(t, 'Def')+'"(FieldIndex := %d);'%index, *read_value(f, '#Module.ConfigDefault'),
                         '        #Stored := "FRK_ConfigPut"(Scope := #Module.Status.Name, ModelCode := '+code+', Text := "FRK_ConfigScratch".Entry.ValueText, RootIndex := #RootIndex);']
            body += ['    END_IF;']
        return self.render(t, 'Restore', [], ['Module : "'+t.name+'";'],
                        ['RootIndex : Int;', 'Ok : Bool;', 'Stored : Bool;'], body)

    def seed(self, code, member):
        """The declared seed literal for (model, member), or None."""
        return next((value for model, name, value in self.model.model_seeds
                     if model == code and name == member), None)

    def read(self, t):
        from fraktal_tia_generate import config_name
        from fraktal_tia_data_classes import effective_level
        body = ['    IF #ModelIndex = 0 THEN']
        service = 'FRK_ConfigUnit' if t.unit_modes else 'FRK_ConfigCatalog'
        facet = 'Policy := #Module.ModePolicy, ModelCount := #Module.AvailableModelCount' if t.name in self.roots else ('Policy := #Module.ModePolicy, ModelCount := 0' if t.unit_modes else 'Catalog := #Module.Catalog, Count := #Module.CatalogCount')
        body += ['        "'+service+'"(Scope := #Module.Status.Name, '+facet+', ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page);', '    END_IF;']
        if t.unit_modes and __import__('fraktal_tia_platform').active_gates(self.model):
            body+=['    IF #ModelIndex = 0 AND #Module.Core.ParentIndex = 0 THEN "FRK_EngineeringManifest"(Scope := #Module.Status.Name, Access := #Access, Cursor := #Cursor, Page := #Page); END_IF;']
        if self.sets and t.name in self.roots:
            body += ['    IF #ModelIndex = 0 AND #Module.Core.ParentIndex = 0 THEN',
                     '        "FRK_ConfigAppend"(Scope := #Module.Status.Name, Item := \'Features/ExportCurrentConfig\', ValueText := WSTRING#\'true\', ValueType := %d, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page);'%self.catalog.enums['E_ConfigValueType']['BOOLEAN'],
                     '    END_IF;']
        if t.sequence_view:
            body += ['    IF #ModelIndex = 0 THEN "FRK_ViewManifest"(Scope := #Module.Status.Name, Defs := #Module.SequenceStepDef, Count := #Module.SequenceStepCount, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page); END_IF;']
        if any(f.capture for f in self.fields[t.name]):
            body += ['    IF #ModelIndex = 0 THEN "FRK_ConfigAppend"(Scope := #Module.Status.Name, Item := \'Features/CaptureConfig\', ValueText := WSTRING#\'true\', ValueType := %d, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page); END_IF;'%self.catalog.enums['E_ConfigValueType']['BOOLEAN']]
        if t.name in self.roots and self.model.model_config:
            body += ['    IF #ModelIndex = 0 THEN']
            for index, code in enumerate(self.models, 1):
                item = 'AvailableModels/AvailableModels[%d]/ModelCode'%index
                body += ['        "FRK_ConfigAppend"(Scope := #Module.Status.Name, Item := '+literal(item)+', ValueText := WSTRING#'+literal(code)+', ValueType := 1, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #Cursor, Page := #Page);']
            body += ['    END_IF;']
        for index, f in enumerate(self.fields[t.name], 1):
            scoped = f.member.startswith('ParCfg.') and t.name in self.roots
            condition = '#ModelIndex = 0' if not scoped else '(#ModelIndex = 0 OR #Module.Core.ParentIndex = 0)'
            body += ['    IF '+condition+' THEN', '        "'+name(t, 'Def')+'"(FieldIndex := %d);'%index,
                     '        "FRK_ConfigScratch".Entry.Scope := STRING_TO_WSTRING(#Module.Status.Name);',
                     '        "FRK_ConfigScratch".Entry.ReadLevel := '+effective_level(False)+';',
                     '        "FRK_ConfigScratch".Entry.WriteLevel := '+effective_level(True)+';',
                     '        "FRK_ConfigScratch".Entry.Readable := #Access.CurrentLevel >= "FRK_ConfigScratch".Entry.ReadLevel;',
                     '        "FRK_ConfigScratch".Entry.ModelScoped := '+('#Module.Core.ParentIndex = 0' if scoped else 'FALSE')+';']
            if scoped:
                body += ['        IF #ModelIndex <> 0 THEN',
                         '            "FRK_ConfigScratch".Entry.RequiresReady := "FRK_ConfigScratch".Entry.RequiresReady AND "FRK_ConfigModelCode"(RootIndex := #RootIndex, ModelIndex := #ModelIndex) = "FRK_ConfigStore".ActiveModels[#RootIndex];',
                         '            #Ok := "FRK_ConfigGet"(Scope := #Module.Status.Name, ModelCode := "FRK_ConfigModelCode"(RootIndex := #RootIndex, ModelIndex := #ModelIndex));',
                         '            IF NOT #Ok THEN "FRK_ConfigScratch".Entry.Readable := FALSE; END_IF;', '        ELSE', *read_value(f), '        END_IF;']
            else:
                body += read_value(f)
            if f.scalar in FLOAT:
                body += ['        IF "FRK_ConfigScratch".Entry.ValueText = WSTRING#\'\' THEN "FRK_ConfigScratch".Entry.Readable := FALSE; END_IF;']
            body += ['        IF NOT "FRK_ConfigScratch".Entry.Readable THEN "FRK_ConfigScratch".Entry.ValueText := WSTRING#\'\'; END_IF;',
                     '        "FRK_ConfigAppendEntry"(Cursor := #Cursor, Page := #Page);', '    END_IF;']
        for child in t.children:
            body += ['    IF #ModelIndex = 0 THEN '+self.call(self.lookup[child.type_name.casefold()], 'Read', '#Module.'+child.name+'.', Access='#Access', RootIndex='#RootIndex', ModelIndex='#ModelIndex', Cursor='#Cursor', Page='#Page')+'; END_IF;']
        if t.name in self.line_types:
            body += ['    IF #ModelIndex = 0 AND #Module.Core.ParentIndex = 0 AND "FRK_LineScope"(Scope := #Module.Status.Name) THEN',
                     '        "FRK_LineManifest"(Scope := #Module.Status.Name, Access := #Access, State := "FRK_Line".Data, Cursor := #Cursor, Page := #Page);', '    END_IF;']
        return self.render(t, 'Read', ['Access : "FRK_Access";', 'RootIndex : Int;', 'ModelIndex : UDInt;'],
                           ['Module : "'+t.name+'";', 'Cursor : "FRK_ConfigCursor";', 'Page : "ST_ConfigPage";'], ['Ok : Bool;'], body, function_name=config_name(t))

    def write(self, t):
        body = ['    #'+name(t, 'Write')+' := FALSE;',
                '    IF #Request.TargetPath = STRING_TO_WSTRING(#Module.Status.Name) OR (#Request.TargetPath = WSTRING#\'\' AND #Module.Core.ParentIndex = 0) THEN']
        for index, f in enumerate(self.fields[t.name], 1):
            # Key matching invokes the same definition used by the manifest and restore.
            body += ['        "'+name(t, 'Def')+'"(FieldIndex := %d);'%index,
                     '        IF #Request.NameValue = "FRK_ConfigScratch".Entry.WriteKey THEN',
                     '            #Matched := TRUE;',
                     '            "FRK_ConfigScratch".CommittedScope := #Module.Status.Name;',
                     '            IF DINT_TO_UDINT(#Request.IntValue) <> "FRK_ConfigScratch".Entry.WriteRevision THEN RETURN; END_IF;',
                     '            IF NOT "FRK_ConfigDataAllowed"(Access := #Access, ForWrite := TRUE, Scope := #Module.Status.Name) THEN',
                     '                "FRK_ConfigScratch".RejectDescription := WSTRING#\'std.error.accessDenied\';',
                     '                "FRK_ConfigScratch".RejectReason := %d; RETURN; END_IF;'%self.catalog.enums['E_Reason']['PERMISSIVE_NOT_MET']]
            model_field = f.member.startswith('ParCfg.')
            root_field = model_field and t.name in self.roots
            if not root_field:
                body += ['            IF #Request.DurationMs <> 0 THEN RETURN; END_IF;']
            else:
                body += ['            IF #Request.DurationMs <> 0 AND #Module.Core.ParentIndex <> 0 THEN RETURN; END_IF;']
            code = '"FRK_ConfigModelCode"(RootIndex := #RootIndex, ModelIndex := #Request.DurationMs)' if model_field else "''"
            body += ['            #Code := '+code+';',
                     '            #Inactive := '+('#Code <> "FRK_ConfigStore".ActiveModels[#RootIndex]' if model_field else 'FALSE')+';',
                     '            IF "FRK_ConfigScratch".Entry.RequiresReady AND NOT #Inactive AND NOT #RootReady THEN',
                     '                "FRK_ConfigScratch".RejectDescription := WSTRING#\'std.release.unitNotReady\';',
                     '                "FRK_ConfigScratch".RejectReason := %d; RETURN; END_IF;'%self.catalog.enums['E_Reason']['PERMISSIVE_NOT_MET'],
                     ]
            body+=['            #Text := #Request.TextValue;']
            capture=self.catalog.enums['E_HmiRequestKind']['CAPTURE_CONFIG']
            if f.capture:
                body+=['            IF #Request.Kind = %d THEN'%capture,
                    '                IF #Inactive OR NOT #RootReady THEN RETURN; END_IF;',
                    *read_value(replace(f,member=f.capture)),
                    '                #Text := "FRK_ConfigScratch".Entry.ValueText;','            END_IF;']
            else:body+=['            IF #Request.Kind = %d THEN RETURN; END_IF;'%capture]
            body += ['            #Ok := "FRK_ConfigPut"(Scope := #Module.Status.Name, ModelCode := #Code, Text := #Text, RootIndex := #RootIndex);',
                     '            IF NOT #Ok THEN RETURN; END_IF;',
                     '            "FRK_ConfigScratch".CommittedText := #Text; "FRK_ConfigScratch".CommittedScope := #Module.Status.Name;', '            IF NOT #Inactive THEN',
                     assign_value(f, '#Module.'+f.member), '            END_IF;',
                     '            #'+name(t, 'Write')+' := TRUE;', '            RETURN;', '        END_IF;']
        if t.name in self.line_types:
            body += ['        IF #Module.Core.ParentIndex = 0 AND "FRK_LineScope"(Scope := #Module.Status.Name) THEN',
                     '            #Ok := "FRK_LineWrite"(Request := #Request, Access := #Access, Ready := #RootReady AND "FRK_Line".Ready, State := "FRK_Line".Data, Matched := #Matched);',
                     '            IF #Ok THEN "FRK_ConfigScratch".CommittedText := #Request.TextValue; "FRK_ConfigScratch".CommittedScope := '+literal(self.model.line.owner)+'; END_IF;',
                     '            IF #Matched THEN #'+name(t, 'Write')+' := #Ok; RETURN; END_IF;', '        END_IF;']
        body += ['    END_IF;']
        if not self.fields[t.name] and t.name not in self.line_types:
            # TIA rejects an empty IF body, even when it is unreachable.
            body = [body[0]]
        for child in t.children:
            body += ['    #Ok := '+self.call(self.lookup[child.type_name.casefold()], 'Write', '#Module.'+child.name+'.', Access='#Access', Request='#Request', RootIndex='#RootIndex', RootReady='#RootReady', Matched='#Matched')+';',
                     '    IF #Matched THEN #'+name(t, 'Write')+' := #Ok; RETURN; END_IF;']
        return self.render(t, 'Write', ['Request : "ST_HmiRequest";', 'Access : "FRK_Access";', 'RootIndex : Int;', 'RootReady : Bool;'],
                        ['Module : "'+t.name+'";', 'Matched : Bool;'], ['Ok : Bool;', 'Code : String[64];', 'Inactive : Bool;', 'Text : WString[255];'], body, 'Bool')

    def recipe(self, t):
        body = ['    #'+name(t, 'Recipe')+' := TRUE;']
        fields = [(i, f) for i, f in enumerate(self.fields[t.name], 1) if f.member.startswith('ParCfg.')]
        if fields:
            body += ['    IF #Phase = 1 THEN', '        #Module.ConfigStaged := FALSE;',
                     '        #Module.ConfigStageParCfg := #Module.ConfigDefaultParCfg;']
            for index, f in fields:
                body += ['        "'+name(t, 'Def')+'"(FieldIndex := %d);'%index,
                         '        #Ok := "FRK_ConfigGet"(Scope := #Module.Status.Name, ModelCode := #ModelCode);',
                         '        IF NOT #Ok THEN #RejectScope := #Module.Status.Name; #RejectKey := "FRK_ConfigScratch".Entry.WriteKey; #'+name(t, 'Recipe')+' := FALSE; RETURN; END_IF;',
                         assign_value(f, '#Module.ConfigStage'+f.member)]
            body += ['        #Module.ConfigStaged := TRUE;', '    ELSIF #Phase = 2 THEN',
                     '        #Module.ParCfg := #Module.ConfigStageParCfg;', '        #Module.ConfigStaged := FALSE;',
                     '    ELSE #Module.ConfigStaged := FALSE;', '    END_IF;']
        for child in t.children:
            body += ['    #Ok := '+self.call(self.lookup[child.type_name.casefold()], 'Recipe', '#Module.'+child.name+'.', ModelCode='#ModelCode', Phase='#Phase', RejectScope='#RejectScope', RejectKey='#RejectKey')+';',
                     '    IF NOT #Ok THEN #'+name(t, 'Recipe')+' := FALSE; RETURN; END_IF;']
        return self.render(t, 'Recipe', ['ModelCode : String;', 'Phase : Int;'],
                        ['Module : "'+t.name+'";', 'RejectScope : String;', 'RejectKey : String;'], ['Ok : Bool;'], body, 'Bool')

    def sources(self):
        from fraktal_tia_generate import db
        def udt(n, fields):
            return type_source(n, [{'member': k, 'native_type': v, 'accessible': False, 'initial': ''} for k, v in fields])
        decimal_limbs = math.ceil((self.value_width + DECIMAL_EXPONENT_LIMIT) * math.log2(10) / 16) + 2
        sources = {
            '02_FRK_ConfigInteger.udt': udt('FRK_ConfigInteger', [('Used', 'Int'), ('Limbs', 'Array[0..%d] of UDInt' % (decimal_limbs - 1))]),
            '02_FRK_ConfigSlot.udt': udt('FRK_ConfigSlot', [('SchemaVersion', 'UInt'), ('Used', 'Bool'), ('ModelCode', 'String[%d]'%self.model_width), ('Record', '"ST_ConfigRecord"')]),
            '02_FRK_ConfigValue.udt': udt('FRK_ConfigValue', [('Number', 'LInt'), ('Decimal', 'LReal'), ('Flag', 'Bool'), ('Text', 'String[%d]'%self.value_width)]),
        }
        root_count = len(self.model.roots)
        declarations = [
            'SchemaVersion'+PRIVATE+' : UInt;',
            'Rows'+PRIVATE+' : Array[1..%d] of "FRK_ConfigSlot";'%self.capacity,
            'ActiveModels'+PRIVATE+' : Array[1..%d] of String[%d];'%(root_count, self.model_width),
            'Lost'+PRIVATE+' : Array[1..%d] of Bool;'%root_count,
            'Acknowledged'+PRIVATE+' : Array[1..%d] of Bool;'%root_count,
            'LostPath'+PRIVATE+' : Array[1..%d] of String[%d];'%(root_count, self.scope_width),
        ]
        sources['05_FRK_ConfigStore.db'] = db('FRK_ConfigStore', declarations).replace('VAR\n', 'VAR RETAIN\n', 1)
        sources['05_FRK_ConfigRuntime.db'] = db('FRK_ConfigRuntime', [
            'Fresh'+PRIVATE+' : Bool;', 'Unavailable'+PRIVATE+' : Bool;',
            'Failed'+PRIVATE+' : Array[1..%d] of Bool;'%root_count,
            'LossSlot'+PRIVATE+' : Array[1..%d] of Int;'%root_count,
        ])
        sources['05_FRK_ConfigScratch.db'] = db('FRK_ConfigScratch', [
            'Entry'+PRIVATE+' : "ST_ConfigEntry";', 'Blank'+PRIVATE+' : "ST_ConfigEntry";',
            'Value'+PRIVATE+' : "FRK_ConfigValue";',
            'EnumCount'+PRIVATE+' : Int;',
            'EnumValues'+PRIVATE+' : Array[1..%d] of DInt;'%max(1, max((len(f.enum_values) for fs in [*self.fields.values(), self.line.fields if self.line else ()] for f in fs), default=0)),
            *[k+PRIVATE+' : '+v+';' for k, v in (
                ('Storage', 'DInt'), ('Schema', 'UInt'), ('Minimum', 'LReal'), ('Maximum', 'LReal'),
                ('MaxLength', 'Int'), ('MinRead', 'DInt'), ('MinWrite', 'DInt'), ('CommittedText','WString[255]'),('CommittedScope','String[80]'),
                ('RejectReason','DInt'),('RejectDescription','WString[255]'),('AccessRejected','Bool'),('RequiredLevel','DInt'),('RejectedScope','String[80]'),('RejectedKey','String[160]'))],
        ])
        text = DECIMAL_TEMPLATE.read_text('ascii') + '\n' + TEMPLATE.read_text('ascii')
        text = text.replace('#Persist.StorePresent := FALSE;', '#Persist.StorePresent := '+str(bool(self.sets)).upper()+';')
        substitutions = {'POOL_CAPACITY': self.capacity, 'ROOT_COUNT': root_count, 'SCOPE_WIDTH': self.scope_width, 'VALUE_WIDTH': self.value_width,
                         'DECIMAL_LIMBS': decimal_limbs,
                         'DECIMAL_EXPONENT_LIMIT': DECIMAL_EXPONENT_LIMIT, **self.catalog.capacities}
        for enum, members in self.catalog.enums.items():
            for member, value in members.items():
                text = text.replace('@'+enum+'.'+member+'@', str(value))
        for key, value in substitutions.items():
            text = text.replace('@'+key+'@', str(value))
        if '@' in text:
            raise ValueError('unresolved config service token')
        root_body = ['    #FRK_ConfigRoot := 0;', '    CASE #RegIndex OF']
        root_body += ['        %d: #FRK_ConfigRoot := %d;'%(i, n) for i, n in self.root_map.items()]
        root_body += ['        ELSE RETURN;', '    END_CASE;']
        text += function('FRK_ConfigRoot', ['RegIndex : DInt;'], [], [], root_body, 'Int')
        body = ['    #FRK_ConfigModelCode := \'\';', '    IF #RootIndex < 1 OR #RootIndex > %d THEN RETURN; END_IF;'%root_count,
                '    IF #ModelIndex = 0 THEN #FRK_ConfigModelCode := "FRK_ConfigStore".ActiveModels[#RootIndex]; RETURN; END_IF;', '    CASE #ModelIndex OF']
        body += ['        %d: #FRK_ConfigModelCode := %s;'%(i, literal(code)) for i, code in enumerate(self.models, 1)]
        body += ['        ELSE RETURN;', '    END_CASE;']
        text += function('FRK_ConfigModelCode', ['RootIndex : Int;', 'ModelIndex : UDInt;'], [], [], body, 'String')
        body = ['    IF NOT #Startup THEN RETURN; END_IF;',
                '    "FRK_ConfigRuntime".Fresh := "FRK_ConfigStore".SchemaVersion = 0;',
                '    IF "FRK_ConfigStore".SchemaVersion <> 1 THEN',
                '        FOR #Index := 1 TO %d DO "FRK_ConfigStore".Rows[#Index].Used := FALSE; END_FOR;'%self.capacity]
        for index, root in enumerate(self.model.roots, 1):
            body += ['        IF NOT "FRK_ConfigRuntime".Fresh THEN "FRK_ConfigLoss"(RootIndex := %d, Scope := %s); END_IF;'%(index, literal(root.name)),
                     '        "FRK_ConfigStore".ActiveModels[%d] := %s;'%(index, literal(self.model.initial_model))]
        body += ['        "FRK_ConfigStore".SchemaVersion := 1;', '    END_IF;']
        for index, root in enumerate(self.model.roots, 1):
            condition = ' AND '.join('"FRK_ConfigStore".ActiveModels[%d] <> %s'%(index, literal(code)) for code in self.models)
            body += ['    IF '+condition+' THEN',
                     '        "FRK_ConfigStore".ActiveModels[%d] := %s;'%(index, literal(self.model.initial_model)),
                     '        "FRK_ConfigLoss"(RootIndex := %d, Scope := %s);'%(index, literal(root.name)), '    END_IF;']
        text += function('FRK_ConfigBoot', ['Startup : Bool;'], [], ['Index : Int;'], body)
        sources['14_ConfigServices.scl'] = text
        if self.sets:
            sources.update(self.sets.sources())
        if self.line:
            sources.update(self.line.production_sources())
        return sources

    def operations(self, t):
        """Root mailbox owns writes, atomic model publication and restore acknowledgment."""
        from fraktal_tia_generate import config_name
        fields = []
        body = ['    #RootIndex := "FRK_ConfigRoot"(RegIndex := #Module.Core.RegIndex);',
                '    IF #Module.Core.ParentIndex <> 0 OR #RootIndex = 0 THEN RETURN; END_IF;',
                '    #Module.Model.ModelCode := "FRK_ConfigStore".ActiveModels[#RootIndex];',
                '    IF NOT #Module.Unit.RequestPending THEN RETURN; END_IF;',
                '    #Request := #Module.Unit.Request;',
                '    #Ready := #Module.Core.Exec = %d AND NOT #Module.Unit.ModePending AND NOT #Module.Unit.Clearing AND "FRK_DescendantsReady"(OwnerIndex := #Module.Core.RegIndex);'%self.catalog.enums['E_ExecState']['READY'],
                '    CASE #Request.Kind OF']
        kinds = self.catalog.enums['E_HmiRequestKind']
        body += ['        %d:'%kinds['QUERY_CONFIG'],
                 '            "FRK_ConfigBegin"(Cursor := #Module.ConfigCursor, Page := #Module.HmiResponse.ConfigPage, PageIndex := #Request.IntValue, Revision := #Module.ConfigRev);',
                 '            #Module.HmiResponse.Accepted := FALSE;',
                 '            #Module.HmiResponse.Diagnostic := WSTRING#\'std.error.modelNotAvailable\';',
                 '            IF #Request.DurationMs <= %d AND #Request.IntValue >= 0 AND #Request.IntValue <= 32767 THEN'%len(self.model.model_config),
                 '                '+self.call(t, 'Read', '#Module.', Access='#Module.Access', RootIndex='#RootIndex', ModelIndex='#Request.DurationMs', Cursor='#Module.ConfigCursor', Page='#Module.HmiResponse.ConfigPage')+';',
                 '                "FRK_ConfigFinish"(Cursor := #Module.ConfigCursor, Page := #Module.HmiResponse.ConfigPage);',
                 '                #Module.HmiResponse.Accepted := TRUE; #Module.HmiResponse.Diagnostic := WSTRING#\'\';', '            END_IF;']
        body += ['        %d:'%kinds['WRITE_CONFIG'],
                 '            #Module.HmiResponse.Accepted := FALSE;',
                 '            "FRK_ConfigScratch".RejectDescription := WSTRING#\'std.error.recipeSchemaInvalid\';',
                 '            "FRK_ConfigScratch".RejectReason := %d;'%self.catalog.enums['E_Reason']['RECIPE_INVALID'],
                 '            "FRK_ConfigScratch".CommittedScope := #Module.Status.Name;',
                 '            #Module.HmiResponse.Diagnostic := "FRK_ConfigScratch".RejectDescription;',
                 '            #Module.ConfigPersist.LastRejectScope := #Module.Status.Name;',
                 '            #Module.ConfigPersist.LastRejectKey := #Request.NameValue;',
                 '            #Module.HmiResponse.Report.Count := 0; #Module.HmiResponse.Report.Released := TRUE;',
                 '            IF #Request.Kind = %d THEN'%kinds['CAPTURE_CONFIG'],
                 '                "FRK_ManualCommon"(Core := #Module.Core, Unit := #Module.Unit, Status := #Module.Status, Report := #Module.HmiResponse.Report);',
                 '                #Ready := #Ready AND #Module.HmiResponse.Report.Released AND #Request.DurationMs = 0;',
                 '                IF NOT #Ready THEN',
                 '                    #Module.HmiResponse.Diagnostic := WSTRING#\'std.release.unitNotReady\';',
                 '                    IF #Module.HmiResponse.Report.Count = 0 THEN "FRK_ReleaseReason"(Report := #Module.HmiResponse.Report, Description := #Module.HmiResponse.Diagnostic, Reason := %d, Path := STRING_TO_WSTRING(#Module.Status.Name), Kind := %d); END_IF;'%(self.catalog.enums['E_Reason']['PERMISSIVE_NOT_MET'],self.catalog.enums['E_ReleaseKind']['OTHER']),
                 '                    RETURN; END_IF;', '            END_IF;',
                 '            IF #Request.DurationMs <= %d THEN'%len(self.model.model_config),
                 '                #Matched := FALSE;',
                 '                #Module.HmiResponse.Accepted := '+self.call(t, 'Write', '#Module.', Access='#Module.Access', Request='#Request', RootIndex='#RootIndex', RootReady='#Ready', Matched='#Matched')+';',
                 '            END_IF;',
                 '            IF #Module.HmiResponse.Accepted THEN',
                 '                "FRK_ConfigWriteAudit"(Scope := "FRK_ConfigScratch".CommittedScope, Key := #Request.NameValue, Value := "FRK_ConfigScratch".CommittedText, Captured := #Request.Kind = %d, User := #Module.Unit.RequestUser, AlarmLog := #Module.AlarmLog);'%kinds['CAPTURE_CONFIG'],
                 '                #Module.ConfigRev := "FRK_ConfigRevision"(Previous := #Module.ConfigRev);',
                 '                #Module.HmiResponse.Diagnostic := WSTRING#\'\';',
                 '                #Module.ConfigPersist.LastRejectScope := \'\'; #Module.ConfigPersist.LastRejectKey := \'\';',
                 '            ELSE',
                 '                #Module.ConfigPersist.LastRejectScope := "FRK_ConfigScratch".CommittedScope;',
                 '                #Module.HmiResponse.Diagnostic := "FRK_ConfigScratch".RejectDescription;',
                 '                "FRK_ReleaseReason"(Report := #Module.HmiResponse.Report, Description := #Module.HmiResponse.Diagnostic, Reason := "FRK_ConfigScratch".RejectReason, Path := STRING_TO_WSTRING("FRK_ConfigScratch".CommittedScope), Kind := %d);'%self.catalog.enums['E_ReleaseKind']['OTHER'],
                 '            END_IF;']
        if self.model.line and self.model.line.role == 'MIRROR':
            body.insert(body.index('            #Module.HmiResponse.Accepted := FALSE;', body.index('        %d:'%kinds['WRITE_CONFIG']))+1, '            #Matched := FALSE;')
            body += ['            IF #Matched AND LEFT(IN := #Request.NameValue, L := 5) = \'line.\' AND NOT #Module.HmiResponse.Accepted THEN',
                     '                #Module.ConfigPersist.LastRejectScope := '+literal(self.model.line.owner)+';', '            END_IF;']
        if self.model.model_config:
            body += ['        %d:'%kinds['SET_MODEL'],
                     '            #Module.HmiResponse.Accepted := FALSE;',
                     '            #Module.HmiResponse.Diagnostic := WSTRING#\'std.error.modelNotAvailable\';',
                     '            #Desired := \'\';']
            for code in self.models:
                body += ['            IF #Request.TextValue = WSTRING#'+literal(code)+' THEN #Desired := '+literal(code)+'; END_IF;']
            body += ['            "FRK_UnitRelease"(Core := #Module.Core, Unit := #Module.Unit, Status := #Module.Status, Policy := #Module.ModePolicy, Access := #Module.Access, Supported := #Module.SupportedModesPublished, Report := #Module.HmiResponse.Report, Gate := %d, Desired := -1, Trusted := FALSE);'%self.catalog.enums['E_GatedAction']['CHANGEOVER'],
                     '            IF #Desired <> \'\' AND #Module.HmiResponse.Report.Released THEN',
                     '                #Scope := \'\'; #Key := \'\';',
                     '                #Ok := '+self.call(t, 'Recipe', '#Module.', ModelCode='#Desired', Phase='1', RejectScope='#Scope', RejectKey='#Key')+';',
                     '                IF #Ok THEN',
                     '                    #Ok := '+self.call(t, 'Recipe', '#Module.', ModelCode='#Desired', Phase='2', RejectScope='#Scope', RejectKey='#Key')+';',
                     '                    "FRK_ConfigStore".ActiveModels[#RootIndex] := #Desired;',
                     '                    #Module.Model.ModelCode := #Desired;',
                     '                    #Module.ConfigRev := "FRK_ConfigRevision"(Previous := #Module.ConfigRev);',
                     '                    #Module.HmiResponse.Accepted := TRUE; #Module.HmiResponse.Diagnostic := WSTRING#\'\';',
                     '                ELSE',
                     '                    #Module.ConfigPersist.LastRejectScope := #Scope; #Module.ConfigPersist.LastRejectKey := #Key;',
                     '                    #Ok := '+self.call(t, 'Recipe', '#Module.', ModelCode='#Desired', Phase='0', RejectScope='#Scope', RejectKey='#Key')+';',
                     '                    #Module.HmiResponse.Diagnostic := WSTRING#\'std.error.recipeSchemaInvalid\';',
                     '                    "FRK_Fault"(Core := #Module.Core, Status := #Module.Status, ReasonCode := %d, Description := #Module.HmiResponse.Diagnostic);'%self.catalog.enums['E_Reason']['RECIPE_INVALID'],
                     '                    #Module.Status.Diagnostic.SourcePath := STRING_TO_WSTRING(#Scope);',
                     '                END_IF;', '            END_IF;']
        body += ['        %d:'%kinds['ACK_CONFIG_RESTORE'],
                 '            #Module.HmiResponse.Accepted := #Module.Access.CurrentLevel >= %d;'%self.catalog.enums['E_AccessLevel']['ENGINEER'],
                 '            IF #Module.HmiResponse.Accepted THEN "FRK_ConfigStore".Acknowledged[#RootIndex] := TRUE;',
                 '            ELSE #Module.HmiResponse.Diagnostic := WSTRING#\'std.error.configRestoreAckRefused\'; END_IF;',
                 '        ELSE RETURN;', '    END_CASE;']
        body=[line.replace('        %d:'%kinds['WRITE_CONFIG'],'        %d, %d:'%(kinds['WRITE_CONFIG'],kinds['CAPTURE_CONFIG'])) for line in body]
        return self.render(t, 'Operation', [], ['Module : "'+t.name+'";'],
                        ['RootIndex : Int;', 'Request : "ST_HmiRequest";', 'Ready : Bool;', 'Matched : Bool;', 'Ok : Bool;',
                         'Desired : String[64];', 'Scope : String[80];', 'Key : String[160];'], body)
