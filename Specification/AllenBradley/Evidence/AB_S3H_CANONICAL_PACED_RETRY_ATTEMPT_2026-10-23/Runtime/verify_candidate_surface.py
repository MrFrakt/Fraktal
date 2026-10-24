"""Read-only post-session acceptance audit; no controller access."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
sys.path.insert(0,"C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools")
import fraktal_ab_access as owner
import fraktal_ab_mailbox as mailbox
manual_path="Press/Access/Policy/Required["+str(owner.GATES[mailbox.MANUAL_COMMAND])+"]"
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():parser.error('new output required')
try:
 fixture=json.loads(args.fixture.read_text())
 assert not fixture.get('error'),'fixture recorded an error'
 assert len(fixture['rows'])==31 and all(r['passed'] for r in fixture['rows']),'31 passing rows required'
 assert fixture['restored'] and fixture['policyRestored'],'fixture restoration incomplete'
 decisions=fixture['s3hDecisionPairs'];conditions=fixture['s3hConditionPairs'];sequences=fixture['s3hSequencePairs']
 assert len(decisions)==4,'four decision pairs required'
 coverage={(r['kind'],r['languageOrdinal']) for r in conditions if r['passed']}
 assert {('held',n) for n in range(3)}|{('fault',n) for n in range(3)}<=coverage,'held/fault coverage incomplete'
 expected={(language,case) for language in ('ST','SFC','LD') for case in ('OK','handled_NOK','HELD_resume','abort','mode_change','adopted_fault','single_reset_restart')}
 actual={(r['language'],r['case']) for r in sequences}
 assert len(sequences)==21 and actual==expected,'complete rendition/sequence coverage required'
 captures=[];fast=set();flag_values=set();event_states=set();closed_durations=[];heads=[]
 resets=fixture['s3hResetPairs'];access=fixture['s3hAccessPairs']
 extra=fixture['s3hAccessRows'];assert len(extra)==2 and all(r['passed'] for r in extra)
 assert {r['case'] for r in extra}=={'unknown_user_login_refused','class_policy_change_restore'}
 assert len(access)==6 and {r['phase'] for r in access}=={'login_busy','login_failed','authenticated','class_policy_changed','class_policy_restored','logged_out'}
 required_values=set();class_values=set();audit_descriptions=[]
 reset_coverage={(r['phase'],r['languageOrdinal']) for r in resets if r['passed']}
 assert {(phase,n) for phase in ('before','after') for n in range(3)}<=reset_coverage,'reset rendition coverage incomplete'
 assert len(resets)%2==0
 for before,after in zip(resets[::2],resets[1::2],strict=True):
  assert before['phase']=='before' and after['phase']=='after' and before['languageOrdinal']==after['languageOrdinal']
 config=fixture['s3hConfigPairs'];config_rows=fixture['s3hConfigRows']
 expected_config={'page_walk_and_model_bank','edit_revision_and_exact_restoration','hidden_values_and_policy_restoration',
  'store_save_list_export_import_load_delete','provider_stale_parent_refused','provider_stale_login_refused',
  'provider_catalog_overflow_refused','provider_invalid_utf8_refused'}
 assert len(config_rows)==8 and {r['case'] for r in config_rows}==expected_config and all(r['passed'] for r in config_rows)
 assert fixture['s3fSetMediumEmpty'],'isolated set medium not cleaned'
 assert len(config)>0 and {r['page'] for r in config}>={0,1,2} and any(r['model']==2 for r in config)
 for kind,items in [('decision',decisions),('condition',conditions),('sequence',sequences),('reset',resets),('access',access),('configuration',config)]:
  for item in items:
   path=Path(item['output']);raw=path.read_bytes();evidence=json.loads(gzip.decompress(raw));result=evidence['comparison'];state=evidence['pair']
   assert item['passed'] and evidence['passed'] and result['equal'] and result['typeAcceptance']
   values=state['canonical']['values'];page=values['Press/HmiResponse/ConfigPage/PageIndex']
   expected_count={0:3672,1:3622,2:3272}[page]+70+13*values['Press/HostEvents/Count']
   assert 0<=values['Press/HostEvents/Count']<=16
   assert state['canonical']['types']['Press/Part/Result/Stamp']=='DateTime'
   assert state['canonical']['types']['Press/HostEvents/Count']=='Int16'
   assert state['canonical']['types']['Press/Part/Result/Records[1]/Value']=='Double'
   if kind=='configuration':assert page==item['page']
   assert result['comparedPaths']==result['typedPaths']==expected_count
   assert values['Press/HmiResponse/ConfigPage/Revision']==values['Press/Status/ConfigRev']
   from fraktal_ab_canonical_reader import snapshot
   assert snapshot(state['capture'])==state['canonical'],'generic capture replay changed'
   assert state['canonical']['types']['Press/ConfigSets[1]/SetSchema']=='UInt16'
   assert state['canonical']['types']['Press/ConfigPersist/PendingSince']=='DateTime'
   proof=state['stateEvidence'];assert state['sameStateVerified'] and proof['kind']=='PLC entire-scan generation'
   assert proof['generation']>0 and proof['generation']%2==0
   values=state['canonical']['values']
   if kind=='decision':assert values['Press/Decision/Prompt']
   if kind=='condition':
    base=item['diagnosticPath'];assert values[base+'ReasonCode']!=0 and values[base+'Since']!=0
   heads.append((proof['generation'],values['Press/AlarmLog/RingHead']))
   flag_values.add(values['Press/StateFlags[1]/Value'])
   assert state['canonical']['types']['Press/Access/LoginResultSequence']=='UInt32'
   required_values.add(values[manual_path])
   class_values.add(values['Press/Access/Classes[2]/ReadLevel'])
   audit_descriptions += [v for p,v in values.items() if '/AlarmLog/Ring[' in p and p.endswith('/Description') and v.startswith('std.audit.')]
   if kind=='access':
    phase=item['phase'];base='Press/Access/'
    if phase=='login_busy':assert values[base+'LoginBusy']
    if phase=='login_failed':assert values[base+'LoginFailed'] and not values[base+'LoginBusy'] and values[base+'CurrentLevel']==0
    if phase=='authenticated':assert not values[base+'LoginFailed'] and not values[base+'LoginBusy'] and values[base+'CurrentUser'] and values[base+'CurrentLevel']==4
    if phase=='logged_out':assert values[base+'CurrentLevel']==0 and values[base+'CurrentUser']==''
    if phase=='logged_out':assert values[base+'Classes[2]/ReadLevel']==4
    if phase=='class_policy_changed':assert values[base+'Classes[2]/ReadLevel']==extra[1]['temporaryReadLevel']
    if phase=='class_policy_restored':assert values[base+'Classes[2]/ReadLevel']==extra[1]['originalReadLevel']
   for n in range(1,17):event_states.add(values[f'Press/AlarmLog/Active[{n}]/State'])
   for n in range(1,65):
    base=f'Press/AlarmLog/Ring[{n}]/'
    if values[base+'SourcePath'] and values[base+'ComeAt'] and values[base+'GoneAt']:
     assert values[base+'State']==0
     closed_durations.append(values[base+'Duration'])
   if kind=='reset':
    assert values['Press/AlarmLog/Blocking']==(item['phase']=='before')
   if kind=='sequence':
    case=item['case'];count=values['Press/SequenceStepCount']
    if case=='mode_change':assert count==0,'mode change failed to clear rows'
    if case in ('OK','handled_NOK','HELD_resume','single_reset_restart'):
     assert count>0 and any(values[f'Press/SequenceSteps[{n}]/Visited'] for n in range(1,22))
    if case=='handled_NOK':assert values['Press/SequenceAnnotationCount']>0
    if any(values[f'Press/SequenceSteps[{n}]/Visited'] and values[f'Press/SequenceSteps[{n}]/StepNo']!=values['Press/CurrentStep/StepNo'] and 0<=values[f'Press/SequenceSteps[{n}]/LastDuration']<100 for n in range(1,22)):
     fast.add(item['language'])
   captures.append(dict(kind=kind,path=str(path),sha256=hashlib.sha256(raw).hexdigest(),paths=expected_count))
 assert fast=={'ST','SFC','LD'},'retained completed fast-step coverage missing'
 assert flag_values=={False,True},'state flag transition coverage missing'
 assert 1 in event_states,'active alarm observation missing'
 assert closed_durations and max(closed_durations)>0,'closed event duration observation missing'
 assert required_values=={0,1},'manual policy transition missing'
 assert class_values=={extra[1]['originalReadLevel'],extra[1]['temporaryReadLevel'],4},'class policy/hiding transition missing'
 assert any(v.startswith('std.audit.loginFailed: fraktal_s3e_no_user ') for v in audit_descriptions),'negative login audit missing'
 assert any(v.startswith('std.audit.operatorAction: ') for v in audit_descriptions),'operator action audit missing'
 ordered=sorted(heads)
 ring_wrap_observed=any(b<a for (_,a),(_,b) in zip(ordered,ordered[1:]))
 report=dict(configurationRows=len(config_rows),configurationPairs=len(config),plannedCandidateRows=41,manualPolicyPath=manual_path,accessRows=2,accessPairs=6,requiredLevelsObserved=sorted(required_values),classReadLevelsObserved=sorted(class_values),auditDescriptionsObserved=len(audit_descriptions),resetPairs=len(resets),resetCoverage=sorted(reset_coverage),activeStatesObserved=sorted(event_states),stateFlagValuesObserved=sorted(flag_values),closedDurationMaximum=max(closed_durations),ringWrapObserved=ring_wrap_observed,passed=True,readOnly=True,rows=31,decisionPairs=len(decisions),conditionPairs=len(conditions),sequencePairs=len(sequences),conditionCoverage=sorted(coverage),retainedFastStepRenditions=sorted(fast),captures=captures)
except (AssertionError,ValueError,KeyError,TypeError,OSError) as error:report=dict(passed=False,readOnly=True,error=str(error))
with args.output.open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
