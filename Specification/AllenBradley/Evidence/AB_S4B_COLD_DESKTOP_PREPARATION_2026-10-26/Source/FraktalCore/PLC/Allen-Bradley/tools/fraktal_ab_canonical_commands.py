"""S3k typed ingress and legacy adapter feeding the one mailbox owner.

Engineering only. The live client consumes the V6.6 descriptor and Templates;
application lookup, parsing and permission decisions stay on the controller.
"""
import xml.etree.ElementTree as ET
import fraktal_ab_canonical_publication as pub
import fraktal_ab_command_binding as binding
import fraktal_ab_mailbox as mb
import fraktal_ab_canonical_text as text
import fraktal_ab_generate as gen

P=pub.PREFIX
ARGS=P+'CommandArgsV66';PAYLOAD=P+'CommandPayloadV66';WORK=P+'CommandWorkV66';ROUTE=P+'CommandRouteV66'
DESCRIPTOR=P+'CommandBindingV66'
SET_STATUS=P+'SetServiceStatusV66'
OPERATION=P+'CommandOperationV66'
INVALID='project.mailbox.refused.command_payload_invalid'
COLLISION='project.mailbox.refused.command_ingress_collision'
STALE='project.mailbox.refused.command_sequence_stale'
KEYS=(INVALID,COLLISION,STALE)
# Work.Error codes the ingress sets; anything else is a malformed payload.
COLLIDED,STALE_SERIAL,STALE_REVISION,FOREIGN_ROOT=2,3,4,5


def refusals():
    """Error code -> refusal key. A failed PLC-side resolution keeps the owner's
    own reason (stale revision, unaddressable target) instead of a generic one."""
    import fraktal_ab_config as config
    return ((COLLIDED,COLLISION),(STALE_SERIAL,STALE),(STALE_REVISION,config.CAPTURE_REVISION_KEY),
            (FOREIGN_ROOT,mb.TARGET_KEY))


def refusal(app):
    lines=[f'CASE {work_tag(app)}.Error OF']
    for code,key in refusals():lines+=[f'{code}:',*mb._refuse(app,key)]
    return lines+['ELSE',*mb._refuse(app,INVALID),'END_CASE;']


def enabled(app):return app.canonical_publication_stage>=13
def payload_tag(app):return f'FRK_{app.name}_CoreCommandPayload'
def sample_tag(app):return f'FRK_{app.name}_CoreCommandSample'
def commit_tag(app):return f'FRK_{app.name}_CoreCommandCommit'
def reply_tag(app):return f'FRK_{app.name}_CoreCommandReply'
def work_tag(app):return f'FRK_{app.name}_CoreCommandWork'
def route_tag(app):return f'FRK_{app.name}_CoreCommandRoutes'
def set_status_tag(app):return f'FRK_{app.name}_CoreSetStatus'
def empty_status_tag(app):return f'FRK_{app.name}_CoreSetEmpty'
def routine(app,suffix):return f'FRK_{app.name}_CoreCommand{suffix}'
def string_type(width):return P+f'String{width}CmdV66'


def descriptors(app):
    from fraktal_ab_canonical_mailbox import input_tag
    import fraktal_ab_manifest as manifest
    facts=manifest.content(app)
    return [dict(Version=binding.VERSION,RootSymbol=app.name,PayloadSymbol=payload_tag(app),
        ArgumentsMember='Arguments',CommitSymbol=commit_tag(app),ResponseSymbol=reply_tag(app),
        StatusSymbol=input_tag(app),ConnectionBytes=4000,MaximumPayloadBytes=1024,ReadRole=binding.ROLE,
        CapabilitiesSymbol=f'FRK_{app.name}_MfWriteCapabilities' if facts['WriteCapabilities'] else '',
        CapabilitiesCount=len(facts['WriteCapabilities']),KeysSymbol=f'FRK_{app.name}_MfLocalization',KeysCount=len(facts['Localization']))]


