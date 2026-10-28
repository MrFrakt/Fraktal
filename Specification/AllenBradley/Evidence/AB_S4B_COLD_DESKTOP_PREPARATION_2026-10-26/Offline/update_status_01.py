from pathlib import Path
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
A = R / 'Specification/AllenBradley'
evidence = 'Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md'
preparation = 'Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md'

path = A / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
start = text.index('**Latest, 2026-10-26:')
end = text.index('**Earlier, 2026-10-26: S4b reader passes functionally;', start)
latest = '''**Latest, 2026-10-26: desktop/scan diagnostics sealed; cold-start correction prepared offline.**
The [completed desktop/scan session](Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md)
passes 41/41 candidate cases, 87/87 independent replays, **895 entirely Good
Dart samples**, four configuration pages/1,100 exact oracle comparisons and
5,407-path idle/generic acquisition. Genealogy, the five original documents,
31/31 baseline cases, final checks and preflight are restored. This approval
is consumed. The earlier pre-download readiness-file failure and its bounded
readiness correction are sealed separately; no download ran in that attempt.

Two S4b acceptance gates remain open. Read-only TASK polling from before
download first observes the 10,033 us maximum/one overlap between probe
observations 1 and 17, before Dart readiness and the desktop. It does not
identify the exact offending scan, routine or host cause. No counters were
cleared. The native desktop helper incorrectly returned success with an
empty module forest and only two screenshots; the overview visibly showed
STALE. Semantic review **rejects** that result. A zero process exit is not
desktop acceptance. Both findings and raw records remain in the runtime seal.

The [new cold-start/desktop preparation](Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md)
changes one generated publisher condition: on a cold first Run scan it keeps
the manifest invalid, publishes no value rows and clears every value buffer;
normal formatting begins next scan. Already initialized retained first scans
still rebuild and apply access masking immediately. Three execution tests
cover cold initialization, retained access drop and invalid catalog refusal.
The generated types/tags/initializers remain identical. This targets measured
early startup pressure; native scan improvement is **not established**.

The qualification helper now requires LIVE, nonempty complete module/bus/view
coverage before and after every capture, checks tab selection, records refresh
and forest diagnostics, captures native test output and validates coverage in
the parent launcher. Static captured-native replay passes all 31 views; a
forced stale/empty replay correctly fails, and six semantic coverage tests
reject the previous false positive. The replay does not prove live freshness.

All **2,339 AB tests**, both v38 builds/read-backs, access audits and SDK log
audits pass. The exact new ACD `30315E6D…A3049A5` measures **2,066,212 used /
1,079,516 available /3,145,728 total Blocks (65%)**, 112 more used Blocks.
Shipping HMI sources and dependencies are unchanged: the pinned Flutter
3.47.5 /Dart 3.13.4 result remains 647 passed/12 skipped by source bindings,
with Windows/analyzer/enforced-lockfile proof. The changed standalone desktop
helper passes analyzer and rendering/refusal checks. Eight failure-injected
session tests, six readiness tests, authorization refusals and root gates pass.

The new image has **not** been downloaded. Fresh exact-image authorization is
required by AGENTS §3a; the completed approval is not reused. V2/Part III
remain inactive. Remaining work: live desktop and scan acceptance on this
image; S5 gateway/installer; S6 classified legacy-reader migration, retirement,
persistence/events and capacity work; S7 physical/CIP Security, including real
I/O proof. Nothing is committed or pushed.

'''
path.write_text(text[:start] + latest + text[end:], encoding='utf-8', newline='')

path = A / 'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md'
text = path.read_text(encoding='utf-8')
start = text.index('**S3\'s Echo exit')
end = text.index('\n## Owner decisions', start)
text = text[:start] + '''**S3's Echo exit and S4a's initial qualification pass. S4b's generic reader
passes its functional Echo scope; live desktop and scan acceptance remain open.**
The [desktop/scan diagnostics](Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md)
pass 41 cases/87 replays/895 Good samples, but reject the desktop helper's
empty/stale success and locate one TASK overlap between early probe
observations 1 and 17. Genealogy and 31 baseline cases are restored. The
[cold-start/desktop correction](Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md)
is prepared offline, passes 2,339 AB tests and both v38 builds/read-backs, and
measures 65% Capacity. Its native scan effect and strict live desktop coverage
are unproven; the new image is not downloaded or authorized. Shipping HMI code
is unchanged by this correction. The existing shipping path has not been
retired or replaced. V2 and the Part III amendment remain inactive target
drafts. See the [plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
''' + text[end:]
path.write_text(text, encoding='utf-8', newline='')

