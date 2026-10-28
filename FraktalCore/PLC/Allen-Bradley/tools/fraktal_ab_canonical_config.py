"""S3f bounded PLC configuration pages, revisions and durability publication."""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_canonical_status as clock
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_data_access as data

P=pub.PREFIX
ENTRY=P+'ConfigEntryS3fV63'
PAGE=P+'ConfigPageS3fV63'
RESPONSE=P+'ConfigResponseS3fV63'
PERSIST=P+'PersistS3fV63'
SET=P+'SetInfoS3fV63'
WORK=P+'ConfigWorkS3fV63'
QUERY_STATUS=P+'QueryStatusS3fV63'
PAGE_SIZE=core.core_limit('MAX_CONFIG_PAGE')


def state_tag(app):return f'FRK_{app.name}_CanonicalConfigWork'
def query_status_tag(app):return f'FRK_{app.name}_ConfigQueryStatus'
def page_routine(app):return f'FRK_{app.name}_CanonicalConfigPage'
def number_routine(app):return f'FRK_{app.name}_CanonicalConfigNumber'


def values(app):return gen.editable_values(app)


# Table-driven page (capacity plan R2): one definition row per editable value.
DEF=P+'ConfigDefV1'
TEXT_FIELDS=(('Item',255),('WriteKey',160),('LabelKey',160),('ClassId',40),('CaptureSource',255))
def defs_tag(app):return f'FRK_{app.name}_CanonicalConfigDefs'


def entry_texts(app):
    source=manifest.content(app);keys={x['NumericKey']:x['PortableKey'] for x in source['Localization']}
    caps=source['WriteCapabilities']
    return [dict(Item='Config/'+m.name,WriteKey=keys.get(caps[o-1]['WriteKeyKey'],''),LabelKey=keys.get(caps[o-1]['LabelKey'],''),
                 ClassId=keys.get(caps[o-1].get('ClassKey',0),''),CaptureSource=keys.get(caps[o-1].get('CaptureSourceKey',0),''))
            for o,r,m in values(app)]


def literals(app):return [app.name,*(t for row in entry_texts(app) for t in row.values())]


def def_rows(app):
    """Static entry facts. Live values are ValueCache slots: the cache is refreshed
    from these exact sources earlier in the same scan, before the page is built."""
    import fraktal_ab_canonical_text as text
    caps=manifest.content(app)['WriteCapabilities'];scoped_members=[m.name for m in gen.model_cfg_members(app)]
    rows=[]
    for index,((ordinal,record,member),texts) in enumerate(zip(values(app),entry_texts(app),strict=True)):
        cap=caps[ordinal-1];scoped=gen.is_model_scoped(app,record,member.name)
        for name,width in TEXT_FIELDS:
            if len(texts[name].encode('utf-8'))>width:raise ValueError('canonical literal exceeds its declared byte width')
        rows.append(dict(**{name:text.slice_value(app,texts[name]) for name,_ in TEXT_FIELDS},
            ConfigKind=cap['ConfigKind'],ValueType=cap['ValueType'],RequiresReady=bool(cap['RequiresReady']),
            Minimum=cap['Minimum'],Maximum=cap['Maximum'],UnitCode=cap['UnitCode'],ModelScoped=scoped,
            CanCapture=bool(cap.get('CaptureSourceKey',0)),CacheIndex=index,
            ModelCache=len(values(app))+scoped_members.index(member.name) if scoped else -1))
    return rows


def cache_sources(app):
    result=[f'{r.name}Tag.{m.name}' for _,r,m in values(app)]
    if gen.model_cfg_members(app):
        result += [f'{gen.model_cfg_tag(app)}[{i}].{m.name}'
            for i in range(app.model_capacity or len(app.models))
            for m in gen.model_cfg_members(app)]
    if app.access_users is not None:
        t=data.tag(app,'Levels')
        result += [f'{t}.{n}[{i}]' for i in range(len(values(app))) for n in ('ReadLevel','WriteLevel','Readable')]
    return result


def validate(app):
    findings=[]
    if not values(app):findings.append('S3f requires at least one editable value')
    if len(values(app))>32767:findings.append('configuration walk exceeds INT page-count range')
    for _,r,m in values(app):
        fields=((app.name,255),('Config/'+m.name,255),(m.write_key,160),(m.label_key,160),
                (m.capture_source or '',255),(m.data_class if hasattr(m,'data_class') else '',40))
        if any(len(t.encode('utf-8'))>width for t,width in fields):findings.append('configuration entry text exceeds Core width')
    return findings