def augment(app,definitions):
    M=pub.Member
    definitions[ARGS]=tuple(M(n,string_type(width) if kind==mb.STRING_MEMBER else 'BOOL' if n=='BoolValue' else 'DINT',
        'ENUM' if n=='Kind' else 'BITSTRING32' if n=='DurationMs' else '',access='Read/Write')
        for n,kind,width,note in mb.REQUEST_MEMBERS if n!='Sequence')
    definitions[PAYLOAD]=tuple(M(n,'DINT',access='Read/Write') for n in binding.HEADER)+(M('Arguments',ARGS,access='Read/Write'),)
    definitions[WORK]=tuple(M(n,'DINT') for n in ('Armed','Pending','NewCore','NewLegacy','CoreSeen','LegacySeen',
        'LastCoreSeen','LastLegacySeen','CoreSerial','OwnerSequence','OwnerAck','OwnerAccepted','OwnerDiagnostic',
        'ResponseRevision','LegacyAck','Error','Index','Cursor','Position','Match','Matches','Purpose','Found',
        'Offset','Length','Sign','Digit','Parsed','Valid','Start','End','Upper','Lower','PriorUpper','Magnitude'))+(M('Seek',string_type(255)),)
    definitions[ROUTE]=tuple(M(n,'DINT') for n in ('Purpose','Offset','Length','Value'))
    definitions[DESCRIPTOR]=tuple(M(k,pub.string_type(40) if k in binding.TEXT_FIELDS else 'DINT')
                                for k in sorted(binding.FIELD))
    definitions[OPERATION]=(M('Kind','DINT'),M('Supported','BOOL'),M('RequiresSetStage','BOOL'),M('RefusalKey',pub.string_type(255)))
    if app.config_sets:
        n=max(1,len(gen.editable_values(app)))
        definitions[SET_STATUS]=(M('SchemaVersion','DINT'),M('Sequence','DINT'),M('Operation','DINT'),M('Kind','DINT'),
            M('Name',pub.string_type(80)),M('Count','DINT'),M('ReasonKey','DINT'),
            M('Values','DINT',count=n),M('Readable','DINT',count=n))


def manifest_members():
    M=pub.Member
    return (M('CommandBindingsCount','DINT'),M('CommandBindingsCapacity','DINT'),M('CommandBindings',DESCRIPTOR,count=1),
        M('CommandOperationsCount','DINT'),M('CommandOperationsCapacity','DINT'),M('CommandOperations',OPERATION,count=len(mb.KINDS)))


def operations(app):
    import fraktal_ab_sets as sets
    refused=mb.refused_for(app)
    return [dict(Kind=kind,Supported=kind!=mb.NONE and kind not in refused,
        RequiresSetStage=bool(app.config_sets and kind in sets.SET_KINDS and kind not in refused),
        RefusalKey=mb.UNKNOWN_KEY if kind==mb.NONE else refused.get(kind,'')) for kind in sorted(mb.KINDS.values())]


def string_data_types():
    out=[]
    for width in sorted({*binding.WIDTHS.values(),255}):
        node=ET.Element('DataType',Name=string_type(width),Family='StringFamily',Class='User')
        fields=ET.SubElement(node,'Members')
        for name,kind,count,radix in [('LEN','DINT',0,'Decimal'),('DATA','SINT',width,'ASCII')]:
            ET.SubElement(fields,'Member',Name=name,DataType=kind,Dimension=str(count),Radix=radix,
                          Hidden='false',ExternalAccess='Read/Write')
        out.append(ET.tostring(node,encoding='unicode'))
    return out


def route_facts(app):
    # Purpose 1 module identity, 2 configuration write key, 3 forceable channel.
    facts=[(4,app.name,1),*((1,app.name+'.'+m.name,i) for i,m in enumerate(app.modules,1))]
    facts += [(2,m.write_key,i) for i,r,m in gen.editable_values(app)]
    for module in app.io_modules:
        for channel in module.channels:
            path=module.name+'.'+channel.name
            target=mb.force_target(app,path)
            if target is None:continue
            try:value=mb.force_argument(*target)
            except ValueError:continue
            facts.append((3,path,value if value<0x80000000 else value-0x100000000))
    facts += [(5,s,v) for s,v in [('true',1),('TRUE',1),('false',0),('FALSE',0),('1',1),('0',0)]]
    if not app.model_capacity:facts += [(6,m.code,i) for i,m in enumerate(app.models,1)]
    return facts


def literals(app):return [app.name,*(label for purpose,label,value in route_facts(app))]


