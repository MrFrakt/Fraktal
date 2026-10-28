from pathlib import Path
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
D = W.parent / 'retry_reader_01'
S = R / 'Specification/AllenBradley'
summary = json.loads((D / 'runtime_summary_01.json').read_bytes())
sealed = json.loads((W / 'sealed_reader_runtime_01.json').read_bytes())
assert sealed['passed'] and summary['nativeReaderPassed'] and not summary['scanReviewPassed']
assert summary['observerSamples'] == 902 and summary['allGoodSamples'] == 902
assert summary['nativeMeasurements']['taskScanCumulativeMaxUs'] == 10033
assert summary['nativeMeasurements']['taskOverlaps'] == 1
path = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: S4b completes 884 cyclic samples; measured retry exhaustion corrected offline.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: S4b reader passes functionally; scan review and desktop remain open.**
The [sealed reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md) completes
41/41 candidate cases, 87/87 independent raw-record replays, and **902 entirely
Good cyclic samples**. No Bad/Uncertain/rejected-root sample occurs. Fast age
median/p95/max is 684.1535 /774.077 /848.974 ms; maximum accepted row window
9,594 us remains below 10,000. All four read-only configuration pages (30 live
entries and four entries in each of three model banks) match the independent
oracle in **1,100 scalar values/types**. Targeted detail reads, exact idle
equivalence on **5,407 paths** and generic acquisition of 5,407 values/seven
modules pass. The unchanged PLC image still measures 65% offline Capacity.

Native TASK median is 966 us, cumulative maximum **10,033 us**, **one overlap**
on its 10 ms period. This keeps the scan review open despite successful runner
and functional results. All 87 paired captures already contain that same
maximum/count, starting at the earliest recorded pair (probe sample 2,350);
none shows another overlap. Their LastScanTime ranges 944–1,144 us, median
973 us. The initial event's location/cause is unrecorded; neither host jitter
nor PLC initialization is established as the cause. Do not clear counters or
faults, waive the finding or claim zero overlaps. Instrument from Run through
discovery/readiness and the workload before deciding on a correction.

Genealogy, the original five host documents, 31/31 baseline cases, policy,
MANUAL/idle/logout, final checks and preflight pass. Baseline scan is 99 us,
maximum 1,167 us, zero overlaps. No dumps, fault clears, clock changes, power
operations or hard kills. Authorization consumed. V2/Part III stay inactive;
desktop rendering and scan review remain S4b gates, followed by S5–S7 and S3
physical I/O proof. No commit/push. The 647-test pinned Flutter result (12
skips), analyzer/Windows/lockfile and 2,336 unchanged AB tests remain bound.

A preliminary pre-S6 syntax census of the 373 bound Python files is archived
with this run: 54 tools/53 test modules have direct legacy references; the
transitive import closure is 155 tools/129 tests. These include oracle,
metadata and test dependencies, not just runtime readers. Classification and
owner review remain before migration/deletion; the old 22/44 count is obsolete.

**Earlier, 2026-10-26: S4b completes 884 cyclic samples; measured retry exhaustion corrected offline.**'''
path.write_text(text.replace(previous, latest), encoding='utf-8')
path = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
needle = '## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(needle) == 1
addition = '''The [bounded reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md)
passes 41 cases/87 replays, 902 entirely Good cyclic samples, four configuration
pages (1,100 exact oracle scalar/type comparisons), targeted details and
5,407-path idle/generic acquisition. Genealogy and all 31 baseline/final checks
are restored. This is functional native proof, with desktop and scan review
still open: cumulative native maximum 10,033 us and one overlap on a 10 ms
task, already present at the earliest paired capture. The cause is unproven;
no limit is widened or counter cleared. V2/Part III remain inactive.

'''
path.write_text(text.replace(needle, addition + needle), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False,nativeReaderPassed=True,desktopAccepted=False,scanReviewPassed=False,
    currentSessionAuthorized=False,retryNativeSessionAuthorized=False,sessionApprovalConsumed=True,
    lastAttempt='Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md',lastAttemptAccepted=False,
    lastAttemptCandidateCases=41,pairedCapturesReplayed=87,observerSamples=902,observerNonBadSamples=902,
    observerAllGoodSamples=902,observerPassed=True,configurationPages=4,configurationScalarComparisons=1100,
    idleCanonicalPaths=5407,genericAcquiredValues=5407,genericAcquiredModules=7,
    lastAttemptFailure=None,scanReviewFinding='10033 us cumulative TASK maximum, one overlap on 10000 us period; present in all 87 pairs, cause unconfirmed',
    scanMedianUs=summary['nativeMeasurements']['taskScanMedianUs'],scanCumulativeMaxUs=10033,scanOverlaps=1,scanCauseConfirmed=False,
    baselineChecks=31,genealogyRestored=True,finalChecksPassed=True,
    preliminaryLegacyDirectTools=54,preliminaryLegacyDirectTestModules=53,legacyConsumerClassificationPending=True)
value['manifestV67']['s4Status'] = 'S4a initial scope accepted. S4b reader functional proof passes: 41 cases/87 pairs/902 entirely Good samples, four exact pages and 5407-path idle/generic reads. Scan review (10033 us, one overlap) and desktop remain open; genealogy/31 baseline restored.'
with path.open('w',encoding='utf-8',newline='') as stream:
    json.dump(value,stream,indent=2,ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True,nativeReaderPassed=True,scanReviewPassed=False,
    nativeAccepted=False,desktopAccepted=False,genealogyRestored=True)))
