# S3e Access, data policy and shared-ring audit preparation

S3d is accepted; see its [runtime evidence](Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md).
The independent [S3e inventory](AB_CANONICAL_PUBLICATION_S3E_INVENTORY_2026-10-22.json)
adds 29 Access paths to 2,125, for 2,154 total. Policy.Required has the approved
D2 lower bound zero. Classes retain their oracle logical extent, controlled
by the PLC's ClassCount. No credentials or registration hashes/salts are public.

The audit is an enrichment of Description/SourcePath on occupied MESSAGE rows
in the existing 64-slot AlarmLog.Ring. It adds no second ring and no paths.
The original Access provider remains the only session/policy/audit owner.
The published audit text must equal the oracle, including actor/action, data
capability detail and automatic shelving markers. Replacement by an ordinary
alarm must clear the enrichment. Changed-input caches avoid reformatting rows
every scan. Stage S3d's output and all earlier image hashes must stay unchanged.

Login remains plain PIN through the mailbox; no canonical client may consult a
station declaration or compute the legacy gateway prehash. LoginBusy and the
result-sequence word are PLC facts. Existing helper values remain published
where required by the oracle; this does not activate prehashing in a client.

The result-sequence word uses native DINT with BITSTRING32 metadata; the generic
reader masks the complete word and exposes UInt32. The old reader validated the
annotation but left a signed DINT value. High-bit vectors now test the correction;
all five earlier native images and their sealed snapshots remain unchanged.
The working inventory records this explicit logical type rather than inferring
it from the frozen sample's small positive integer. Its first work copy is retained.

Model tests execute generated ST against the owning session/policy/audit oracle:
busy/failure/authentication/logout, all policy levels, live class extents and
unknown keys, signed decimal extremes, arbitrary actor bytes (ASCII replacement),
automatic shelving, shared-slot replacement, schema/occupancy changes and cache
reuse. Ordinary alarms re-enter the common text resolver when enrichment expires.
The alarm/Access owners' append, reset and authority logic are unchanged.

Both v38 targets build/read back equivalently: 111 UDTs, seven AOIs, 133 tags,
one program/task, 48 executable bodies, 21 SFC steps, 352 descriptions and 30,949
authored initial values. Source, both exports and prepared ACD export pass access.
The full AB suite passes 2,078 tests in 280.759 s. The generated source SHA is
3BFFCEADB98EC7B7B7AA05550202CC187C736A8C2B22C75B7B7D158BE4F5AD87;
the prepared ACD pin is 95E85B507387A548553688C1B5CCF52D7D99B35751C68F1B02DE92AC2A1B240B.

Automatic Studio Capacity is 49%, 1,568,852 used / 1,576,876 available /
3,145,728 total Blocks, +278,836 over S3d. The held-out six-sample forecast was
1,439,517 (error -129,335, -8.2439%), planning budget 1,681,312. It remains
advisory. The measured gate is automatic, source-preserving and exact-image.
This observation is not added to calibration before accepted runtime.

The planned fixture keeps the inherited 31 rows and adds two explicit checks:
one unknown-user login refusal before the existing valid login, and one read-level
edit/restoration on the last declared class. Restoration is in a finally block;
test failure cannot bypass it. Six read-only Access phases cover Busy, failure,
authenticated authority, logout and changed/restored class policy. The unknown
identity must not be registered. Command arguments are never observation metadata.
These checks require explicit inclusion in the next approval. Expected planned
rows total 64 (31 + 2 candidate, 31 baseline); per-tag write calls are unmeasured.

All preparation gates pass, including 74 root tests in 2.065 s, spec/contracts,
strict consistency (zero errors/warnings) and whitespace. Fifteen predecessor
seals / 2,628 artifacts verify unchanged. The exact-artifact
[preparation record](Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22.md) seals the
source, native outputs, receipt, false approval template, helpers and runbook.
The subsequent owner-approved session is accepted below. Its authorization is
consumed; future controller work needs separate approval. No commit/push is
authorized; shipping V2 remains inactive.

## Accepted runtime, 2026-10-22

The original full candidate fixture passes 31 inherited rows and both fixed
Access checks. All 2,154 values/types match at four decision, 14 held/fault,
21 sequence, eight reset and six Access captures, plus idle. All 54 paired
captures and the generic seven-module snapshot replay identically. Busy,
failed/successful login, logout, manual/class-policy transitions and audit
actor/action text pass; ring wrap and closed-event duration are observed.
WAIT_RESET is not runtime-observed. Native high-bit counter injection, arbitrary
actor bytes and data-denial capability detail remain model-only coverage.

The first coverage audit incorrectly tested Required[1] for MANUAL. Native
dispatch and enforcement use zero-based gate 2. A temporary observer made the
same assumption and stopped an unnecessary repeat after one inherited row and
two Access checks; the comparisons themselves passed, and cleanup restored
documents/policy. The corrected audit derives the index from
fraktal_ab_access.GATES[MANUAL_COMMAND], finds both 0/1 at Required[2] in the
original full captures, and accepts them without changing any coverage criterion.
Both erroneous variants and outputs remain archived. The temporary observer/
test changes were restored byte-for-byte; all 76 prepared root sources match.
The corrected post-session audit is a versioned runtime helper, not a PLC change.

Baseline passes 31/31 on its first run. Total recorded rows are 67: 31 + 2 in
the accepted candidate, 1 + 2 in the partial repeat, 31 baseline. Three are extra
to the planned 64. Two executions of the fixed vectors add six known mailbox
commands; two MANUAL normalizations add six more. Individual tag-write calls
are unmeasured. The equal-even proof and 100-attempt/five-second limits remain
unchanged; accepted attempts range 1-41, using two guarded read-only connections
and V6.2 metadata coherence. The tighter acquisition margin remains an S4 risk.

Native Template sizes equal complete payloads: root 77,856 bytes, sequence
definitions 7,308, alarm metadata 16,616; total 101,780. Twenty TASK samples
give candidate median/range 817 us / 816-817, cumulative max 4,033 us, zero
overlaps. Restored genealogy is 99 us / 99-100, max 1,167 us, zero overlaps.
Workloads/history differ; these do not isolate publication cost. Measured
Capacity is added as the seventh forecast sample only after runtime acceptance.

SDK/read-back/access gates pass for backup, candidate and restored genealogy.
Final checks verify Run, not faulted, Remote, scanning, actual MANUAL=1/idle,
logged out, not restoring, all five saved/live documents equal, original policy,
unchanged preflight and immutable original. See
[runtime evidence](Evidence/AB_S3E_CANONICAL_RUNTIME_2026-10-22.md).
S3f preparation is next. No fault clear, clock change, commit or push occurred.
