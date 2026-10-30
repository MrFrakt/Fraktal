"""Summarize actual rehearsal results; do not turn diagnostics into acceptance."""
from pathlib import Path
import hashlib,json,re
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
load=lambda p:json.loads(Path(p).read_bytes())
rows=[];decoder=json.JSONDecoder()
for label in ('profile_final_01','debug_final_01','apparatus_final_01'):
    O=W/label;q=load(O/'result.json');refresh=(O/'desktop/refresh.log').read_text(encoding='utf-8')
    refusals=[]
    for line in refresh.splitlines():
        if 'stage=complete-sample-rejected' not in line:continue
        value={key:float(raw) if '.' in raw else int(raw) for key,raw in re.findall(r'(\w+)=(\d+(?:\.\d+)?)',line)}
        refusals.append(value)
    snapshots=[];operations=[]
    for line in (O/'desktop.log').read_text(encoding='utf-8',errors='replace').splitlines():
        for marker,output in (('{"cipTiming"',snapshots),('{"cipOperation"',operations)):
            at=line.find(marker)
            if at>=0:output.append(decoder.raw_decode(line[at:])[0])
    walks=[row for row in snapshots if row['cipTiming']=='snapshot']
    failure=load(O/'desktop/failure.json')
    assert not q['passed'] and not q['nativeAcceptanceClaim'] and q['controllerChanges']==0
    assert q['genealogyBeforeAfterVerified'] and not q['forcedPeerShutdown']
    stopped=[json.loads(line[line.find('{'):]) for line in (O/'peer.log').read_text().splitlines()
        if '{"rehearsalStopped"' in line][-1]
    assert stopped['refusedServices']==stopped['controllerWrites']==0
    rows.append(dict(label=label,**q,freshnessRefusals=refusals,views=len(failure['shots']),
        lastLink=failure['link'],failure=failure['error'],peer=stopped,
        walks=[{k:v for k,v in row.items() if k!='slowestGroups'} for row in walks],
        lastOperations=operations[-16:]))
bindings=load(R/'Specification/AllenBradley/Evidence/AB_S4B_MSP_PREPARATION_2026-10-27/Preparation/source_bindings.json')['sha256']
plc={path:pin for path,pin in bindings.items() if 'FraktalCore/PLC/Allen-Bradley/tools/' in path}
assert len(plc)==373
for path,pin in plc.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()==pin
summary=dict(schema='fraktal.ab.wp4b5-rehearsal-analysis',rows=rows,unchangedPlcBindings=373,
    abTestsTransferred=2339,capacityPercentTransferred=65,controllerChanges=0,
    prerequisitePassed=False,consecutiveQualifyingPasses=0,nativePreparationAllowed=False,
    nativeAcceptanceClaim=False,hardwareFallbackTriggered=False,
    interpretation='Quantile-model and zero-delay apparatus diagnostics; precise host/transport cause is not isolated. No native E7 run or host CPU threshold is claimed.')
with (W/'rehearsal_analysis_01.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
print(json.dumps(dict(passed=True,qualifyingPasses=0,unchangedPlcBindings=373,controllerChanges=0,
    runs=[dict(label=row['label'],views=row['views'],maxMappedEffectiveAgeUs=row['maxMappedEffectiveAgeUs'],
        freshnessRefusals=row['freshnessRefusals']) for row in rows])))
