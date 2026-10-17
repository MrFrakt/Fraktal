"""Core 3.8d class policy; native UMAC does not own per-root value thresholds."""
from pathlib import Path
from fraktal_tia_binding import PRIVATE, READONLY, literal, type_source
from fraktal_tia_config import function, width

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/data_classes.scl.in'


def effective_level(for_write):
    return ('"FRK_DataLevel"(Access := #Access, ClassId := "FRK_ConfigScratch".Entry.ClassId, Minimum := '
            +'"FRK_ConfigScratch".'+('MinWrite' if for_write else 'MinRead')+', ForWrite := '+str(for_write).upper()+')')


def validate_classes(value, roots, types, catalog):
    from fraktal_tia_declaration import DeclarationError, object_fields, items
    lookup = {t.name.casefold(): t for t in types}
    eligible = {r.name for r in roots if lookup[r.type_name.casefold()].unit_modes}
    if not isinstance(value, dict) or set(value) - eligible:
        raise DeclarationError('T-GEN', 'data_classes', 'class policies select deployed root Units')
    result = []
    for scope, definitions in value.items():
        rows = items(definitions, 'data_classes.'+scope)
        if not 1 <= len(rows) <= catalog.capacities['MAX_DATA_CLASSES']:
            raise DeclarationError('T-WIDTH', scope, 'data class count exceeds Core capacity or is empty')
        names = set()
        for row in rows:
            object_fields(row, ('id', 'label', 'read_level', 'write_level'), (), scope+'.data_classes')
            for key, member in (('id', 'ClassId'), ('label', 'LabelKey')):
                v = row[key]
                if not isinstance(v, str) or not v.isascii() or not 1 <= len(v) <= width(catalog, 'ST_DataClassPolicy', member) or any(ord(c) < 32 for c in v):
                    raise DeclarationError('T-WIDTH', scope, 'class identity/label exceeds its Core bound')
            if row['id'] in names:
                raise DeclarationError('T-GEN', scope, 'class identities must be unique')
            names.add(row['id'])
            for key in ('read_level', 'write_level'):
                if type(row[key]) is not int or row[key] not in catalog.enums['E_AccessLevel'].values():
                    raise DeclarationError('T-GEN', scope, 'class thresholds must be Core access levels')
        result.append((scope, tuple(tuple(r.items()) for r in rows)))
    return tuple(result)


def image_fields(catalog):
    return [('SchemaVersion','UInt'), ('Scope','String[80]'), ('Generation','UDInt'),
            ('Count','Int'), ('Rows','Array[1..%d] of "ST_DataClassPolicy"'%catalog.capacities['MAX_DATA_CLASSES']), ('Checksum','DWord')]


