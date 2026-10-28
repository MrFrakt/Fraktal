"""Read-only verification and SDK log audits for the incomplete S3k image."""
from pathlib import Path
import datetime,gzip,hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal'); E=R/'Specification/AllenBradley/Evidence'; W=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
from fraktal_ab_sdk_log_gate import audit_log
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(name,value):
    with (W/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
for target in ('EchoController','PhysicalController'):
    p=W/f'native_{target}_02.log'
    report=audit_log(p.read_text(),('Open project','Build','Save As'),True)
    save(f'sdk_{target}_02.json',report)
    assert report['Clean'],report
report=audit_log((W/'prepare_acd_01.log').read_text(),('Open project','Build','Save As','Save'),True)
save('sdk_prepare_01.json',report);assert report['Clean'],report
latest=E/'AB_S3J_CANONICAL_RUNTIME_2026-10-25/manifest.json'
previous=json.loads(latest.read_bytes())
names={row['name'] for row in previous['priorSeals']}|{latest.parent.name}
rows=[]; total=0
for name in sorted(names):
    p=E/name/'manifest.json'; m=json.loads(p.read_bytes())
    for a in m['artifacts']:
        raw=(p.parent/a['path']).read_bytes()
        assert len(raw)==a['bytes'] and sha(raw)==a['sha256'].lower(),(name,a['path'])
        if a.get('expandedSha256'):assert sha(gzip.decompress(raw))==a['expandedSha256'].lower()
    if m.get('report') and m.get('reportSha256'):assert sha((E/m['report']).read_bytes())==m['reportSha256'].lower()
    total+=len(m['artifacts']);rows.append(dict(name=name,manifestSha256=sha(p.read_bytes()),artifacts=len(m['artifacts'])))
save('prior_seals_01.json',dict(passed=True,records=len(rows),artifacts=total,rows=rows))
pins={'s3k_read_surface_02.L5X':'ADA479ACA4305DD07E512ABDDC16446E9FDB220562A641FC0E6F026C201FD515',
 'read_surface_01.ACD':'CB180CDD8F6ED31380C3D288B13FA746313BC8A5E1F1677CBF3630FEAF6F0ED6',
 'read_surface_capacity_review.ACD':'CB180CDD8F6ED31380C3D288B13FA746313BC8A5E1F1677CBF3630FEAF6F0ED6'}
for name,pin in pins.items():assert sha((W/name).read_bytes()).upper()==pin
v=json.loads((W/'capacity_auto_01.json').read_bytes())
assert v['SourceUnchanged'] and v['VerifiedFit'] and v['UsedStandardBlocks']==1807120
assert v['AvailableBlocks']+v['UsedStandardBlocks']==v['TotalBlocks']==3145728
assert sha((W/'capacity_capture_01.json').read_bytes())==v['CaptureSha256']
tests=json.loads((W/'ab_suite_02_exit.json').read_bytes())
assert tests['exitCode']==0
end=datetime.datetime.fromisoformat(tests['endUtc']).timestamp()
code=list((R/'FraktalCore/PLC/Allen-Bradley/tools').glob('*.py'))
modified_after=[p.name for p in code if p.stat().st_mtime>end]
assert not modified_after,modified_after
save('final_provenance_01.json',dict(passed=True,priorSeals=len(rows),priorArtifacts=total,
 pins=pins,sdkAudits=3,abSourceFiles=len(code),abSourceModifiedAfterFinalSuite=modified_after,
 usedBlocks=1807120,availableBlocks=1338608,totalBlocks=3145728,displayedPercent=57,
 controllerOperations=0,nativeAccepted=False))
print(json.dumps(dict(passed=True,priorSeals=len(rows),priorArtifacts=total,pins=len(pins),sdkAudits=3,abSourceFiles=len(code))))