def rows(app):
    return [dict(Purpose=purpose,**text.slice_value(app,label),Value=value) for purpose,label,value in route_facts(app)]


def tags(app,serialize):
    from fraktal_ab_canonical_mailbox import RESPONSE
    return [serialize(payload_tag(app),PAYLOAD,dict(SchemaVersion=binding.VERSION),access='Read/Write'),
        serialize(sample_tag(app),PAYLOAD,{},access='None'),serialize(work_tag(app),WORK,{},access='None'),
        serialize(reply_tag(app),RESPONSE,{}),serialize(route_tag(app),ROUTE,rows(app),array=True,access='None'),
        f'<Tag Name="{commit_tag(app)}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read/Write"/>',
        *([serialize(set_status_tag(app),SET_STATUS,{}),serialize(empty_status_tag(app),SET_STATUS,{},access='None')] if app.config_sets else [])]


def wipe_string(app,value,width):
    i=work_tag(app)+'.Index'
    return [f'{value}.LEN := 0;',f'FOR {i} := 0 TO {width-1} DO',f'{value}.DATA[{i}] := 0;','END_FOR;']


def wipe_transport(app):
    import fraktal_ab_mailbox_frame as frame
    w=work_tag(app);q=mb.request_tag_name(app);p=payload_tag(app)+'.Arguments';s=sample_tag(app)+'.Arguments'
    lines=[f'FOR {w}.Index := 0 TO {frame.word_count(app)-1} DO',f'{q}.Frame.Words[{w}.Index] := 0;',
           f'{frame.sample_tag(app)}.Words[{w}.Index] := 0;','END_FOR;']
    for base in (p,s):
        for n in ('Secret','TextValue'):lines+=wipe_string(app,base+'.'+n,binding.WIDTHS[n])
    return lines


def copy_string(app,target,source):
    i=work_tag(app)+'.Index'
    return [f'{target}.LEN := {source}.LEN;',f'FOR {i} := 0 TO {source}.LEN - 1 DO',
            f'{target}.DATA[{i}] := {source}.DATA[{i}];','END_FOR;']


