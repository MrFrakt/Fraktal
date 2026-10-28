from pathlib import Path
import json

R = Path('C:/Users/SoftIndVM/Fraktal')
S = R / 'Specification/AllenBradley'
plan = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = plan.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: S4b discovery attempt failed; genealogy restored; Template retry prepared.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: S4b Template discovery passed; first root sample refused; genealogy restored.**
The owner-approved unchanged-image retry downloaded/returned to Run and passed
SDK, read-back and access audits. Dart passed Template/manifest discovery, then
refused its first root sample before readiness or candidate writes. The observer
ran for 2,745 ms including discovery; it did not retain the refused snapshot, so
root presence, identity and age cannot yet be distinguished. The runner restored
genealogy and the exact original five documents. **31/31 baseline cases**, all
final checks and preflight pass, with no dumps/fault clears/clock/power changes.
The session's approval is consumed. Read the
[sealed retry attempt](Evidence/AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md).

The read-only qualification tool now retains refused snapshots, root quality/age
and separate root/identity/age reasons before failing. Two new tests cover that
capture and the unchanged 1,000 ms boundary. No PLC/production client, coherence,
freshness or retry rule changed. The full pinned Flutter 3.47.5 /Dart 3.13.4 suite
passes **637 tests, 12 skipped**; analyzer and root gates pass. The unchanged
2,336-test PLC and Windows build bindings transfer by hash.

The [root diagnostic preparation](Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md)
uses a fresh workspace and the same ACD `7D75E86E…DEF056BF` /65% Capacity and
41/31-case scope. It may reproduce the refusal; no production correction or
native acceptance is claimed. A new session is not authorized. S4b/desktop,
S5-S7 and S3 physical I/O proof remain open; V2 inactive; no commit/push.

**Earlier, 2026-10-26: S4b discovery attempt failed; genealogy restored; Template retry prepared.**'''
plan.write_text(text.replace(previous, latest), encoding='utf-8')
amendment = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = amendment.read_text(encoding='utf-8')
old = '''the read-only parser correction has a recorded-byte reproduction and awaits
a separately approved retry. See the
[preparation](Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26.md). V2/Part III
remain inactive; no download is authorized by the contract choice.'''
new = '''the parser correction then passed discovery in the approved retry. That retry
refused its first root sample before candidate writes and again restored
genealogy with 31/31 baseline/final checks. The rejected snapshot was not saved,
so the cause remains open; the read-only tool now retains root/quality/age
diagnostics without changing production guards. See the
[retry attempt](Evidence/AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md) and
[diagnostic preparation](Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md).
V2/Part III remain inactive; no new session is authorized by the contract choice.'''
assert text.count(old) == 1
amendment.write_text(text.replace(old, new), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False, currentSessionAuthorized=False, retryNativeSessionAuthorized=False,
    preparation='Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_root_diagnostic_01/qualification_session_v2.py',
    lastAttempt='Evidence/AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md', lastAttemptAccepted=False,
    sessionApprovalConsumed=True, lastAttemptCandidateCases=0, baselineChecks=31,
    genealogyRestored=True, finalChecksPassed=True, templateDiscoveryPassed=True,
    lastAttemptFailure='First canonical root-sample check refused before readiness; rejected snapshot not retained',
    rootFailureCauseConfirmed=False,
    diagnosticCorrection='Read-only qualifier retains refused snapshot and separate root/identity/age reasons with root DataValue metadata; production rules unchanged',
    earlierDiscoveryFailure='Evidence/AB_S4B_CANONICAL_ATTEMPT_2026-10-26.md')
v['offlineGates']['flutterTests'] = 637
v['offlineGates']['qualificationDiagnosticsTests'] = 2
v['correctionProof'] = 'Ten recorded native S0 definitions and four tests; corrected discovery passed on the exact S4b image, then root-sample qualification refused'
value['manifestV67']['s4Status'] = 'S4a initial small-group scope accepted. S4b Template discovery passes after correction; first root-sample check refused before candidate writes, with verified genealogy rollback. Root diagnostics prepared; native S4b/desktop acceptance pending.'
with path.open('w', encoding='utf-8', newline='') as stream:
    json.dump(value, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True, nativeAccepted=False, currentSessionAuthorized=False, genealogyRestored=True)))
