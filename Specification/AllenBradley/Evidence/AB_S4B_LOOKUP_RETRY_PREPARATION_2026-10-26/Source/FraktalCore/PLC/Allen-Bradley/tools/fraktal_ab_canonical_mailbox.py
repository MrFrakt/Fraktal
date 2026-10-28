"""S3k response/report publication and the remaining derived Unit surface.

The mailbox remains the mutation owner. This renderer translates its numeric
keys/identities once per acknowledgement; it never evaluates release policy.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_canonical_config as config
import fraktal_ab_canonical_text as text
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_manifest as manifest

P=pub.PREFIX
REASON=P+'ReleaseReasonS3kV66'
REPORT=P+'ReleaseReportS3kV66'
RESPONSE=P+'ResponseS3kV66'
REQUEST=P+'RequestS3kV66'
FEATURES=P+'FeaturesS3kV66'
WORK=P+'MailboxWorkS3kV66'
INPUT=P+'MailboxInputS3kV66'
CAPACITY=core.core_limit('MAX_RELEASE_REASONS')


def work_tag(app):return f'FRK_{app.name}_CanonicalMailboxWork'
def key_tag(app):return f'FRK_{app.name}_MailboxKeyText'
def source_tag(app):return f'FRK_{app.name}_MailboxSourceText'
def blank_tag(app):return f'FRK_{app.name}_MailboxEmptyReason'
def routine(app):return f'FRK_{app.name}_CanonicalMailbox'
def number_routine(app):return f'FRK_{app.name}_CanonicalMailboxNumber'
def input_tag(app):return f'FRK_{app.name}_MailboxObservationInput'


def catalogue(app):return {r['NumericKey']:r['PortableKey'] for r in manifest.content(app)['Localization']}


def sources(app):return {i:app.name+('.'+m.name if m else '') for i,m in enumerate((None,*app.modules))}


def literals(app):return [*catalogue(app).values(),*sources(app).values(),mailbox.UNKNOWN_KEY+'#']


def tables(app):
    return {key_tag(app):text.keyed_table(app,catalogue(app)),source_tag(app):text.keyed_table(app,sources(app))}


def validate(app):
    import fraktal_ab_declaration as declaration
    errors=[]
    if not app.canonical_table_driven:errors.append('S3k requires the shared table-driven text pool')
    if any(len(v.encode('utf-8'))>255 for v in literals(app)):
        errors.append('S3k localization/source identity exceeds Core STRING(255)')
    for mode in declaration.declared_modes(app):
        bound=int(app.access_users is not None)+int(mode==app.manual_mode)+2+int(declaration.live_documents(app))
        bound+=sum(not p.modes or mode in p.modes for p in app.start_permits)
        if bound>CAPACITY:errors.append(f'Start release mode {mode} can exceed the complete {CAPACITY}-reason ceiling')
    return errors


def augment(app,definitions):
    M=pub.Member;S=pub.string_type
    definitions[REASON]=(M('Description',S(255)),M('ReasonCode','DINT','ENUM'),
        M('SourcePath',S(255)),M('Kind','DINT','ENUM'),M('Bypassable','BOOL'))
    definitions[REPORT]=(M('Released','BOOL'),M('Count','INT'),M('Reasons',REASON,count=CAPACITY,lower=1))
    definitions[RESPONSE]=(M('AckSequence','DINT','BITSTRING32'),M('Accepted','BOOL'),
        M('Diagnostic',S(255)),M('Report',REPORT),M('ConfigPage',config.PAGE))
    # Core argument/transport metadata and the single ingress are added by the
    # request-binding slice. This engineering profile exposes only live Sequence.
    definitions[REQUEST]=(M('Sequence','DINT','BITSTRING32'),)
    definitions[INPUT]=tuple(M(n,'DINT') for n in ('Sequence','AckSequence','Accepted','DiagnosticKey','ResponseRevision','CoreSerial'))
    definitions[FEATURES]=(M('CaptureEnabled','BOOL'),M('ExportCurrentConfig','BOOL'))
    root=pub.root_type(app)
    definitions[root]=tuple(M(m.name,RESPONSE) if m.name=='HmiResponse' else m for m in definitions[root])
    definitions[root]+=(M('HmiRequest',REQUEST),M('GoodCount','DINT','BITSTRING32'),
        M('NokCount','DINT','BITSTRING32'),M('ReworkCount','DINT','BITSTRING32'),
        M('Starved','BOOL'),M('Blocked','BOOL'),M('Features',FEATURES))
    definitions[WORK]=tuple(M(n,'DINT') for n in ('Initialized','ResponseValid','LastAck','Slot','Key','Index','Source',
        'Number','Negative','Digit','DigitCount','Position','LastDiagnostic','LastAccepted','LastSequence'))+(M('Digits','DINT',count=10),M('Render',S(255)))


def initialize(app,values):
    caps=manifest.content(app)['WriteCapabilities']
    values['Features']=dict(CaptureEnabled=any(c.get('CaptureSourceKey',0) for c in caps),
                            ExportCurrentConfig=bool(app.config_sets))


def tags(app,serialize):
    return [serialize(work_tag(app),WORK,{},access='None'),serialize(blank_tag(app),REASON,{},access='None'),
            serialize(input_tag(app),INPUT,{},access='Read Only'),
            *(serialize(name,text.SLICE,rows,access='None',array=True) for name,(base,rows) in tables(app).items())]


def put_key(app,target,key):
    w=work_tag(app);base,rows=tables(app)[key_tag(app)];index=w+'.Index'
    return [f'{w}.Key := {key};',f'{target}.LEN := 0;',
        f'IF ({w}.Key >= {base}) AND ({w}.Key < {base+len(rows)}) THEN',f'{index} := {w}.Key - {base};',
        *text.put(app,target,f'{key_tag(app)}[{index}].Offset',f'{key_tag(app)}[{index}].Length'),'END_IF;']


def number_logic(app):
    import fraktal_ab_canonical_access as formatting
    return [line.replace(formatting.state_tag(app),work_tag(app)) for line in formatting.number_logic(app)]


def response_logic(app):
    w=work_tag(app);target=app.name+'.HmiResponse';owner=input_tag(app)
    source=gen.release_report_tag(app);row=f'{target}.Report.Reasons[{w}.Slot]';valid=pub.header_tag(app)+'.Valid'
    base,keys=tables(app)[key_tag(app)]
    lines=[f'IF ({source}.Count < 0) OR ({source}.Count > {CAPACITY}) OR ({source}.Overflow <> 0) THEN',
        f'{valid} := 0;',f'{w}.ResponseValid := 0;','ELSE',f'IF ({w}.Initialized = 0) OR ({w}.LastAck <> {owner}.ResponseRevision) OR ({w}.LastDiagnostic <> {owner}.DiagnosticKey) OR ({w}.LastAccepted <> {owner}.Accepted) OR ({w}.LastSequence <> {owner}.AckSequence) THEN',
        f'{w}.ResponseValid := 1;',
        *put_key(app,target+'.Diagnostic',owner+'.DiagnosticKey'),
        f'IF ({owner}.DiagnosticKey <> 0) AND (({owner}.DiagnosticKey < {base}) OR ({owner}.DiagnosticKey >= {base+len(keys)})) THEN',
        *text.put_text(app,w+'.Render',mailbox.UNKNOWN_KEY+'#',255),f'{w}.Number := {owner}.DiagnosticKey;',
        f'JSR({number_routine(app)},0);',f'CPS({w}.Render,{target}.Diagnostic,1);','END_IF;',
        f'FOR {w}.Slot := 0 TO {CAPACITY-1} DO',f'CPS({blank_tag(app)},{row},1);',
        f'IF {w}.Slot < {source}.Count THEN',*put_key(app,row+'.Description',f'{source}.Key[{w}.Slot]'),
        f'{w}.Source := {source}.Source[{w}.Slot];',
        f'IF ({w}.Source >= 0) AND ({w}.Source <= {len(app.modules)}) THEN',
        *text.put(app,row+'.SourcePath',f'{source_tag(app)}[{w}.Source].Offset',f'{source_tag(app)}[{w}.Source].Length'),
        'ELSE',f'{w}.ResponseValid := 0;','END_IF;',f'{row}.ReasonCode := {source}.Reason[{w}.Slot];',
        f'{row}.Kind := {source}.Kind[{w}.Slot];','END_IF;','END_FOR;',
        f'{target}.Report.Count := {source}.Count;',f'{target}.Report.Released := {source}.Released <> 0;',
        f'{target}.Accepted := {owner}.Accepted <> 0;',f'{target}.AckSequence := {owner}.AckSequence;',
        f'{w}.LastAck := {owner}.ResponseRevision;',f'{w}.LastDiagnostic := {owner}.DiagnosticKey;',f'{w}.LastAccepted := {owner}.Accepted;',
        f'{w}.LastSequence := {owner}.AckSequence;',f'{w}.Initialized := 1;','END_IF;','END_IF;',
        f'IF {w}.ResponseValid = 0 THEN {valid} := 0; END_IF;']
    return lines


def cyclic(app):
    import fraktal_ab_machine_state as machine
    import fraktal_ab_canonical_commands as commands
    unit=f'FRK_{app.name}_Unit';w=commands.work_tag(app);q=input_tag(app);owner=mailbox.response_tag_name(app)
    return [f'{q}.Sequence := {w}.OwnerSequence;',f'{q}.AckSequence := {w}.OwnerAck;',
        f'{q}.Accepted := {owner}.Accepted;',f'{q}.DiagnosticKey := {owner}.DiagnosticKey;',
        f'{q}.ResponseRevision := {w}.ResponseRevision;',f'{q}.CoreSerial := {w}.CoreSerial;',
        f'{app.name}.HmiRequest.Sequence := {input_tag(app)}.Sequence;',
        *(f'{app.name}.{target} := {unit}.{source};' for target,source in
            (('GoodCount','GoodCount'),('NokCount','ScrapCount'),('ReworkCount','ReworkCount'))),
        *machine.wait_logic(app,app.name+'.Starved',app.name+'.Blocked',unit),f'JSR({routine(app)},0);',
        *commands.publish_reply(app),*commands.service_status(app)]


def routines(app):return [(routine(app),response_logic(app)),(number_routine(app),number_logic(app))]
