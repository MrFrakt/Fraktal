"""Approved V6.8 read-only configuration view; the existing R2 owner is authority.

No client mailbox query or private-cache exposure. New profiles opt in; older
generated artifacts are byte-identical. Every public value is PLC-formatted and
masked, including its full StringFamily buffer when access drops.
"""
import hashlib
import re

MINOR=8
SERVICE_FIELD=frozenset(('Kind','Version','RootSymbol','CanonicalRoot'))
SERVICE_HEADERS=frozenset(('ReadServicesCount','ReadServicesCapacity','ReadServices'))
VIEW='FRK_T_ConfigReadViewV1'
DEFINITION='FRK_T_ConfigReadDefV1'
VALUE='FRK_T_ConfigReadValueV1'
WORK='FRK_T_ConfigReadWorkV1'
SERVICE='FRK_T_ReadServiceV68'


def enabled(app):return app.canonical_config_read_view
def work_type(app):return 'FRK_T_ConfigReadWorkV610' if app.canonical_owner_revisions else WORK
def _name(app,suffix):
    value=f'FRK_{app.name}_{suffix}'
    return value if len(value)<=40 else value[:23]+'_'+hashlib.sha256(value.encode()).hexdigest()[:16]
def tag(app):return _name(app,'ConfigRead')
def work_tag(app):return _name(app,'ConfigReadWork')
def canonical_root(app):return app.name+'Configuration/ReadView'
def products(app):return [dict(SourceSymbol=tag(app),CoreType='ST_ConfigReadViewV1',CanonicalRoot=canonical_root(app))] if enabled(app) else []
def descriptors(app):return [dict(Kind=1,Version=1,RootSymbol=app.name,CanonicalRoot=canonical_root(app))] if enabled(app) else []


def validate_descriptors(rows):
    """Runtime validation: no declaration or generator imports."""
    if not isinstance(rows,list) or not 1<=len(rows)<=1024:raise ValueError('invalid read-service count')
    roots=set();views=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!=SERVICE_FIELD or type(row['Kind']) is not int or row['Kind']!=1 \
                or type(row['Version']) is not int or row['Version']!=1 \
                or not isinstance(row['RootSymbol'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,39}',row['RootSymbol']) \
                or not isinstance(row['CanonicalRoot'],str) or len(row['CanonicalRoot'].encode())>255 \
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)+',row['CanonicalRoot']) \
                or row['RootSymbol'] in roots or row['CanonicalRoot'] in views:
            raise ValueError('invalid or duplicate read-service descriptor')
        roots.add(row['RootSymbol']);views.add(row['CanonicalRoot'])
    return rows


def capacities(app):
    import fraktal_ab_canonical_config as owner
    definitions=owner.def_rows(app)
    scoped=sum(bool(row['ModelScoped']) for row in definitions)
    return len(definitions),len(definitions)+(app.model_capacity or len(app.models))*scoped


def validate(app):
    errors=[]
    if type(app.canonical_config_read_view) is not bool:return ['canonical_config_read_view must be a BOOL opt-in']
    if not enabled(app):return errors
    if not app.canonical_read_coherence or not app.canonical_table_driven or app.canonical_publication_stage!=13:
        return ['configuration read view requires the complete V6.7/R2 profile']
    definitions,values=capacities(app)
    if not 1<=definitions<=32767 or not definitions<=values<=65535:
        errors.append('configuration read view exceeds the declared table wire extent; split the publication, never truncate')
    return errors


def augment(app,schema):
    if not enabled(app):return
    from fraktal_ab_canonical_publication import Member as M,string_type as S
    import fraktal_ab_canonical_config as owner
    definitions,values=capacities(app);root=canonical_root(app)
    schema[DEFINITION]=(M('DefinitionIndex','DINT'),*(m for m in schema[owner.ENTRY] if m.name not in ('ValueText','Readable')))
    schema[VALUE]=(M('DefinitionIndex','DINT'),M('ModelOrdinal','DINT'),M('ModelCode',S(64)),
                   M('ValueText',S(255)),M('Readable','BOOL'),M('Revision','DINT','BITSTRING32'))
    schema[VIEW]=(M('SchemaVersion','DINT','UINT16'),M('RootIdentity',S(80)),M('Revision','DINT','BITSTRING32'),
        M('DefinitionCount','DINT'),M('DefinitionCapacity','DINT'),
        M('Definitions',DEFINITION,count=definitions,lower=0,count_path=root+'/DefinitionCount'),
        M('ValueCount','DINT'),M('ValueCapacity','DINT'),
        M('Values',VALUE,count=values,lower=0,count_path=root+'/ValueCount'))
    schema[work_type(app)]=tuple(M(n,'DINT') for n in ('Initialized','LastRevision','DefinitionIndex','ValueIndex','ModelIndex','DataIndex'))+(M('CleanText',S(255)),)
    if app.canonical_owner_revisions:schema[work_type(app)]+=(M('LastInvalid','DINT'),)


def manifest_members():
    from fraktal_ab_canonical_publication import Member as M
    return M('ReadServicesCount','DINT'),M('ReadServicesCapacity','DINT'),M('ReadServices',SERVICE,count=1)


def augment_manifest(app,schema):
    if not enabled(app):return
    from fraktal_ab_canonical_publication import Member as M,string_type as S,header_type
    schema[SERVICE]=(M('Kind','DINT'),M('Version','DINT'),M('RootSymbol',S(40)),M('CanonicalRoot',S(255)))
    schema[header_type(app)]+=manifest_members()


