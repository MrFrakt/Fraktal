from pathlib import Path
import json

W = Path(__file__).parent
L = W.parent / 'session_01'
assert json.loads((L / 'coherence_flutter_01_exit.json').read_bytes())['exitCode'] == 0
assert '641 ~12: All tests passed!' in (L / 'coherence_flutter_01.log').read_text(encoding='utf-8')
S = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
path = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: S4b root-age refusal diagnosed; lookup correction prepared offline.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: S4b lookup retry passes 41 PLC cases; root-coherence refusal stops Dart.**
The [sealed attempt](Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md)
records 41/41 candidate checks and 87/87 independent raw-read replays, spanning
4,799-5,407 logical paths as occupied counts change. Dart passed readiness and
140 snapshots: fast age median 621.756 ms, maximum 745.063 ms; no Bad values.
Fifty-nine completed samples carried payload-free Uncertain rows. At the next
snapshot the root Status row was Uncertain (`coherence-unavailable`) without
a value, so the strict root check stopped the observer. Exact failed attempt
counters were not captured. No all-bank Dart pages, detail or candidate scan
acceptance was reached. The separate fixture completed its approved cases and
restoration. Genealogy rollback, original five documents, 31/31 baseline cases,
policy, MANUAL/idle/logout, final checks and preflight pass. Approval is consumed.

An offline counter that finishes publishing on a later scheduling turn
reproduces exhausted rapid retries; its regression failed on the sealed code.
The correction yields after an odd pre-counter, at most 1 ms and never beyond
the existing total deadline. The same three-attempt/one-second bounds and all
equal-even, read-window, type, identity and freshness checks remain. Uncertain
metadata for previously sampled rows now includes bounded failed counters/
windows, while preserving old sample ages and omitting payloads. Three new tests
cover phase completion, counter traces and deadline expiry during the wait;
existing planner tests also check diagnostic delivery. The exact native attempt
pattern remains unknown; this is a reproduced retry weakness, not a proven
explanation of that particular Echo refusal.

Full pinned Flutter 3.47.5 /Dart 3.13.4 gates pass: **641 tests, 12 skipped**,
analyzer, enforced lockfile and rebuilt Windows debug binary. PLC source/image
is unchanged, preserving 2,336 AB tests through 373 bindings and both v38
builds/read-backs/65% Capacity; all 74 root tests and gates pass again.
The [paced coherence retry](Evidence/AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26.md)
uses a fresh workspace and the same 41/31-case write scope. No new session is
authorized. Strict root qualification remains: no unavailable identity is
counted as a successful sample. S4b native/desktop, S5-S7 and S3 physical I/O
acceptance remain open; V2/Part III inactive; nothing committed or pushed.

**Earlier, 2026-10-26: S4b root-age refusal diagnosed; lookup correction prepared offline.**'''
path.write_text(text.replace(previous, latest), encoding='utf-8')
path = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
needle = '## AB §1, §2.1 and §4.1 — reference profile'
assert text.count(needle) == 1
addition = '''The lookup retry then passed 41 candidate cases and 87 raw-read replays.
Dart met the original freshness limit for 140 snapshots, then stopped on a
payload-free Uncertain root Status row. Genealogy and 31 baseline/final checks
were restored. The [sealed attempt](Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md)
claims no native S4b or desktop acceptance. A bounded pacing correction and
failed-attempt metadata are [prepared offline](Evidence/AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26.md),
with the same attempt/deadline/quality rules and strict root qualification.

'''
path.write_text(text.replace(needle, addition + needle), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False, currentSessionAuthorized=False, retryNativeSessionAuthorized=False,
    preparation='Evidence/AB_S4B_COHERENCE_RETRY_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_coherence_01/qualification_session_v2.py',
    lastAttempt='Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md', lastAttemptAccepted=False,
    sessionApprovalConsumed=True, lastAttemptCandidateCases=41, candidateChecksPassed=True,
    pairedCapturesReplayed=87, minimumPairedPaths=4799, maximumPairedPaths=5407,
    baselineChecks=31, genealogyRestored=True, finalChecksPassed=True, observerSamples=140,
    observerPassed=False, configurationPages=0, rootFailureCauseConfirmed=False,
    lastAttemptFailure='After 140 fresh snapshots, root Status became payload-free Uncertain/coherence-unavailable; failed attempt counters unrecorded',
    nativeLookupFreshness=dict(medianAgeMs=621.756, maxAgeMs=745.063, maxAcceptedRowWindowUs=8455),
    coherenceRetryCorrection='Yield after odd pre-counter within original deadline; unchanged max 3 attempts/1 second; bounded counter/window traces in existing Uncertain row metadata',
    coherenceCorrectionProof='Later-turn publisher regression fails before pacing and passes after; native failed-attempt pattern remains unrecorded',
    strictRootQualificationUnchanged=True)
v['offlineGates']['flutterTests'] = 641
v['offlineGates']['coherenceRegressionTests'] = 3
value['manifestV67']['s4Status'] = 'S4a initial scope accepted. S4b lookup retry: 41 checks/87 pairs pass, Dart stops after 140 snapshots on root coherence refusal; genealogy/31 baseline restored. Paced retry and diagnostics prepared offline; native S4b/desktop pending.'
with path.open('w', encoding='utf-8', newline='') as stream:
    json.dump(value, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True, nativeAccepted=False, currentSessionAuthorized=False, genealogyRestored=True)))
