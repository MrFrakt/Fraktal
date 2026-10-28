from pathlib import Path
import json

W = Path(__file__).parent
L = W.parent / 'session_01'
assert json.loads((L / 'reader_flutter_01_exit.json').read_bytes())['exitCode'] == 0
assert '647 ~12: All tests passed!' in (L / 'reader_flutter_01.log').read_text(encoding='utf-8')
S = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
path = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: paced S4b run reaches 588 rows; slow aging mismatch found and corrected offline.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: S4b completes 884 cyclic samples; measured retry exhaustion corrected offline.**
The [freshness attempt](Evidence/AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26.md)
passes 41/41 candidate cases and 87/87 independent raw-record replays, spanning
4,799–5,407 paths. Its 884 completed Dart samples have no Bad values; 806 are
all Good and 78 contain payload-free Uncertain rows. Fast age median/maximum
is 676.3125 /943.021 ms. The next root Status acquisition fails strict
qualification: one changed counter followed by two odd pre-counters ends all
three attempts in 6,237 us, within the same publication phase. No torn row or
cached root identity is accepted. All-bank configuration pages, detail reads,
candidate idle acquisition/scan and desktop acceptance are not reached.

Genealogy, exact original five documents, 31/31 baseline cases, policy, MANUAL
cleanup, final checks and preflight pass. Baseline scan median/cumulative max
is 99 /1,166 us, no overlaps; this is not candidate scan acceptance. No dumps,
fault clears, clock changes, power operations or Echo hard kills. The session
approval is consumed; the complete failed run is sealed before source edits.

The next [reader retry](Evidence/AB_S4B_READER_RETRY_PREPARATION_2026-10-26.md)
changes the desktop plan's default **three attempts to 20 within the same
one-second deadline**. The generic guard's default remains three; its proof,
10 ms maximum accepted window, odd-counter pacing, strict fresh-root gate and
published fast 1/3-second and slow 7.5/15-second limits remain unchanged.
Source age now starts before the accepted attempt's pre-counter I/O, and the
processing bracket stops before response age calculation. Both preserve
conservative age and do not renew a retained sample. Two regression tests
fail against the sealed reader and pass after correction.

Pinned Flutter 3.47.5 /Dart 3.13.4: **647 tests pass, 12 skipped**; analyzer,
locked dependencies and rebuilt Windows pass. Unchanged PLC/image hashes
retain both v38 builds/read-backs, 65% Capacity and 2,336 AB tests through 373
file bindings; all 74 root tests and spec/contracts/strict consistency gates
pass. The prepared fresh workspace uses unchanged ACD `7D75E86E…DEF056BF`
and the same 41/31 write scope. It has no current authorization. S4b native
and desktop acceptance, S5–S7 and S3 physical I/O proof remain. V2/Part III
stay inactive; nothing committed or pushed.

**Earlier, 2026-10-26: paced S4b run reaches 588 rows; slow aging mismatch found and corrected offline.**'''
path.write_text(text.replace(previous, latest), encoding='utf-8')
path = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
needle = '## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(needle) == 1
addition = '''The [freshness run](Evidence/AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26.md)
then passed 41 cases/87 replays and 884 completed cyclic samples without Bad
values, before a root-coherence refusal. Its recorded three attempts ended
after 6,237 us within one publication phase. Genealogy and all 31 baseline
and final checks are restored. The [prepared reader correction](Evidence/AB_S4B_READER_RETRY_PREPARATION_2026-10-26.md)
allows the desktop plan 20 attempts instead of three, retaining its one-second
deadline and every per-row proof/freshness condition. Source age starts before
accepted pre-counter I/O; the processing bracket ends before age calculation.
These are client policy/bookkeeping changes, not a publication ABI amendment
or acceptance claim. Native pages, detail, acquisition/scan and desktop
acceptance remain open; no new controller session is authorized here.

'''
path.write_text(text.replace(needle, addition + needle), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False, currentSessionAuthorized=False, retryNativeSessionAuthorized=False,
    preparation='Evidence/AB_S4B_READER_RETRY_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_reader_01/qualification_session_v2.py',
    lastAttempt='Evidence/AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26.md', lastAttemptAccepted=False,
    sessionApprovalConsumed=True, lastAttemptCandidateCases=41, pairedCapturesReplayed=87,
    baselineChecks=31, genealogyRestored=True, finalChecksPassed=True,
    observerSamples=884, observerNonBadSamples=884, observerAllGoodSamples=806,
    observerPassed=False, configurationPages=0,
    lastAttemptFailure='Root Status coherence unavailable: changed 123678 to 123679, then two odd 123679 pre-counters; three attempts ended in 6237 us',
    rootFailureCauseConfirmed=True, exactFailedAttemptCountersRecorded=True,
    plannedDesktopMaxAttempts=20, previousDesktopMaxAttempts=3, rowDeadlineMs=1000,
    acceptedWindowRuleUnchanged=True, advertisedFreshnessLimitsUnchanged=True,
    sourceAgeCorrection='Before accepted pre-counter I/O, never renewed by a snapshot',
    processingBracketCorrection='Ends before response age calculation; later work remains in transit allowance',
    strictRootQualificationUnchanged=True)
v['offlineGates']['flutterTests'] = 647
v['offlineGates']['readerRegressionTests'] = 2
value['manifestV67']['s4Status'] = 'S4a initial scope accepted. S4b freshness run: 41 cases/87 pairs/884 cyclic samples pass; root proof exhausts three attempts in 6237 us. Prepared default20/1s and conservative-age correction; genealogy/31 baseline restored. Native S4b/desktop pending.'
with path.open('w', encoding='utf-8', newline='') as stream:
    json.dump(value, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True, nativeAccepted=False, currentSessionAuthorized=False, genealogyRestored=True)))
