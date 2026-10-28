from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
T=Path('C:/work/fraktal-ab-s4b-timing-20261027/session_01');q=json.loads((T/'runtime_summary_01.json').read_bytes())
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['observerSamples']==2035
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and not q['nativeAccepted']
assert json.loads((W/'array_flutter_01_exit.json').read_bytes())['exitCode']==0
assert b'665 ~12: All tests passed!' in (W/'array_flutter_01.log').read_bytes()
runtime='Evidence/AB_S4B_DESKTOP_TIMING_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_TIER_QUEUE_PREPARATION_2026-10-27.md'
body=f'''**Latest, 2026-10-27: timing isolates acquisition costs; two bounded corrections are prepared offline.**
The [desktop timing attempt]({runtime}) completes **41/41 cases, 87/87 exact
independent raw-record replays and 2,035 observer samples**: **2,033 entirely
Good, two with payload-free Uncertain rows, zero Bad**. Observer age median/
p95/max is **309.58 /373.504 /997.151 ms**; accepted row window maximum is
**9,959 us**. Four configuration page queries and targeted details complete.
All 218 Part calls succeed in 223 attempts. Desktop reaches LIVE with seven
modules, then fails `after-overview`: source age **874,812 us**, RPC **1,170,250
us**, server bracket **879.170 ms**, transit **292,080 us**, received age
**1,166,892 us**, local **2,391 us**, effective **1,169,283 us** against
**1,000,000 us**. Zero views are accepted. Full acquisition/final scan are skipped.
TASK trace maximum is **8,937 us /zero overlaps**; genealogy, five original
documents, **31/31 baseline** and all final/preflight checks are restored.
The completed authorization is consumed. S4b remains open.

The refused desktop sample records **873,556 us acquisition**, **50,904 us
worker queue**, **10,934 us projection**, **18,689 us path expansion**,
**1,167 us send**, and **1 us frontend validation**. These intervals include
scheduling/instrumentation and do not isolate a network/host/PLC cause. The
trace reveals profiler primitive arrays being acquired despite excluded leaf
tiers. Offline regression cases confirm that the planner classified the array
base instead of its indexed logical leaves, and that excluded siblings could
incorrectly keep an otherwise slow group fast.

The [tier/queue correction]({prep}) resolves primitive-array leaves from the
PLC-published lower bound, extent and indices, then schedules the consumed
leaves. Fully excluded groups perform no cyclic read; all-consumed-slow groups
follow the existing heartbeat. A fast consumer keeps its group fast, and
targeted reads still bypass exclusion under the same row proof. Recorded-wire
replay falls **990→810 reads /297→237 groups /60→0 hidden ByClass reads**,
preserving all **976 consumed values and types** exactly. Four regression cases
fail before the correction and pass after; the targeted-read preservation case
passes both. This is offline work reduction, not a native latency claim.

The response-processing clock now starts when the worker receives a request
and ends at the existing source-age boundary. It includes serialized queue
time, as the transport envelope's server wait/read bracket requires. Source
timestamps, leaf/complete ages, Good/expiry limits, row proof and retry/deadline
remain unchanged. The existing receiver test covers queue+read accounting and
still refuses an underreported bracket. No PLC/source/type/value contract or
direct read-only policy change. Existing diagnostic tracing remains opt-in.

**665 HMI tests pass /12 skipped**, 53 trace-enabled focused tests, analyzer,
Windows and enforced lockfile with Flutter **3.47.5 /Dart 3.13.4**; **319 mirror
inputs** match. Three existing HMI source/test files change and one five-test
module is added. All **373 PLC/gate bindings**, **2,339 AB tests**, both v38
build/read-back/access/SDK gates, prior byte-identical images and **65% Capacity**
transfer by hashes. Fresh SDK, six retained Part-trace tests, authorization/
workflow/readiness/refusal gates, root checks and **74 root tests** pass.

The same-image retry is prepared and **not authorized**: fresh guards/backup,
MANUAL normalization if needed, Program/download/Run, five-document restore/
41 cases with the corrected four-connection reader and existing traces, 100 ms
TASK monitoring, strict desktop and remaining comparisons/acquisition/scan if
ready, then genealogy/original documents/31 baseline/final checks. Fault/TASK
counter clears, clock changes and power/vendor-state operations are excluded.
Native acceptance is unproven. V2/Part III inactive; no commit/push. S5 gateway/
installer, S6 retirement/persistence/events/capacity, S7 physical/CIP Security
including real I/O remain.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Timing attempt]({runtime}) passes 41 cases/87 exact replays and 2,035 observer
samples (2,033 entirely Good, two Uncertain, zero Bad). Desktop initially LIVE
then fails overview at 1,169.283 ms; full acquisition/final timing are skipped.
TASK maximum is 8,937 us /zero overlaps. Genealogy/31 baseline/final checks are
restored and the authorization is consumed. [Offline corrections]({prep})
honor logical primitive-array tiers and include worker queue time in the
existing response-processing bracket. No freshness/proof/retry limits change.
665 HMI tests pass /12 skipped. A fresh exact-image session is still required.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** The [timing attempt]({runtime})
passes 41 cases/87 exact replays and 2,035 observer samples (2,033 entirely
Good, two Uncertain, zero Bad). Desktop initially LIVE then becomes STALE after
overview at 1,169.283 ms. Acquisition is 873.556 ms, queue 50.904 ms, frontend
validation 0.001 ms. TASK maximum is 8,937 us /zero overlaps. Genealogy and all
31 baseline/final checks are restored. The [offline correction]({prep}) honors
logical primitive-array tiers and brackets server processing from worker
receipt, including queue time. Replay reduces 990→810 reads with 976 identical
consumed values/types; 665 HMI tests pass /12 skipped. Source ages, freshness,
row proofs and retries are preserved. Native improvement remains unproven;
fresh session approval is required. Unchanged PLC retains 2,339 tests and 65%
Capacity. V2/Part III inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [next diagnostic]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [timing attempt]({runtime}) passes 41 cases/87 exact replays and 2,035
observer samples: 2,033 entirely Good, two with Uncertain rows, zero Bad.
Desktop initially LIVE then fails overview at 1,169.283 ms. Worker acquisition
is 873.556 ms, queue 50.904 ms and frontend validation 0.001 ms. TASK maximum is
8,937 us /zero overlaps. Genealogy and all 31 baseline/final checks are restored.
Full acquisition/desktop/final scan acceptance remains open.

The [offline tier/queue correction]({prep}) classifies primitive-array logical
elements from published bounds/indices and schedules only consumed tiers.
Excluded arrays cause no cyclic reads; all-consumed-slow groups use the existing
heartbeat; fast consumers and explicit target reads retain their behavior.
The response-processing bracket starts at worker request receipt and includes
queue time through the original age boundary, per the transport envelope.
Source timestamps, Good/expiry limits, row proof and retries do not change.
Recorded replay reduces 990→810 reads and preserves 976 consumed values/types.
665 HMI tests pass /12 skipped; native improvement remains unproven. The PLC
image/65% Capacity and both v38 gates are unchanged. A fresh session needs
current approval. V2/Part III remain inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner='C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01/qualification_session_v2.py',
 lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptFailure='Desktop initially LIVE then STALE after overview at 1169283 us; zero accepted views',
 observerSamples=2035,observerNonBadSamples=2035,observerAllGoodSamples=2033,allGoodSamples=2033,
 samplesWithUncertainRows=2,scanCumulativeMaxUs=8937)
v['offlineGates']['flutterTests']=665;v['offlineGates']['arrayTierRegressionTests']=5
v['nativeLookupFreshness'].update(medianAgeMs=309.58,maxAgeMs=997.151,maxAcceptedRowWindowUs=9959)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=2035,observerAllGood=False,fullFixturePassed=True)
v['desktopLatestCoverage'].update(q['desktopCoverage']);v['desktopLatestCoverage'].update(initialLiveModules=7,failedAt='after-overview')
v['latestDesktopAgeComponents']=q['desktopFreshnessDiagnostics']['observations'][0]
v['partReadDiagnostic'].update(latestRuntimeEvidence=runtime,calls=218,successfulCalls=218,failedCalls=0,attempts=223)
v['desktopTimingDiagnostic'].update(prepared=False,completed=True,authorized=False,approvalConsumed=True,runtimeEvidence=runtime)
v['tierQueueCorrection']=dict(implementedOffline=True,nativeAccepted=False,nativeSessionAuthorized=False,
 logicalPrimitiveArrayLeaves=True,consumedLeavesGovernGroupTier=True,excludedArraysNotCyclic=True,
 slowHeartbeatPreserved=True,fastConsumersPreserved=True,targetedBypassPreserved=True,
 responseClockStartsAtWorkerReceipt=True,sourceTimestampsChanged=False,freshnessLimitsChanged=False,
 rowProofChanged=False,retryLimitsChanged=False,readOnlyPolicyChanged=False,logicalValuesOrTypesChanged=False,
 replayReadsBefore=990,replayReadsAfter=810,replayGroupsBefore=297,replayGroupsAfter=237,
 replayHiddenByClassBefore=60,replayHiddenByClassAfter=0,replayConsumedValuesAndTypes=976,
 newTests=5,focusedTests=53,hmiMirrorInputs=319,changedExistingHmiFiles=3,addedHmiFiles=1)
v['acceptancePending']=['Native tier/queue correction qualification and strict live desktop coverage',
 'Independent pages/idle/generic acquisition','Final candidate scan timing','Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b timing run passes 41 cases/87 replays/2035 samples (2033 Good, two Uncertain). Desktop initially LIVE then STALE at 1169.283 ms. Genealogy/31 baseline restored. Offline array-tier and worker-queue bracket corrections pass 665 HMI tests; native acceptance remains open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated completed timing outcome and unapproved tier/queue correction status; no controller access or activation.')
