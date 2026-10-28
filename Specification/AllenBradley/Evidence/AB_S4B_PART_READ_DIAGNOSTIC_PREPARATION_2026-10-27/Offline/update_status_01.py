from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
runtime='Evidence/AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_PART_READ_DIAGNOSTIC_PREPARATION_2026-10-27.md'
q=json.loads(Path('C:/work/fraktal-ab-s4b-pool-20261027/session_01/runtime_summary_01.json').read_bytes())
assert q['candidateCases']==25 and q['observerSamples']==1288 and q['pairedCapturesReplayed']==53
assert not q['nativeAccepted'] and q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed']
assert json.loads((W/'part_trace_tests_01_exit.json').read_bytes())['exitCode']==0
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+f'''**Latest, 2026-10-27: parallel observer passes its partial workload; legacy Part read stops the fixture.**
The [parallel-reader attempt]({runtime}) completes **25/41 cases**: 15 main,
two Access and eight configuration/set-store. The legacy Part reader then
refuses the SFC adopted-fault record: `part snapshot changed during every
bounded read`. Its original three-attempt rule remains enforced. All **53
completed paired captures** replay independently, exactly on 4,799–5,407 paths.
The full 41-case/87-pair exit gate is not met.

The four-connection Dart observer completes **1,288 entirely Good samples**,
zero Bad/Uncertain, all four configuration page queries and targeted details.
Sample age median/p95/max is **295.514 /385.779 /493.517 ms**. Maximum accepted
row window is **9,965 us**, below the published 10,000 us. This shorter run is
partial workload evidence, not a controlled comparison with earlier runs.
Desktop, independent page comparison, idle/generic acquisition and final scan
are **not reached** after the fixture refusal. The initial desktop boundary
measured previously at 1,003.130 ms remains unqualified with this reader.
TASK monitoring records **8,994 us maximum /zero overlaps** through 4,303 valid
candidate observations. No counters are cleared. Genealogy, the five exact
original documents, **31/31 baseline**, policy, MANUAL/idle/logout and all
final checks/preflight are restored. The session approval is consumed.

The failed Part read does not record its before/body/after revisions or request
timings. No contention, counter or publisher cause is inferred. The
[Part-read diagnostic preparation]({prep}) adds session-only instrumentation
around the **unchanged original legacy Part reader**. It records only the
schema/revision words, before/body/after phase, attempt and per-read/call
timing, including trace overhead. No payload/UID/PIN is recorded. The original
function still owns requests, attempts, projection and rejection. No added PLC
requests, retries, write vectors or acceptance changes. Logging adds overhead;
the next run may reproduce the refusal rather than establish acceptance.

**Six tracing tests** pass, covering exact return/error preservation, unchanged
request counts/arguments/attempts, payload exclusion, evidence overwrite refusal
and restoration of the original function. Shipping HMI/PLC inputs are unchanged:
**660 HMI tests /12 skipped**, analyzer/Windows/enforced lockfile using Flutter
**3.47.5 /Dart 3.13.4**, all 318 mirror inputs; **2,339 AB tests**, both v38
build/read-back/access/SDK gates and **65% Capacity** transfer by hashes through
all 373 unchanged PLC/gate bindings. Fresh SDK, 16 authorization refusals,
eight workflow, six readiness and both read-only helper refusals pass without
controller access. Root gates and 74 tests pass.

The fresh diagnostic session is prepared and **not authorized**: same guards/
backup, MANUAL normalization if needed, Program/download/Run, five-document
restore/41 cases with four-connection observer and Part tracing, 100 ms TASK
monitor, strict desktop and remaining reads/scan if ready, then genealogy/
original documents/31 baseline/final checks. Fault/TASK-counter clears, clock
changes and power/vendor-state operations remain excluded. S4b remains open;
V2/Part III inactive; no commit/push. S5 gateway/installer, S6 migration/
retirement/persistence/events/capacity, S7 physical/CIP Security and real I/O remain.

'''+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Parallel-reader attempt]({runtime}) records **25/41 cases, 53 exact completed
replays and 1,288 entirely Good observer samples**. The legacy Part reader
refuses its three bounded attempts at the SFC adopted-fault record; desktop,
full acquisition and final timing are not reached. TASK trace maximum is
8,994 us /zero overlaps. Genealogy/31 baseline/final checks are restored;
authorization is consumed. [Session-only Part tracing]({prep}) is prepared
without changing shipping code, requests, attempts or acceptance rules.
Full native reader, desktop and scan acceptance remain open; physical/CIP
Security and later stages remain separate.

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3's Echo exit and S4a pass. S4b remains open.** The
[parallel-reader attempt]({runtime}) completes 25/41 cases and 53 exact raw
replays. The observer records 1,288 entirely Good samples at 295.514 ms median /
493.517 ms maximum age. The legacy Part reader then refuses its three bounded
reads during the SFC adopted-fault record. This is partial workload proof;
desktop/full acquisition/final timing are not reached. TASK maximum is 8,994 us
with zero overlaps. Genealogy, exact original documents and all 31 baseline/
final checks are restored. The [next diagnostic]({prep}) instruments the
unchanged Part reader's revisions/timing, with no added requests, retries,
write vectors or acceptance changes. Six tracing tests pass. Shipping code is
unchanged: 660 HMI tests /12 skipped, 2,339 AB tests and 65% Capacity transfer
by hashes. Fresh session approval is required. V2/Part III remain inactive;
S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [parallel-reader preparation]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [parallel-reader attempt]({runtime}) adds a bounded pool of four
serial-pinned read-only connections, keeping a full row proof on one connection
and at most one request outstanding per socket. Count barriers and revision
ordering protect out-of-order replies. It records 1,288 entirely Good samples,
295.514 ms median /493.517 ms maximum age and 25/41 fixture cases, with 53 exact
raw-record replays. The legacy Part reader refuses its three bounded reads at
the SFC adopted-fault record; desktop/full acquisition/final timing are not
reached. TASK trace maximum is 8,994 us /zero overlaps. Genealogy, original
documents and 31 baseline/final checks are restored. Full S4b acceptance is open.

