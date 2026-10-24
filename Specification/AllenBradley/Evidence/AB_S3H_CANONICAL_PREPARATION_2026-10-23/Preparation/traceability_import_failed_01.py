"""S3h engineering publication of existing traceability and indication owners.

No append, carrier or lamp policy lives here. Private caches translate the
owners' committed records only when their revisions change. Bounds come from
the application; logical occupied ring slots come from the published Count.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_status as clock
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_genealogy as genealogy
import fraktal_ab_host_events as host
import fraktal_ab_nameplate as nameplate
import fraktal_ab_part as part
import fraktal_ab_resources as resources
import fraktal_ab_signal_tower as tower

P=pub.PREFIX
MEAS=P+'MeasurementS3hV63'
RESULT=P+'PartResultS3hV63'
PART=P+'PartS3hV63'
EVENT=P+'HostEventS3hV63'
RING=P+'HostEventsS3hV63'
PLATE=P+'NameplateS3hV63'
TOWER=P+'SignalTowerS3hV63'
WORK=P+'TraceWorkS3hV63'
DEFINITION=P+'MeasurementDefinitionS3hV63'
DEFINITIONS=P+'MeasurementDefinitionsS3hV63'
PLATE_FIELDS=(('product_uri','ProductUri',255),('manufacturer','ManufacturerName',80),
    ('product','ProductDesignation',80),('serial','SerialNumber',40),
    ('year','YearOfConstruction',8),('hardware_version','HardwareVersion',24),
    ('firmware_version','FirmwareVersion',24),('software_version','SoftwareVersion',24),
    ('order_code','OrderCode',40),('documentation_url','DocumentationUrl',255))


def state_tag(app):return f'FRK_{app.name}_CanonicalTraceState'
def definitions_tag(app):return f'FRK_{app.name}_CanonicalMeasurementDefinitions'
def routine(app,suffix):return f'FRK_{app.name}_CanonicalTrace{suffix}'


def validate(app):
    findings=[]
    for owner in (app,*app.modules):
        if owner.nameplate is not None:
            for attribute,_,width in PLATE_FIELDS:
                if len(getattr(owner.nameplate,attribute).encode('utf-8'))>width:
                    findings.append(f'S3h {owner.name} nameplate {attribute} exceeds its Core width')
    if app.part_carrier is not None:
        if app.part_carrier.result_capacity>core.core_limit('MAX_RESULTS'):
            findings.append('S3h result capacity exceeds Core MAX_RESULTS')
        for record in app.part_carrier.records:
            if len(record.name.encode('utf-8'))>64 or len(record.unit.encode('utf-8'))>16:
                findings.append('S3h measurement text exceeds its Core width')
    if app.host_event_capacity>core.core_limit('MAX_HOST_EVENTS'):
        findings.append('S3h host ring capacity exceeds Core MAX_HOST_EVENTS')
    return findings


def augment(app,definitions):
    M=pub.Member;S=pub.string_type;parents=genealogy.capacity(app)
    definitions[MEAS]=(M('Name',S(64)),*(M(n,'LREAL') for n in ('Value','Minimum','Maximum','Target')),M('Unit',S(16)),M('InTol','BOOL'))
    if app.part_carrier is not None:
        definitions[RESULT]=(M('Verdict','DINT','ENUM'),M('ReasonCode','DINT','ENUM'),
            M('Records',MEAS,count=app.part_carrier.result_capacity,lower=1),
            M('StationPath',S(255)),M('Stamp','LDT','TIMESTAMP'),M('TimeSynchronized','BOOL'))
        definitions[PART]=(M('Uid',S(64)),M('Present','BOOL'),M('CarrierKind','DINT','ENUM'),M('Result',RESULT))
        if parents:definitions[PART]+=(M('ParentCapacity','DINT'),M('ParentCount','DINT'),M('Parents',S(64),count=parents,lower=1))
        definitions[pub.root_type(app)]+=(M('Part',PART),)
    if app.host_event_capacity:
        definitions[EVENT]=(M('Sequence','DINT','BITSTRING32'),M('Kind','DINT','ENUM'),M('StationPath',S(255)),
            M('PartUid',S(64)),M('Subject',S(80)),M('Value',S(80)),M('Stamp','LDT','TIMESTAMP'),
            M('TimeSynchronized','BOOL'),M('Verdict','DINT','ENUM'),M('ReasonCode','DINT','ENUM'))
        if parents:definitions[EVENT]+=(M('ParentCount','DINT'),M('Parents',S(64),count=parents,lower=1))
        definitions[RING]=tuple(M(n,'INT' if n in ('Count','Capacity') else 'BOOL' if n=='Wrapped' else 'DINT') for n in host.META)+(
            M('RingHead','INT'),M('Ring',EVENT,count=app.host_event_capacity,lower=1,count_path=app.name+'/HostEvents/Count'))
        if parents:definitions[RING]+=(M('GenealogyCapacity','DINT'),)
        definitions[pub.root_type(app)]+=(M('HostEvents',RING),)
    definitions[PLATE]=tuple(M(leaf,S(width)) for _,leaf,width in PLATE_FIELDS)
    for owner in (app,*app.modules):
        if owner.nameplate is not None:
            key=pub.root_type(app) if owner is app else pub.leaf_type(bool(owner.type_key))
            # Leaf kinds are shared. Only a declared owner's instance receives
            # identity; reserve distinct kinds so undeclared peers stay absent.
            if owner is not app:
                key=f'{P}{owner.name}NameplateLeafS3hV63'
                previous=next(m.kind for m in definitions[pub.root_type(app)] if m.name==owner.name)
                definitions[key]=definitions[previous]
                definitions[pub.root_type(app)]=tuple(M(m.name,key) if m.name==owner.name else m for m in definitions[pub.root_type(app)])
            definitions[key]+=(M('Nameplate',PLATE),)
    if app.signal_tower is not None:
        definitions[TOWER]=tuple(M(n,'BOOL') for n in tower.OUTPUTS)
        definitions[pub.root_type(app)]+=(M('SignalTower',TOWER),)
    definitions[pub.root_type(app)]+=(M('MachineState','DINT','ENUM'),)
    definitions[DEFINITION]=(M('Name',S(64)),M('Unit',S(16)),*(M(n,'LREAL') for n in ('Scale','Minimum','Maximum','Target')))
    definitions[DEFINITIONS]=(M('Entries',DEFINITION,count=max(1,len(app.part_carrier.records) if app.part_carrier else 0)),)
    definitions[WORK]=tuple(M(n,'DINT') for n in ('Initialized','SeenPart','SeenRing','SeenLow','SeenHigh','SeenModels','Index','ParentIndex','ByteIndex',
        'SourceIndex','ByteValue','Ended','Kind','ModelIndex','WordValue','DigitCount'))+(
        M('Measured','LREAL'),M('Number','LINT'),M('Negative','BOOL'),M('Digits','DINT',count=11),M('Text',S(80)),M('EmptyMeasurement',MEAS))
    if app.host_event_capacity:definitions[WORK]+=(M('EmptyEvent',EVENT),)


def initialize(app,result):
    if app.part_carrier is not None:
        result['Part']=dict(CarrierKind=2,Result=dict(StationPath=app.name),**({'ParentCapacity':genealogy.capacity(app)} if genealogy.enabled(app) else {}))
    if app.host_event_capacity:
        result['HostEvents']=dict(Capacity=app.host_event_capacity,**({'GenealogyCapacity':genealogy.capacity(app)} if genealogy.enabled(app) else {}))
    for owner in (app,*app.modules):
        if owner.nameplate is not None:
            target=result if owner is app else result[owner.name]
            target['Nameplate']={leaf:getattr(owner.nameplate,attribute) for attribute,leaf,_ in PLATE_FIELDS}
    if app.signal_tower is not None:result['SignalTower']={}
    result['MachineState']=1


def tags(app,serialize):
    definitions=[dict(Name=r.name,Unit=r.unit,Scale=float(r.scale),Minimum=r.minimum/r.scale,
        Maximum=r.maximum/r.scale,Target=r.target/r.scale) for r in app.part_carrier.records] if app.part_carrier else []
    return [serialize(state_tag(app),WORK,{},access='None'),
        serialize(definitions_tag(app),DEFINITIONS,dict(Entries=definitions or [{}]),access='None')]


def ascii_copy(app,target,source,width,*,packed=False):
    """Bounded ASCII copy; reject non-printable bytes and nonzero tails."""
    w=state_tag(app);i=w+'.ByteIndex';bad=pub.header_tag(app)+'.Valid'
    lines=[f'{target}.LEN := 0;',f'{w}.Ended := 0;',f'FOR {i} := 0 TO {width-1} DO']
    if packed:
        lines += [f'{w}.SourceIndex := ({i} - ({i} MOD 4)) / 4;',f'{w}.WordValue := {source};',
            f'IF {w}.WordValue < 0 THEN {bad} := 0; END_IF;',
            f'CASE {i} MOD 4 OF',f'0: {w}.ByteValue := {w}.WordValue MOD 256;',
            f'1: {w}.ByteValue := (({w}.WordValue - ({w}.WordValue MOD 256)) / 256) MOD 256;',
            f'2: {w}.ByteValue := (({w}.WordValue - ({w}.WordValue MOD 65536)) / 65536) MOD 256;',
            f'3: {w}.ByteValue := ({w}.WordValue - ({w}.WordValue MOD 16777216)) / 16777216;',
            f'ELSE {bad} := 0;','END_CASE;']
    else:lines += [f'{w}.ByteValue := {source};']
    lines += [f'IF {w}.ByteValue = 0 THEN {w}.Ended := 1;',
        f'ELSIF ({w}.Ended <> 0) OR ({w}.ByteValue < 32) OR ({w}.ByteValue > 126) THEN {bad} := 0;',
        'ELSE',f'{target}.DATA[{i}] := {w}.ByteValue;',f'{target}.LEN := {i} + 1;','END_IF;','END_FOR;']
    return lines


def timestamp(app,target,date,clock_code,*,required=False):
    w=clock.work_tag(app)
    return [f'{w}.Inputs.DateCode := {date};',f'{w}.Inputs.ClockCode := {clock_code};',
        f'JSR({clock.timestamp_routine_name(app)},0);',f'{target} := {w}.EpochNs;']+(
        [f'IF {date} <= 0 THEN {pub.header_tag(app)}.Valid := 0; END_IF;'] if required else [])


def decimal(app):
    """Full signed DINT decimal text, widened before negating INT32_MIN."""
    w=state_tag(app);text=w+'.Text';i=w+'.ByteIndex'
    return [f'{text}.LEN := 0;',f'{w}.Negative := {w}.Number < 0;',
        f'IF {w}.Negative THEN {w}.Number := 0 - {w}.Number; END_IF;',f'{w}.DigitCount := 0;',
        # Ten bounded iterations also cover zero, without a native string cast.
        f'FOR {i} := 0 TO 9 DO',f'IF ({w}.Number <> 0) OR ({i} = 0) THEN',
        f'{w}.Digits[{w}.DigitCount] := {w}.Number MOD 10 + 48;',f'{w}.DigitCount := {w}.DigitCount + 1;',
        f'{w}.Number := ({w}.Number - ({w}.Number MOD 10)) / 10;','END_IF;','END_FOR;',
        f'IF {w}.Negative THEN {text}.DATA[0] := 45; {text}.LEN := 1; END_IF;',
        f'FOR {i} := 0 TO {w}.DigitCount-1 DO',f'{text}.DATA[{text}.LEN] := {w}.Digits[{w}.DigitCount-1-{i}];',
        f'{text}.LEN := {text}.LEN + 1;','END_FOR;']


def part_logic(app):
    if app.part_carrier is None:return []
    w=state_tag(app);s=part.tag(app);t=app.name+'.Part';i=w+'.Index';j=w+'.ParentIndex';b=w+'.ByteIndex'
    valid=pub.header_tag(app)+'.Valid';cap=app.part_carrier.result_capacity;parents=genealogy.capacity(app)
    lines=[f'IF ({s}.SchemaVersion <> {part.schema(app)}) OR ({s}.DataRevision < 0) OR (({s}.DataRevision MOD 2) <> 0) '
        f'OR ({s}.CarrierKind <> 2) OR ({s}.Present < 0) OR ({s}.Present > 1) '
        f'OR ({s}.Verdict < 0) OR ({s}.Verdict > 3) OR (({s}.Verdict = 2) AND ({s}.ReasonCode = 0)) '
        f'OR ({s}.RecordCount < 0) OR ({s}.RecordCount > {cap}) '
        f'OR ({s}.TimeSynchronized < 0) OR ({s}.TimeSynchronized > 1) THEN {valid} := 0;',
        f'ELSIF ({w}.Initialized = 0) OR ({w}.SeenPart <> {s}.DataRevision) THEN']
    lines += ascii_copy(app,t+'.Uid',f'{s}.Uid[{b}]',64)
    lines += [f'IF ({s}.Present <> 0) AND ({t}.Uid.LEN = 0) THEN {valid} := 0; END_IF;',
        f'{t}.Present := {s}.Present <> 0;',f'{t}.CarrierKind := {s}.CarrierKind;',
        f'{t}.Result.Verdict := {s}.Verdict;',f'{t}.Result.ReasonCode := {s}.ReasonCode;',
        f'{t}.Result.TimeSynchronized := {s}.TimeSynchronized <> 0;']
    lines += timestamp(app,t+'.Result.Stamp',s+'.Date',s+'.Time')
    lines += [f'IF ({s}.Verdict <> 0) AND ({s}.Date <= 0) THEN {valid} := 0; END_IF;',f'FOR {i} := 0 TO {cap-1} DO',
        f'CPS({w}.EmptyMeasurement,{t}.Result.Records[{i}],1);',f'IF {i} < {s}.RecordCount THEN',
        f'{w}.Kind := {s}.RecordKind[{i}];',f'IF ({w}.Kind >= 1) AND ({w}.Kind <= {len(app.part_carrier.records)}) THEN']
    definition=definitions_tag(app)+f'.Entries[{w}.Kind-1]';record=f'{t}.Result.Records[{i}]'
    lines += [f'CPS({definition}.Name,{record}.Name,1);',f'CPS({definition}.Unit,{record}.Unit,1);',
        f'{w}.Measured := {s}.RecordValue[{i}];',f'{record}.Value := {w}.Measured / {definition}.Scale;']
    lines += [f'{record}.{n} := {definition}.{n};' for n in ('Minimum','Maximum','Target')]
    lines += [f'{record}.InTol := {s}.RecordInTol[{i}] <> 0;',
        f'IF ({s}.RecordInTol[{i}] < 0) OR ({s}.RecordInTol[{i}] > 1) OR '
        f'({record}.InTol <> (({record}.Value >= {record}.Minimum) AND ({record}.Value <= {record}.Maximum))) THEN {valid} := 0; END_IF;',
        f'ELSE {valid} := 0;','END_IF;','END_IF;','END_FOR;']
    if parents:
        lines += [f'{t}.ParentCount := {s}.ParentCount;',f'IF ({s}.ParentCount < 0) OR ({s}.ParentCount > {parents}) THEN {valid} := 0;',
            'ELSE',f'FOR {j} := 0 TO {parents-1} DO']
        lines += ascii_copy(app,f'{t}.Parents[{j}]',f'{s}.Parents[{j}*64+{b}]',64)
        lines += [f'IF (({j} < {s}.ParentCount) AND ({t}.Parents[{j}].LEN = 0)) OR '
            f'(({j} >= {s}.ParentCount) AND ({t}.Parents[{j}].LEN <> 0)) THEN {valid} := 0; END_IF;',
            'END_FOR;','END_IF;']
    return lines+[f'IF {valid} THEN {w}.SeenPart := {s}.DataRevision; END_IF;','END_IF;']


def host_logic(app):
    if not app.host_event_capacity:return []
    import fraktal_ab_declaration as decl
    w=state_tag(app);s=host.tag(app);t=app.name+'.HostEvents';i=w+'.Index';b=w+'.ByteIndex';j=w+'.ParentIndex'
    cap=app.host_event_capacity;parents=genealogy.capacity(app);valid=pub.header_tag(app)+'.Valid'
    lines=[f'IF ({s}.SchemaVersion <> {host.schema(app)}) OR ({s}.Failed <> 0) '
        f'OR ({s}.Capacity <> {cap}) OR ({s}.Count < 0) OR ({s}.Count > {cap}) OR ({s}.NewestSequence < {s}.Count) '
        f'OR ({s}.Head < 0) OR ({s}.Head > {cap}) OR ({s}.DataRevision < 0) OR (({s}.DataRevision MOD 2) <> 0) '
        f'OR (({s}.EpochLow = 0) AND ({s}.EpochHigh = 0)) THEN {valid} := 0;',
        'ELSE',f'IF ({s}.Count <> {s}.NewestSequence) AND ({s}.Count <> {cap}) THEN {valid} := 0; END_IF;',
        f'IF ({s}.NewestSequence > 0) AND (({s}.Head <> (({s}.NewestSequence-1) MOD {cap})+1) OR ({s}.DataRevision = 0)) THEN {valid} := 0; END_IF;',
        f'IF ({s}.NewestSequence = 0) AND ({s}.Head <> 0) THEN {valid} := 0; END_IF;',
        f'IF (({s}.NewestSequence > {cap}) AND ({s}.Wrapped <> 1)) OR (({s}.NewestSequence <= {cap}) AND ({s}.Wrapped <> 0)) THEN {valid} := 0; END_IF;']
    for name in host.META:lines += [f'{t}.{name} := {s}.{name}'+(' <> 0;' if name=='Wrapped' else ';')]
    lines += [f'{t}.RingHead := {s}.Head;',f'IF ({w}.Initialized = 0) OR ({w}.SeenRing <> {s}.DataRevision) '
        f'OR ({w}.SeenLow <> {s}.EpochLow) OR ({w}.SeenHigh <> {s}.EpochHigh) '
        f'OR ({w}.SeenModels <> {app.name}.AvailableModelCount) THEN' if app.models and app.model_capacity else
        f'{t}.RingHead := {s}.Head; IF ({w}.Initialized = 0) OR ({w}.SeenRing <> {s}.DataRevision) '
        f'OR ({w}.SeenLow <> {s}.EpochLow) OR ({w}.SeenHigh <> {s}.EpochHigh) THEN',
        f'FOR {i} := 0 TO {cap-1} DO',f'CPS({w}.EmptyEvent,{t}.Ring[{i}],1);',f'IF {i} < {s}.Count THEN']
    event=f'{t}.Ring[{i}]';kind=s+f'.Kind[{i}]'
    lines += core.put_text(event+'.StationPath',app.name,255)
    for name in ('Sequence','Kind','Verdict','ReasonCode','TimeSynchronized'):
        lines += [f'{event}.{name} := {s}.{name}[{i}]'+(' <> 0;' if name=='TimeSynchronized' else ';')]
    supported=(*host.SUPPORTED,*((1,2,3,4) if app.part_carrier else ()),*((7,8) if resources.enabled(app) else ()))
    lines += [f'IF NOT ('+' OR '.join(f'({kind} = {n})' for n in supported)+f') THEN {valid} := 0; END_IF;',
        f'IF ({s}.TimeSynchronized[{i}] < 0) OR ({s}.TimeSynchronized[{i}] > 1) THEN {valid} := 0; END_IF;',
        f'IF {s}.Sequence[{i}] <> {s}.NewestSequence - (({s}.Head-1-{i}+{cap}) MOD {cap}) THEN {valid} := 0; END_IF;']
    lines += timestamp(app,event+'.Stamp',s+f'.Date[{i}]',s+f'.Time[{i}]',required=True)
    if host.schema(app)>=2:
        lines += ascii_copy(app,w+'.Text',f'{s}.Uid[{i}*64+{b}]',64)
        lines += [f'IF ({kind} >= 1) AND ({kind} <= 4) THEN',f'IF {w}.Text.LEN = 0 THEN {valid} := 0; END_IF;',
            f'{event}.PartUid.LEN := {w}.Text.LEN;',f'FOR {b} := 0 TO {w}.Text.LEN-1 DO',
            f'{event}.PartUid.DATA[{b}] := {w}.Text.DATA[{b}];','END_FOR;',
            f'ELSIF ({kind} = 7) OR ({kind} = 8) THEN',f'IF ({w}.Text.LEN = 0) OR ({w}.Text.LEN > 63) THEN {valid} := 0; END_IF;',
            f'CPS({w}.Text,{event}.Subject,1);',f'ELSIF {w}.Text.LEN <> 0 THEN {valid} := 0;','END_IF;']
    lines += [f'IF ({kind} = 7) OR ({kind} = 8) OR ({kind} = 9) THEN',
        f'{w}.Number := {s}.Value[{i}];',f'JSR({routine(app,"Decimal")},0);',f'CPS({w}.Text,{event}.Value,1);',
        f'IF ({kind} = 9) AND NOT ('+' OR '.join(f'({s}.Value[{i}] = {m})' for m in decl.declared_modes(app))+f') THEN {valid} := 0; END_IF;',
        f'ELSIF ({kind} = 5) OR ({kind} = 6) THEN',f'{w}.ModelIndex := {s}.ModelOrdinal[{i}]-1;']
    if app.models and app.model_capacity:
        code=f'{app.name}.AvailableModels[{w}.ModelIndex].ModelCode'
        lines += [f'IF ({w}.ModelIndex >= 0) AND ({w}.ModelIndex < {app.name}.AvailableModelCount) THEN',
            f'{event}.Value.LEN := {code}.LEN;',f'FOR {b} := 0 TO {code}.LEN-1 DO',f'{event}.Value.DATA[{b}] := {code}.DATA[{b}];','END_FOR;',
            f'ELSIF ({kind} <> 5) OR ({w}.ModelIndex <> -1) THEN {valid} := 0;','END_IF;']
    else:lines += [f'IF ({kind} <> 5) OR ({w}.ModelIndex <> -1) THEN {valid} := 0; END_IF;']
    lines += ['END_IF;']
    if resources.text_enabled(app):
        lines += [f'IF {s}.ValueFormat[{i}] = 1 THEN',f'IF (({kind} <> 7) AND ({kind} <> 8)) OR ({s}.Value[{i}] <> 0) THEN {valid} := 0; END_IF;']
        lines += ascii_copy(app,event+'.Value',f'{s}.ValueText[{i}*{resources.TEXT_WORDS}+{w}.SourceIndex]',resources.TEXT_LIMIT,packed=True)
        lines += [f'IF {s}.ValueText[{i}*{resources.TEXT_WORDS}+{resources.TEXT_WORDS-1}] <> 0 THEN {valid} := 0; END_IF;',
            f'ELSIF {s}.ValueFormat[{i}] = 0 THEN',f'FOR {b} := 0 TO {resources.TEXT_WORDS-1} DO',
            f'IF {s}.ValueText[{i}*{resources.TEXT_WORDS}+{b}] <> 0 THEN {valid} := 0; END_IF;','END_FOR;',f'ELSE {valid} := 0;','END_IF;']
    if parents:
        lines += [f'{event}.ParentCount := {s}.ParentCount[{i}];',f'IF ({event}.ParentCount < 0) OR ({event}.ParentCount > {parents}) THEN {valid} := 0;',
            'ELSE',f'FOR {j} := 0 TO {parents-1} DO']
        lines += ascii_copy(app,f'{event}.Parents[{j}]',f'{s}.ParentWords[({i}*{parents}+{j})*16+{w}.SourceIndex]',64,packed=True)
        lines += [f'IF (({j} < {event}.ParentCount) AND ({event}.Parents[{j}].LEN = 0)) OR '
            f'(({j} >= {event}.ParentCount) AND ({event}.Parents[{j}].LEN <> 0)) OR '
            f'((({kind} < 1) OR ({kind} > 4)) AND ({event}.ParentCount <> 0)) THEN {valid} := 0; END_IF;',
            'END_FOR;','END_IF;']
    lines += ['END_IF;','END_FOR;',f'IF {valid} THEN',f'{w}.SeenRing := {s}.DataRevision;',
        f'{w}.SeenLow := {s}.EpochLow;',f'{w}.SeenHigh := {s}.EpochHigh;']
    if app.models and app.model_capacity:lines += [f'{w}.SeenModels := {app.name}.AvailableModelCount;']
    return lines+['END_IF;','END_IF;','END_IF;']


def routines(app):return [(routine(app,'Decimal'),decimal(app))]


def cyclic(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_machine_state as machine
    w=state_tag(app)
    lines=[f'IF S:FS THEN {w}.Initialized := 0; END_IF;']+part_logic(app)+host_logic(app)
    if app.signal_tower is not None:
        lines += [f'{app.name}.SignalTower.{n} := {tower.tag(app)}.{n} <> 0;' for n in tower.OUTPUTS]
        lines += [f'{app.name}.MachineState := {tower.tag(app)}.MachineState;']
    else:lines += machine.logic(app,app.name+'.MachineState',f'FRK_{app.name}_Unit',gen.alarm_active_tag(app))
    return lines+[f'IF {pub.header_tag(app)}.Valid THEN {w}.Initialized := 1; END_IF;']
