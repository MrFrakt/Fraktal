"""S3b engineering: publish existing diagnostics/timing in their owning PLC.

One private resolver owns reason text, electrical joins and timestamp conversion.
Modules supply their owned inputs; no client reconstructs these relationships.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core

P=pub.PREFIX
DIAGNOSTIC=P+'DiagnosticS3bV61'
INPUTS=P+'DiagnosticInputsS3bV61'
CACHE=P+'DiagnosticCacheS3bV61'
COMMAND_CACHE=P+'DiagCommandCacheS3bV61'
WORK=P+'DiagnosticWorkS3bV61'
IO=P+'DiagnosticIoS3bV61'
INPUT_NAMES=('Owner','Reason','Stamped','DateCode','ClockCode','IoSource','IoRoles','Fault',
             'Held','AreaSafe','Permit','PermitKey')


def work_tag(app):return f'FRK_{app.name}_CanonicalDiagnosticWork'
def cache_tag(app,index):return f'FRK_{app.name}_CanonicalDiagnosticCache{index}'
def io_tag(app):return f'FRK_{app.name}_CanonicalDiagnosticIo'
def area_tag(app):return f'FRK_{app.name}_CanonicalAreaKeys'
def routine_name(app):return f'FRK_{app.name}_CanonicalDiagnostic'


def bindings(app):
    import fraktal_ab_library as library
    rows=[]
    for io_module in app.io_modules:
        for channel in io_module.channels:
            owner=next((i for i,m in enumerate(app.modules,1) if m.name==channel.module_path),None)
            if owner is None:continue
            roles=library.type_of(app.modules[owner-1]).io_roles
            if channel.role not in roles:continue
            bit=roles.index(channel.role)
            if bit>=31:raise ValueError('diagnostic role exceeds positive DINT bit mask')
            direction='O' if channel.direction==1 else 'I'
            rows.append(dict(Source=owner,Mask=1<<bit,ElectricalTag=channel.name,
                             Address=f'{io_module.address}:{direction}.{channel.bit}'))
    return rows


def validate(app):
    import fraktal_ab_manifest as manifest
    findings=[]
    texts=[manifest.reason_key(app,name) for name in app.reasons]
    texts += [m.area_safe_key for m in app.modules]
    texts += [p.key for m in app.modules for _,permits in m.permits for p in permits]
    if any(len(text.encode('utf-8'))>255 for text in texts):
        findings.append('canonical diagnostic description exceeds Core width 255')
    for owner in range(1,len(app.modules)+1):
        owned=[row for row in bindings(app) if row['Source']==owner]
        for column in ('ElectricalTag','Address'):
            if len(' / '.join(row[column] for row in owned).encode('utf-8'))>80:
                findings.append('canonical diagnostic electrical join exceeds Core width 80')
    return findings


def augment(app,definitions):
    import fraktal_ab_generate as gen
    M=pub.Member
    definitions[DIAGNOSTIC]=(M('ReasonCode','DINT','ENUM'),M('Description',pub.string_type(255)),
        M('IoTag',pub.string_type(80)),M('IoAddress',pub.string_type(80)),
        M('Since','LDT','TIMESTAMP'),M('TimeSynchronized','BOOL'))
    # New types preserve the previously accepted S2/S3a layouts verbatim.
    statuses={pub.status_type(bool(app.type_key)),*(pub.status_type(bool(m.type_key)) for m in app.modules)}
    for old in statuses:
        definitions[old+'S3b']=definitions.pop(old)+(M('Diagnostic',DIAGNOSTIC),)
    for kind,fields in list(definitions.items()):
        definitions[kind]=tuple(M(m.name,m.kind+'S3b',m.logical,m.count,m.lower,m.extent,m.count_path,m.indices)
                                if m.kind in statuses else m for m in fields)
    definitions[P+'TimingRowS3bV61']=(M('Id','DINT','ENUM'),M('Label',pub.string_type(120)),
        M('Count','DINT'),*(M(name,'DINT','DURATION') for name in ('Last','Minimum','Maximum','Avg')))
    definitions[P+'CommandTimingS3bV61']=(M('Rows',P+'TimingRowS3bV61',count=gen.CMD_STATS,lower=1),)
    for module in app.modules:
        old=core.leaf_type(module)
        new=old+'S3b'
        if new in definitions:continue
        fields=definitions[old]
        if module.commands:fields += (M('Timing',P+'CommandTimingS3bV61'),)
        definitions[new]=fields
    root=pub.root_type(app)
    leaf_names={core.leaf_type(m) for m in app.modules}
    definitions[root]=tuple(M(m.name,m.kind+'S3b') if m.kind in leaf_names else m for m in definitions[root])
    for name in leaf_names:definitions.pop(name,None)
    definitions[INPUTS]=tuple(M(n,'DINT') for n in INPUT_NAMES)
    definitions[CACHE]=(M('Initialized','DINT'),M('Inputs',INPUTS))
    definitions[COMMAND_CACHE]=definitions[CACHE]+(M('TimingCount','DINT',count=gen.CMD_STATS),)
    definitions[IO]=(M('Source','DINT'),M('Mask','DINT'),M('ElectricalTag',pub.string_type(80)),M('Address',pub.string_type(80)))
    definitions[WORK]=(M('Inputs',INPUTS),M('Diagnostic',DIAGNOSTIC),
        *(M(n,'DINT') for n in ('Changed','Index','ByteIndex','YearNo','MonthNo','DayNo','EraNo',
             'YearOfEra','MonthShift','MonthDays','DayOfYear','DayOfEra','DayCount','HourNo','MinuteNo','SecondNo','Millis','Valid')),
        *(M(n,'LINT') for n in ('EpochSeconds','Nanoseconds','LimitSeconds','EpochNs')))


def initialize(app,values):
    import fraktal_ab_generate as gen
    for module in app.modules:
        if module.commands:
            by_id={c.ordinal:c for c in module.commands}
            values[module.name]['Timing']=dict(Rows=[dict(Id=i if i in by_id else 0,
                Label='std.command.'+by_id[i].name.lower() if i in by_id else '')
                for i in range(1,gen.CMD_STATS+1)])


def private_tags(app,serialize):
    # serialize is the owning publisher's typed initializer, with private access.
    result=[serialize(work_tag(app),WORK,{},access='None')]
    result += [serialize(cache_tag(app,i),COMMAND_CACHE if m is not None and m.commands else CACHE,{},access='None')
               for i,m in enumerate((None,*app.modules))]
    rows=bindings(app)
    # These arrays are private engineering data, not discovered module roots.
    for name,kind,values in ((io_tag(app),IO,rows),(area_tag(app),pub.string_type(255),[m.area_safe_key for m in app.modules])):
        if values:
            result.append(serialize(name,kind,values,access='None',array=True))
    return result


def _floor(target,source,divisor):
    return f'{target} := ({source} - ({source} MOD {divisor})) / {divisor};'


def epoch_logic(app):
    """Convert the owner's stored UTC calendar stamp, including ms, once on change."""
    w=work_tag(app);i=w+'.Inputs';d=w+'.Diagnostic'
    lines=[f'{w}.EpochNs := 0;',f'{d}.Since := {w}.EpochNs;',f'{w}.Valid := 1;',
           f'IF ({i}.Reason <> 0) AND ({i}.Reason = {i}.Stamped) AND ({i}.DateCode > 0) THEN',
           _floor(w+'.YearNo',i+'.DateCode',10000),f'{w}.MonthNo := {i}.DateCode MOD 10000;',
           _floor(w+'.MonthNo',w+'.MonthNo',100),f'{w}.DayNo := {i}.DateCode MOD 100;',
           _floor(w+'.HourNo',i+'.ClockCode',10000000),f'{w}.MinuteNo := {i}.ClockCode MOD 10000000;',
           _floor(w+'.MinuteNo',w+'.MinuteNo',100000),f'{w}.SecondNo := {i}.ClockCode MOD 100000;',
           _floor(w+'.SecondNo',w+'.SecondNo',1000),f'{w}.Millis := {i}.ClockCode MOD 1000;',
           f'IF ({w}.YearNo < 1) OR ({w}.MonthNo < 1) OR ({w}.MonthNo > 12) THEN {w}.Valid := 0; END_IF;',
           f'IF ({w}.DayNo < 1) OR ({w}.DayNo > 31) OR ({i}.ClockCode < 0) THEN {w}.Valid := 0; END_IF;',
           f'IF ({w}.HourNo >= 24) OR ({w}.MinuteNo >= 60) OR ({w}.SecondNo >= 60) THEN {w}.Valid := 0; END_IF;',
           f'{w}.MonthDays := 31;',f'CASE {w}.MonthNo OF',
           f'4,6,9,11: {w}.MonthDays := 30;',f'2: {w}.MonthDays := 28;',
           f'IF (({w}.YearNo MOD 4) = 0) AND ((({w}.YearNo MOD 100) <> 0) OR (({w}.YearNo MOD 400) = 0)) THEN',
           f'{w}.MonthDays := 29;', 'END_IF;', 'ELSE', '(* Other valid months have 31 days. *)', 'END_CASE;',
           f'IF {w}.DayNo > {w}.MonthDays THEN {w}.Valid := 0; END_IF;',
           f'IF {w}.Valid <> 0 THEN',
           f'IF {w}.MonthNo <= 2 THEN {w}.YearNo := {w}.YearNo - 1; END_IF;',
           _floor(w+'.EraNo',w+'.YearNo',400),f'{w}.YearOfEra := {w}.YearNo - {w}.EraNo * 400;',
           f'IF {w}.MonthNo > 2 THEN {w}.MonthShift := {w}.MonthNo - 3; ELSE {w}.MonthShift := {w}.MonthNo + 9; END_IF;',
           f'{w}.DayOfYear := 153 * {w}.MonthShift + 2;',_floor(w+'.DayOfYear',w+'.DayOfYear',5),
           f'{w}.DayOfYear := {w}.DayOfYear + {w}.DayNo - 1;',
           f'{w}.DayOfEra := {w}.YearOfEra * 365 + ({w}.YearOfEra - ({w}.YearOfEra MOD 4)) / 4;',
           f'{w}.DayOfEra := {w}.DayOfEra - ({w}.YearOfEra - ({w}.YearOfEra MOD 100)) / 100 + {w}.DayOfYear;',
           f'{w}.DayCount := {w}.EraNo * 146097 + {w}.DayOfEra - 719468;',
           f'{w}.EpochSeconds := {w}.DayCount;',
           f'{w}.EpochSeconds := {w}.EpochSeconds * 86400 + {w}.HourNo * 3600 + {w}.MinuteNo * 60 + {w}.SecondNo;',
           f'{w}.Nanoseconds := {w}.Millis;',f'{w}.Nanoseconds := {w}.Nanoseconds * 1000000;',
           # Construct wider constants from DINT literals, as measured in S0.
           f'{w}.LimitSeconds := 922337203;',f'{w}.LimitSeconds := {w}.LimitSeconds * 10 + 6;',
           f'IF ({w}.EpochSeconds > {w}.LimitSeconds) OR ({w}.EpochSeconds < (0 - {w}.LimitSeconds - 1)) THEN',
           f'{w}.Valid := 0;',
           f'ELSIF {w}.EpochSeconds = (0 - {w}.LimitSeconds - 1) THEN',
           f'IF {w}.Nanoseconds < 145224192 THEN {w}.Valid := 0; ELSE',
           f'{w}.EpochSeconds := {w}.EpochSeconds + 1;',f'{w}.Nanoseconds := {w}.Nanoseconds - 1000000000;', 'END_IF;',
           f'ELSIF ({w}.EpochSeconds = {w}.LimitSeconds) AND ({w}.Nanoseconds > 854775807) THEN',f'{w}.Valid := 0;', 'END_IF;',
           f'IF {w}.Valid <> 0 THEN',f'{w}.EpochNs := {w}.EpochSeconds * 1000000000 + {w}.Nanoseconds;',
           f'{d}.Since := {w}.EpochNs;', 'END_IF;', 'END_IF;', 'END_IF;',
           f'IF {w}.Valid = 0 THEN {pub.header_tag(app)}.Valid := 0; END_IF;']
    return lines