The [session-only Part diagnostic]({prep}) records schema/revision words and
timing around the unchanged original reader. No UID/payload/PIN is recorded;
no requests, attempts, write vectors, freshness or acceptance rules change.
Logging has overhead and may reproduce the refusal. Six tracing tests pass;
unchanged shipping inputs retain 660 HMI tests /12 skipped, 2,339 AB tests,
both v38 gates and 65% Capacity by hashes. A new session needs current approval.
V2/Part III remain inactive.

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner='C:/work/fraktal-ab-s4b-partdiag-20261027/session_01/qualification_session_v2.py',
 lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptCandidateCases=25,
 lastAttemptFailure='Legacy Part reader refused all three bounded attempts during SFC adopted-fault record; 25/41 cases completed; desktop not reached',
 candidateChecksPassed=False,pairedCapturesReplayed=53,observerSamples=1288,observerNonBadSamples=1288,
 observerAllGoodSamples=1288,allGoodSamples=1288,samplesWithUncertainRows=0,activeWorkloadObserverPassed=False,
 observerCapturePassed=True,desktopStageReached=False,desktopPrimaryFailure=None,desktopSecondaryFailure=None,
 scanCumulativeMaxUs=8994,partialFixture=q['partialFixtureProof'])
v['nativeLookupFreshness'].update(medianAgeMs=295.514,maxAgeMs=493.517,maxAcceptedRowWindowUs=9965)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,nativeSessionAuthorized=False,sessionApprovalConsumed=True,
 observerSamples=1288,observerAllGood=True,fullFixturePassed=False)
v['desktopLatestCoverage'].update(error=None,primaryError=None,primaryBoundary=None,helperSecondaryError=None,
 stageReached=False,localWriteRefusals=None)
v['partReadDiagnostic']=dict(prepared=True,authorized=False,sessionOnly=True,shippingCodeChanged=False,
 originalReaderUnchanged=True,requestCountChanged=False,attemptBudgetChanged=False,acceptanceChanged=False,
 fields=['schemaVersion','dataRevision','phase','attempt','elapsedUs'],payloadOrUidRecorded=False,
 traceOverheadIncluded=True,tests=6,nativeCauseConfirmed=False)
v['acceptancePending']=['Identify legacy Part read refusal under four-connection workload',
 'Complete 41-case/87-pair workload gate','Strict live desktop coverage',
 'Independent pages/idle/generic acquisition','Final candidate scan timing',
 'Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b parallel observer has 1288 entirely Good samples and 25/41 cases/53 exact completed replays. Legacy Part bounded read refusal stops the fixture before desktop. Genealogy/31 baseline restored; session-only Part tracing prepared. Full native S4b remains open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated partial S4b outcome and unapproved diagnostic status; no controller access or contract activation.')
