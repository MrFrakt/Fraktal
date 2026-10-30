"""Append-only investigation seal; deliberately does not assert acceptance."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
O=R/'Specification/AllenBradley/Evidence/AB_S4B_READ_SCHEDULE_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
for label in ['locked_dependencies_01','full_hmi_01','analyze_01','windows_profile_01',
 'plc_transfer_01','configuration_stage_tests_01','root_02','ab_spec_02','ab_contracts_02',
 'consistency_02','whitespace_02','final_guard_01','final_inspect_01','final_preflight_01','header_probe_02']:
 assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert '+750 ~12: All tests passed!' in (W/'full_hmi_01.log').read_text(encoding='utf-8')
current=load(W/'restored_source_01.json')['sourceSha256'];assert len(current)==31
for name,pin in current.items():assert sha(H/name)==pin,name
probe=load(W/'header_probe_analysis_01.json');assert probe['samples']==87 and probe['attempts']==20
debug=load(W/'debug_01/result.json');assert not debug['passed'] and debug['genealogyBeforeAfterVerified']
assert load(W/'debug_01/sources.json')==current
transfer=load(W/'plc_transfer_01.json');assert transfer['passed'] and len(transfer['sourceSha256'])==373
for path,pin in transfer['sourceSha256'].items():assert sha(Path(path))==pin.lower(),path
folders=[('Serial',Path('C:/work/fraktal-ab-s4b-serial-20261029/offline_01')),
 ('Cadence',Path('C:/work/fraktal-ab-s4b-cadence-20261029/offline_01')),
 ('Structure',Path('C:/work/fraktal-ab-s4b-structure-20261029/offline_01')),
 ('Gap',Path('C:/work/fraktal-ab-s4b-gap-20261029/offline_01')),
 ('Split',Path('C:/work/fraktal-ab-s4b-split-20261029/offline_01')),
 ('Headers',Path('C:/work/fraktal-ab-s4b-headers-20261029/offline_01'))]
attempts=[]
for group,directory in folders:
 for path in sorted(directory.glob('profile_*/result.json')):
  value=load(path);assert value['controllerChanges']==0 and value['genealogyBeforeAfterVerified']
  assert not value['forcedPeerShutdown']
  attempts.append(dict(workspace=group,label=path.parent.name,passed=value['passed'],mapped=value['mappedSnapshots'],
   maximumMappedAgeUs=value['maxMappedEffectiveAgeUs']))
assert len(attempts)==13 and sum(a['passed'] for a in attempts)==4
with (W/'investigation_analysis_01.json').open('x') as f:json.dump(dict(profiles=attempts,
 finalSourceFiles=31,desktopPrerequisitePassed=False,currentConsecutiveProfilePasses=0,
 allExperimentsReverted=True,headerProbe=probe,fullHmiPassed=750,hmiSkipped=12,rootTestsPassed=74,
 controllerChanges=0,nativePreparationCreated=False,nativeAcceptanceClaim=False),f,indent=2)
O.mkdir();artifacts=[]
def copy(p,name):
 raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),**({'expandedSha256':expanded} if expanded else {})))
for group,directory in [('Work',W)]+folders:
 for p in sorted(directory.rglob('*')):
  if not p.is_file() or p.suffix.lower() not in {'.py','.ps1','.json','.jsonl','.log','.gz','.dart','.png','.csv','.sha256'}:continue
  if any(s in p.parts for s in ['__pycache__','bin','obj','.dart_tool','build']):continue
  if group=='Work' and p.name in ['seal_investigation_01.log','seal_investigation_01_exit.json']:continue
  assert not any(x in p.name.lower() for x in ['credential','password'])
  copy(p,group+'/'+p.relative_to(directory).as_posix())
bound={}
for p in [H/name for name in current]+[R/'Specification/AllenBradley'/name for name in [
 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md',
 'AB_CANONICAL_PUBLICATION_S4B_OWNER_REVISION_REVIEW_2026-10-29.md']]:
 relative=p.relative_to(R).as_posix();bound[relative]=sha(p);copy(p,'Current/'+relative)
value=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceSha256=bound,hmiSourceFiles=31,artifactCount=len(artifacts),artifacts=artifacts,
 offlineStaticGatesPassed=True,desktopPrerequisitePassed=False,profileAttempts=13,fullProfilePasses=4,
 allExperimentalChangesReverted=True,controllerChanges=0,nativeClaim=False,
 credentialFilesArchived=False,binaryOrAcdArchived=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(value,f,indent=2)
for entry in artifacts:
 p=O/entry['path'];assert sha(p)==entry['sha256'],p
 if 'expandedSha256' in entry:assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==entry['expandedSha256']
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),manifestSha256=sha(O/'artifact_manifest.json'),
 desktopPrerequisitePassed=False,controllerChanges=0)))
