"""Selected native byte medium; documents derive from their existing owners."""
from dataclasses import dataclass
import hashlib
import json
import re

from fraktal_tia_binding import REPO, PRIVATE, READONLY, literal, type_source
from fraktal_tia_config import function

POLICY = REPO / 'FraktalCore/PLC/Siemens/Framework/Core/persistence.json'
TEMPLATE = POLICY.with_name('persist_medium.scl.in')
FACTS = json.loads(POLICY.read_bytes())


def udt(name, fields):
    return type_source(name, [dict(member=n, native_type=t, accessible=False, initial='') for n, t in fields])


@dataclass
class Document:
    index: int
    key: str
    root: int
    role: str
    model: str = ''
    ordinal: int = 0
    entries: tuple = ()
    capacity: int = 0

    @property
    def tag(self):
        return 'D%03d' % self.index

    @property
    def image_type(self):
        return 'FRK_Document_' + self.tag


class Medium:
    def __init__(self, layout):
        self.layout = layout
        self.model = layout.model
        self.catalog = layout.catalog
        self.documents = []
        self.fields = {}
        self.types = {}
        for root_index, root in enumerate(self.model.roots, 1):
            owned = [i for i in self.model.instances if layout.root_map[i.index] == root_index]
            station = tuple((i, f) for i in owned for f in layout.fields[i.type_name] if f.kind == self.catalog.enums['E_ConfigKind']['STATION_CFG'])
            model = tuple((i, f) for i in owned for f in layout.fields[i.type_name] if f.kind == self.catalog.enums['E_ConfigKind']['PAR_CFG'])
            self.add(root.name + '.station', root_index, 'config', entries=station)
            for code in layout.models:
                if model:
                    self.add(root.name + '.model' + ('.' + code if code else ''), root_index, 'config', model=code, entries=model)
            self.add(root.name + '.policy', root_index, 'policy')
            if layout.sets:
                for ordinal in range(1, layout.sets.capacity + 1):
                    self.add(root.name + '.set' + str(ordinal), root_index, 'set', ordinal=ordinal)
        self.add('users', 0, 'users')
        if self.model.line:
            host = next(i for i, root in enumerate(self.model.roots, 1) if root.name == self.model.line.roots[0])
            self.add('line.'+hashlib.sha256(self.model.line.line_id.encode('ascii')).hexdigest(), host, 'line')
        # Append optional policy documents; existing action-policy documents and
        # their station/model/set slots keep their identities and layouts.
        for root_index, root in enumerate(self.model.roots, 1):
            if root.name in dict(self.model.data_classes):
                self.add(root.name+'.classes', root_index, 'classes')
        if len(self.documents) > self.catalog.capacities['MAX_PERSIST_KEYS']:
            self.reject('document count exceeds the Core key bound')
        import xml.etree.ElementTree as ET
        from fraktal_tia_binding import CORE
        declaration=ET.fromstring((CORE/'Params/PL_Fraktal.TcGVL').read_bytes()).findtext('.//Declaration')
        window=int(re.search(r'CONFIG_PERSIST_WINDOW_MS\s*:\s*UDINT\s*:=\s*(\d+)',declaration)[1])
        self.window = self.model.persistence_min_write_ms * (len(self.documents) + 1) + window
        if self.window > 4294967295:
            self.reject('write window exceeds UDInt')

    @staticmethod
    def reject(message):
        from fraktal_tia_declaration import DeclarationError
        raise DeclarationError('T-WIDTH', 'persistence', message)

    def add(self, key, root, role, **kwargs):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', key):
            self.reject('derived document key must fit the Core 80-character key rule')
        d = Document(len(self.documents) + 1, key, root, role, **kwargs)
        self.documents.append(d)
        fields = [('SchemaVersion', 'UInt'), ('Scope', 'String[80]')]
        if role == 'config':
            fields += [('Kind', 'DInt'), ('ModelCode', 'String[64]'), ('ActiveModel', 'String[64]'), ('Count', 'Int'),
                       ('Rows', 'Array[1..%d] of "FRK_ConfigSlot"' % max(1, len(d.entries)))]
        elif role == 'policy':
            fields += [('Image', '"FRK_AccessPolicyImage"')]
        elif role == 'classes':
            fields += [('Image', '"FRK_ClassPolicyImage"')]
        elif role == 'users':
            fields += [('Generation', 'UDInt'), ('Count', 'DInt'), ('Rows', 'Array[1..%d] of "ST_UserRecord"' % self.catalog.capacities['MAX_USERS']), ('Checksum', 'DWord')]
        elif role == 'line':
            fields += [('Image', '"ST_LineImage"')]
        else:
            fields += [('Ordinal', 'Int'), ('Payload', '"FRK_SetPayload"')]
        self.fields[d.tag] = fields
        # Conservative standard serialization bound, proportional to owned fields.
        definitions = self.catalog.resolve(['ST_ConfigRecord', 'ST_UserRecord', 'ST_AccessPolicy', 'ST_ConfigSetInfo'])
        if self.model.line:
            definitions.update(self.catalog.resolve(['ST_LineImage']))
        if self.model.data_classes:
            from fraktal_tia_data_classes import image_fields
            definitions.update(self.catalog.resolve(['ST_DataClassPolicy']))
            definitions['FRK_ClassPolicyImage'] = [dict(member=n,native_type=t) for n,t in image_fields(self.catalog)]
        definitions.update({
            'FRK_ConfigSlot': [dict(member=n, native_type=t) for n, t in [('SchemaVersion','UInt'),('Used','Bool'),('ModelCode','String[64]'),('Record','"ST_ConfigRecord"')]],
            'FRK_AccessPolicyImage': [dict(member=n,native_type=t) for n,t in [('SchemaVersion','UInt'),('Initialized','Bool'),('Scope','String[80]'),('Generation','UDInt'),('Policy','"ST_AccessPolicy"'),('Checksum','DWord')]],
        })
        if self.layout.sets:
            definitions['FRK_SetPayload'] = [dict(member=n,native_type=t) for n,t in [('Info','"ST_ConfigSetInfo"'),('Records','Array[1..%d] of "ST_ConfigRecord"'%self.layout.sets.records)]]
        def size(t):
            t=t.split(':=')[0].strip()
            string=re.fullmatch(r'(W)?String\[(\d+)\]',t,re.I)
            if string:return (2 if string[1] else 1)*int(string[2])+4
            array=re.fullmatch(r'Array\[(-?\d+)\.\.(-?\d+)\] of (.+)',t,re.I)
            if array:return (int(array[2])-int(array[1])+1)*(size(array[3])+2)
            name=t.strip('"')
            if name in definitions:return sum(size(f['native_type'])+2 for f in definitions[name])
            if re.fullmatch(r'(Bool|Byte|Char|Word|DWord|Int|UInt|DInt|UDInt|LInt|ULInt|LReal|Real|Time|LDT)',t,re.I):return 8
            self.reject('unsupported serialization type: '+t)
        d.capacity=sum(size(t)+2 for _,t in fields)+32
        if d.capacity > self.catalog.capacities['MAX_PERSIST_DOC_BYTES']:
            self.reject('document '+key+' exceeds the Core byte bound')

    def sources(self):
        from fraktal_tia_generate import db
        docs=self.documents; count=len(docs); queue=self.model.persistence_queue_capacity
        sources={
            '03_FRK_PersistAnchor.udt':udt('FRK_PersistAnchor',[('SchemaVersion','UInt'),('KeyCrc','DWord'),('Generation','UDInt'),('DocumentCrc','DWord'),('Checksum','DWord')]),
            '03_FRK_PersistCheck.udt':udt('FRK_PersistCheck',[('SchemaVersion','UInt'),('Cursor','DInt'),('Crc','DWord'),('Generation','UDInt'),('Length','UDInt'),('Valid','Bool'),('Empty','Bool'),('ZeroMode','Bool')]),
            '03_FRK_PersistQueue.udt':udt('FRK_PersistQueue',[('SchemaVersion','UInt'),('State','Int'),('Ticket','UDInt'),('Slot','Int'),('WriteDocument','Bool'),('Length','DInt'),('Result','"ST_PersistResult"')]),
        }
        for d in docs:
            sources['03_'+d.image_type+'.udt']=udt(d.image_type,self.fields[d.tag])
            self.types[d.image_type]=self.fields[d.tag]
            for bank in ('A','B'):
                block='FRK_Load_'+d.tag+bank
                text=db(block,['Bytes'+PRIVATE+' : Array[0..%d] of Byte;'%(d.capacity+FACTS['header_bytes']-1)])
                assert text.count('NON_RETAIN')==1
                sources['06_'+block+'.db']=text.replace('NON_RETAIN','UNLINKED\nNON_RETAIN',1)
        runtime_fields=[('Scan','UDInt'),('LastScan','UDInt'),('LastTicket','UDInt'),('Active','Int'),('Stage','Int'),('Slot','Int'),('Chosen','Int'),('Generation','UDInt'),('NativeBusy','Bool'),('NativeReq','Bool'),('NativeResult','Int'),('LastWriteMs','UDInt'),('HadWrite','Bool'),('Unavailable','Bool'),('Result','"ST_PersistResult"'),('EmptyResult','"ST_PersistResult"'),('CheckA','"FRK_PersistCheck"'),('CheckB','"FRK_PersistCheck"'),('CheckWrite','"FRK_PersistCheck"'),('Queue','Array[1..%d] of "FRK_PersistQueue"'%queue),('Capacity','Array[1..%d] of DInt'%count),('KeyCrc','Array[1..%d] of DWord'%count),('Leased','Array[1..%d] of Bool'%count),('Anchor','Array[1..%d] of "FRK_PersistAnchor"'%count)]
        sources['06_FRK_PersistRuntime.db']=db('FRK_PersistRuntime',[n+PRIVATE+' : '+t+';' for n,t in runtime_fields])
        sources['06_FRK_PersistAnchors.db']=db('FRK_PersistAnchors',[n+PRIVATE+' : '+t+';' for n,t in [('RowsA','Array[1..%d] of "FRK_PersistAnchor"'%count),('RowsB','Array[1..%d] of "FRK_PersistAnchor"'%count),('SelectedB','Array[1..%d] of Bool'%count),('Commissioned','Array[1..%d] of Bool'%count)]]).replace('VAR\n','VAR RETAIN\n',1)
        buffers=[]; images=[]
        for d in docs:
            images += [d.tag+PRIVATE+' : "'+d.image_type+'";']
            buffers += [d.tag+s+PRIVATE+' : Array[0..%d] of Byte;'%(d.capacity+FACTS['header_bytes']-1) for s in ('A','B','Data')]
        sources['06_FRK_PersistBuffers.db']=db('FRK_PersistBuffers',buffers)
        sources['06_FRK_PersistImages.db']=db('FRK_PersistImages',images)
        consumers=[('State','Int'),('Ticket','UDInt'),('Dirty','Bool'),('Failed','Bool'),('Rejected','Bool'),('Acknowledged','Bool'),('Virgin','Bool'),('RetrySince','UDInt'),('PendingSince','LDT'),('NextSince','LDT'),('Result','"ST_PersistResult"')]
        sources['03_FRK_PersistConsumer.udt']=udt('FRK_PersistConsumer',[('SchemaVersion','UInt'),*consumers])
        sources['06_FRK_PersistConsumers.db']=db('FRK_PersistConsumers',['Rows'+PRIVATE+' : Array[1..%d] of "FRK_PersistConsumer";'%count,'Ready'+PRIVATE+' : Bool;','BootApplied'+PRIVATE+' : Bool;'])
        sources['06_FRK_PersistStatus.db']=db('FRK_PersistStatus',['SchemaVersion'+READONLY+' : UInt := 1;','Medium'+READONLY+" : String[16] := 'LOAD_DB';",'Restoring'+READONLY+' : Bool;','Failed'+READONLY+' : Bool;','NativeStatus'+READONLY+' : Word;','DocumentCount'+READONLY+' : Int := %d;'%count])
        text=TEMPLATE.read_text('ascii')
        constants={'DOCUMENT_COUNT':count,'QUEUE_CAPACITY':queue,'HEADER_BYTES':FACTS['header_bytes'],'MAGIC':FACTS['magic'],'CRC_BUDGET':FACTS['crc_bytes_per_scan']}
        constants.update({'ERROR_'+k:v for k,v in FACTS['errors'].items()})
        for k,v in constants.items():text=text.replace('@'+k+'@',str(v))
        assert '@' not in text
        commit=function('FRK_PersistCommitAnchor',['Slot : Int;'],[],[],[
            '    IF #Slot < 1 OR #Slot > %d THEN RETURN; END_IF;'%count,
            '    IF "FRK_PersistAnchors".SelectedB[#Slot] THEN "FRK_PersistAnchors".RowsA[#Slot] := "FRK_PersistRuntime".Anchor[#Slot];',
            '    ELSE "FRK_PersistAnchors".RowsB[#Slot] := "FRK_PersistRuntime".Anchor[#Slot]; END_IF;',
            '    "FRK_PersistAnchors".SelectedB[#Slot] := NOT "FRK_PersistAnchors".SelectedB[#Slot];',
            '    "FRK_PersistAnchors".Commissioned[#Slot] := TRUE;'])
        text=text.replace('"FRK_PersistAnchors".Rows[','"FRK_PersistRuntime".Anchor[')
        anchor='    END_IF;\nEND_FUNCTION\n\nFUNCTION "FRK_PersistStart"'
        assert text.count(anchor)==1
        text=text.replace(anchor,'    END_IF;\n    "FRK_PersistCommitAnchor"(Slot := #Slot);\nEND_FUNCTION\n\nFUNCTION "FRK_PersistStart"')
        engine=self.engine().replace('"FRK_PersistAnchors".Rows[','"FRK_PersistRuntime".Anchor[').replace('Started :=','OldMs :=').replace('NowMs :=','NewMs :=')
        sources['15_PersistMedium.scl']=commit+text+engine+self.consumer_functions()
        return sources

    def io(self):
        b=['    CASE "FRK_PersistRuntime".Slot OF']
        for d in self.documents:
            data='"FRK_PersistBuffers".'+d.tag
            b += ['        %d:'%d.index,'            CASE #Operation OF']
            for op,bank,write in ((1,'A',False),(2,'B',False),(3,'A',True),(4,'B',True)):
                source=data+'Data' if write else '"FRK_Load_'+d.tag+bank+'".Bytes'
                destination='"FRK_Load_'+d.tag+bank+'".Bytes' if write else data+bank
                b += ['                %d: "FRK_PersistRuntime".NativeResult := %s(REQ := "FRK_PersistRuntime".NativeReq, SRCBLK := %s, BUSY => "FRK_PersistRuntime".NativeBusy, DSTBLK => %s);'%(op,'WRIT_DBL' if write else 'READ_DBL',source,destination)]
            b += ['                ELSE "FRK_PersistRuntime".NativeResult := -1; "FRK_PersistRuntime".NativeBusy := FALSE;','            END_CASE;']
        b += ['        ELSE "FRK_PersistRuntime".NativeResult := -1; "FRK_PersistRuntime".NativeBusy := FALSE;','    END_CASE;']
        return function('FRK_PersistIo',['Operation : Int;'],[],[],b)

    def dispatch(self, operation):
        b=['    #Done := FALSE;',*(['    #FRK_Persist'+operation+' := FALSE;'] if operation!='Inspect' else []),'    CASE "FRK_PersistRuntime".Slot OF']
        for d in self.documents:
            p='"FRK_PersistBuffers".'+d.tag
            if operation=='Inspect':
                call='"FRK_PersistInspect"(BytesA := '+p+'A, BytesB := '+p+'B, Payload := '+p+'Data);'
            else:
                check={'CheckA':'A','CheckB':'B','CheckWrite':'Data'}[operation]
                call='#Done := "FRK_PersistValidate"(ExpectedKey := "FRK_PersistRuntime".KeyCrc[%d], Bytes := %s%s, Check := "FRK_PersistRuntime".%s);'%(d.index,p,check,operation)
            b += ['        %d: %s'%(d.index,call)]
        b += ['        ELSE RETURN;','    END_CASE;']
        return function('FRK_Persist'+operation,[],[],['Done : Bool;'],b+(['    #FRK_Persist'+operation+' := #Done;'] if operation!='Inspect' else []),'Bool' if operation!='Inspect' else 'Void')

    def engine(self):
        n=len(self.documents);q=self.model.persistence_queue_capacity
        text=self.io()+''.join(self.dispatch(o) for o in ('CheckA','CheckB','CheckWrite','Inspect'))
        body=['    IF #Startup THEN', '        "FRK_PersistRuntime".Active := 0; "FRK_PersistRuntime".Stage := 0;',
              '        "FRK_PersistRuntime".HadWrite := TRUE; "FRK_PersistRuntime".LastWriteMs := "FRK_Clock".NowMs; "FRK_PersistRuntime".LastScan := "FRK_PersistRuntime".Scan;',
              '        FOR #Index := 1 TO %d DO "FRK_PersistRuntime".Queue[#Index].State := 0; END_FOR;'%q]
        for d in self.documents:
            p='"FRK_PersistRuntime".Anchor[%d]'%d.index
            body += ['        "FRK_PersistRuntime".Leased[%d] := FALSE;'%d.index,
                     '        "FRK_PersistRuntime".Capacity[%d] := %d;'%(d.index,d.capacity),
                     '        "FRK_PersistRuntime".KeyCrc[%d] := "FRK_PersistKeyCrc"(Key := %s);'%(d.index,literal(d.key)),
                     '        IF "FRK_PersistAnchors".SelectedB[%d] THEN %s := "FRK_PersistAnchors".RowsB[%d]; ELSE %s := "FRK_PersistAnchors".RowsA[%d]; END_IF;'%(d.index,p,d.index,p,d.index),
                     '        IF NOT "FRK_PersistAnchors".Commissioned[%d] AND %s.SchemaVersion = 0 AND %s.Generation = 0 AND %s.KeyCrc = DWORD#0 AND %s.DocumentCrc = DWORD#0 AND %s.Checksum = DWORD#0 THEN'%(d.index,p,p,p,p,p),
                     '            "FRK_PersistRepair"(Slot := %d);'%d.index,'        END_IF;']
        body += ['    END_IF;', '    "FRK_PersistRuntime".Scan := "FRK_PersistRuntime".Scan + 1;']
        text+=function('FRK_PersistEnter',['Startup : Bool;'],[],['Index : Int;'],body)
        # Native calls are serialized. Every poll advances at most one scan.
        body=['    IF "FRK_PersistRuntime".LastScan = "FRK_PersistRuntime".Scan THEN RETURN; END_IF;',
              '    "FRK_PersistRuntime".LastScan := "FRK_PersistRuntime".Scan;',
              '    IF "FRK_PersistRuntime".Active = 0 THEN', '        #Pick := 0;',
              '        FOR #Index := 1 TO %d DO'%q,
              '            IF "FRK_PersistRuntime".Queue[#Index].State = 1 THEN',
              '                IF #Pick = 0 THEN #Pick := #Index; ELSIF "FRK_PersistRuntime".Queue[#Index].Ticket < "FRK_PersistRuntime".Queue[#Pick].Ticket THEN #Pick := #Index; END_IF;',
              '            END_IF;', '        END_FOR;', '        IF #Pick = 0 THEN RETURN; END_IF;',
              '        "FRK_PersistRuntime".Active := #Pick;', '        "FRK_PersistRuntime".Slot := "FRK_PersistRuntime".Queue[#Pick].Slot;',
              '        "FRK_PersistRuntime".Queue[#Pick].State := 2;', '        "FRK_PersistRuntime".Result := "FRK_PersistRuntime".EmptyResult;',
              '        "FRK_PersistRuntime".Stage := 1; "FRK_PersistRuntime".NativeReq := TRUE;',
              '        "FRK_PersistRuntime".CheckA.Cursor := -1; "FRK_PersistRuntime".CheckB.Cursor := -1;', '    END_IF;',
              '    IF "FRK_PersistRuntime".Unavailable THEN', '        "FRK_PersistRuntime".Result.ErrorId := UDINT#32963;', '        "FRK_PersistFinish"(); RETURN;', '    END_IF;',
              '    CASE "FRK_PersistRuntime".Stage OF', '        1, 2, 8, 9:',
              '            #Operation := "FRK_PersistRuntime".Stage;',
              '            IF #Operation = 8 THEN #Operation := "FRK_PersistRuntime".Chosen + 2; ELSIF #Operation = 9 THEN #Operation := "FRK_PersistRuntime".Chosen; END_IF;',
              '            "FRK_PersistIo"(Operation := #Operation);', '            "FRK_PersistRuntime".NativeReq := FALSE;',
              '            IF "FRK_PersistRuntime".NativeBusy THEN RETURN; END_IF;',
              '            IF "FRK_PersistRuntime".NativeResult <> 0 THEN', '                "FRK_PersistRuntime".Result.ErrorId := WORD_TO_UDINT(INT_TO_WORD("FRK_PersistRuntime".NativeResult));',
              '                "FRK_PersistFinish"(); RETURN;', '            END_IF;',
              '            CASE "FRK_PersistRuntime".Stage OF', '                1: "FRK_PersistRuntime".Stage := 2;', '                2: "FRK_PersistRuntime".Stage := 3;',
              '                8: "FRK_PersistRuntime".Stage := 9;',
              '                9: "FRK_PersistRuntime".Stage := 10; IF "FRK_PersistRuntime".Chosen = 1 THEN "FRK_PersistRuntime".CheckA.Cursor := -1; ELSE "FRK_PersistRuntime".CheckB.Cursor := -1; END_IF;',
              '                ELSE RETURN;', '            END_CASE;', '            "FRK_PersistRuntime".NativeReq := TRUE;',
              '        3: IF "FRK_PersistCheckA"() THEN "FRK_PersistRuntime".Stage := 4; END_IF;',
              '        4: IF "FRK_PersistCheckB"() THEN "FRK_PersistRuntime".Stage := 5; END_IF;',
              '        5: "FRK_PersistInspect"();',
              '        6:', '            IF "FRK_PersistCheckWrite"() THEN', '                CASE "FRK_PersistRuntime".Slot OF']
        for d in self.documents:
            body += ['                    %d: "FRK_PersistPutNumber"(Bytes := "FRK_PersistBuffers".%sData, Offset := 20, Value := "FRK_PersistRuntime".CheckWrite.Crc);'%(d.index,d.tag)]
        body += ['                    ELSE RETURN;', '                END_CASE;', '                "FRK_PersistRuntime".Stage := 7;', '            END_IF;',
                 '        7:', '            IF NOT "FRK_PersistRuntime".HadWrite OR "FRK_Elapsed"(Started := "FRK_PersistRuntime".LastWriteMs, NowMs := "FRK_Clock".NowMs) >= %d THEN'%self.model.persistence_min_write_ms,
                 '                "FRK_PersistRuntime".HadWrite := TRUE; "FRK_PersistRuntime".LastWriteMs := "FRK_Clock".NowMs;',
                 '                "FRK_PersistRuntime".Stage := 8; "FRK_PersistRuntime".NativeReq := TRUE;', '            END_IF;',
                 '        10:', '            IF "FRK_PersistRuntime".Chosen = 1 THEN #Done := "FRK_PersistCheckA"(); #Check := "FRK_PersistRuntime".CheckA;',
                 '            ELSE #Done := "FRK_PersistCheckB"(); #Check := "FRK_PersistRuntime".CheckB; END_IF;',
                 '            IF #Done THEN', '                IF #Check.Valid AND #Check.Generation = "FRK_PersistRuntime".Generation AND #Check.Crc = "FRK_PersistRuntime".CheckWrite.Crc THEN',
                 '                    #Slot := "FRK_PersistRuntime".Slot;', '                    "FRK_PersistAnchors".Rows[#Slot].Generation := #Check.Generation;',
                 '                    "FRK_PersistAnchors".Rows[#Slot].DocumentCrc := #Check.Crc;',
                 '                    "FRK_PersistAnchors".Rows[#Slot].Checksum := "FRK_PersistAnchorCrc"(Image := "FRK_PersistAnchors".Rows[#Slot]);',
                 '                    "FRK_PersistCommitAnchor"(Slot := #Slot);',
                 '                    "FRK_PersistRuntime".Result.Ok := TRUE;',
                 '                ELSE "FRK_PersistRuntime".Result.ErrorId := %d; END_IF;'%FACTS['errors']['VERIFY_FAILED'],
                 '                "FRK_PersistFinish"();', '            END_IF;', '        ELSE', '            "FRK_PersistRuntime".Result.ErrorId := %d; "FRK_PersistFinish"();'%FACTS['errors']['INVALID_REQUEST'], '    END_CASE;']
        # Inspect dispatch has a distinct name from the shared open-array algorithm.
        body=[s.replace('5: "FRK_PersistInspect"();','5: "FRK_PersistInspectSlot"();') for s in body]
        text=text.replace('FUNCTION "FRK_PersistInspect" : Void\n','FUNCTION "FRK_PersistInspectSlot" : Void\n')
        text+=function('FRK_PersistTick',[],[],['Pick : Int;','Index : Int;','Slot : Int;','Operation : Int;','Done : Bool;','Check : "FRK_PersistCheck";'],body)
        body=['    #FRK_PersistPoll := TRUE; #Result := "FRK_PersistRuntime".EmptyResult;',
              '    #Result.ErrorId := %d;'%FACTS['errors']['INVALID_REQUEST'], '    "FRK_PersistTick"();', '    IF #Ticket = 0 THEN RETURN; END_IF;',
              '    FOR #Index := 1 TO %d DO'%q, '        IF "FRK_PersistRuntime".Queue[#Index].State <> 0 AND "FRK_PersistRuntime".Queue[#Index].Ticket = #Ticket THEN',
              '            #FRK_PersistPoll := "FRK_PersistRuntime".Queue[#Index].State = 3;',
              '            IF #FRK_PersistPoll THEN', '                #Result := "FRK_PersistRuntime".Queue[#Index].Result;',
              '                "FRK_PersistRuntime".Leased["FRK_PersistRuntime".Queue[#Index].Slot] := FALSE;',
              '                "FRK_PersistRuntime".Queue[#Index].State := 0;', '            END_IF;', '            RETURN;', '        END_IF;', '    END_FOR;']
        return text+function('FRK_PersistPoll',['Ticket : UDInt;'],['Result : "ST_PersistResult";'],['Index : Int;'],body,'Bool')

    def consumer_functions(self):
        text=''
        for d in self.documents:
            image='"FRK_PersistImages".'+d.tag
            data='"FRK_PersistBuffers".'+d.tag+'Data'
            scope=self.model.roots[d.root-1].name if d.root else 'users'
            if d.role == 'line':
                scope = self.model.line.owner
            capture=['    #FRK_DocCapture_'+d.tag+' := FALSE;',
                     '    '+image+'.SchemaVersion := 1; '+image+'.Scope := '+literal(scope)+';']
            validate=['    #FRK_DocApply_'+d.tag+' := FALSE;',
                      '    #Position := %d;'%FACTS['header_bytes'],
                      '    #NativeResult := Deserialize(SRC_ARRAY := '+data+', DEST_VARIABLE => '+image+', POS := #Position);',
                      '    IF #NativeResult <> 0 OR #Position <> %d + UDINT_TO_DINT("FRK_PersistConsumers".Rows[%d].Result.Length) THEN RETURN; END_IF;'%(FACTS['header_bytes'],d.index),
                      '    IF '+image+'.SchemaVersion <> 1 OR '+image+'.Scope <> '+literal(scope)+' THEN RETURN; END_IF;']
            apply=[]
            extra_temps=[]
            if d.role=='config':
                kind=d.entries[0][1].kind if d.entries else self.catalog.enums['E_ConfigKind']['STATION_CFG']
                capture += ['    '+image+'.Kind := %d;'%kind,'    '+image+'.ModelCode := '+literal(d.model)+';',
                            '    '+image+'.ActiveModel := "FRK_ConfigStore".ActiveModels[%d];'%d.root,
                            '    '+image+'.Count := %d;'%len(d.entries)]
                validate += ['    IF '+image+'.Kind <> %d OR '%kind+image+'.ModelCode <> '+literal(d.model)+' OR '+image+'.Count <> %d THEN RETURN; END_IF;'%len(d.entries)]
                codes=self.model.model_config or ('',)
                validate += ['    IF '+' AND '.join(image+'.ActiveModel <> '+literal(code) for code in codes)+' THEN RETURN; END_IF;']
                reserve=[]
                extra_temps=['Targets : Array[1..%d] of Int;'%max(1,len(d.entries)),'Prior : Int;','Reserved : Bool;']
                for ordinal,(instance,field) in enumerate(d.entries,1):
                    row=image+'.Rows[%d]'%ordinal
                    lookup='"FRK_ConfigFind"(Scope := '+literal(instance.path)+', Key := '+literal(field.key)+', ModelCode := '+literal(d.model)+')'
                    capture += ['    #Stored := '+lookup+';', '    IF #Stored = 0 THEN RETURN; END_IF;', '    '+row+' := "FRK_ConfigStore".Rows[#Stored];']
                    validate += ['    IF NOT '+row+'.Used OR '+row+'.SchemaVersion <> %d OR '%field.schema+row+'.ModelCode <> '+literal(d.model)+' OR '+row+'.Record.Scope <> '+literal(instance.path)+' OR '+row+'.Record.WriteKey <> '+literal(field.key)+' OR '+row+'.Record.Revision <> %d OR '%field.revision+row+'.Record.Kind <> %d OR '%field.kind+row+'.Record.ValueType <> %d THEN RETURN; END_IF;'%field.value_type,
                                 '    #Ok := "FRK_ConfigDecode"(Text := STRING_TO_WSTRING('+row+'.Record.ValueText), Storage := %d, Minimum := %s, Maximum := %s, MaxLength := %d, Value := "FRK_ConfigScratch".Value);'%(field.storage,str(float(field.minimum)),str(float(field.maximum)),field.length),
                                 '    IF NOT #Ok THEN RETURN; END_IF;']
                    reserve += ['    #Stored := '+lookup+';', '    IF #Stored = 0 THEN',
                                '        FOR #Index := 1 TO %d DO'%self.layout.capacity,
                                '            #Reserved := NOT "FRK_ConfigStore".Rows[#Index].Used;',
                                *(['            FOR #Prior := 1 TO %d DO IF #Targets[#Prior] = #Index THEN #Reserved := FALSE; END_IF; END_FOR;'%(ordinal-1)] if ordinal>1 else []),
                                '            IF #Reserved THEN #Stored := #Index; EXIT; END_IF;',
                                '        END_FOR;', '    END_IF;',
                                '    IF #Stored < 1 OR #Stored > %d THEN RETURN; END_IF;'%self.layout.capacity,
                                '    #Targets[%d] := #Stored;'%ordinal]
                    apply += ['    "FRK_ConfigStore".Rows[#Targets[%d]] := '%ordinal+row+';']
                # Reserve every destination before changing the cache. A full
                # or damaged cache cannot turn a valid document into a partial apply.
                validate += reserve
                if kind==self.catalog.enums['E_ConfigKind']['STATION_CFG']:
                    apply += ['    "FRK_ConfigStore".ActiveModels[%d] := '%d.root+image+'.ActiveModel;']
                apply += ['    "FRK_ConfigStore".SchemaVersion := 1;']
            elif d.role=='policy':
                capture += ['    #Stored := 0;', '    FOR #Index := 1 TO %d DO'%len(self.model.roots),
                            '        IF "FRK_AccessPolicies".Rows[#Index].Scope = '+literal(scope)+' THEN #Stored := #Index; END_IF;',
                            '    END_FOR;', '    IF #Stored = 0 THEN RETURN; END_IF;',
                            '    '+image+'.Image := "FRK_AccessPolicies".Rows[#Stored];',
                            '    IF NOT "FRK_AccessPolicyValid"(Image := '+image+'.Image) THEN RETURN; END_IF;']
                validate += ['    IF '+image+'.Image.Scope <> '+literal(scope)+' OR NOT "FRK_AccessPolicyValid"(Image := '+image+'.Image) THEN RETURN; END_IF;']
                apply += ['    "FRK_AccessPolicies".Rows[%d] := '%d.root+image+'.Image;']
            elif d.role=='classes':
                capture += ['    '+image+'.Image := "FRK_ClassPolicies".Rows[%d];'%d.root,
                            '    IF NOT "FRK_ClassValid"(Image := '+image+'.Image) THEN RETURN; END_IF;']
                validate += ['    IF '+image+'.Image.Scope <> '+literal(scope)+' OR NOT "FRK_ClassValid"(Image := '+image+'.Image) THEN RETURN; END_IF;']
                apply += ['    "FRK_ClassPolicies".Rows[%d] := '%d.root+image+'.Image;']
            elif d.role=='users':
                capture += ['    IF NOT "FRK_AccessStorage".UsersReady THEN RETURN; END_IF;']
                for member in ('Generation','Count','Rows','Checksum'):
                    capture += ['    '+image+'.'+member+' := "FRK_LocalUsers".'+member+';']
                    apply += ['    "FRK_LocalUsers".'+member+' := '+image+'.'+member+';']
                validate += ['    IF '+image+'.Generation = 0 OR NOT "FRK_AccessUsersShapeData"(Count := '+image+'.Count, Rows := '+image+'.Rows) THEN RETURN; END_IF;',
                             '    IF '+image+'.Checksum <> "FRK_AccessUsersCrcData"(SchemaVersion := '+image+'.SchemaVersion, Generation := '+image+'.Generation, Count := '+image+'.Count, Rows := '+image+'.Rows) THEN RETURN; END_IF;']
                apply += ['    "FRK_LocalUsers".SchemaVersion := 1; "FRK_AccessStorage".UsersCommissioned := TRUE;']
            elif d.role=='line':
                capture += ['    IF NOT "FRK_Line".Data.Applied OR "FRK_Line".Data.Image.Revision <> "FRK_Line".Data.Status.Revision THEN RETURN; END_IF;',
                            '    '+image+'.Image := "FRK_Line".Data.Image;']
                validate += ['    IF NOT "FRK_LineApply"(Image := '+image+'.Image, Restore := TRUE, NowMs := "FRK_Clock".NowMs, Stamp := LDT#1970-01-01-00:00:00, TimeSynchronized := FALSE, State := "FRK_Line".Data) THEN RETURN; END_IF;']
                apply += ['    "FRK_Line".Data.Dirty := FALSE;',
                          '    "FRK_Line".Data.BuiltRevision := "FRK_Line".Data.Status.Revision;']
            else:
                payload=image+'.Payload'
                capture += ['    '+image+'.Ordinal := %d;'%d.ordinal,
                            '    '+payload+' := "FRK_SetStore".Sets[%d, %d];'%(d.root,d.ordinal)]
                validate += ['    IF '+image+'.Ordinal <> %d THEN RETURN; END_IF;'%d.ordinal,
                             '    IF '+payload+'.Info.Used THEN',
                             '        "FRK_SetRuntime".Work[%d].Payload := '%d.root+payload+';',
                             '        IF NOT "FRK_SetShape"(RootIndex := %d, RootIdentity := %s) THEN RETURN; END_IF;'%(d.root,literal(scope)),
                             '    END_IF;']
                apply += ['    "FRK_SetStore".Sets[%d, %d] := '%(d.root,d.ordinal)+payload+';', '    "FRK_SetStore".SchemaVersion := 1;']
            # Stable private buffer is borrowed until its ticket is collected.
            capture += ['    FOR #Index := 0 TO %d DO '%(d.capacity+FACTS['header_bytes']-1)+data+'[#Index] := BYTE#0; END_FOR;',
                        '    #Position := %d;'%FACTS['header_bytes'],
                        '    #NativeResult := Serialize(SRC_VARIABLE := '+image+', DEST_ARRAY => '+data+', POS := #Position);',
                        '    IF #NativeResult <> 0 OR #Position < %d OR #Position > %d THEN RETURN; END_IF;'%(FACTS['header_bytes'],d.capacity+FACTS['header_bytes']),
                        '    #Length := #Position - %d;'%FACTS['header_bytes'],
                        '    #FRK_DocCapture_'+d.tag+' := TRUE;']
            validate+=apply+['    #FRK_DocApply_'+d.tag+' := TRUE;']
            temps=['Index : Int;','Stored : Int;','Position : DInt;','NativeResult : Int;','Ok : Bool;',*extra_temps]
            text+=function('FRK_DocCapture_'+d.tag,[],['Length : DInt;'],temps,capture,'Bool')
            text+=function('FRK_DocApply_'+d.tag,[],[],temps,validate,'Bool')
        text+=self.consumer_dispatch()
        return text

    def consumer_dispatch(self):
        docs=self.documents;n=len(docs)
        # Rejection withdraws only the affected domain; peers remain independent.
        b=['    CASE #Slot OF']
        for d in docs:
            b += ['        %d:'%d.index]
            if d.role=='config':
                for i,f in d.entries:
                    b += ['            #Stored := "FRK_ConfigFind"(Scope := '+literal(i.path)+', Key := '+literal(f.key)+', ModelCode := '+literal(d.model)+');',
                          '            IF #Stored > 0 THEN "FRK_ConfigStore".Rows[#Stored].Used := FALSE; END_IF;']
                b += ['            "FRK_ConfigLoss"(RootIndex := %d, Scope := %s);'%(d.root,literal(self.model.roots[d.root-1].name))]
            elif d.role=='users':
                b += ['            "FRK_LocalUsers".SchemaVersion := 0; "FRK_LocalUsers".Generation := 0; "FRK_LocalUsers".Checksum := DWORD#0;',
                      '            "FRK_AccessStorage".UsersCommissioned := TRUE; "FRK_AccessStorage".UsersReady := FALSE; "FRK_AccessStorage".UsersLost := TRUE;']
            elif d.role=='policy':
                scope=literal(self.model.roots[d.root-1].name)
                b += ['            "FRK_AccessPolicies".Rows[%d].Scope := %s;'%(d.root,scope),
                      '            "FRK_AccessPolicies".Rows[%d].SchemaVersion := 0;'%d.root,
                      '            "FRK_AccessPolicies".Rows[%d].Initialized := TRUE;'%d.root]
            elif d.role=='classes':
                b += ['            "FRK_ClassPolicies".Rows[%d].Scope := %s;'%(d.root,literal(self.model.roots[d.root-1].name)),
                      '            "FRK_ClassPolicies".Rows[%d].SchemaVersion := 0;'%d.root]
            elif d.role=='line':
                b += ['            "FRK_Line".Data.Dirty := FALSE;',
                      '            "FRK_Line".Data.Status.SourceError := 0;',
                      '            "FRK_ConfigLoss"(RootIndex := %d, Scope := %s);'%(d.root,literal(self.model.line.owner))]
            else:
                b += ['            "FRK_SetStore".Sets[%d, %d].Info.Used := FALSE;'%(d.root,d.ordinal),
                      '            "FRK_ConfigLoss"(RootIndex := %d, Scope := %s);'%(d.root,literal(self.model.roots[d.root-1].name))]
        b += ['        ELSE RETURN;', '    END_CASE;']
        text=function('FRK_DocReject',['Slot : Int;'],[],['Stored : Int;'],b)
        b=['    #Ok := FALSE; #Length := 0;', '    CASE #Slot OF']
        for d in docs:b += ['        %d: #Ok := "FRK_DocCapture_%s"(Length := #Length);'%(d.index,d.tag)]
        b += ['        ELSE RETURN;', '    END_CASE;']
        text+=function('FRK_DocCapture',['Slot : Int;'],['Ok : Bool;','Length : DInt;'],[],b)
        b=['    #FRK_DocApply := FALSE;', '    CASE #Slot OF']
        for d in docs:b += ['        %d: #FRK_DocApply := "FRK_DocApply_%s"();'%(d.index,d.tag)]
        b += ['        ELSE RETURN;', '    END_CASE;']
        text+=function('FRK_DocApply',['Slot : Int;'],[],[],b,'Bool')
        # Boot restoration precedes the existing frame startup and command acceptance.
        b=['    IF #Startup THEN', '        "FRK_PersistConsumers".Ready := FALSE;',
           '        FOR #Slot := 1 TO %d DO'%n,
           '            "FRK_PersistConsumers".Rows[#Slot].State := 0; "FRK_PersistConsumers".Rows[#Slot].Ticket := 0;',
           '            "FRK_PersistConsumers".Rows[#Slot].Dirty := FALSE; "FRK_PersistConsumers".Rows[#Slot].Failed := FALSE;',
           '            "FRK_PersistConsumers".Rows[#Slot].Rejected := FALSE; "FRK_PersistConsumers".Rows[#Slot].Acknowledged := FALSE;',
           '            "FRK_PersistConsumers".Rows[#Slot].RetrySince := "FRK_Clock".NowMs;',
           '            "FRK_PersistConsumers".Rows[#Slot].PendingSince := LDT#1970-01-01-00:00:00;',
           '            "FRK_PersistConsumers".Rows[#Slot].NextSince := LDT#1970-01-01-00:00:00;',
           '        END_FOR;', '    END_IF;',
           '    #Ready := TRUE;', '    "FRK_PersistStatus".Failed := FALSE;',
           '    FOR #Slot := 1 TO %d DO'%n,
           '        IF "FRK_PersistConsumers".Rows[#Slot].State = 0 THEN',
           '            IF NOT "FRK_PersistConsumers".Rows[#Slot].Failed OR "FRK_Elapsed"(NewMs := "FRK_Clock".NowMs, OldMs := "FRK_PersistConsumers".Rows[#Slot].RetrySince) >= %d THEN'%FACTS['retry_ms'],
           '                "FRK_PersistConsumers".Rows[#Slot].Ticket := "FRK_PersistStart"(Slot := #Slot, WriteDocument := FALSE, Length := 0);',
           '                IF "FRK_PersistConsumers".Rows[#Slot].Ticket <> 0 THEN "FRK_PersistConsumers".Rows[#Slot].State := 1; END_IF;', '            END_IF;',
           '        ELSIF "FRK_PersistConsumers".Rows[#Slot].State = 1 THEN',
           '            #Done := "FRK_PersistPoll"(Ticket := "FRK_PersistConsumers".Rows[#Slot].Ticket, Result := "FRK_PersistConsumers".Rows[#Slot].Result);',
           '            IF #Done THEN', '                "FRK_PersistConsumers".Rows[#Slot].Ticket := 0;',
           '                IF NOT "FRK_PersistConsumers".Rows[#Slot].Result.Ok THEN',
           '                    "FRK_PersistConsumers".Rows[#Slot].Failed := TRUE; "FRK_PersistConsumers".Rows[#Slot].State := 0;',
           '                    "FRK_PersistConsumers".Rows[#Slot].RetrySince := "FRK_Clock".NowMs;',
           '                ELSE', '                    "FRK_PersistConsumers".Rows[#Slot].Failed := FALSE;',
           '                    #Ok := NOT "FRK_PersistConsumers".Rows[#Slot].Result.Lost;',
           '                    "FRK_PersistConsumers".Rows[#Slot].Virgin := #Ok AND NOT "FRK_PersistConsumers".Rows[#Slot].Result.Found;',
           '                    IF #Ok AND "FRK_PersistConsumers".Rows[#Slot].Result.Found THEN #Ok := "FRK_DocApply"(Slot := #Slot); END_IF;',
           '                    IF NOT #Ok THEN', '                        "FRK_DocReject"(Slot := #Slot);',
           '                        "FRK_PersistConsumers".Rows[#Slot].Rejected := TRUE;',
           '                    ELSIF "FRK_PersistConsumers".Rows[#Slot].Virgin THEN '+(
               'IF #Slot <> %d OR "FRK_Line".Data.Applied THEN "FRK_PersistDirty"(Slot := #Slot); END_IF;'%next(d.index for d in docs if d.role=='line')
               if self.model.line and self.model.line.role == 'MIRROR' else '"FRK_PersistDirty"(Slot := #Slot);')+' END_IF;',
           '                    "FRK_PersistConsumers".Rows[#Slot].State := 2;', '                END_IF;', '            END_IF;',
           '        END_IF;', '        IF "FRK_PersistConsumers".Rows[#Slot].State <> 2 THEN #Ready := FALSE; END_IF;',
           '        "FRK_PersistStatus".Failed := "FRK_PersistStatus".Failed OR "FRK_PersistConsumers".Rows[#Slot].Failed;', '    END_FOR;',
           '    "FRK_PersistStatus".Restoring := NOT #Ready;',
           '    "FRK_PersistStatus".NativeStatus := INT_TO_WORD("FRK_PersistRuntime".NativeResult);',
           '    "FRK_PersistConsumers".Ready := #Ready;']
        text+=function('FRK_DocBoot',['Startup : Bool;'],['Ready : Bool;'],['Slot : Int;','Done : Bool;','Ok : Bool;'],b)
        b=['    IF NOT "FRK_PersistConsumers".Ready THEN RETURN; END_IF;',
           '    FOR #Slot := 1 TO %d DO'%n,
           '        IF "FRK_PersistConsumers".Rows[#Slot].Ticket <> 0 THEN',
           '            #Done := "FRK_PersistPoll"(Ticket := "FRK_PersistConsumers".Rows[#Slot].Ticket, Result := "FRK_PersistConsumers".Rows[#Slot].Result);',
           '            IF #Done THEN', '                "FRK_PersistConsumers".Rows[#Slot].Ticket := 0;',
           '                "FRK_PersistConsumers".Rows[#Slot].Failed := NOT "FRK_PersistConsumers".Rows[#Slot].Result.Ok;',
           '                "FRK_PersistConsumers".Rows[#Slot].RetrySince := "FRK_Clock".NowMs;',
           '                IF "FRK_PersistConsumers".Rows[#Slot].Failed THEN "FRK_PersistConsumers".Rows[#Slot].Dirty := TRUE;',
           '                ELSIF "FRK_PersistConsumers".Rows[#Slot].Dirty THEN "FRK_PersistConsumers".Rows[#Slot].PendingSince := "FRK_PersistConsumers".Rows[#Slot].NextSince;',
           '                ELSE "FRK_PersistConsumers".Rows[#Slot].PendingSince := LDT#1970-01-01-00:00:00; END_IF;', '            END_IF;',
           '        ELSIF "FRK_PersistConsumers".Rows[#Slot].Dirty AND (NOT "FRK_PersistConsumers".Rows[#Slot].Rejected OR "FRK_PersistConsumers".Rows[#Slot].Acknowledged) THEN',
           '            IF NOT "FRK_PersistConsumers".Rows[#Slot].Failed OR "FRK_Elapsed"(NewMs := "FRK_Clock".NowMs, OldMs := "FRK_PersistConsumers".Rows[#Slot].RetrySince) >= %d THEN'%FACTS['retry_ms'],
           '                "FRK_DocCapture"(Slot := #Slot, Ok := #Ok, Length := #Length);',
           '                IF #Ok THEN', '                    "FRK_PersistConsumers".Rows[#Slot].Ticket := "FRK_PersistStart"(Slot := #Slot, WriteDocument := TRUE, Length := #Length);',
           '                    IF "FRK_PersistConsumers".Rows[#Slot].Ticket <> 0 THEN "FRK_PersistConsumers".Rows[#Slot].Dirty := FALSE; END_IF;',
           '                ELSE "FRK_PersistConsumers".Rows[#Slot].Failed := TRUE; "FRK_PersistConsumers".Rows[#Slot].RetrySince := "FRK_Clock".NowMs; END_IF;', '            END_IF;',
           '        END_IF;', '    END_FOR;']
        text+=function('FRK_DocCyclic',[],[],['Slot : Int;','Done : Bool;','Ok : Bool;','Length : DInt;'],b)
        return text

    def inputs(self):
        return {p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (POLICY,TEMPLATE,__import__('pathlib').Path(__file__))}

    def hooks(self):
        n=len(self.documents)
        b=['    IF #Slot < 1 OR #Slot > %d THEN RETURN; END_IF;'%n,
           '    IF NOT "FRK_PersistConsumers".Rows[#Slot].Dirty THEN',
           '        #NativeResult := RD_SYS_T(OUT => #Stamp);',
           '        IF "FRK_PersistConsumers".Rows[#Slot].Ticket = 0 THEN "FRK_PersistConsumers".Rows[#Slot].PendingSince := #Stamp;',
           '        ELSE "FRK_PersistConsumers".Rows[#Slot].NextSince := #Stamp; END_IF;',
           '    END_IF;', '    "FRK_PersistConsumers".Rows[#Slot].Dirty := TRUE;']
        text=function('FRK_PersistDirty',['Slot : Int;'],[],['Stamp : LDT;','NativeResult : Int;'],b)
        b=['    #FRK_PersistConfigSlot := 0;']
        for d in self.documents:
            if d.role!='config':continue
            for instance,field in d.entries:
                b += ['    IF #Scope = '+literal(instance.path)+' AND #ModelCode = '+literal(d.model)+' AND #Kind = %d THEN #FRK_PersistConfigSlot := %d; RETURN; END_IF;'%(field.kind,d.index)]
        text+=function('FRK_PersistConfigSlot',['Scope : String;','ModelCode : String;','Kind : DInt;'],[],[],b,'Int')
        for role in ('users','policy','set','model', *(['classes'] if self.model.data_classes else [])):
            inputs=[] if role=='users' else ['RootIndex : Int;']
            if role=='set':inputs+=['Ordinal : Int;']
            b=[]
            for d in self.documents:
                matches=d.role==role or (role=='model' and d.role=='config' and (not d.entries or d.entries[0][1].kind==self.catalog.enums['E_ConfigKind']['STATION_CFG']))
                if not matches:continue
                condition='' if role=='users' else 'IF #RootIndex = %d'%d.root+(' AND #Ordinal = %d'%d.ordinal if role=='set' else '')+' THEN '
                b += ['    '+condition+'"FRK_PersistDirty"(Slot := %d);'%d.index+(' END_IF;' if condition else '')]
            text+=function('FRK_Persist'+role.title()+'Dirty',inputs,[],[],b)
        b=['    #FRK_PersistVirginConfig := FALSE;',
           '    #Slot := "FRK_PersistConfigSlot"(Scope := #Scope, ModelCode := #ModelCode, Kind := #Kind);',
           '    IF #Slot > 0 THEN #FRK_PersistVirginConfig := "FRK_PersistConsumers".Rows[#Slot].Virgin; END_IF;']
        text+=function('FRK_PersistVirginConfig',['Scope : String;','ModelCode : String;','Kind : DInt;'],[],['Slot : Int;'],b,'Bool')
        if self.model.line:
            d = next(d for d in self.documents if d.role == 'line')
            text += function('FRK_PersistLineTick', [], [], [], [
                '    IF "FRK_PersistConsumers".Ready AND "FRK_Line".Data.Dirty THEN',
                '        "FRK_PersistDirty"(Slot := %d);'%d.index,
                '        "FRK_Line".Data.Dirty := FALSE;', '    END_IF;'])
        return text

    def root_condition(self, document):
        if document.role == 'line':
            return ' OR '.join('#RootIndex = %d'%i for i, r in enumerate(self.model.roots, 1) if r.name in self.model.line.roots)
        return '#RootIndex = %d'%document.root if document.root else ''

    def status_functions(self):
        b=['    IF #RootIndex < 1 OR #RootIndex > %d THEN RETURN; END_IF;'%len(self.model.roots),
           '    #Persist.Pending := FALSE; #Persist.PendingSince := LDT#1970-01-01-00:00:00;',
           '    #Persist.WindowMs := %d;'%self.window]
        for d in self.documents:
            c='"FRK_PersistConsumers".Rows[%d]'%d.index
            condition = self.root_condition(d)
            cond = 'IF '+condition+' THEN ' if condition else ''
            b+=['    '+cond,
                '        #Persist.Failed := #Persist.Failed OR '+c+'.Failed;',
                '        IF '+c+'.Dirty OR '+c+'.Ticket <> 0 THEN',
                '            #Persist.Pending := TRUE;',
                '            IF #Persist.PendingSince = LDT#1970-01-01-00:00:00 OR ('+c+'.PendingSince <> LDT#1970-01-01-00:00:00 AND '+c+'.PendingSince < #Persist.PendingSince) THEN #Persist.PendingSince := '+c+'.PendingSince; END_IF;',
                '        END_IF;']
            if cond:b+=['    END_IF;']
            if d.role == 'line':
                b += ['    IF ('+condition+') AND '+c+'.Rejected AND NOT '+c+'.Acknowledged THEN',
                      '        #Persist.RestoreLost := TRUE; #Persist.RestoreAcknowledged := FALSE;',
                      '        #Persist.LostPath := '+literal(self.model.line.owner)+';', '    END_IF;']
        # Wall clock is display-only; the store's bounded service window uses monotonic time.
        b+=['    IF #Persist.Pending THEN',
            '        IF "FRK_PersistRootSince".WasPending[#RootIndex] THEN',
            '            IF "FRK_Elapsed"(NewMs := "FRK_Clock".NowMs, OldMs := "FRK_PersistRootSince".SinceMs[#RootIndex]) > #Persist.WindowMs THEN #Persist.Failed := TRUE; END_IF;',
            '        ELSE "FRK_PersistRootSince".SinceMs[#RootIndex] := "FRK_Clock".NowMs; END_IF;',
            '    END_IF;', '    "FRK_PersistRootSince".WasPending[#RootIndex] := #Persist.Pending;']
        text=function('FRK_PersistRootStatus',['RootIndex : Int;'],['Persist : "ST_ConfigPersistStatus";'],[],b)
        b=[]
        for d in self.documents:
            if not d.root:continue
            c='"FRK_PersistConsumers".Rows[%d]'%d.index
            condition = '('+self.root_condition(d)+')' if d.role == 'line' else self.root_condition(d)
            b+=['    IF '+condition+' AND '+c+'.Rejected THEN',
                '        '+c+'.Acknowledged := TRUE;', '        "FRK_PersistRepair"(Slot := %d);'%d.index,
                '        "FRK_PersistDirty"(Slot := %d);'%d.index, '    END_IF;']
            if d.role == 'line':
                b += ['    IF ('+self.root_condition(d)+') AND '+c+'.Acknowledged AND "FRK_ConfigStore".LostPath[%d] = '%d.root+literal(self.model.line.owner)+' THEN',
                      '        "FRK_ConfigStore".Acknowledged[%d] := TRUE;'%d.root, '    END_IF;']
        return text+function('FRK_PersistAckRoot',['RootIndex : Int;'],[],[],b)

    def adapt(self, sources):
        from fraktal_tia_generate import db
        sources.update(self.sources())
        sources['11_PersistHooks.scl']=self.hooks()
        sources['16_PersistStatus.scl']=self.status_functions()
        sources['06_FRK_PersistRootSince.db']=db('FRK_PersistRootSince',['SinceMs'+PRIVATE+' : Array[1..%d] of UDInt;'%len(self.model.roots),'WasPending'+PRIVATE+' : Array[1..%d] of Bool;'%len(self.model.roots)])
        # Generic validation receives a candidate, so privileged data is never
        # installed merely to check its CRC. One owning algorithm serves both.
        p=next(k for k,s in sources.items() if 'FUNCTION "FRK_AccessUsersCrc"' in s);s=sources[p]
        for role,result in (('Crc','DWord'),('Shape','Bool')):
            old='FRK_AccessUsers'+role;new=old+'Data'
            pattern=r'FUNCTION "'+old+r'" : '+result+r'\n.*?END_FUNCTION\n'
            match=re.search(pattern,s,re.S);assert match
            generic=match[0].replace(old,new).replace('"FRK_LocalUsers".','#')
            declarations=('VAR_INPUT\n    Count : DInt;\n'+('    SchemaVersion : UInt;\n    Generation : UDInt;\n' if role=='Crc' else '')+'END_VAR\nVAR_IN_OUT\n    Rows : Array[1..%d] of "ST_UserRecord";\nEND_VAR\n'%self.catalog.capacities['MAX_USERS'])
            generic=generic.replace('VAR_TEMP\n',declarations+'VAR_TEMP\n',1)
            args=['Count := "FRK_LocalUsers".Count','Rows := "FRK_LocalUsers".Rows']
            if role=='Crc':args+=['SchemaVersion := "FRK_LocalUsers".SchemaVersion','Generation := "FRK_LocalUsers".Generation']
            wrapper=function(old,[],[],[],['    #'+old+' := "'+new+'"('+', '.join(args)+');'],result)
            s=s[:match.start()]+generic+wrapper+s[match.end():]
        a='    "FRK_AccessStorage".UsersLost := FALSE;\nEND_FUNCTION\n\nFUNCTION "FRK_AccessRegisterHash"'
        assert s.count(a)==1
        users=next(d for d in self.documents if d.role=='users')
        s=s.replace(a,'    "FRK_AccessStorage".UsersLost := FALSE;\n    IF "FRK_PersistConsumers".Ready THEN\n        "FRK_PersistConsumers".Rows[%d].Acknowledged := TRUE;\n        "FRK_PersistRepair"(Slot := %d);\n        "FRK_PersistUsersDirty"();\n    END_IF;\nEND_FUNCTION\n\nFUNCTION "FRK_AccessRegisterHash"'%(users.index,users.index))
        a='    "FRK_AccessPolicies".Rows[#Access.PolicySlot].Checksum := "FRK_AccessPolicyCrc"(Image := "FRK_AccessPolicies".Rows[#Access.PolicySlot]);'
        assert s.count(a)==1
        b='\n'.join('    IF #Scope = '+literal(self.model.roots[d.root-1].name)+' THEN "FRK_PersistPolicyDirty"(RootIndex := %d); END_IF;'%d.root for d in self.documents if d.role=='policy')
        s=s.replace(a,a+'\n'+b)
        sources[p]=s
        if self.model.data_classes:
            marker='    "FRK_ClassPolicies".Rows[#Access.ClassSlot].Checksum := "FRK_ClassCrc"(Image := "FRK_ClassPolicies".Rows[#Access.ClassSlot]);'
            p='13_UnitServices.scl';s=sources[p]
            assert s.count(marker)==1
            s=s.replace(marker,marker+'\n    IF "FRK_PersistConsumers".Ready THEN "FRK_PersistClassesDirty"(RootIndex := #Access.ClassSlot); END_IF;')
            sources[p]=s
        # Public live write still owns all validation; the medium is a side effect
        # only after success, and unchanged values do not wear flash.
        p='14_ConfigServices.scl';s=sources[p]
        s=s.replace('FUNCTION "FRK_ConfigPut" : Bool','FUNCTION "FRK_ConfigPutRaw" : Bool',1)
        start=s.index('FUNCTION "FRK_ConfigPutRaw"');end=s.index('END_FUNCTION',start)
        body=s[start:end].replace('#FRK_ConfigPut :=','#FRK_ConfigPutRaw :=')
        s=s[:start]+body+s[end:]
        wrapper=function('FRK_ConfigPut',['Scope : String;','ModelCode : String;','Text : WString;','RootIndex : Int;'],[],['Stored : Int;','Changed : Bool;','Slot : Int;'],[
            '    #Stored := "FRK_ConfigFind"(Scope := #Scope, Key := "FRK_ConfigScratch".Entry.WriteKey, ModelCode := #ModelCode);',
            '    #Changed := #Stored = 0;',
            '    IF #Stored > 0 THEN #Changed := "FRK_ConfigStore".Rows[#Stored].SchemaVersion <> "FRK_ConfigScratch".Schema OR "FRK_ConfigStore".Rows[#Stored].Record.Revision <> "FRK_ConfigScratch".Entry.WriteRevision OR "FRK_ConfigStore".Rows[#Stored].Record.ValueText <> WSTRING_TO_STRING(#Text); END_IF;',
            '    #FRK_ConfigPut := "FRK_ConfigPutRaw"(Scope := #Scope, ModelCode := #ModelCode, Text := #Text, RootIndex := #RootIndex);',
            '    IF #FRK_ConfigPut AND #Changed THEN',
            '        #Slot := "FRK_PersistConfigSlot"(Scope := #Scope, ModelCode := #ModelCode, Kind := "FRK_ConfigScratch".Entry.ConfigKind);',
            '        IF #Slot > 0 THEN "FRK_PersistDirty"(Slot := #Slot); END_IF;', '    END_IF;'],'Bool')
        pos=s.index('END_FUNCTION',s.index('FUNCTION "FRK_ConfigPutRaw"'))+len('END_FUNCTION\n')
        s=s[:pos]+'\n'+wrapper+s[pos:]
        # Root status is evaluated from the existing mandatory frame path.
        pos=s.index('END_FUNCTION',s.index('FUNCTION "FRK_ConfigStatus"'))
        s=s[:pos]+'    "FRK_PersistRootStatus"(RootIndex := #RootIndex, Persist := #Persist);\n'+s[pos:]
        sources[p]=s
        for p,s in list(sources.items()):
            if not p.startswith('20_') or not p.endswith('.scl'):continue
            a='    Startup'+PRIVATE+' : Bool;'
            assert s.count(a)==1
            s=s.replace(a,a+'\n    BoundPath'+PRIVATE+' : WString[254];')
            a='        #InstancePath := GetInstancePath(SIZE := 0);'
            assert s.count(a)==1
            s=s.replace(a,'        #InstancePath := #BoundPath;')
            s=re.sub(r'(Startup := #Startup, Hal := #Hal\.(\w+))\);',lambda m:m[1]+', BoundPath := CONCAT(IN1 := #BoundPath, IN2 := WSTRING#'+literal('.'+m[2])+'));',s)
            a='                    "FRK_ConfigStore".ActiveModels[#RootIndex] := #Desired;'
            if a in s:s=s.replace(a,a+'\n                    "FRK_PersistModelDirty"(RootIndex := #RootIndex);')
            for prefix in ('#Module.','#'):
                a='IF '+prefix+'HmiResponse.Accepted THEN "FRK_ConfigStore".Acknowledged[#RootIndex] := TRUE;'
                if a in s:s=s.replace(a,a+' "FRK_PersistAckRoot"(RootIndex := #RootIndex);')
            a='            IF #Module.HmiResponse.Accepted THEN\n'
            # Set apply writes the already validated records directly. It shares
            # the same document dirty hook as individual configuration writes.
            pattern=r'^(\s*)("FRK_ConfigStore"\.Rows\[#Stored\]\.Record) := ("FRK_SetRuntime"\.Work\[#RootIndex\]\.Payload\.Records\[#Slot\]);$'
            def set_record(hit):
                indent, target, record = hit.groups()
                return (indent+'IF '+target+'.ValueText <> '+record+'.ValueText THEN\n'
                        +indent+'    "FRK_PersistDirty"(Slot := "FRK_PersistConfigSlot"(Scope := '+record+'.Scope, ModelCode := "FRK_SetRuntime".Work[#RootIndex].Payload.Info.ModelCode, Kind := '+record+'.Kind));\n'
                        +indent+'END_IF;\n'+hit[0])
            s=re.sub(pattern,set_record,s,flags=re.M)
            # Set operations run once in their own service; import chunks are not durable yet.
            if 'FUNCTION "FRK_CfgSetOperation_' in s:
                i=s.index('FUNCTION "FRK_CfgSetOperation_');part=s[i:]
                marker='END_FUNCTION'
                end=part.index(marker)
                prefix='#Module.' if 'Module :' in part[:part.index('BEGIN')] else '#'
                part=part[:end]+'    IF '+prefix+'HmiResponse.Accepted AND (#Request.Kind = %d OR #Request.Kind = %d OR (#Request.Kind = %d AND #Request.BoolValue)) THEN\n        "FRK_PersistSetDirty"(RootIndex := #RootIndex, Ordinal := #Slot);\n    END_IF;\n'%(self.catalog.enums['E_HmiRequestKind']['SAVE_CONFIG_SET'],self.catalog.enums['E_HmiRequestKind']['DELETE_CONFIG_SET'],self.catalog.enums['E_HmiRequestKind']['IMPORT_CONFIG_SET'])+part[end:]
                s=s[:i]+part
            sources[p]=s
        self.adapt_main(sources)

    def adapt_main(self, sources):
        # A cold restore withdraws old commands/outputs through the same owning
        # abort hooks, before any asynchronous storage operation can wait.
        quiesce=self.quiesce(sources)
        sources['23_PersistQuiesce.scl']=quiesce
        s=sources['30_FB_FraktalMain.scl']
        assert s.count('END_VAR\nBEGIN')==1
        s=s.replace('END_VAR\nBEGIN','END_VAR\nVAR\n    MediaBoot'+PRIVATE+' : Bool := TRUE;\nEND_VAR\nVAR_TEMP\n    MediaReady : Bool;\n    RootStartup : Bool;\nEND_VAR\nBEGIN',1)
        a='    "FRK_ClockTick"();'
        assert s.count(a)==1
        early=['    IF #Startup THEN']
        for root in self.model.roots:
            t=self.layout.lookup[root.type_name.casefold()]
            early+=['        "FRK_Quiesce_'+t.name.removeprefix('FB_')+'"(Module := "'+root.name+'", Hal := "GDB_FraktalHal".Data.'+root.name+');']
        early+=['    END_IF;']
        anchor='BEGIN\n    IF #Startup THEN'
        assert s.count(anchor)==1
        s=s.replace(anchor,'BEGIN\n'+'\n'.join(early)+'\n    IF #Startup THEN')
        boot=[a,'    IF #Startup THEN #MediaBoot := TRUE; END_IF;',
              '    "FRK_PersistEnter"(Startup := #Startup);',
              '    "FRK_DocBoot"(Startup := #Startup, Ready := #MediaReady);',
              '    IF NOT #MediaReady THEN']
        if self.model.line:
            line_boot = self.layout.line.boot_call()
            assert s.count(line_boot) == 1
            s = s.replace(line_boot+'\n', '')
            boot.insert(1, line_boot)
        for root in self.model.roots:
            boot += ['        "'+root.name+'".ConfigPersist.Failed := "FRK_PersistStatus".Failed;']
        boot+=['        RETURN;', '    END_IF;', '    #RootStartup := #MediaBoot; #MediaBoot := FALSE;']
        s=s.replace(a,'\n'.join(boot))
        # Restore and lifecycle each consume one real startup after the barrier.
        before,after=s.split('    #RootStartup := #MediaBoot; #MediaBoot := FALSE;',1)
        after=after.replace('Startup := #Startup','Startup := #RootStartup')
        for root in self.model.roots:
            a='Hal := "GDB_FraktalHal".Data.'+root.name+');'
            assert after.count(a)==1
            after=after.replace(a,'Hal := "GDB_FraktalHal".Data.'+root.name+', BoundPath := WSTRING#'+literal(root.name)+');')
        after=after.replace('END_FUNCTION_BLOCK',('    "FRK_PersistLineTick"();\n' if self.model.line else '')+'    "FRK_DocCyclic"();\nEND_FUNCTION_BLOCK')
        sources['30_FB_FraktalMain.scl']=before+'    #RootStartup := #MediaBoot; #MediaBoot := FALSE;'+after

    def quiesce(self,sources):
        text=''
        for p in sorted(sources):
            if not p.startswith('20_') or not p.endswith('.scl'):continue
            source=sources[p]
            hit=re.search(r'FUNCTION_BLOCK "([^"]+)"',source)
            if not hit:continue
            t=self.layout.lookup[hit[1].casefold()]
            name=t.name.removeprefix('FB_')
            declaration=source[hit.start():source.index('\nBEGIN\n',hit.start())]
            mirror=re.search(r'^\s+OutImm\s*\{[^}]*\}\s*:\s*[^;]+;\n',declaration,re.M)
            assert mirror
            # The owning cyclic hook mutates a published mirror. Use static
            # storage rather than borrowing an uninitialized VAR_OUTPUT.
            moved=declaration[:mirror.start()]+declaration[mirror.end():]
            moved, count = re.subn(r'^VAR\n', lambda _: 'VAR\n'+mirror[0].lstrip('\n'), moved, count=1, flags=re.M)
            assert count == 1
            source=source[:hit.start()]+moved+source[hit.start()+len(declaration):]
            declaration=moved
            variables={}
            for section in re.finditer(r'\b(VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|VAR)\n(.*?)END_VAR',declaration,re.S):
                for field in re.finditer(r'^\s*(\w+)(?:\s*\{[^}]*\})?\s*:\s*([^;]+);',section[2],re.M):
                    variables[field[1]]=field[2].split(':=')[0].strip()
            abort=dict(t.logic).get('Abort','')
            required=[]
            if abort.strip():
                required=sorted(set(re.findall(r'#(\w+)',abort)))
                if set(required)-variables.keys():
                    self.reject(t.name+' abort hook refers to a non-owning temporary')
                helper='FRK_AbortHook_'+name
                helper_text=function(helper,[],[n+' : '+variables[n]+';' for n in required],[],abort.splitlines())
                marker='    // ---- AUTHORED: Abort\n'+abort+'\n    // ---- GENERATED: reaction end'
                assert source.count(marker)==1
                call='"'+helper+'"('+', '.join(n+' := #'+n for n in required)+');'
                source=helper_text+source.replace(marker,'    // ---- AUTHORED: Abort\n    '+call+'\n    // ---- GENERATED: reaction end')
                sources[p]=source
            derived=re.search(r'    // ---- AUTHORED: unconditional cyclic/derived data\n(.*?)\n    // ---- GENERATED: (?:diagnostic snapshot|frame end)',source,re.S)
            assert derived
            cyclic=derived[1]
            cyclic_required=sorted(set(re.findall(r'#(\w+)',cyclic)))
            if set(cyclic_required)-variables.keys():self.reject(t.name+' cyclic hook refers to a non-owning temporary')
            cyclic_helper='FRK_CyclicHook_'+name
            cyclic_text=function(cyclic_helper,[],[n+' : '+variables[n]+';' for n in cyclic_required],[],cyclic.splitlines())
            cyclic_call='"'+cyclic_helper+'"('+', '.join(n+' := #'+n for n in cyclic_required)+');'
            source=cyclic_text+source[:derived.start(1)]+'    '+cyclic_call+source[derived.end(1):]
            sources[p]=source
            body=['    #Module.Execute := FALSE; #Module.Abort := FALSE;',
                  '    #WasBusy := #Module.Core.Exec = %d;'%self.catalog.enums['E_ExecState']['BUSY'],
                  '    "FRK_RouteAbort"(Abort := TRUE, Core := #Module.Core);']
            if abort.strip():
                args=', '.join(n+' := '+('#Hal' if n=='Hal' else '#Module.'+n) for n in required)
                body+=['    IF #WasBusy THEN "FRK_AbortHook_'+name+'"('+args+'); END_IF;']
            body+=['    IF #Module.Core.RegIndex > 0 THEN',
                   '        "FRK_End"(Core := #Module.Core, Status := #Module.Status, '+', '.join(n+' => #Module.'+n for n in ('Busy','Done','Error','Aborted','Held','ErrorID','Timing'))+');',
                   '    END_IF;']
            if t.unit_modes:
                body+=['    "FRK_AccessDropSession"(Access := #Module.Access);','    "FRK_AccessCancel"(Access := #Module.Access);', '    #Module.RunningPublished := FALSE;']
                if t.sequence_view:
                    from fraktal_tia_sequence_view import mirror
                    body+=['    "FRK_SeqViewWithdraw"(Owner := #Module.Core.RegIndex);',
                           '    "FRK_SeqLifecycleUpdate"(Owner := #Module.Core.RegIndex, Exec := #Module.Core.Exec, Restart := TRUE);',
                           '    #Module.Pending := "FRK_ViewScratch".Diagnostic;',*mirror(t,self.model,owner='#Module.')]
                    from fraktal_tia_profile import prepare as profile_prepare
                    body+=profile_prepare(t,self.catalog,owner='#Module.',withdraw=True)
                    body+=['    #Module.Starved := FALSE; #Module.Blocked := FALSE;']
            body+=['    "'+cyclic_helper+'"('+', '.join(n+' := '+('#Hal' if n=='Hal' else '#Module.'+n) for n in cyclic_required)+');']
            for child in t.children:
                ct=self.layout.lookup[child.type_name.casefold()]
                body+=['    "FRK_Quiesce_'+ct.name.removeprefix('FB_')+'"(Module := #Module.'+child.name+', Hal := #Hal.'+child.name+');']
            if any(x.sequence_view for x in self.model.types):
                from fraktal_tia_diagnostics import sync
                body+=sync(t,self.model,owner='#Module.',withdraw=True)
            text+=function('FRK_Quiesce_'+name,[],['Module : "'+t.name+'";','Hal : '+variables['Hal']+';'],['WasBusy : Bool;'],body)
        return text
