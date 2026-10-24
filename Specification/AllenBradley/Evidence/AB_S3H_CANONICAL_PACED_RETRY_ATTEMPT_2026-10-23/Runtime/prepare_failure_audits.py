from pathlib import Path
R=Path(__file__).parent;prior=R.parent/'runtime_fd53835fe9684f598bdd829da6d29c8d'
t=(R/'replay_runtime_captures.py').read_text()
old="items=[item for key,value in fixture.items() if key.endswith('Pairs') for item in value]"
assert t.count(old)==1
t=t.replace(old,old[:-1]+" if item['passed']]")
t=t.replace("items.append(dict(output=str(R/'idle_equivalence_01.json.gz'),passed=True))\n",'')
with (R/'replay_partial_captures.py').open('x') as f:f.write(t)
t=(prior/'close_failed_session.py').read_text()
for old,new in {
 'retry_9d1da9a04d564b03bc2b176f5b17ea42':'retry_fc306d330cc642499a52abbb53bae945',
 "'acquisition_inspection_02'":"'acquisition_inspection_01','partial_replay_01'",
 "fixture['error']=='access equivalence failed'":"fixture['error']=='condition equivalence failed'",
 'len(passed)==3':'len(passed)==39',
 '==(93,3,4)':'==(77,6,17)',
 'passingPairs=3,failedPairs=1':'passingPairs=39,failedPairs=1',
 'abTests=2148':'abTests=2149',
 "failedOfflineAuditCorrected='Initial audit compared unadjusted old/new D2 paths; rerun applies only existing five-bound allow-list',":"activeHeldCaptureNotAccepted=True,independentPartialReplays=39,",
 'call_b3c6555953654068a83f787a8b82de5e:0':'call_9b203bdff24848999469abe17a76ee4f:0',
 }.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (R/'close_failed_session.py').open('x') as f:f.write(t)
