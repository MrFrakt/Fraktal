# S4b freshness retry attempt — 2026-10-26

**41 candidate cases and 87 paired comparisons pass. The Dart observer stops
after 884 completed samples when three coherence attempts end in one PLC
publication phase. Genealogy, the five original documents and all 31 baseline
and final checks are restored. S4b desktop acceptance remains open.**

The owner answered “Approve guarded S4b freshness retry” to
`call_9f47a022b96c480b81af9d85ec59f551:0`, approving the
[sealed freshness retry](AB_S4B_FRESHNESS_RETRY_PREPARATION_2026-10-26.md).
This session completed with verified rollback. Its authorization is consumed.
Local date is October 26; final UTC timestamps fall on October 27.

## Passed

- Fresh identity/service/listener, MANUAL/idle/logout/document guards, backup,
  SDK audits, download/Run, read-back and external-access audits pass on Echo
  601FC87B, 1756-L81E v38.011, 127.0.0.1 slot 0.
- Image `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`,
  source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`.
  Exact-image offline Capacity remains 65%: 2,066,100 used /1,079,628 available
  /3,145,728 total Blocks. Fresh backup SHA256 is
  `31ECCF8EB8D9D213DAA45F4EB9679A6ABE806A16CFC8B1729A8036C5C49A86BF`.
- Discovery/readiness passed. **884 completed cyclic samples** contained no
  Bad values; 806 had only Good values and 78 had payload-free Uncertain rows.
  Fast sample age median/p95/maximum: **676.3125 /777.784 /943.021 ms**.
  RPC median/p95/maximum: 688.9735 /791.235 /956.691 ms. The largest accepted
  row window was **9,906 us**, below its declared 10,000 us mutation interval.
  Total observer duration was 600,789 ms.
- **41/41 candidate cases** pass: 31 main, two Access and eight configuration
  and set-store checks. Changes and policy were restored; the isolated store
  was empty. **87/87 comparisons replay** independently from saved native
  record bytes against the oracle, including the configuration view. Occupied
  counts yield **4,799–5,407 paths**. These do not establish Dart page acceptance.
- Pinned genealogy was downloaded from a hash-checked copy. The original
  remains `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Exact original five host documents, **31/31 baseline cases**, policy, MANUAL
  cleanup, final checks, preflight and baseline timing pass. Final state is
  Run, not faulted, scanning, MANUAL/idle, logged out and not restoring, with
  original policy and all five saved/live documents equal.
- No dumps, fault clears, clock changes, power operations, vendor-state edits
  or Echo hard kills. Only the SDK-saved working ACD differs from its 744
  source bindings; original image/source and genealogy hashes remain pinned.

## Failed and skipped

The next root Status acquisition exhausted three attempts in **6,237 us**:

| Attempt | Observation | Before | After | Window (us) |
|---|---|---:|---:|---:|
| 1 | Revision changed | 123678 | 123679 | 1460 |
| 2 | Odd before | 123679 | — | 457 |
| 3 | Odd before | 123679 | — | 355 |

The actual trace shows all retries ended within one ongoing publication
phase, shorter than the declared 10 ms interval. Root identity was therefore
Uncertain (`coherence-unavailable`), omitted from values, and 1,376.901 ms old.
Other Good fast samples were 688.556 ms old. The strict fresh-root check
correctly refused it. No torn row or cached identity was accepted as Good.

The inherited fixture completed its approved cases/restoration before the
wrapper collected the observer failure and rolled back. This is a failed
concurrent-observation qualification despite passing PLC cases. All-bank Dart
configuration pages (zero reached), detail reads, candidate idle equivalence,
generic acquisition and candidate scan measurement were not reached. Desktop
rendering/connection acceptance remains open.

## Next

Prepare an explicitly larger bounded retry effort for the desktop plan, while
retaining the one-second deadline, equal-even proof, 10 ms accepted window,
published freshness limits and strict root checks. Three attempts did not
span the measured publication phase. Any proposed increase must be stated in
the next preparation and authorization; this record does not approve it.

An offline audit also found age bookkeeping to correct before the next run:
record conservative source age from before the accepted pre-counter read,
and stop the processing-time bracket before calculating response ages. The
audit is archived. These corrections have not been applied in this record.

Offline preparation results remain 2,336 AB /74 root /645 Flutter tests
(12 skipped), Windows build, analyzer, locked dependencies and both v38
builds. V2 and Part III remain inactive. S4b, S5–S7 and S3 physical I/O proof
remain. Nothing is committed or pushed. No credentials or ACD binaries are
archived; all failed runs are preserved.