def augment(app,definitions):
    M=pub.Member;S=pub.string_type
    definitions[ENTRY]=(M('Scope',S(255)),M('Item',S(255)),M('ValueText',S(255)),
        M('WriteKey',S(160)),M('WriteRevision','DINT','BITSTRING32'),M('ConfigKind','DINT','ENUM'),
        M('ValueType','DINT','ENUM'),M('Writable','BOOL'),M('RequiresReady','BOOL'),
        M('HasMinimum','BOOL'),M('HasMaximum','BOOL'),M('Minimum','LREAL'),M('Maximum','LREAL'),
        M('Unit',S(16)),M('LabelKey',S(160)),M('EnumDomain',S(255)),M('UnitCode','DINT','ENUM'),
        M('EnumLabelKey',S(80)),M('ClassId',S(40)),M('ReadLevel','DINT','ENUM'),M('WriteLevel','DINT','ENUM'),
        M('Readable','BOOL'),M('ModelScoped','BOOL'),M('CaptureSource',S(255)),M('CanCapture','BOOL'))
    definitions[PAGE]=(M('Revision','DINT','BITSTRING32'),M('PageIndex','INT'),M('PageCount','INT'),
        M('EntryCount','INT'),M('Entries',ENTRY,count=PAGE_SIZE,lower=1,
            count_path=app.name+'/HmiResponse/ConfigPage/EntryCount'))
    definitions[RESPONSE]=(M('ConfigPage',PAGE),)
    definitions[PERSIST]=(M('Pending','BOOL'),M('Failed','BOOL'),M('WindowMs','DINT','BITSTRING32'),
        M('PendingSince','LDT','TIMESTAMP'),M('StorePresent','BOOL'),M('StoreKind','DINT','ENUM'),
        M('RestoreLost','BOOL'),M('RestoreAcknowledged','BOOL'),M('LostPath',S(80)),M('RestorePolicy','DINT','ENUM'),
        M('LastSetName',S(80)),M('LastSetRecords','INT'),M('LastRejectScope',S(80)),M('LastRejectKey',S(160)))
    definitions[SET]=(M('Used','BOOL'),M('SetName',S(80)),M('RootIdentity',S(80)),M('SetSchema','DINT','UINT16'),
        M('ConfigRev','DINT','BITSTRING32'),M('Kind','DINT','ENUM'),M('ModelCode',S(64)),
        M('RecordCount','INT'),M('CreatedAt','LDT','TIMESTAMP'),M('TimeSynchronized','BOOL'))
    # A versioned root status type leaves earlier deployed layouts untouched.
    old=next(m.kind for m in definitions[pub.root_type(app)] if m.name=='Status');new=P+'RootStatusS3fV63'
    definitions[new]=definitions[old]+(M('ConfigRev','DINT','BITSTRING32'),)
    root=pub.root_type(app)
    definitions[root]=tuple(M(m.name,new) if m.name=='Status' else m for m in definitions[root])
    definitions[root]+=(M('HmiResponse',RESPONSE),M('ConfigPersist',PERSIST),M('ConfigSetCount','INT'),
        M('ConfigSets',SET,count=core.core_limit('MAX_CONFIG_SETS'),lower=1),M('ConfigSetDocument',S(480)),
        M('ConfigSetDocumentLine','INT'),M('ConfigSetDocumentLines','INT'))
    definitions[QUERY_STATUS]=tuple(M(n,'DINT') for n in ('SchemaVersion','AckSequence','Accepted','PageIndex','ModelIndex','Revision'))
    definitions[WORK]=tuple(M(n,'DINT') for n in (
        'Initialized','Changed','LastModeModel','LastCatalogCount','Revision','PageIndex','ModelIndex',
        'QuerySequence','PageBuilt','Index','Slot','Ordinal','ByteIndex','Number','Negative','Digit','DigitCount',
        'Position','ReadLevel','WriteLevel','Readable','PendingDate','PendingClock','LastPendingDate','LastPendingClock',
        'LastSetSequence','LastLostModule','LastLevel','BootSeed','NameValid'))+(
        M('BootMicros','LINT'),M('ValueCache','DINT',count=max(1,len(cache_sources(app)))),
        M('Digits','DINT',count=10),M('Render',S(255)))
    import fraktal_ab_canonical_text as text
    if text.enabled(app):
        definitions[DEF]=(*(M(name,text.SLICE) for name,_ in TEXT_FIELDS),M('ConfigKind','DINT'),M('ValueType','DINT'),
            M('RequiresReady','BOOL'),M('Minimum','LREAL'),M('Maximum','LREAL'),M('UnitCode','DINT'),
            M('ModelScoped','BOOL'),M('CanCapture','BOOL'),M('CacheIndex','DINT'),M('ModelCache','DINT'))


