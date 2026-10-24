"""Inventory S3h from immutable public values and authoritative owning declarations."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,sys,xml.etree.ElementTree as ET
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent;T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools'
CORE=ROOT/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core';AB=ROOT/'Specification/AllenBradley'
sys.path.insert(0,str(T))
import fraktal_ab_genealogy_s3g_demo as demo
import fraktal_ab_host_events as host
import fraktal_ab_genealogy as genealogy
app=demo.application();assert app.canonical_publication_stage==9
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=T/'fixtures/canonical/genealogy_projection_01.json.gz';raw=gzip.decompress(source.read_bytes());capture=json.loads(raw)
assert sha(raw)=='5ca907e6076a02833a5670ef3741cd62aca626f762f9dd557f1e4b9c2c3bbe0c'
prior_paths=set()
for filename in ('AB_CANONICAL_PUBLICATION_S3A_INVENTORY_2026-10-21.json','AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json',
    'AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json','AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json',
    'AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json','AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json','AB_CANONICAL_PUBLICATION_S3G_INVENTORY_2026-10-23.json'):
    inventory=json.loads((AB/filename).read_text());prior_paths.update(inventory['paths'])
assert len(prior_paths)==4010
declarations={};used=set()
for path in [*CORE.joinpath('DUTs').glob('*.TcDUT'),*CORE.joinpath('BaseClasses').glob('*.TcPOU')]:
    root=ET.parse(path).getroot();node=root.find('DUT')
    if node is None:node=root.find('POU')
    if node is None:continue
    text=re.sub(r'//[^\n]*','',node.findtext('Declaration'))
    members={m[1]:m[2].strip() for m in re.finditer(r'\b(\w+)\s*:\s*(ARRAY\s*\[[^\]]+\]\s*OF\s+\w+(?:\([^)]*\))?|\w+(?:\([^)]*\))?)\s*(?::=[^;]*)?;',text,re.I)}
    declarations[node.get('Name')]=(members,path)
roots=dict(Part='ST_PartContext',HostEvents='FB_HostEventPublisher',Nameplate='ST_Nameplate',SignalTower='ST_SignalTowerOut',MachineState='E_MachineState')
for name in ('Part','HostEvents','SignalTower','MachineState'):assert declarations['FB_UnitBase'][0][name]==roots[name]
assert declarations['FB_ModuleBase'][0]['Nameplate']=='ST_Nameplate'
primitive=dict(BOOL='Boolean',INT='Int16',DINT='Int32',UDINT='UInt32',UINT='UInt16',LINT='Int64',REAL='Float',LREAL='Double',DT='DateTime',LDT='DateTime',TIME='Int32')
ab_spec=ROOT/'Specification/Fraktal_AB_Part_III.md'
def resolve(path):
    parts=path.split('/')[1:];surface=re.sub(r'\[.*','',parts[0]);kind=roots[surface];owners=[]
    extension=False
    for index,part in enumerate(parts[1:],1):
        member=re.sub(r'\[.*','',part);members,owner=declarations[kind]
        used.add(owner);owners.append(owner)
        if member not in members:
            if surface=='Part' and index==1 and member in ('ParentCapacity','ParentCount'):
                kind='DINT';extension=True;owners += [ab_spec,T/'fraktal_ab_part.py',T/'fraktal_ab_genealogy.py']
            elif surface=='HostEvents' and index==1 and member in (set(host.META)-{'Count','Capacity','Wrapped'})|{'GenealogyCapacity'}:
                kind='DINT';extension=True;owners += [ab_spec,T/'fraktal_ab_host_events.py',T/'fraktal_ab_genealogy.py']
            elif surface=='HostEvents' and index==2 and member in ('ParentCount','Parents'):
                kind='STRING(64)' if member=='Parents' else 'DINT';extension=True
                owners += [ab_spec,T/'fraktal_ab_host_events.py',T/'fraktal_ab_genealogy.py']
            else:raise AssertionError((path,kind,member))
        else:kind=members[member]
        if kind.startswith('ARRAY'):kind=re.search(r'OF\s+(\w+(?:\([^)]*\))?)',kind)[1]
    target='String' if kind.startswith('STRING') else 'Int32' if kind.startswith('E_') else primitive[kind]
    return kind,target,extension,[p.relative_to(ROOT).as_posix() for p in dict.fromkeys(owners)]
def legacy_type(value):return 'Boolean' if type(value) is bool else 'String' if type(value) is str else 'Double' if type(value) is float else 'Int32' if type(value) is int else 'UNSUPPORTED'
paths={};counts=collections.Counter();changes=collections.Counter()
for path,value in sorted(capture['values'].items()):
    surface=re.sub(r'\[.*','',path.split('/')[1])
    if surface not in roots:continue
    assert path not in prior_paths,path
    kind,target,extension,owners=resolve(path);old=legacy_type(value)
    paths[path]=dict(value=value,legacyType=old,coreOrBindingDeclarationType=kind,proposedCoreType=target,
        bindingExtension=extension,ownerSources=owners,ownerApprovalRequired=old!=target)
    counts[surface]+=1
    if old!=target:changes[old+'->'+target]+=1
assert counts==dict(Part=40,HostEvents=220,Nameplate=10,SignalTower=7,MachineState=1),counts
assert changes=={'String->DateTime':17,'Int32->UInt32':16,'Int32->Int16':3},changes
assert len(paths)==278 and len(prior_paths|set(paths))==4288
sources={source,ab_spec,CORE/'Params/PL_Fraktal.TcGVL',CORE/'BaseClasses/FB_ModuleBase.TcPOU',CORE/'BaseClasses/FB_UnitBase.TcPOU',
    T/'fraktal_ab_projection.py',T/'fraktal_ab_host_events.py',T/'fraktal_ab_part.py',T/'fraktal_ab_genealogy.py',
    T/'fraktal_ab_signal_tower.py',T/'fraktal_ab_machine_state.py',*used}
result=dict(schema='fraktal.ab.s3h-surface-inventory',schemaVersion=1,date='2026-10-23',
    capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='owner-contract-review-required',
    controllerAccess=False,controllerWrites=0,productionSourceChanges=False,approvedAllowListChanged=False,
    priorLegacyPaths=4010,addedLegacyPaths=278,cumulativeLegacyPaths=4288,remainingLegacyPaths=len(capture['values'])-4288,
    surfaceCounts=dict(counts),proposedTypeChanges=sum(changes.values()),proposedTypeChangeCounts=dict(changes),
    canonicalPagePathForecast=[3672+278,3622+278,3272+278],
    declaredLogicalCapacities=dict(results=app.part_carrier.result_capacity,genealogy=genealogy.capacity(app),hostEvents=app.host_event_capacity),
    sourceProjectionExpandedSha256=sha(raw),paths=paths,
    sourceBindings={p.relative_to(ROOT).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(sources)},
    zeroTimestampFinding=dict(path=app.name+'/Part/Result/Stamp',legacyUnset='',proposedCanonicalUnset=0,
        populatedTimestampsRemainExact=True,insideEnumeratedTypePaths=True),
    notes=['No implementation or new exception is authorized by this inventory.',
        'Part genealogy fields and AB HostEvents delivery metadata retain existing binding semantics and types.',
        'The sparse host ring publishes only populated physical slots; its logical count comes from the PLC.',
        'Existing append, measurement, genealogy, UID, sequence/epoch and tower/classification owners remain authoritative.',
        'Four result rows, two parent slots and sixteen event slots are the existing consumed project bounds, not new D2 exceptions.'])
with (G/'inventory_02.json').open('x') as file:json.dump(result,file,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('paths','sourceBindings')}))