def ingress(app):
    import fraktal_ab_mailbox_frame as frame
    w=work_tag(app);q=mb.request_tag_name(app);s=sample_tag(app);a=s+'.Arguments'
    lines=[f'{w}.Pending := 0;',f'{w}.NewCore := 0;',f'{w}.NewLegacy := 0;',f'{w}.Error := 0;',
        f'{w}.LegacySeen := {q}.Sequence;',f'{w}.CoreSeen := {commit_tag(app)};',
        f'IF S:FS OR ({w}.Armed = 0) THEN',f'IF {w}.Armed = 0 THEN {w}.CoreSerial := {w}.CoreSeen; END_IF;',
        f'{w}.LastCoreSeen := {w}.CoreSeen;',f'{w}.LastLegacySeen := {w}.LegacySeen;',f'{w}.Armed := 1;',
        *wipe_transport(app),*wipe_string(app,q+'.Secret',32),*wipe_string(app,q+'.TextValue',255),'ELSE',
        f'IF {w}.LegacySeen <> {w}.LastLegacySeen THEN {w}.NewLegacy := 1; {w}.LastLegacySeen := {w}.LegacySeen; END_IF;',
        f'IF {w}.CoreSeen <> {w}.LastCoreSeen THEN',f'{w}.NewCore := 1;',f'{w}.LastCoreSeen := {w}.CoreSeen;',
        # Unsigned serial subtraction in 16-bit halves avoids DINT overflow and
        # needs neither a wide literal nor a platform arithmetic-fault exception.
        f'{w}.Upper := ({w}.CoreSeen AND 2147418112) / 65536;',
        f'IF {w}.CoreSeen < 0 THEN {w}.Upper := {w}.Upper + 32768; END_IF;',
        f'{w}.PriorUpper := ({w}.CoreSerial AND 2147418112) / 65536;',
        f'IF {w}.CoreSerial < 0 THEN {w}.PriorUpper := {w}.PriorUpper + 32768; END_IF;',
        f'{w}.Lower := ({w}.CoreSeen AND 65535) - ({w}.CoreSerial AND 65535);',
        f'{w}.Upper := {w}.Upper - {w}.PriorUpper;',
        f'IF {w}.Lower < 0 THEN {w}.Upper := {w}.Upper - 1; END_IF;',
        f'IF {w}.Upper < 0 THEN {w}.Upper := {w}.Upper + 65536; END_IF;',
        f'IF ({w}.Upper >= 32768) OR (({w}.Upper = 0) AND ({w}.Lower = 0)) THEN {w}.Error := {STALE_SERIAL};',
        f'ELSE {w}.CoreSerial := {w}.CoreSeen; END_IF;','END_IF;',
        f'IF ({w}.NewLegacy <> 0) OR ({w}.NewCore <> 0) THEN',f'{w}.Pending := 1;',
        f'{w}.LegacyAck := {mb.response_tag_name(app)}.AckSequence;',
        f'{w}.OwnerSequence := {w}.LegacySeen;',
        f'IF {w}.NewCore <> 0 THEN {w}.OwnerSequence := {w}.CoreSeen; END_IF;',
        f'IF ({w}.NewLegacy <> 0) AND ({w}.NewCore <> 0) THEN {w}.Error := {COLLIDED};',
        f'ELSIF {w}.NewLegacy <> 0 THEN']
    legacy=list(frame.logic(app,legacy=True))
    assert legacy[0].startswith('IF ') and legacy[-1]=='END_IF;'
    lines+=legacy[1:-1]
    # A stale serial is refused as stale: its payload is never sampled.
    lines += ['ELSE',f'IF {w}.Error = 0 THEN',f'CPS({payload_tag(app)},{s},1);',
        f'IF ({s}.SchemaVersion <> {binding.VERSION}) OR ({s}.ManifestRevision <> {pub.header_tag(app)}.ConfigRevision) OR',
        f'({s}.StagedSequence <> {w}.CoreSeen) OR ({commit_tag(app)} <> {w}.CoreSeen) THEN {w}.Error := 1; END_IF;']
    for n,width in binding.WIDTHS.items():
        lines += [f'IF ({a}.{n}.LEN < 0) OR ({a}.{n}.LEN > {width}) THEN {w}.Error := 1; END_IF;']
    lines += [f'IF {w}.Error = 0 THEN']
    for n in binding.ARGUMENTS:
        if n in binding.WIDTHS:lines+=copy_string(app,q+'.'+n,a+'.'+n)
        elif n=='BoolValue':lines += [f'IF {a}.BoolValue THEN {q}.BoolValue := 1; ELSE {q}.BoolValue := 0; END_IF;']
        else:lines.append(f'{q}.{n} := {a}.{n};')
    lines += [f'JSR({routine(app,"Resolve")},0);','END_IF;','END_IF;','END_IF;',*wipe_transport(app),'END_IF;','END_IF;']
    return lines


def after_owner(app):
    w=work_tag(app);q=mb.request_tag_name(app);a=mb.response_tag_name(app)
    return [f'IF {w}.Pending <> 0 THEN',f'{w}.OwnerAck := {w}.OwnerSequence;',f'{w}.OwnerAccepted := {a}.Accepted;',
        f'{w}.OwnerDiagnostic := {a}.DiagnosticKey;',
        f'IF {w}.ResponseRevision >= 2147483646 THEN {w}.ResponseRevision := 1; ELSE {w}.ResponseRevision := {w}.ResponseRevision + 1; END_IF;',
        # Native legacy clients see only their own ACK, including on collision.
        f'IF {w}.NewLegacy <> 0 THEN {a}.AckSequence := {w}.LegacySeen; ELSE {a}.AckSequence := {w}.LegacyAck; END_IF;',
        *wipe_string(app,q+'.Secret',32),*wipe_string(app,q+'.TextValue',255),'END_IF;']


def publish_reply(app):
    w=work_tag(app);target=reply_tag(app);source=app.name+'.HmiResponse'
    return [f'IF ({w}.NewCore <> 0) AND ({pub.header_tag(app)}.Valid) THEN',f'{target}.Accepted := {source}.Accepted;',
        *(f'CPS({source}.{n},{target}.{n},1);' for n in ('Diagnostic','Report','ConfigPage')),
        f'{target}.AckSequence := {w}.CoreSeen;','END_IF;']


