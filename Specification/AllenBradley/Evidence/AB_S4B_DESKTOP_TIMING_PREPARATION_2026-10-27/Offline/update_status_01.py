from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
Q=Path('C:/work/fraktal-ab-s4b-partdiag-20261027/session_01')
q=json.loads((Q/'runtime_summary_01.json').read_bytes())
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['observerSamples']==1991
assert q['genealogyRestored'] and q['baselineCases']==31 and q['finalChecksPassed'] and not q['nativeAccepted']
runtime='Evidence/AB_S4B_PART_READ_DIAGNOSTIC_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_DESKTOP_TIMING_PREPARATION_2026-10-27.md'
body=f'''**Latest, 2026-10-27: full observer workload passes; desktop loses freshness after reaching LIVE.**
The [Part-read diagnostic]({runtime}) completes **41/41 cases, 87/87 exact
independent raw-record replays and 1,991 entirely Good observer samples**,
zero Bad/Uncertain. Age median/p95/max is **311.621 /384.682 /528.719 ms**;
maximum accepted row window **9,995 us** remains below 10,000 us. Four read-only
configuration page queries and targeted details complete. All **218 traced
Part calls succeed**, using 229 attempts: 11 header mismatches/parity refusals
are retried by the unchanged original three-attempt reader. Traces include
live and held-oracle reads. The earlier exhausted Part refusal does not recur;
this does not establish its unrecorded cause.

Desktop reaches **LIVE with all seven modules**, then fails `after-overview`
when a new complete sample is refused. **Zero views are accepted**. Timing is
source **906,062 us**, RPC **1,221,541 us**, server bracket **908.841 ms**,
transit **313,700 us**, received age **1,219,762 us**, local processing
**13,590 us**, effective age **1,233,352 us** against **1,000,000 us**. This is
**233,352 us over**; the existing RPC bracket also contains frontend validation
before receipt accounting, so it cannot isolate network/queue/validation cost.
Independent page comparison, idle/generic acquisition and final candidate
timing are skipped. TASK monitoring records **9,002 us maximum /zero overlaps**
through 6,918 candidate observations. Genealogy, the five exact original
documents, **31/31 baseline**, policy, MANUAL/idle/logout and all final checks/
preflight are restored. The approval is consumed. S4b remains open.

The [desktop phase-timing preparation]({prep}) adds diagnostic-only worker
queue, manifest/progress proof, acquisition, projection, age selection,
path expansion, assembly and SendPort delivery timing, including the eight
slowest guarded groups. It logs no values or credentials. Worker tracing is
**off by default**, enabled only in qualification launchers with the compile-time
`fraktal.cip.trace=true` flag. The existing repository refusal log separately
records snapshot wait, service decoding and validation. Original response age
brackets, reads, snapshots, row proofs, retries, freshness and write policy
remain unchanged. Instrumentation adds overhead; native acceptance is not promised.

A recorded V6.8 benchmark measures the existing 5,940-path expansion at
**7,263 us median**, with **256,711 encoded path bytes**. It does not explain
the desktop overrun by itself. No metadata caching or delivery optimization
is implemented. The helper already uses a real-time fully-live binding.

All **660 HMI tests pass /12 skipped**, analyzer/Windows/enforced lockfile with
Flutter **3.47.5 /Dart 3.13.4**; the 318-input mirror matches. Three existing
HMI source/test files change for diagnostics. All **373 PLC/gate bindings**,
2,339 AB tests, both v38 build/read-back/access/SDK gates, 15 byte-identical
prior images and **65% Capacity** transfer by hashes. Fresh SDK, six retained
Part-trace tests, 16 authorization refusals, eight workflow, six readiness and
both read-only helper refusals pass. Root gates and 74 tests pass.

The fresh timing session is prepared and **not authorized**: same guards/
backup, MANUAL normalization if needed, Program/download/Run, five-document
restore/41 cases with traced four-connection observation and Part reads,
100 ms TASK monitoring, strict desktop and remaining checks if ready, then
genealogy/original documents/31 baseline/final checks. Fault/TASK-counter clears,
clock changes and power/vendor-state operations remain excluded. V2/Part III
inactive; no commit/push. S5 gateway/installer, S6 migration/retirement/
persistence/events/capacity, S7 physical/CIP Security and real I/O remain.

'''
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+body+text[end:]
start=text.index('**S4b latest Echo qualification remains open:**');end=text.index('- **New** `HMI/packages/',start)
text=text[:start]+f'''**S4b latest Echo qualification remains open:**
[Part-read diagnostic]({runtime}) completes **41 cases /87 exact replays /
1,991 entirely Good observer samples**. All 218 Part calls succeed. Desktop
reaches LIVE with seven modules, then fails the overview freshness gate at
1,233.352 ms. Zero views are accepted; full acquisition/final timing are skipped.
TASK trace maximum is 9,002 us /zero overlaps. Genealogy/31 baseline/final checks
are restored and authorization is consumed. [Diagnostic-only phase timing]({prep})
is prepared; no reads, row proofs, retry/freshness or acceptance rules change.
Physical/CIP Security and later stages remain separate.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md';text=path.read_text(encoding='utf-8')
start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b desktop acceptance remains open.** The
[Part-read diagnostic]({runtime}) passes 41 cases/87 exact replays and 1,991
entirely Good observer samples, with all 218 traced Part reads succeeding.
Desktop reaches LIVE with seven modules, then becomes STALE during overview
when effective age reaches 1,233.352 ms against the unchanged one-second limit.
Zero views are accepted. Full acquisition/final timing are skipped; TASK trace
maximum is 9,002 us with zero overlaps. Genealogy and all 31 baseline/final
checks are restored. The [next diagnostic]({prep}) separates worker acquisition/
queue/projection/delivery and frontend validation timing, without changing reads,
row proofs, retry or freshness rules. Worker trace is off by default. The
5,940-path benchmark measures 7,263 us median; no caching change is implemented.
660 HMI tests /12 skipped and 74 root tests pass; unchanged PLC retains 2,339
tests and 65% Capacity. Fresh session approval is required. V2/Part III remain
inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md';text=path.read_text(encoding='utf-8')
start=text.index('The [session-only Part diagnostic]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [Part-read diagnostic]({runtime}) completes 41 cases/87 exact replays
and 1,991 entirely Good observer samples. All 218 traced Part calls succeed;
the earlier exhausted refusal is not reproduced or explained. Desktop reaches
LIVE with all seven modules, then fails the overview freshness gate at
1,233.352 ms. Zero views are accepted; full acquisition/final timing are skipped.
TASK trace maximum is 9,002 us /zero overlaps. Genealogy, original documents
and all 31 baseline/final checks are restored.

The [next diagnostic]({prep}) adds worker phase/queue/delivery and frontend
validation timing only. Worker trace is disabled by default and enabled in the
qualification launchers. Snapshot values/types, reads, age calculation, row
proofs, retries, freshness and write policy remain unchanged. Instrumentation
has overhead and may reproduce the refusal. 660 HMI tests pass /12 skipped,
with analyzer/Windows/locked dependencies and root gates. The unchanged PLC
retains 2,339 AB tests, both v38 gates and 65% Capacity by hashes. Fresh
authorization is required. V2/Part III remain inactive.

'''+text[end:];path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner='C:/work/fraktal-ab-s4b-timing-20261027/session_01/qualification_session_v2.py',
 lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptCandidateCases=41,
 lastAttemptFailure='Desktop initially LIVE with seven modules, then STALE after overview: effective age 1233352 us against 1000000 us; zero accepted views',
 candidateChecksPassed=True,pairedCapturesReplayed=87,observerSamples=1991,observerNonBadSamples=1991,
 observerAllGoodSamples=1991,allGoodSamples=1991,activeWorkloadObserverPassed=True,observerCapturePassed=True,
 desktopStageReached=True,desktopPrimaryFailure='Overview complete-sample freshness refusal after initial LIVE',
 desktopSecondaryFailure=None,scanCumulativeMaxUs=9002)
