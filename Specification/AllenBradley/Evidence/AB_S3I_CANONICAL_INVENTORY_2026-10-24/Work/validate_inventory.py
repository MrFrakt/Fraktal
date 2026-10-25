"""Independent set/finite-amendment/source checks for the remaining-S3 review."""
from pathlib import Path
import collections,gzip,hashlib,json,re,xml.etree.ElementTree as ET
R=Path(__file__).parent;ROOT=Path('C:/Users/SoftIndVM/Fraktal');AB=ROOT/'Specification/AllenBradley'
T=ROOT/'FraktalCore/PLC/Allen-Bradley/tools';CORE=ROOT/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((R/'inventory_01.json').read_text())
assert (R/'inventory_01.json').read_bytes()==(AB/'AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json').read_bytes()
f=json.loads(gzip.decompress((T/'fixtures/canonical/genealogy_projection_01.json.gz').read_bytes()))
rules=json.loads((AB/'AB_FROZEN_CONTRACTS_V2.json').read_text())['arrayBounds']['correctionsFromV1']
covered=set()
for prefix in ('S3A','S3B','S3C','S3D','S3E','S3F','S3G','S3H'):
    matches=list(AB.glob('AB_CANONICAL_PUBLICATION_'+prefix+'_INVENTORY_*.json'));assert len(matches)==1
    covered.update(json.loads(matches[0].read_text())['paths'])
def normalize(path):
    for rule in rules:
        base=rule['path'].replace('<Unit>','Press')
        match=re.match(re.escape(base)+r'\[(\d+)\](?=/|$)',path)
        if match:
            index=int(match[1])+rule['lowerBound']-rule['oldLowerBound']
            return path[:match.start(1)]+str(index)+path[match.end(1):]
    return path
expected={path for path in f['values'] if normalize(path) not in covered}
assert expected==set(d['paths']) and len(expected)==149
assert len(set(f['values'])-covered)==157
assert {row['legacyPath'] for row in d['d2FalseMissing']}==(set(f['values'])-covered)-expected
assert all(normalize(row['legacyPath'])==row['canonicalPath'] and row['canonicalPath'] in covered for row in d['d2FalseMissing'])
expected_renames={f'Press/HmiResponse/Report/Reasons/Reasons[{i}]/{leaf}':f'Press/HmiResponse/Report/Reasons[{i}]/{leaf}'
    for i in range(1,25) for leaf in ('Description','ReasonCode','SourcePath','Kind','Bypassable')}
expected_renames.update({'Press/Line/OwnerId':'Press/Line/Owner','Press/Line/LastUpdatedAt':'Press/Line/LastUpdate'})
assert {row['legacyPath']:row['canonicalPath'] for row in d['proposedFrozenPathRenames']}==expected_renames
expected_types={
    'Press/CurrentShift':'Int16','Press/HmiResponse/Report/Count':'Int16','Press/ShiftHistoryCount':'Int16',
    'Press/HmiRequest/Sequence':'UInt32','Press/HmiResponse/AckSequence':'UInt32','Press/GoodCount':'UInt32',
    'Press/NokCount':'UInt32','Press/ReworkCount':'UInt32','Press/Line/Revision':'UInt32','Press/ShiftProductionTarget':'UInt32',
    'Press/Line/LastUpdatedAt':'DateTime','Press/ShiftStartedAt':'DateTime','Press/ShiftEndsAt':'DateTime'}
assert {path:row['proposedLogicalType'] for path,row in d['paths'].items() if row['typeChange']}==expected_types
for path,row in d['paths'].items():
    assert row['legacyValue']==f['values'][path]
    assert row['proposedCanonicalPath']==expected_renames.get(path,path)
    if row['proposedLogicalType']!='DateTime':assert type(row['proposedFrozenValue']) is type(row['legacyValue']) and row['proposedFrozenValue']==row['legacyValue']
assert d['paths']['Press/ShiftEndsAt']['proposedFrozenValue']==0
assert d['paths']['Press/ShiftStartedAt']['proposedFrozenValue']=='1998-01-08T19:28:58.055Z'
assert d['paths']['Press/Line/LastUpdatedAt']['proposedFrozenValue']==f['values']['Press/Line/LastUpdatedAt']
assert set(d['additionalStaticCorePaths'])=={'Press/Line/TimeSynchronized','Press/Line/SourceError',*('Press/HmiRequest/'+name for name in ('Kind','TargetPath','NameValue','TextValue','User','Secret','IntValue','BoolValue','DurationMs'))}
assert all('excluded' in row['valuePublication'] for path,row in d['additionalStaticCorePaths'].items() if path.startswith('Press/HmiRequest/'))
history=d['dynamicShiftHistory'];assert history['capacity']==8 and len(history['paths'])==168
assert all(sum(path.startswith(f'Press/ShiftHistory[{i}]/') for path in history['paths'])==21 for i in range(1,9))
assert collections.Counter(row['classification'] for row in history['paths'].values())==dict(additionalCoreField=8,typeCorrection=112,exact=48)
assert len(history['coreArithmeticDependentBooleanPaths'])==32
assert history['proposedTypeCorrectionCounts']=={'Int32->UInt32':56,'Int32->Int16':8,'StringOrNull->DateTime':16,'Double->Float':32}
core_members=ET.parse(CORE/'DUTs/ST_HmiRequest.TcDUT').findtext('./DUT/Declaration')
assert len(re.findall(r'^\s+\w+\s*:',core_members,re.M))==10
for name,bound in d['sourceBindings'].items():assert (ROOT/name).stat().st_size==bound['bytes'] and sha(ROOT/name)==bound['sha256'],name
accepted=AB/'Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24'
pins=json.loads((accepted/'Runtime/initial_source_verification.json').read_text())
assert pins['sourceBindings']==162
for name,pin in pins['sha256'].items():assert sha(ROOT/name)==pin.lower(),name
capacity=json.loads((accepted/'Session/capacity_review.json').read_text())
assert capacity['Measured'] and capacity['VerifiedFit'] and capacity['Provider']=='StudioUIAutomation'
assert (capacity['UsedStandardBlocks'],capacity['AvailableBlocks'],capacity['TotalBlocks'])==(2680132,465596,3145728)
result=dict(passed=True,controllerAccess=False,controllerWrites=0,productionSourceChanges=False,
    inventoryPaths=149,rawUnmatchedPaths=157,d2EndpointsAlreadyCovered=8,finiteRenames=122,finiteFrozenTypeCorrections=13,
    additionalStaticCoreCommandAndStatusPaths=11,possibleShiftHistoryPaths=168,dynamicShiftTypeCorrections=112,
    dynamicShiftDependentBooleanValues=32,acceptedSourceBindingsUnchanged=162,
    capacityImageSha256=capacity['CanonicalSha256'],capacityBlocks=dict(used=2680132,available=465596,total=3145728),
    approvedV2Unchanged=True,implementationStillRefused=True)
with (R/'validation_01.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
