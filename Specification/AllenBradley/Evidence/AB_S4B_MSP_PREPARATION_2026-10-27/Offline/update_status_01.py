"""Record the refill attempt and the proof-preserving body-packet preparation."""
from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
C=Path('C:/work/fraktal-ab-s4b-refill-20261027/session_01')
q=json.loads((C/'runtime_summary_01.json').read_bytes())
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['allGoodSamples']==q['observerSamples']==3144
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and q['authorizationConsumed']
assert not q['nativeAccepted'] and q['loginBusyWitness']['passed']
assert json.loads((W/'flutter_02_exit.json').read_bytes())['exitCode']==0
assert b'685 ~12: All tests passed!' in (W/'flutter_02.log').read_bytes()
replay=json.loads((W/'wire_replay_01.json').read_bytes())
runtime='Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md'
timing='Evidence/AB_S4B_HOST_TIMING_2026-10-27.md'
prep='Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md'
body=f'''**Latest, 2026-10-27: refill preserves the workload; desktop remains open; body batching is prepared.**
The [sealed refill attempt]({runtime}) passes **41/41 cases**, **87/87 exact
independent raw-record replays** (4,799–5,407 paths), the separate busy witness
and **3,144 entirely Good Dart samples** (zero Uncertain/Bad). Observer age
median/p95/max is **265.8085 /337.691 /523.733 ms**, maximum accepted row window
**9,995 us**. Four configuration queries/targeted details complete; all 218 Part
calls succeed in 222 attempts. Desktop initially LIVE with seven modules then
fails `after-overview`: source **996,563 us**, RPC **1,610,859 us**, server bracket
**1,183.292 ms**, transit **428,567 us**, received **1,425,130 us**, local **3,015 us**,
effective **1,428,145 us** against **1,000,000 us**. Worker acquisition is
**1,125,722 us**, queue **50,819 us**, projection **2,452 us**, path expansion
**18,215 us**, frontend validation **2 us**. These measured intervals do not
isolate a host/network/PLC cause. Zero views are accepted. Independent
configuration/idle/generic acquisition/final timing are skipped. TASK maximum
**9,003 us /zero overlaps** is observational, not final scan acceptance.
Genealogy/five original documents/**31/31 baseline**/all final/preflight checks
pass. The completed session's authorization is consumed. S4b remains open.

The [read-only timing controls]({timing}) read the restored baseline. Scalar
request medians are **0.891 ms** (Dart CLI), **1.120 ms** (Flutter without widgets),
**1.2765 ms** (simulator UI); Flutter maxima **13.073 /16.290 ms** can exceed
the 10 ms proof window. They do not establish the cause of prior refusals.
Python and Dart each validate 20 native MSPs/60 reads. One Dart packet spans
a sample-counter change, so packet atomicity is not assumed. No tag writes,
mode/download/clear/clock/power changes occur. These are not canonical/UI acceptance.

The [prepared MSP correction]({prep}) batches only the count/body reads of a
fitting row **between separately completed pre/post counter requests**. No
MSP execution-order guarantee is assumed; reversed-body execution retains exact
golden values/types and verified outer bracketing. An earlier counter-folding
prototype is archived but excluded. Every embedded service is a bounded symbolic
Read Tag Fragmented request to the Message Router; nested/write/connection-manager
wrappers are refused. Queued bytes are copied before validation and queuing. All reply
counts/offsets/services/types/handles/extents are strict. Large or data-dependent
primitive rows keep the original reader. Unsupported or partial transfers fall
back inside the original attempt/window/deadline; malformed replies refuse.
The existing equal-even/elapsed-window proof, 20 attempts/one second, source
ages, fast 1/3 s and slow 7.5/15 s Good/expiry limits remain unchanged. Read-only
policy, four-row refill/leases and count/Status barriers remain.

**685 HMI tests pass /12 skipped**, **73 focused tests**, analyzer/Windows/
enforced lockfile on Flutter **3.47.5 /Dart 3.13.4**, identical **320-input mirror**.
Four existing HMI source/test files change and one 16-case module is added;
the existing pool test adds queued-input mutation coverage. Recorded-wire replay
uses **{replay['packetRequests']} packets** for **{replay['wireReads']} logical reads**
and **{replay['groups']} groups**, preserving all **976 consumed values/types**.
These are model counts, not native full-tree timing. Fourteen busy-witness/six
Part trace tests, fresh SDK/authorization/workflow/readiness/refusal gates and
**74 root tests** pass. All **373 PLC/gate bindings**, **2,339 AB tests**, both v38
build/read-back/access/SDK gates and **65% Capacity** transfer by hashes.

A fresh same-image session is prepared and **not authorized**: fresh guards/
backup, MANUAL normalization if needed, Program/download/Run; inherited 41 cases
with the proven busy witness and corrected read-only observer, existing traces/
TASK monitoring; strict desktop and remaining comparisons/acquisition/scan if
ready; genealogy/original documents/31 baseline/final checks. No new PLC writes.
Fault/TASK-counter clears, clock/power/vendor-state operations are excluded.
Native improvement remains unproven; V2/Part III inactive; no commit/push.
S5 gateway/installer, S6 retirement/persistence/events/capacity and S7 physical/
CIP Security including real I/O remain.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Refill attempt]({runtime}) passes 41 cases/87 replays, the busy witness and
3,144 entirely Good samples. Desktop becomes STALE after overview at 1,428.145 ms;
later acquisition/final timing are skipped. TASK maximum 9,003 us /zero overlaps.
Genealogy/31 baseline/all final checks pass; authorization consumed. [Read-only
controls]({timing}) record Flutter scalar tails above 10 ms without isolating
the prior failure cause. The [MSP preparation]({prep}) batches only body/count
reads between separate counters, preserving proofs/freshness/read-only policy.
685 HMI/12 skips and 73 focused tests pass; native qualification needs approval.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** [Refill qualification]({runtime})
passes 41 cases/87 exact replays, the busy witness and 3,144 entirely Good
samples. Desktop initially LIVE then STALE after overview at 1,428.145 ms.
TASK maximum 9,003 us /zero overlaps; genealogy/31 baseline/final checks pass.
The [read-only controls]({timing}) establish packet support and long scalar
tails, not the precise failure cause or canonical acceptance. The [prepared
MSP path]({prep}) batches body/count reads between separate counter requests,
with strict read-only/type/extent validation and original proof/freshness limits.
No intra-packet ordering assumption. 685 HMI/12 skips and 73 focused tests pass.
Native improvement remains unproven; fresh approval required. Unchanged PLC
retains 2,339 tests/65% Capacity by hashes. V2/Part III inactive; S5-S7/physical
I/O remain. See the [plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [busy-witness attempt]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [refill attempt]({runtime}) passes 41 cases/87 exact replays, the busy
witness and 3,144 entirely Good samples. Desktop initially LIVE then STALE at
1,428.145 ms; later acquisition/final timing skipped. TASK maximum 9,003 us /
zero overlaps. Genealogy/31 baseline/final checks pass; approval consumed.
S4b remains open. The [read-only diagnostic]({timing}) establishes MSP support,
not atomicity or canonical acceptance. The [prepared client]({prep}) batches
only body/count reads between separately completed counter requests, retaining
all value/type/proof/freshness/read-only rules and the original fallback.
685 HMI/12 skips, 73 focused, analyzer/Windows/locked dependencies and 74 root
tests pass. Native qualification needs new approval. No PLC/source/layout or
Capacity change; V2/Part III remain inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner=(W.parent/'session_01/qualification_session_v2.py').as_posix(),
    lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptFailure='Desktop initially LIVE then STALE after overview at 1428145 us',
    observerSamples=3144,observerNonBadSamples=3144,observerAllGoodSamples=3144,allGoodSamples=3144,
    samplesWithUncertainRows=0,scanCumulativeMaxUs=9003,candidateCases=41,pairedCapturesReplayed=87,
    nativeAccepted=False,currentSessionAuthorized=False)
v['offlineGates'].update(flutterTests=685,mspRegressionTests=16)
v['nativeLookupFreshness'].update(medianAgeMs=265.8085,maxAgeMs=523.733,maxAcceptedRowWindowUs=9995)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=3144,observerAllGood=True,fullFixturePassed=True)
v['desktopLatestCoverage']=q['desktopCoverage']|dict(skipped=False,initialLiveModules=7,failedAt='after-overview')
v['latestDesktopAgeComponents']=q['desktopFreshnessDiagnostics']['observations'][0]
v['partReadDiagnostic'].update(latestRuntimeEvidence=runtime,calls=218,successfulCalls=218,failedCalls=0,attempts=222,skipped=False)
v['rowRefillCorrection'].update(nativeAccepted=False,nativeSessionAuthorized=False,
    nativeSessionCompleted=True,approvalConsumed=True,runtimeEvidence=runtime)
v['loginBusyWitness'].update(authorized=False,nativeAccepted=True,runtimeEvidence=runtime,
    approvalConsumed=True,generation=q['loginBusyWitness']['generation'],polls=q['loginBusyWitness']['attempts'])
v['readOnlyMsp']=dict(implementedOffline=True,nativeAccepted=False,nativeSessionAuthorized=False,
    bodyOnly=True,separateCompletedCounters=True,intraPacketOrderAssumed=False,
    maximumEmbeddedReads=64,maximumConnections=4,requestAndReplyBudgets=True,
    exactTypedReplies=True,writeAndNestedWrappersRefused=True,queuedInputCopied=True,
    originalFragmentedFallback=True,attemptAndWindowPreserved=True,sourceAgesChanged=False,
    freshnessLimitsChanged=False,logicalValuesOrTypesChanged=False,plcImageChanged=False,
    hmiTests=685,focusedTests=73,hmiMirrorInputs=320,changedExistingHmiFiles=4,addedHmiFiles=1,
    baselinePacketSupport=True,nativeCanonicalQualificationPending=True,hostTimingEvidence=timing,
    replayPacketRequests=replay['packetRequests'],replayLogicalReads=replay['wireReads'],
    replayConsumedValuesAndTypes=976,preparation=prep)
v['acceptancePending']=['Native body-packet qualification and strict live desktop coverage',
    'Independent pages/idle/generic acquisition','Final candidate scan timing',
    'Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b refill passes 41 cases/87 replays and 3144 all-Good samples; desktop becomes STALE at 1428.145 ms. Genealogy/31 baseline restored. Body-only MSP between separate counters passes 685 HMI/12 skips and 73 focused offline; native acceptance remains open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated completed refill, read-only controls and unapproved body-packet preparation; no activation/controller access.')
