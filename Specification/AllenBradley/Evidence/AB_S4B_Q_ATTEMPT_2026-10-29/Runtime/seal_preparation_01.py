"""Bind every used input and seal preparation before actual O3 authorization."""
from pathlib import Path
import datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
C=Path('C:/work/fraktal-ab-s4b-o8-20261028/offline_01')
E=R/'Specification/AllenBradley/Evidence';O=E/'AB_S4B_Q_PREPARATION_2026-10-29'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
load=lambda p:json.loads(p.read_bytes())
assert not (D/'authorization.json').exists() and not (D/'session_started.json').exists() and not O.exists()
report=O.with_suffix('.md');assert report.is_file()
for label in ['helper_tests_01','workflow_tests_01','cpu_sampler_check_01','sdk_build_02','desktop_native_build_01','prepared_readback_01']:
    assert load(D/(label+'_exit.json'))['exitCode']==0,label
comparison=json.loads((D/'prepared_readback_01.log').read_text(encoding='utf-8'));assert comparison['Equivalent']
with (D/'canonical_prepared_compare.json').open('x') as f:json.dump(comparison,f,indent=2)
transfer=load(C/'plc_transfer_01.json');bound=dict(transfer['sourceSha256'])
assert len(bound)==373
for name,pin in bound.items():assert sha(name)==pin.upper(),name
proof=E/'AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28/artifact_manifest.json'
manifest=load(proof);assert manifest['rehearsalPrerequisitePassed']
for name,pin in manifest['sourceSha256'].items():assert sha(R/name)==pin.upper(),name
for name in ['rehearsal_analysis_01.json','plc_transfer_01.json']:
    with (D/name).open('xb') as f:f.write((C/name).read_bytes())
paths=[proof,E/'AB_S4B_MSP_PREPARATION_2026-10-27/Preparation/source_bindings.json',report,R/'AGENTS.md']
for tree in ['lib','packages/fraktal_opcua_client/lib','test','integration_test','test_driver','tool']:
    paths += list((H/tree).rglob('*.dart'))
paths += [H/'pubspec.yaml',H/'pubspec.lock',H/'packages/fraktal_opcua_client/pubspec.yaml',D/'dart_package_config.json']
paths += [p for p in D.rglob('*') if p.is_file() and not any(s in p.parts for s in ['__pycache__','obj'])
          and (p.suffix in ['.py','.ps1','.cs','.csproj'] or 'desktop_app' in p.parts or 'bin' in p.parts)]
paths += [D/name for name in ['capacity_review.json','canonical_prepared_compare.json','desktop_app_hashes.json','desktop_expected_inventory.json','rehearsal_analysis_01.json','authorization.template.json']]
prior=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
paths += [prior/name for name in ['audit_baseline_access.py','final_checks.py','measure_timing.py']]
paths += [Path('C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe')]
for path in paths:bound[path.as_posix()]=sha(path)
value=dict(gatesPassed=True,sha256=bound,plcTransferInputs=373,sourceFiles=len(bound),
    approvedOwnerDecision='O8',nativeClaim=False,standingAuthorization='O3',
    prerequisiteManifestSha256=sha(proof),candidateAcd='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5',
    credentialFilesBoundOrArchived=False)
with (D/'source_bindings.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
O.mkdir();artifacts=[]
for p in sorted(D.rglob('*')):
    if not p.is_file() or any(x in p.parts for x in ['desktop_app','bin','obj','__pycache__']):continue
    if p.suffix not in {'.json','.log','.py','.ps1','.cs','.csproj','.sha256','.csv'}:continue
    if p.name in {'seal_preparation_01.log','seal_preparation_01_exit.json'}:continue
    assert not any(s in p.name.lower() for s in ['credential','password'])
    relative=p.relative_to(D).as_posix();raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);relative+='.gz'
    target=O/'Preparation'/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path='Preparation/'+relative,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        **({'expandedSha256':expanded} if expanded else {})))
value=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceBindingsSha256=sha(D/'source_bindings.json'),artifactCount=len(artifacts),artifacts=artifacts,
    controllerChanges=0,actualAuthorizationCreated=False)
with (O/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),sourceFiles=len(bound),manifestSha256=sha(O/'artifact_manifest.json'))))
