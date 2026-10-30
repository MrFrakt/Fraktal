from pathlib import Path
import datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal')
O=R/'Specification/AllenBradley/Evidence/AB_S4B_OWNER_REVISION_RUNTIME_ATTEMPT_2026-10-29'
report=O.with_suffix('.md');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_bytes())
assert not O.exists() and report.is_file()
s=load(D/'session_result.json');assert not s['passed'] and s['genealogyRestored'] and s['rollbackError'] is None
assert not s['dumpFiles'] and not any(s[k] for k in ['faultClears','clockChanges','powerOperations','hardKills'])
for label in ['deploy','deploy_audit','deploy_readback','deploy_access','candidate_timing',
 'restore_genealogy','restore_genealogy_audit','restore_access','restore_original_medium',
 'baseline_regressions','manual_final','final_checks','preflight_final','baseline_timing']:
 assert load(D/(label+'_exit.json'))['exitCode']==0,label
b=load(D/'baseline_regressions.json');assert len(b['rows'])==31 and all(r['passed'] for r in b['rows'])
O.mkdir();artifacts=[]
for p in sorted(D.rglob('*')):
 if not p.is_file() or any(s in p.parts for s in ['__pycache__','obj','bin','desktop_app']):continue
 if p.suffix not in {'.py','.ps1','.cs','.csproj','.json','.jsonl','.log','.sha256','.gz','.csv','.png'}:continue
 if p.name in ['seal_runtime_attempt_01.log','seal_runtime_attempt_01_exit.json']:continue
 assert not any(s in p.name.lower() for s in ['credential','password'])
 raw=p.read_bytes();name='Runtime/'+p.relative_to(D).as_posix();expanded=None
 if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
 target=O/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(raw)
 artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
  **({'expandedSha256':expanded} if expanded else {})))
m=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 artifactCount=len(artifacts),artifacts=artifacts,passed=False,genealogyRestored=True,baselineCases=31,
 credentialsArchived=False,binariesOrAcdArchived=False,nativeAccepted=False)
with (O/'artifact_manifest.json').open('x') as f:json.dump(m,f,indent=2)
for a in artifacts:assert sha(O/a['path'])==a['sha256']
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),manifestSha256=sha(O/'artifact_manifest.json'))))