def resolver(app):
    import fraktal_ab_manifest as manifest
    w=work_tag(app);i=w+'.Inputs';d=w+'.Diagnostic';put=core.put_text
    lines=[f'{d}.ReasonCode := {i}.Reason;',f'{d}.Description.LEN := 0;',f'{d}.IoTag.LEN := 0;',f'{d}.IoAddress.LEN := 0;']
    by_reason={}
    for name,code in app.reasons.items():
        if code:by_reason.setdefault(code,manifest.reason_key(app,name))
    if by_reason:
        lines += [f'CASE {i}.Reason OF']
        for code,key in by_reason.items():lines += [f'{code}:']+put(d+'.Description',key,255)
        lines += ['ELSE','(* Unregistered reasons have no invented description. *)','END_CASE;']
    if app.modules:
        lines += [f'IF ({i}.Held <> 0) AND ({i}.Owner >= 1) AND ({i}.Owner <= {len(app.modules)}) THEN',
                  f'IF ({i}.AreaSafe = 0) AND ({area_tag(app)}[{i}.Owner-1].LEN > 0) THEN',
                  f'CPS({area_tag(app)}[{i}.Owner-1],{d}.Description,1);',
                  f'ELSIF ({i}.Permit = 0) AND ({i}.PermitKey <> 0) THEN']
        permits={p.key for m in app.modules for _,rows in m.permits for p in rows}
        if permits:
            lines += [f'CASE {i}.PermitKey OF']
            for key in sorted(permits):lines += [f'{manifest.numeric_key(app,key)}:']+put(d+'.Description',key,255)
            lines += ['ELSE','(* Keep the reason description for an unknown permit key. *)','END_CASE;']
        lines += ['END_IF;','END_IF;']
    rows=bindings(app)
    if rows:
        lines += [f'FOR {w}.Index := 0 TO {len(rows)-1} DO',
                  f'IF ({io_tag(app)}[{w}.Index].Source = {i}.IoSource) AND (({i}.IoRoles AND {io_tag(app)}[{w}.Index].Mask) <> 0) THEN']
        for column,target in (('ElectricalTag','IoTag'),('Address','IoAddress')):
            source=f'{io_tag(app)}[{w}.Index].{column}';dest=d+'.'+target
            lines += [f'IF {dest}.LEN > 0 THEN']
            for byte in (32,47,32):lines += [f'{dest}.DATA[{dest}.LEN] := {byte};',f'{dest}.LEN := {dest}.LEN + 1;']
            lines += ['END_IF;',f'FOR {w}.ByteIndex := 0 TO {source}.LEN-1 DO',
                      f'{dest}.DATA[{dest}.LEN] := {source}.DATA[{w}.ByteIndex];',f'{dest}.LEN := {dest}.LEN + 1;','END_FOR;']
        lines += ['END_IF;','END_FOR;']
    return lines+epoch_logic(app)