def lookup(app):
    w=work_tag(app);t=route_tag(app);pool=text.pool_tag(app);n=len(rows(app))
    return [f'{w}.Found := 0;',f'{w}.Matches := 0;',f'FOR {w}.Cursor := 0 TO {n-1} DO',
        f'IF {t}[{w}.Cursor].Purpose = {w}.Purpose THEN',f'{w}.Offset := {t}[{w}.Cursor].Offset;',
        f'{w}.Length := {t}[{w}.Cursor].Length;',f'{w}.Match := 0;',
        f'IF ({w}.Length >= 0) AND ({w}.Length <= 255) AND ({w}.Seek.LEN = {w}.Length) THEN',f'{w}.Match := 1;',
        f'FOR {w}.Index := 0 TO {w}.Length - 1 DO',f'{w}.Position := {w}.Offset + {w}.Index;',
        f'IF {w}.Seek.DATA[{w}.Index] <> {pool}[{w}.Position] THEN {w}.Match := 0; END_IF;','END_FOR;','END_IF;',
        f'IF {w}.Match <> 0 THEN {w}.Matches := {w}.Matches + 1; {w}.Found := {t}[{w}.Cursor].Value; END_IF;',
        'END_IF;','END_FOR;',f'IF {w}.Matches <> 1 THEN {w}.Found := 0; END_IF;']


def seek(app,field,purpose):
    w=work_tag(app)
    return [*copy_string(app,w+'.Seek',mb.request_tag_name(app)+'.'+field),f'{w}.Purpose := {purpose};',
            f'JSR({routine(app,"Find")},0);']


def parse_integer(app):
    """Strict full-string DINT parser; optional sign, surrounding ASCII spaces.

    A zero-only decimal suffix accepts a UI's integral '2500.0' spelling. No
    floating conversion can lose a DINT boundary or partially accept a suffix.
    """
    w=work_tag(app)
    return [f'{w}.Valid := 1;',f'{w}.Magnitude := 0;',f'{w}.Parsed := 0;',f'{w}.Sign := 1;',
        f'{w}.Start := 0;',f'{w}.End := {w}.Seek.LEN;',
        f'FOR {w}.Index := 0 TO {w}.Seek.LEN - 1 DO',
        f'IF ({w}.Index = {w}.Start) AND ({w}.Seek.DATA[{w}.Index] = 32) THEN {w}.Start := {w}.Start + 1; END_IF;','END_FOR;',
        f'FOR {w}.Index := {w}.Seek.LEN - 1 TO 0 BY -1 DO',
        f'IF ({w}.Index = {w}.End - 1) AND ({w}.Seek.DATA[{w}.Index] = 32) THEN {w}.End := {w}.End - 1; END_IF;','END_FOR;',
        f'IF {w}.Start < {w}.End THEN',f'{w}.Digit := {w}.Seek.DATA[{w}.Start];',
        f'IF ({w}.Digit = 45) OR ({w}.Digit = 43) THEN',f'IF {w}.Digit = 45 THEN {w}.Sign := -1; END_IF;',
        f'{w}.Start := {w}.Start + 1;','END_IF;','END_IF;',f'{w}.Matches := 0;',f'{w}.Match := 0;',
        f'FOR {w}.Index := {w}.Start TO {w}.End - 1 DO',f'{w}.Digit := {w}.Seek.DATA[{w}.Index];',
        f'IF ({w}.Digit = 46) AND ({w}.Match = 0) AND ({w}.Matches > 0) THEN {w}.Match := 1;',
        f'ELSIF ({w}.Digit < 48) OR ({w}.Digit > 57) THEN {w}.Valid := 0;',
        f'ELSIF {w}.Match <> 0 THEN',f'IF {w}.Digit <> 48 THEN {w}.Valid := 0; END_IF;',
        'ELSE',f'{w}.Matches := {w}.Matches + 1;',
        f'IF ({w}.Magnitude < -214748364) OR (({w}.Magnitude = -214748364) AND ({w}.Digit > 56)) THEN {w}.Valid := 0;',
        f'ELSE {w}.Magnitude := {w}.Magnitude * 10 - ({w}.Digit - 48); END_IF;','END_IF;','END_FOR;',
        f'IF ({w}.Matches = 0) OR (({w}.Sign = 1) AND ({w}.Magnitude = -2147483648)) THEN {w}.Valid := 0; END_IF;',
        f'IF {w}.Valid <> 0 THEN',f'{w}.Parsed := {w}.Magnitude;',
        f'IF {w}.Sign = 1 THEN {w}.Parsed := -{w}.Parsed; END_IF;','END_IF;']


