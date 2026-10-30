"""Seal a collector-only correction; transfer unchanged PLC/HMI proofs by hashes."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
E=R/'Specification/AllenBradley/Evidence';BASE=E/'AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29'
O=E/'AB_S4B_OWNER_REVISION_COLLECTOR_CORRECTION_2026-10-29';report=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
for name in ['ab_suite_03','collector_seam_tests_01','root_04','ab_spec_04','ab_contracts_04','consistency_04',
             'collector_whitespace_01','collector_guard_01','collector_preflight_01']:
 assert load(W/(name+'_exit.json'))['exitCode']==0,name
assert b'Ran 2356 tests' in (W/'ab_suite_03.log').read_bytes()
old=load(BASE/'artifact_manifest.json');profiles=load(W/'three_profiles_01.json')
assert old['offlineGatesPassed'] and profiles['passed']
for name,pin in profiles['sourceSha256'].items():assert sha(H/name)==pin,name
allowed={
 'FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py',
 'FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_owner_read_fixture.py',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md',
 'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json'}
changed={p for p,pin in old['sourceSha256'].items() if sha(R/p)!=pin}
assert changed<=allowed and len(changed)==5,changed
for p,pin in old['sourceSha256'].items():
 if p not in allowed:assert sha(R/p)==pin,p
assert sha(W/'canonical_owner_01.ACD').upper()=='84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC'
assert sha(W/'canonical_owner_01.L5X').upper()=='22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06'
assert load(W/'collector_regression_replay_01.json')['oldCollectorReproducesNativeRefusal']
O.mkdir();artifacts=[]
def copy(p,name):
 raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
  **({'expandedSha256':expanded} if expanded else {})))
for pattern in ['ab_suite_03*','collector*','run_root_gates_04.py','root_04*','ab_spec_04*','ab_contracts_04*','consistency_04*','seal_collector_correction_01.py']:
 for p in sorted(W.glob(pattern)):
  if p.is_file():copy(p,'Work/'+p.name)
bound={}
for relative in old['sourceSha256']:
 p=R/relative;bound[relative]=sha(p);copy(p,'Current/'+relative)
transfer=dict(passed=True,changedFiles=sorted(changed),hmiProofPins=35,retainedHmiPassed=759,hmiSkipped=12,
 retainedBothV38BuildReadbacks=True,retainedCapacityPercent=66,imageUnchanged=True,
 retainedThreeProfiles=True,retainedObserverPeerSamples=100,retainedConfigurationScalars=1100,
 baselineManifestSha256=sha(BASE/'artifact_manifest.json'))
with (O/'transfer.json').open('x') as f:json.dump(transfer,f,indent=2)
copy(O/'transfer.json','Proof/transfer.json')
m=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceSha256=bound,artifactCount=len(artifacts),artifacts=artifacts,
 offlineGatesPassed=True,desktopPrerequisitePassed=True,observerPeerPassed=True,
 abTests=2356,hmiPassed=759,hmiSkipped=12,rootTests=74,controllerChanges=0,
 nativeAccepted=False,credentialsArchived=False,binariesOrAcdArchived=False,transfer=transfer)
with (O/'artifact_manifest.json').open('x') as f:json.dump(m,f,indent=2)
for a in artifacts:assert sha(O/a['path'])==a['sha256']
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),sourceFiles=len(bound),manifestSha256=sha(O/'artifact_manifest.json'))))