def initialize(app,result):
    result.update(HmiResponse=dict(ConfigPage={}),ConfigPersist={},ConfigSetCount=0)


def tags(app,serialize):
    import fraktal_ab_canonical_text as text
    result=[serialize(state_tag(app),WORK,{},access='None'),
        serialize(query_status_tag(app),QUERY_STATUS,dict(SchemaVersion=1))]
    if text.enabled(app):result.append(serialize(defs_tag(app),DEF,def_rows(app),access='None',array=True))
    return result


def query(app):
    import fraktal_ab_mailbox as mb
    w=state_tag(app);q=mb.request_tag_name(app)
    # A query chooses the bounded window; only the owning mailbox acknowledges.
    return [f'{w}.PageIndex := {q}.IntValue;',f'IF {w}.PageIndex < 0 THEN {w}.PageIndex := 0; END_IF;',
        f'{w}.ModelIndex := {q}.DurationMs;',f'{w}.QuerySequence := {mb.committed_sequence(app)};',f'{w}.PageBuilt := 0;']


def pending_stamp(app):
    w=state_tag(app)
    return [f'{w}.PendingDate := FRK_{app.name}_NowDate;',f'{w}.PendingClock := FRK_{app.name}_NowTime;']


def cyclic(app):
    import fraktal_ab_models as models
    import fraktal_ab_sets as sets
    w=state_tag(app);root=app.name;p=root+'.ConfigPersist';source=gen.config_persist_tag(app)
    revision=root+'.Status.ConfigRev';unit=f'FRK_{root}_Unit'
    count=f'{models.tag(app)}.Count' if app.model_capacity else str(len(app.models))
    lines=[f'{w}.Changed := 0;',f'IF S:FS OR ({w}.Initialized = 0) THEN',
        f'GSV(WallClockTime,,CurrentValue,{w}.BootMicros);',f'{w}.BootSeed := {w}.BootMicros MOD 2147483646;',
        f'IF {w}.BootSeed < 1 THEN {w}.BootSeed := 1; END_IF;',
        f'IF {w}.BootSeed = {w}.Revision THEN',f'IF {w}.BootSeed >= 2147483646 THEN {w}.BootSeed := 1; ELSE {w}.BootSeed := {w}.BootSeed + 1; END_IF;','END_IF;',
        # The seed already differs from the retained token. Treat first scan as
        # initialization so the ordinary change bump cannot collide with it.
        f'{w}.Revision := {w}.BootSeed;',f'{w}.Initialized := 0;',f'{w}.Changed := 1;',f'{w}.PageBuilt := 0;','END_IF;']
    for i,source_value in enumerate(cache_sources(app)):
        lines += [f'IF {w}.ValueCache[{i}] <> {source_value} THEN',f'{w}.ValueCache[{i}] := {source_value};',f'{w}.Changed := 1;','END_IF;']
    lines += [f'IF ({w}.LastModeModel <> {unit}.ModelOrdinal) OR ({w}.LastCatalogCount <> {count}) THEN',
        f'{w}.LastModeModel := {unit}.ModelOrdinal;',f'{w}.LastCatalogCount := {count};',f'{w}.Changed := 1;','END_IF;',
        f'IF ({w}.Changed <> 0) AND ({w}.Initialized <> 0) THEN',
        f'IF {w}.Revision >= 2147483646 THEN {w}.Revision := 1; ELSE {w}.Revision := {w}.Revision + 1; END_IF;',
        f'{w}.PageBuilt := 0;','END_IF;',f'{w}.Initialized := 1;',f'{revision} := {w}.Revision;']
    for n in ('Pending','Failed','WindowMs','StorePresent','StoreKind','RestoreLost','RestoreAcknowledged','RestorePolicy'):
        lines += [f'{p}.{n} := {source}.{n}'+(' <> 0;' if n in ('Pending','Failed','StorePresent','RestoreLost','RestoreAcknowledged') else ';')]
    lines += [f'IF ({w}.PendingDate <> {w}.LastPendingDate) OR ({w}.PendingClock <> {w}.LastPendingClock) THEN',
        f'{clock.work_tag(app)}.Inputs.DateCode := {w}.PendingDate;',f'{clock.work_tag(app)}.Inputs.ClockCode := {w}.PendingClock;',
        f'JSR({clock.timestamp_routine_name(app)},0);',f'{p}.PendingSince := {clock.work_tag(app)}.EpochNs;',
        f'{w}.LastPendingDate := {w}.PendingDate;',f'{w}.LastPendingClock := {w}.PendingClock;','END_IF;',
        f'IF {w}.LastLostModule <> {source}.LostModuleId THEN',f'{p}.LostPath.LEN := 0;',f'CASE {source}.LostModuleId OF']
    for i,name in enumerate([app.name,*[app.name+'.'+m.name for m in app.modules]],1):
        lines += [f'{i}:']+core.put_text(p+'.LostPath',name,80)
    lines += ['ELSE','(* No valid module identity. *)','END_CASE;',f'{w}.LastLostModule := {source}.LostModuleId;','END_IF;']
    if app.config_sets:
        s=sets.state_tag(app);staged=sets.staged_tag(app);b=w+'.ByteIndex'
        lines += [f'IF {w}.LastSetSequence <> {s}.Sequence THEN',f'{p}.LastSetName.LEN := 0;',
            f'IF ({staged}.NameLength >= 0) AND ({staged}.NameLength <= 80) THEN',
            f'{w}.NameValid := 1;',f'FOR {b} := 0 TO {staged}.NameLength - 1 DO',
            f'IF ({staged}.NameBytes[{b}] < 1) OR ({staged}.NameBytes[{b}] > 127) THEN {w}.NameValid := 0; END_IF;','END_FOR;',
            f'IF {w}.NameValid <> 0 THEN',
            f'FOR {b} := 0 TO {staged}.NameLength - 1 DO',f'{p}.LastSetName.DATA[{b}] := {staged}.NameBytes[{b}];','END_FOR;',
            f'{p}.LastSetName.LEN := {staged}.NameLength;','END_IF;','END_IF;',f'{p}.LastSetRecords := 0;',
            f'IF ({s}.Count >= 0) AND ({s}.Count <= {sets.MAX_RECORDS}) THEN {p}.LastSetRecords := {s}.Count; END_IF;',
            f'{w}.LastSetSequence := {s}.Sequence;','END_IF;']
    if app.canonical_config_read_view:
        from fraktal_ab_config_read_view import work_tag as read_work
        clean=read_work(app)+'.CleanText';slot=w+'.Slot'
        lines += [f'IF {w}.PageBuilt = 0 THEN',f'FOR {slot} := 0 TO {PAGE_SIZE-1} DO',
                  f'CPS({clean},{root}.HmiResponse.ConfigPage.Entries[{slot}].ValueText,1);',
                  f'{root}.HmiResponse.ConfigPage.Entries[{slot}].Readable := 0;','END_FOR;',
                  f'JSR({page_routine(app)},0);','END_IF;']
    else:
        lines += [f'IF {w}.PageBuilt = 0 THEN',f'JSR({page_routine(app)},0);','END_IF;']
    return lines


