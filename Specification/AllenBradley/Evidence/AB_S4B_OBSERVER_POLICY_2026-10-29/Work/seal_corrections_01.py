"""Seal final observer-only corrections and all reverted/failed experiments."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
O=R/'Specification/AllenBradley/Evidence/AB_S4B_OBSERVER_POLICY_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
labels=['locked_dependencies_01','full_hmi_03','analyze_03','windows_profile_03','root_02','ab_spec_01','ab_contracts_01',
        'consistency_01','whitespace_01','plc_transfer_01','workflow_02','cpu_churn_02','cpu_actual_01','desktop_transfer_01','observer_peer_02']
assert all(load(W/(name+'_exit.json'))['exitCode']==0 for name in labels)
assert '+743 ~12: All tests passed!' in (W/'full_hmi_03.log').read_text(encoding='utf-8')
desktop=load(W/'desktop_prerequisite_transfer_01.json');assert desktop['passed'] and desktop['reusedConsecutiveProfiles']==3
observer=load(W/'observer_peer_qualification_01.json');assert observer['passed'] and observer['samples']==100 and observer['badSamples']==0
sources={**desktop['sourceSha256'],**observer['sourceSha256']};assert len(sources)==29
for path,pin in sources.items():assert sha(H/path)==pin,path
assert load(W/'adaptive_experiment_reverted_01.json')['reverted']
O.mkdir();artifacts=[]
def copy(p,name):
    raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
    dest=O/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        **({'expandedSha256':expanded} if expanded else {})))
for p in sorted(W.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in {'.py','.ps1','.json','.jsonl','.log','.gz','.dart','.png','.csv'}:continue
    if any(s in p.parts for s in ['__pycache__','bin','obj','.dart_tool','build']):continue
    if p.name in {'seal_corrections_01.log','seal_corrections_01_exit.json'}:continue
    assert not any(x in p.name.lower() for x in ['credential','password'])
    copy(p,'Work/'+p.relative_to(W).as_posix())
current={}
for path in [H/name for name in sources]+[R/'Specification/AllenBradley'/name for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md']]:
    relative=path.relative_to(R).as_posix();current[relative]=sha(path);copy(path,'Current/'+relative)
value=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceSha256=current,hmiSourceFiles=29,artifactCount=len(artifacts),artifacts=artifacts,
    desktopPrerequisiteTransferredByExactSources=True,newObserverRehearsalPassed=True,controllerChanges=0,nativeClaim=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(value,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),hmiSourceFiles=29,manifestSha256=sha(O/'artifact_manifest.json'))))