def resolve(app):
    """Resolve Core strings/revisions before the released access/dispatch path."""
    w=work_tag(app);q=mb.request_tag_name(app)
    lines=[f'CASE {q}.Kind OF',f'{mb.MANUAL_COMMAND},{mb.RELEASE_MANUAL}:',*seek(app,'TargetPath',1),
        f'{q}.DurationMs := {w}.Found;',f'{mb.WRITE_CONFIG},{mb.CAPTURE_CONFIG}:',
        *seek(app,'TargetPath',4),f'IF {w}.Matches <> 1 THEN {w}.Error := {FOREIGN_ROOT}; END_IF;',
        f'IF ({w}.Error = 0) AND ({q}.IntValue <> {app.name}.Status.ConfigRev) THEN {w}.Error := {STALE_REVISION}; END_IF;',
        # An unknown key resolves to no ordinal; the owner refuses it by name.
        *seek(app,'NameValue',2),f'{q}.IntValue := {w}.Found;',f'IF {q}.Kind = {mb.WRITE_CONFIG} THEN',
        *copy_string(app,w+'.Seek',q+'.TextValue'),f'JSR({routine(app,"ParseInteger")},0);',
        f'IF ({w}.Error = 0) AND ({w}.Valid = 0) THEN {w}.Error := 1; END_IF;',f'{q}.BoolValue := {w}.Parsed;',
        'ELSE',f'{q}.BoolValue := 0;',f'{q}.DurationMs := {__import__("fraktal_ab_manifest").config_revision(app)};','END_IF;',
        f'{mb.SET_MODEL}:',*model_lookup(app),f'{q}.IntValue := {w}.Found;',
        f'{mb.FORCE_CHANNEL}:',*seek(app,'TargetPath',3),f'{q}.IntValue := {w}.Found;',f'{q}.DurationMs := 0;',
        f'IF {q}.BoolValue <> 0 THEN',*seek(app,'TextValue',5),
        f'IF {w}.Matches <> 1 THEN {w}.Error := 1; END_IF;',f'{q}.DurationMs := {w}.Found;','END_IF;',
        *set_arguments(app),
        'ELSE','(* Other Core arguments already have their owning handler types. *)','END_CASE;']
    return lines


def model_lookup(app):
    import fraktal_ab_models as models
    w=work_tag(app);q=mb.request_tag_name(app)
    if not app.model_capacity:return seek(app,'TextValue',6)
    c=models.tag(app)
    return [f'{w}.Found := 0;',f'{w}.Matches := 0;',
        f'IF ({c}.SchemaVersion = 1) AND ({c}.Count >= 0) AND ({c}.Count <= {app.model_capacity}) THEN',
        f'FOR {w}.Cursor := 0 TO {c}.Count - 1 DO',f'{w}.Length := {c}.CodeLength[{w}.Cursor];',
        f'IF ({w}.Length > 0) AND ({w}.Length <= {models.CODE_MAX}) AND ({q}.TextValue.LEN = {w}.Length) THEN',
        f'{w}.Match := 1;',f'FOR {w}.Index := 0 TO {w}.Length - 1 DO',
        f'{w}.Position := {w}.Cursor * {models.CODE_MAX} + {w}.Index;',
        f'IF {c}.CodeBytes[{w}.Position] <> {q}.TextValue.DATA[{w}.Index] THEN {w}.Match := 0; END_IF;','END_FOR;',
        f'IF {w}.Match <> 0 THEN {w}.Matches := {w}.Matches + 1; {w}.Found := {w}.Cursor + 1; END_IF;',
        'END_IF;','END_FOR;','END_IF;',f'IF {w}.Matches <> 1 THEN {w}.Found := 0; END_IF;']


