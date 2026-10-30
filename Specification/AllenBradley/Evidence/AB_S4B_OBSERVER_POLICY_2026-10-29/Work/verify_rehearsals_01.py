"""Independent, append-only WP4b.5 source/result/coverage verification."""
from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
labels=['profile_03','profile_04','profile_05']
source=load(W/labels[0]/'sources.json')
rows=[]
for label in labels+['debug_01']:
    bound=load(W/label/'sources.json');assert bound==source,label
    for name,pin in bound.items():
        assert sha(H/name)==pin,(label,name,'current')
        assert sha(W/label/'Sources'/name)==pin,(label,name,'copy')
    result=load(W/label/'result.json')
    assert result['controllerChanges']==0 and result['genealogyBeforeAfterVerified'] is True
    assert result['forcedPeerShutdown'] is False and result['delayScale']==1
    peer=[json.loads(s) for s in (W/label/'peer.log').read_text(encoding='utf-8').splitlines() if s.startswith('{')][-1]
    assert peer['rehearsalStopped'] is True and peer['refusedServices']==0 and peer['controllerWrites']==0
    timings=peer['delayTimingsUs'];assert timings and all(actual>=draw>0 for draw,actual in timings)
    result.update(label=label,checkedDelaySamples=len(timings),delayTimingsTruncated=peer['delayTimingsTruncated'])
    if label in labels:
        assert result['passed'] and result['completed'] and result['maxMappedEffectiveAgeUs']<=700000
        coverage=load(W/label/'desktop/result.json')
        assert coverage['rehearsalPassed'] and not coverage['desktopLiveAccepted']
        assert len(coverage['shots'])==31 and len(coverage['modules'])==7 and len(coverage['fieldbusNodes'])==3
        assert coverage['refusedActions']==2 and all(s['link']=='live' for s in coverage['shots'])
        result.update(shots=31,modules=7,busNodes=3,refusedActions=2)
    elif result['passed']:
        coverage=load(W/label/'desktop/result.json')
        assert coverage['rehearsalPassed'] and len(coverage['shots'])==31
        result['debugComparison']='Debug completed all 31 rehearsal views; no native claim'
    else:
        failure=load(W/label/'desktop/failure.json')
        assert not failure['desktopLiveAccepted']
        result['debugComparison']=str(failure['error'])
    rows.append(result)
changed=subprocess.check_output(['git','diff','--name-only','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','FraktalCore/HMI'],cwd=R,text=True).splitlines()
for path in changed:
    name=Path(path).relative_to('FraktalCore/HMI').as_posix()
    assert name in source,('unbound changed HMI input',name)
proof=dict(prerequisitePassed=True,consecutiveQualifyingProfiles=3,profileMaximumAgeLimitUs=700000,
    sourceFiles=len(source),sourceSha256=source,runs=rows,nativeAcceptanceClaim=False,controllerChanges=0)
with (W/'rehearsal_analysis_01.json').open('x',encoding='utf-8') as f:json.dump(proof,f,indent=2)
print(json.dumps(dict(prerequisitePassed=True,profiles=labels,debugComparison=rows[-1]['debugComparison'],sourceFiles=len(source))))
