"""Seal startup read-schedule qualification and independent E4, including failures."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
O=R/'Specification/AllenBradley/Evidence/AB_S4B_READ_SCHEDULE_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
labels=['locked_dependencies_01','full_hmi_02','analyze_02','windows_profile_01','plc_transfer_01',
 'configuration_stage_tests_01','peer_qualification_01','verify_rehearsals_01','root_01',
 'ab_spec_01','ab_contracts_01','consistency_01','whitespace_01']
for label in labels:assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert '+750 ~12: All tests passed!' in (W/'full_hmi_02.log').read_text(encoding='utf-8')
proof=load(W/'rehearsal_analysis_01.json');assert proof['prerequisitePassed'] and proof['consecutiveQualifyingProfiles']==3
sources=proof['sourceSha256'];assert len(sources)==31
for name,pin in sources.items():assert sha(H/name)==pin,name
peer=load(W/'observer_peer_qualification_01.json');assert peer['passed'] and peer['samples']==100 and peer['badSamples']==0
config=load(W/'configuration_peer_comparison_01.json');assert config['passed'] and config['scalarComparisons']==1100
transfer=load(W/'plc_transfer_01.json');assert transfer['passed'] and len(transfer['sourceSha256'])==373
for path,pin in transfer['sourceSha256'].items():assert sha(Path(path))==pin.lower(),path
O.mkdir();artifacts=[]
def copy(p,name):
 raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 dest=O/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),**({'expandedSha256':expanded} if expanded else {})))
for p in sorted(W.rglob('*')):
 if not p.is_file() or p.suffix.lower() not in {'.py','.ps1','.json','.jsonl','.log','.gz','.dart','.png','.csv'}:continue
 if any(s in p.parts for s in ['__pycache__','bin','obj','.dart_tool','build']):continue
 if p.name in {'seal_qualification_01.log','seal_qualification_01_exit.json'}:continue
 assert not any(x in p.name.lower() for x in ['credential','password'])
 copy(p,'Work/'+p.relative_to(W).as_posix())
current={}
for path in [H/name for name in sources]+[R/'Specification/AllenBradley'/name for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md']]:
 relative=path.relative_to(R).as_posix();current[relative]=sha(path);copy(path,'Current/'+relative)
value=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceSha256=current,hmiSourceFiles=len(sources),artifactCount=len(artifacts),artifacts=artifacts,
 desktopPrerequisitePassed=True,consecutiveQualifyingProfiles=3,newObserverRehearsalPassed=True,
 independentConfigurationScalars=1100,controllerChanges=0,nativeClaim=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(value,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),hmiSourceFiles=len(sources),manifestSha256=sha(O/'artifact_manifest.json'))))
