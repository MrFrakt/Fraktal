from pathlib import Path
import datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
E=R/'Specification/AllenBradley/Evidence'
Q=E/'AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29'
O=E/'AB_S4B_OWNER_REVISION_RETRY_PREPARATION_2026-10-29';report=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and not (D/'authorization.json').exists() and report.is_file()
for label in ['sdk_build_01','desktop_native_build_01','helper_tests_01','workflow_tests_01','capacity_readiness_tests_01']:
 assert load(D/(label+'_exit.json'))['exitCode']==0,label
from capacity_readiness import validate
assert validate(load(D/'authorization.template.json'),load(D/'capacity_review.json'),(D/'canonical.sha256').read_text().strip())
offline=load(Q/'artifact_manifest.json')
assert offline['offlineGatesPassed'] and offline['desktopPrerequisitePassed'] and offline['observerPeerPassed']
for a in offline['artifacts']:assert sha(Q/a['path'])==a['sha256'].upper(),a['path']
bound={}
for p,pin in offline['sourceSha256'].items():
 assert sha(R/p)==pin.upper(),p
 bound[(R/p).as_posix()]=pin.upper()
paths=[Q/'artifact_manifest.json',Q.with_suffix('.md'),report,R/'AGENTS.md',
 R/'Specification/Fraktal_AB_Part_III.md',R/'Specification/HMI_CONTRACT.md',R/'Specification/OPCUA_TRANSPORT.md',
 H/'packages/fraktal_opcua_client/pubspec.yaml',D/'dart_package_config.json']
paths += [p for p in D.rglob('*') if p.is_file() and not any(s in p.parts for s in ['__pycache__','obj'])
 and (p.suffix in ['.py','.ps1','.cs','.csproj'] or 'desktop_app' in p.parts or 'bin' in p.parts)]
paths += [D/n for n in ['capacity_review.json','canonical_prepared_compare.json','desktop_app_hashes.json',
 'desktop_expected_inventory.json','authorization.template.json']]
prior=Path('C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c')
paths += [prior/n for n in ['audit_baseline_access.py','final_checks.py','measure_timing.py']]
paths += [Path('C:/work/fraktal-echo-control-20261018/bin/Debug/net8.0-windows/EchoControl.exe')]
for p in paths:bound[p.as_posix()]=sha(p)
with (D/'source_bindings.json').open('x') as f:json.dump(dict(gatesPassed=True,sha256=bound,
 sourceFiles=len(bound),offlineManifestSha256=sha(Q/'artifact_manifest.json'),nativeClaim=False,
 credentialFilesBoundOrArchived=False),f,indent=2)
O.mkdir();artifacts=[]
for p in sorted(D.rglob('*')):
 if not p.is_file() or any(s in p.parts for s in ['__pycache__','obj','bin','desktop_app']):continue
 if p.suffix not in {'.py','.ps1','.cs','.csproj','.json','.log','.sha256'}:continue
 if p.name in ['seal_preparation_01.log','seal_preparation_01_exit.json']:continue
 assert not any(s in p.name.lower() for s in ['credential','password'])
 name='Preparation/'+p.relative_to(D).as_posix();raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
  **({'expandedSha256':expanded} if expanded else {})))
m=dict(report=dict(path=report.name,sha256=sha(report)),sourceBindingsSha256=sha(D/'source_bindings.json'),
 createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifactCount=len(artifacts),artifacts=artifacts,
 controllerChanges=0,actualAuthorizationCreated=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(m,f,indent=2)
for a in artifacts:assert sha(O/a['path'])==a['sha256'].upper()
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),sourceFiles=len(bound),manifestSha256=sha(O/'artifact_manifest.json'))))