def build(model, catalog, sources):
    """One effective-level resolver also covers legacy deployments without classes."""
    count = catalog.capacities['MAX_DATA_CLASSES']
    active = bool(model.data_classes)
    body = ['    #FRK_DataLevel := %d;'%catalog.enums['E_AccessLevel']['ADMIN'],
            '    IF #Minimum < 0 OR #Minimum > %d THEN RETURN; END_IF;'%catalog.enums['E_AccessLevel']['ADMIN'],
            '    #Required := #Access.Policy.Required[0];',
            '    IF #ForWrite THEN #Required := #Access.Policy.Required[1]; END_IF;',
            '    IF #ClassId <> \'\' THEN']
    if active:
        body += ['        #Required := %d;'%catalog.enums['E_AccessLevel']['ADMIN'],
                 '        IF #Access.ClassesLost OR #Access.ClassCount < 0 OR #Access.ClassCount > %d THEN RETURN; END_IF;'%count,
                 '        FOR #Index := 1 TO #Access.ClassCount DO',
                 '            IF #Access.Classes[#Index].ClassId = #ClassId THEN',
                 '                #Required := #Access.Classes[#Index].ReadLevel;',
                 '                IF #ForWrite THEN #Required := #Access.Classes[#Index].WriteLevel; END_IF;',
                 '                EXIT;', '            END_IF;', '        END_FOR;']
    else:
        body += ['        RETURN;']
    body += ['    END_IF;', '    IF #Required < 0 OR #Required > %d THEN RETURN; END_IF;'%catalog.enums['E_AccessLevel']['ADMIN'],
             '    #FRK_DataLevel := MAX(IN1 := #Required, IN2 := #Minimum);']
    text = function('FRK_DataLevel', ['Access : "FRK_Access";', 'ClassId : String;', 'Minimum : DInt;', 'ForWrite : Bool;'], [], ['Required : DInt;', 'Index : Int;'], body, 'DInt')
    text += function('FRK_DataPolicyReady', ['Access : "FRK_Access";'], [], [],
                     ['    #FRK_DataPolicyReady := NOT #Access.PolicyLost'+(' AND NOT #Access.ClassesLost' if active else '')+';'], 'Bool')
    if not active:
        return text
    from fraktal_tia_generate import db
    sources['02_FRK_ClassPolicyImage.udt'] = type_source('FRK_ClassPolicyImage', [dict(member=n,native_type=t,accessible=False,initial='') for n,t in image_fields(catalog)])
    sources['05_FRK_ClassPolicies.db'] = db('FRK_ClassPolicies', ['Rows'+PRIVATE+' : Array[1..%d] of "FRK_ClassPolicyImage";'%len(model.roots)]).replace('VAR\n','VAR RETAIN\n',1)
    sources['05_FRK_ClassScratch.db'] = db('FRK_ClassScratch', ['Blank'+PRIVATE+' : "ST_DataClassPolicy";'])
    p = '02_FRK_Access.udt'
    s = sources[p]
    assert s.count('END_STRUCT') == 1
    extra = '    ClassCount'+READONLY+' : Int;\n    Classes'+READONLY+' : Array[1..%d] of "ST_DataClassPolicy";\n'%count
    s = s.replace('END_STRUCT', extra+'    ClassSlot'+PRIVATE+' : Int;\n    ClassesLost'+PRIVATE+' : Bool;\nEND_STRUCT')
    sources[p] = s
    defaults = ['    #Slot := 0; #Access.ClassCount := 0;']
    for slot, root in enumerate(model.roots,1):
        rows = dict(model.data_classes).get(root.name, ())
        if not rows: continue
        defaults += ['    IF #Scope = '+literal(root.name)+' THEN', '        #Slot := %d; #Access.ClassCount := %d;'%(slot,len(rows))]
        for i, row in enumerate(rows,1):
            row = dict(row)
            for member,key in (('ClassId','id'),('LabelKey','label'),('ReadLevel','read_level'),('WriteLevel','write_level')):
                defaults += ['        #Access.Classes[%d].%s := %s;'%(i,member,literal(row[key]) if key in ('id','label') else str(row[key]))]
        defaults += ['    END_IF;']
    text += TEMPLATE.read_text('ascii').replace('@CLASS_COUNT@',str(count)).replace('@ROOT_COUNT@',str(len(model.roots)))
    for enum,members in catalog.enums.items():
        for member,value in members.items(): text = text.replace('@'+enum+'.'+member+'@',str(value))
    assert text.count('@DEFAULTS@')==1
    assert '@' not in text.replace('@DEFAULTS@','')
    return text.replace('@DEFAULTS@','\n'.join(defaults))


def adapt(model, sources):
    if not model.data_classes:
        return
    boot = '    "FRK_AccessPolicyBoot"(Access := #Access, Startup := #Startup, Root := #Core.ParentIndex = 0, Scope := #Status.Name);'
    persist = '    "FRK_AccessPersist"(Access := #Access, Unit := #Unit, Response := #HmiResponse, SourcePath := STRING_TO_WSTRING(#Status.Name), AlarmLog := #AlarmLog);'
    for name, text in list(sources.items()):
        if boot in text:
            text = text.replace('#Access.PolicyLost', '(#Access.PolicyLost OR #Access.ClassesLost)')
            text = text.replace(boot, boot+'\n    "FRK_ClassBoot"(Access := #Access, Startup := #Startup, Root := #Core.ParentIndex = 0, Scope := #Status.Name);')
            text = text.replace(persist, '    "FRK_ClassOperation"(Access := #Access, Unit := #Unit, Response := #HmiResponse, Scope := #Status.Name);\n'+persist)
        if 'FUNCTION "FRK_AccessPersist"' in text:
            first = text.index('FUNCTION "FRK_AccessPersist"')
            end = text.index('END_FUNCTION',first)
            section = text[first:end]
            section = section.replace('AND #Access.PolicyLost THEN', 'AND (#Access.PolicyLost OR #Access.ClassesLost) THEN')
            section = section.replace('            "FRK_AccessPolicySave"(Access := #Access, Scope := WSTRING_TO_STRING(#SourcePath));',
                '            IF #Access.PolicyLost THEN "FRK_AccessPolicySave"(Access := #Access, Scope := WSTRING_TO_STRING(#SourcePath)); END_IF;\n'
                '            IF #Access.ClassesLost THEN "FRK_ClassSave"(Access := #Access, Scope := WSTRING_TO_STRING(#SourcePath)); END_IF;')
            section = section.replace('#Access.PolicyLost := FALSE;', '#Access.PolicyLost := FALSE; #Access.ClassesLost := FALSE;')
            section = section.replace('IF #Access.PolicyLost AND', 'IF (#Access.PolicyLost OR #Access.ClassesLost) AND')
            section = section.replace('ELSIF NOT #Access.PolicyLost AND #Access.PolicyLossAlarm', 'ELSIF NOT #Access.PolicyLost AND NOT #Access.ClassesLost AND #Access.PolicyLossAlarm')
            text = text[:first]+section+text[end:]
        sources[name] = text
