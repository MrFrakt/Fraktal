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
Current controller authorization and all S3e runtime gates remain open.
No S3e controller-changing operation is authorized. The completed S3d approval
is historical. No commit/push is authorized; shipping V2 remains inactive.
