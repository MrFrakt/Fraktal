"""PLC-owned named sets over the authoritative typed config definitions."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from fraktal_tia_binding import PRIVATE, READONLY, REPO, literal, type_source
from fraktal_tia_config import function, name, assign_value, read_value

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/config_set_services.scl.in'
LINE_AUTHORITY = REPO / 'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Platform/FB_ConfigSetJson.TcPOU'
LINE_WIDTH = int(re.search(r'LINE_MAX\s*:\s*INT\s*:=\s*(\d+)', ET.fromstring(LINE_AUTHORITY.read_bytes()).findtext('.//Declaration'))[1])


class Sets:
    def __init__(self, layout):
        self.layout = layout
        self.capacity = layout.model.config_set_capacity
        counts = {}
        for instance in layout.model.instances:
            for field in layout.fields[instance.type_name]:
                key = (layout.root_map[instance.index], field.kind)
                counts[key] = counts.get(key, 0) + 1
        if layout.line:
            counts['line'] = len(layout.line.fields)
        self.records = min(max(counts.values(), default=1), layout.catalog.capacities['MAX_SET_RECORDS'])

    def declarations(self, t):
        if t.name not in self.layout.roots:
            return []
        return ['    ConfigSets'+READONLY+' : Array[1..%d] of "ST_ConfigSetInfo";' % self.capacity,
                '    ConfigSetCount'+READONLY+' : Int;',
                '    ConfigSetDocument'+READONLY+' : WString[%d];' % LINE_WIDTH,
                '    ConfigSetDocumentLine'+READONLY+' : Int;',
                '    ConfigSetDocumentLines'+READONLY+' : Int;']

    def walk(self, t):
        layout = self.layout
        model_kind = layout.catalog.enums['E_ConfigKind']['PAR_CFG']
        body = ['    #'+name(t, 'SetWalk')+' := FALSE;']
        if t.name in layout.line_types:
            body += ['    IF "FRK_SetRuntime".Work[#RootIndex].Payload.Info.Kind = %d THEN'%layout.catalog.enums['E_ConfigKind']['LINE_CFG'],
                     '        #'+name(t, 'SetWalk')+' := "FRK_LineSetWalk"(RootIndex := #RootIndex, Scope := #Module.Status.Name, Phase := #Phase, Access := #Access, Ready := #Ready);',
                     '        RETURN;', '    END_IF;']
        roles = {f.member.split('.')[0] for f in layout.fields[t.name]}
        for role in sorted(roles):
            body += ['    IF #Phase = 1 THEN #Module.ConfigStage%s := #Module.%s; END_IF;' % (role, role)]
        for index, field in enumerate(layout.fields[t.name], 1):
            body += ['    IF "FRK_SetRuntime".Work[#RootIndex].Payload.Info.Kind = %d THEN' % field.kind,
                     '        "'+name(t, 'Def')+'"(FieldIndex := %d);' % index,
                     '        "FRK_SetRuntime".Work[#RootIndex].RejectScope := #Module.Status.Name;',
                     '        "FRK_SetRuntime".Work[#RootIndex].RejectKey := "FRK_ConfigScratch".Entry.WriteKey;',
                     '        IF #Phase = 0 OR #Phase = 5 THEN',
                     '            IF #Phase = 5 AND NOT "FRK_ConfigDataAllowed"(Access := #Access, ForWrite := FALSE, Scope := #Module.Status.Name) THEN RETURN; END_IF;',
                     '            IF #Phase = 5 AND (%d <> %d OR "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode = "FRK_ConfigStore".ActiveModels[#RootIndex]) THEN'%(field.kind, model_kind),
                     *read_value(field), '                #Ok := "FRK_ConfigValidate"(Text := "FRK_ConfigScratch".Entry.ValueText);',
                     '            ELSE',
                     '                #Ok := "FRK_ConfigGet"(Scope := #Module.Status.Name, ModelCode := "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode);',
                     '            END_IF;',
                     '            IF NOT #Ok OR "FRK_SetRuntime".Work[#RootIndex].Payload.Info.RecordCount >= %d THEN RETURN; END_IF;' % self.records,
                     '            #Slot := "FRK_SetRuntime".Work[#RootIndex].Payload.Info.RecordCount + 1;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].Scope := #Module.Status.Name;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].WriteKey := "FRK_ConfigScratch".Entry.WriteKey;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].Revision := "FRK_ConfigScratch".Entry.WriteRevision;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].Kind := "FRK_ConfigScratch".Entry.ConfigKind;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].ValueType := "FRK_ConfigScratch".Entry.ValueType;',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot].ValueText := WSTRING_TO_STRING("FRK_ConfigScratch".Entry.ValueText);',
                     '            "FRK_SetRuntime".Work[#RootIndex].Payload.Info.RecordCount := #Slot;',
                     '        ELSIF #Phase = 2 THEN',
                     '            #Slot := "FRK_SetRecord"(RootIndex := #RootIndex, Scope := #Module.Status.Name, WriteKey := "FRK_ConfigScratch".Entry.WriteKey);',
                     '            #Stored := "FRK_SetRuntime".Work[#RootIndex].Targets[#Slot];',
                     '            "FRK_ConfigCommit"(SlotIndex := #Stored, ModelCode := "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode, Schema := "FRK_ConfigScratch".Schema, Record := "FRK_SetRuntime".Work[#RootIndex].Payload.Records[#Slot]);',
                     '        ELSE',
                     '            #Slot := "FRK_SetCheck"(RootIndex := #RootIndex, Scope := #Module.Status.Name, Access := #Access, Ready := #Ready, WriteAccess := #Phase <> 3, ReserveTarget := #Phase = 1);',
                     '            IF #Slot = 0 THEN RETURN; END_IF;',
                     '            IF #Phase = 1 THEN', assign_value(field, '#Module.ConfigStage'+field.member),
                     '            END_IF;', '        END_IF;', '    END_IF;']
        for role in sorted(roles):
            kind = 0 if role == 'ParCfg' else 1
            body += ['    IF #Phase = 2 AND "FRK_SetRuntime".Work[#RootIndex].Payload.Info.Kind = %d THEN #Module.%s := #Module.ConfigStage%s; END_IF;' % (kind, role, role)]
        for child in t.children:
            body += ['    #Ok := '+layout.call(layout.lookup[child.type_name.casefold()], 'SetWalk', '#Module.'+child.name+'.',
                     RootIndex='#RootIndex', Phase='#Phase', Access='#Access', Ready='#Ready')+';',
                     '    IF NOT #Ok THEN RETURN; END_IF;']
        body += ['    #'+name(t, 'SetWalk')+' := TRUE;']
        return layout.render(t, 'SetWalk', ['RootIndex : Int;', 'Phase : Int;', 'Access : "FRK_Access";', 'Ready : Bool;'],
                             ['Module : "'+t.name+'";'], ['Slot : Int;', 'Stored : Int;', 'Ok : Bool;'], body, 'Bool')

    def sources(self):
        from fraktal_tia_generate import db
        def udt(n, fields):
            return type_source(n, [{'member': k, 'native_type': v, 'accessible': False, 'initial': ''} for k, v in fields])
        roots = len(self.layout.model.roots)
        sources = {
            '02_FRK_SetPayload.udt': udt('FRK_SetPayload', [('Info', '"ST_ConfigSetInfo"'), ('Records', 'Array[1..%d] of "ST_ConfigRecord"' % self.records)]),
            '02_FRK_JsonField.udt': udt('FRK_JsonField', [('Key', 'String[16]'), ('Text', 'WString[160]'), ('Quoted', 'Bool')]),
            '02_FRK_SetWorkspace.udt': udt('FRK_SetWorkspace', [
                ('Payload', '"FRK_SetPayload"'), ('Seen', 'Array[1..%d] of Bool' % self.records), ('Matched', 'Int'), ('RejectScope', 'String[80]'), ('RejectKey', 'String[160]'),
                ('Targets', 'Array[1..%d] of Int'%self.layout.catalog.capacities['MAX_SET_RECORDS']),
                ('Schemas', 'Array[1..%d] of UInt'%self.layout.catalog.capacities['MAX_SET_RECORDS']),
                ('Importing', 'Bool'), ('Exporting', 'Bool'), ('NextLine', 'Int'), ('Generation', 'UDInt'), ('Received', 'Int'),
                ('CurrentExport', 'Bool'), ('ExportToken', 'String[32]'),
                ('Piece', 'WString[%d]' % LINE_WIDTH), ('Line', 'WString[%d]' % LINE_WIDTH),
                ('Fields', 'Array[1..9] of "FRK_JsonField"'), ('FieldCount', 'Int')]),
            '05_FRK_SetStore.db': db('FRK_SetStore', ['SchemaVersion'+PRIVATE+' : UInt;',
                'Sets'+PRIVATE+' : Array[1..%d, 1..%d] of "FRK_SetPayload";' % (roots, self.capacity)]).replace('VAR\n', 'VAR RETAIN\n', 1),
            '05_FRK_SetRuntime.db': db('FRK_SetRuntime', ['Work'+PRIVATE+' : Array[1..%d] of "FRK_SetWorkspace";' % roots]),
        }
        text = TEMPLATE.read_text('ascii')
        slot_guard = '\n'.join([
            '    IF #ReserveTarget THEN',
            '        #TargetSlot := "FRK_ConfigReserve"(Scope := #Scope, Key := "FRK_ConfigScratch".Entry.WriteKey, ModelCode := "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode, Reserved := "FRK_SetRuntime".Work[#RootIndex].Targets);',
            '        IF #TargetSlot < 1 OR #TargetSlot > %d THEN RETURN; END_IF;'%self.layout.capacity,
            '        "FRK_SetRuntime".Work[#RootIndex].Targets[#Index] := #TargetSlot;', '    END_IF;'])
        line_shape = ''
        if self.layout.line:
            line_kind = self.layout.catalog.enums['E_ConfigKind']['LINE_CFG']
            slot_guard = slot_guard.replace('IF #ReserveTarget THEN', 'IF #ReserveTarget AND "FRK_ConfigScratch".Entry.ConfigKind <> %d THEN'%line_kind)
            line_shape = ('    ELSIF "FRK_SetRuntime".Work[#RootIndex].Payload.Info.Kind = %d THEN\n'%line_kind
                          +'        IF "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode <> \'\' THEN RETURN; END_IF;\n')
            sources.update(self.layout.line.set_sources(self.records))
        text = text.replace('@SET_SLOT_GUARD@', slot_guard).replace('@LINE_SET_SHAPE@', line_shape)
        if self.layout.runtime_models:
            # A typed complete set may be a recovery/clone source whose old
            # catalog code is absent here. Only LOAD requires a live identity.
            text,hits=re.subn(r'        #KnownModel := FALSE;\n.*?        IF NOT #KnownModel THEN RETURN; END_IF;',
                '        IF LEN("FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode) < 1 THEN RETURN; END_IF;',text,flags=re.S)
            assert hits==1
        if not self.layout.model.model_config:
            # A station-only deployment has no model loop (TIA rejects 1..0).
            text, hits = re.subn(r'        FOR #ModelIndex := 1 TO @MODEL_COUNT@ DO\n.*?        END_FOR;\n', '', text, flags=re.S)
            assert hits == 1
        for key, value in {'SET_CAPACITY': self.capacity, 'SET_RECORDS': self.records,
                           'MAX_SET_RECORDS':self.layout.catalog.capacities['MAX_SET_RECORDS'],
                           'MODEL_COUNT': len(self.layout.model.model_config), 'LINE_WIDTH': LINE_WIDTH}.items():
            text = text.replace('@'+key+'@', str(value))
        for enum, members in self.layout.catalog.enums.items():
            for member, value in members.items():
                text = text.replace('@'+enum+'.'+member+'@', str(value))
        assert '@' not in text
        body = ['    IF NOT #Startup THEN RETURN; END_IF;',
                '    IF "FRK_SetStore".SchemaVersion <> 1 THEN',
                '        FOR #RootIndex := 1 TO %d DO'%roots,
                '            IF "FRK_SetStore".SchemaVersion <> 0 THEN "FRK_ConfigLoss"(RootIndex := #RootIndex, Scope := "FRK_SetStore".Sets[#RootIndex, 1].Info.RootIdentity); END_IF;',
                '            FOR #Slot := 1 TO %d DO "FRK_SetStore".Sets[#RootIndex, #Slot].Info.Used := FALSE; END_FOR;'%self.capacity,
                '        END_FOR;', '        "FRK_SetStore".SchemaVersion := 1;', '    END_IF;']
        text += function('FRK_SetBoot', ['Startup : Bool;'], [], ['RootIndex : Int;', 'Slot : Int;'], body)
        text += self.codec()
        sources['14a_ConfigSetServices.scl'] = text
        return sources

    def codec(self):
        # Same fields/order as Core FB_ConfigSetJson, one schema for both vendors.
        shapes = {
            'Header': [('set','SetName',80), ('root','RootIdentity',80), ('schema','SetSchema',0), ('configRev','ConfigRev',0),
                       ('kind','Kind',0), ('model','ModelCode',64), ('records','RecordCount',0), ('created','CreatedAt',0), ('clock','TimeSynchronized',0)],
            'Record': [('scope','Scope',80), ('key','WriteKey',160), ('rev','Revision',0), ('kind','Kind',0), ('type','ValueType',0), ('value','ValueText',80)],
        }
        text = ''
        for shape, fields in shapes.items():
            record = 'ST_ConfigSetInfo' if shape == 'Header' else 'ST_ConfigRecord'
            body = ['    #FRK_Json'+shape+' := FALSE;', "    #Line := WSTRING#'{';"]
            for i, (key, member, length) in enumerate(fields):
                value = 'STRING_TO_WSTRING(#Data.'+member+')' if length else 'UDINT_TO_WSTRING(#Data.'+member+')'
                if member in ('Kind','RecordCount','ValueType'): value = 'DINT_TO_WSTRING(#Data.'+member+')'
                if member == 'SetSchema': value = 'UINT_TO_WSTRING(#Data.SetSchema)'
                if member == 'TimeSynchronized': value = "WSTRING#'0'"; body += ["    IF #Data.TimeSynchronized THEN #Flag := WSTRING#'1'; ELSE #Flag := WSTRING#'0'; END_IF;"]; value = '#Flag'
                if member == 'CreatedAt': value = 'ULINT_TO_WSTRING(LDT_TO_ULINT(#Data.CreatedAt) / ULINT#1000000000)'
                body += ['    #Ok := "FRK_JsonAdd"(Key := '+literal(key)+', Value := '+value+', Quoted := '+str(bool(length)).upper()+', LastField := '+str(i==len(fields)-1).upper()+', Line := #Line);',
                         '    IF NOT #Ok THEN #Line := WSTRING#\'\'; RETURN; END_IF;']
            body += ['    #FRK_Json'+shape+' := TRUE;']
            text += function('FRK_Json'+shape, ['Data : "'+record+'";'], ['Line : WString;'], ['Ok : Bool;', 'Flag : WString[1];'], body, 'Bool')
            # Parse into a temporary record; publish only after all fields pass.
            body = ['    #FRK_JsonRead'+shape+' := FALSE;', '    IF #Count <> %d THEN RETURN; END_IF;' % len(fields)]
            for key, member, length in fields:
                body += ['    #Found := 0;', '    FOR #Index := 1 TO #Count DO IF #Fields[#Index].Key = '+literal(key)+' THEN #Found := #Index; END_IF; END_FOR;',
                         '    IF #Found = 0 THEN RETURN; END_IF;',
                         '    IF #Fields[#Found].Quoted <> '+str(bool(length)).upper()+' THEN RETURN; END_IF;']
                if length:
                    body += ['    IF LEN(#Fields[#Found].Text) > %d OR STRING_TO_WSTRING(WSTRING_TO_STRING(#Fields[#Found].Text)) <> #Fields[#Found].Text THEN RETURN; END_IF;' % length,
                             '    #Candidate.'+member+' := WSTRING_TO_STRING(#Fields[#Found].Text);']
                else:
                    maximum = 4294967295
                    if member == 'SetSchema': maximum = 65535
                    if member == 'Kind': maximum = max(self.layout.catalog.enums['E_ConfigKind'].values()) if self.layout.line else 1
                    if member == 'ValueType': maximum = 3
                    if member == 'RecordCount': maximum = self.records
                    if member == 'TimeSynchronized': maximum = 1
                    body += ['    #Ok := "FRK_ConfigDecode"(Text := #Fields[#Found].Text, Storage := %d, Minimum := 0.0, Maximum := %s.0, MaxLength := 0, Value := "FRK_ConfigScratch".Value);' % (self.layout.catalog.enums['E_ConfigStorage']['AS_UDINT'], maximum),
                             '    IF NOT #Ok THEN RETURN; END_IF;']
                    value = ('LINT_TO_'+('UINT' if member == 'SetSchema' else 'INT' if member == 'RecordCount' else 'DINT' if member in ('Kind','ValueType') else 'UDINT')+'("FRK_ConfigScratch".Value.Number)')
                    if member == 'CreatedAt': value = 'ULINT_TO_LDT(LINT_TO_ULINT("FRK_ConfigScratch".Value.Number) * ULINT#1000000000)'
                    elif member == 'TimeSynchronized': value = '"FRK_ConfigScratch".Value.Number = 1'
                    body += ['    #Candidate.'+member+' := '+value+';']
            body += ['    #Data := #Candidate;', '    #FRK_JsonRead'+shape+' := TRUE;']
            text += function('FRK_JsonRead'+shape, ['Count : Int;', 'Fields : Array[1..9] of "FRK_JsonField";'],
                             ['Data : "'+record+'";'], ['Candidate : "'+record+'";', 'Index : Int;', 'Found : Int;', 'Ok : Bool;'], body, 'Bool')
        return text

    def operation(self, t):
        l = self.layout
        k = l.catalog.enums['E_HmiRequestKind']
        model_kind = l.catalog.enums['E_ConfigKind']['PAR_CFG']
        station_kind = l.catalog.enums['E_ConfigKind']['STATION_CFG']
        work = '"FRK_SetRuntime".Work[#RootIndex]'
        payload = work+'.Payload'
        def walk(phase, ready='#Ready'):
            return l.call(t, 'SetWalk', '#Module.', RootIndex='#RootIndex', Phase=str(phase), Access='#Module.Access', Ready=ready)
        kinds = [k[n] for n in ('SAVE_CONFIG_SET','LOAD_CONFIG_SET','LIST_CONFIG_SETS','EXPORT_CONFIG_SET','IMPORT_CONFIG_SET','DELETE_CONFIG_SET','EXPORT_CURRENT_CONFIG')]
        body = ['    #RootIndex := "FRK_ConfigRoot"(RegIndex := #Module.Core.RegIndex);',
                '    IF #Module.Core.ParentIndex <> 0 OR #RootIndex = 0 THEN RETURN; END_IF;',
                '    IF #Startup THEN', '        '+work+'.Importing := FALSE; '+work+'.Exporting := FALSE; '+work+'.Piece := WSTRING#\'\';',
                '        IF "FRK_SetStore".SchemaVersion <> 1 THEN',
                '            FOR #Slot := 1 TO %d DO "FRK_SetStore".Sets[#RootIndex, #Slot].Info.Used := FALSE; END_FOR;' % self.capacity,
                '        END_IF;', '    END_IF;',
                '    IF '+work+'.Generation <> #Module.Access.SessionGeneration THEN',
                '        '+work+'.Importing := FALSE; '+work+'.Exporting := FALSE; '+work+'.Piece := WSTRING#\'\';',
                '        '+work+'.Generation := #Module.Access.SessionGeneration;', '    END_IF;',
                '    IF NOT #Module.Unit.RequestPending THEN RETURN; END_IF;',
                '    #Request := #Module.Unit.Request;',
                '    #Exporting := '+work+'.Exporting; '+work+'.Exporting := FALSE;',
                '    IF #Request.Kind <> %d THEN %s.Importing := FALSE; %s.Piece := WSTRING#\'\'; END_IF;' % (k['IMPORT_CONFIG_SET'],work,work),
                '    IF #Request.Kind <> %d THEN %s.Exporting := FALSE; END_IF;' % (k['EXPORT_CONFIG_SET'],work),
                '    IF '+ ' AND '.join('#Request.Kind <> %d' % n for n in kinds)+' THEN RETURN; END_IF;',
                '    #Module.HmiResponse.Accepted := FALSE; #Module.HmiResponse.Diagnostic := WSTRING#\'std.error.configSetRejected\';',
                '    #Module.ConfigPersist.LastRejectScope := #Module.Status.Name; #Module.ConfigPersist.LastRejectKey := \'\';',
                '    '+work+'.RejectScope := #Module.Status.Name; '+work+'.RejectKey := \'\';',
                '    IF #Module.Access.CurrentLevel < #Module.Access.Policy.Required[%d] THEN '%l.catalog.enums['E_GatedAction']['CONFIG_SET']+work+'.Importing := FALSE; '+work+'.Exporting := FALSE; '+work+'.Piece := WSTRING#\'\'; RETURN; END_IF;',
                '    IF "FRK_ConfigRuntime".Unavailable THEN "FRK_ConfigRuntime".Failed[#RootIndex] := TRUE; '+work+'.Importing := FALSE; '+work+'.Exporting := FALSE; '+work+'.Piece := WSTRING#\'\'; RETURN; END_IF;',
                '    #Ready := #Module.Core.Exec = %d AND NOT #Module.Unit.ModePending AND NOT #Module.Unit.Clearing AND "FRK_DescendantsReady"(OwnerIndex := #Module.Core.RegIndex);' % l.catalog.enums['E_ExecState']['READY'],
                '    #SetName := WSTRING_TO_STRING(#Request.TextValue);',
                '    IF #Request.Kind <> %d THEN' % k['IMPORT_CONFIG_SET'],
                '        IF LEN(#Request.TextValue) < 1 AND #Request.Kind <> %d THEN RETURN; END_IF;' % k['LIST_CONFIG_SETS'],
                '        IF LEN(#Request.TextValue) > 80 OR STRING_TO_WSTRING(#SetName) <> #Request.TextValue THEN RETURN; END_IF;',
                '    END_IF;', '    '+work+'.RejectScope := #Module.Status.Name; '+work+'.RejectKey := \'\';',
                '    CASE #Request.Kind OF',
                '        %d:' % k['LIST_CONFIG_SETS'], '            #Module.ConfigSetCount := 0;',
                '            FOR #Slot := 1 TO %d DO' % self.capacity,
                '                IF "FRK_SetStore".Sets[#RootIndex, #Slot].Info.Used THEN',
                '                    #Module.ConfigSetCount := #Module.ConfigSetCount + 1;',
                '                    #Module.ConfigSets[#Module.ConfigSetCount] := "FRK_SetStore".Sets[#RootIndex, #Slot].Info;',
                '                END_IF;', '            END_FOR;', '            #Module.HmiResponse.Accepted := TRUE;',
                '        %d:' % k['DELETE_CONFIG_SET'],
                '            #Slot := "FRK_SetFind"(RootIndex := #RootIndex, SetName := #SetName);',
                '            IF #Slot > 0 THEN "FRK_SetStore".Sets[#RootIndex, #Slot].Info.Used := FALSE; #Module.HmiResponse.Accepted := TRUE; END_IF;',
                '        %d:' % k['SAVE_CONFIG_SET'],
                '            #Slot := "FRK_SetSlot"(RootIndex := #RootIndex, SetName := #SetName);',
                '            IF #Slot = 0 OR (#Request.IntValue <> 0 AND #Request.IntValue <> 1) THEN RETURN; END_IF;',
                '            '+payload+'.Info.SetName := #SetName; '+payload+'.Info.RootIdentity := #Module.Status.Name;',
                '            '+payload+'.Info.SetSchema := 1; '+payload+'.Info.ConfigRev := #Module.ConfigRev;',
                '            '+payload+'.Info.Kind := #Request.IntValue; '+payload+'.Info.RecordCount := 0;',
                '            '+payload+'.Info.ModelCode := \'\';',
                '            IF #Request.IntValue = 0 THEN '+payload+'.Info.ModelCode := #Module.Model.ModelCode; END_IF;',
                '            #ResultCode := RD_SYS_T(OUT => #Stamp); '+payload+'.Info.CreatedAt := DTL_TO_LDT(#Stamp);',
                '            '+payload+'.Info.TimeSynchronized := FALSE; '+payload+'.Info.Used := TRUE;',
                '            #Ok := '+walk(0)+';',
                '            IF #Ok THEN #Ok := "FRK_SetShape"(RootIndex := #RootIndex, RootIdentity := #Module.Status.Name); END_IF;',
                '            IF #Ok AND '+payload+'.Info.RecordCount > 0 THEN "FRK_SetStore".Sets[#RootIndex, #Slot] := '+payload+'; #Module.HmiResponse.Accepted := TRUE; END_IF;',
                '        %d:' % k['LOAD_CONFIG_SET'],
                '            #Slot := "FRK_SetFind"(RootIndex := #RootIndex, SetName := #SetName);',
                '            IF #Slot = 0 THEN RETURN; END_IF;',
                '            '+payload+' := "FRK_SetStore".Sets[#RootIndex, #Slot];',
                '            #Ok := "FRK_SetShape"(RootIndex := #RootIndex, RootIdentity := #Module.Status.Name);',
                '            IF NOT #Ok THEN RETURN; END_IF;',
                '            IF '+payload+'.Info.Kind = 0 THEN',
                '                "FRK_UnitRelease"(Core := #Module.Core, Unit := #Module.Unit, Status := #Module.Status, Policy := #Module.ModePolicy, Access := #Module.Access, Supported := #Module.SupportedModesPublished, Report := #Module.HmiResponse.Report, Gate := %d, Desired := -1, Trusted := FALSE);' % l.catalog.enums['E_GatedAction']['CHANGEOVER'],
                '                IF NOT #Module.HmiResponse.Report.Released THEN RETURN; END_IF;', '            END_IF;',
                '            "FRK_SetValidateBegin"(RootIndex := #RootIndex); #Ok := '+walk(1)+';',
                '            IF #Ok THEN #Ok := "FRK_SetValidateEnd"(RootIndex := #RootIndex); END_IF;',
                '            IF #Ok AND '+work+'.Matched = '+payload+'.Info.RecordCount THEN',
                '                #Ok := '+walk(2)+';',
                '                IF '+payload+'.Info.Kind = 0 THEN "FRK_ConfigSetActiveModel"(RootIndex := #RootIndex, ModelCode := '+payload+'.Info.ModelCode); #Module.Model.ModelCode := '+payload+'.Info.ModelCode; END_IF;',
                '                #Module.ConfigRev := "FRK_ConfigRevision"(Previous := #Module.ConfigRev);',
                '                #Module.HmiResponse.Accepted := TRUE;', '            END_IF;',
                '        %d:' % k['EXPORT_CONFIG_SET'],
                '            #Module.ConfigSetDocument := WSTRING#\'\'; #Module.ConfigSetDocumentLine := -1; #Module.ConfigSetDocumentLines := 0;',
                '            IF #Request.IntValue < 0 THEN '+work+'.Exporting := FALSE; RETURN; END_IF;',
                '            IF #Request.IntValue = 0 THEN',
                '                IF #Request.NameValue <> \'\' THEN '+work+'.Exporting := FALSE; RETURN; END_IF;',
                '                #Slot := "FRK_SetFind"(RootIndex := #RootIndex, SetName := #SetName); IF #Slot = 0 THEN RETURN; END_IF;',
                '                '+payload+' := "FRK_SetStore".Sets[#RootIndex, #Slot];',
                '                '+work+'.CurrentExport := FALSE; '+work+'.ExportToken := \'\';',
                '                '+work+'.NextLine := 0; #Exporting := TRUE;', '            END_IF;',
                '            IF ('+work+'.CurrentExport AND #Request.NameValue <> '+work+'.ExportToken) OR (NOT '+work+'.CurrentExport AND #Request.NameValue <> \'\') THEN '+work+'.Exporting := FALSE; RETURN; END_IF;',
                '            IF NOT #Exporting OR #SetName <> '+payload+'.Info.SetName OR #Request.IntValue <> '+work+'.NextLine OR #Request.IntValue > '+payload+'.Info.RecordCount THEN RETURN; END_IF;',
                '            #Ok := "FRK_SetShape"(RootIndex := #RootIndex, RootIdentity := #Module.Status.Name);',
                '            "FRK_SetValidateBegin"(RootIndex := #RootIndex);', '            IF #Ok THEN #Ok := '+walk(3)+'; END_IF;',
                '            IF NOT #Ok OR '+work+'.Matched <> '+payload+'.Info.RecordCount THEN '+work+'.Exporting := FALSE; RETURN; END_IF;',
                '            IF #Request.IntValue = 0 THEN #Ok := "FRK_JsonHeader"(Data := '+payload+'.Info, Line := #Module.ConfigSetDocument);',
                '            ELSE #Ok := "FRK_JsonRecord"(Data := '+payload+'.Records[#Request.IntValue], Line := #Module.ConfigSetDocument); END_IF;',
                '            IF #Ok THEN #Module.ConfigSetDocumentLine := DINT_TO_INT(#Request.IntValue); #Module.ConfigSetDocumentLines := '+payload+'.Info.RecordCount; '+work+'.NextLine := '+work+'.NextLine + 1; #Module.HmiResponse.Accepted := TRUE; END_IF;',
                '            '+work+'.Exporting := #Ok AND #Request.IntValue < '+payload+'.Info.RecordCount;',
                '        %d:' % k['EXPORT_CURRENT_CONFIG'],
                '            #Module.ConfigSetDocument := WSTRING#\'\'; #Module.ConfigSetDocumentLine := -1; #Module.ConfigSetDocumentLines := 0;',
                '            IF NOT "FRK_ExportTokenValid"(Token := #Request.NameValue) OR (#Request.IntValue <> %d AND #Request.IntValue <> %d) THEN RETURN; END_IF;'%(model_kind, station_kind),
                '            IF #Request.DurationMs > '+('INT_TO_UDINT(#Module.AvailableModelCount)' if l.runtime_models else str(len(l.model.model_config)))+' OR (#Request.IntValue = %d AND #Request.DurationMs <> 0) THEN RETURN; END_IF;'%station_kind,
                '            '+payload+'.Info.SetName := #SetName; '+payload+'.Info.RootIdentity := #Module.Status.Name;',
                '            '+payload+'.Info.SetSchema := 1; '+payload+'.Info.ConfigRev := #Module.ConfigRev;',
                '            '+payload+'.Info.Kind := #Request.IntValue; '+payload+'.Info.RecordCount := 0;',
                '            '+payload+'.Info.ModelCode := \'\';',
                '            IF #Request.IntValue = %d THEN '%model_kind+payload+'.Info.ModelCode := "FRK_ConfigModelCode"(RootIndex := #RootIndex, ModelIndex := #Request.DurationMs); END_IF;',
                '            #ResultCode := RD_SYS_T(OUT => #Stamp); '+payload+'.Info.CreatedAt := DTL_TO_LDT(#Stamp);',
                '            '+payload+'.Info.TimeSynchronized := FALSE; '+payload+'.Info.Used := TRUE;',
                '            #Ok := '+walk(5)+';',
                '            IF #Ok THEN #Ok := "FRK_SetShape"(RootIndex := #RootIndex, RootIdentity := #Module.Status.Name); END_IF;',
                '            IF NOT #Ok OR '+payload+'.Info.RecordCount = 0 THEN RETURN; END_IF;',
                '            #Ok := "FRK_JsonHeader"(Data := '+payload+'.Info, Line := #Module.ConfigSetDocument);',
                '            IF NOT #Ok THEN RETURN; END_IF;',
                '            '+work+'.ExportToken := #Request.NameValue; '+work+'.CurrentExport := TRUE; '+work+'.NextLine := 1; '+work+'.Exporting := TRUE;',
                '            #Module.ConfigSetDocumentLine := 0; #Module.ConfigSetDocumentLines := '+payload+'.Info.RecordCount; #Module.HmiResponse.Accepted := TRUE;',
                '        %d:' % k['IMPORT_CONFIG_SET'],
                '            #Ok := "FRK_SetImport"(RootIndex := #RootIndex, Request := #Request);',
                '            IF #Ok AND #Request.BoolValue THEN',
                '                #Ok := "FRK_SetShape"(RootIndex := #RootIndex, RootIdentity := #Module.Status.Name);',
                '                "FRK_SetValidateBegin"(RootIndex := #RootIndex);', '                IF #Ok THEN #Ok := '+walk(4, 'TRUE')+'; END_IF;',
                '                IF #Ok THEN #Ok := "FRK_SetValidateEnd"(RootIndex := #RootIndex); END_IF;',
                '                #Slot := "FRK_SetSlot"(RootIndex := #RootIndex, SetName := '+payload+'.Info.SetName);',
                '                IF #Ok AND #Slot > 0 THEN "FRK_SetStore".Sets[#RootIndex, #Slot] := '+payload+'; ELSE #Ok := FALSE; END_IF;',
                '            END_IF;', '            #Module.HmiResponse.Accepted := #Ok;',
                '            IF NOT #Ok THEN '+work+'.Importing := FALSE; '+work+'.Piece := WSTRING#\'\'; END_IF;',
                '        ELSE RETURN;', '    END_CASE;',
                '    IF #Module.HmiResponse.Accepted THEN',
                '        #Module.HmiResponse.Diagnostic := WSTRING#\'\'; "FRK_ConfigRuntime".Failed[#RootIndex] := FALSE;',
                '        #Module.ConfigPersist.LastSetName := '+payload+'.Info.SetName; #Module.ConfigPersist.LastSetRecords := '+payload+'.Info.RecordCount;',
                '        #Module.ConfigPersist.LastRejectScope := \'\'; #Module.ConfigPersist.LastRejectKey := \'\';',
                '    ELSE #Module.ConfigPersist.LastRejectScope := '+work+'.RejectScope; #Module.ConfigPersist.LastRejectKey := '+work+'.RejectKey; END_IF;']
        if l.runtime_models:
            anchor='            IF '+payload+'.Info.Kind = 0 THEN'
            insert=body.index(anchor)+1
            body.insert(insert,'                IF NOT "FRK_ModelKnown"(RootIndex := #RootIndex, Code := '+payload+'.Info.ModelCode) THEN RETURN; END_IF;')
        if l.line:
            line_kind = l.catalog.enums['E_ConfigKind']['LINE_CFG']
            before = '(#Request.IntValue <> %d AND #Request.IntValue <> %d)'%(model_kind, station_kind)
            assert sum(s.count(before) for s in body) == 2
            body = [s.replace(before, '(#Request.IntValue <> %d AND #Request.IntValue <> %d AND #Request.IntValue <> %d)'%(model_kind, station_kind, line_kind)) for s in body]
            body = [s.replace('(#Request.IntValue = %d AND #Request.DurationMs <> 0)'%station_kind,
                              '(#Request.IntValue <> %d AND #Request.DurationMs <> 0)'%model_kind) for s in body]
            if l.model.line.role == 'MIRROR':
                # Keep ordinary station/model operations available. Refuse a
                # line snapshot as soon as its kind is known, naming its owner.
                refuse = ['            '+work+'.Importing := FALSE; '+work+'.Exporting := FALSE; '+work+'.Piece := WSTRING#\'\';',
                          '            '+work+'.RejectScope := '+literal(l.model.line.owner)+';',
                          '            #Module.ConfigPersist.LastRejectScope := '+literal(l.model.line.owner)+';',
                          '            #Module.ConfigPersist.LastRejectKey := \'line.\';', '            RETURN;']
                insert = body.index('    CASE #Request.Kind OF')
                guard = ['    IF (#Request.Kind = %d OR #Request.Kind = %d) AND #Request.IntValue = %d THEN'%(k['SAVE_CONFIG_SET'],k['EXPORT_CURRENT_CONFIG'],line_kind), *refuse, '    END_IF;',
                         '    IF #Request.Kind = %d OR #Request.Kind = %d OR #Request.Kind = %d THEN'%(k['LOAD_CONFIG_SET'],k['EXPORT_CONFIG_SET'],k['DELETE_CONFIG_SET']),
                         '        #Slot := "FRK_SetFind"(RootIndex := #RootIndex, SetName := #SetName);',
                         '        IF #Slot > 0 THEN',
                         '            IF "FRK_SetStore".Sets[#RootIndex, #Slot].Info.Kind = %d THEN'%line_kind,
                         *['    '+s for s in refuse], '            END_IF;', '        END_IF;', '    END_IF;']
                body[insert:insert] = guard
                insert = body.index('            #Ok := "FRK_SetImport"(RootIndex := #RootIndex, Request := #Request);')+1
                body[insert:insert] = ['            IF #Ok AND '+payload+'.Info.Kind = %d THEN'%line_kind, *refuse, '            END_IF;']
        return l.render(t, 'SetOperation', ['Startup : Bool;'], ['Module : "'+t.name+'";'],
            ['RootIndex : Int;', 'Request : "ST_HmiRequest";', 'Ready : Bool;', 'SetName : String[80];', 'Slot : Int;', 'Ok : Bool;', 'Exporting : Bool;', 'Stamp : DTL;', 'ResultCode : Int;'], body)
