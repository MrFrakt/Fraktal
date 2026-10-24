"""S3d publication of the existing alarm owner and unconditional state flags.

The legacy owner alone appends/closes events. This service mirrors its facts;
text, I/O joins and calendar conversion run only when their inputs change.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_status as diagnostic
import fraktal_ab_canonical_unit_core as core

P=pub.PREFIX
EVENT=P+'AlarmEventS3dV62'
LOG=P+'AlarmLogS3dV62'
META=P+'AlarmMetaS3dV62'
META_LOG=P+'AlarmMetaLogS3dV62'
METADATA=P+'AlarmMetaTableS3dV62'
FLAG=P+'StateFlagS3dV62'
CACHE=P+'AlarmCacheS3dV62'
FLAG_CACHE=P+'FlagCacheS3dV62'
STATE=P+'AlarmStateS3dV62'
TEXT_INPUTS=('ReasonCode','SourceModuleId','IoRoles')
STAMP_INPUTS=('ComeDate','ComeTime','GoneDate','GoneTime')


def metadata_tag(app):return f'FRK_{app.name}_AlarmMetadata'
def state_tag(app):return f'FRK_{app.name}_CanonicalAlarmState'
def cache_type(app):return P+'AlarmCacheS3eV62' if app.canonical_publication_stage>=7 else CACHE
def state_type(app):return P+'AlarmStateS3eV62' if app.canonical_publication_stage>=7 else STATE
def bindings(app):return [dict(SourceSymbol=metadata_tag(app),TargetRoot=app.name)]


def metadata(app):
    import fraktal_ab_manifest as manifest
    rows=manifest.content(app)
    keys={r['NumericKey']:r['PortableKey'] for r in rows['Localization']}
    return [dict(ReasonCode=r['ReasonCode'],Priority=r['Priority'],Category=r['Category'],
        OperatorAction=keys.get(r['ActionKey'],''),Consequence=keys.get(r['ConsequenceKey'],''),
        Shelvable=bool(r['Shelvable'])) for r in rows['Rationalization']]


def validate(app):
    findings=[]
    for row in metadata(app):
        if any(len(row[key].encode('utf-8'))>255 for key in ('OperatorAction','Consequence')):
            findings.append('canonical alarm metadata exceeds Core text width 255')
    if any(len(f.key.encode('utf-8'))>120 for f in app.state_flags):
        findings.append('canonical state flag exceeds Core key width 120')
    return findings


def augment(app,definitions):
    import fraktal_ab_generate as gen
    M=pub.Member
    definitions[EVENT]=tuple(M(name,'DINT','ENUM') for name in ('State','ReasonCode','Severity','ResetClass'))+(
        M('Description',pub.string_type(255)),M('SourcePath',pub.string_type(255)),
        M('ComeAt','LDT','TIMESTAMP'),M('GoneAt','LDT','TIMESTAMP'),M('Duration','DINT','DURATION'),
        M('Shelved','BOOL'),M('IoTag',pub.string_type(80)),M('IoAddress',pub.string_type(80)),
        *(M(name,'BOOL') for name in ('ComeTimeSynchronized','GoneTimeSynchronized',
                                    'ResetTimeSynchronized','ShelfTimeSynchronized')))
    definitions[LOG]=(M('RingHead','DINT'),M('Blocking','BOOL'),M('MetaCount','DINT'),
        M('Active',EVENT,count=gen.ALARM_ACTIVE,lower=1),M('Ring',EVENT,count=gen.ALARM_RING,lower=1))
    definitions[META]=(M('ReasonCode','DINT','ENUM'),M('OperatorAction',pub.string_type(255)),
        M('Consequence',pub.string_type(255)),M('Priority','DINT','ENUM'),M('Category','DINT','ENUM'),M('Shelvable','BOOL'))
    definitions[META_LOG]=(M('Meta',META,count=max(1,len(metadata(app))),lower=1,
                            count_path=app.name+'/AlarmLog/MetaCount'),)
    definitions[METADATA]=(M('AlarmLog',META_LOG),)
    definitions[pub.root_type(app)] += (M('AlarmLog',LOG),)
    if app.state_flags:
        definitions[FLAG]=(M('Key',pub.string_type(120)),M('Value','BOOL'),M('Since','LDT','TIMESTAMP'),M('Stale','BOOL'))
        definitions[pub.root_type(app)] += (M('StateFlagCount','DINT'),M('StateFlags',FLAG,count=len(app.state_flags),lower=1))
    cache=cache_type(app)
    definitions[cache]=tuple(M(name,'DINT') for name in ('Initialized',*TEXT_INPUTS,*STAMP_INPUTS))
    if app.canonical_publication_stage>=7 and app.access_users is not None:
        import fraktal_ab_canonical_access as access
        definitions[cache]+=access.audit_cache_members()
    definitions[FLAG_CACHE]=tuple(M(name,'DINT') for name in ('Initialized','DateCode','ClockCode'))
    definitions[state_type(app)]=(M('Index','DINT'),M('CacheIndex','DINT'),M('ByteIndex','DINT'),M('Changed','DINT'),
        M('Events',cache,count=gen.ALARM_ACTIVE+gen.ALARM_RING),
        *((M('Flags',FLAG_CACHE,count=len(app.state_flags)),) if app.state_flags else ()))


def initialize(app,values):
    values['AlarmLog']=dict(MetaCount=len(metadata(app)))
    if app.state_flags:
        values.update(StateFlagCount=len(app.state_flags),StateFlags=[dict(Key=f.key) for f in app.state_flags])


def tags(app,serialize):
    rows=metadata(app)
    return [serialize(metadata_tag(app),METADATA,dict(AlarmLog=dict(Meta=rows or [{}]))),
            serialize(state_tag(app),state_type(app),{},access='None')]


def cyclic(app):
    import fraktal_ab_generate as gen
    state=state_tag(app);i=state+'.Index';ci=state+'.CacheIndex';byte=state+'.ByteIndex'
    cache=f'{state}.Events[{ci}]';work=diagnostic.work_tag(app);inputs=work+'.Inputs'
    lines=[f'{app.name}.AlarmLog.RingHead := {gen.alarm_active_tag(app)}.RingHead;',
           f'{app.name}.AlarmLog.Blocking := {gen.alarm_active_tag(app)}.Blocking <> 0;']
    for surface,prefix,source,count,offset in (
        ('Active','Act',gen.alarm_active_tag(app),gen.ALARM_ACTIVE,0),
        ('Ring','Ring',gen.alarm_ring_tag(app),gen.ALARM_RING,gen.ALARM_ACTIVE)):
        target=f'{app.name}.AlarmLog.{surface}[{i}]'
        col=lambda name:f'{source}.{prefix}{name}[{i}]'
        lines += [f'FOR {i} := 0 TO {count-1} DO',f'{ci} := {i} + {offset};']
        for name,field in (('State','State'),('ReasonCode','ReasonCode'),('Severity','Severity'),
                           ('ResetClass','ResetClass'),('Duration','DurationMs'),('Shelved','Shelved')):
            lines += [f'{target}.{name} := {col(field)}'+(' <> 0;' if name=='Shelved' else ';')]
        lines += [f'{state}.Changed := 0;',f'IF {cache}.Initialized = 0 THEN {state}.Changed := 1; END_IF;']
        lines += [f'IF {cache}.{name} <> {col(name)} THEN {state}.Changed := 1; END_IF;' for name in TEXT_INPUTS]
        audit=surface=='Ring' and app.canonical_publication_stage>=7 and app.access_users is not None
        if audit:
            import fraktal_ab_canonical_access as access
            lines+=access.audit_changed(app,cache,i,state+'.Changed')
        lines += [f'IF {state}.Changed <> 0 THEN']
        lines += [f'{inputs}.{name} := 0;' for name in diagnostic.INPUT_NAMES]
        lines += [f'{inputs}.Reason := {col("ReasonCode")};',f'{inputs}.IoSource := {col("SourceModuleId")} - 1;',
            f'{inputs}.IoRoles := {col("IoRoles")};',f'JSR({diagnostic.routine_name(app)},0);',
            f'CPS({work}.Diagnostic.Description,{target}.Description,1);',
            f'CPS({work}.Diagnostic.IoTag,{target}.IoTag,1);',f'CPS({work}.Diagnostic.IoAddress,{target}.IoAddress,1);',
            f'{target}.SourcePath.LEN := 0;',f'CASE {col("SourceModuleId")} OF']
        for ordinal,module in enumerate((None,*app.modules),1):
            path=app.name+('.'+module.name if module else '')
            lines += [f'{ordinal}:']+core.put_text(target+'.SourcePath',path,255)
        lines += ['ELSE','(* Unknown source has no invented drill-down path. *)','END_CASE;']
        if audit:lines+=access.audit_update(app,cache,i)
        lines += [f'{cache}.{name} := {col(name)};' for name in TEXT_INPUTS]
        lines += ['END_IF;']
        for stem,target_name in (('Come','ComeAt'),('Gone','GoneAt')):
            date,clock=stem+'Date',stem+'Time'
            lines += [f'IF ({cache}.Initialized = 0) OR ({cache}.{date} <> {col(date)}) OR ({cache}.{clock} <> {col(clock)}) THEN',
                f'{inputs}.DateCode := {col(date)};',f'{inputs}.ClockCode := {col(clock)};',
                f'JSR({diagnostic.timestamp_routine_name(app)},0);',f'{target}.{target_name} := {work}.Diagnostic.Since;',
                f'{cache}.{date} := {col(date)};',f'{cache}.{clock} := {col(clock)};','END_IF;']
        lines += [f'{cache}.Initialized := 1;','END_FOR;']
    if app.state_flags:
        source=gen.state_flags_tag(app);target=f'{app.name}.StateFlags[{i}]';cache=f'{state}.Flags[{i}]'
        lines += [f'FOR {i} := 0 TO {len(app.state_flags)-1} DO',f'{target}.Value := {source}.Value[{i}] <> 0;',
            f'IF ({cache}.Initialized = 0) OR ({cache}.DateCode <> {source}.SinceDate[{i}]) OR',
            f'({cache}.ClockCode <> {source}.SinceTime[{i}]) THEN',
            f'{inputs}.DateCode := {source}.SinceDate[{i}];',f'{inputs}.ClockCode := {source}.SinceTime[{i}];',
            f'JSR({diagnostic.timestamp_routine_name(app)},0);',f'{target}.Since := {work}.Diagnostic.Since;',
            f'{cache}.DateCode := {source}.SinceDate[{i}];',f'{cache}.ClockCode := {source}.SinceTime[{i}];',
            f'{cache}.Initialized := 1;','END_IF;','END_FOR;']
    return lines
