"""Seal the failed native attempt and successful rollback without credentials."""
from pathlib import Path
import csv,datetime,gzip,hashlib,json
D=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');E=R/'Specification/AllenBradley/Evidence'
O=E/'AB_S4B_Q_ATTEMPT_2026-10-29';report=O.with_suffix('.md')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
result=load(D/'session_result.json');assert not result['passed'] and result['genealogyRestored'] and result['rollbackError'] is None
fixture=load(D/'candidate_regressions.json');counts={key:len(fixture[key]) for key in ['rows','s4bAccessRows','s4bConfigRows']}
assert counts==dict(rows=31,s4bAccessRows=2,s4bConfigRows=8)
assert all(row['passed'] for key in counts for row in fixture[key]) and fixture['restored'] and fixture['policyRestored']
replay=load(D/'paired_replay_01.json');assert replay['passed'] and replay['pairs']==87
observer=load(D/'dart_qualification.json.gz');assert not observer['passed'] and observer['writes']==0 and len(observer['samples'])==43
refused=next(s for s in observer['snapshots'] if s.get('qualificationRejectedBadSample'))
bad={p:v for p,v in refused['dataValues'].items() if v['status']&0xc0000000==0x80000000}
assert len(bad)==56 and all(v['reason']=='read-expired' and 'value' not in v for v in bad.values())
marker=load(D/'candidate_run_requested.json');stamp=lambda t:datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
trace=load(D/'task_monitor.json.gz');assert trace['passed']
values=[r['values'] for r in trace['rows'] if r['available'] and stamp(r['utc'])>=stamp(marker['Utc'])]
maximum=max(v['FRK_Press_HealthProbe.TaskMaxScanUs'] for v in values)
overlaps=max(v['FRK_Press_HealthProbe.TaskOverlapCount'] for v in values)
assert len(values)==6416 and maximum==8994 and overlaps==0
baseline=load(D/'baseline_regressions.json');assert len(baseline['rows'])==31 and all(r['passed'] for r in baseline['rows'])
assert baseline['restored'] and baseline['policyRestored'] and load(D/'final_checks.json')['passed']
assert load(D/'medium_restored_01.json')['originalDocumentsRestored']==5
assert load(D/'preflight_final_exit.json')['exitCode']==0 and not result['dumpFiles']
assert all(result[k]==0 for k in ['faultClears','clockChanges','powerOperations','hardKills'])
bound=load(D/'source_bindings.json')['sha256'];assert len(bound)==700
for path,pin in bound.items():assert sha(Path(path))==pin.upper(),path
cpu=list(csv.DictReader((D/'host_cpu.csv').open(encoding='utf-8')))
analysis=dict(passed=False,candidateCases=41,replayedPairs=87,observerSamples=43,rejectedLeaves=len(bad),
    rejectedAgeMs=next(iter(bad.values()))['ageMs'],taskSamples=len(values),taskCumulativeMaxUs=maximum,taskOverlaps=overlaps,
    skipped=['configuration_comparison','idle_equivalence','generic_acquire','desktop_profile','candidate_timing'],
    p5Satisfied=False,cpuSamplerExit=load(D/'host_cpu_monitor_exit.json')['exitCode'],hostCpuSamples=sum(r['kind']=='host' for r in cpu),
    o7Triggered=False,genealogyRestored=True,baselineCases=31,finalChecksPassed=True,currentSourcesStillBound=len(bound),
    inheritedOfflineHmiPassed=740,inheritedOfflineHmiSkipped=12,transferredAbTests=2339,transferredV38Targets=2)
with (D/'runtime_analysis_01.json').open('x') as f:json.dump(analysis,f,indent=2)
O.mkdir();artifacts=[]
sources=list(D.glob('*'))+list((D/'scripts').glob('*.py'))+[D/'session/Program.cs',D/'session/S4bSession.csproj']
for p in sorted(sources):
    if not p.is_file() or p.suffix.lower() not in {'.json','.jsonl','.log','.py','.ps1','.csv','.gz','.cs','.csproj','.sha256'}:continue
    if p.name in {'seal_runtime_01.log','seal_runtime_01_exit.json'}:continue
    assert not any(x in p.name.lower() for x in ['credential','password'])
    # Only top-level known reports/captures/helpers and the explicit SDK/guard
    # sources above. Private medium backups and build trees are never walked.
    name='Runtime/'+p.relative_to(D).as_posix();raw=p.read_bytes();expanded=None
    if p.suffix=='.log':expanded=hashlib.sha256(raw).hexdigest();raw=gzip.compress(raw,mtime=0);name+='.gz'
    dest=O/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(raw)
    artifacts.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        **({'expandedSha256':expanded} if expanded else {})))
for name in ['AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md','AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md']:
    p=R/'Specification/AllenBradley'/name;dest=O/'Current'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(p.read_bytes())
    artifacts.append(dict(path='Current/'+name,sha256=sha(p).lower(),bytes=p.stat().st_size))
manifest=dict(report=dict(path=report.name,sha256=sha(report)),createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceBindingsSha256=sha(D/'source_bindings.json'),artifactCount=len(artifacts),artifacts=artifacts,
    passed=False,genealogyRestored=True,credentialFilesArchived=False,binaryOrAcdArchived=False)
with (O/'artifact_manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
print(json.dumps(dict(sealed=str(O),artifacts=len(artifacts),manifestSha256=sha(O/'artifact_manifest.json'),analysis=analysis)))
