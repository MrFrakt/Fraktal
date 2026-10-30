"""Append-only scheduling checkpoint. No credentials, binaries or controller I/O."""
from pathlib import Path
import datetime,gzip,hashlib,json,subprocess
W=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
E=R/'Specification/AllenBradley/Evidence'
O=E/'AB_WP4B5_SCHEDULING_2026-10-28'
REPORT=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_bytes())
assert REPORT.is_file() and not O.exists()
for label in ['locked_dependencies_02','analyze_final_02','full_hmi_03','profile_build_02',
              'root_tests_04','ab_spec_04','ab_contracts_04','strict_consistency_04',
              'whitespace_04','plc_transfer_03','final_genealogy_preflight_01']:
    assert load(W/(label+'_exit.json'))['exitCode']==0,label
assert '+738 ~12: All tests passed!' in (W/'full_hmi_03.log').read_text(encoding='utf-8')
assert 'Ran 74 tests' in (W/'root_tests_04.log').read_text(encoding='utf-8')
assert 'No issues found!' in (W/'analyze_final_02.log').read_text(encoding='utf-8')
package=load(H/'.dart_tool/package_config.json')
assert package['flutterVersion']=='3.47.5' and package['generatorVersion']=='3.13.4'
source=load(W/'debug_03/sources.json')
assert source==load(W/'profile_27/sources.json')
for path,pin in source.items():assert sha(H/path)==pin,path
changed=subprocess.check_output(['git','diff','--name-only','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
assert all(Path(p).relative_to('FraktalCore/HMI').as_posix() in source for p in changed)
assert 'if (_streamsDetail && OpcUaFieldTier.isManifestServed(path))' not in (H/'lib/data/opcua_repository.dart').read_text()
runs=[]
for d in sorted(p for p in W.iterdir() if p.is_dir() and (p/'result.json').is_file()):
    result=load(d/'result.json');bound=load(d/'sources.json')
    for name,pin in bound.items():assert sha(d/'Sources'/name)==pin,(d.name,name)
    assert result['controllerChanges']==0 and result['genealogyBeforeAfterVerified']
    assert not result['forcedPeerShutdown']
    coverage=d/'desktop/result.json';failure=d/'desktop/failure.json'
    result=dict(result,label=d.name,sourceMatchesCurrent=bound==source,
                completedViews=len(load(coverage if coverage.exists() else failure).get('shots',[])))
    old=(d/'Sources/lib/data/opcua_repository.dart').read_text(encoding='utf-8')
    result['temporaryUnapprovedMetadataTier']='A binding may publish static containers' in old
    if failure.exists():result['failure']=load(failure)['error']
    runs.append(result)
for label in ['profile_23','profile_24','profile_25']:
    row=next(r for r in runs if r['label']==label)
    assert row['passed'] and row['completedViews']==31 and row['temporaryUnapprovedMetadataTier']
for label in ['profile_27','debug_03']:
    row=next(r for r in runs if r['label']==label)
    assert row['sourceMatchesCurrent'] and not row['passed']
summary=dict(prerequisitePassed=False,currentConsecutiveQualifyingProfiles=0,
             ownerDecisionApproved='O8',dependentImplementationNext=True,originalFastConfigurationFallbackActive=True,
             sourceFiles=len(source),sourceSha256=source,controllerChanges=0,
             nativePreparation=False,nativeAcceptanceClaim=False,runs=runs)
with (W/'rehearsal_summary_final_01.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)

O.mkdir()
artifacts=[]
def archive(path,relative,origin):
    assert path.suffix.lower() in {'.py','.dart','.json','.log','.png','.gz','.md','.yaml','.lock','.txt'},path
    assert not any(bad in path.name.lower() for bad in ['credential','authorization','password']),path
    raw=path.read_bytes();expanded=None
    if path.suffix.lower()=='.log':
        expanded=hashlib.sha256(raw).hexdigest()
        raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=relative,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                          origin=origin,**({'expandedSha256':expanded} if expanded else {})))

for p in sorted(W.rglob('*')):
    if not p.is_file():continue
    if p.name in {'seal_scheduling_01.log','seal_scheduling_01_exit.json'}:continue
    rel=p.relative_to(W)
    if any(part in {'.dart_tool','build','bin','obj','__pycache__'} for part in rel.parts):continue
    if p.suffix.lower() not in {'.py','.dart','.json','.log','.png','.gz'}:continue
    archive(p,'Work/'+rel.as_posix(),'work/'+rel.as_posix())
sources={}
current=[H/p for p in source]
current+=[R/'Specification/AllenBradley'/p for p in [
 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md',
 'AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md','AB_S4B_METADATA_TIER_PATHS_2026-10-28.json']]
for p in current:
    rel=p.relative_to(R).as_posix();sources[rel]=sha(p)
    archive(p,'Current/'+rel,'repository/'+rel)
manifest=dict(schemaVersion=1,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    report=dict(path=REPORT.name,sha256=sha(REPORT)),sourceSha256=sources,
    currentRehearsalPrerequisitePassed=False,ownerDecisionApproved='O8',dependentImplementationNext=True,controllerChanges=0,
    artifactCount=len(artifacts),artifacts=artifacts)
with (O/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
result=dict(report=str(REPORT),payload=str(O),artifacts=len(artifacts),sourceFiles=len(sources),
            manifestSha256=sha(O/'artifact_manifest.json'),currentRehearsalPrerequisitePassed=False,
            controllerChanges=0)
with (W/'sealed_scheduling_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
