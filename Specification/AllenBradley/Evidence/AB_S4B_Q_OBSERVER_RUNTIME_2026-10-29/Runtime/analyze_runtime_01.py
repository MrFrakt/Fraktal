from pathlib import Path
import csv,gzip,json,re,statistics
D=Path(__file__).parent
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
session=load(D/'session_result.json');assert not session['passed'] and session['genealogyRestored'] and session['rollbackError'] is None
fixture=load(D/'candidate_regressions.json');replay=load(D/'paired_replay_01.json')
assert all(row['passed'] for key in ['rows','s4bAccessRows','s4bConfigRows'] for row in fixture[key])
assert replay['passed'] and replay['pairs']==87
observer=load(D/'dart_qualification.json.gz')
refused=next(s for s in observer['snapshots'] if s.get('qualificationRejectedBadSample'))
bad={p:v for p,v in refused['dataValues'].items() if v['status']&0xc0000000==0x80000000}
desktop=load(D/'desktop_profile/result.json');assert desktop['desktopLiveAccepted'] and len(desktop['shots'])==31
ages=[int(x) for x in re.findall(r'stage=complete-sample-mapped effectiveAgeUs=(\d+)',(D/'desktop_profile/refresh.log').read_text(encoding='utf-8'))]
gate=load(D/'native_read_gates_01.json')['gates'];assert gate['E5']['passed'] and gate['E6']['passed'] and gate['E7']['passed'] and gate['E8']['passed']
baseline=load(D/'baseline_regressions.json');assert len(baseline['rows'])==31 and all(r['passed'] for r in baseline['rows'])
assert load(D/'final_checks.json')['passed'] and load(D/'preflight_final_exit.json')['exitCode']==0
assert load(D/'host_cpu_monitor_exit.json')['exitCode']==0
cpu=list(csv.DictReader((D/'host_cpu.csv').open(encoding='utf-8')))
timing=load(D/'candidate_timing.json');prefix='FRK_Press_HealthProbe.'
stages=['configuration_comparison','idle_equivalence','generic_acquire','desktop_profile','candidate_timing']
assert [s for s in session['stagesStarted'] if s in stages]==stages
probe=load(D/'packet_timing_01.json.gz');assert probe['error'] is None and len(probe['outcomes'])==24
result=dict(passed=False,caseCounts={key:len(fixture[key]) for key in ['rows','s4bAccessRows','s4bConfigRows']},
    replayedPairs=87,observerSamples=len(observer['samples']),observerBadLeaves=len(bad),
    observerBadAgesMs=sorted({v['ageMs'] for v in bad.values()}),configurationPages=len(observer['configurationPages']),
    p5Satisfied=True,readOnlyStageOrder=stages,idlePaths=5407,genericValues=5407,modules=7,desktopViews=31,busNodes=3,
    desktopMappedSamples=len(ages),desktopMaxMappedAgeUs=max(ages),task=gate['E8'],
    taskFinalMedianUs=statistics.median(r['values'][prefix+'TaskLastScanUs'] for r in timing['samples']),
    cpuHostSamples=sum(r['kind']=='host' for r in cpu),cpuInvalidSamples=sum(r['kind']=='invalid' for r in cpu),
    cpuMissingHostSamples=sum(r['kind']=='missing' for r in cpu),cpuMonitorExit=0,
    oneConnectionDiagnostic=dict(outcomes=24,bad=sum(r['bad'] for r in probe['outcomes']),uncertain=sum(r['uncertain'] for r in probe['outcomes']),
        cyclicMedianUs=statistics.median(r['us'] for r in probe['outcomes'] if r['phase']=='cyclic-coalesced'),acceptanceClaim=False),
    fourConnectionDiagnostic='Refused after genealogy restore: no canonical manifest; zero outcomes. Not a concurrency comparison.',
    genealogyRestored=True,originalDocuments=5,baselineCases=31,finalChecksPassed=True,preflightPassed=True,
    dumpFiles=session['dumpFiles'],o7Triggered=False,forbiddenOperations={k:session[k] for k in ['faultClears','clockChanges','powerOperations','hardKills']})
with (D/'runtime_analysis_01.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
