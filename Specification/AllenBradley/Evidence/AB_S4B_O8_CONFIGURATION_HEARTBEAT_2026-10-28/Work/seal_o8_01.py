"""Seal approved O8 offline qualification; no controller I/O."""
from pathlib import Path
import datetime,gzip,hashlib,json
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
E=R/'Specification/AllenBradley/Evidence';O=E/'AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28'
REPORT=O.with_suffix('.md');load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert REPORT.is_file() and not O.exists()
labels=['policy_focused_01','rehearsal_verify_02','locked_dependencies_01','analyze_01',
        'full_hmi_01','profile_build_01','root_tests_01','ab_spec_01','ab_contracts_01',
        'strict_consistency_01','whitespace_01','plc_transfer_01']
assert all(load(W/(n+'_exit.json'))['exitCode']==0 for n in labels)
assert '+740 ~12: All tests passed!' in (W/'full_hmi_01.log').read_text(encoding='utf-8')
assert 'Ran 74 tests' in (W/'root_tests_01.log').read_text(encoding='utf-8')
proof=load(W/'rehearsal_analysis_01.json')
assert proof['prerequisitePassed'] and proof['consecutiveQualifyingProfiles']==3
assert proof['sourceFiles']==27 and all(sha(H/p)==s for p,s in proof['sourceSha256'].items())
approval=load(R/'Specification/AllenBradley/AB_S4B_METADATA_TIER_PATHS_2026-10-28.json')
assert approval['ownerApproved'] and approval['implemented'] and approval['candidatePaths']==230
O.mkdir();artifacts=[]
def copy(p,name,origin):
    assert not any(word in p.name.lower() for word in ['credential','authorization','password'])
    raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
    target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),origin=origin,
                          **({'expandedSha256':expanded} if expanded else {})))
for p in sorted(W.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in {'.py','.dart','.json','.log','.png','.gz'}:continue
    if p.name in {'seal_o8_01.log','seal_o8_01_exit.json'}:continue
    if any(x in p.parts for x in ['__pycache__','.dart_tool','build','bin','obj']):continue
    rel=p.relative_to(W).as_posix();copy(p,'Work/'+rel,'work/'+rel)
sources={}
current=[H/p for p in proof['sourceSha256']]
current+=[R/'Specification/AllenBradley'/p for p in [
 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md',
 'AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md','AB_S4B_METADATA_TIER_PATHS_2026-10-28.json']]
for p in current:
    rel=p.relative_to(R).as_posix();sources[rel]=sha(p);copy(p,'Current/'+rel,'repository/'+rel)
manifest=dict(schemaVersion=1,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 report=dict(path=REPORT.name,sha256=sha(REPORT)),sourceSha256=sources,
 ownerDecision='O8 approved',rehearsalPrerequisitePassed=True,nativeAcceptanceClaim=False,
 controllerChanges=0,artifactCount=len(artifacts),artifacts=artifacts)
with (O/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
receipt=dict(report=str(REPORT),payload=str(O),artifacts=len(artifacts),sourceFiles=len(sources),
 manifestSha256=sha(O/'artifact_manifest.json'),rehearsalPrerequisitePassed=True,controllerChanges=0)
with (W/'sealed_o8_01.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
