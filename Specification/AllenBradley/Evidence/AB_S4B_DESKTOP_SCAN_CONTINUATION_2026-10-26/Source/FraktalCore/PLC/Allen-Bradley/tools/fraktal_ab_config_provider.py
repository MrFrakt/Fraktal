"""Versioned store-response protocol. PLC validates; adapter only transports I/O.

The wire vocabulary is binding-wide. Live symbols and the negotiated version
come from the canonical manifest, never an application declaration in a client.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core

from fraktal_ab_config_provider_wire import (
    VERSION,SERVICE_KIND,QUERY_KIND,INPUT,ACK,WORK,MAX_SETS,TEXTS,OFFSETS,BYTE_CAPACITY,
    CATALOG,DOCUMENT,REJECTION,layout,payload)
assert MAX_SETS==core.core_limit('MAX_CONFIG_SETS'), 'Provider V1 capacity requires Core contract review'


def request_symbol(app):
    import fraktal_ab_mailbox as mailbox
    return mailbox.request_tag_name(app)

def input_tag(app):return request_symbol(app)+'.ConfigProvider'
def staged_tag(app):return f'FRK_{app.name}_ConfigProviderStaged'
def state_tag(app):return f'FRK_{app.name}_ConfigProviderWork'
def ack_tag(app):return f'FRK_{app.name}_ConfigProviderAck'
def routine_name(app):return f'FRK_{app.name}_ConfigProviderResponse'


def services(app):
    import fraktal_ab_mailbox as mailbox
    import fraktal_ab_canonical_config as config
    import fraktal_ab_manifest as manifest
    rows=[dict(Kind=SERVICE_KIND,Version=VERSION,BuildRevision=manifest.config_revision(app),RequestSymbol=request_symbol(app),
        RequestMember='ConfigProvider',ResponseSymbol=ack_tag(app)),
        dict(Kind=QUERY_KIND,Version=VERSION,BuildRevision=manifest.config_revision(app),RequestSymbol=request_symbol(app),
        RequestMember='Frame',ResponseSymbol=config.query_status_tag(app))]
    if app.canonical_publication_stage>=13 and app.config_sets:
        from fraktal_ab_canonical_commands import set_status_tag
        rows.append(dict(Kind=3,Version=1,BuildRevision=manifest.config_revision(app),RequestSymbol=request_symbol(app),
            RequestMember='ConfigSet',ResponseSymbol=set_status_tag(app)))
    return rows


def members():
    return tuple(pub.Member(name,'DINT',count=count) for name,count in layout())


def native_members():
    import fraktal_ab_declaration as decl
    return tuple(decl.scalar(m.name,dimension=m.count,initial=VERSION if m.name=='SchemaVersion' else 0) for m in members())


def augment(app,definitions):
    M=pub.Member
    definitions[INPUT]=members()
    definitions[ACK]=tuple(M(n,'DINT') for n in ('SchemaVersion','AckSequence','Accepted','ErrorCode','RequestSequence'))
    definitions[WORK]=tuple(M(n,'DINT') for n in ('LastCommit','Valid','Index','ByteIndex','ByteValue','Position','Width',
        'Remaining','Lower','Upper','Prior','Current','ExpectedOperation','Changed'))+(
        M('EpochSeconds','LINT'),)


def tags(app,serialize):
    return [serialize(staged_tag(app),INPUT,{},access='None'),serialize(state_tag(app),WORK,{},access='None'),
            serialize(ack_tag(app),ACK,dict(SchemaVersion=VERSION))]


def _copy_text(app,target,field,width):
    source=staged_tag(app);w=state_tag(app);i=w+'.ByteIndex';offset=OFFSETS[field]
    return [f'{target}.LEN := {source}.TextLength[{field}];',
        f'FOR {i} := 0 TO {target}.LEN - 1 DO',f'{w}.ByteValue := {source}.TextBytes[{offset} + {i}];',
        f'IF {w}.ByteValue > 127 THEN {w}.ByteValue := {w}.ByteValue - 256; END_IF;',
        f'{target}.DATA[{i}] := {w}.ByteValue;','END_FOR;']


def logic(app):
    import fraktal_ab_access as access
    import fraktal_ab_mailbox as mailbox
    import fraktal_ab_sets as sets
    import fraktal_ab_manifest as manifest
    q=input_tag(app);s=staged_tag(app);w=state_tag(app);ack=ack_tag(app);root=app.name
    owner=sets.state_tag(app);command=sets.staged_tag(app);authority=access.tag(app,'State')
    i=w+'.Index';b=w+'.ByteIndex';v=w+'.ByteValue'
    lines=[f'IF ({q}.Commit <> 0) AND ({q}.Commit <> {w}.LastCommit) THEN',
        f'CPS({q},{s},1);',f'{w}.Valid := 1;',
        f'{ack}.Accepted := 0;',f'{ack}.ErrorCode := 1;',
        f'IF ({s}.Commit < 1) OR ({s}.Commit > 2147483646) THEN {w}.Valid := 0; ELSE',
        f'{w}.Prior := {s}.Commit - {w}.LastCommit;',
        f'IF {w}.Prior < 0 THEN {w}.Prior := {w}.Prior + 2147483646; END_IF;',
        f'IF ({w}.LastCommit <> 0) AND (({w}.Prior = 0) OR ({w}.Prior > 1073741823)) THEN {w}.Valid := 0;',
        f'ELSE {w}.LastCommit := {s}.Commit; END_IF;','END_IF;',
        f'IF ({s}.SchemaVersion <> {VERSION}) OR ({s}.Sequence <> {s}.Commit) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.RequestSequence <> {owner}.Sequence) OR ({s}.RequestSequence <> {mailbox.acknowledged_sequence(app)}) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.BuildRevision <> {manifest.config_revision(app)}) OR ({s}.Operation <> {command}.Operation) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.Flags < 0) OR ({s}.Flags > 7) OR ({s}.Count < 0) OR ({s}.Count > {MAX_SETS}) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.DocumentLine < -1) OR ({s}.DocumentLine > {sets.MAX_RECORDS}) OR ({s}.DocumentLines < 0) OR ({s}.DocumentLines > {sets.MAX_RECORDS}) THEN {w}.Valid := 0; END_IF;']
    allowed=','.join(str(k) for k in sets.SET_KINDS)
    lines += [f'CASE {s}.Operation OF',allowed+':','(* Only a configuration-store response. *)',
        'ELSE',f'{w}.Valid := 0;','END_CASE;']
    if app.access_users is None:
        lines += [f'{w}.Valid := 0;']
    else:
        lines += [f'IF ({authority}.CurrentLevel <= 0) OR ({authority}.CurrentLevel > 4) OR',
            f'({authority}.CurrentLevel < {authority}.Required[11]) OR ({authority}.UserLength <= 0) OR',
            f'({authority}.LoginBusy <> 0) OR ({s}.LoginSequence <> {authority}.LoginResultSequence) THEN {w}.Valid := 0; END_IF;']
    # Validate every text before any published mutation; one shared routine
    # owns RFC 3629 validation for all fifteen bounded fields.
    lines += [f'FOR {i} := 0 TO {len(TEXTS)-1} DO',f'CASE {i} OF']
    for field,(_,width) in enumerate(TEXTS):
        lines += [f'{field}: {w}.Width := {width}; {w}.Position := {OFFSETS[field]};']
    lines += ['ELSE',f'{w}.Valid := 0;','END_CASE;',f'JSR({validate_text_routine(app)},0);','END_FOR;']
    lines += [f'IF (({s}.Flags AND {CATALOG}) <> 0) AND ({s}.Count >= 0) AND ({s}.Count <= {MAX_SETS}) THEN',f'FOR {i} := 0 TO {s}.Count - 1 DO',
        f'IF ({s}.SetSchema[{i}] < 1) OR ({s}.SetSchema[{i}] > 65535) OR ({s}.RecordKind[{i}] < 0) OR ({s}.RecordKind[{i}] > 2) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.RecordCount[{i}] < 0) OR ({s}.RecordCount[{i}] > {sets.MAX_RECORDS}) OR ({s}.Synchronized[{i}] < 0) OR ({s}.Synchronized[{i}] > 1) THEN {w}.Valid := 0; END_IF;',
        f'IF ({s}.TextLength[{i} * 3] < 1) OR ({s}.TextLength[{i} * 3 + 1] < 1) THEN {w}.Valid := 0; END_IF;',
        'END_FOR;',f'IF {w}.Valid <> 0 THEN',f'FOR {i} := 0 TO {s}.Count - 1 DO',
        f'FOR {w}.Prior := 0 TO {i} - 1 DO',f'{w}.Changed := 0;',
        f'IF {s}.TextLength[{i} * 3] = {s}.TextLength[{w}.Prior * 3] THEN',f'{w}.Changed := 1;',
        f'FOR {b} := 0 TO {s}.TextLength[{i} * 3] - 1 DO',
        f'IF {s}.TextBytes[{i} * {sum(width for _,width in TEXTS[:3])} + {b}] <> {s}.TextBytes[{w}.Prior * {sum(width for _,width in TEXTS[:3])} + {b}] THEN {w}.Changed := 0; END_IF;',
        'END_FOR;','END_IF;',f'IF {w}.Changed <> 0 THEN {w}.Valid := 0; END_IF;',
        'END_FOR;','END_FOR;','END_IF;','END_IF;',f'IF {w}.Valid <> 0 THEN']
    # Catalog replacement, document and rejection text are independently
    # flagged. Queries/exports never accidentally erase a previously listed set.
    lines += [f'IF ({s}.Flags AND {CATALOG}) <> 0 THEN',f'{root}.ConfigSetCount := {s}.Count;']
    for index in range(MAX_SETS):
        row=f'{root}.ConfigSets[{index}]'
        lines += [f'{row}.Used := 0;',f'{row}.SetName.LEN := 0;',f'{row}.RootIdentity.LEN := 0;',f'{row}.ModelCode.LEN := 0;']
        lines += [f'{row}.{name} := 0;' for name in ('SetSchema','ConfigRev','Kind','RecordCount','TimeSynchronized')]
        lines += [f'{w}.EpochSeconds := 0;',f'{row}.CreatedAt := {w}.EpochSeconds;']
        lines += [f'IF {s}.Count > {index} THEN',f'{row}.Used := 1;']
        for j,(name,width) in enumerate((('SetName',80),('RootIdentity',80),('ModelCode',64))):
            lines += _copy_text(app,row+'.'+name,index*3+j,width)
        for dst,src in (('SetSchema','SetSchema'),('ConfigRev','ConfigRevision'),('Kind','RecordKind'),('RecordCount','RecordCount')):
            lines += [f'{row}.{dst} := {s}.{src}[{index}];']
        lines += [f'{row}.TimeSynchronized := {s}.Synchronized[{index}] <> 0;',
            f'{w}.EpochSeconds := {s}.CreatedSeconds[{index}];',f'IF {w}.EpochSeconds < 0 THEN',
            f'{w}.EpochSeconds := {w}.EpochSeconds + 2147483647;',f'{w}.EpochSeconds := {w}.EpochSeconds + 2147483647 + 2;','END_IF;',
            f'{w}.EpochSeconds := {w}.EpochSeconds * 1000000000;',f'{row}.CreatedAt := {w}.EpochSeconds;','END_IF;']
    lines += ['END_IF;',f'IF ({s}.Flags AND {DOCUMENT}) <> 0 THEN']
    lines += _copy_text(app,root+'.ConfigSetDocument',MAX_SETS*3,480)
    lines += [f'{root}.ConfigSetDocumentLine := {s}.DocumentLine;',f'{root}.ConfigSetDocumentLines := {s}.DocumentLines;','END_IF;',
        f'IF ({s}.Flags AND {REJECTION}) <> 0 THEN']
    lines += _copy_text(app,root+'.ConfigPersist.LastRejectScope',MAX_SETS*3+1,80)
    lines += _copy_text(app,root+'.ConfigPersist.LastRejectKey',MAX_SETS*3+2,160)
    lines += ['END_IF;',f'{ack}.Accepted := 1;',f'{ack}.ErrorCode := 0;','END_IF;',
        f'{ack}.RequestSequence := {s}.RequestSequence;',f'{ack}.AckSequence := {s}.Commit;','END_IF;']
    return lines


def validate_text_routine(app):return f'FRK_{app.name}_ConfigProviderText'

def validate_text_logic(app):
    s=staged_tag(app);w=state_tag(app);i=w+'.Index';b=w+'.ByteIndex';v=w+'.ByteValue'
    return [f'IF ({s}.TextLength[{i}] < 0) OR ({s}.TextLength[{i}] > {w}.Width) THEN',f'{w}.Valid := 0;','ELSE',
            f'{w}.Remaining := 0;',f'{w}.Lower := 128;',f'{w}.Upper := 191;',
            f'FOR {b} := 0 TO {s}.TextLength[{i}] - 1 DO',f'{v} := {s}.TextBytes[{w}.Position + {b}];',
            f'IF ({v} < 1) OR ({v} > 255) THEN {w}.Valid := 0;',
            f'ELSIF {w}.Remaining > 0 THEN',
            f'IF ({v} < {w}.Lower) OR ({v} > {w}.Upper) THEN {w}.Valid := 0; END_IF;',
            f'{w}.Remaining := {w}.Remaining - 1;',f'{w}.Lower := 128;',f'{w}.Upper := 191;',
            f'ELSIF {v} < 128 THEN','(* ASCII code point. *)',
            f'ELSIF ({v} >= 194) AND ({v} <= 223) THEN {w}.Remaining := 1;',
            f'ELSIF ({v} >= 224) AND ({v} <= 239) THEN',f'{w}.Remaining := 2;',
            f'IF {v} = 224 THEN {w}.Lower := 160; END_IF;',f'IF {v} = 237 THEN {w}.Upper := 159; END_IF;',
            f'ELSIF ({v} >= 240) AND ({v} <= 244) THEN',f'{w}.Remaining := 3;',
            f'IF {v} = 240 THEN {w}.Lower := 144; END_IF;',f'IF {v} = 244 THEN {w}.Upper := 143; END_IF;',
            'ELSE',f'{w}.Valid := 0;','END_IF;','END_FOR;',f'IF {w}.Remaining <> 0 THEN {w}.Valid := 0; END_IF;','END_IF;']