def number_logic(app):
    # The existing signed formatter owns the algorithm; substitute only its
    # private work record so login/audit state can never be overwritten.
    import fraktal_ab_canonical_access as formatting
    return [line.replace(formatting.state_tag(app),state_tag(app)) for line in formatting.number_logic(app)]


def table_page_logic(app):
    """The same page as page_logic, walked over the definition table."""
    import fraktal_ab_canonical_text as text
    w=state_tag(app);target=app.name+'.HmiResponse.ConfigPage';slot=w+'.Slot';row=f'{target}.Entries[{slot}]'
    d=f'{defs_tag(app)}[{w}.Index]';count=len(values(app));pcount=(count+PAGE_SIZE-1)//PAGE_SIZE
    stride=len(gen.model_cfg_members(app));cache=text.work_tag(app)+'.Index'
    lines=[f'{target}.Revision := {w}.Revision;',f'{target}.PageCount := {pcount};',f'{target}.EntryCount := 0;',
        f'{target}.PageIndex := 0;',f'IF {w}.PageIndex <= 32767 THEN {target}.PageIndex := {w}.PageIndex; ELSE {target}.PageIndex := 32767; END_IF;',
        f'IF {w}.PageIndex < {pcount} THEN',f'FOR {slot} := 0 TO {PAGE_SIZE-1} DO',
        f'{w}.Ordinal := {w}.PageIndex * {PAGE_SIZE} + {slot} + 1;',
        f'IF ({w}.Ordinal >= 1) AND ({w}.Ordinal <= {count}) THEN',f'{w}.Index := {w}.Ordinal - 1;',
        f'IF (NOT {d}.ModelScoped) OR (({w}.ModelIndex >= 0) AND ({w}.ModelIndex <= {w}.LastCatalogCount)) THEN',
        *text.put_text(app,row+'.Scope',app.name,255)]
    for name,_ in TEXT_FIELDS:lines += text.put(app,f'{row}.{name}',f'{d}.{name}.Offset',f'{d}.{name}.Length')
    lines += [f'{row}.{n}.LEN := 0;' for n in ('Unit','EnumDomain','EnumLabelKey')]
    lines += [f'{row}.WriteRevision := {manifest.config_revision(app)};',f'{row}.Writable := 1;',
        f'{row}.HasMinimum := 1;',f'{row}.HasMaximum := 1;',
        *[f'{row}.{n} := {d}.{n};' for n in ('ConfigKind','ValueType','RequiresReady','Minimum','Maximum','UnitCode','ModelScoped','CanCapture')]]
    if app.access_users is not None:
        levels=data.tag(app,'Levels')
        lines += [f'{row}.{n} := {levels}.{n}[{w}.Index];' for n in ('ReadLevel','WriteLevel')]
        lines += [f'{row}.Readable := {levels}.Readable[{w}.Index] <> 0;']
    else:lines += [f'{row}.ReadLevel := -1;',f'{row}.WriteLevel := -1;',f'{row}.Readable := 1;']
    lines += [f'{row}.ValueText.LEN := 0;',f'IF {row}.Readable THEN',
        f'IF ({d}.ModelCache < 0) OR ({w}.ModelIndex = 0) THEN {cache} := {d}.CacheIndex;',
        f'ELSE {cache} := {d}.ModelCache + ({w}.ModelIndex - 1) * {stride}; END_IF;',
        f'{w}.Number := {w}.ValueCache[{cache}];',
        f'{w}.Render.LEN := 0;',f'JSR({number_routine(app)},0);',f'CPS({w}.Render,{row}.ValueText,1);','END_IF;',
        f'{target}.EntryCount := {target}.EntryCount + 1;','END_IF;','END_IF;','END_FOR;','END_IF;']
    if app.canonical_config_read_view:
        from fraktal_ab_config_read_view import work_tag as read_work
        # Old formatter scratch can contain a longer, previously readable value.
        lines=[f'CPS({read_work(app)}.CleanText,{w}.Render,1);' if line==f'{w}.Render.LEN := 0;' else line for line in lines]
    status=query_status_tag(app)
    return lines+[f'IF ({w}.ModelIndex < 0) OR ({w}.ModelIndex > {w}.LastCatalogCount) THEN {target}.EntryCount := 0; END_IF;',
        f'{w}.PageBuilt := 1;',f'{status}.PageIndex := {w}.PageIndex;',f'{status}.ModelIndex := {w}.ModelIndex;',
        f'{status}.Revision := {w}.Revision;',f'{status}.Accepted := 1;',f'{status}.AckSequence := {w}.QuerySequence;']