if 'partialFixture' in v:v['previousPartialFixture']=v.pop('partialFixture')
v['nativeLookupFreshness'].update(medianAgeMs=311.621,maxAgeMs=528.719,maxAcceptedRowWindowUs=9995)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['parallelReader'].update(latestRuntimeEvidence=runtime,observerSamples=1991,observerAllGood=True,fullFixturePassed=True)
v['desktopLatestCoverage'].update(q['desktopCoverage'])
v['desktopLatestCoverage'].update(stageReached=True,initialLiveModules=7,failedAt='after-overview',accepted=False)
v['latestDesktopAgeComponents']=q['desktopFreshnessDiagnostics']['observations'][0]
v['partReadDiagnostic'].update(completed=True,prepared=False,authorized=False,approvalConsumed=True,
 latestRuntimeEvidence=runtime,calls=218,successfulCalls=218,failedCalls=0,attempts=229,
 includesLiveAndHeldOracleReads=True,nativeCauseConfirmed=False)
v['desktopTimingDiagnostic']=dict(prepared=True,authorized=False,productionBehaviorChanged=False,
 compileTimeFlag='fraktal.cip.trace',workerTraceDefault=False,qualificationTraceEnabled=True,
 phases=['queue','manifestBefore','progressProof','acquire','manifestAfter','projection','ageSelection','pathExpansion','assembly','send'],
 slowestGroups=8,frontendPhases=['snapshotAwait','serviceDecode','validation'],
 additionalNativeRequests=0,snapshotValuesChanged=False,responseAgeBracketChanged=False,
 proofChanged=False,retryChanged=False,freshnessChanged=False,nativeCauseIsolated=False)
v['acceptancePending']=['Identify desktop acquisition/delivery/validation costs under overview rendering',
 'Strict live desktop coverage','Independent pages/idle/generic acquisition','Final candidate scan timing',
 'Verified genealogy/baseline restoration per new session']
doc['manifestV67']['s4Status']='S4a accepted. S4b passes 41 cases/87 exact replays/1991 entirely Good samples; all 218 Part calls succeed. Desktop initially LIVE then STALE after overview at 1233.352 ms. Genealogy/31 baseline restored; phase-timing diagnostic prepared. Native desktop/full acquisition/final scan remain open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Recorded completed Part diagnostic and unapproved desktop timing preparation; no controller changes or activation.')