def cyclic(app):
    import fraktal_ab_generate as gen
    w=work_tag(app);lines=[]
    for index,module in enumerate((None,*app.modules)):
        cache=cache_tag(app,index);target=app.name+('.'+module.name if module else '')
        ctx=f'FRK_{app.name}_Unit' if module is None else gen.ctx_tag_for(app,module.name)
        if module is None:
            values=dict(Owner='0',Reason=ctx+'.DiagReason',Stamped=ctx+'.DiagStamped',DateCode=ctx+'.DiagSinceDate',
                        ClockCode=ctx+'.DiagSinceTime',IoSource=ctx+'.ErrorSource',IoRoles=ctx+'.DiagIoRoles',Fault=ctx+'.Error',Held='0',AreaSafe='1',Permit='1',PermitKey='0')
        else:
            fields={m.name for m in gen.module_members(module)}
            values=dict(Owner=str(index),Reason=ctx+'.OutImm_Reason',Stamped=ctx+'.DiagStamped',DateCode=ctx+'.DiagSinceDate',
                        ClockCode=ctx+'.DiagSinceTime',IoSource=str(index),IoRoles=ctx+'.OutImm_IoRoles',Fault=ctx+'.Error',Held=ctx+'.OutImm_Held',
                        AreaSafe=ctx+'.AreaSafe' if 'AreaSafe' in fields else '1',
                        Permit=ctx+'.Permit' if 'Permit' in fields else '1',PermitKey=ctx+'.PermitKey' if 'PermitKey' in fields else '0')
        lines += [f'{w}.Changed := 0;',f'IF {cache}.Initialized = 0 THEN {w}.Changed := 1; END_IF;']
        for name,source in values.items():lines += [f'IF {cache}.Inputs.{name} <> {source} THEN {w}.Changed := 1; END_IF;']
        lines += [f'IF {w}.Changed <> 0 THEN']
        lines += [f'{cache}.Inputs.{name} := {source};' for name,source in values.items()]
        lines += [f'CPS({cache}.Inputs,{w}.Inputs,1);']
        if module is None:lines += [f'IF {ctx}.Error = 0 THEN {w}.Inputs.IoSource := 0; {w}.Inputs.IoRoles := 0; END_IF;']
        lines += [f'JSR({routine_name(app)},0);',
                  f'CPS({w}.Diagnostic,{target}.Status.Diagnostic,1);','END_IF;',
                  f'{target}.Status.Diagnostic.TimeSynchronized := FRK_{app.name}_HealthProbe.TimeIsSynchronized <> 0;']
        if module is not None and module.commands:
            for command in module.commands:
                row=command.ordinal-1;destination=f'{target}.Timing.Rows[{row}]'
                lines += [f'IF ({cache}.Initialized = 0) OR ({cache}.TimingCount[{row}] <> {ctx}.TimCount[{row}]) THEN']
                for name,source in (('Count','TimCount'),('Last','TimLast'),('Minimum','TimMin'),('Maximum','TimMax'),('Avg','TimAvg')):
                    lines += [f'{destination}.{name} := {ctx}.{source}[{row}];']
                lines += [f'{cache}.TimingCount[{row}] := {ctx}.TimCount[{row}];','END_IF;']
        lines += [f'{cache}.Initialized := 1;']
    return lines
