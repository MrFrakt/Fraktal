"""Record the completed short attempt and the unapproved apparatus-only follow-up."""
from pathlib import Path
import json

R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley'
W=Path(__file__).parent
A=Path('C:/work/fraktal-ab-s4b-array-tiers-20261027/session_01')
q=json.loads((A/'runtime_summary_01.json').read_bytes())
assert q['candidateCases']==0 and q['pairedCapturesReplayed']==1 and q['observerSamples']==49
assert q['allGoodSamples']==49 and q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert not q['nativeAccepted'] and q['authorizationConsumed']
runtime='Evidence/AB_S4B_TIER_QUEUE_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_BUSY_WITNESS_PREPARATION_2026-10-27.md'
body=f'''**Latest, 2026-10-27: the tier/queue attempt stops at the transient-login check; genealogy is restored.**
The [sealed attempt]({runtime}) stops before a completed regression row at
`bounded login must be observed busy`. Its full comparison is exact on **5,199
paths** and independently replays from raw reads. Canonical and legacy Access
both show `LoginBusy=false`, `LoginFailed=true`, `LoginResultSequence=1`,
`CurrentLevel=0`: the full capture sampled completed refusal. This does not prove
missing PLC publication; request-to-capture latency and the precise miss cause
were not measured. All earlier failed attempts remain sealed separately.

The corrected four-connection Dart reader completes **49 entirely Good samples**,
four configuration queries and targeted detail reads. Sample age median/p95/max
is **275.568 /413.967 /438.839 ms**; maximum accepted row window **9,109 us**.
These short-run observations do not establish full workload performance.
Strict desktop, independent configuration comparison, idle equivalence, generic
acquisition and final candidate timing are **skipped**. Read-only TASK maximum
is **7,752 us /zero overlaps** during the recorded short epoch. Genealogy, five
original documents, **31/31 baseline** and all final/preflight checks pass.
The approved session is complete and its authorization consumed. S4b is open.

The [apparatus-only follow-up]({prep}) warms two public scalar paths before
the existing first login. Immediately after its existing acknowledgement, it
compares canonical BOOL and legacy DINT `LoginBusy` within the existing equal-
even entire-scan proof (100 polls/five seconds). Both must be busy and equivalent.
The inherited full comparison then runs, retaining its actual later state;
its failure still stops the fixture. All 41 cases, 87 expected full pairs,
negative-login refusal, exact restoration and cleanup remain required.
**14 focused tests pass**, including missed-busy, mismatched values, changed/
odd/frozen counters, invalid types/replies and a later full-comparison failure.
Six Part trace tests and fresh SDK/authorization/workflow/readiness/refusal gates
pass. No additional PLC writes, shipping client or PLC changes are introduced.

Unchanged shipping inputs retain **665 HMI tests passed /12 skipped**, 53 focused
tests, analyzer/Windows/enforced lockfile with Flutter **3.47.5 /Dart 3.13.4**
and the identical **319-input mirror**. The tier/queue changes honor logical
primitive-array consumption and include worker queue time in server processing;
source ages, Good/expiry limits, row proofs and retry/deadline remain unchanged.
Replay retains **990 to 810 reads**, **297 to 237 groups**, **60 to zero** hidden
ByClass reads and **976 identical consumed values/types**. All **373 PLC/gate
bindings**, **2,339 AB tests**, both v38 build/read-back/access/SDK gates and
**65% Capacity** transfer by hashes. Root checks and **74 root tests** pass.

A fresh same-image session is prepared and **not authorized**: fresh guards/
backup, MANUAL normalization if needed, Program/download/Run, the inherited
41 cases with the short read-only busy witness and concurrent Dart observation,
TASK monitoring, strict desktop and remaining comparisons/acquisition/scan if
ready, then genealogy/original documents/31 baseline/final checks. Native
acceptance remains unproven. V2/Part III inactive; no commit/push. S5 gateway/
installer, S6 retirement/persistence/events/capacity and S7 physical/CIP Security
including real I/O remain.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Tier/queue attempt]({runtime}) stops at the missed transient busy observation
before a completed case. One full 5,199-path pair replays exactly; 49 Dart
samples are entirely Good and four configuration queries complete. Desktop,
independent configuration/idle/full acquisition/final timing are skipped.
TASK maximum is 7,752 us /zero overlaps in the short epoch. Genealogy/31 baseline/
final checks pass. The [prepared follow-up]({prep}) adds an immediate same-scan
busy witness before the unchanged later full comparison; 14 tests pass.
Shipping client/PLC, 665 HMI/12 skipped, 2,339 AB and 65% Capacity are unchanged.
Fresh current session authorization is required; prior approval is consumed.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** The [tier/queue attempt]({runtime})
stops at the missed transient login-busy observation before a completed case.
One 5,199-path pair replays exactly: both Access representations show completed
unknown-user refusal. The Dart reader completes 49 entirely Good samples and
four configuration queries; median/max age 275.568/438.839 ms. Desktop and full
acquisition/final timing are skipped. Short TASK epoch maximum 7,752 us /zero
overlaps. Genealogy/31 baseline/all final checks pass; authorization is consumed.
The [prepared read-only witness]({prep}) checks both busy values under the
existing scan proof immediately after acknowledgement, then retains the full
later comparison. Fourteen tests pass. Shipping HMI/PLC and their gates are
unchanged: 665 HMI/12 skipped, 2,339 AB and 65% Capacity transfer by hashes.
Native acceptance remains unproven; fresh approval is required. V2/Part III
inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [timing attempt]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [tier/queue attempt]({runtime}) stops at the transient login-busy
observation before a completed case. Its full comparison/replay is exact on
5,199 paths and samples completed refusal in both Access representations.
Forty-nine Dart samples are entirely Good; four configuration queries complete.
Desktop, independent configuration/idle/full acquisition/final timing are
skipped. Short TASK epoch maximum 7,752 us /zero overlaps. Genealogy/31 baseline/
all final checks pass; the authorization is consumed. S4b remains open.

The [apparatus-only follow-up]({prep}) proves canonical/legacy busy values
under the existing equal-even scan guard immediately after acknowledgement,
before the retained full comparison. Fourteen tests pass; the full comparison
can still fail. No PLC writes, shipping source, row proofs/retries, source ages
or freshness limits change. The shipping tier/queue correction and its 665 HMI
tests/12 skips remain hash-bound, with both v38 gates/65% Capacity unchanged.
Native acceptance requires a fresh authorized session. V2/Part III inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner=(W.parent/'session_01/qualification_session_v2.py').as_posix(),
    lastAttempt=runtime,latestRuntimeEvidence=runtime,
    lastAttemptFailure='Transient login busy not observed by the full capture; both sides show completed refusal',
    observerSamples=49,observerNonBadSamples=49,observerAllGoodSamples=49,allGoodSamples=49,
    samplesWithUncertainRows=0,scanCumulativeMaxUs=7752,
    candidateCases=0,pairedCapturesReplayed=1,nativeAccepted=False,currentSessionAuthorized=False)
v['nativeLookupFreshness'].update(medianAgeMs=275.568,maxAgeMs=438.839,maxAcceptedRowWindowUs=9109)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=49,observerAllGood=True,fullFixturePassed=False)
v['desktopLatestCoverage']=q['desktopCoverage']|dict(skipped=True,reason='Candidate stopped at login-busy observation')
v['latestDesktopAgeComponents']=None
v['partReadDiagnostic'].update(latestRuntimeEvidence=runtime,calls=0,successfulCalls=0,failedCalls=0,attempts=0,skipped=True)
v['tierQueueCorrection'].update(nativeAccepted=False,nativeSessionAuthorized=False,runtimeEvidence=runtime,
    nativeSessionCompleted=True,approvalConsumed=True,shortRunOnly=True)
v['loginBusyWitness']=dict(prepared=True,authorized=False,nativeAccepted=False,sessionOnly=True,
    readOnly=True,canonicalLegacySameScan=True,existingProofBudgetUnchanged=True,
    fullComparisonRetained=True,originalCases=41,expectedFullPairs=87,focusedTests=14,
    shippingSourceChanged=False,additionalPlcWrites=False,preparation=prep)
v['acceptancePending']=['Full 41-case/87-pair workload with immediate busy witness',
    'Strict live desktop coverage','Independent pages/idle/generic acquisition',
    'Final candidate scan timing','Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b tier/queue attempt stops at transient login-busy capture before a completed case. One exact 5199-path replay/49 all-Good Dart samples; desktop/full acquisition skipped. Genealogy/31 baseline restored. Same-image read-only busy-witness retry prepared with 14 tests; shipping 665 HMI/12 skipped, 2339 AB and 65% Capacity unchanged.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated completed attempt and unapproved witness preparation; no activation or controller access.')
