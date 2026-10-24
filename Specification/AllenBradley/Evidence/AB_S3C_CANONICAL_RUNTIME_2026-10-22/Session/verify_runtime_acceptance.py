"""Read-only post-session acceptance audit; no controller access."""
from pathlib import Path
import argparse,gzip,hashlib,json
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():parser.error('new output required')
try:
 fixture=json.loads(args.fixture.read_text())
 assert not fixture.get('error'),'fixture recorded an error'
 assert len(fixture['rows'])==31 and all(r['passed'] for r in fixture['rows']),'31 passing rows required'
 assert fixture['restored'] and fixture['policyRestored'],'fixture restoration incomplete'
 decisions=fixture['s3cDecisionPairs'];conditions=fixture['s3cConditionPairs'];sequences=fixture['s3cSequencePairs']
 assert len(decisions)==4,'four decision pairs required'
 coverage={(r['kind'],r['languageOrdinal']) for r in conditions if r['passed']}
 assert {('held',n) for n in range(3)}|{('fault',n) for n in range(3)}<=coverage,'held/fault coverage incomplete'
 expected={(language,case) for language in ('ST','SFC','LD') for case in ('OK','handled_NOK','HELD_resume','abort','mode_change','adopted_fault','single_reset_restart')}
 actual={(r['language'],r['case']) for r in sequences}
 assert len(sequences)==21 and actual==expected,'complete rendition/sequence coverage required'
 captures=[];fast=set()
 for kind,items in [('decision',decisions),('condition',conditions),('sequence',sequences)]:
  for item in items:
   path=Path(item['output']);raw=path.read_bytes();evidence=json.loads(gzip.decompress(raw));result=evidence['comparison'];state=evidence['pair']
   assert item['passed'] and evidence['passed'] and result['equal'] and result['typeAcceptance']
   assert result['comparedPaths']==result['typedPaths']==647
   proof=state['stateEvidence'];assert state['sameStateVerified'] and proof['kind']=='PLC entire-scan generation'
   assert proof['generation']>0 and proof['generation']%2==0
   values=state['canonical']['values']
   if kind=='decision':assert values['Press/Decision/Prompt']
   if kind=='condition':
    base=item['diagnosticPath'];assert values[base+'ReasonCode']!=0 and values[base+'Since']!=0
   if kind=='sequence':
    case=item['case'];count=values['Press/SequenceStepCount']
    if case=='mode_change':assert count==0,'mode change failed to clear rows'
    if case in ('OK','handled_NOK','HELD_resume','single_reset_restart'):
     assert count>0 and any(values[f'Press/SequenceSteps[{n}]/Visited'] for n in range(1,22))
    if case=='handled_NOK':assert values['Press/SequenceAnnotationCount']>0
    if any(values[f'Press/SequenceSteps[{n}]/Visited'] and values[f'Press/SequenceSteps[{n}]/StepNo']!=values['Press/CurrentStep/StepNo'] and 0<=values[f'Press/SequenceSteps[{n}]/LastDuration']<100 for n in range(1,22)):
     fast.add(item['language'])
   captures.append(dict(kind=kind,path=str(path),sha256=hashlib.sha256(raw).hexdigest(),paths=647))
 assert fast=={'ST','SFC','LD'},'retained completed fast-step coverage missing'
 report=dict(passed=True,readOnly=True,rows=31,decisionPairs=len(decisions),conditionPairs=len(conditions),sequencePairs=len(sequences),conditionCoverage=sorted(coverage),retainedFastStepRenditions=sorted(fast),captures=captures)
except (AssertionError,ValueError,KeyError,TypeError,OSError) as error:report=dict(passed=False,readOnly=True,error=str(error))
with args.output.open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