def page_logic(app):
    import fraktal_ab_canonical_text as text
    if text.enabled(app):return table_page_logic(app)
    w=state_tag(app);target=app.name+'.HmiResponse.ConfigPage';slot=w+'.Slot';row=f'{target}.Entries[{slot}]'
    source=manifest.content(app);keys={x['NumericKey']:x['PortableKey'] for x in source['Localization']}
    caps=source['WriteCapabilities'];pcount=(len(caps)+PAGE_SIZE-1)//PAGE_SIZE
    lines=[f'{target}.Revision := {w}.Revision;',f'{target}.PageCount := {pcount};',f'{target}.EntryCount := 0;',
        f'{target}.PageIndex := 0;',f'IF {w}.PageIndex <= 32767 THEN {target}.PageIndex := {w}.PageIndex; ELSE {target}.PageIndex := 32767; END_IF;',
        f'IF {w}.PageIndex < {pcount} THEN',f'FOR {slot} := 0 TO {PAGE_SIZE-1} DO',
        f'{w}.Ordinal := {w}.PageIndex * {PAGE_SIZE} + {slot} + 1;',f'CASE {w}.Ordinal OF']
    for ordinal,record,member in values(app):
        cap=caps[ordinal-1];scoped=gen.is_model_scoped(app,record,member.name)
        lines += [f'{ordinal}:']
        if scoped:
            guard=f'({w}.ModelIndex >= 0) AND ({w}.ModelIndex <= {w}.LastCatalogCount)'
            lines += [f'IF {guard} THEN']
        static=dict(Scope=app.name,Item='Config/'+member.name,WriteKey=keys.get(cap['WriteKeyKey'],''),
            Unit='',LabelKey=keys.get(cap['LabelKey'],''),EnumDomain='',EnumLabelKey='',
            ClassId=keys.get(cap.get('ClassKey',0),''),CaptureSource=keys.get(cap.get('CaptureSourceKey',0),''))
        widths={'Scope':255,'Item':255,'WriteKey':160,'Unit':16,'LabelKey':160,'EnumDomain':255,
                'EnumLabelKey':80,'ClassId':40,'CaptureSource':255}
        for name,text in static.items():lines += core.put_text(row+'.'+name,text,widths[name])
        for name,value in dict(WriteRevision=manifest.config_revision(app),ConfigKind=cap['ConfigKind'],ValueType=cap['ValueType'],
            Writable=1,RequiresReady=int(bool(cap['RequiresReady'])),HasMinimum=1,HasMaximum=1,
            Minimum=cap['Minimum'],Maximum=cap['Maximum'],UnitCode=cap['UnitCode'],
            ModelScoped=int(scoped),CanCapture=int(bool(cap.get('CaptureSourceKey',0)))).items():
            lines.append(f'{row}.{name} := {value};')
        if app.access_users is not None:
            levels=data.tag(app,'Levels')
            lines += [f'{row}.{n} := {levels}.{n}[{ordinal-1}];' for n in ('ReadLevel','WriteLevel')]
            lines += [f'{row}.Readable := {levels}.Readable[{ordinal-1}] <> 0;']
        else:lines += [f'{row}.ReadLevel := -1;',f'{row}.WriteLevel := -1;',f'{row}.Readable := 1;']
        lines += [f'{row}.ValueText.LEN := 0;',f'IF {row}.Readable THEN']
        live=f'{record.name}Tag.{member.name}'
        if scoped:
            lines += [f'IF {w}.ModelIndex = 0 THEN {w}.Number := {live};',
                f'ELSE {w}.Number := {gen.model_cfg_tag(app)}[{w}.ModelIndex - 1].{member.name}; END_IF;']
        else:lines.append(f'{w}.Number := {live};')
        lines += [f'{w}.Render.LEN := 0;',f'JSR({number_routine(app)},0);',f'CPS({w}.Render,{row}.ValueText,1);','END_IF;',
            f'{target}.EntryCount := {target}.EntryCount + 1;']
        if scoped:lines += ['END_IF;']
    lines += ['ELSE','(* No entry past the deterministic walk. *)','END_CASE;','END_FOR;','END_IF;']
    # Queries outside the model catalog must never leave holes or old values.
    # Normal mailbox callers use 0..catalog; malformed selections return no page.
    lines += [f'IF ({w}.ModelIndex < 0) OR ({w}.ModelIndex > {w}.LastCatalogCount) THEN {target}.EntryCount := 0; END_IF;',
        f'{w}.PageBuilt := 1;']
    status=query_status_tag(app)
    lines += [f'{status}.PageIndex := {w}.PageIndex;',f'{status}.ModelIndex := {w}.ModelIndex;',
        f'{status}.Revision := {w}.Revision;',f'{status}.Accepted := 1;',f'{status}.AckSequence := {w}.QuerySequence;']
    return lines


def routines(app):return [(number_routine(app),number_logic(app)),(page_routine(app),page_logic(app))]
