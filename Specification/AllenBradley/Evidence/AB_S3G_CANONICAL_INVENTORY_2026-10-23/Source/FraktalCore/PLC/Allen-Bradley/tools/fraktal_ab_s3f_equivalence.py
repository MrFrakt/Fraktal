"""Approved S3f reference contract. Station facts stay in this test oracle only.

The frozen oracle remains unchanged. This reference independently pages its
ordered configuration walk and explicitly types the approved corrected fields.
Opaque PLC revision tokens are compared with the owning query acknowledgement;
causal changes/restart are separate required fixture/model checks.
"""
from functools import partial
import fraktal_ab_s3e_equivalence as previous
import fraktal_ab_s2_equivalence as shared

PAGE_SIZE=16
ENTRY_FIELDS=('Scope','Item','ValueText','WriteKey','WriteRevision','ConfigKind','ValueType','Writable',
    'RequiresReady','HasMinimum','HasMaximum','Minimum','Maximum','Unit','LabelKey','EnumDomain','UnitCode',
    'EnumLabelKey','ClassId','ReadLevel','WriteLevel','Readable','ModelScoped','CaptureSource','CanCapture')
PERSIST_FIELDS=('Pending','Failed','WindowMs','PendingSince','StorePresent','StoreKind','RestoreLost',
    'RestoreAcknowledged','LostPath','RestorePolicy','LastSetName','LastSetRecords','LastRejectScope','LastRejectKey')
SET_FIELDS=('Used','SetName','RootIdentity','SetSchema','ConfigRev','Kind','ModelCode','RecordCount','CreatedAt','TimeSynchronized')


def entry_count(app,page,model,codes):
    import fraktal_ab_generate as gen
    if type(page) is not int or not 0<=page<=32767 or type(model) is not int or not 0<=model<=len(codes):
        return 0
    return max(0,min(PAGE_SIZE,len(gen.editable_values(app))-page*PAGE_SIZE))


def subset_paths(app,codes,*,canonical,page=0,model=0):
    paths=previous.subset_paths(app,codes,canonical=canonical);root=app.name+'/'
    paths.update(root+'ConfigPersist/'+n for n in PERSIST_FIELDS)
    paths.update(root+name for name in ('Status/ConfigRev','ConfigSetCount','ConfigSetDocument','ConfigSetDocumentLine','ConfigSetDocumentLines'))
    paths.update(root+f'ConfigSets[{i}]/'+n for i in range(1,5) for n in SET_FIELDS)
    paths.update(root+'HmiResponse/ConfigPage/'+n for n in ('Revision','PageIndex','PageCount','EntryCount'))
    paths.update(root+f'HmiResponse/ConfigPage/Entries[{i}]/'+n
                 for i in range(1,entry_count(app,page,model,codes)+1) for n in ENTRY_FIELDS)
    return paths


def additional_inputs(reader):
    import fraktal_ab_projection as projection
    import fraktal_ab_press_execute as execute
    import fraktal_ab_declaration as decl
    import fraktal_ab_data_access as data
    import fraktal_ab_sets as sets
    result=previous.additional_inputs(reader)
    import fraktal_ab_models as catalog
    codes=catalog.read(reader,projection.APP)
    result.update(persist=projection.read_persist(reader),models=projection.read_models(reader,len(codes)),
        levels=projection.read_data_access(reader),sets=execute.read_layout(reader,sets.state_tag(projection.APP),sets.state_members(projection.APP)))
    # This is the owning query service's independent native acknowledgement,
    # never a sample copied out of the generic canonical document.
    names=('SchemaVersion','AckSequence','Accepted','PageIndex','ModelIndex','Revision')
    result['query']=execute.read_layout(reader,f'FRK_{projection.APP.name}_ConfigQueryStatus',tuple(decl.scalar(n) for n in names))
    if any(result[n] is None for n in ('persist','models','levels','sets','query')):
        raise ValueError('S3f owner read failed')
    return result


