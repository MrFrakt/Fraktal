"""Record the completed witness session and prepared row-refill correction."""
from pathlib import Path
import json

R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
B=Path('C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01')
q=json.loads((B/'runtime_summary_01.json').read_bytes())
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['observerSamples']==2805
assert q['allGoodSamples']==2805 and q['loginBusyWitness']['passed']
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and not q['nativeAccepted']
assert json.loads((W/'flutter_01_exit.json').read_bytes())['exitCode']==0
assert b'668 ~12: All tests passed!' in (W/'flutter_01.log').read_bytes()
runtime='Evidence/AB_S4B_BUSY_WITNESS_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_REFILL_PREPARATION_2026-10-27.md'
body=f'''**Latest, 2026-10-27: the busy witness and full workload pass; strict desktop remains open.**
The [sealed witness attempt]({runtime}) passes **41/41 candidate cases** and
**87/87 independent exact raw-record replays** (4,799–5,407 paths). The short
busy witness separately proves both canonical/legacy values true at entire-scan
generation **4,934**, using six polls; it is not counted as a full pair.
The corrected reader completes **2,805 entirely Good samples**, zero Uncertain
or Bad, four configuration queries and targeted details. Observer age median/
p95/max is **279.061 /347.923 /520.648 ms**; accepted row maximum **9,998 us**.
All **218 Part calls** succeed in **225 attempts**.

Desktop initially reaches LIVE with seven modules, then refuses `after-overview`.
The rejected sample has source age **995,517 us**, RPC **1,377,140 us**, server
bracket **1,066.586 ms**, transit **311,554 us**, received age **1,307,071 us**,
local **3,489 us**, effective **1,310,560 us**, fast Good **1,000,000 us**.
Worker acquisition is **1,011,964 us**, queue **50,754 us**, projection **6,260 us**,
path expansion **18,757 us** and send **927 us**; frontend validation **2 us**.
These include instrumentation/scheduling and do not isolate a host/network/PLC
cause. Zero desktop views are accepted. Independent configuration comparison,
idle equivalence, generic acquisition and final candidate timing are skipped.
TASK maximum is **8,994 us /zero overlaps** over the recorded candidate epoch.
Genealogy/five original documents/**31/31 baseline**/all final and preflight
checks pass. The session is complete and its authorization consumed.

The [prepared refill correction]({prep}) removes the fixed four-row completion
barrier between independent groups. Each completed row makes its slot available
immediately, with **at most four active rows and one slot waiter**. Count
dependencies and the Status phase still drain the full window. Failures stop
further dispatch once observed and drain all started rows before refusing.
Targeted reads remain serial; each row keeps its whole socket lease and original
counter proof. Reads, values/types, publication order rules, source ages,
Good/expiry limits, attempts/deadlines and read-only policy are unchanged.
The old planner fails the deterministic held-sibling counterexample (four
groups started); the corrected planner starts the next ready group before the
slow sibling finishes. Native latency improvement is unproven.

**668 HMI tests pass /12 skipped**, **56 trace-enabled focused tests**, analyzer,
Windows build and enforced lockfile with Flutter **3.47.5 /Dart 3.13.4**. The
identical **319-input mirror** differs only in the planner and pool tests;
three new cases cover refill, failure draining and invalid concurrency. The
native-proven busy witness remains, with **14 apparatus tests** and six Part
trace tests. Fresh SDK/authorization/workflow/readiness/refusal gates, root
checks and **74 root tests** pass. All **373 PLC/gate bindings**, **2,339 AB tests**,
both v38 build/read-back/access/SDK gates and **65% Capacity** transfer by hashes.

The same-image retry is prepared and **not authorized**: fresh guards/backup,
MANUAL normalization if needed, Program/download/Run; inherited 41 cases with
the proven busy witness, corrected four-connection reader, existing traces and
TASK monitoring; strict desktop and remaining comparisons/acquisition/scan if
ready; then genealogy/original documents/31 baseline/final checks. No new PLC
write vectors. Fault/TASK-counter clears, clock/power/vendor-state operations
remain excluded. S4b is open, V2/Part III inactive; no commit/push. S5 gateway/
installer, S6 retirement/persistence/events/capacity and S7 physical/CIP Security
including real I/O remain.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Witness attempt]({runtime}) passes 41 cases/87 exact replays, the separate
same-scan busy witness and 2,805 entirely Good observer samples. Desktop becomes
STALE after overview at 1,310.560 ms; zero views accepted. Independent
configuration/idle/generic acquisition/final timing are skipped. TASK maximum
8,994 us /zero overlaps; genealogy/31 baseline/all final checks pass. The
[offline correction]({prep}) immediately refills completed row slots within
the same four-row bound, retaining count/Status barriers and failure draining.
668 HMI tests pass /12 skipped, 56 focused. Fresh session approval is required.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** The [witness attempt]({runtime})
passes 41 cases/87 exact replays plus the separate busy proof and 2,805 entirely
Good Dart samples. Desktop initially LIVE then becomes STALE after overview:
source 995.517 ms, received 1,307.071 ms, effective 1,310.560 ms. Worker acquisition
1,011.964 ms, queue 50.754 ms; frontend validation 0.002 ms. TASK maximum
8,994 us /zero overlaps. Genealogy/31 baseline/all final checks pass. The
[offline refill correction]({prep}) starts ready independent rows as slots
finish, retaining at most four active rows, count/Status barriers, whole-row
leases, failure draining and all proof/freshness limits. Three new tests,
668 HMI/12 skipped and 56 focused pass. Native improvement remains unproven;
fresh session approval is required. Unchanged PLC retains 2,339 AB tests and
65% Capacity by hashes. V2/Part III inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [tier/queue attempt]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [busy-witness attempt]({runtime}) passes all 41 cases/87 exact replays,
the separate same-scan busy proof and 2,805 entirely Good Dart samples. Desktop
initially LIVE then becomes STALE after overview at 1,310.560 ms. Zero views
are accepted; independent configuration/idle/full acquisition/final timing are
skipped. TASK maximum 8,994 us /zero overlaps. Genealogy/31 baseline/all final
checks pass and the authorization is consumed. S4b remains open.

The [offline row-refill correction]({prep}) retains the four-row bound but
starts the next ready independent row as a slot finishes. Count/Status barriers,
whole-row leases and failure draining remain. No wire/read/value/type contract,
source age, Good/expiry limit, row proof/retry/deadline or write policy changes.
Three new tests, 668 HMI/12 skips, 56 focused, analyzer/Windows/locked dependencies
and 74 root tests pass. The unchanged PLC/both v38 gates/65% Capacity remain
hash-bound. Native improvement requires a fresh authorized session.
V2/Part III remain inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner=(W.parent/'session_01/qualification_session_v2.py').as_posix(),
    lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptFailure='Desktop initially LIVE then STALE after overview at 1310560 us',
    observerSamples=2805,observerNonBadSamples=2805,observerAllGoodSamples=2805,allGoodSamples=2805,
    samplesWithUncertainRows=0,scanCumulativeMaxUs=8994,candidateCases=41,pairedCapturesReplayed=87,
    nativeAccepted=False,currentSessionAuthorized=False)
v['offlineGates'].update(flutterTests=668,rowRefillRegressionTests=3)
v['nativeLookupFreshness'].update(medianAgeMs=279.061,maxAgeMs=520.648,maxAcceptedRowWindowUs=9998)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=2805,observerAllGood=True,fullFixturePassed=True)
v['desktopLatestCoverage']=q['desktopCoverage']|dict(skipped=False,initialLiveModules=7,failedAt='after-overview')
v['latestDesktopAgeComponents']=q['desktopFreshnessDiagnostics']['observations'][0]
v['partReadDiagnostic'].update(latestRuntimeEvidence=runtime,calls=218,successfulCalls=218,failedCalls=0,attempts=225,skipped=False)
v['tierQueueCorrection'].update(nativeAccepted=False,nativeSessionAuthorized=False,runtimeEvidence=runtime,
    nativeSessionCompleted=True,approvalConsumed=True,shortRunOnly=False)
v['loginBusyWitness'].update(prepared=False,authorized=False,nativeAccepted=True,runtimeEvidence=runtime,
    approvalConsumed=True,generation=4934,polls=6)
v['rowRefillCorrection']=dict(implementedOffline=True,nativeAccepted=False,nativeSessionAuthorized=False,
    maximumActiveRows=4,maximumSlotWaiters=1,immediateRefill=True,countBarriersPreserved=True,
    statusBarrierPreserved=True,targetedReadsSerial=True,wholeRowLeasePreserved=True,
    drainsStartedRowsOnFailure=True,wireReadsChanged=False,sourceAgeChanged=False,
    freshnessLimitsChanged=False,rowProofChanged=False,retryLimitsChanged=False,
    readOnlyPolicyChanged=False,logicalValuesOrTypesChanged=False,newTests=3,focusedTests=56,
    hmiMirrorInputs=319,changedExistingHmiFiles=2,addedHmiFiles=0,preparation=prep)
v['acceptancePending']=['Native bounded row-refill qualification and strict live desktop coverage',
    'Independent pages/idle/generic acquisition','Final candidate scan timing',
    'Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b witness run passes 41 cases/87 replays, separate same-scan busy proof and 2805 all-Good samples. Desktop initially LIVE then STALE at 1310.560 ms; later acquisition skipped. Genealogy/31 baseline restored. Bounded immediate row refill passes 668 HMI/12 skipped and 56 focused tests offline; native acceptance open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated completed witness outcome and unapproved bounded row-refill preparation; no activation or controller access.')
