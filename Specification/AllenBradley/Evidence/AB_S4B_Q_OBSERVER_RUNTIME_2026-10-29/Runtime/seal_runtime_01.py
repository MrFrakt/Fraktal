from pathlib import Path
import datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');E=R/'Specification/AllenBradley/Evidence'
O=E/'AB_S4B_Q_OBSERVER_RUNTIME_2026-10-29';report=O.with_suffix('.md')
W=Path('C:/work/fraktal-ab-s4b-observer-20261029/offline_01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
analysis=load(D/'runtime_analysis_01.json')
assert not analysis['passed'] and analysis['desktopViews']==31 and analysis['genealogyRestored']
assert analysis['p5Satisfied'] and analysis['task']['passed'] and analysis['baselineCases']==31
assert all(load(D/(label+'_exit.json'))['exitCode']==0 for label in ['spec_post_01','contracts_post_01','consistency_post_01','root_post_01','whitespace_post_01'])
bound=load(D/'source_bindings.json')['sha256'];assert len(bound)==699
for path,pin in bound.items():assert sha(Path(path))==pin.upper(),path
(D/'Diagnostics').mkdir()
for number in [1,2]:
    name=f'packet_timing_{number:02}.dart';prepared=load(D/f'packet_probe_preparation_{number:02}.json')
    assert sha(W/name)==prepared['sourceSha256'].upper()
    with (D/'Diagnostics'/name).open('xb') as f:f.write((W/name).read_bytes())
with (D/'Diagnostics/prepare_four_socket_probe_01.py').open('xb') as f:f.write((W/'prepare_four_socket_probe_01.py').read_bytes())
O.mkdir();artifacts=[]
sources=list(D.glob('*'))+list((D/'scripts').glob('*.py'))+[D/'session/Program.cs',D/'session/S4bSession.csproj']
sources+=list((D/'desktop_profile').glob('*'))+list((D/'Diagnostics').glob('*'))
for p in sorted(sources):
    if not p.is_file() or p.suffix.lower() not in {'.json','.jsonl','.log','.py','.ps1','.csv','.gz','.cs','.csproj','.sha256','.dart','.png'}:continue
    if p.name in ['seal_runtime_01.log','seal_runtime_01_exit.json']:continue
    assert not any(x in p.name.lower() for x in ['credential','password'])
    name='Runtime/'+p.relative_to(D).as_posix();raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
    target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        **({'expandedSha256':expanded} if expanded else {})))
for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md']:
    path=R/'Specification/AllenBradley'/name;target=O/'Current'/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(path.read_bytes())
    artifacts.append(dict(path='Current/'+name,sha256=sha(path).lower(),bytes=path.stat().st_size))
manifest=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceBindingsSha256=sha(D/'source_bindings.json'),artifactCount=len(artifacts),artifacts=artifacts,passed=False,
    desktopNativeAccepted=True,genealogyRestored=True,credentialFilesArchived=False,binaryOrAcdArchived=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),manifestSha256=sha(O/'artifact_manifest.json'),desktopNativeAccepted=True,stagePassed=False)))
