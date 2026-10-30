from pathlib import Path
import datetime,gzip,hashlib,json,re,statistics
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
O=R/'Specification/AllenBradley/Evidence/AB_S4B_OWNER_REVISION_RUNTIME_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
session=load(D/'session_result.json');gates=load(D/'native_read_gates_01.json')
assert session['passed'] and session['genealogyRestored'] and session['candidateError'] is session['rollbackError'] is None
assert not session['dumpFiles'] and not any(session[k] for k in ['faultClears','clockChanges','powerOperations','hardKills'])
assert gates['passed'] and all(v['passed'] for v in gates['gates'].values())
baseline=load(D/'baseline_regressions.json');assert len(baseline['rows'])==31 and all(x['passed'] for x in baseline['rows'])
assert load(D/'final_checks.json')['passed'] and load(D/'preflight_final_exit.json')['exitCode']==0
ages=[int(x) for x in re.findall(r'stage=complete-sample-mapped effectiveAgeUs=(\d+)',(D/'desktop_profile/refresh.log').read_text(encoding='utf-8'))]
assert max(ages)==255856
timing=load(D/'candidate_timing.json');median=statistics.median(x['values']['FRK_Press_HealthProbe.TaskLastScanUs'] for x in timing['samples'])
assert median==966 and gates['gates']['E8']['cumulativeMaxUs']==8974
capture=json.loads(gzip.decompress((D/'generic_capture.json.gz').read_bytes()))
assert capture['manifest']['schemaMinor']==10 and len(capture['manifest']['ownerReadBindings'])==8
assert sha(Path('C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD')).upper()=='D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084'
bindings=load(D/'source_bindings.json')['sha256']
changed={p for p,pin in bindings.items() if sha(Path(p)).upper()!=pin.upper()}
allowed={str(R/'Specification/AllenBradley'/n).replace('\\','/') for n in [
 'AB_FROZEN_CONTRACTS_V2.json','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md']}
assert changed<=allowed,changed
O.mkdir();artifacts=[]
def copy(p,name):
 raw=p.read_bytes();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
  **({'expandedSha256':expanded} if expanded else {})))
for p in sorted(D.rglob('*')):
 if not p.is_file() or any(s in p.parts for s in ['__pycache__','obj','bin','desktop_app']):continue
 if p.suffix not in {'.py','.ps1','.cs','.csproj','.json','.jsonl','.log','.sha256','.gz','.csv','.png'}:continue
 if p.name in ['seal_runtime_01.log','seal_runtime_01_exit.json']:continue
 assert not any(s in p.name.lower() for s in ['credential','password'])
 copy(p,'Runtime/'+p.relative_to(D).as_posix())
for name in ['AB_FROZEN_CONTRACTS_V2.json','AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
 'AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md','AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md']:
 copy(R/'Specification/AllenBradley'/name,'PostRuntime/'+name)
m=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 artifactCount=len(artifacts),artifacts=artifacts,passed=True,genealogyRestored=True,baselineCases=31,
 gates=gates['gates'],maximumMappedAgeUs=max(ages),medianScanUs=median,
 postRuntimeStatusDocumentsChanged=sorted(changed),productAndRuntimeInputsUnchanged=True,
 credentialsArchived=False,binariesOrAcdArchived=False,nativeScope='Echo S4b E1-E9; physical/security deferred')
with (O/'artifact_manifest.json').open('x') as f:json.dump(m,f,indent=2)
for a in artifacts:
 assert sha(O/a['path'])==a['sha256']
 if 'expandedSha256' in a:assert hashlib.sha256(gzip.decompress((O/a['path']).read_bytes())).hexdigest()==a['expandedSha256']
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),manifestSha256=sha(O/'artifact_manifest.json'),passed=True)))
