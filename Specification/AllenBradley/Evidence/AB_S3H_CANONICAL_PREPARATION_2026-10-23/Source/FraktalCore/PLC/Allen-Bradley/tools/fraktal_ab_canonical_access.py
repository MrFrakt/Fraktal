"""PLC-owned session/data policy and enrichment of the existing event ring.

Registration/credential storage remains private. The Access owner alone logs
events and changes authority; this service publishes its already-owned facts.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_access as owner
import fraktal_ab_data_access as data

P=pub.PREFIX
POLICY=P+'AccessPolicyS3eV62'
CLASS=P+'DataClassS3eV62'
ACCESS=P+'AccessS3eV62'
CLASS_CACHE=P+'ClassCacheS3eV62'
WORK=P+'AccessWorkS3eV62'
AUDIT_FIELDS=('Key','Sequence','Kind','Gate','UserLength','DataCapability','DataRequiredLevel')


def state_tag(app):return f'FRK_{app.name}_CanonicalAccessWork'
def audit_routine(app):return f'FRK_{app.name}_CanonicalAccessAudit'
def number_routine(app):return f'FRK_{app.name}_CanonicalAccessNumber'


def keys(app):
    import fraktal_ab_manifest as mf
    return {r['NumericKey']:r['PortableKey'] for r in mf.content(app)['Localization']}


def validate(app):
    findings=[]
    for c in app.data_classes:
        if len(c.label_key.encode('utf-8'))>160:findings.append('canonical data-class label exceeds Core width 160')
    # Audit actors can include arbitrary bytes from a rejected login. The
    # oracle replaces each non-ASCII byte with one three-byte U+FFFD glyph.
    import fraktal_ab_manifest as mf
    rows=mf.content(app);catalogue=keys(app)
    longest=max((len(catalogue.get(r['WriteKeyKey'],'').encode('utf-8')) for r in rows['WriteCapabilities']),default=0)
    longest_key=max((len(k) for k in catalogue.values() if k.startswith('std.audit.')),default=0)
    maximum=longest_key+2+owner.WIDTH*3+len(' [kind=, gate=]')+22
    maximum+=max(len(' [automatic]'),len(' [value=, required=]')+longest+11)
    if maximum>255:findings.append('canonical audit description can exceed Core width 255')
    return findings


def augment(app,definitions):
    M=pub.Member
    definitions[POLICY]=(M('Required','DINT','ENUM',count=owner.GATE_COUNT),M('SessionTimeout','DINT','DURATION'))
    fields=(M('CurrentLevel','DINT','ENUM'),M('CurrentUser',pub.string_type(owner.WIDTH)),M('LoginFailed','BOOL'),M('Policy',POLICY))
    if app.access_users is not None:
        fields+=(M('LoginBusy','BOOL'),M('LoginTimeoutMs','DINT','DURATION'),M('LoginPrehashRounds','DINT'),
                 M('LoginResultSequence','DINT','BITSTRING32'),M('ClassCount','DINT'))
        if app.data_classes:
            definitions[CLASS]=(M('ClassId',pub.string_type(40)),M('LabelKey',pub.string_type(160)),M('ReadLevel','DINT','ENUM'),M('WriteLevel','DINT','ENUM'))
            fields+=(M('Classes',CLASS,count=len(app.data_classes),lower=1,count_path=app.name+'/Access/ClassCount'),)
    definitions[ACCESS]=fields
    definitions[pub.root_type(app)]+=(M('Access',ACCESS),)
    definitions[CLASS_CACHE]=(M('Initialized','DINT'),M('ClassKey','DINT'),M('LabelKey','DINT'))
    definitions[WORK]=tuple(M(n,'DINT') for n in ('Index','ByteIndex','WordIndex','ByteValue','UserLength','AuditSlot','Number','Negative','Digit','DigitCount','Position'))+(
        M('Digits','DINT',count=10),M('Render',pub.string_type(255)),
        *((M('Classes',CLASS_CACHE,count=len(app.data_classes)),) if app.data_classes else ()))


def initialize(app,values):values['Access']=dict(Policy={})
def tags(app,serialize):return [serialize(state_tag(app),WORK,{},access='None')]


def cyclic(app):
    target=app.name+'.Access';work=state_tag(app);i=work+'.Index';b=work+'.ByteIndex'
    if app.access_users is None:
        return [f'{target}.CurrentLevel := 0;',f'{target}.CurrentUser.LEN := 0;',f'{target}.LoginFailed := 0;']
    source=owner.tag(app,'State');policy=data.tag(app,'Policy')
    lines=[f'{target}.{n} := {source}.{n}'+(' <> 0;' if n in ('LoginFailed','LoginBusy') else ';')
           for n in ('CurrentLevel','LoginFailed','LoginBusy','LoginTimeoutMs','LoginPrehashRounds','LoginResultSequence')]
    lines += [f'{target}.Policy.SessionTimeout := {source}.SessionTimeout;',
        f'FOR {i} := 0 TO {owner.GATE_COUNT-1} DO',f'{target}.Policy.Required[{i}] := {source}.Required[{i}];','END_FOR;',
        f'{target}.CurrentUser.LEN := 0;',f'{work}.UserLength := {source}.UserLength;',
        f'IF {work}.UserLength < 0 THEN {work}.UserLength := 0; END_IF;',
        f'IF {work}.UserLength > {owner.WIDTH} THEN {work}.UserLength := {owner.WIDTH}; END_IF;',
        f'FOR {b} := 0 TO {work}.UserLength - 1 DO',
        f'{target}.CurrentUser.DATA[{b}] := {source}.UserBytes[{b}];',
        f'{target}.CurrentUser.LEN := {target}.CurrentUser.LEN + 1;','END_FOR;',f'{target}.ClassCount := 0;']
    if app.data_classes:
        lines += [f'IF ({policy}.SchemaVersion = 1) AND ({policy}.Count >= 0) AND ({policy}.Count <= {len(app.data_classes)}) THEN',
            f'{target}.ClassCount := {policy}.Count;',f'FOR {i} := 0 TO {target}.ClassCount - 1 DO']
        cache=f'{work}.Classes[{i}]';row=f'{target}.Classes[{i}]'
        lines += [f'{row}.ReadLevel := {policy}.ReadLevel[{i}];',f'{row}.WriteLevel := {policy}.WriteLevel[{i}];',
            f'IF ({cache}.Initialized = 0) OR ({cache}.ClassKey <> {policy}.ClassKey[{i}]) OR ({cache}.LabelKey <> {policy}.LabelKey[{i}]) THEN']
        for member,width in (('ClassId',40),('LabelKey',160)):
            key='ClassKey' if member=='ClassId' else 'LabelKey'
            texts={r.class_id if member=='ClassId' else r.label_key for r in app.data_classes}
            lines += [f'{row}.{member}.LEN := 0;',f'CASE {policy}.{key}[{i}] OF']
            for number,text in keys(app).items():
                if text in texts:lines += [f'{number}:']+core.put_text(row+'.'+member,text,width)
            lines += ['ELSE','(* Unknown published identity remains empty, as in the oracle. *)','END_CASE;']
        lines += [f'{cache}.ClassKey := {policy}.ClassKey[{i}];',f'{cache}.LabelKey := {policy}.LabelKey[{i}];',f'{cache}.Initialized := 1;','END_IF;','END_FOR;','END_IF;']
    return lines


def audit_cache_members():
    return tuple(pub.Member('Audit'+n,'DINT') for n in (*AUDIT_FIELDS,'Schema','RingState'))+(pub.Member('AuditWords','DINT',count=owner.ACTOR_WORDS),)


def audit_changed(app,cache,index,changed):
    import fraktal_ab_generate as gen
    source=owner.tag(app,'Audit');work=state_tag(app);j=work+'.WordIndex'
    lines=[f'IF {cache}.Audit{n} <> {source}.{n}[{index}] THEN {changed} := 1; END_IF;' for n in AUDIT_FIELDS]
    return lines+[f'IF {cache}.AuditSchema <> {source}.SchemaVersion THEN {changed} := 1; END_IF;',
        f'IF {cache}.AuditRingState <> {gen.alarm_ring_tag(app)}.RingState[{index}] THEN {changed} := 1; END_IF;',
        f'FOR {j} := 0 TO {owner.ACTOR_WORDS-1} DO',
        f'IF {cache}.AuditWords[{j}] <> {source}.UserWords[{index} * {owner.ACTOR_WORDS} + {j}] THEN {changed} := 1; END_IF;','END_FOR;']


def audit_update(app,cache,index):
    import fraktal_ab_generate as gen
    source=owner.tag(app,'Audit');work=state_tag(app);j=work+'.WordIndex'
    return [f'{work}.AuditSlot := {index};',f'JSR({audit_routine(app)},0);',
        *[f'{cache}.Audit{n} := {source}.{n}[{index}];' for n in AUDIT_FIELDS],
        f'{cache}.AuditSchema := {source}.SchemaVersion;',f'{cache}.AuditRingState := {gen.alarm_ring_tag(app)}.RingState[{index}];',
        f'FOR {j} := 0 TO {owner.ACTOR_WORDS-1} DO',f'{cache}.AuditWords[{j}] := {source}.UserWords[{index} * {owner.ACTOR_WORDS} + {j}];','END_FOR;']


def append_byte(app,value):
    render=state_tag(app)+'.Render'
    return [f'IF {render}.LEN < 255 THEN',f'{render}.DATA[{render}.LEN] := {value};',f'{render}.LEN := {render}.LEN + 1;',
            'ELSE',f'{pub.header_tag(app)}.Valid := 0;','END_IF;']


def append_text(app,text):
    raw=text.encode('utf-8');render=state_tag(app)+'.Render'
    if not raw:return []
    return [f'IF {render}.LEN + {len(raw)} <= 255 THEN',
        *[f'{render}.DATA[{render}.LEN + {i}] := {byte if byte<128 else byte-256};' for i,byte in enumerate(raw)],
        f'{render}.LEN := {render}.LEN + {len(raw)};','ELSE',f'{pub.header_tag(app)}.Valid := 0;','END_IF;']


def number_logic(app):
    w=state_tag(app);n=w+'.Number';digit=w+'.Digit';count=w+'.DigitCount';i=w+'.Position'
    # Work in the negative domain so MIN_DINT has no overflowing ABS/negation.
    return [f'{w}.Negative := 0;',f'IF {n} < 0 THEN {w}.Negative := 1; ELSE {n} := -{n}; END_IF;',
        f'{count} := 0;',f'{digit} := {n} MOD 10;',f'{w}.Digits[{count}] := 48 - {digit};',f'{count} := {count} + 1;',
        f'{n} := ({n} - {digit}) / 10;',f'FOR {i} := 1 TO 9 DO',f'IF {n} <> 0 THEN',
        f'{digit} := {n} MOD 10;',f'{w}.Digits[{count}] := 48 - {digit};',f'{count} := {count} + 1;',f'{n} := ({n} - {digit}) / 10;','END_IF;','END_FOR;',
        f'IF {w}.Negative <> 0 THEN',*append_byte(app,'45'),'END_IF;',
        f'FOR {i} := 1 TO {count} DO',*append_byte(app,f'{w}.Digits[{count} - {i}]'),'END_FOR;']


def audit_logic(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    import fraktal_ab_shelving as shelving
    w=state_tag(app);i=w+'.AuditSlot';source=owner.tag(app,'Audit');ring=gen.alarm_ring_tag(app)
    target=f'{app.name}.AlarmLog.Ring[{i}]';render=w+'.Render';b=w+'.ByteIndex';byte=w+'.ByteValue'
    col=lambda name:f'{source}.{name}[{i}]'
    lines=[f'IF ({source}.SchemaVersion = {owner.AUDIT_SCHEMA}) AND ({col("Key")} <> 0) AND',
        f'({ring}.RingState[{i}] = {gen.ALARM_CLOSED}) AND ({ring}.RingReasonCode[{i}] = 0) THEN',
        f'{render}.LEN := 0;',f'CASE {col("Key")} OF']
    for number,text in keys(app).items():
        if text.startswith('std.audit.'):lines += [f'{number}:']+append_text(app,text)
    lines += ['ELSE','(* Unknown audit key has the oracle\'s empty prefix. *)','END_CASE;',*append_text(app,': '),
        f'{w}.UserLength := {col("UserLength")};',f'IF {w}.UserLength < 0 THEN {w}.UserLength := 0; END_IF;',
        f'IF {w}.UserLength > {owner.WIDTH} THEN {w}.UserLength := {owner.WIDTH}; END_IF;',
        f'FOR {b} := 0 TO {w}.UserLength - 1 DO',f'{w}.WordIndex := {i} * {owner.ACTOR_WORDS} + ({b} - ({b} MOD 4)) / 4;',f'CASE {b} MOD 4 OF']
    word=f'{source}.UserWords[{w}.WordIndex]'
    for j in range(4):
        mask=(255 if j<3 else 127)<<(j*8)
        lines += [f'{j}:',f'{byte} := ({word} AND {mask}) / {1<<(j*8)};']
        if j==3:lines += [f'IF {word} < 0 THEN {byte} := {byte} + 128; END_IF;']
    lines += ['ELSE',f'{byte} := 0;','END_CASE;',f'IF {byte} > 127 THEN',
        *append_text(app,'\ufffd'),'ELSE',*append_byte(app,byte),'END_IF;','END_FOR;',*append_text(app,' [kind='),
        f'{w}.Number := {col("Kind")};',f'JSR({number_routine(app)},0);',*append_text(app,', gate='),
        f'{w}.Number := {col("Gate")};',f'JSR({number_routine(app)},0);',*append_text(app,']')]
    lines += core.put_text(target+'.SourcePath',app.name+'.Access',255)
    shelved=[mf.numeric_key(app,k) for k in (shelving.SHELVED,shelving.UNSHELVED)]
    lines += [f'IF ({col("Key")} = {shelved[0]}) OR ({col("Key")} = {shelved[1]}) THEN',
        f'(* Base source resolution already selected the module for shelving. *)',
        f'{target}.SourcePath.LEN := 0;',f'CASE {ring}.RingSourceModuleId[{i}] OF']
    for ordinal,module in enumerate((None,*app.modules),1):
        lines += [f'{ordinal}:']+core.put_text(target+'.SourcePath',app.name+('.'+module.name if module else ''),255)
    lines += ['ELSE','(* Unknown module has no invented source path. *)','END_CASE;',
        f'IF {col("Sequence")} = 0 THEN',*append_text(app,' [automatic]'),'END_IF;','END_IF;',
        f'IF {col("DataCapability")} <> 0 THEN',*append_text(app,' [value='),f'CASE {col("DataCapability")} OF']
    catalogue=keys(app)
    for row in mf.content(app)['WriteCapabilities']:
        lines += [f'{row["CapabilityIndex"]}:']+append_text(app,catalogue.get(row['WriteKeyKey'],''))
    lines += ['ELSE','(* Unknown capability has the oracle\'s empty write key. *)','END_CASE;',*append_text(app,', required='),
        f'{w}.Number := {col("DataRequiredLevel")};',f'JSR({number_routine(app)},0);',*append_text(app,']'),'END_IF;',
        f'CPS({render},{target}.Description,1);','END_IF;']
    return lines


def routines(app):return [(number_routine(app),number_logic(app)),(audit_routine(app),audit_logic(app))] if app.access_users is not None else []
