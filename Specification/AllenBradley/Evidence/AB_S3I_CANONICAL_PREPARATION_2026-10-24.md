# S3i canonical Line/shift preparation — 2026-10-24

**Offline gates passed; native session approval required. No controller operation
was performed. S3i and the overall canonical-publication plan are not complete.**

The owner approved the remaining-S3 contract and dependent offline work in
question `call_2e1575c86f2947c59925e347cd3d0109:0`, answering “Approve contract
and offline work (recommended)”. The exact reviewed contract, inventory and
approval are sealed in [inventory evidence](AB_S3I_CANONICAL_INVENTORY_2026-10-24.md).
That approval expressly excludes downloads. V2 remains an inactive target.

The opt-in stage 11 publishes sixteen previously missing frozen Line/shift
paths, two additional Core Line status fields, and eight physical V3 history
slots with 21 fields per occupied row. The generic reader obtains occupancy
from PLC-published `ShiftHistoryCount`. The finite comparison maps only the
approved `OwnerId` → `Owner` and `LastUpdatedAt` → `LastUpdate` spellings for
this slice. It preserves exact types and values, with no tolerance or ignored
paths. The remaining frozen census after this slice is 133 paths: 126 mailbox/
report and seven production/Features fields; this is inventory, not runtime
acceptance. Fieldbus publication remains a separate S3j obligation.

The Line owner samples update time quality on commit into private LineStateV2.
The original six-member prefix remains stable, and old profiles still emit
LineStateV1 byte-for-byte. Canonical history reuses the existing Core OEE
Float32/UInt32 routine. It widens seconds before multiplication, preserves
unsigned count bits, converts UTC stamps to native LDT without floating-point
rounding, and refuses out-of-range stamps. `SchemaVersion` uses the approved
V2 DINT carrier with a UInt16 annotation. Closed rows refresh at the owner's
closure/count marker and republish on first scan; calendar policy remains
with the existing Line owner.

| Artifact | SHA-256 |
|---|---|
| Generated candidate `s3i_bench_05.L5X` | `0F3A5F6DD762BED3819404025DAF6D5703511807B440C4988EACF5E494EC72C3` |
| Prepared `s3i_canonical.ACD` / pristine Capacity review copy | `A5FAFA46CB5DECCF2EF2C5D6B069B19CB772A42B876A70CFA2E73506B7E36C42` |
| Prepared read-back | `C6C8A39E36202B5BD83F27324B9F0EC760A3835A08742BAC398F368055029146` |

Work directory:
`C:/work/fraktal-ab-s3i-20261024/prepare_d6df75f72d02435aab2ef3fbd7ea986d/`.
The ACD is not archived in Git; source/read-backs, hashes and helper sources are
in the append-only [payload manifest](AB_S3I_CANONICAL_PREPARATION_2026-10-24/manifest.json).

| Gate | Exact result |
|---|---|
| AB suite, discovery from binding tools | **2,178 tests, OK**, 335.169 s (`ab_suite_02.log`) |
| Root consistency/spec/contracts tests | **74 tests, OK** (`root_tests_02.log`) |
| Spec / contracts / strict consistency / whitespace | Pass; zero consistency warnings |
| Native v38 EchoController and PhysicalController | Clean import, zero warnings/errors, builds accepted |
| Both native exports and reopened prepared ACD | Equivalent: **58 executable bodies, 43,648 authored initial values, 21 SFC steps** |
| Effective access | Pass on all three read-backs; result/frame read-only, saved owners inaccessible, no added external write target |
| Previous stages | Eight earlier stages, S3h frame-off and accepted frame source regenerate to their pins; all **88 accepted S3h pairs** replay unchanged |
| Source closure | **170 source bindings**, six changed and eight added relative to accepted S3h preparation |
| Session authorization | Three commands refused before guard/SDK access with all approval flags false |
| Studio automatic Capacity | **2,763,512 used / 382,216 available / 3,145,728 total Blocks, displayed 87%** |

Capacity increased by **83,380 Blocks** from the accepted S3h frame image
(2,680,132 used). This is an exact-image offline Studio measurement. The
empirical forecast, now calibrated through S3h, predicts 2,769,579 used Blocks
(6,067 above measured, about 0.22%). Its planning budget is 3,087,663 Blocks,
leaving 58,065 within that budget. This advisory fit does not replace the
measured gate or settle later release-report growth; the earlier S3h warning
remains in its sealed evidence. No feature, width or validation was cut.
Native scan/overlap, record-size and retention results are not yet available.

Eight fixed first-scan **publication** vectors are prepared: empty history;
full history with unscheduled/manual rows and unsigned/Float32 wrap; unchanged
closure-marker caching; pending calendar with latched history targets; partial
history; empty-after-history clearing; exact LDT upper limit; and overflow
refusal. They save the two fixed Line owner records, temporarily set those
records, call the production publisher, capture read-only results, restore
both owners byte-for-byte in the same scan and rebuild normal publication.
The emitted ST passes its independent model/reference checks. **These vectors
do not simulate the calendar producer or establish natural calendar lifetime,
closure or physical retention acceptance.** Those remain explicit open gates.

The proposed native session is limited to local Echo **601FC87B**, 127.0.0.1
slot 0, Emulate 5580/v38.011, Remote keyswitch and no fault:

1. Fresh service/listener/identity/mode/fault checks; guarded MANUAL normalization
   through LOGIN/SET_MODE/LOGOUT only when required; idle/logged-out preflight.
2. Fresh backup, audited as `Save As`; Program/download/Run of the pinned ACD.
   The eight first-scan vectors above run once per first scan.
3. Restore five live documents; run the inherited 41 fixed candidate cases
   with read-only Line/trace/configuration equivalence captures. Measure all
   current logical paths, native sizes and task scan/overlap.
4. Roll back using a hash-checked **copy** of the immutable genealogy original
   `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`;
   restore five documents and run 31 baseline cases; MANUAL cleanup/final checks.

The session helper binds exact image, fresh backup, measured Capacity,
read-back and current authorization. The HMI login guard remains intact.
Fault clears, clock changes, firmware/network changes, power-state operations,
hard kills and vendor-state edits are excluded. Avoid hard-killing a faulted
emulator; use orderly shutdown and inspect dump files before rebooting.
No credential, ACD, vendor state or crash dump is archived.

Failed runs remain evidence: the model caught a mistaken LDT upper remainder;
compiler attempts caught BOOL/DINT and array-element operand errors; read-back
caught an unapproved native UINT carrier/format; the first full suite caught
an obsolete stage-11 rejection. The final image uses the approved DINT/UInt16
mapping and all final gates above pass. A failed preparation audit script and
encoding failures while updating working notes and checking a raw Windows
test log during sealing are also retained, followed
by their successful corrected runs. Generated L5X was never hand-edited.

HMI/Flutter gates are inapplicable because no HMI source changed. Controller
runtime, actual press declaration in all three AUTO renditions, S3j/S3k,
shipping per-row/group coherence, S4–S7 and the owner’s persistence/gateway/
hardware decisions remain open. The migration observation frame now includes
the two Line owner records; it remains read-only, undiscoverable as a root,
and scheduled for retirement at S6. No commit or push was made.
