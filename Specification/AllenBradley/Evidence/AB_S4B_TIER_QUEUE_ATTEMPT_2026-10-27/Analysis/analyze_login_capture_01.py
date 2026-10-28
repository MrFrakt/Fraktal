"""Classify the recorded missed busy-state observation; no controller access."""
from pathlib import Path
import gzip
import json

S=Path(__file__).parent.parent/'session_01'
load=lambda p:json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
fixture=load(S/'candidate_regressions.json')
report=load(S/'candidate_regressions_access_01.json.gz')
pair=report['pair']
fields=('CurrentLevel','LoginBusy','LoginFailed','LoginResultSequence')
canonical={n:pair['canonical']['values']['Press/Access/'+n] for n in fields}
legacy={n:pair['legacyInputs']['additional']['accessState'][n] for n in fields}
assert canonical==dict(CurrentLevel=0,LoginBusy=False,LoginFailed=True,LoginResultSequence=1)
assert canonical==legacy and report['passed'] and pair['sameStateVerified']
assert fixture['error']=='bounded login must be observed busy'
result=dict(controllerAccess=False,fixtureError=fixture['error'],
    capturePassed=True,paths=len(pair['canonical']['values']),canonical=canonical,legacy=legacy,
    sameStateVerified=True,stateEvidence=pair['stateEvidence'],
    conclusion='The accepted full comparison sampled completed refusal, not the required transient busy state.',
    busyStateObserved=False,requestToCaptureDurationMeasured=False,
    exactMissCauseConfirmed=False,acceptancePassed=False,
    next='Observe the canonical/legacy busy values under one scan guard immediately after acknowledgement, before the full capture; retain the full comparison and all refusals.')
with (S/'login_capture_analysis_01.json').open('x',encoding='utf-8') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