def reference_config(app,additional,*,page=0,model=0,provider_state=None):
    import datetime
    import fraktal_ab_projection as projection
    import fraktal_ab_manifest as manifest
    import fraktal_ab_sets as sets
    state=provider_state or {};q=additional['query'];s=additional['sets'];root=app.name+'/'
    if (q['SchemaVersion'],q['PageIndex'],q['ModelIndex'],q['Accepted'])!=(1,page,model,1) or not 1<=q['Revision']<=2147483646:
        raise ValueError('query acknowledgement does not match expected page/model')
    full=projection.config_page(app,manifest.content(app),additional['records'],additional['models'],model,additional['levels'])
    count=full['HmiResponse/ConfigPage/EntryCount'];selected=[]
    for i in range(page*PAGE_SIZE+1,min((page+1)*PAGE_SIZE,count)+1):
        prefix=f'HmiResponse/ConfigPage/Entries[{i}]/'
        row={p[len(prefix):]:value for p,value in full.items() if p.startswith(prefix)}
        if set(row)!=set(ENTRY_FIELDS):raise ValueError('reference configuration entry incomplete')
        # The two enumerated Core LREAL fields alone change Python value kind.
        for name in ('Minimum','Maximum'):
            if type(row[name]) is not int:raise ValueError('legacy configuration bounds must be exact DINT integers')
            row[name]=float(row[name])
        selected.append(row)
    out={'Status/ConfigRev':q['Revision'],'HmiResponse/ConfigPage/Revision':q['Revision'],
        'HmiResponse/ConfigPage/PageIndex':page,'HmiResponse/ConfigPage/PageCount':(count+PAGE_SIZE-1)//PAGE_SIZE,
        'HmiResponse/ConfigPage/EntryCount':len(selected)}
    for i,row in enumerate(selected,1):out.update({f'HmiResponse/ConfigPage/Entries[{i}]/{k}':v for k,v in row.items()})
    out.update(projection.config_persist_status(app,additional['persist']))
    # The old scalar has only time-of-day. The set owner's audit captures the
    # operation date/clock together. A saved reference may carry that exact
    # operation stamp after a long export has wrapped the bounded audit ring.
    stamp=0;pending=additional['persist']['PendingSince']
    if pending:
        seq=s['PendingSequence'];found=None
        for i in range(sets.AUDIT_CAPACITY):
            if s['AuditSequence'][i]==seq:found=(s['AuditDate'][i],s['AuditClock'][i])
        if found is None and state.get('pendingSequence')==seq:found=(state['pendingDate'],state['pendingClock'])
        if found is None or found[1]!=pending:raise ValueError('absolute pending timestamp lacks independent operation date')
        stamp=projection._controller_time(*found)
    out['ConfigPersist/PendingSince']=stamp
    head=s['Head']-1
    name='';records=0
    if 0<=head<sets.AUDIT_CAPACITY:
        length=s['AuditNameLength'][head];raw=s['AuditNameBytes'][head*80:head*80+max(0,min(length,80))]
        if 0<=length<=80 and all(1<=b<=127 for b in raw):name=bytes(raw).decode('ascii')
        records=s['Count'] if 0<=s['Count']<=sets.MAX_RECORDS else 0
    out.update({'ConfigPersist/LastSetName':name,'ConfigPersist/LastSetRecords':records,
        'ConfigPersist/LastRejectScope':state.get('rejectScope',''),'ConfigPersist/LastRejectKey':state.get('rejectKey',''),
        'ConfigSetDocument':state.get('document',''),'ConfigSetDocumentLine':state.get('documentLine',0),
        'ConfigSetDocumentLines':state.get('documentLines',0)})
    headers=state.get('headers',[]);out['ConfigSetCount']=len(headers)
    for i in range(1,5):
        header=headers[i-1] if i<=len(headers) else None
        row=dict(Used=header is not None,SetName='',RootIdentity='',SetSchema=0,ConfigRev=0,Kind=0,ModelCode='',
            RecordCount=0,CreatedAt=0,TimeSynchronized=False)
        if header:
            row.update({target:header[source] for target,source in (('SetName','set'),('RootIdentity','root'),('SetSchema','schema'),
                ('ConfigRev','configRev'),('Kind','kind'),('ModelCode','model'),('RecordCount','records'))})
            row['TimeSynchronized']=bool(header['clock'])
            if header['created']:
                row['CreatedAt']=(datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=header['created'])).isoformat(timespec='milliseconds').replace('+00:00','Z')
        out.update({f'ConfigSets[{i}]/{k}':v for k,v in row.items()})
    return {root+p:v for p,v in out.items()}


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    return {**previous.extra_values(app,unit,additional),
        **reference_config(app,additional,page=page,model=model,provider_state=provider_state)}


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    for p in paths:
        leaf=p.rsplit('/',1)[-1]
        if '/HmiResponse/ConfigPage/Entries[' in p:
            if leaf in ('Minimum','Maximum'):result[p]='Double'
            elif leaf=='WriteRevision':result[p]='UInt32'
        elif '/HmiResponse/ConfigPage/' in p:result[p]='UInt32' if leaf=='Revision' else 'Int16'
        elif '/ConfigSets[' in p:
            if leaf=='SetSchema':result[p]='UInt16'
            elif leaf=='ConfigRev':result[p]='UInt32'
            elif leaf=='RecordCount':result[p]='Int16'
            elif leaf=='CreatedAt':result[p]='DateTime'
        elif p.endswith('/Status/ConfigRev') or p.endswith('/ConfigPersist/WindowMs'):result[p]='UInt32'
        elif p.endswith(('/ConfigSetCount','/ConfigSetDocumentLine','/ConfigSetDocumentLines','/ConfigPersist/LastSetRecords')):result[p]='Int16'
        elif p.endswith('/ConfigPersist/PendingSince'):result[p]='DateTime'
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s3f_demo as candidate
    return shared.run(comm,application_factory=candidate.application,
        path_contract=partial(subset_paths,page=page,model=model),
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),
        logical_types=logical_types,additional_inputs=additional_inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
