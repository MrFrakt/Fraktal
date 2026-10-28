from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');D=R/'Specification/AllenBradley';W=Path(__file__).parent
assert json.loads((W/'pool_flutter_02_exit.json').read_bytes())['exitCode']==0
assert b'660 ~12: All tests passed!' in (W/'pool_flutter_02.log').read_bytes()
runtime='Evidence/AB_S4B_STARTUP_DIAGNOSTIC_ATTEMPT_2026-10-27.md'
prep='Evidence/AB_S4B_PARALLEL_READER_PREPARATION_2026-10-27.md'
path=D/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text=path.read_text(encoding='utf-8');start=text.index('**Latest, 2026-10-27:');end=text.index('**Earlier, 2026-10-26:',start)
text=text[:start]+f'''**Latest, 2026-10-27: startup timing measured; parallel reader prepared offline.**
The [startup diagnostic attempt]({runtime}) passes **41/41 fixture cases,
87/87 independent raw-record replays and 906 entirely Good concurrent Dart
samples**, with zero Bad/Uncertain. All four configuration page queries and
targeted detail reads complete. Observer age median/max is 691.696 /898.383 ms;
maximum accepted row window is 8,908 us. Desktop still refuses its initial
complete station sample before app construction: **zero accepted views**.

The preserved primary error is `Complete station sample is late or expired.`
The recorded arithmetic is source age **982,641 us**, transit **16,992 us**,
received age **999,633 us**, local processing **3,497 us**, effective age
**1,003,130 us** against **1,000,000 us**: **3,130 us over**. RPC is 1,026,951 us,
with a 1,010.959 ms server processing bracket. Local processing crosses the
boundary; this does not isolate a particular routine or host cause. The helper
retains the primary exception/stack without the earlier null assertion.
Independent page comparison, idle/generic acquisition and final candidate
timing are skipped after refusal. TASK monitoring records **8,937 us cumulative
maximum /zero overlaps** through 6,733 valid candidate observations; it does
not replace the skipped final scan gate.

Genealogy, all five exact original documents, **31/31 baseline cases**, policy,
MANUAL/idle/logout, final checks and preflight are restored. The completed
approval is consumed. S4b desktop/full acquisition/final scan remain open.

The [parallel-reader preparation]({prep}) keeps the same **30315E6D…A3049A5**
PLC image and write vectors. Four read-only CIP connections all pin to the
same controller serial, with one outstanding request per socket. One complete
row proof leases one connection. Full walks use bounded cohorts of four and
count-dependency barriers; targeted reads stay serial. Counter/count ordering
uses publication revisions. Contradictory counts, counter restart and failed
transport force rediscovery; older parallel replies cannot renew progress.
Complete-sample and leaf ages, freshness/expiry, retry/deadline and per-row
proof rules stay unchanged. **Native performance improvement is unproven.**

All **660 HMI tests pass /12 skipped**, including 11 pool tests and one counter
ordering test, pinned Flutter **3.47.5 /Dart 3.13.4**. The **318-input** isolated
mirror matches: six existing HMI source/test files change and two are added.
Analyzer, Windows debug build and enforced lockfile pass. All **373 PLC/gate
bindings** remain unchanged: **2,339 AB tests**, both v38 builds/read-backs/
access/SDK audits and exact-image **65% Capacity** transfer by hashes. Root
gates and 74 tests pass. The new session is prepared and **not authorized**:
same guards/backup, MANUAL normalization if needed, Program/download/Run,
five-document restore/41 cases with concurrent observer, 100 ms TASK monitor,
strict desktop and remaining checks if ready, then genealogy/original documents/
31 baseline/final checks. Fault/TASK-counter clears, clock changes and power/
vendor-state operations remain excluded. V2/Part III inactive; no commit/push.
S5 gateway/installer, S6 migration/retirement/persistence/events/capacity, and
S7 physical/CIP Security including real I/O remain.

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md'
text=path.read_text(encoding='utf-8');start=text.index('Non-normative design note,');end=text.index('## Owner decisions',start)
text=text[:start]+f'''Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3's Echo exit and S4a's initial qualification pass. S4b desktop acceptance
remains open.** The [startup diagnostic]({runtime}) passes 41 cases/87 replays,
906 entirely Good observer samples and four page queries. Desktop refuses its
initial complete sample at **1,003.130 ms**, 3.130 ms over the unchanged limit:
source 982.641 ms +transit 16.992 ms +local processing 3.497 ms. The original
exception/stack is retained; no live views are accepted. Final acquisition/
timing are skipped. TASK trace maximum is 8,937 us with zero overlaps.
Genealogy, the original documents and 31 baseline/final checks are restored.
The [offline parallel reader]({prep}) uses four serial-pinned read-only
connections, complete row leases and count barriers, with unchanged freshness,
retry and row proofs. Native improvement is unproven; fresh approval is needed.
Same PLC image/65% Capacity, 660 HMI tests passed /12 skipped, 2,339 AB tests
bound. V2/Part III inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text=path.read_text(encoding='utf-8');start=text.index('The [startup diagnostic package]');end=text.index('## AB §1, §2.1 and §4.1',start)
text=text[:start]+f'''The [startup diagnostic]({runtime}) completes 41 cases/87 replays and 906
entirely Good observer samples, but the initial desktop complete sample is
refused at 1,003.130 ms: 982.641 ms source +16.992 ms transit +3.497 ms local
processing. Zero live views are accepted. The preserved primary exception
has no secondary null assertion. TASK trace maximum is 8,937 us /zero overlaps;
remaining acquisition/final timing are skipped. Genealogy, the exact original
documents and 31 baseline/final checks are restored.

The [parallel-reader preparation]({prep}) adds a generic bounded pool of four
read-only connections, all pinned to one controller serial. Each consumed row
keeps one connection through its counter/body/counter proof, with one request
outstanding per socket. Full walks use cohorts of four and count-dependency
barriers; targeted reads remain serial. Revision ordering prevents an older
parallel completion renewing progress or replacing a newer count; contradictory
same-revision counts, counter restart and transport failure force rediscovery.
No wire contract, freshness/expiry, retry/deadline, row proof or write policy
changes. Same image/65% Capacity; 660 HMI tests pass /12 skipped, analyzer/
Windows/locked dependencies and root gates pass, with 2,339 AB tests transferred
through unchanged hashes. Native improvement and desktop acceptance remain
unproven; a fresh session requires current approval. V2/Part III remain inactive.

'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=D/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=prep,qualificationRunner='C:/work/fraktal-ab-s4b-pool-20261027/session_01/qualification_session_v2.py',
 lastAttempt=runtime,latestRuntimeEvidence=runtime,lastAttemptFailure='Initial desktop complete sample refused at 1003130 us, 3130 us over the unchanged 1000000 us limit; original error retained',
 observerSamples=906,observerNonBadSamples=906,observerAllGoodSamples=906,allGoodSamples=906,samplesWithUncertainRows=0,
 scanCumulativeMaxUs=8937,desktopSecondaryFailure=None,repositoryRejectedAgeComponentsKnown=True)
v['offlineGates'].update(flutterTests=660,parallelPoolTests=11,sourceCounterOrderingTests=1)
v['nativeLookupFreshness'].update(medianAgeMs=691.696,maxAgeMs=898.383,maxAcceptedRowWindowUs=8908)
v['coldStartCorrection']['latestRuntimeEvidence']=runtime
v['desktopLatestCoverage'].update(error='FormatException: Complete station sample is late or expired.',helperSecondaryError=None)
v['startupDiagnostic'].update(authorized=False,completed=True,approvalConsumed=True,runtimeEvidence=runtime,
 measuredTiming=json.loads(Path('C:/work/fraktal-ab-s4b-startup-20261027/session_01/desktop_freshness_analysis_01.json').read_bytes())['observations'][0])
v['parallelReader']={
 'implementedOffline':True,'nativeAccepted':False,'nativeSessionAuthorized':False,'connections':4,
 'sameControllerSerialPinned':True,'outstandingRequestsPerSocket':1,'completeGuardedRowLease':True,
 'countDependencyBarriers':True,'targetedReadsSerial':True,'sourceRevisionOrdersParallelReplies':True,
 'contradictoryCountsAbort':True,'counterRestartForcesRediscovery':True,'frozenPublisherCannotRemainGood':True,
 'freshnessRulesChanged':False,'retryRulesChanged':False,'rowProofChanged':False,'additionalPlcWriteVectors':0,
 'hmiMirrorInputs':318,'changedExistingHmiFiles':6,'addedHmiFiles':2,'poolTests':11,'counterOrderingTests':1}
v['acceptancePending']=[
 'Native parallel-reader performance and strict live desktop coverage',
 'Independent pages/idle/generic acquisition','Final candidate scan timing',
 'Verified genealogy/baseline restoration per new session']
assert doc['manifestV67']['s4Status'].startswith('S4a accepted.')
doc['manifestV67']['s4Status']='S4a accepted. S4b startup diagnostic passes 906 entirely Good samples/41 cases/87 replays, but desktop complete-sample age is 3.130 ms over its unchanged limit. Zero accepted views; genealogy/31 baseline restored. Four-connection generic reader prepared offline; native S4b remains open.'
path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='')
print('Updated plan, design, inactive amendment and V2 status; no controller access or contract activation.')
