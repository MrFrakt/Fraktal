from pathlib import Path
import json

W = Path(__file__).parent
L = W.parent / 'session_01'
assert json.loads((L / 'freshness_flutter_01_exit.json').read_bytes())['exitCode'] == 0
assert '645 ~12: All tests passed!' in (L / 'freshness_flutter_01.log').read_text(encoding='utf-8')
S = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
path = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: S4b lookup retry passes 41 PLC cases; root-coherence refusal stops Dart.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: paced S4b run reaches 588 rows; slow aging mismatch found and corrected offline.**
The [paced attempt](Evidence/AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md)
passes 41/41 candidate cases and 87/87 independent paired replays. The observer
records 587 non-Bad rows, then one row with a Bad value: fast age median
680.2575 ms, maximum 931.960 ms; no repeated missing-Good-root refusal. The
retained preceding snapshots identify ShiftHistoryTruncated as an Uncertain
slow row, but the final Bad branch did not save its full snapshot. Its exact
Bad-path identity therefore remains an inference. A supplementary read-only
capture ended as rollback stopped the publisher and did not reproduce the
original Bad leaf. All failed evidence is retained. Genealogy, original five
documents, 31/31 baseline cases, policy, MANUAL/idle/logout, final checks and
preflight pass; no fault clear, clock/power operation or dump. Approval consumed.

Code inspection and failing-before/passing-after clock tests establish a real
mismatch: planner slow expiry was 10 seconds, while the session declared 15.
The planner and envelope now share one profile with the original values:
fast Good/expiry 1/3 seconds, slow Good/expiry 7.5/15 seconds and heartbeat 5.
Good cutoffs remove payloads, expiry is enforced at the boundary, non-Good
quality is never promoted, cached ages are preserved, and retained excluded
groups use the declared slow profile per OPCUA_TRANSPORT. No advertised limit,
coherence rule, attempt/deadline, identity or strict root check is increased.
The Bad-value branch now retains the entire rejected snapshot and affected
path metadata before stopping. Four new tests cover these profile boundaries,
excluded retention and diagnostic capture. Full pinned Flutter 3.47.5 /
Dart 3.13.4 gates pass: **645 tests, 12 skipped**, analyzer, enforced lockfile,
rebuilt Windows. The unchanged PLC/image retains both v38 builds/read-backs,
65% Capacity and the 2,336-test AB result through 373 file bindings. All 74
root tests/gates pass again. Native S4b acceptance is still open.

The [freshness retry](Evidence/AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26.md)
uses the same ACD `7D75E86E…DEF056BF`, a fresh workspace and the same 41/31
write scope. No new controller session is authorized. All-bank Dart pages,
detail, complete acquisition/scan and desktop acceptance remain; then S5-S7
and S3 physical I/O proof. V2/Part III inactive; nothing committed or pushed.

**Earlier, 2026-10-26: S4b lookup retry passes 41 PLC cases; root-coherence refusal stops Dart.**'''
path.write_text(text.replace(previous, latest), encoding='utf-8')
path = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
needle = '## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(needle) == 1
addition = '''The paced attempt then passed 41 cases/87 replays and reached 587 non-Bad
cyclic rows before one Bad value. The strict observer stopped; genealogy and
31 baseline/final checks were restored. The [sealed run](Evidence/AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md)
records the missing Bad-branch snapshot explicitly. A verified slow-expiry
implementation mismatch (10 seconds versus the published 15) is corrected
offline using one unchanged profile for aging and its envelope. Rejected Bad
snapshots are now retained. See the [freshness preparation](Evidence/AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26.md).
No publication contract or advertised budget is changed; native/desktop
acceptance remains open and V2/Part III remain inactive.

'''
path.write_text(text.replace(needle, addition + needle), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False, currentSessionAuthorized=False, retryNativeSessionAuthorized=False,
    preparation='Evidence/AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_freshness_01/qualification_session_v2.py',
    lastAttempt='Evidence/AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md', lastAttemptAccepted=False,
    sessionApprovalConsumed=True, lastAttemptCandidateCases=41, pairedCapturesReplayed=87,
    baselineChecks=31, genealogyRestored=True, finalChecksPassed=True,
    observerSamples=588, observerNonBadSamples=587, observerPassed=False, configurationPages=0,
    lastAttemptFailure='One Bad cyclic value; preceding retained Uncertain row ShiftHistoryTruncated; final Bad map was not retained',
    rootFailureCauseConfirmed=False, specificBadPathConfirmed=False,
    slowExpiryMismatchVerified=True, previousImplementationSlowExpiryMs=10000, publishedSlowExpiryMs=15000,
    freshnessCorrection='One unchanged profile drives planner and envelope; Good cutoffs/expiry enforced; excluded retained groups use slow limits; no timestamp renewal',
    badDiagnosticCorrection='Full rejected snapshot and all Bad paths/metadata retained before throwing',
    strictRootQualificationUnchanged=True)
v['offlineGates']['flutterTests'] = 645
v['offlineGates']['freshnessRegressionTests'] = 4
value['manifestV67']['s4Status'] = 'S4a initial scope accepted. S4b paced run: 41 cases/87 pairs pass; 587 non-Bad rows then one Bad. Slow expiry/envelope mismatch corrected offline, rejection capture fixed; genealogy/31 baseline restored. Native S4b/desktop pending.'
with path.open('w', encoding='utf-8', newline='') as stream:
    json.dump(value, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True, nativeAccepted=False, currentSessionAuthorized=False, genealogyRestored=True)))
