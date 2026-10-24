"""Independent finite-path/type checks and unchanged S3g/predecessor bindings."""
from pathlib import Path
from dataclasses import replace
import datetime,gzip,hashlib,json,re,sys
ROOT=Path('C:/Users/SoftIndVM/Fraktal');G=Path(__file__).parent;AB=ROOT/'Specification/AllenBradley';E=AB/'Evidence'
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_genealogy_s3g_demo as demo
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_reader as reader
sha=lambda raw:hashlib.sha256(raw).hexdigest()
inventory=json.loads((G/'inventory_02.json').read_text())
assert sha((G/'inventory_02.json').read_bytes())==sha((AB/'AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json').read_bytes())
values=json.loads(gzip.decompress((T/'fixtures/canonical/genealogy_projection_01.json.gz').read_bytes()))['values']
selected={p:v for p,v in values.items() if p.split('/')[1] in ('Part','Nameplate','SignalTower','MachineState','HostEvents')}
assert set(selected)==set(inventory['paths']) and len(selected)==278
assert all(inventory['paths'][p]['value']==v for p,v in selected.items())
expected={f'Press/HostEvents/Ring[{i}]/Sequence':'UInt32' for i in range(1,17)}
expected.update({f'Press/HostEvents/{n}':'Int16' for n in ('Count','Capacity','RingHead')})
expected.update({f'Press/HostEvents/Ring[{i}]/Stamp':'DateTime' for i in range(1,17)})
expected['Press/Part/Result/Stamp']='DateTime'
actual={p:row['proposedCoreType'] for p,row in inventory['paths'].items() if row['legacyType']!=row['proposedCoreType']}
assert actual==expected and len(actual)==36
assert all(not row['ownerApprovalRequired'] and row['legacyType']==row['proposedCoreType'] for row in inventory['paths'].values() if row['bindingExtension'])
for path,row in inventory['paths'].items():
    if '/Result/Records[' in path and path.rsplit('/',1)[-1] in ('Value','Minimum','Maximum','Target'):
        assert row['legacyType']==row['proposedCoreType']=='Double'
assert len([p for p in inventory['paths'] if '/Result/Records[' in p])==28
assert reader.timestamp_ns(0)==0 and inventory['zeroTimestampFinding']['legacyUnset']==''
for path in expected:
    if path.endswith('/Stamp'):
        stamp=selected[path];assert stamp.endswith('Z')
        value=datetime.datetime.fromisoformat(stamp.replace('Z','+00:00'))
        epoch=datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc);delta=value-epoch
        nanos=(delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000
        assert reader.timestamp_ns(nanos)==stamp
for name,bound in inventory['sourceBindings'].items():assert sha((ROOT/name).read_bytes())==bound['sha256'],name
v2=json.loads((AB/'AB_FROZEN_CONTRACTS_V2.json').read_text());assert not v2['active'] and v2['approvedMetricsCorrection']['runtimeAccepted']
assert pub.validate(replace(demo.application(),canonical_publication_stage=10))
current=json.loads((E/'AB_S3G_CANONICAL_RUNTIME_2026-10-23/Runtime/source_verification_01.json').read_text())
assert current['sourceBindings']==151
for name,pin in current['sha256'].items():assert sha((ROOT/name).read_bytes())==pin,name
seals=[]
for path in sorted(E.glob('AB_*/manifest.json')):
    if not any(n in path.parent.name for n in ('AB_S0_CANONICAL','AB_S0_SUPPLEMENTARY','AB_S1_CANONICAL','AB_S2_CANONICAL','AB_S3A_CANONICAL','AB_S3B_CANONICAL','AB_S3C_CANONICAL','AB_S3D_CANONICAL','AB_S3E_CANONICAL','AB_S3F_CANONICAL','AB_S3G_CANONICAL')):continue
    m=json.loads(path.read_text())
    for item in m['artifacts']:
        raw=(path.parent/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256'].lower()
        if item.get('expandedSha256'):assert sha(gzip.decompress(raw))==item['expandedSha256'].lower()
    if m.get('report'):assert sha((E/m['report']).read_bytes())==m['reportSha256'].lower()
    seals.append(dict(name=path.parent.name,artifacts=len(m['artifacts']),manifestSha256=sha(path.read_bytes())))
assert len(seals)==26 and sum(row['artifacts'] for row in seals)==6059
report=dict(passed=True,capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllerAccess=False,controllerWrites=0,
    productionSourceChanges=False,acceptanceRulesChanged=False,paths=278,typeCorrectionsProposed=36,otherPathsExact=242,
    proposedCounts={'Int32->UInt32':16,'Int32->Int16':3,'String->DateTime':17},unsetTimestampPaths=1,
    declaredLogicalCapacities=inventory['declaredLogicalCapacities'],currentAbSourceBindings=151,currentAbSources=current['sha256'],
    sourceBindings=inventory['sourceBindings'],priorSeals=seals,predecessorRecords=26,predecessorArtifacts=6059,
    implementationStillRefused=True,failedInventoryRunRetained=True)
with (G/'validation_01.json').open('x') as file:json.dump(report,file,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('currentAbSources','sourceBindings','priorSeals')}))
