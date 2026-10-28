from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal')
A=R/'Specification/AllenBradley'
path=A/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text=path.read_text(encoding='utf-8')
start=text.index('**Latest, 2026-10-27:')
end=text.index('**Earlier, 2026-10-26: S4b reader passes functionally;',start)
latest='''**Latest, 2026-10-27: active observer passes; desktop startup refusal sealed and instrumented offline.**
The [Status-order attempt](Evidence/AB_S4B_STATUS_ORDER_ATTEMPT_2026-10-27.md)
passes **41/41 fixture cases /87/87 independent raw-record replays** and the
full concurrent observer: **910 samples**, **902 entirely Good /eight with
Uncertain /zero Bad**, all four configuration page queries and targeted detail
reads. Good age median/max is 828.5365 /999.542 ms; maximum accepted row window
9,737 us. The earlier aged-root failure does not recur. This is active observer
proof; independent page comparison, idle/generic acquisition and final candidate
timing remain skipped because the next desktop stage fails.

The desktop factory refuses its **initial repository refresh** with
`Complete station sample is late or expired.` before app construction or any
view capture. Its helper then reports a secondary null assertion because
Flutter runAsync retained the first exception. Both errors, full stdout and
the failure record are archived; **zero desktop views** are accepted. The
current native record lacks the rejected repository sample's source/transit/
local age components, so it does not establish which component exhausted the
budget. No expiry, retry or quality rule is widened or bypassed.

Read-only TASK monitoring covers **8,099 valid candidate observations** through
the observer and refused desktop startup: **8,994 us cumulative maximum /zero
overlaps** on the 10,000 us task. The earliest paired capture is 7,752 us /zero.
This does not replace skipped final timing or prove a routine/host cause.
Genealogy, five exact original documents, **31/31 baseline cases**, policy,
MANUAL/idle/logout, all final checks and preflight are restored. The completed
approval is consumed. S4b desktop/full acquisition/final scan acceptance stays open.

The [startup diagnostic preparation](Evidence/AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md)
keeps the same PLC image and write vectors. The repository logs numeric source
age, RPC duration, server processing bracket, transit allowance, received age,
local processing and effective age **only on the existing freshness refusal**.
The original exception and every acceptance threshold remain unchanged. The
existing first-frame rejection test now checks that these components reconcile,
with the client closed, one snapshot and no writes. The desktop helper catches
startup errors within runAsync and rethrows their original stack before using
app state. A forced startup fixture retains that primary error without a null
assertion; the positive 31-view and forced-stale fixtures retain their outcomes.

All **648 HMI tests pass /12 skipped**, pinned Flutter 3.47.5 /Dart 3.13.4,
analyzer, Windows debug build and enforced lockfile. The same 316-input mirror
is verified. Relative to the Status-order package, only repository diagnostics,
its existing freshness test and the standalone helper change. All **373 PLC/gate
bindings** are unchanged: 2,339 AB tests, both v38 builds/read-backs/access/SDK
audits and exact-image 65% Capacity transfer. Root gates and 74 tests pass.

The new diagnostic session is prepared and **not authorized**. It repeats the
same fresh guards/backup, MANUAL normalization if needed, Program/download/Run,
five-document restore/41 cases with concurrent observer, 100 ms TASK monitor,
strict desktop and subsequent checks if ready, then genealogy/original documents/
31 baseline/final checks. It may reproduce the refusal; its purpose is to
measure that startup boundary. Fault/TASK-counter clears, clock changes and
power/vendor-state operations remain excluded. V2/Part III inactive; no commit/push.
S5 gateway/installer, S6 migration/retirement/persistence/events/capacity, and
S7 physical/CIP Security including real I/O remain.

'''
path.write_text(text[:start]+latest+text[end:],encoding='utf-8',newline='')
path=A/'AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md'
text=path.read_text(encoding='utf-8');start=text.index('**S3\'s Echo exit');end=text.index('\n## Owner decisions',start)
opening='''**S3's Echo exit and S4a's initial qualification pass. S4b desktop acceptance
remains open.** The [Status-order attempt](Evidence/AB_S4B_STATUS_ORDER_ATTEMPT_2026-10-27.md)
passes 41 cases/87 replays and 910 concurrent observer samples, with four page
queries, but desktop initial repository freshness is refused before rendering.
The TASK trace has 8,994 us maximum /zero overlaps; final acquisition/timing
are skipped. Genealogy and 31 baseline/final checks are restored. The
[startup diagnostic](Evidence/AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md)
adds only refusal timing logs and correct primary exception capture, retaining
all acceptance rules. Same PLC image/65% Capacity, 648 HMI tests passed /12
skipped, 2,339 AB tests bound. It may reproduce the refusal and needs fresh
authorization. V2/Part III inactive; S5-S7/physical I/O remain. See the
[plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
'''
path.write_text(text[:start]+opening+text[end:],encoding='utf-8',newline='')
path=A/'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text=path.read_text(encoding='utf-8');marker='\n## AB §1, §2.1 and §4.1 — reference profile'
addition='''
The [startup diagnostic package](Evidence/AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md)
follows 910 successful concurrent observer samples and a refused initial
desktop repository sample. It adds numeric source/RPC/server/transit/local age
diagnostics and preserves the original startup exception/stack. No acceptance,
freshness or row-proof rule changes. Same image at 65% Capacity; 648 HMI tests
pass, 12 skipped, with analyzer/Windows/locked dependencies and root gates.
Native desktop acceptance remains open; V2/Part III remain inactive.
'''
assert text.count(marker)==1
path.write_text(text.replace(marker,addition+marker),encoding='utf-8',newline='')
path=A/'AB_FROZEN_CONTRACTS_V2.json';doc=json.loads(path.read_bytes());v=doc['manifestV68']
v.update(preparation='Evidence/AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-startup-20261027/session_01/qualification_session_v2.py',
    activeWorkloadObserverPassed=True,observerSamples=910,allGoodSamples=902,samplesWithUncertainRows=8,
    lastAttemptFailure='Initial desktop repository sample refused as late/expired; secondary helper null assertion',
    desktopPrimaryFailure='Complete station sample is late or expired.',
    desktopSecondaryFailure='Null check operator used on a null value',
    repositoryRejectedAgeComponentsKnown=False,currentSessionAuthorized=False,retryNativeSessionAuthorized=False,
    startupDiagnostic=dict(prepared=True,authorized=False,productionBehaviorChanged=False,
        freshnessRulesChanged=False,retryRulesChanged=False,rowProofChanged=False,
        logs=['sourceAgeUs','rpcUs','responseProcessingMs','transitUs','receivedAgeUs','localProcessingUs','effectiveAgeUs','fastGoodUs'],
        primaryStartupExceptionAndStackRetained=True,positiveFixtureViews=31,
        forcedStartupRefused=True,forcedStaleRefused=True,nativeAcceptancePromised=False),
    acceptancePending=['Measure refused desktop initial complete-sample timing',
        'Strict live desktop coverage','Independent pages/idle/generic acquisition',
        'Final candidate scan timing','Verified genealogy/baseline restoration per new session'])
doc['manifestV67']['s4Status']='S4a accepted. S4b active observer passes 910 samples/41 cases/87 replays, but desktop initial complete-sample freshness is refused. Zero accepted views; genealogy/31 baseline restored. Same-image startup diagnostic prepared offline; S4b remains open.'
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
print(json.dumps(dict(updated=4,nativeAccepted=False,diagnosticSessionAuthorized=False)))
