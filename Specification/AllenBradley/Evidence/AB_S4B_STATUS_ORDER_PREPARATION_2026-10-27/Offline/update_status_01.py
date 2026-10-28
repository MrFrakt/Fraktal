from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal')
A=R/'Specification/AllenBradley'
W=Path(__file__).parent
P='Evidence/AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md'
E='Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md'
q=json.loads(Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01/runtime_summary_01.json').read_bytes())
assert q['candidateCases']==41 and q['pairedCapturesReplayed']==87 and q['observerSamples']==68
assert q['genealogyRestored'] and not q['nativeAccepted']
path=A/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-26:')
end=text.index('**Earlier, 2026-10-26: S4b reader passes functionally;',start)
latest='''**Latest, 2026-10-27: cold-image attempt sealed; module-Status scheduling correction prepared offline.**
The [cold-start/desktop attempt](Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md)
downloads ACD `30315E6D…A3049A5` and passes all **41 candidate cases /87 raw-record
replays**. The Dart observer stops after **68 entirely Good samples** when root
Status becomes payload-free Uncertain: `read-late`, **1,035.46 ms**, above the
unchanged 1,000 ms Good cutoff. The rejected snapshot is retained. Its global
sampleAgeMs is 998.907 because that aggregate includes only remaining Good
values; it does not make the older root usable. No cached identity is accepted.
The bounded fixture completes, then its wrapper observes the failed observer
exit and stops subsequent candidate stages. Full concurrent-workload reader
acceptance, configuration/detail queries, desktop, idle/generic acquisition
and final candidate timing are **not passed by this attempt**.

The read-only TASK monitor spans startup through the completed candidate
fixture: **7,659 valid candidate observations**, cumulative maximum **9,002 us**,
**zero overlaps**, no dump or controller fault. The first paired capture has
7,752 us /zero overlaps. This is useful cold-start/workload evidence; skipped
desktop/final timing remain required, and the trace does not isolate a routine
or host cause. Genealogy, all five original documents, **31/31 baseline cases**,
MANUAL/idle/logout, all final checks and preflight pass. Baseline median is
99 us, maximum 1,167 us, zero overlaps. The approval is consumed.

The [new Status-order preparation](Evidence/AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md)
keeps the **same PLC image and 65% Capacity**. In a full cyclic read walk only,
the generic client schedules discovered module Status groups near delivery;
leaf modules whose Status is already in one group move with that group. No
station facts or wire contract are added. Targeted reads, tier selection,
per-row proofs, attempt/deadline limits and 1/3-second fast freshness stay
unchanged. Other rows that become late still lose their payload. The new
long-walk execution test fails on the previous reader and passes on this one;
all 12 read-plan tests pass. Comparison to the immutable prior reader checks
the wire-read multiset and projected values/types without timing claims.

All **648 HMI tests pass /12 skipped**, using pinned Flutter 3.47.5 /Dart
3.13.4; analyzer, Windows debug build and enforced lockfile pass. The two HMI
source changes are the plan and its regression test; the same 316-input
isolated source mirror is verified. The unchanged PLC source/image retains
**2,339 AB tests**, both v38 builds/read-backs, access/SDK audits and measured
Capacity **2,066,212 used /1,079,516 available /3,145,728 total Blocks (65%)**.
Fresh workflow/readiness/authorization gates and 74 root tests pass.

No further download has run. This is a fresh unapproved session: native reader
freshness, strict LIVE desktop coverage, complete acquisition and final scan
acceptance remain open. The new session repeats the same 41-case scope and
read-only 100 ms TASK/desktop checks, then genealogy/31 baseline/final checks.
Fault/TASK-counter clears, clock changes and power/vendor-state operations
remain excluded. V2/Part III inactive; nothing committed or pushed.

'''
text=text[:start]+latest+text[end:]
text=text.replace('1. **Migrate the harnesses.** 22 tools and 44 test modules read the generated\n   contexts (`read_unit`, `read_layout`, `*_context_members`, the projection).',
    '1. **Migrate the harnesses.** The original 22-tool/44-test estimate is\n   superseded by the preliminary syntax census: 54 tools/53 test modules have\n   direct legacy references, including oracle/metadata dependencies. Classify\n   actual runtime readers before migration. The affected generated contexts\n   include `read_unit`, `read_layout`, `*_context_members` and the projection.')
text=text.replace('| Harness migration volume (22 tools, 44 tests) | Migrate behind the equivalence gate before deleting anything |',
    '| Harness migration volume (preliminary 54 tools/53 tests with direct references) | Classify runtime readers, then migrate behind the equivalence gate before deleting anything |')
path.write_text(text,encoding='utf-8',newline='')
path=A/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md'
text=path.read_text(encoding='utf-8')
start=text.index('**S3\'s Echo exit')
end=text.index('\n## Owner decisions',start)
text=text[:start]+'''**S3's Echo exit and S4a's initial qualification pass. S4b remains open.**
The [cold-image attempt](Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md)
passes 41 cases/87 replays and records zero TASK overlaps, maximum 9,002 us,
but its Dart observer refuses a 1,035.46 ms root Status after 68 Good samples.
Desktop and later acquisition/timing stages are skipped. Genealogy, the original
documents and 31 baseline/final checks are restored. The
[Status-order correction](Evidence/AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md)
is prepared offline on the same PLC image at 65% Capacity. It changes cyclic
group order while preserving wire reads, values/types, row proofs and freshness
limits; 648 HMI tests pass, 12 skipped, with analyzer/Windows/locked dependencies.
Native correction and strict live desktop acceptance are unproven. The new
session requires current authorization. V2/Part III remain inactive; the
shipping legacy path is not retired. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
'''+text[end:]
path.write_text(text,encoding='utf-8',newline='')
path=A/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text=path.read_text(encoding='utf-8')
marker='\n## AB §1, §2.1 and §4.1 — reference profile'
addition='''
The [2026-10-27 cold-image attempt](Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md)
passes 41 cases/87 replays and records zero TASK overlaps with a 9,002 us
maximum through the candidate fixture. The Dart observer refuses a root Status
at 1,035.46 ms after 68 Good samples; its payload stays withheld. Desktop and
later acquisition/final timing are skipped, and genealogy/31 baseline/final
checks are restored. The same-image [offline retry](Evidence/AB_S4B_STATUS_ORDER_PREPARATION_2026-10-27.md)
schedules discovered module Status groups at the end of cyclic walks, retaining
all reads, values/types, targeted semantics, row proofs and freshness limits.
The regression, 648 HMI tests (12 skipped), analyzer, Windows and lockfile gates
pass. No native improvement is claimed before a new authorized qualification.
V2/Part III remain inactive.
'''
assert text.count(marker)==1
path.write_text(text.replace(marker,addition+marker),encoding='utf-8',newline='')
path=A/'AB_FROZEN_CONTRACTS_V2.json'
doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation=P,lastAttempt=E,lastAttemptAccepted=False,nativeAccepted=False,
    lastRuntimeAcdSha256=q['canonicalSha256'],lastRuntimeSourceSha256=q['sourceSha256'],
    qualificationRunner='C:/work/fraktal-ab-s4b-status-20261027/session_01/qualification_session_v2.py',
    currentSessionAuthorized=False,retryNativeSessionAuthorized=False,sessionApprovalConsumed=True,
    lastAttemptCandidateCases=41,candidateChecksPassed=True,pairedCapturesReplayed=87,
    observerSamples=68,observerNonBadSamples=68,observerPassed=False,nativeReaderPassed=False,
    lastAttemptFailure='Root Status read-late at 1035.46 ms; strict freshness refusal after 68 Good samples',
    configurationPages=0,configurationScalarComparisons=0,idleCanonicalPaths=0,
    genericAcquiredValues=0,genericAcquiredModules=0,desktopAccepted=False,scanReviewPassed=False,
    scanCumulativeMaxUs=9002,scanOverlaps=0,scanMedianUs=None,scanCauseConfirmed=False,
    scanReviewFinding='Startup/fixture monitor: 7659 valid candidate observations, 9002 us maximum, zero overlaps; desktop/final candidate timing skipped after observer failure',
    nativeLookupFreshness=dict(medianAgeMs=788.9125,maxAgeMs=961.11,maxAcceptedRowWindowUs=5857,
        rejectedRootAgeMs=1035.46,rejectedRootQuality='Uncertain/read-late',rejectedGlobalGoodSampleAgeMs=998.907),
    statusOrderCorrection=dict(implementedOffline=True,nativeAccepted=False,
        scope='Full cyclic walks only; discovered module Status groups, including whole leaf-module groups, scheduled last',
        extraWireReads=0,wireTypesChanged=False,targetedReadsChanged=False,
        rowProofChanged=False,freshnessLimitsChanged=False,latePayloadStillWithheld=True,
        regressionTests=1,readPlanTests=12),
    acceptancePending=['Fresh exact-image/current-client Echo session','Full concurrent Dart/41-case workload',
        'Configuration/detail/idle/generic checks on current client','Strict live desktop coverage',
        'Complete startup/workload/desktop/final scan acceptance','Genealogy/original documents/31 baseline/final checks'])
v['offlineGates']['flutterTests']=648
v['offlineGates']['statusOrderRegressionTests']=1
v['desktopFollowup'].update(prepared=True,authorized=False,shippingHmiSourcesUnchanged=False,
    plcPublisherConditionChanged=False,completedPreviousSession=True)
v['coldStartCorrection'].update(nativeAccepted=False,
    startupFixtureTraceEvidence=E,startupFixtureMaxScanUs=9002,startupFixtureOverlaps=0,
    completeDesktopFinalScanAcceptance=False)
doc['manifestV67']['s4Status']='S4a accepted. S4b cold-image fixture passes 41/87 with zero overlaps, 9002 us maximum; observer refuses 1035.46 ms root after 68 Good samples. Genealogy/31 baseline restored. Status-order correction prepared offline; native desktop/freshness/acquisition/final timing remain open.'
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
print(json.dumps(dict(updated=4,latestNativeAccepted=False,controllerChangesAuthorized=False)))
