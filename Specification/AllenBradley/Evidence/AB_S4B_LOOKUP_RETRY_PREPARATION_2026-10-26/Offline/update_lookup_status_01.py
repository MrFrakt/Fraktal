from pathlib import Path
import json

S = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
path = S / 'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text = path.read_text(encoding='utf-8')
previous = '**Latest, 2026-10-26: S4b Template discovery passed; first root sample refused; genealogy restored.**'
assert text.count(previous) == 1
latest = '''**Latest, 2026-10-26: S4b root-age refusal diagnosed; lookup correction prepared offline.**
The [diagnostic attempt](Evidence/AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26.md)
retains the refused snapshot: correct root identity, 976 Good values, no
Bad/Uncertain, but oldest fast-row age **2,065.752 ms** after **2,495.609 ms**
snapshot processing. The unchanged 1,000 ms freshness guard correctly refused
readiness; zero candidate cases ran. Genealogy downloaded back. Its first
baseline run passed 22 checks before an SFC HOME timeout and incomplete cleanup;
that failed record remains. Residual policy/MANUAL cleanup and one unchanged
baseline retry completed the originally approved rollback: **31/31**, original
five documents, policy, MANUAL/idle/logged-out final checks and preflight pass.
No fault clear, clock/power/vendor-state operation or dump. Approval is consumed.

Recorded-byte replay reproduces client cost with an immediate fake transport.
The correction indexes the already published count references once and checks
tier membership against a path's ancestors, replacing repeated whole-table scans.
It changes no values, types, reads, scope, tier, guard, timeout or freshness limit.
The same replay drops from 1,697.892/1,596.195 ms to **305.020/228.057 ms** for
first/second acquisitions, with the same 976 values, 1,986 requests and 596 groups
across two passes. These are offline profiling results; Echo acceptance is open.
The new scope-boundary equivalence test and full pinned SDK suite pass:
**638 Flutter tests, 12 skipped**, analyzer and a rebuilt Windows debug binary.
Unchanged PLC source preserves 2,336 AB tests; all 74 root tests/gates pass.

The [lookup retry preparation](Evidence/AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md)
uses the same image `7D75E86E…DEF056BF` /65% Capacity, a private package map,
fresh workspace/guards/backup and the same 41/31-case write scope. It is not
authorized. The native active-workload, configuration/detail, acquisition/scan
and desktop gates remain. S5-S7 and S3 physical I/O acceptance remain open;
V2/Part III inactive; nothing committed or pushed.

**Earlier, 2026-10-26: S4b Template discovery passed; first root sample refused; genealogy restored.**'''
path.write_text(text.replace(previous, latest), encoding='utf-8')
path = S / 'AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md'
text = path.read_text(encoding='utf-8')
old = '''genealogy with 31/31 baseline/final checks. The rejected snapshot was not saved,
so the cause remains open; the read-only tool now retains root/quality/age
diagnostics without changing production guards. See the
[retry attempt](Evidence/AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md) and
[diagnostic preparation](Evidence/AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md).
V2/Part III remain inactive; no new session is authorized by the contract choice.'''
new = '''genealogy with 31/31 baseline/final checks. The following diagnostic session
retained the rejected snapshot: correct identity and 976 Good values, but oldest
fast-row age 2,065.752 ms. It completed rollback after a retained 22-check baseline
failure, residual cleanup and one unchanged 31/31 retry. The offline client
lookup correction preserves all reads and production guards; native S4b remains
open. See the [diagnostic attempt](Evidence/AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26.md)
and [lookup retry preparation](Evidence/AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md).
V2/Part III remain inactive; no new session is authorized by the contract choice.'''
assert text.count(old) == 1
path.write_text(text.replace(old, new), encoding='utf-8')
path = S / 'AB_FROZEN_CONTRACTS_V2.json'
value = json.loads(path.read_bytes())
v = value['manifestV68']
v.update(nativeAccepted=False, currentSessionAuthorized=False, retryNativeSessionAuthorized=False,
    preparation='Evidence/AB_S4B_LOOKUP_RETRY_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/retry_lookup_01/qualification_session_v2.py',
    lastAttempt='Evidence/AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26.md', lastAttemptAccepted=False,
    sessionApprovalConsumed=True, lastAttemptCandidateCases=0, baselineChecks=31,
    genealogyRestored=True, finalChecksPassed=True, rootFailureCauseConfirmed=True,
    lastAttemptFailure='Oldest fast row age 2065.752 ms after 2495.609 ms processing; correct root, 976 Good values',
    originalBaselineFailure='22 successful rows then SFC HOME readiness timeout; cleanup and unchanged 31-case retry completed rollback',
    lookupCorrection='Ancestor Set membership and a derived count-reference index replace full-table scans; no omitted reads or rule changes',
    offlineLookupReplay=dict(firstBeforeUs=1697892, secondBeforeUs=1596195, firstAfterUs=305020, secondAfterUs=228057,
        requests=1986, groups=596, values=976, nativeTimingClaim=False))
v['offlineGates']['flutterTests'] = 638
v['offlineGates']['tierScopeBoundaryTests'] = 1
value['manifestV67']['s4Status'] = 'S4a initial scope accepted. S4b native root-age refusal diagnosed; client lookup correction prepared offline. Genealogy rollback completed after one retained baseline failure and unchanged 31/31 retry. Native S4b/desktop pending.'
with path.open('w', encoding='utf-8', newline='') as stream:
    json.dump(value, stream, indent=2, ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True, nativeAccepted=False, currentSessionAuthorized=False, genealogyRestored=True)))
