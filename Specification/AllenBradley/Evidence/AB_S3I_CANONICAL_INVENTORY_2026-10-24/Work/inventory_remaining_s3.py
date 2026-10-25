"""Offline remaining-S3 census; source facts are read from frozen data and Core."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,subprocess,sys,xml.etree.ElementTree as ET

ROOT=Path('C:/Users/SoftIndVM/Fraktal');WORK=Path(__file__).parent
AB=ROOT/'Specification/AllenBradley';TOOLS=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
CORE=ROOT/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core'
sys.path.insert(0,str(TOOLS))
import fraktal_ab_canonical_equivalence as comparison
import fraktal_ab_canonical_reader as reader
import fraktal_ab_generate as generate
import fraktal_ab_projection as projection
import fraktal_ab_line as line

digest=lambda raw:hashlib.sha256(raw).hexdigest()
frozen_path=TOOLS/'fixtures/canonical/genealogy_projection_01.json.gz'
frozen_raw=gzip.decompress(frozen_path.read_bytes())
assert digest(frozen_raw)=='5ca907e6076a02833a5670ef3741cd62aca626f762f9dd557f1e4b9c2c3bbe0c'
frozen=json.loads(frozen_raw);assert len(frozen['values'])==4437
inventory_names=[f'AB_CANONICAL_PUBLICATION_{suffix}.json' for suffix in (
    'S3A_INVENTORY_2026-10-21','S3B_INVENTORY_2026-10-21','S3C_INVENTORY_2026-10-22',
    'S3D_INVENTORY_2026-10-22','S3E_INVENTORY_2026-10-22','S3F_INVENTORY_2026-10-22',
    'S3G_INVENTORY_2026-10-23','S3H_INVENTORY_2026-10-23')]
covered=set()
for name in inventory_names:covered.update(json.loads((AB/name).read_text())['paths'])
shifted=comparison.compare_documents(frozen,dict(values={}),require_types=False)['correctedPaths']
d2={row['projectionPath']:row['canonicalPath'] for row in shifted}
normalized={d2.get(path,path):path for path in frozen['values']}
assert len(normalized)==4437 and len(covered)==4288 and covered<=set(normalized)
remaining=sorted(set(normalized)-covered)
raw_missing=set(frozen['values'])-covered
false_missing=sorted(raw_missing-{normalized[path] for path in remaining})
assert len(remaining)==149 and len(raw_missing)==157 and len(false_missing)==8
assert all(d2[path] in covered for path in false_missing)

declarations={};used=set()
for path in sorted([*CORE.joinpath('DUTs').glob('*.TcDUT'),*CORE.joinpath('BaseClasses').glob('*.TcPOU')]):
    tree=ET.parse(path).getroot();node=tree.find('DUT')
    if node is None:node=tree.find('POU')
    if node is None:continue
    text=re.sub(r'//[^\n]*','',node.findtext('Declaration') or '')
    members={match[1]:match[2].strip() for match in re.finditer(
        r'\b(\w+)\s*:\s*(ARRAY\s*\[[^\]]+\]\s*OF\s+\w+(?:\([^)]*\))?|\w+(?:\([^)]*\))?)\s*(?::=[^;]*)?;',text,re.I)}
    declarations[node.get('Name')]=(members,path)
primitive=dict(BOOL='Boolean',INT='Int16',DINT='Int32',UDINT='UInt32',UINT='UInt16',LINT='Int64',
               REAL='Float',LREAL='Double',DT='DateTime',LDT='DateTime',TIME='Int32')
def logical(kind):return 'String' if kind.startswith('STRING') else 'Int32' if kind.startswith('E_') else primitive[kind]
def resolve(kind,parts):
    owners=[]
    for part in parts:
        members,path=declarations[kind];used.add(path);owners.append(path)
        kind=members[re.sub(r'\[.*','',part)]
        if kind.startswith('ARRAY'):kind=re.search(r'OF\s+(\w+(?:\([^)]*\))?)',kind)[1]
    return kind,[path.relative_to(ROOT).as_posix() for path in dict.fromkeys(owners)]
def legacy_type(value):
    return {bool:'Boolean',str:'String',float:'Double',int:'Int32',type(None):'Null'}.get(type(value),'UNSUPPORTED')
def canonical_stamp(value):
    if value is None or value=='':return 0
    instant=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    assert instant.tzinfo is not None
    delta=instant.astimezone(datetime.timezone.utc)-datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
    ns=(delta.days*86400+delta.seconds)*1_000_000_000+delta.microseconds*1000
    return reader.timestamp_ns(ns)

binding_types={'Line/AppliedRevision':'DINT','ShiftClosedSequence':'DINT','ShiftEndsAt':'DT',
               'ShiftTimeSynchronized':'BOOL','ShiftCalendarPending':'BOOL','Features/CaptureEnabled':'BOOL'}
rows={};groups=collections.Counter();type_changes=collections.Counter();renames=[]
for current in remaining:
    legacy=normalized[current];target=current
    if target.startswith('Press/HmiResponse/Report/Reasons/Reasons['):
        target=target.replace('/Report/Reasons/Reasons[','/Report/Reasons[',1)
    target=target.replace('/Line/OwnerId','/Line/Owner').replace('/Line/LastUpdatedAt','/Line/LastUpdate')
    relative=target.removeprefix('Press/');extension=relative in binding_types
    if extension:
        kind=binding_types[relative]
        owners=['Specification/HMI_CONTRACT.md','FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_line.py'] if relative!='Features/CaptureEnabled' else [
            'Specification/Fraktal_Core_Part_I.md','FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_projection.py']
    elif relative.startswith('Line/'):
        kind,owners=resolve('ST_LineStatus',relative.split('/')[1:])
    else:kind,owners=resolve('FB_UnitBase',relative.split('/'))
    value=frozen['values'][legacy];old=legacy_type(value);new=logical(kind)
    proposed=canonical_stamp(value) if new=='DateTime' else value
    group=('lineAndShift' if relative.startswith(('Line/','Shift')) or relative=='CurrentShift' else
           'mailboxAndReleaseReport' if relative.startswith(('HmiRequest/','HmiResponse/')) else
           'features' if relative.startswith('Features/') else 'production')
    stage='S3i' if group=='lineAndShift' else 'S3k'
    row=dict(legacyPath=legacy,inventoryPath=current,proposedCanonicalPath=target,legacyValue=value,
        legacyType=old,coreOrBindingDeclarationType=kind,proposedLogicalType=new,proposedFrozenValue=proposed,
        pathSpellingChange=target!=legacy,typeChange=old!=new,valueChange=type(value) is not type(proposed) or value!=proposed,
        bindingExtension=extension,group=group,stage=stage,ownerSources=owners)
    rows[legacy]=row;groups[group]+=1
    if old!=new:type_changes[old+'->'+new]+=1
    if target!=legacy:renames.append(dict(legacyPath=legacy,canonicalPath=target))
assert groups==dict(mailboxAndReleaseReport=126,lineAndShift=16,production=5,features=2),groups
assert sum(type_changes.values())==13 and len(renames)==122,(type_changes,len(renames))
assert len({row['proposedCanonicalPath'] for row in rows.values()})==149

additional={}
for leaf in ('TimeSynchronized','SourceError'):
    kind,owners=resolve('ST_LineStatus',[leaf])
    additional['Press/Line/'+leaf]=dict(coreType=kind,logicalType=logical(kind),ownerSources=owners,
        sourceRule=('Quality of the stored LastUpdate, sampled by the Line owner at commit; unknown historical quality stays false.' if leaf=='TimeSynchronized' else
                    'Existing declared local Line owner reports zero for a valid owner; unsupported mirror/source states are not fabricated as healthy.'))
request_members=declarations['ST_HmiRequest'][0]
assert len(request_members)==10
for leaf in request_members:
    if leaf=='Sequence':continue
    kind,owners=resolve('ST_HmiRequest',[leaf])
    additional['Press/HmiRequest/'+leaf]=dict(coreType=kind,logicalType=logical(kind),ownerSources=owners,
        valuePublication='command discovery/write surface only; excluded from cyclic snapshots and observation evidence',
        secret=leaf=='Secret')
assert len(additional)==11

history_members=declarations['ST_ShiftRecordV3'][0]
assert len(history_members)==21
history={};history_changes=collections.Counter();dependent=[]
for index in range(1,line.HISTORY+1):
    for leaf in history_members:
        kind,owners=resolve('ST_ShiftRecordV3',[leaf]);new=logical(kind)
        old=('absent' if leaf=='SchemaVersion' else 'StringOrNull' if kind in ('DT','LDT') else
             'Double' if kind in ('REAL','LREAL') else 'Boolean' if kind=='BOOL' else 'Int32')
        path=f'Press/ShiftHistory[{index}]/{leaf}'
        history[path]=dict(coreType=kind,logicalType=new,legacyProjectionType=old,ownerSources=owners,
            classification='additionalCoreField' if old=='absent' else 'typeCorrection' if old!=new else 'exact')
        if old not in ('absent',new):history_changes[old+'->'+new]+=1
        if leaf in ('AvailValid','PerfValid','QualValid','OeeValid'):dependent.append(path)
assert len(history)==168 and sum(history_changes.values())==112 and len(dependent)==32

params=CORE/'Params/PL_Fraktal.TcGVL';parameter_text=ET.parse(params).findtext('./GVL/Declaration')
release_max=int(re.search(r'MAX_RELEASE_REASONS\s*:\s*INT\s*:=\s*(\d+)',parameter_text)[1])
history_max=int(re.search(r'MAX_SHIFT_HISTORY\s*:\s*INT\s*:=\s*(\d+)',parameter_text)[1])
assert release_max==projection.REPORT_SLOTS==24 and history_max==line.HISTORY==8
assert generate.RELEASE_CAPACITY==8
sources={frozen_path,params,AB/'AB_FROZEN_CONTRACTS_V2.json',ROOT/'Specification/Fraktal_Core_Part_I.md',
    ROOT/'Specification/Fraktal_AB_Part_III.md',ROOT/'Specification/HMI_CONTRACT.md',
    ROOT/'FraktalCore/HMI/lib/data/opcua_repository.dart',
    TOOLS/'fraktal_ab_generate.py',TOOLS/'fraktal_ab_declaration.py',TOOLS/'fraktal_ab_mailbox.py',
    TOOLS/'fraktal_ab_line.py',TOOLS/'fraktal_ab_projection.py',TOOLS/'fraktal_ab_canonical_equivalence.py',
    TOOLS/'fraktal_ab_canonical_observation.py',TOOLS/'fraktal_ab_s3h_equivalence.py',
    AB/'Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24.md',
    *(AB/name for name in inventory_names),*used}
result=dict(schema='fraktal.ab.remaining-s3-contract-inventory',schemaVersion=1,date='2026-10-24',
    capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='owner-contract-review-required',
    controllerAccess=False,controllerWrites=0,productionSourceChanges=False,approvedAllowListChanged=False,
    repositoryHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    frozenLegacyPaths=4437,coveredAfterD2Normalization=4288,remainingPaths=149,rawUnmatchedKeys=157,
    d2FalseMissing=[dict(legacyPath=path,canonicalPath=d2[path],alreadyCovered=True) for path in false_missing],
    d2Rules=comparison.corrections(),groups=dict(groups),paths=rows,
    proposedFrozenPathRenames=renames,proposedFrozenTypeCorrections=sum(type_changes.values()),
    proposedFrozenTypeCorrectionCounts=dict(type_changes),
    frozenTimestampNormalizationPaths=[path for path,row in rows.items() if row['proposedLogicalType']=='DateTime'],
    additionalStaticCorePaths=additional,
    dynamicShiftHistory=dict(legacyFrozenRows=0,capacity=history_max,occupancySource='PLC ShiftHistoryCount',
        fieldsPerRow=21,oldFieldsPerRow=20,maximumPublishedPaths=168,paths=history,
        proposedTypeCorrectionCount=112,proposedTypeCorrectionCounts=dict(history_changes),
        additionalSchemaVersionPaths=[path for path in history if path.endswith('/SchemaVersion')],
        coreArithmeticDependentBooleanPaths=dependent,
        rule='Only occupied history rows appear. Preserve eight-row newest-first ownership, closing snapshots and targets. Core Float32 arithmetic and UInt32 bucket wrap are finite row-local amendments; no blanket coercion/tolerance.'),
    releaseReport=dict(coreCapacity=release_max,legacyOwnerCapacity=generate.RELEASE_CAPACITY,
        frozenPublishedCapacity=projection.REPORT_SLOTS,proposal='Versioned canonical-profile owner supports all 24 Core reasons; released V1 layouts stay unchanged. Publish all 24 slots and clear unused rows.',
        minimumReasonPayloadBytes=release_max*(2*255+2*4+1),
        byteEstimateQualification='Payload-only lower bound: omits string LEN/alignment, report headers, frame copy, other structures and compiled logic; not a Capacity estimate.'),
    declarationWidthFinding=dict(field='Line/LineId',legacyValidationCharacters=80,coreStringBytes=40,
        proposal='Canonical V2 generation enforces Core STRING(40) and rejects overflow; no truncation or in-place change to released legacy layouts.'),
    acceptanceScope=dict(genealogyFrozenPaths=True,pressDeclarationAllRenditionsStillRequired=True,
        fieldbusFrozenPaths=0,fieldbusSeparateDataProductStillRequired=True,observationFrameMigrationOnly=True,
        shippingCoherence='Per PLC-published row/group and read tier, Part III 3.13; no whole-document coherence requirement or observation-frame client dependency.',
        exactCapacityAndScanPerImageStillRequired=True,noRuntimeOperationAuthorized=True),
    frozenExpandedSha256=digest(frozen_raw),
    sourceBindings={path.relative_to(ROOT).as_posix():dict(bytes=path.stat().st_size,sha256=digest(path.read_bytes())) for path in sorted(sources)})
with (WORK/'inventory_01.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2);out.write('\n')
target=AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json'
with target.open('xb') as out:out.write((WORK/'inventory_01.json').read_bytes())
print(json.dumps({key:result[key] for key in ('frozenLegacyPaths','coveredAfterD2Normalization','remainingPaths','rawUnmatchedKeys',
    'groups','proposedFrozenTypeCorrections','proposedFrozenTypeCorrectionCounts')}))
print(json.dumps(dict(proposedPathRenames=len(renames),additionalStaticCorePaths=len(additional),dynamicHistoryPaths=len(history),
    dynamicTypeCorrections=112,dependentHistoryValidityFlags=32,legacyReleaseOwnerCapacity=8,proposedCoreCapacity=24)))
