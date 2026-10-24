# S3d — AlarmLog and StateFlags preparation

The [independent inventory](AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json)
was recorded before implementation from the frozen legacy projection and the
accepted S3c inventory. It adds **1,478 paths**, for **2,125 total**: 1,469
AlarmLog paths and nine StateFlags paths. The plan's 1,469 figure describes
AlarmLog alone; two flags add eight fields and StateFlagCount adds one.
Only the five approved D2 bound differences remain permitted.

Offline compiler/read-back/access, tests and measured Capacity pass. S3d
runtime equivalence, regression/reset coverage, native structure-size and
scan measurements remain open. No S3d controller-changing operation is
authorized or performed. Shipping Part III/V1 remain authoritative; V2 is
an approved target and remains inactive.

## PLC ownership and record layout

The existing alarm owner remains the sole append/close/reset owner. Publication
mirrors all 16 active and 64 ring slots, including empty slots, RingHead and
Blocking. It changes no lifecycle, shelving, release or reset predicate.
Unconditional existing state-flag evaluation still owns each value and its
change timestamp; publication adds no latch or poll accumulation.

The cyclic root contains AlarmLog.Active/Ring and StateFlags. Rationalization
text is a separate read-only metadata record bound to the discovered root
through the existing [V6.2 mechanism](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md).
There are now two explicit bindings: sequence definitions and alarm metadata.
Metadata publishes all 31 rationalization rows at the oracle's logical extent,
with a root-published MetaCount. This adds no station declaration or name
inference to a runtime client. Tiered transport scheduling remains S4 work.

Native event Description/SourcePath and metadata OperatorAction/Consequence
use Core STRING(255); IoTag/IoAddress use STRING(80); flag Key uses STRING(120).
ComeAt/GoneAt/Since use LDT nanoseconds with TIMESTAMP annotations, including
unset zero. Duration uses DINT milliseconds. Logical array bounds remain
one-based here. Private input caches remain outside public whole-read records.

Text and electrical joins reuse the existing PLC diagnostic resolver on
changed reason/source/role inputs. SourceModuleId is the legacy manifest
ordinal (1=root, 2=first CM), distinct from the diagnostic resolver's CM
ordinal. Calendar conversion runs only when a stored date/time pair changes.
S3d extracts the existing calendar algorithm into one shared generated routine;
diagnostics, alarm timestamps and flag timestamps call it. S2/S3a/S3b/S3c
emission remains byte-identical. A reason-zero event still retains its valid
timestamp. Invalid calendars or LDT overflow invalidate publication rather
than inventing a representable date.

## Acceptance preparation

The independent oracle reads the existing chart, recipe, alarm columns and
state flags through their owning readers. The generic discovery reader itself
is unchanged. Paired reads keep the equal-even entire-scan generation proof,
100 attempts and five-second budget, with a separate 4,000-byte observation
connection and the existing 500-byte mailbox framing. A 2 MiB read was qualified
in S0; that does not establish S3d's larger same-scan read plan. The actual
published record sizes and acquisition budget must be measured after deployment.

The inherited 31-row fixture keeps its commands, stimuli and cleanup. It adds
read-only observations before/after its existing blocking OperatorReset calls,
alongside the inherited decision, held/fault and 21 sequence captures. The
prepared audit requires all 2,125 paths/types, all rendition coverage, active
and closed events with duration, state-flag transitions and one-reset release
of Blocking. It records observed event states and ring wrap separately;
offline model coverage must not be reported as controller coverage. A failed
observation cannot block the parent's existing cleanup writes.

Model execution covers ACTIVE/WAIT_RESET/closed states, ring wrap, slot reuse,
source/I/O joins, reason-zero timestamps, flag changes, metadata equality and
unchanged timestamp caching. The initial model run incorrectly used its
default DINT arithmetic for native LINT conversion. The harness now applies
the same 64-bit model used by S3b and checks all DINT intermediates remain in
range. Native builds independently validate the generated code. That failed
run and a test-launch import-path failure remain in preparation evidence.

## Scope and current preparation

Full-Core event Category, ResetAt and ShelvedUntil have no legacy oracle paths
or stored columns; they remain explicit gaps. Event time-quality fields retain
the legacy binding's false values. StateFlag.Stale remains false because its
owner evaluates every declared flag unconditionally. The fixture has no EM
or concurrent sequence branch. Earlier Core gaps remain as recorded for
S3a/S3b/S3c; this stage makes no full-Core or physical acceptance claim.

Both v38 targets build and read back equivalently: 104 UDTs, seven AOIs,
132 tags, one program/task, 46 executable bodies, the 21-step SFC graph and
29,346 authored initial values. The prepared ACD was reopened/rebuilt/exported
equivalently. S2/S3a/S3b/S3c accepted hashes and sealed snapshots are unchanged.
The AB suite passes 2,062 tests. Source, both native exports and prepared
export pass access audits, including both metadata bindings.

Prepared source SHA-256:
`03E0775EDD8A1A22D88D198D4D3CE2B7C19A2F2029A40E3C428CB838FC2EE962`.
Prepared ACD pin:
`E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D`.

Automatic Studio Capacity is **1,290,016 used / 1,855,712 available /
3,145,728 total Blocks**, displayed **41%**, +182,464 over S3c. Two stable
offline samples, exact source preservation and review-process closure pass.
Blocks are not assumed bytes. This is the offline estimate, not online memory
or a substitute for completed download and native scan measurements.

Fresh read-only guards/preflight/final checks verify genealogy on Echo 601FC87B,
Run, not faulted, Remote, scanning, actual MANUAL=1/idle, logged out, not
restoring and all five saved documents equal live. The original preflight is
recorded once and verified; it is never overwritten. No backup/deploy marker
or current authorization exists for S3d. The completed S3c authorization is
historical. A new exact-session approval is required under AGENTS.md §3a.
No commit or push is authorized.