def tags(app,serialize):
    if not enabled(app):return []
    definitions,values=capacities(app)
    return [serialize(tag(app),VIEW,dict(SchemaVersion=1,RootIdentity=app.name,DefinitionCount=definitions,
                                      DefinitionCapacity=definitions,ValueCapacity=values)),
            serialize(work_tag(app),work_type(app),{},access='None')]


def cyclic(app):
    if not enabled(app):return []
    import fraktal_ab_canonical_config as owner
    import fraktal_ab_canonical_text as text
    import fraktal_ab_data_access as access
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as manifest
    import fraktal_ab_owner_read_bindings as publication
    definitions,capacity=capacities(app)
    v=tag(app);w=work_tag(app);source=owner.state_tag(app)
    index=w+'.DefinitionIndex';position=w+'.ValueIndex';model=w+'.ModelIndex'
    d=f'{owner.defs_tag(app)}[{index}]';definition=f'{v}.Definitions[{index}]';row=f'{v}.Values[{position}]'
    source_cache=f'{source}.ValueCache[{w}.DataIndex]'
    clean=w+'.CleanText';levels=access.tag(app,'Levels')
    maximum_banks=app.model_capacity or len(app.models)
    # Leave cold formatting off the first Run scan. The existing refusal path
    # withholds the manifest and clears every value buffer, including unused
    # tails. Retained views still rebuild/mask immediately on access changes.
    lines=[f'IF ({source}.LastCatalogCount < 0) OR ({source}.LastCatalogCount > {maximum_banks}) OR (({w}.Initialized = 0) AND S:FS) THEN',
           f'{__import__("fraktal_ab_canonical_publication").header_tag(app)}.Valid := 0;']
    if publication.enabled(app):
        lines += [f'IF ({w}.LastInvalid = 0) OR S:FS THEN']+publication.begin(publication.view_revision(app))
    lines += [f'{v}.ValueCount := 0;',f'FOR {position} := 0 TO {capacity-1} DO',
              f'CPS({clean},{row}.ValueText,1);',f'{row}.Readable := 0;','END_FOR;']
    if publication.enabled(app):
        lines += publication.close(publication.view_revision(app))+[f'{w}.LastInvalid := 1;','END_IF;']
    lines += ['ELSE',
           f'IF ({w}.Initialized = 0) OR ({w}.LastRevision <> {source}.Revision)'+(f' OR ({w}.LastInvalid <> 0)' if publication.enabled(app) else '')+' THEN']
    if publication.enabled(app):lines += publication.begin(publication.view_revision(app))
    lines += [
           f'{v}.Revision := {source}.Revision;',f'{v}.ValueCount := 0;',f'{position} := 0;',
           f'FOR {index} := 0 TO {definitions-1} DO',f'{definition}.DefinitionIndex := {index};',
           *text.put_text(app,definition+'.Scope',app.name,255)]
    for name,_ in owner.TEXT_FIELDS:
        lines+=text.put(app,definition+'.'+name,f'{d}.{name}.Offset',f'{d}.{name}.Length')
    lines += [f'{definition}.{name}.LEN := 0;' for name in ('Unit','EnumDomain','EnumLabelKey')]
    lines += [f'{definition}.WriteRevision := {manifest.config_revision(app)};',f'{definition}.Writable := 1;',
              f'{definition}.HasMinimum := 1;',f'{definition}.HasMaximum := 1;']
    lines += [f'{definition}.{name} := {d}.{name};' for name in ('ConfigKind','ValueType','RequiresReady','Minimum','Maximum','UnitCode','ModelScoped','CanCapture')]
    lines += [f'{definition}.{name} := {levels}.{name}[{index}];' for name in ('ReadLevel','WriteLevel')] if app.access_users is not None else [f'{definition}.ReadLevel := -1;',f'{definition}.WriteLevel := -1;']

    def value(model_index):
        result=[f'{row}.DefinitionIndex := {index};',f'{row}.ModelOrdinal := {model_index};',
                f'{row}.Revision := {source}.Revision;',f'CPS({clean},{row}.ValueText,1);']
        result += [f'{row}.Readable := {levels}.Readable[{index}] <> 0;'] if app.access_users is not None else [f'{row}.Readable := 1;']
        if model_index=='0':result += [f'{row}.ModelCode.LEN := 0;',f'{w}.DataIndex := {d}.CacheIndex;']
        else:
            result += [f'CPS({app.name}.AvailableModels[{model}-1],{row}.ModelCode,1);',
                       f'{w}.DataIndex := {d}.ModelCache + ({model}-1)*{len(gen.model_cfg_members(app))};']
        result += [f'IF {row}.Readable THEN',f'CPS({clean},{source}.Render,1);',
                   f'{source}.Number := {source_cache};',f'JSR({owner.number_routine(app)},0);',
                   f'CPS({source}.Render,{row}.ValueText,1);','END_IF;',f'{position} := {position} + 1;']
        return result

    lines += value('0')+['END_FOR;']
    if (app.models or app.model_capacity) and any(r['ModelScoped'] for r in owner.def_rows(app)):
        lines += [f'FOR {model} := 1 TO {source}.LastCatalogCount DO',
                  f'FOR {index} := 0 TO {definitions-1} DO',f'IF {d}.ModelScoped THEN']+value(model)+['END_IF;','END_FOR;','END_FOR;']
    lines += [f'{v}.ValueCount := {position};',f'FOR {position} := {v}.ValueCount TO {capacity-1} DO',
              f'CPS({clean},{row}.ValueText,1);',f'{row}.Readable := 0;','END_FOR;',
              f'{w}.LastRevision := {source}.Revision;',f'{w}.Initialized := 1;']
    if publication.enabled(app):
        lines += [f'{w}.LastInvalid := 0;']+publication.close(publication.view_revision(app))
    lines += ['END_IF;','END_IF;']
    return lines