def set_arguments(app):
    """Core arguments bind the staged service; staging never overrides them."""
    if not app.config_sets:return []
    import fraktal_ab_sets as sets
    w=work_tag(app);q=mb.request_tag_name(app);s=q+'.ConfigSet'
    return [','.join(map(str,sets.SET_KINDS))+':',
        f'IF ({s}.Sequence <> {w}.OwnerSequence) OR ({s}.Operation <> {q}.Kind) THEN {w}.Error := 1; END_IF;',
        f'IF ({s}.NameLength < 0) OR ({s}.NameLength > {sets.NAME_MAX}) THEN {w}.Error := 1; ELSE',
        *copy_string(app,w+'.Seek',q+'.TextValue'),
        f'IF {q}.Kind = {mb.CREATE_MODEL} THEN',*copy_string(app,w+'.Seek',q+'.NameValue'),'END_IF;',
        f'IF ({q}.Kind <> {mb.LIST_CONFIG_SETS}) AND ({q}.Kind <> {mb.IMPORT_CONFIG_SET}) THEN',f'IF {w}.Seek.LEN <> {s}.NameLength THEN {w}.Error := 1; ELSE',
        f'FOR {w}.Index := 0 TO {s}.NameLength - 1 DO',
        f'IF {w}.Seek.DATA[{w}.Index] <> {s}.NameBytes[{w}.Index] THEN {w}.Error := 1; END_IF;','END_FOR;','END_IF;','END_IF;','END_IF;',
        f'IF ({q}.Kind = {mb.SAVE_CONFIG_SET}) OR ({q}.Kind = {mb.EXPORT_CURRENT_CONFIG}) THEN',
        f'IF {s}.Kind <> {q}.IntValue THEN {w}.Error := 1; END_IF;','END_IF;',
        f'IF ({q}.Kind = {mb.IMPORT_CONFIG_SET}) AND ({s}.Commit <> {q}.BoolValue) THEN {w}.Error := 1; END_IF;']


def service_status(app):
    if not app.config_sets:return []
    import fraktal_ab_sets as sets
    import fraktal_ab_access as access
    import fraktal_ab_data_access as data
    o=set_status_tag(app);s=sets.state_tag(app);q=sets.staged_tag(app);w=work_tag(app)
    lines=[f'CPS({empty_status_tag(app)},{o},1);']
    if app.access_users is None:return lines
    level=access.tag(app,'State');caps=f'FRK_{app.name}_MfWriteCapabilities';flags=data.tag(app,'Levels')
    import fraktal_ab_manifest as manifest
    # The loop below indexes the capability rows by ordinal; a truncated table would fault the controller.
    if len(gen.editable_values(app))>next(t.capacity for t in manifest.tables(app) if t.name=='WriteCapabilities'):
        raise ValueError('set-service status requires every editable value in the capability table')
    # A logged-in session that holds the config-set gate; the shared predicate bounds both levels.
    lines += [f'IF ({level}.CurrentLevel > 0) AND {access.permits(app,access.GATES[mb.SAVE_CONFIG_SET])} AND',
        f'({s}.Sequence = {w}.OwnerAck) AND ({mb.response_tag_name(app)}.Accepted <> 0) THEN',
        f'IF ({q}.NameLength >= 0) AND ({q}.NameLength <= {sets.NAME_MAX}) THEN',
        f'{o}.SchemaVersion := 1;',f'{o}.Sequence := {s}.Sequence;',f'{o}.Operation := {q}.Operation;',
        f'{o}.Kind := {q}.Kind;',f'{o}.Count := {s}.Count;',f'{o}.ReasonKey := {s}.Reason;',
        f'{o}.Name.LEN := {q}.NameLength;',f'FOR {w}.Index := 0 TO {q}.NameLength - 1 DO',
        f'{o}.Name.DATA[{w}.Index] := {q}.NameBytes[{w}.Index];','END_FOR;',
        f'FOR {w}.Index := 0 TO {len(gen.editable_values(app))-1} DO',
        f'IF ({caps}[{w}.Index].ConfigKind = {q}.Kind) AND ({flags}.Readable[{w}.Index] <> 0) THEN',
        f'{o}.Values[{w}.Index] := {s}.Snapshot[{w}.Index];',f'{o}.Readable[{w}.Index] := 1;',
        'END_IF;','END_FOR;','END_IF;','END_IF;']
    return lines


def routines(app):
    return [(routine(app,'Find'),lookup(app)),(routine(app,'ParseInteger'),parse_integer(app)),
            (routine(app,'Resolve'),resolve(app))]
