from pathlib import Path
import datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
W=Path('C:/work/fraktal-ab-s4b-observer-20261029/offline_01')
E=R/'Specification/AllenBradley/Evidence';Q=E/'AB_S4B_OBSERVER_POLICY_2026-10-29'
O=E/'AB_S4B_Q_OBSERVER_PREPARATION_2026-10-29';report=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and not (D/'authorization.json').exists() and report.is_file()
for label in ['sdk_build_01','desktop_native_build_01','helper_tests_01','workflow_tests_01']:
    assert load(D/(label+'_exit.json'))['exitCode']==0,label
qualified=load(Q/'artifact_manifest.json')
for artifact in qualified['artifacts']:
    p=Q/artifact['path'];assert sha(p)==artifact['sha256'].upper(),p
for path,pin in qualified['sourceSha256'].items():assert sha(R/path)==pin.upper(),path
assert qualified['desktopPrerequisiteTransferredByExactSources'] and qualified['newObserverRehearsalPassed']
for name in ['desktop_prerequisite_transfer_01.json','observer_peer_qualification_01.json','plc_transfer_01.json']:
    with (D/name).open('xb') as f:f.write((W/name).read_bytes())
transfer=load(D/'plc_transfer_01.json');bound=dict(transfer['sourceSha256']);assert len(bound)==373
for path,pin in bound.items():assert sha(Path(path))==pin.upper(),path
paths=[Q/'artifact_manifest.json',Q.with_suffix('.md'),report,R/'AGENTS.md']
for tree in ['lib','packages/fraktal_opcua_client/lib','test','integration_test','test_driver','tool']:
    paths+=list((H/tree).rglob('*.dart'))
paths += [H/'pubspec.yaml',H/'pubspec.lock',H/'packages/fraktal_opcua_client/pubspec.yaml',D/'dart_package_config.json']
paths += [p for p in D.rglob('*') if p.is_file() and not any(s in p.parts for s in ['__pycache__','obj'])
          and (p.suffix in ['.py','.ps1','.cs','.csproj'] or 'desktop_app' in p.parts or 'bin' in p.parts)]
paths += [D/name for name in ['capacity_review.json','canonical_prepared_compare.json','desktop_app_hashes.json',
    'desktop_expected_inventory.json','authorization.template.json','desktop_prerequisite_transfer_01.json','observer_peer_qualification_01.json']]
prior=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
paths += [prior/name for name in ['audit_baseline_access.py','final_checks.py','measure_timing.py']]
paths += [Path('C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe')]
for path in paths:bound[path.as_posix()]=sha(path)
with (D/'source_bindings.json').open('x') as f:
    json.dump(dict(gatesPassed=True,sha256=bound,sourceFiles=len(bound),plcTransferInputs=373,
        desktopProofTransferred=True,newObserverSamples=100,correctionManifestSha256=sha(Q/'artifact_manifest.json'),
        nativeClaim=False,credentialFilesBoundOrArchived=False),f,indent=2)
O.mkdir();artifacts=[]
for p in sorted(D.rglob('*')):
    if not p.is_file() or any(s in p.parts for s in ['__pycache__','obj','bin','desktop_app']):continue
    if p.suffix not in {'.py','.ps1','.cs','.csproj','.json','.log','.sha256'}:continue
    if p.name in ['seal_preparation_01.log','seal_preparation_01_exit.json']:continue
    name='Preparation/'+p.relative_to(D).as_posix();raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
    target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        **({'expandedSha256':expanded} if expanded else {})))
manifest=dict(report=dict(path=report.name,sha256=sha(report)),sourceBindingsSha256=sha(D/'source_bindings.json'),
    createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifactCount=len(artifacts),artifacts=artifacts,
    controllerChanges=0,actualAuthorizationCreated=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),sourceFiles=len(bound),manifestSha256=sha(O/'artifact_manifest.json'))))
