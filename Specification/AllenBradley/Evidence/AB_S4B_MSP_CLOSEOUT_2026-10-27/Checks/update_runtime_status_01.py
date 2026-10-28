"""Record completed body-only qualification; keep failed desktop acceptance open."""
from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
S=W.parent/'session_01';load=lambda p:json.loads(Path(p).read_bytes())
q=load(S/'runtime_summary_01.json');seal=load(W/'sealed_runtime_01.json')
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87
assert q['observerSamples']==q['allGoodSamples']==2851 and q['activeWorkloadReaderPassed']
assert not q['nativeAccepted'] and not q['desktopAccepted']
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert q['authorizationConsumed'] and not q['currentControllerChangesAuthorized']
runtime='Evidence/'+Path(seal['report']).name
prep='Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md'
fresh=q['desktopFreshnessDiagnostics']['observations'][0]
assert fresh['effectiveAgeUs']==1051723 and fresh['fastGoodUs']==1000000
body=f'''**Latest, 2026-10-27: body packets improve the observer; desktop acceptance remains open.**
The [sealed body-packet attempt]({runtime}) completes **41/41 candidate cases**,
**87/87 independently replayed exact pairs** (4,799–5,407 paths), the separate
same-scan login-busy witness and **2,851 entirely Good Dart samples** (zero
Uncertain/Bad). Median/p95/max observer age is **209.959 /259.133 /346.397 ms**;
RPC median **220,433 us**, maximum accepted row window **9,998 us**. Four
configuration queries/targeted details complete. All **218 Part calls** pass
in **226 attempts**. The native-proven packet path batches count/body reads
between separately completed counter requests, with no ordering/atomicity
assumption and unchanged source ages, row proofs, retry/freshness limits or
write vectors. This proves the recorded workload, not full S4b acceptance.

Strict desktop initially LIVE with seven modules then refuses `after-overview`:
source **737,967 us**, RPC **1,107,987 us**, server bracket **799.297 ms**, transit
**309,690 us**, received **1,047,657 us**, local **4,066 us**, effective
**1,051,723 us** against **1,000,000 us**. Excess **51,723 us**. The corresponding
worker acquisition is **745,588 us**, queue **50,723 us**, projection **5,642 us**,
path expansion **19,430 us**, frontend validation **1 us**. These measured
intervals do not isolate a precise host/network/PLC cause. Zero views are
accepted. The complete reader/configuration/idle/generic/final scan gates remain
open; later workflow stages are skipped after this first failure.

Read-only TASK maximum is **9,002 us /zero overlaps**, not final scan acceptance.
Genealogy/five original documents/**31/31 baseline**/all final/preflight checks
pass; baseline median **99 us**, maximum **1,166 us**, zero overlaps. No dumps,
fault/TASK-counter clears, clock/power/vendor-state changes or Echo hard kills.
Only the SDK-saved working ACD differs among **1,081** frozen inputs. All shipping
PLC/HMI inputs remain unchanged during the run. The current authorization is
consumed; no new controller-changing session is prepared or authorized.

Compared with the [refill attempt](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md),
observer median age falls from **265.8085 to 209.959 ms**, and the recorded desktop
refusal falls from **1,428.145 to 1,051.723 ms**. These are different sessions,
not a controlled causal benchmark; the desktop still fails. The [preparation]({prep})
binds **685 HMI tests /12 skips**, **73 trace-enabled focused tests**, analyzer,
Windows build and enforced lockfile on **Flutter 3.47.5 /Dart 3.13.4**, a matching
**320-input mirror**, and model replay **711 packets /810 logical reads /237
groups /976 exact consumed values/types**. All **373 PLC/gate bindings**, **2,339
AB tests**, both v38 build/read-back/access/SDK gates and **65% Capacity** transfer
by hashes. Fourteen busy-witness/six Part-trace tests and 74 root tests pass.

**Next:** evaluate how to reduce the remaining cold-desktop acquisition/delivery
cost offline, using the recorded timings and exact consumed path set. Any
coalescing must retain each row's published counter binding, external completed
counter reads, count/Status barriers and original deadlines/age rules. Establish
an offline counterexample and packet/value/type proof before preparing another
native qualification. Fresh exact-session authorization remains required.
S4b desktop/full configuration/acquisition/final scan is open. S5 gateway/Web/
installer, S6 retirement/persistence/events/capacity and S7 physical/CIP Security
including real I/O remain. V2/Part III inactive; no commit/push.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Body-packet attempt]({runtime}) passes 41 cases/87 replays and the busy witness;
2,851 entirely Good samples, median age 209.959 ms. Strict desktop is STALE after
overview at **1,051.723 ms** against 1,000 ms; zero views accepted. Later
configuration/idle/generic/final timing skipped. TASK maximum 9,002 us /zero
overlaps is observational. Genealogy/31 baseline/final checks pass; authorization
consumed. Shipping inputs unchanged; 685 HMI/12 skips, 73 focused and 74 root
tests pass. Offline reduction of the remaining acquisition/delivery cost is next;
no subsequent download is authorized. Full acceptance remains open.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** The [body-packet attempt]({runtime})
passes 41 cases/87 exact replays, the busy witness and 2,851 entirely Good Dart
samples, median age 209.959 ms. Counts/body are batched between separate completed
counter reads; no MSP ordering/atomicity assumption. Strict desktop initially
LIVE then STALE after overview at **1,051.723 ms** against 1,000 ms. Precise delay
cause remains unisolated; later acquisition/final timing skipped. TASK maximum
9,002 us /zero overlaps; genealogy/31 baseline/final checks pass. Approval consumed.
Offline acquisition/delivery reduction is next, preserving proofs/freshness.
685 HMI/12 skips, 73 focused and 74 root tests pass; unchanged 373 PLC/gate
bindings retain 2,339 AB tests/65% Capacity by hashes. V2/Part III inactive;
S5-S7/physical I/O remain. See the [plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [refill attempt]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [body-packet attempt]({runtime}) passes 41 cases/87 exact replays, the
busy witness and 2,851 entirely Good Dart samples. Strict desktop initially LIVE
then STALE at **1,051.723 ms** against 1,000 ms; later acquisition/final timing
skipped. TASK maximum 9,002 us /zero overlaps. Genealogy/31 baseline/final checks
pass; approval consumed. Counts/body batch between separate completed counters;
all value/type/proof/freshness/read-only rules remain. Offline acquisition/
delivery reduction is next; no subsequent controller change is authorized.
685 HMI/12 skips, 73 focused, analyzer/Windows/locked dependencies and 74 root
tests pass. No PLC/layout/Capacity change; V2/Part III remain inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=load(path);v=doc['manifestV68']
v.update(lastAttempt=runtime,latestRuntimeEvidence=runtime,
    lastAttemptFailure='Desktop initially LIVE then STALE after overview at 1051723 us',
    observerSamples=2851,observerNonBadSamples=2851,observerAllGoodSamples=2851,allGoodSamples=2851,
    samplesWithUncertainRows=0,scanCumulativeMaxUs=9002,candidateCases=41,pairedCapturesReplayed=87,
    nativeAccepted=False,currentSessionAuthorized=False)
v['nativeLookupFreshness'].update(medianAgeMs=209.959,maxAgeMs=346.397,maxAcceptedRowWindowUs=9998)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=2851,observerAllGood=True,fullFixturePassed=True)
v['desktopLatestCoverage']=q['desktopCoverage']|dict(skipped=False,initialLiveModules=7,failedAt='after-overview')
v['latestDesktopAgeComponents']=fresh
v['partReadDiagnostic'].update(latestRuntimeEvidence=runtime,calls=218,successfulCalls=218,failedCalls=0,attempts=226,skipped=False)
v['rowRefillCorrection'].update(nativeAccepted=False,nativeSessionAuthorized=False,nativeSessionCompleted=True,
    approvalConsumed=True,runtimeEvidence=runtime)
v['loginBusyWitness'].update(authorized=False,nativeAccepted=True,runtimeEvidence=runtime,
    approvalConsumed=True,generation=q['loginBusyWitness']['generation'],polls=q['loginBusyWitness']['attempts'])
v['readOnlyMsp'].update(nativeAccepted=False,nativeSessionAuthorized=False,nativeSessionCompleted=True,
    authorizationConsumed=True,activeWorkloadReaderPassed=True,runtimeEvidence=runtime,observerSamples=2851,
    observerAllGood=True,nativeCanonicalQualificationPending=True,strictDesktopAccepted=False)
v['acceptancePending']=['Offline correction and native strict live desktop coverage',
    'Independent pages/idle/generic acquisition','Final candidate scan timing',
    'Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b body packets pass 41 cases/87 replays and 2851 all-Good samples; desktop becomes STALE at 1051.723 ms. Genealogy/31 baseline restored. Authorization consumed; offline acquisition/delivery work remains. 685 HMI/12 skips and 73 focused gates pass; native acceptance remains open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Recorded completed MSP attempt and consumed grant; desktop/full-reader acceptance remains open.')