path = A / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
marker = '\n## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(marker) == 1
addition = '''
The [desktop/scan diagnostic run](Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md)
repeats functional proof with 41 cases/87 replays and 895 entirely Good Dart
samples. It first observes the one overlap between probe observations 1 and
17, before the observer/desktop; scalar polling does not identify the exact
scan or cause. The desktop helper's success is rejected: its native result
contains zero modules and two screenshots, including a stale/empty overview.
Genealogy, the original documents and 31 baseline/final checks are restored.

The [new offline preparation](Evidence/AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26.md)
withholds the uninitialized read-only view on the cold first Run scan, clears
all value buffers and starts normal formatting next scan. Retained initialized
first scans still mask access immediately. No wire type, tags or initializer
change. The strict desktop qualification now requires LIVE, complete nonempty
coverage at every capture, with parent semantic validation and refresh/forest
diagnostics. These corrections pass 2,339 AB tests, both v38 builds/read-backs,
65% Capacity and the standalone desktop positive/stale-refusal checks. No
native timing improvement or live desktop acceptance is claimed. This image
requires fresh exact-image authorization; V2/Part III remain inactive.
'''
path.write_text(text.replace(marker, addition + marker), encoding='utf-8', newline='')

path = A / 'AB_FROZEN_CONTRACTS_V2.json'
doc = json.loads(path.read_bytes())
v = doc['manifestV68']
v.update(preparation=preparation,
    preparedAcdSha256='30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5',
    sourceSha256='60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E',
    qualificationRunner='C:/work/fraktal-ab-s4b-cold-20261026/session_01/qualification_session_v2.py',
    lastAttempt=evidence, lastAttemptAccepted=False,
    lastRuntimeAcdSha256='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF',
    lastRuntimeSourceSha256='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F',
    observerSamples=895, observerNonBadSamples=895,
    scanReviewFinding='10033 us cumulative TASK maximum and one overlap, first observed between probe observations 1 and 17 before observer/desktop; exact scan/routine/host cause unconfirmed',
    scanMedianUs=966, scanCauseConfirmed=False,
    acceptancePending=['Fresh exact-image approved cold-start/desktop Echo session',
        'Repeat candidate/reader/configuration/acquisition checks on corrected image',
        'Native startup and active-workload scan acceptance without counter clears',
        'Strict live desktop rendering/connection and complete coverage',
        'Verified genealogy rollback, original documents and 31 baseline/final checks'],
    nativeLookupFreshness=dict(medianAgeMs=682.356,maxAgeMs=964.315,maxAcceptedRowWindowUs=9990),
    desktopNativeReview=dict(accepted=False, helperReportedPassed=True,
        actualModules=0,expectedModules=7,actualViews=2,expectedViews=31,
        visibleState='STALE with empty overview',evidence=evidence),
    coldStartCorrection=dict(implementedOffline=True,nativeAccepted=False,
        coldFirstScanInvalidPublication=True,allValueBuffersCleared=True,
        retainedInitializedFirstScanMaskingImmediate=True,executionTests=3,
        generatedTypesTagsInitializersUnchanged=True,
        purpose='Move cold initial formatting off first Run scan; native scan effect unproven'),
    desktopFollowup=dict(prepared=True,authorized=False,
        shippingHmiSourcesUnchanged=True,plcPublisherConditionChanged=True,
        taskPollMs=100,taskMonitorBeginsBeforeDownload=True,taskMonitorStopsBeforeRollback=True,
        liveDesktopUsesProductionFactory=True,requiresLiveAtEveryCapture=True,
        requiresNonemptyCompleteCoverage=True,parentSemanticValidation=True,
        nativeTestOutputCaptured=True,refreshAndForestDiagnostics=True,
        additionalPlcWriteVectors=0,workflowAndMonitorTests=8,readinessTests=6,
        semanticCoverageTests=6,existingAuthorizationRefusals=16),
    desktopFixtureProof=dict(passed=True,live=False,modules=7,fieldbusNodes=3,views=31,
        clientWriteCalls=0,staleEmptyNegativeReplayRefused=True,
        source='Captured native values/pages; strict static rendering proof, not native freshness'))
v['measuredCapacityBlocks'].update(used=2066212,available=1079516)
v['offlineGates']['abTests'] = 2339
v['offlineGates']['coldStartExecutionTests'] = 3
v['offlineGates']['desktopCoverageTests'] = 6
doc['manifestV67']['s4Status'] = ('S4a initial scope accepted. S4b functional Echo proof repeats with '
    '41 cases/87 replays/895 Good samples, four exact pages and 5407-path reads. '
    'Native desktop false positive rejected; one overlap first observed between probe observations 1 and 17. '
    'Genealogy/31 baseline restored. Cold-start/strict desktop correction prepared offline; fresh authorization pending.')
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
print(json.dumps(dict(updated=4,nativeAccepted=False,currentControllerChangesAuthorized=False)))
