"""Reuse only exact-source desktop proof; new observer-only inputs stay separate."""
from pathlib import Path
import gzip,hashlib,json,subprocess
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
C=R/'Specification/AllenBradley/Evidence/AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((C/'artifact_manifest.json').read_bytes())
for entry in manifest['artifacts']:
    path=C/entry['path'];assert sha(path)==entry['sha256'],path
    if 'expandedSha256' in entry:assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==entry['expandedSha256']
proof=json.loads((C/'Work/rehearsal_analysis_01.json').read_bytes())
assert proof['prerequisitePassed'] and proof['consecutiveQualifyingProfiles']==3 and proof['sourceFiles']==27
for path,pin in proof['sourceSha256'].items():assert sha(H/path)==pin,path
assert all(row['passed'] and row['shots']==31 and row['maxMappedEffectiveAgeUs']<=700000 for row in proof['runs'][:3])
changed=subprocess.check_output(['git','diff','--name-only','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
unbound={Path(p).relative_to('FraktalCore/HMI').as_posix() for p in changed}.difference(proof['sourceSha256'])
assert unbound=={'tool/qualify_cip_canonical.dart','test/cip_qualification_test.dart'},unbound
# Neither new observer input is imported by the desktop graph. The integration
# entry references only its UI/font helper and product libraries, unchanged.
for folder in ['lib','packages/fraktal_opcua_client/lib','integration_test','test_driver','tool/screenshots']:
    for p in (H/folder).rglob('*.dart'):
        assert 'qualify_cip_canonical.dart' not in p.read_text(encoding='utf-8'),p
result=dict(passed=True,desktopSourceUnchanged=True,sourceFiles=27,sourceSha256=proof['sourceSha256'],
    reusedConsecutiveProfiles=3,debugComparisonRetained=True,reference=str(C/'artifact_manifest.json'),
    referenceSha256=sha(C/'artifact_manifest.json'),newObserverOnlyInputs=sorted(unbound),
    newObserverQualificationRequired=True,experimentalProfilesSuperseded=True,nativeClaim=False)
with (W/'desktop_prerequisite_transfer_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='sourceSha256'}))
