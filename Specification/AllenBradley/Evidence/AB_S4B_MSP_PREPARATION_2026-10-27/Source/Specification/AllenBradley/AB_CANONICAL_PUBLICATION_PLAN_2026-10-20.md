# Fraktal/AB canonical publication — implementation plan

Non-normative plan, 2026-10-20. It executes the decisions in
[AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md](AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md)
(D1–D9). Where the two differ, the design note's decisions win and this plan is
corrected. Part III stays authoritative until a stage amends it.

## 1. Goal and definition of done

AB reaches the HMI the way TC3 and TIA do:

- the PLC publishes the canonical Core module tree;
- one generic session client discovers it through the controller's own Symbol
  and Template objects plus the manifest, with no station declaration at
  runtime.

The work is done when **all** of the following hold:

1. **Value equivalence.** A generic reader recovers every canonical path the
   Python projection serves today, with identical values and types. The only
   exceptions are the five D2 array-bound corrections and the explicitly
   versioned [owner-approved S3f corrections](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md):
   the 110 enumerated Core types, bounded page windows, 12 missing Core fields,
   PLC-owned revision/timestamps and validated provider responses. The owner also
   approved the [200 S3g numeric corrections](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
   on 2026-10-23, including exact Core Float32 arithmetic and UInt32 bucket wrap. The
   [224 dependent value paths](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
   are also approved: 64 OEE validity flags and 160 profiler row values. No general
   numeric coercion, ignored path or tolerance is permitted. The owner also approved
   the [36 S3h type corrections](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md),
   including unset Part timestamp empty string to zero; the other 242 added paths
   retain exact values and types. The owner also approved the finite
   [remaining-S3 corrections](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md)
   on 2026-10-24: 122 path spellings, 13 frozen type corrections and the
   enumerated command/status/history schema and arithmetic consequences.
   The exact inventory and approval are bound in S3i inventory evidence. The frozen genealogy
   capture (4,437 legacy paths) stays immutable; page-window shape and additional
   Core fields have their own explicit S3f oracle. This holds for genealogy and
   the press declaration in all three AUTO renditions.
   The separately versioned [S4b read-only configuration view](AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md)
   was approved on 2026-10-25. Its explicit additional data-product path family
   has its own independent oracle; the frozen path comparison stays exact. It
   resolves configuration paging without making unsecured direct mailbox writes.
2. **Desktop.** The desktop HMI connects with `cip://<controller>` through a
   generic `CipSessionClient` in `fraktal_opcua_client`. It is read-only unless
   the target has a commissioned CIP Security policy (D9).
3. **Web.** The Dart gateway serves Web clients from the same client
   (`--plc-endpoint cip://…`), with Core §14 writes over `wss://`.
4. **Retirement.** The Python projection, the Python gateway and the Dart
   spike (`HMI/lib/data/cip/`) are removed. §3.8b persistence, configuration
   sets and the host-event sink have new owners (S6). The old generated
   contexts are gone, and the canonical structures are the working storage.
5. **Documents.** Part III, frozen contracts V2, `OPCUA_TRANSPORT.md`,
   `AGENTS.md`, the AB README and the new-station guide describe the final
   behaviour. Every gate is green.
6. **Acceptance.** Echo acceptance passes per stage; physical and CIP Security
   acceptance pass on a v37+ capable controller (S7).

## 2. State at hand-over (2026-10-20)

**Latest, 2026-10-27: refill preserves the workload; desktop remains open; body batching is prepared.**
The [sealed refill attempt](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes **41/41 cases**, **87/87 exact
independent raw-record replays** (4,799–5,407 paths), the separate busy witness
and **3,144 entirely Good Dart samples** (zero Uncertain/Bad). Observer age
median/p95/max is **265.8085 /337.691 /523.733 ms**, maximum accepted row window
**9,995 us**. Four configuration queries/targeted details complete; all 218 Part
calls succeed in 222 attempts. Desktop initially LIVE with seven modules then
fails `after-overview`: source **996,563 us**, RPC **1,610,859 us**, server bracket
**1,183.292 ms**, transit **428,567 us**, received **1,425,130 us**, local **3,015 us**,
effective **1,428,145 us** against **1,000,000 us**. Worker acquisition is
**1,125,722 us**, queue **50,819 us**, projection **2,452 us**, path expansion
**18,215 us**, frontend validation **2 us**. These measured intervals do not
isolate a host/network/PLC cause. Zero views are accepted. Independent
configuration/idle/generic acquisition/final timing are skipped. TASK maximum
**9,003 us /zero overlaps** is observational, not final scan acceptance.
Genealogy/five original documents/**31/31 baseline**/all final/preflight checks
pass. The completed session's authorization is consumed. S4b remains open.

The [read-only timing controls](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md) read the restored baseline. Scalar
request medians are **0.891 ms** (Dart CLI), **1.120 ms** (Flutter without widgets),
**1.2765 ms** (simulator UI); Flutter maxima **13.073 /16.290 ms** can exceed
the 10 ms proof window. They do not establish the cause of prior refusals.
Python and Dart each validate 20 native MSPs/60 reads. One Dart packet spans
a sample-counter change, so packet atomicity is not assumed. No tag writes,
mode/download/clear/clock/power changes occur. These are not canonical/UI acceptance.

The [prepared MSP correction](Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md) batches only the count/body reads of a
fitting row **between separately completed pre/post counter requests**. No
MSP execution-order guarantee is assumed; reversed-body execution retains exact
golden values/types and verified outer bracketing. An earlier counter-folding
prototype is archived but excluded. Every embedded service is a bounded symbolic
Read Tag Fragmented request to the Message Router; nested/write/connection-manager
wrappers are refused. Queued bytes are copied before validation and queuing. All reply
counts/offsets/services/types/handles/extents are strict. Large or data-dependent
primitive rows keep the original reader. Unsupported or partial transfers fall
back inside the original attempt/window/deadline; malformed replies refuse.
The existing equal-even/elapsed-window proof, 20 attempts/one second, source
ages, fast 1/3 s and slow 7.5/15 s Good/expiry limits remain unchanged. Read-only
policy, four-row refill/leases and count/Status barriers remain.

**685 HMI tests pass /12 skipped**, **73 focused tests**, analyzer/Windows/
enforced lockfile on Flutter **3.47.5 /Dart 3.13.4**, identical **320-input mirror**.
Four existing HMI source/test files change and one 16-case module is added;
the existing pool test adds queued-input mutation coverage. Recorded-wire replay
uses **711 packets** for **810 logical reads**
and **237 groups**, preserving all **976 consumed values/types**.
These are model counts, not native full-tree timing. Fourteen busy-witness/six
Part trace tests, fresh SDK/authorization/workflow/readiness/refusal gates and
**74 root tests** pass. All **373 PLC/gate bindings**, **2,339 AB tests**, both v38
build/read-back/access/SDK gates and **65% Capacity** transfer by hashes.

A fresh same-image session is prepared and **not authorized**: fresh guards/
backup, MANUAL normalization if needed, Program/download/Run; inherited 41 cases
with the proven busy witness and corrected read-only observer, existing traces/
TASK monitoring; strict desktop and remaining comparisons/acquisition/scan if
ready; genealogy/original documents/31 baseline/final checks. No new PLC writes.
Fault/TASK-counter clears, clock/power/vendor-state operations are excluded.
Native improvement remains unproven; V2/Part III inactive; no commit/push.
S5 gateway/installer, S6 retirement/persistence/events/capacity and S7 physical/
CIP Security including real I/O remain.

**Earlier, 2026-10-26: S4b reader passes functionally; scan review and desktop remain open.**
The [sealed reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md) completes
41/41 candidate cases, 87/87 independent raw-record replays, and **902 entirely
Good cyclic samples**. No Bad/Uncertain/rejected-root sample occurs. Fast age
median/p95/max is 684.1535 /774.077 /848.974 ms; maximum accepted row window
9,594 us remains below 10,000. All four read-only configuration pages (30 live
entries and four entries in each of three model banks) match the independent
oracle in **1,100 scalar values/types**. Targeted detail reads, exact idle
equivalence on **5,407 paths** and generic acquisition of 5,407 values/seven
modules pass. The unchanged PLC image still measures 65% offline Capacity.

Native TASK median is 966 us, cumulative maximum **10,033 us**, **one overlap**
on its 10 ms period. This keeps the scan review open despite successful runner
and functional results. All 87 paired captures already contain that same
maximum/count, starting at the earliest recorded pair (probe sample 2,350);
none shows another overlap. Their LastScanTime ranges 944–1,144 us, median
973 us. The initial event's location/cause is unrecorded; neither host jitter
nor PLC initialization is established as the cause. Do not clear counters or
faults, waive the finding or claim zero overlaps. Instrument from Run through
discovery/readiness and the workload before deciding on a correction.

Genealogy, the original five host documents, 31/31 baseline cases, policy,
MANUAL/idle/logout, final checks and preflight pass. Baseline scan is 99 us,
maximum 1,167 us, zero overlaps. No dumps, fault clears, clock changes, power
operations or hard kills. Authorization consumed. V2/Part III stay inactive;
desktop rendering and scan review remain S4b gates, followed by S5–S7 and S3
physical I/O proof. No commit/push. The 647-test pinned Flutter result (12
skips), analyzer/Windows/lockfile and 2,336 unchanged AB tests remain bound.

A preliminary pre-S6 syntax census of the 373 bound Python files is archived
with this run: 54 tools/53 test modules have direct legacy references; the
transitive import closure is 155 tools/129 tests. These include oracle,
metadata and test dependencies, not just runtime readers. Classification and
owner review remain before migration/deletion; the old 22/44 count is obsolete.

**Earlier, 2026-10-26: S4b completes 884 cyclic samples; measured retry exhaustion corrected offline.**
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

**Earlier, 2026-10-26: paced S4b run reaches 588 rows; slow aging mismatch found and corrected offline.**
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

**Earlier, 2026-10-26: S4b lookup retry passes 41 PLC cases; root-coherence refusal stops Dart.**
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

**Earlier, 2026-10-26: S4b root-age refusal diagnosed; lookup correction prepared offline.**
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

**Earlier, 2026-10-26: S4b Template discovery passed; first root sample refused; genealogy restored.**
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

**Earlier, 2026-10-26: S4b discovery attempt failed; genealogy restored; Template retry prepared.**
The approved image downloaded/returned to Run and passed SDK, read-back and access
audits. The Dart observer then reported `Unterminated Template name` before
readiness, so **zero of 41 candidate cases** ran. The guarded rollback restored
genealogy and the original five documents; **31/31 baseline cases**, final checks
and preflight pass. No dump, fault clear, clock/power operation or hard kill.
The approval is consumed. Read the
[sealed attempt](Evidence/AB_S4B_CANONICAL_ATTEMPT_2026-10-26.md).

Recorded S0 definitions reproduce a truncation bug: for two native Templates the
final member-name NUL lies just beyond the unrounded formula length. The client
now fetches the complete DINT allocation, preserves strict names/fragment bounds
and reports bounded handle/offset diagnostics. Ten native definitions replay in
four new tests; read-only baseline discovery still finds 60 Symbols/50 Templates.
This establishes the bug mechanism, not the exact failing handle in the S4b image.
The retry will confirm the correction on that image. Full HMI testing passes
**635 tests with 12 skips** on an identical isolated source copy using pinned
Flutter 3.47.5, including the unchanged sibling PLC inventory. A timing-dependent
login fixture now asserts that the completed expired response was observed,
without changing the production timeout or acceptance rule.

The [Template retry preparation](Evidence/AB_S4B_TEMPLATE_RETRY_PREPARATION_2026-10-26.md)
uses the same ACD `7D75E86E…DEF056BF` and 65% Capacity, the same 41/31 operation
scope, a frozen package map and fresh backup/guards. It is not authorized. Native
S4b and desktop acceptance remain pending; V2 inactive; no commit/push.

**Earlier, 2026-10-26: S4b implemented offline; exact-image qualification prepared.**
The runnable preparation is the
[frozen-package revision](Evidence/AB_S4B_FROZEN_PACKAGE_PREPARATION_2026-10-26.md),
using `qualification_session_v2.py` and a private package map from the tested
Flutter 3.47.5 setup. The initial seal caught the IDE regenerating the shared
package map with Flutter 3.47.2. Both the failed verification and original seal
are retained; the runner no longer depends on that mutable generated file.
The owner-approved V6.8 read service exposes the full configured definition set
and live/occupied-bank values without mailbox writes. The existing R2 owner
supplies formatting, revisions and access decisions; unreadable and unused
ValueText buffers are wiped across their full widths. Its independent migration
oracle covers **979 added genealogy paths**; the existing **4,428** remain exact.
Both v38 targets build/read back, access audits pass, and the prepared image
`7D75E86E…DEF056BF` measures **2,066,100 used / 1,079,628 available / 3,145,728
total Blocks (65%)**. Fifteen accepted older images regenerate byte-identically.

The generic Dart transport discovers Symbol/Template objects and the hashed
manifest; its row planner joins fragment members, validates counts and bounds,
and carries quality/monotonic age. The worker client, desktop factory,
reconnect/read-only policy and configuration adapter are implemented. Config
reads yield between bounded RPC batches; unselected banks supply only routing
references. The HMI spike and 13 dependent one-off probes are archived with
hashes and removed from the active tree. A Windows debug build passes.
The final gates and failed attempts are bound by the
[preparation evidence](Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26.md).

Only read-only access to the unchanged genealogy baseline has occurred. Native
Symbol/Template discovery passes, but **S4b is not accepted**: the new image's
concurrent Dart/41-case qualification, all-bank reads, native coherence/scan,
genealogy rollback and desktop rendering must run under a new exact-image
approval. The prepared session enforces that approval and retains every prior
guard. S5–S7 and S3's physical I/O proof remain open. V2 inactive; no commit/push.

**Earlier, 2026-10-25: S4a Echo qualification passes; genealogy restored.**
The owner-approved V6.7 image `07C54E8D…1CC2FF3` passes 31 candidate cases,
exact idle equivalence on **4,428 paths/types**, and generic acquisition across
seven modules. The station-free small-group probe discovers two counter bindings
and eight groups: **798/800 Good**, **2/800 Uncertain with no payload**, no Bad
reads; all groups meet the predeclared threshold and show counter progress.
Accepted-window median/p95/max is **1,227.7 / 1,451.4 / 2,223.0 µs**, below the
10,000 µs publication interval. All 798 Good raw rows replay; both whole-record
captures also replay. Capacity remains 60%. Candidate scan median/max is
**965 / 8,990 µs**, zero overlaps on 10 ms. Pinned genealogy rollback, exact
original five-document host restore, 31 baseline cases and all final/preflight
checks pass. No dumps, fault clears, clock or power operations. Authorization is
consumed. See [runtime evidence](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md).
This accepts S4a's initial module Status/product-row scope only. **S4b is next:**
complete transport/session, logical snapshots/goldens, isolate, demand/read tiers,
active-workload row/liveness proof, read-only UI/factory, spike retirement and
desktop acceptance. V2 inactive; no commit or push.

**Earlier, 2026-10-25: S4 coherence contract A approved; V6.7 prepared offline.**
The [S4 review](AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md)
corrects the assumption that V6.6 already published its read-counter associations.
The owner selected “A — publish existing counter bindings (Recommended)”.
V6.7 adds hash-covered prefix/counter/protocol/period bindings to existing scan
guards; canonical values and cyclic code stay unchanged. Both v38 targets build
and read back, and automatic Studio Capacity is 1,904,400 used / 1,241,328
available / 3,145,728 total Blocks (60%). Small-group native qualification is
S4a; completion of the generic desktop client and its full tier/rendering gates
is S4b. Dart physical decoding and bounded group-guard foundations are tested,
but CipSessionClient/factory/spike retirement are not implemented. This contract
approval does not authorize controller changes. Only read-only Echo readiness
has run in this S4 preparation; S3's last verified rollback remains the baseline.
V2 inactive; no commit or push.

**Earlier, 2026-10-25: press S3 exit runtime acceptance passes on Echo; genealogy restored.**
The press declaration (AUTO in ST, SFC and LD; image `15E89025…CFD76F`, 53%
Capacity) passes **47/47 candidate rows** (23 main rows with all seven core
cases in each rendition, 2 access, 8 configuration, 14 typed with collision
refused), **85/85 paired captures** and **86/86 independent replays**, exact idle
equivalence on 4,058 paths and generic acquisition (4,058 values, seven modules).
Candidate MaxScan 7,246 us, zero overlaps under 10,000 us. Rollback, 31/31
baseline cases and all final checks pass. Three earlier attempts are sealed;
their corrections are in the walk and oracle, not the image. With the path census,
S3's Echo exit criteria are met; physical-module identity/offline I/O proof and
the consumer census before S6 remain, then S4-S7. V2 inactive; no commit or push.
See [runtime evidence](Evidence/AB_PRESS_S3_EXIT_RUNTIME_2026-10-25.md).

**Earlier, 2026-10-25: S3 path census passes; press candidate prepared offline.**
All 4,437 frozen genealogy paths reconcile against the 91 accepted S3k native
comparisons: 4,087 compared with stage-approved types, 350 in the Core 16-entry
configuration window, 0 unexplained; the 341 extra compared paths are approved
additions. The press S3 candidate (press declaration on Echo, AUTO in ST/SFC/LD,
S3k canonical choices) builds and reads back on both v38 targets, passes access
and uses 1,669,892 / 3,145,728 Blocks (53%). Its walk (machine core in
ST/SFC/LD, inherited capture layers, typed vectors) and guarded session are
prepared. The first approved session downloaded it and stopped at the walk's
first capture (legacy oracle lacked tower-less `MachineState`); genealogy was
restored with 31/31 baseline cases and all final checks. The oracle is corrected
and covers all 4,058 press paths offline. The retry then stopped at the
live-document restore (shared host medium held genealogy-revision documents);
rollback and 31/31 baseline passed again. The walk now commissions an isolated
press medium from the image's own documents. The third attempt passed the medium
restore, access, all configuration and typed rows and four ST core cases (49
captures), stopping at held mode change (wrong observable, now corrected);
rollback and 31/31 baseline again. Next: a fourth session under new authorization. See [S3 exit notes](AB_CANONICAL_PUBLICATION_S3_EXIT_NOTES_2026-10-25.md).

**Earlier, 2026-10-25: S3k genealogy runtime acceptance passes; genealogy restored.**
The authorized `AA4239C6…1653BBDF` image passes **55 candidate check rows**
(41 inherited plus 14 typed/interleaving), including real PIN login, full-width
wipe, independent ACKs and both-ingress collision refusal without replay. All
**91 paired captures** independently replay exact values/types; generic
acquisition yields **4,428 values, seven modules and nine command arguments**
with no secret values or command-input records read. Native root/frame sizes
are **147,784 / 230,368 bytes**. Exact-image Capacity remains **1,903,344 /
3,145,728 Blocks (60%)**. Candidate LastScan median is 965 us, cumulative maximum
**8,969 us**, zero overlaps under the 10,000 us period. Pinned-copy genealogy
rollback, original host-document restoration, all **31 baseline cases** and
every final/preflight check pass. The 2,295 AB tests/both v38 builds remain bound
by unchanged native source hashes; post-runtime 74 root tests and all cheap
gates pass. Current authorization is consumed. **S3k passes at this recorded
genealogy scope; the wider S3 declaration/rendition exit and S4–S7 remain open.**
Next: full path-census reconciliation and actual press ST/SFC/LD/I/O proof,
behind its exact-image Capacity/scan/authorization gates. V2 inactive; no commit
or push. See [runtime evidence](Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25.md).

**Earlier, 2026-10-25: S3k private login token corrected offline; new retry prepared.**
The private LoginRequest now snapshots the shared committed owner sequence;
external legacy commit/ACK stay independent. Three coupled ingress/access tests
pass, including correct PIN login with generated SHA-256 and wrong-PIN refusal.
All **2,295 AB / 74 root tests**, specification/contracts/strict consistency,
both v38 builds/read-backs/access audits, 12 accepted image pins and 1,431 capture
replays pass. Only `FRK_PressHmiMailbox` changes; types and tag initializers are
identical. Prepared ACD `AA4239C6…1653BBDF` measures **1,903,344 / 3,145,728 Blocks**
(60%), +36 Blocks. It has not been downloaded. The prepared rollback restores
the exact original host documents before the old baseline fixture. Next: current
exact-image authorization for the request/rollback session. Genealogy remains
restored, S3k native acceptance open and V2 inactive; no commit/push. See
[login retry preparation](Evidence/AB_S3K_CANONICAL_LOGIN_RETRY_PREPARATION_2026-10-25.md).

**Earlier, 2026-10-25: S3k revision retry reaches typed login; genealogy restored.**
The authorized `12211B81…45995D9` image downloads/reads back cleanly. Five-document
restore, two Access and eight configuration cases pass. Twelve typed ACK/wipe
rows are recorded, but login consumption is followed by a failed authentication
completion wait. Main 31 rows, legacy-after-typed, collision and post-case TASK
measurement are not reached. All 39 paired captures independently replay exact
values/types and raw frame fragments. Rollback downloads genealogy; its first
document restore refuses the newer saved publication revision. The original
five preflight documents are preserved/restored through the host FileMedium,
then all 31 baseline cases and final/preflight checks pass. Native S3k acceptance
remains open; authorization consumed; V2 inactive. A synthetic offline causal
reproduction confirms login compares the legacy Sequence with the typed owner
token. Next: correct its private snapshot, coupled regression tests and exact
image/build/Capacity gates; include original host-document rollback before the
baseline fixture; then separately authorize a retry. See
[runtime evidence](Evidence/AB_S3K_CANONICAL_REVISION_RETRY_RUNTIME_2026-10-25.md).

**Earlier, 2026-10-25: S3k document-revision correction passes offline; native retry pending.**
The shared validator now derives the exact predecessor publication revision
from the same stage-13 declaration. Configuration Records, data types and tag
initializers are unchanged; only `FRK_Press_ConfigSets` differs. Saved document
headers/rows at revision 7203916 pass that predicate; changed schemas, foreign
stations and unknown revisions remain refused. Both v38 targets build/read
back at 0 warnings/errors and effective access passes. All **2,292 AB and 74
root tests**, specification/contracts/strict consistency, 12 accepted image pins
and 1,385 prior capture replays pass. Corrected ACD `12211B81…45995D9`
uses **1,903,308 / 3,145,728 Blocks**, 60% displayed, 4,284 fewer than the failed
image. The first longer-operand build failure is preserved. A fresh combined
request/rollback session is prepared and refuses missing or mismatched approval.
It has **not run**. Genealogy remains restored; current controller-changing
authorization is consumed. Next: current exact-image authorization, guarded
download, inherited/typed request cases, then genealogy rollback and 31 baseline
checks. Native S3k acceptance remains open and V2 inactive. See
[retry preparation](Evidence/AB_S3K_CANONICAL_REVISION_RETRY_PREPARATION_2026-10-25.md).

**Earlier, 2026-10-25: S3k request walk stopped at live-document restore; genealogy restored.**
The current owner instruction explicitly approved request cases then genealogy
rollback. The first invocation refused before writes because the inherited
harness selected the old declaration. Its exact binding is corrected; all
2,287 AB and 74 root tests pass and PLC source remains byte-identical.
The resumed walk passed two Access cases and five pairs, then stopped at
`station load refused`; none of the main 31 rows or typed vectors ran.
All five saved documents carry revision 7203916, rejected by S3k's 14896938
publication even though configuration Record declarations are unchanged.
Rollback of the hash-checked genealogy copy, five-document restore, 31 baseline
cases and all final/preflight checks pass: Run, no fault, MANUAL/idle, logged
out, not restoring, saved/live documents equal, no dumps. Authorization is
consumed. S3k acceptance is open; V2 inactive; no commit/push.
Next: exact prior-publication revision compatibility in the shared validator,
full offline gates and a corrected image, then separately authorized native
retry. Read [attempt/rollback evidence](Evidence/AB_S3K_CANONICAL_ATTEMPT_2026-10-25.md).

**Earlier, 2026-10-25: S3k option A command binding passes offline.**
The owner chose A: a typed Core payload with native BOOL and Core string
widths, PLC-side routing, one owner and a temporary legacy Frame adapter.
CommandBindings/CommandOperations (V6.6) describe every endpoint and all 39
kinds. The full image compiles/reads back on both v38 targets; access passes.
All 2,282 AB and 74 root tests pass; 12 pins and 1,385 captures still
hold. Capacity is 1,907,592 / 3,145,728 Blocks (60% displayed),
+164,512 for S3k over S3j, inside the planned band. No S3k download, native
regression or scan measurement has occurred; a native session needs a current
exact-image authorization. Read [offline evidence](Evidence/AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md)
and the [wire draft](AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md).

**Earlier, 2026-10-25: S3k read surfaces and R4 pass offline; command ABI choice pending.**
The approved 133 read paths, versioned 24-reason owner and table-driven manual
dispatcher compile/read back on both v38 targets; effective access passes.
All 2,264 AB and 74 root tests pass. Twelve accepted image pins regenerate
byte-identically and all 1,385 prior captures replay. The incomplete offline
image uses 1,807,120 / 3,145,728 Blocks (57% displayed), +64,040 versus S3j.
No S3k download, native regression or scan measurement has occurred.
The [command ABI review](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
asks A (typed Core payload and temporary legacy adapter, one owner) or B
(frozen Frame with published encoding/lookups). The whole legacy request also
embeds staged services and cannot simply become one bounded payload. Dependent
command binding waits for this choice; the semantic contract is already approved.
Next: chosen command binding, secret exclusion and service discovery, complete
offline gates, then separately authorized exact-image native acceptance. Genealogy
is unchanged, V2 inactive, no commit/push. Read [offline evidence](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md)
and [engineering notes](AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md).

**Earlier, 2026-10-25: S3j native acceptance passes on genealogy/Echo.**
The approved retry of 285BF972...8CC3212 passes all 41 candidate cases and
nine sampled-word vectors (80 fixed DINT writes including exact restoration).
All 98 captures replay independently with exact values/types. Idle equivalence
and generic acquisition publish 4,295 typed paths, seven modules and the
327-path fieldbus product (three nodes, twenty channels). Counts remain live
logical views, so snapshot size depends on occupied rows. Capacity stays
1,743,080 / 3,145,728 Blocks (55% displayed). Twenty TASK samples give
937 us median LastScan, 8,466 us cumulative maximum, zero overlaps and
1,534 us margin under the unchanged 10 ms period. The 216,872-byte migration
frame needs 55 fragments; S4 still requires row/group coherence and read tiers.
Rollback, 31 baseline cases and final checks pass: Run, no fault, scanning,
MANUAL/idle/logged out, policy restored and five saved/live documents equal.
No dumps. The approval is consumed; V2 remains inactive; no commit or push.
Read [native evidence](Evidence/AB_S3J_CANONICAL_RUNTIME_2026-10-25.md).
Next: S3k's 133 frozen paths (126 mailbox/report, five production and two
Features), with the approved R4 dispatcher reduction and its own gates.
Press ST/SFC/LD acceptance, real-module identity/offline proof and S4-S7 remain.

**Earlier, 2026-10-25: S3j native attempt stopped at a root-reference mismatch;
genealogy restored.** The exact 285BF972...8CC3212 image downloaded and passed
read-back/access. Forty paired captures passed; condition capture 2 differed
only at root Diagnostic.IoTag/IoAddress. The root oracle used the original
genealogy global declaration without S3j's I/O catalog. Nineteen named case
rows completed before the fixture stopped. Rollback, 31 baseline cases and
final checks pass; no dumps. The approval is consumed. Read the
[failed attempt](Evidence/AB_S3J_CANONICAL_ATTEMPT_2026-10-25.md).
The offline correction passes the candidate declaration explicitly to the root
reference; all 41 saved captures now agree exactly. Generated PLC bytes and
the measured 55% image remain unchanged. The corrected 2,249 AB / 74 root
tests pass; the [fresh guarded retry preparation](Evidence/AB_S3J_CANONICAL_RETRY_PREPARATION_2026-10-25.md)
binds the same image and write scope. Native I/O vectors, the rest of the 41-case
fixture, all-path acquisition and candidate scan remain open. No new controller
operation is authorized; genealogy is restored, V2 inactive, no commit or push.

**Earlier, 2026-10-25: S3j offline implementation and exact image prepared.**
The approved fieldbus product is PLC-owned and discovered through V6.5
DataProducts. The simulated genealogy catalog publishes 327 typed paths,
three nodes and twenty channels; live counts hide unused native slots.
R1/R2 stay enabled. Both v38 targets compile/read back equivalently and
pass effective access. Measured Capacity is 1,743,080 used / 1,402,648
available / 3,145,728 Blocks (55% displayed), +89,648 from accepted R1/R2.
The exact ACD is 285BF972...8CC3212, source 2F0B2CE7...A753EEA.
The inherited 41-case apparatus and a separate nine-vector/80-write word
fixture are prepared, with rollback and authorization gates. No S3j controller
operation is authorized yet. Native value/type/scan acceptance remains open;
R1/R2's 171 us scan margin is a measured risk to check, not a period to relax.
Read the [wire draft](AB_CANONICAL_PUBLICATION_S3J_WIRE_DRAFT_2026-10-24.md) and
[sealed preparation](Evidence/AB_S3J_CANONICAL_PREPARATION_2026-10-25.md).
Genealogy remains restored, V2 inactive, no commit or push.

**Earlier, 2026-10-24: R1/R2 native acceptance passes; genealogy restored.**
The owner approved the exact combined D170F1E3?33FF906C image. All 41
candidate cases, eight first-scan vectors, seven calendar lifetime rows
(38 public commits), retained Program/Run, 4,010-path equivalence and
97 independent packet/reference replays pass. Rollback, 31 baseline cases
and final checks pass. Echo is Run, not faulted, scanning, MANUAL/idle,
logged out, not restoring, policy restored and five saved/live documents equal.
Capacity stays 1,653,432 used / 1,492,296 available / 3,145,728 Blocks
(52% displayed). TASK LastScan median is 874 ?s; cumulative max is 9,829 ?s,
zero overlaps, leaving only 171 ?s below the existing 10 ms period. That
peak includes startup and the retained cycle; later stages need their own
measured scan gates. Read [native evidence](Evidence/AB_R1_R2_CANONICAL_RUNTIME_2026-10-24.md).
The approval is consumed. V2 is inactive; no commit or push. Next is the
already-approved S3j offline fieldbus product and simulated-node fixture,
then its own exact-image Capacity/build/read-back/native authorization.

**Earlier, 2026-10-24: R1 V6.4 implemented offline with R2.** The opt-in
`canonical_type_manifest` emits 137 type annotations and two sparse exceptions,
replacing 467 path rows. Both v38 targets compile/read back equivalently and
pass effective access. Automatic Studio Capacity measures 1,653,432 used /
1,492,296 available / 3,145,728 total Blocks (52% displayed): 360,600 saved
beyond R2, 1,110,080 versus accepted S3i. All ten accepted images remain
byte-identical with the opt-ins off; sealed V6.0?6.3 captures preserve their
snapshots under V6.4 metadata. The extra pair above the review's 136 estimate
belongs to the live and definition SequenceSteps arrays' separate UDTs.
The exact combined ACD is D170F1E3?33FF906C, source C3E1FA7E?02021333.
Read the [sealed preparation](Evidence/AB_R1_R2_CANONICAL_PREPARATION_2026-10-24.md).
Native R1/R2 acceptance, scan and regressions remain open. The exact combined
image must be prepared/sealed and confirmed before download. Genealogy is
unchanged; V2 remains inactive; no commit or push.

**Latest, 2026-10-24: capacity reduction started; R1, S3j and an R2 native
session approved.** A fitted estimate showed the migration design will not fit
S3k, S3j or the press, and gives about 56 K Blocks per added module. The
[capacity plan](AB_CAPACITY_BUDGET_AND_REDUCTION_PLAN_2026-10-24.md) lists eight
objective-aligned reductions. R2 (table-driven configuration page and audit,
opt-in `canonical_table_driven`) is implemented offline. It measures 2,014,032
Blocks (64%) on the S3i bench, 749,480 below the accepted image, with
equivalent read-back, all oracle cases passing, and every accepted stage image
byte-identical with the opt-in off. The owner approved the
[V6.4 manifest](AB_CANONICAL_MANIFEST_V64_CONTRACT_REVIEW_2026-10-24.md) (R1)
and the [S3j contract](AB_CANONICAL_PUBLICATION_S3J_CONTRACT_REVIEW_2026-10-24.md)
for offline work. An R2 native session is approved in principle, pending
exact-image preparation and confirmation. V2 remains inactive.

**Earlier, 2026-10-24: S3i exit passes on genealogy/Echo; genealogy is
restored.** The owner approved the second lifetime retry (“go on”). Every
stage ran once and exited 0. Candidate checks were 41/41. The calendar
lifetime passed 7/7 rows with 38 public commits: natural interval, deferred
target and calendar, natural closure into history, closed-target
immutability. Its 7 pairs read on the independent 4,000-byte observer. One
Program/Run without download preserved Line metadata, history values and
types, and 8/8 first-scan vectors. Idle equivalence matches 4,010 paths. All
97 pairs replay independently; rollback, 31/31 baseline and final checks pass,
with no dumps. Candidate cumulative TASK max is 9,206 µs (zero overlaps), close
to the 10 ms period. Physical power retention, the press renditions, S3j,
S3k and S4–S7 remain. Read
[S3i lifetime runtime](Evidence/AB_S3I_CANONICAL_LIFETIME_RUNTIME_2026-10-24.md).
The approval is consumed; no commit or push; V2 remains inactive.

**Earlier, 2026-10-24: the corrected S3i lifetime retry was refused by its
own download gate; the controller is unchanged and a second retry is
prepared.** The retry workspace setup had copied files as text, rewriting CRLF
line ends; the helper's hash-bound Capacity evidence no longer matched, so it
refused before download. No download, mode change or tag write occurred;
read-only guard and preflight afterwards equal the session's record. The
second workspace is byte-exact, and a new offline replica of the helper's
download gates passes on it (and fails on the refused workspace). The PLC image
and the approved observer correction are unchanged. Read the
[refused retry](Evidence/AB_S3I_CANONICAL_LIFETIME_RETRY_ATTEMPT_2026-10-24.md) and
[second retry preparation](Evidence/AB_S3I_CANONICAL_LIFETIME_RETRY2_PREPARATION_2026-10-24.md).
New approval required; no commit or push; V2 remains inactive.

**Earlier, 2026-10-24: S3i lifetime attempt failed at its first calendar
capture; genealogy is restored and a corrected retry is prepared.** The
approved lifetime session passed backup, download and 41/41 candidate checks
(87 frame pairs, independently replayed). Its first calendar capture failed
before any calendar write: `CalendarRun.observe` read the 173,792-byte frame
through the mailbox writer, which every command leaves at 500 bytes (about 357
requests against 44), so no read fitted the frame period. Rollback, 31/31
baseline and final checks passed, with no dumps. The retained Program/Run cycle
was not reached; the approval is consumed. The capture now uses the fixture's
independent 4,000-byte observer, and the frame reader refuses any other socket
size. 2,191 AB / 74 root tests pass; the PLC image is byte-identical. A fresh
retry workspace awaits new approval. Read the
[attempt](Evidence/AB_S3I_CANONICAL_LIFETIME_ATTEMPT_2026-10-24.md) and
[retry preparation](Evidence/AB_S3I_CANONICAL_LIFETIME_RETRY_PREPARATION_2026-10-24.md).
No commit or push; V2 remains inactive.

**Earlier, 2026-10-24: S3i publication passes on genealogy/Echo; calendar
lifetime remains open.** The approved A5FAFA46…7E36C42 image passed 41 candidate,
eight native publication vectors and 31 restored-baseline checks. All 88
same-frame pairs replay independently at 3,360–3,968 typed paths. Capacity is
87% (2,763,512 / 3,145,728 Blocks); median LastScan is 875.5 µs, cumulative
max 8,405 µs, zero overlaps. Genealogy is restored, MANUAL/idle/logged out with
five saved/live documents equal. Every live pair had zero occupied shift
history rows: synthetic publication vectors do not close natural calendar,
target-lifetime or retained Program/Run gates. Prepare those next, before S3i
exit or S3j. Read [runtime evidence](Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md).
The read-only observer's missing stage-11 result label was corrected before
controller changes; all 2,178 AB /74 root tests pass. The session approval is
consumed. No commit or push; V2 remains inactive.

**Earlier, 2026-10-24: remaining-S3 inventory reconciled; contract review
is owner-approved for offline implementation.** The 157 raw unmatched keys
include eight already-covered D2 endpoints. Comparing once in canonical index
space leaves exactly 149: 126 mailbox/report, 16 Line/shift, five production
fields and two Features flags; Access/Policy has no remaining gap. The
[inventory](AB_CANONICAL_PUBLICATION_REMAINING_S3_INVENTORY_2026-10-24.json) proposes 122 native Core path spellings and 13 frozen
type corrections, plus explicit bounded history and command/status schema
obligations absent from the frozen sample. The finite target allowance is recorded; V2 remains inactive.
Read the [contract review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md) and [next-stage notes](AB_CANONICAL_PUBLICATION_REMAINING_S3_NOTES_2026-10-24.md).

The accepted S3h image uses 85% Capacity, including its migration frame;
genealogy was restored afterward. The next image's fit/scan is not measured.
Shipping S4 coherence is per row/group under Part III §3.13; the frame is not
a client dependency and is removed at S6. The actual press declaration in all
three renditions and the separate fieldbus product remain S3 gates. This
inventory performed no controller operation or production-source change.
The S3h session approval is consumed. No commit or push.

**Accepted S3h baseline, 2026-10-24: S3h exit passes on Echo through the observation
frame; genealogy is restored.** The owner approved the session for ACD
`E07C4196…649745` in chat (“yes i approve”). Every stage ran once and exited 0:
guard, preflight, backup, download, SDK/read-back/access, 41 / 41 candidate
checks, idle equivalence, generic acquisition and TASK timing; then
hash-checked rollback and 31 / 31 baseline checks, followed by MANUAL cleanup
and final checks. All 88 pairs were read from the PLC-latched frame under the
unchanged `stable_scan_pair`, accepted in 2–29 of 100 polls, and compared equal
at 3,342–3,950 typed paths. They replay independently from native bytes, and
every record slice equals its frame bytes. Native records are 133,744 / 7,308 /
16,616 bytes; the frame is 172,088. Candidate LastScan median is 872 µs,
cumulative max 8,402 µs (equal to the C6 reading), zero overlaps; restored
genealogy is 99 / 1,167 µs. Capacity is 85% (2,680,132 Blocks); the held-out
forecast missed by +1.52% and its planning budget now exceeds the total. No
dumps, fault clears, clock changes or hard kills. The approval is consumed.
Physical/CIP Security, the 149 remaining inventory paths, S4–S7 and V2
activation remain separate. Read
[S3h runtime evidence](Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24.md).
No commit or push.

**Earlier, 2026-10-24: a PLC-latched observation frame replaces the scan
race; offline gates pass, native authorization pending.** Part III §3.13 says a
coherence-guarded set shall change less often than its read window or be
buffered on the PLC side, and retry is no substitute. The S3h pair (the
133,744-byte root plus 30 legacy owner records) changed every 10 ms scan and
took 8.7–15.9 ms to read. The owner asked for an evaluation against the Core
§1.1 objectives and a decision; the frame was adopted under six conditions.
Every fifth scan, after the canonical section's final even mark, generated
`CPS` statements copy exactly those records into Read Only
`FRK_Press_ObservationFrame`. A separate odd/even `FRK_Press_ObservationGeneration`
brackets the copy, which carries the source scan generation and fragment
revision. The oracle reads the frame through the unchanged `stable_scan_pair`
(100 polls/five seconds, fresh start, four sockets, one pending read). It
refuses a frame older than the capture request, from another definition
revision, or whose Template members differ from its reads. Comparisons, types,
corrections and the task period are unchanged. The frame has no top-level
Status, manifest row or write, and is removed with the legacy contexts at S6.

Nine new tests and 2,158 AB / 74 root tests pass; spec, contracts and strict
consistency are clean. The frame's sources equal the reads in all 64 accepted
native pairs. With the frame off the generator reproduces `E83B9A2C…567315`,
and all eight prior stage images and sealed replays are exact. Source
`BF456BCA…EFB1F2` builds on both v38 targets (import 0/0), reads back
equivalent and passes effective access. Prepared ACD: `E07C4196…649745`.
Automatic Capacity: 2,680,132 used / 465,596 available / 3,145,728 Blocks
(85%), +178,412 over C6. Scan time and native equivalence need the next
session, which requires current authorization for this exact ACD. Read
[observation-frame preparation](Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_PREPARATION_2026-10-24.md).
No controller operation, commit or push.

**Earlier, 2026-10-24: Echo recovery and S3h diagnostic download succeeded;
S3h stops at the unchanged coherence gate. Genealogy is restored.** The owner's
current “retry download on echo” instruction resumed the unused diagnostic
scope. Exact identity/service/listener/Remote/no-fault checks passed, but the
genealogy preflight refused a missing manifest. Two raw Symbol reads proved an
empty RemoteProgram controller. A separate empty-only helper restored a
hash-checked copy of the already-approved genealogy ACD, ran all 31 baseline
checks and re-entered the original preflight/backup/S3h driver without changing
its guards. The recovery helper initially lacked SDK FtspAdapter.exe and
stopped before download; the exact existing SDK dependency was added and the
failed log retained. Seven authorization cases and warning-clean build pass.

The C6 S3h download, SDK audit, read-back and access audit pass. The instrumented
fixture independently replays **64 exact pairs**, with 30 candidate checks
passing, one SFC `abort` check failing at acquisition, and 10 checks not reached.
The failed proof uses all 100 allowed polls in 267.188 ms: 38 unchanged-even
waits, 46 odd polls and 16 complete windows. Five close in the next odd
generation (+1); eleven close after the next even commit (+2). Wire windows
are 7,975.6 / 9,838.55 / 15,090.6 µs min/median/max; opening-to-closing spans
are 8,690 / 10,649.35 / 15,870.6 µs against the 10 ms task period. Immediately
after failure both TASK mirrors report LastScan 1,065 µs, cumulative max
8,402 µs and zero overlaps. This sample is not per-window task timing or the
missing final 20-sample candidate scan gate. No accepted pair mismatches a
value or type; mixed-generation bytes stay unaccepted.

Candidate cleanup, strict hash-checked genealogy rollback/read-back, all 31
final baseline checks, MANUAL normalization and final readiness/preflight
pass. Final baseline native timing is 99 µs median, 1,167 µs cumulative max,
zero overlaps (20 samples). Total recorded checks this continuation are 93:
92 pass, one candidate fails; these include the separate initial 31-check
recovery. No emulator crash, new native dump, hard kill, fault clear, clock
change or service/power toggle occurred. The session approval is consumed.

The owner's reverse-engineering report and final Ghidra log now explain the
libComms +0x50C2A4 NULL dereference on the expected-length I/O error-logging
path. The report attributes its startup trigger to corrupted power-down state
after the earlier forced shutdown. This session corroborates the instruction/
logging-call chain and matching binary hash; it does not reproduce that
corruption. Keep orderly shutdown after faults and inspect controller dump
folders before a later reboot. No vendor binary/state-file patch is applied.
Read [diagnostic runtime and recovery evidence](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24.md).
All 159 source and two wrapper bindings stay exact. S3h remains incomplete and
V2 inactive; the next blocker is reliable read-coherence timing. No commit/push.

**Earlier post-reboot observation, 2026-10-24: Windows reboot did not recover the virtual controller.**
Windows booted at 06:25:37 UTC; Echo's automatic startup exited with code 1
at 06:26:46 UTC. The service is Running, but exact controller 601FC87B is
enabled/ClosedExternally, RemoteProgram/Remote, not faulted, with no emulator
process or CIP listener. The fresh dump repeats 0xC0000005 in libComms.dll
at offset 0x50C2A4 and the same seven libComms frame offsets. The cause remains
unconfirmed. The observed reboot is not an agent power-state retry.

This continuation performed read-only checks only. All 159 project and two
diagnostic source pins, and the unused C6 deployment image, remain exact.
The diagnostic approval b76d12f2… remains recorded and unused. Its baseline
identity/session/document guards cannot pass while the controller is absent;
no upload, download, mode command or tag write ran. Controller definitions
and retained-state files were preserved. The consumed restart approval does
not authorize a further restart/reset/recreation. Rockwell's published next
step after unsuccessful reboot is technical support; no underlying ASLR or
retained-state cause has been established. Read
[post-reboot evidence](Evidence/AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24.md).
S3h remains incomplete and V2 inactive. No commit or push.

**Earlier, 2026-10-23: authorized Echo restart failed during emulator startup.**
The one-shot approval `call_37bd66c3442340b08084fd7b2deb2ce5:0` was used:
IsEnabled false applied; re-enable was requested and the native emulator
exited with code 1. The service remains Running; controller 601FC87B remains
enabled/ClosedExternally, RemoteProgram/Remote, not faulted, with no CIP
listener. No PLC download, tag write, mode command, fault clear or clock
change ran. The original S3h diagnostic approval remains recorded and unused.

Fresh native crash metadata records 0xC0000005 in v38.011 libComms.dll at
offset 0x50C2A4, with exception parameters [0, 0]. The x86 frame chain stays
in libComms before runtime-library thread frames. Private vendor symbols are
unavailable; the underlying cause remains unconfirmed. Earlier service logs
also record an emulator shutdown timeout/forced close and the same startup
exit before this authorized attempt. Controller definitions/state files stay
in place. The full memory dump is not archived; only metadata/control-address
stack frames and selected logs are recorded.

Rockwell's Echo 4.00 release notes describe an initialization issue for which
a Windows-host reboot is recommended. That is a possible next recovery step;
ASLR is unconfirmed here. Read [restart result](Evidence/AB_S3H_CANONICAL_ECHO_RESTART_2026-10-23.md).
S3h remains incomplete and V2 inactive; no further restart is authorized by
the consumed one-shot approval. No commit or push.

**Earlier restart preparation: the virtual controller was
ClosedExternally.** Read-only SDK metadata identifies the exact 601FC87B /
127.0.0.1 / slot 0 / v38.011 controller, enabled, RemoteProgram, Remote,
not faulted. The emulator process and 44818 listener are absent. SDK loaded-
project/path strings are empty; that does not prove the persisted PLC image
is empty while the emulator is unavailable. No new controller change ran.

A separate one-shot disable/re-enable helper is prepared and compile-clean.
Six offline authorization cases pass. It verifies exact identity/GUID/firmware/
slot/Remote/not-faulted and the reviewed ClosedExternally/RemoteProgram state
immediately before use, and refuses if an emulator/listener appears. It changes
only IsEnabled false then true, through the public SDK. It does not download,
change keyswitch/mode, clear a fault or set a clock. This added restart needs
current explicit approval under AGENTS.md §3a; its approval template is false.
The original diagnostic approval remains recorded and unused. After restart,
normal identity/session/document guards run; an unverified baseline stops
before any diagnostic download. Read
[restart preparation](Evidence/AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23.md). S3h is incomplete; V2 stays inactive.

**Earlier diagnostic preflight: Echo service was stopped.**
The owner approved `call_b76d12f2f038411386f83c339fcd94e0:0`, “Approve this
guarded S3h diagnostic session”. The resumed service/identity guards refuse:
FactoryTalk Logix Echo Service is Stopped, there is no 44818 listener, and
this process is not an elevated Administrator. No upload, download, mode
change or tag write ran. The prepared C6 ACD and diagnostic source pins still
match; no deployment sentinel or backup artifact exists. Current approval
remains recorded and unused; it is not being requested again.

The initial command orchestration continued after the first failed guard.
The backup helper independently refused before upload; all four failed logs
are retained. The replacement runner checks each return code and stops before
starting the next dependent phase. Owner action is the handover's documented
elevated `Start-Service "FactoryTalk Logix Echo Service"`. Once service is
back, fresh exact-identity/fault/keyswitch/HMI-session/document guards run again.
Fault clears remain excluded. Read
[service preflight](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_SERVICE_PREFLIGHT_2026-10-23.md). S3h/V2 acceptance is unchanged.

**Earlier active-workload S3h diagnostic preparation;
current authorization pending.** The failed paced retry is sealed: 39 exact
independent replays, first HELD coherence failure, successful rollback and all
31 baseline regressions. Larger message requests do not offer a useful path:
4,000/4,002 bytes connect; 8,000/16,000/60,000 are refused. An immediate-send
event-loop prototype does not establish a reliable latency gain and is not
in the implementation. No production reader/observer/PLC source changed.

A separate guarded wrapper now records per-window and generation-read timing,
keeps the last attempted raw frames explicitly unaccepted, and reads the eight
existing native TASK mirror scalars after an acquisition failure, before the
inherited fixture cleans up. It preserves the exact original exception,
100-poll/five-second history, four sockets/one pending request, comparisons
and all existing 41 candidate vectors. Evidence compression/writes happen
after the proof. Timing calls/in-memory rows add small observer overhead;
the native result will be labelled as instrumented diagnostics. Four wrapper
tests pass, including authorization refusal and error/history preservation.

All 159 existing source bindings remain exact, so their 2,149 AB / 74 root
tests and exact-image two-target v38/79% Capacity proofs apply. A fresh C6
image/helper is ready; fresh read-only baseline checks pass. No new native
write is authorized or performed. Proposed scope is the same guarded backup,
C6 download, inherited candidate fixture with diagnostics, and hash-checked
genealogy rollback/31 baseline checks/final cleanup. Failure still stops the
fixture and triggers rollback; there is no extra retry loop or acceptance claim.
Read [diagnostic preparation](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23.md). V2 stays inactive;
fault clears, clock changes, commit and push remain excluded.

**Earlier paced S3h retry stops at active HELD coherence;
genealogy is restored.** All 39 Access/configuration captures compare and replay
exactly from native bytes and independently reconstructed owner/provider contexts.
The two Access and eight configuration cases pass, but the first HELD capture
fails before comparison: 100 polls contain 77 unchanged-even waits, six odd
polls and 17 complete read windows; every window crosses one scan boundary.
Pacing removed the earlier tight-poll starvation but did not establish active
workload timing. The 1,000 baseline proxy passes do not transfer to this active
HELD state. No path, type or value mismatch was observed in an accepted pair.

Candidate cleanup, hash-checked rollback, all 31 baseline regressions, strict
rollback read-back and final Run/not-faulted/Remote/scanning, MANUAL=1/idle/
logout/not-restoring, five saved/live documents and original policy/preflight
equality pass. All 159 sources remain unchanged; 2,149 AB / 74 root tests and
the exact-image compiler/79% Capacity proofs still apply. The current session
approval is consumed. No fault clear, clock change, commit or push occurred.

S3h remains incomplete. Complete inherited/active/traceability checks, generic
idle acquisition and candidate TASK timing were not reached. No accepted
Capacity calibration sample is added; V2 stays inactive. The next task is to
reduce and instrument active-workload acquisition latency, keeping the same
100-poll/five-second positive equal-even proof. Read
[paced retry attempt](Evidence/AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23.md). No further download is authorized.

**Earlier paced S3h retry preparation (attempt completed above):**
The prior retry is sealed with genealogy restored and all 31 baseline checks
passing. Its failed capture spent 93/100 polls waiting for a fresh generation.
The observer now waits one millisecond after an unchanged even generation.
Every poll and wait remains inside the same 100-attempt/five-second gate;
the next iteration checks the deadline before another read. Closing positive
equal-even proof, four connections, one pending request each, all 47 packets,
post-window decoding, PLC image and candidate stimuli are unchanged.

The installed four-connection observer passes 1,000 consecutive read-only
baseline proxy captures in 2–54 polls.
These use the legacy scan counter and immutable payloads and do not establish
S3h canonical acceptance. An eight-connection experiment showed similar median
latency; it is retained as an experiment and is not shipped. All 2,149 AB tests
(276.776 s), 74 root tests and strict cheap gates pass. The 159-file source
closure differs only in the pacing implementation and its test. Regeneration
is byte-identical to source E83B9A2C…567315 and ACD C6B42327…5D7D9DC, so the
existing two-target v38 compiler/read-back/access and 79% automatic Capacity
proofs apply. A fresh one-shot helper builds with zero warnings/errors.

Fresh read-only preflight/readiness checks pass on restored genealogy. No new
download, mode change or tag write is authorized or performed. The next native
scope remains fresh backup, this exact image, 41 candidate checks/read-only
equivalence and scan, genealogy rollback and 31 baseline checks/final cleanup.
Fault clears and clock changes remain excluded. S3h remains incomplete and V2
inactive; no commit or push. Read
[paced retry preparation](Evidence/AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23.md).

**Earlier guarded S3h retry failed the coherence gate;
genealogy is restored.** The first three Access captures match 3,742 paths/types
exactly, with the five approved D2 bound corrections. The fourth capture
(`class_policy_changed`) exhausts 100 polls: 93 waiting for a fresh scan,
three odd-generation polls and four complete read windows, each crossing one
scan boundary. There is no accepted value/type mismatch. All four sockets
retain one outstanding read each; the 100-attempt/five-second gate is unchanged.

Candidate cleanup, hash-checked genealogy rollback, all 31 baseline regressions,
strict rollback read-back and final Run/not-faulted/Remote/scanning,
MANUAL=1/idle/logout/not-restoring, five saved/live documents and original
policy/preflight equality pass. No fault clear or clock change occurred.
The current retry approval is consumed. S3h remains incomplete; the 41 candidate
checks, complete traceability coverage and candidate timing remain open.

All 159 bound sources remain unchanged during this attempt; the sealed
2,148 AB / 74 root tests and exact-image v38/Capacity proofs still apply.
Capacity remains 79%, not added as accepted calibration. Native record sizes
from the three valid captures are 133,744 / 7,308 / 16,616 bytes. The next
offline task is to pace fresh-generation polling and reduce acquisition
overhead; another native session requires a newly prepared, reviewed scope.
V2 remains inactive; no commit or push. Read
[retry-attempt evidence](Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md).

**Earlier S3h retry preparation (attempt completed above):**
The failed attempt remains sealed and genealogy remains restored. A qualified
read-only observer now multiplexes four sockets with one pending request each,
and starts acquisition on a newly completed generation. Every waiting poll
counts against the original 100 attempts/five seconds. The closing equal-positive-
even proof, complete byte coverage and post-window decoding are unchanged.
Twenty baseline timing-proxy captures pass in 4–32 polls, with identical bytes;
these are transport diagnostics, not S3h canonical acceptance.

All 2,148 AB tests (270.165 s), 74 root tests and the focused transport/
scan-start tests pass. The source closure binds 159 files. Source L5X and ACD
are byte-identical to the original qualified S3h image: `C6B42327...5D7D9DC`.
Both v38 build/read-back/access and automatic Capacity (79%) gates are reused
by exact hash. A fresh one-shot helper/workspace is ready; no retry controller
operation is authorized. Next requires current approval for backup, this exact
download, 41 candidate checks/read-only captures, genealogy rollback and 31
baseline checks. No fault clear, clock change, commit or push. V2 remains inactive.
Read [retry preparation](Evidence/AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23.md).

**Earlier S3h native attempt stopped at the coherence gate;
genealogy is restored.** Ten paired captures matched all paths/types exactly,
but configuration capture six exhausted 100 attempts under the unchanged
five-second, four-connection proof. The 47-request read plan (42 fragments,
five batches) needs lower latency; no value tolerance or retry-budget extension
is accepted. Candidate fixture cleanup and genealogy rollback pass, followed
by all 31 baseline regressions and final Run/not-faulted/Remote/scanning,
MANUAL=1/idle/logout, five saved/live documents and policy/preflight equality.
No fault clear or clock change occurred. This session authorization is consumed.

Before download a reference callback incorrectly treated its Boolean path
selector as a document. It now takes occupied Count from the independently
bracketed owner. Two regression tests were added; all 2,140 AB / 74 root /
13 focused tests and cheap gates pass. PLC source/ACD and generic reader
remain byte-identical; only the reference and its tests changed before download.
The prepared Capacity gate stays 79%; the pending stage is not calibrated as
accepted. Native record sizes from successful pairs are 133,744 / 7,308 /
16,616 bytes, 157,668 total. S3h remains incomplete; V2 stays inactive.
Read [failed-attempt evidence](Evidence/AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md).

**Earlier S3h offline preparation (native attempt recorded above):**
The owner-approved 36 type corrections and unset Part stamp correction are
implemented with 278 additional consumed paths. The emitted ST and independent
reference reproduce all 278 frozen genealogy values exactly. Eleven focused
tests, 2,138 AB tests (277.202 s), 74 root tests, both v38 builds,
strict read-backs/access and specification/contracts/strict-consistency pass.
All eight prior accepted images and sealed generic snapshots remain exact;
the generic reader is unchanged. The source closure binds 157 files.

Prepared ACD `C6B42327...5D7D9DC` has automatic Studio Capacity of
2,501,720 used / 644,008 available / 3,145,728 total Blocks (79%),
+94,520 over accepted S3g. No capacity figure was requested from the owner.
The empirical forecast was 2,501,330 Blocks; it remains advisory. With a full
host ring, expected page totals are 3,950 / 3,900 / 3,550. Empty/partial rings
retain only their occupied physical paths, from the PLC Count. Cumulative
legacy inventory is 4,288 of 4,437, leaving 149 paths for later stages.

Fresh read-only checks confirm genealogy is still Run/not faulted/Remote/
scanning, MANUAL=1/idle/logout/not-restoring; five saved/live documents and
policy/preflight match. S3h has not been downloaded. Native equivalence,
record sizes, scan and rollback remain open; the whole-scan gate stays
100 attempts/five seconds. Next is separate current authorization for this
exact image, inherited 41 candidate checks, read-only traceability captures,
genealogy rollback and 31 baseline checks. No fault clear, clock change,
commit or push is authorized. V2 remains inactive. Read
[S3h preparation evidence](Evidence/AB_S3H_CANONICAL_PREPARATION_2026-10-23.md).

**Earlier, 2026-10-23: S3g exit passes on Echo.** All 83 planned checks
pass on their first runs: 41 candidate cases, nine OEE boundary vectors, two
profiler high-bit vectors and 31 restored-genealogy regressions. All 88 paired
captures replay exactly from native bytes and independent provider/metric
references, at 3,672 / 3,622 / 3,272 paths/types. The unchanged whole-scan proof
accepts in 1–75 attempts within 100 attempts/five seconds. All 151 prepared
sources, including the PLC/image and generic reader, are unchanged; their
2,127 AB and 74 root tests remain bound to the preparation seal.

Automatic Capacity is 76%: 2,407,200 used / 738,528 available / 3,145,728 total
Blocks, +108,752 over accepted S3f. Native root/definitions/alarm metadata total
145,084 bytes (121,160 / 7,308 / 16,616). Candidate scan median/max is
868 / 5,273 µs; restored genealogy 99 / 1,168 µs; zero overlaps. These are Echo
observations under different workloads, not isolated publication costs.

Genealogy is restored: Run/not faulted/Remote/scanning, MANUAL=1/idle/logout,
not restoring, all five saved/live documents and policy/preflight equal. No
fault clear or clock change occurred. This exact session authorization is
consumed. V2 remains inactive; no commit or push. Read
[S3g runtime evidence](Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md).
S3h offline preparation is now complete as recorded above; further controller
changes need separate current approval.

**Earlier S3h inventory (2026-10-23):** 278 added legacy paths bring
cumulative coverage to 4,288, leaving 149. The [contract review](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md)
enumerates 36 Core type corrections: 16 UInt32 event sequences, three Int16
ring counters and 17 DateTime stamps. The unset Part timestamp would change
from the legacy empty string to canonical zero within that same list; all
242 other added paths stay exact. Existing AB genealogy/delivery extensions,
append/epoch/measurement/tower owners and consumed bounds stay unchanged.
The owner approved these finite corrections and dependent offline work on
2026-10-23 (`call_f7da50b3655c43e4be6d7145b8b02c9b:0`). S3h offline implementation now passes the preparation gates above;
no S3h controller-changing operation is authorized. All 151 accepted S3g sources and 26 seals / 6,059 artifacts verify
unchanged. Read [S3h inventory evidence](Evidence/AB_S3H_CANONICAL_INVENTORY_2026-10-23.md).

**Earlier S3g offline preparation, 2026-10-23 (session completed above):** both approved amendments
are implemented: 200 Core numeric types and 224 dependent values, with exactly
1,055 additional consumed paths. The independent Core Float32/UInt32 reference
and actual emitted ST pass 13 focused tests, 2,127 full AB tests (291.415 s),
74 root tests, specification/contracts/strict-consistency and whitespace gates.
The complete image passes both v38 builds, exact read-back and access audits;
all seven accepted prior stage images and sealed capture replays remain exact.
The generic reader is unchanged.

Prepared ACD `CCE00F97...B4A6331` has measured automatic Studio Capacity of
2,407,200 used / 738,528 available / 3,145,728 total Blocks (76%), +108,752
over accepted S3f. Source `50E0F897...104DAE91` includes a separately generated
bench routine: nine first-scan OEE boundary vectors and two high-bit profiler
rows. The latter save/restore six fixed DINT owner cells in that same scan,
before normal publication. Results are read-only and outside the canonical tree.
No controller-changing operation is authorized or performed. Fresh read-only
checks pass on restored genealogy: Run/not faulted/Remote/scanning,
MANUAL=1/idle/logout/not-restoring, five documents and policy equal.

Next is current authorization for this exact image and the guarded S3g native
session: backup, Program/download/Run, 41 candidate regressions plus 11 native
boundary results, read-only 3,672 / 3,622 / 3,272-path equivalence/size/scan,
genealogy rollback and 31 baseline regressions/final checks. Native equivalence,
scan, hardware and CIP Security acceptance remain open. No commit or push.
Read [complete preparation evidence](Evidence/AB_S3G_CANONICAL_PREPARATION_2026-10-23.md).

**Earlier S3g schema checkpoint, 2026-10-23 (superseded above):** owner approval records the 200 numeric
corrections. The schema covers all 1,055 paths; native REAL/INT and the existing
UInt32 bit representation need no generic decoder changes. The schema and health
mapper pass both v38 compiler/read-back/access gates in an explicitly offline,
uncalled type/health probe. Four focused tests and 2,118 full AB tests pass;
S3f source still regenerates exactly B71E30AB...0AE7CF3.

Boundary analysis found 224 dependent value paths omitted by the type-only
allow-list: 64 OEE validity flags and 160 profiler row values. Their exact Core
counterexamples and [review draft](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md)
were approved by the owner on 2026-10-23 (question
`call_43d1f40d2efb4ab69d699df590f3c0bc:0`). The combined finite allowance is
424 paths: 200 numeric types and 224 dependent values. Full algorithms and
all complete-image gates remain required before deployment. No complete S3g deployment image,
exact-image Capacity, native equivalence/scan or session is prepared. The layout
forecast is advisory only. No controller access or changing operation occurred;
the last verified live image is restored genealogy from the S3f session.
Read [checkpoint evidence](Evidence/AB_S3G_CANONICAL_SCHEMA_2026-10-23.md).

**Latest, 2026-10-23: S3f exit passes on Echo.** The authorized revision
follow-up completed 74 accepted checks (42 candidate, one retained Program/Run,
31 restored genealogy), with 93 independently replayed paired captures and
2,114 AB / 74 root tests passing. Revision changes 745193095 → 1646242802 across
the no-download restart; retained configuration/banks/policy/page stay equal.
Both model CHANGEOVERs and exact restoration pass. Capacity is 73%, 2,298,448
used / 847,280 available / 3,145,728 total Blocks. Candidate scan is 835 µs
median / 4,573 µs maximum; restored genealogy 99 / 1,168 µs; zero overlaps.
Read [revision runtime evidence](Evidence/AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md).
All failed attempts are retained (125 actual rows, 74 accepted); four read-only
connections and fixture mode-application waits leave the PLC image and generic
reader unchanged. Echo is restored to genealogy, Run/not faulted/Remote,
MANUAL=1/idle/logout, five saved/live documents equal, policy/preflight equal.
Current sources: 143. This session approval is consumed; V2 remains inactive.
S3g offline preparation is described above; further native changes need their own current approval.

**Next stage, S3g inventory (2026-10-23):** 1,055 added legacy paths bring
cumulative legacy coverage to 4,010. Core declarations differ at 200 numeric
paths (64 Float, 101 UInt32, 35 Int16), including explicit OEE rounding/wrap
consequences. The [contract review](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md)
was approved by the owner for contract/offline work on 2026-10-23. S3g
implementation is now in progress. No S3g controller operation is authorized.

**Completed session, 2026-10-23:** the authorized S3f runtime session passes
at its recorded scope: 31 inherited candidate rows, two Access checks, eight
configuration cases and 31 restored-baseline rows. All 88 paired captures replay
identically, including complete native fragments and independent provider
contexts. Pages contain 2,617 / 2,567 / 2,217 paths/types. The observer now balances
bounded fragment packets across two read-only connections inside the unchanged
100-attempt/five-second whole-scan proof (1-59 accepted attempts); the PLC image
and generic reader are unchanged. Two observer failures and a full repeat for
missing MANUAL policy observations remain archived (113 actual rows, 72 accepted).
140 current sources are bound; 2,108 AB tests and 74 root tests pass. See
[runtime evidence](Evidence/AB_S3F_CANONICAL_RUNTIME_2026-10-23.md). Genealogy,
Run/not faulted, MANUAL=1/idle/logout, five documents, policy and preflight are
restored. This exact session approval is consumed. S3f retained restart and
active-model native revision vectors remain open before its full exit; S3g is
not started. No commit/push or further controller operation is authorized by
the completed session.

**Prior preparation, 2026-10-23:** S3f offline implementation has both v38
compiler/read-back/access gates and a prepared ACD, pin A05695F1...E3EB66.
Automatic Studio Capacity passes at 73%: 2,298,412 used / 847,316 available /
3,145,728 total Blocks (+729,560 over S3e). Closing gates pass: 2,104 AB tests,
74 root tests, specification/contracts and strict consistency. The
[preparation evidence](Evidence/AB_S3F_CANONICAL_PREPARATION_2026-10-23.md) binds
138 sources and retains all failed runs. The [S3f notes](AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md)
and V6.3 wire draft describe bounded pages, corrected Core types and validated
PLC-held provider responses. The fixture prepares 31 inherited rows, two Access
checks and eight configuration cases, with 31 baseline rows after rollback.
Native equivalence/scan/rollback and current controller authorization remain
pending; the accepted live genealogy baseline is unchanged. No commit/push.

**Current continuation, 2026-10-20:** the corrected first S0 probe was downloaded
and measured, and genealogy restored with 31/31 regressions and passing final
checks. D6/D7 are selected in the design note. See
[runtime evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md),
[V2 draft](AB_FROZEN_CONTRACTS_V2.json) and
[Part III amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md).
**Owner approved the target drafts on 2026-10-20: “Approve drafts and proceed
to S1”. The S1 reference-oracle exit now passes at its recorded scope.** See
[S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md).
The supplementary S0 runtime session completed on 2026-10-21 with owner
Capacity fit, exact 2 MiB fragmented reads, browse-name root, effective access,
precise LREAL vectors, 31/31 restored regressions and passing final checks; see
[supplementary evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md). The
following hand-over state is historical; its original probe was superseded by
[the corrected preparation](Evidence/AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20.md).

### Echo

- **Loaded image:** `fraktal_ab_genealogy_demo`, manifest
  `6DEC4C1DC2F7F78A`. Re-downloaded on 10-19 with 31/31 regressions; see
  [AB_ECHO_REDOWNLOAD_2026-10-19](Evidence/AB_ECHO_REDOWNLOAD_2026-10-19.md).
- **The Echo service fails to start at boot.** The host rebooted on 10-19
  20:38 and on 10-20 21:40, and both times the FactoryTalk Logix Echo Service
  timed out on start (Service Control Manager events 7009/7000). The service
  ACL lets only SYSTEM and elevated Administrators start it, so the owner must
  run `Start-Service "FactoryTalk Logix Echo Service"` from an elevated shell.
- **An HMI session was still logged in** (`echo_admin`, level 4) at the last
  check. The preflight refuses to download over an active session. Do not
  weaken that guard; ask the owner to log out.

### S0 (prepared, not downloaded)

- **Tools** (uncommitted):
  - `tools/fraktal_ab_s0_canonical_probe.py` — generator;
  - `tools/fraktal_ab_s0_canonical_measure.py` — read-only template decoder
    and measurement;
  - `tools/test_fraktal_ab_s0_canonical_probe.py` — 7 tests, passing.
- **Work folder:** `C:/work/fraktal-ab-s0-20261019/`.
  - The combined probe `combined/s0_combined.L5X` compiles on both v38 targets
    with equivalent read-back.
  - The prepared ACD `s0_probe.ACD` (SHA-256 `F7E54A1A…`) has equivalent
    read-back and a clean log.
  - `session/S0Session.exe` has the modes `prepare-probe` (done), `backup`,
    `deploy-probe` and `restore-genealogy`.
  - `scripts/preflight.py`, `scripts/guard_echo.py` and
    `scripts/probe_loaded.py` support the session.
- **Compiler facts already measured** (v38, offline SDK build):
  - A member named after a type (`Time`, `DT`, …) fails with
    `RxSTX_E_UNEXPECTED_TOKEN`.
  - Time literals must be normalised: `T#1500ms` fails and `T#1s500ms`
    compiles. The `TIME#` prefix fails.
  - `TIME32`, `LTIME`, `DT` and `LDT` declare.
  - Assigning a LINT into `TIME`/`DT`/`LDT` compiles.
  - ST has no `MOV` (`RxSTX_E_INVALID_FUNC`).
  - Studio canonicalises structured members to `Radix="NullType"`.
  - StringFamily widths up to 480 compile.
- **Runtime facts already measured** (Echo, read-only, 10-19):
  - Symbol/Template discovery returns member names, types, offsets and BOOL
    bit numbers.
  - The generic decoder matches the layout decoder on all 47 `FRK_Press_Unit`
    members.
  - StringFamily members are recognised by shape.
  - The golden projection capture is
    `C:/work/fraktal-ab-echo-20261019/projection_capture_01.json`
    (50 reads, 4,437 values, SHA-256 `5CA907E6…`).

### Uncommitted working tree

- The design note and this plan.
- The S0 tools and their tests.
- The 10-19 Echo evidence record.
- The removal of the CIP spike's hex-dump `print`s in
  `HMI/lib/data/cip/eip_cip_client.dart`.
- Pre-existing owner edits that are not this work: `.gitignore`,
  `AGENTS.md`, and the `.dart_tool` files under the Siemens archive snapshot.

## 3. Invariants for every stage

- **One source.** The declaration remains the only source; the generator emits
  the L5X. Hand-authored L5X is forbidden, and no station knowledge may enter a
  client.
- **Canonical paths.** Paths, leaf names, enum ordinals and logical types equal
  TC3's (`HMI_CONTRACT.md`, `HMI/lib/domain/types.dart`). Array indices follow
  each array's Core-declared bound (D2).
- **Published versus private.** Published members are External Access *Read
  Only*; only `HmiRequest` is *Read/Write*; private storage is *None*. The R6
  allow-list audit runs on every generated image.
- **Native types per D3–D7.** Never name a member after a type. Use
  normalised time literals.
- **Language parity.** ST/SFC/LD parity holds; the rendition gate and the 31
  regressions stay green.
- **Controller-changing operations.** Each needs the owner's **current**
  authorization, the exact identity guard immediately before use, a backup
  upload, and restoration with acceptance afterwards. Evidence is append-only
  under `Specification/AllenBradley/Evidence/`, including failed runs.
- **Budget.** Memory and scan time are measured per stage (Studio Capacity
  Estimate; native `TASK` `MaxScanTime`). The owner requested an automatic
  estimate on 2026-10-21; the [calibrated forecast](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md)
  provides offline budgets. The qualified automatic Studio collector now
  supplies the exact offline Capacity values from a hash-checked review copy;
  it reproduced the owner's S3a values before measuring S3b. This replaces
  routine screenshot requests on the qualified L81E/v38 English setup, while
  preserving the measured gate. Forecasts remain advisory. No feature is cut
  and no validation weakened to make an image fit.

## 4. Stages

### S0 — Measure the type rules and draft contract V2 (target drafts approved)

Steps 1–3, 5 and 6's draft preparation have completed for the first probe.
The supplementary step-4 session completed on 2026-10-21; see
[runtime evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md) and
[preparation evidence](Evidence/AB_S0_SUPPLEMENTARY_PREPARATION_2026-10-21.md).
Five positive cases compile/read back on both v38 targets. Echo reads all
2,097,152 bytes exactly at both 500/4000-byte connection settings, with
fragmented reads from byte zero. The 2 MiB + 4-byte UDT is rejected at import
on both compiler targets; no global array-tag size limit is claimed. The
browse-name root and precise LREAL `L`-suffix/typed-data vectors pass. Owner
Capacity displays 69%: 2,189,916 used / 3,145,728 total blocks, 955,812 available.
Native task MaxScanTime is 10 us with zero overlaps on this inert 10 ms probe.
Genealogy and all five live documents were restored, 31/31 regressions pass,
and final read-only checks pass. This completed session must not be reused. The
first image's untyped decimal rounded to REAL before LREAL assignment. Retain
this finding and the failed
reader/acquisition attempts in the runtime evidence. The first session's
preflight, backup and download outputs already exist and must not be overwritten.

1. Owner starts Echo (elevated) and logs out of the HMI. Get current download
   authorization.
2. Run `S0Session.exe backup` (guard, preflight, upload), then
   `deploy-probe`.
3. Run the read-only `fraktal_ab_s0_canonical_measure.py --expect-serial
   601FC87B --generation combined/combined.json --output <new>.json`. Record:
   - template type codes for `TIME`/`TIME32`/`LTIME`/`DT`/`LDT`;
   - their units, by comparison with the assigned literals;
   - what LINT→`DT`/`LDT` assignment does to the value (Rockwell treats every
     LINT as an `LDT` in conversion);
   - BOOL bit packing, string LEN and bytes (UTF-8), nested structure arrays.
4. Extend the probe with the questions S2 depends on, compiled and measured
   in the same session if possible:
   - **Size:** the largest single structure and tag the controller accepts,
     and whether reads need Read Tag Fragmented (`0x52`).
   - **Naming:** a controller-scope root tag named exactly as the root's
     browse name (`Press`).
   - **Discoverable access:** whether External Access shows in the Symbol and
     Template access bits.
5. Run `restore-genealogy`, then `fraktal_ab_genealogy_execute.py`
   (configuration restore and 31 regressions) and the final read-only checks.
6. **Decide** D6 and D7 from the measurements. Write the evidence record,
   `AB_FROZEN_CONTRACTS_V2.json` (draft) and the Part III amendment draft. The
   amendment covers §3.8 type map V2, §3.10 exposure, §11.1 (desktop direct
   per D9, replacing "Direct CIP from the HMI is not the reference design"),
   and the L24ER retirement.

**Exit:** the owner approves the V2 draft. Achieved on 2026-10-20. The
supplementary gates before S2 now pass at their measured Echo scope.
Access findings correct the earlier physical assumption: a writable descendant
needs Read/Write on every ancestor, with Read Only on other public members.
None members prevent whole-structure reads, so private working storage stays
outside the canonical whole-read records. Symbol attribute 10 distinguishes
top-level RO (2) / RW (0) on this Echo; raw Template metadata does not distinguish
member RO/RW/None. The V6 manifest therefore publishes effective member access
alongside logical types and bounds. These findings implement the approved
leaf policy; they do not activate shipping V2 or authorize an S2 download.

### S1 — Generic reference reader (Python, test oracle)

- **New tool** `tools/fraktal_ab_canonical_reader.py`. It discovers through
  Symbol, Template and manifest, decodes with the S0 decoder, and emits the
  same `values` document shape as `fraktal_ab_projection.project`. It is a gate
  oracle, not a shipped runtime: no gateway uses it.
- **New tool** `tools/fraktal_ab_canonical_equivalence.py`. It compares the
  reader's output with the projection for the same controller state, both live
  and from recorded captures. Its report lists every differing path, with the
  D2 allow-list explicit.
- **Capture fixtures.** Promote `projection_capture_01.json` (and a press
  capture) to compact test fixtures, plus Symbol/Template/tag-byte captures for
  the canonical image once S2 exists. Fixtures are recorded data, never
  hand-edited. Keep them within a stated size budget; compress if necessary.
- **Tests:** synthetic-template unit tests, extending
  `test_fraktal_ab_s0_canonical_probe.py`, and capture-replay tests.

**Exit:** the reader reproduces S0 measurements and the equivalence tool runs
in the AB suite.

**Oracle exit passed, 2026-10-20:** 1,921 AB tests (20 canonical tests), 74 root
tests, clean spec/contracts/strict consistency, both unchanged S0 v38 offline
build/read-backs, full 47-check S0 replay and 4,437-value legacy replay. See
[S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md) for the remaining
capture/wire-adapter boundary and exact outputs. No controller change occurred.

**Implementation boundary clarified on 2026-10-20:** S1's generic reader uses
a normalized PLC-manifest annotation model. The physical V6 layout is explicitly
S2 work in the approved V2 target; therefore the standard wire-manifest loader
and stable paired live V1/V2 acquisition belong to S2, alongside its first image.
The S1 live seam requires that loader, never a station declaration or an external
manifest file. Matching configuration tokens does not prove scan atomicity.

No recorded press projection read/values capture was found in the checkout or
`C:/work`; only the genealogy golden capture exists. Record the press fixture
on an appropriately gated image before full S3 equivalence acceptance. Do not
re-contact the retired L24ER to fill this gap, relabel genealogy, or manufacture
recorded values. Canonical Symbol/Template/byte captures remain S2 work as above.

S0's recorded bytes omit Template structure sizes and have no canonical root
or manifest. S1 replays them diagnostically and reproduces all 47 checks,
including the two DT/LREAL findings. Strict canonical decoding requires Template
attribute **5** byte sizes. Synthetic templates test that path; a read-only Echo
observation confirms the attribute service against 50 legacy templates, without
claiming V6 acceptance or settling the supplementary maximum-size/access probe.

### S2 — Canonical module tree (first published surface)

**Offline candidate prepared, 2026-10-21:** the opt-in genealogy image publishes
46 S2 paths for one Unit and six CMs, alongside unchanged legacy contexts and
its V5 oracle manifest. The separate V6 manifest and generic physical loader
are implemented; see [wire candidate](AB_CANONICAL_PUBLICATION_S2_WIRE_DRAFT_2026-10-21.md)
and [preparation evidence](Evidence/AB_S2_CANONICAL_PREPARATION_2026-10-21.md).
Both v38 targets compile/read back; prepared ACD pin is 2B3F99D9...D200973.
The fixture's same-state gate uses an equal-even generation around all paired
reads, bracketed around the entire PLC scan. **S2 exit passed on 2026-10-21**:
46/46 paths and types match with same-scan proof, both owner Capacity values
and native scan deltas are recorded, and candidate/restored-baseline
regressions pass 31/31 each. Genealogy is restored and final checks pass. See
[runtime evidence](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md), including
the retained interrupted backup and guarded recovery. The next surface is S3a;
shipping V2 activation and the remaining stages are still open.

During migration V5 remains solely for the existing oracle/harnesses. V6 is
the canonical client's manifest; no client reinterprets the V5 context rows.
The first Status slice contains identity/state/fault fields; diagnostics follow
in S3b. ModelCode retains the application's existing 80-byte catalog bound.
The module forest is discovered from native Status members. Private scratch
and the test generation/timing records are not module roots.

- **Generator** (`fraktal_ab_generate.py`):
  - a root record (`FRK_T_<App>Root`) and a controller tag named exactly as the
    root's browse name;
  - every module's `Status : ST_ModuleStatus` equivalent as named members;
  - children as members named after the schematic;
  - mode, run style, model, `Step`/`CurrentStep`.
  - During S2–S3 the canonical structures are written **alongside** the
    existing contexts. Running both is a migration device only; S6 collapses
    them.
  - Derived values move into generated ST in the owning service
    (`unit_logic`, `module_logic`, `diagnostic_logic`, …), never into a client.
- **Manifest** (`fraktal_ab_manifest.py`): `Fields` rows describe canonical
  paths with `LogicalType` and the D2 logical lower bound/element count. BOOL
  arrays are expanded from template DWORD storage using that logical extent.
  Manifest major steps to 6.
  Effective member access is published where native discovery does not provide
  it; derive it from the same owning declarations as the UDT access settings.
  Canonical whole-read records contain no None members. Ancestors of a writable
  mailbox are Read/Write while other public branches remain Read Only.
  `content_hash`/`config_revision` stay the coherence token.
- **Tests:** generator unit tests (member names, access, radix, no reserved
  names), compile and read-back on both targets, then live equivalence on Echo
  for the published subset.

**Exit:** equivalence for the S2 subset, plus memory and scan deltas recorded.

### S3 — Remaining surfaces, one at a time

Migrate in this order, smallest dependency first. Each surface is one commit
with its own equivalence, Capacity and scan record.

S3a uses a [94-path inventory](AB_CANONICAL_PUBLICATION_S3A_NOTES_2026-10-21.md).
The code exposes a distinction the original surface list did not spell out:
physical array capacity differs from the current logical view, and the model
count changes at runtime. V6.0's static exact-extent rows need a versioned
published view before this image can be generated. Decision.Timeout/SourcePath
also have no oracle paths; resolve that separate Core gap explicitly. Neither
finding permits weakening the five-D2-only equivalence rule. The owner selected the logical-view option, and the
[V6.1 candidate](AB_CANONICAL_PUBLICATION_S3A_WIRE_DRAFT_2026-10-21.md) implements
explicit selections/live count references with validation even for empty
arrays. S2 output is unchanged. **S3a offline preparation passes:** 1,960 AB
tests, 74 root tests, both v38 compiler/read-backs and a pinned reopened ACD.
See [preparation evidence](Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md).
**S3a runtime exit passes at this subset**, after current owner authorization
for the pinned F1D24CA8...A7EE79F image. Capacity is 817,476 used / 2,328,252
available / 3,145,728 total blocks (displayed 25%), +72,232 blocks over S2.
All 94 paths/types match, including four active-decision pairs. Candidate
and restored-genealogy regressions pass 31/31 each. The first candidate run's
18 completed rows and failed same-scan acquisition are retained; moving
metadata copies/decoding after the closing generation read fixes the harness
without changing PLC code, proof or retry budget. Native candidate median
LastScanTime is 110 us, cumulative MaxScanTime 1,178 us, zero overlaps; the
prior S2 observations were 109 / 1,177 us. Workloads differ by the disclosed
failed/retried fixture and paired captures, so these are observations rather
than isolated cost measurements. Genealogy is restored and final checks pass.
See [runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
S3b offline preparation now passes 2,007 AB tests, 74 root tests, the native
compiler/read-back and automatic Capacity gates; see
[preparation evidence](Evidence/AB_S3B_CANONICAL_PREPARATION_2026-10-21.md).
Its independent inventory has 304 paths: the accepted 94, six diagnostic
fields on seven modules (42), and seven timing fields on eight rows for three
commanded CMs (168). The fixture has no EM. Several full-Core status fields have
no oracle paths; these remain explicit gaps in
[the S3b notes](AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md).
The prepared ACD is pinned to `634A3A86...4394EEF`. Automatic Studio Capacity
is 991,612 used / 2,154,116 available / 3,145,728 total blocks (31% displayed),
+174,136 blocks over S3a. **S3b runtime exit now passes at this subset** after
current owner approval of that exact image: 304/304 paths/types, four decision
pairs, ten held pairs and four Unit first-out fault pairs, covering all three
renditions. Candidate and restored-genealogy regressions pass 31/31 each.
The first eight-row run failed same-scan acquisition because mailbox commands
set the shared connection to 500 bytes. An independent 4,000-byte read observer
fixes this without changing framing or proof. A subsequent 31-row run lacked
fault observations after child Execute-drop; observing the owning Unit's
latched first-out closes the original coverage gate. All failures and 39 extra
candidate rows remain recorded. Accepted captures need one or two attempts.
Native candidate median LastScanTime is 123 us (122–123), cumulative maximum
1,190 us, zero overlaps; prior S3a was 110/1,178 us. These are observations
under disclosed different workloads, not isolated publication costs.
Genealogy/five documents are restored and final checks pass. Final gates:
2,011 AB tests, 74 root tests, spec/contracts/strict consistency and native
download/read-back/access checks. See
[runtime evidence](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md).
S3c offline preparation passes at an independently inventoried
647 paths (304 prior plus 343 sequence/current-step leaves). Both v38 builds,
strict read-backs/access, 2,052 AB tests and 74 root tests pass. Automatic
Capacity is 1,107,552 used / 2,038,176 available / 3,145,728 total Blocks (35%),
+115,940 over S3b. ACD pin: A2559188...0C2286C. See
[preparation evidence](Evidence/AB_S3C_CANONICAL_PREPARATION_2026-10-22.md) and the
[S3c notes](AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md) and
[V6.2 record-binding draft](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md).
Definitions live in a separate PLC record bound by the manifest; the PLC Chart
still owns fast-step history. The native root carries the cursor, history,
sparse notes and current-step detail. Generic discovery imports no station.

**S3c runtime exit passes at this subset** after current owner approval of
A2559188...0C2286C. Candidate/baseline regressions pass 31/31 each on their first
runs. All 647 paths/types match across four decisions, 14 held/fault pairs and
21 sequence pairs, covering ST/SFC/LD mode clear, sparse warning notes and
retained completed fast steps. Idle equivalence and generic discovery also
pass. All 40 paired captures and the generic capture replay identically.
Same-scan attempts range 1-6 within the unchanged 100-attempt/five-second gate.
Native candidate median/range is 200 us / 200-201, cumulative maximum 1,600 us,
zero overlaps; prior S3b observations were 123/1,190 us. Different workloads
preclude an isolated publication-cost claim. Restored genealogy is 99/1,167 us.
See [runtime evidence](Evidence/AB_S3C_CANONICAL_RUNTIME_2026-10-22.md).

**Readiness correction, 2026-10-22:** the inherited work scripts called Mode 0
MANUAL; the declaration defines AUTO=0, MANUAL=1. Earlier MANUAL claims remain
unsupported and sealed evidence is unchanged. Under the S3c approval the fixed
helper performed three LOGIN/SET_MODE(1)/LOGOUT normalizations, without policy
or stimulus changes. Final guards now verify actual MANUAL=1/idle, Run, not
faulted, Remote, scanning, logged out, not restoring, saved/live documents
equal, restored policy and the original preflight. The initial legacy-backup
access audit used the wrong canonical allow-list and stopped deployment; an
exact tag/access comparison with the sealed genealogy artifact passes before
download. The failed audit is retained; no controller or reader rule changed.

S3d offline preparation passes at 2,125 paths: the accepted 647 plus 1,469
AlarmLog paths and nine StateFlags paths. The original table's 1,469 described
AlarmLog alone; see the [S3d inventory/notes](AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md).
Both v38 builds/read-backs/access and 2,062 AB tests pass. The prepared ACD pin
is E5CA9AB3...7CF7C9D. Automatic Capacity is 1,290,016 used / 1,855,712 available /
3,145,728 total Blocks (41%), +182,464 over S3c. One shared PLC calendar routine
serves diagnostics, event timestamps and flags; caches avoid unchanged text/time
work. Alarm append/reset ownership and all earlier image outputs are unchanged.

S3d runtime now passes under the owner's exact-session approval. Candidate
and restored-baseline fixtures pass 31/31; four decision, 14 held/fault,
21 sequence and eight reset captures (four before/after pairs) cover ST/SFC/LD.
All 2,125 paths/types match; 48 paired captures including idle replay exactly.
Active/closed events, nonzero duration, ring wrap, flag transitions and one-reset
Blocking release are observed. WAIT_RESET is model-covered but was not observed
in these runtime captures. Full-Core event Category, ResetAt and ShelvedUntil
remain explicit oracle gaps. See [runtime evidence](Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md).

**Acquisition correction:** the original full-record read exceeded the 10 ms
task window. Two retained attempts stopped after eight and 26 passing rows.
The acceptance harness now caches PLC-bound V6.2 metadata under equal manifest
revision tokens and reads live canonical/oracle records on two independently
guarded read-only connections. Both finish inside the same unchanged equal-even
scan proof (100 attempts/five seconds); accepted attempts range 1-8. The generic
reader, PLC image, task period and regression stimuli are unchanged. Actual
recorded regression rows total 96, including 34 from the failed attempts;
individual tag-write calls were not instrumented. This fixes the read plan,
without weakening the gate or treating failed runs as accepted coverage.

Native root/sequence/alarm-metadata payloads measure 77,304 / 7,308 / 16,616
bytes. Candidate scan median/range is 437 us / 436-437, cumulative maximum
3,111 us, zero overlaps. Restored genealogy is 99 us / 99-100, maximum 1,167 us.
These workloads differ; their difference is not an isolated publication cost.
Genealogy is restored, actual MANUAL=1/idle, Run, not faulted, Remote, scanning,
logged out, five saved/live documents equal, policy and original preflight
verified. The S3d approval is consumed; S3e preparation is next and a future
controller session needs its own gates/authorization. No commit/push is authorized.

Final S3d gates: 2,066 AB tests / 276.677 s and 74 root tests / 1.942 s;
spec/contracts, strict consistency (0 errors/warnings) and whitespace pass.
Only the acquisition oracle and its tests changed from the preparation seal;
68 other bound sources, including all PLC/generator inputs, are unchanged.
Both native v38 build/read-back gates remain bound to that exact image.

S3e offline preparation now covers 2,154 paths, adding 29 Access/data-policy
paths and enriching the existing ring's audit Description/SourcePath in place.
See its [independent inventory and notes](AB_CANONICAL_PUBLICATION_S3E_NOTES_2026-10-22.md).
Policy.Required completes the fifth D2 zero-bound mapping. A generic BITSTRING32
reader correction preserves the unsigned LoginResultSequence high bit; no
station fact enters the reader. All five earlier images/replays are unchanged.
Both v38 builds/read-back/access and 2,078 AB tests pass. Original prepared pin
95E85B50...A1B240B has automatic measured Capacity 1,568,852 / 3,145,728 Blocks
(49%, +278,836 over S3d). The source, review copy and receipt are hash-bound.

The next fixture scope includes the inherited 31 rows plus two explicit Access
checks (unknown-user login refusal, one class read-level edit/restoration), six
read-only Access phases and the inherited decision/condition/sequence/reset
captures. The owner subsequently approved and completed that S3e session. Its
exact-artifact [preparation record](Evidence/AB_S3E_CANONICAL_PREPARATION_2026-10-22.md)
binds both native builds, 2,078 AB / 74 root tests, spec/contracts, strict
consistency/whitespace, measured Capacity, helpers and false approval template.
Runtime now passes at all 2,154 values/types: 31 inherited candidate rows, two
fixed Access checks, four decisions, 14 held/fault, 21 sequence, eight reset and
six Access captures, plus idle (54 paired captures, independently replayed).
LoginBusy/failure/success/logout, manual/class-policy changes and audit actor/
action text are observed. The original whole-scan proof remains 100 attempts /
five seconds, with accepted attempts 1-41; metadata uses V6.2 revision coherence.
See [runtime evidence](Evidence/AB_S3E_CANONICAL_RUNTIME_2026-10-22.md).

The first complete candidate matrix passed. Its first coverage audit incorrectly
checked Required[1] for MANUAL; the owner uses zero-based gate 2. An unnecessary
partial repeat stopped after one inherited row and two passing Access checks
under that same wrong observer expectation. Both cleanups restored documents/
policy. The corrected audit derives the gate from the owning action map and
accepts the original complete captures, which already include 0/1 at Required[2].
The temporary observer/test edits were restored byte-for-byte. All 76 prepared
root sources still match; no PLC/image/stimulus/proof change was needed.

Baseline regressions pass 31/31. Actual recorded rows total 67 (64 accepted,
three extra from the partial repeat). Known additional fixed-vector/normalization
mailbox commands total 12; per-tag write calls are unmeasured. Native root/
sequence/alarm-metadata payloads are 77,856 / 7,308 / 16,616 bytes. Candidate
TASK median/range is 817 us / 816-817, cumulative maximum 4,033 us, zero overlaps;
genealogy is 99 us / 99-100, maximum 1,167 us. Workloads differ; this is not an
isolated publication-cost measurement. WAIT_RESET, high-bit injection and
data-denial detail retain explicit model-only scope where not runtime-observed.
Genealogy is restored, Run/not faulted, Remote, scanning, actual MANUAL=1/idle,
logged out, five saved/live documents equal, original policy/preflight verified.
S3e authorization is consumed. S3f preparation is next; future controller work
requires its own exact-image gates and current approval. No commit/push.

**S3f inventory finding, 2026-10-22:** the independent
[inventory](AB_CANONICAL_PUBLICATION_S3F_INVENTORY_2026-10-22.json) identifies
801 additional legacy paths (2,955 cumulative), including 30 configuration
entries of 25 fields. The current oracle conflicts with the target's Core
types at 110 paths, omits 12 Core fields, and serves all 30 entries as one
host-assembled page. PendingSince is time-of-day without a date; revisions
exclude boot identity; non-empty set/document responses are host overlays.
Read the [contract correction proposal](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md).
The owner has approved its bounded-page/type/time/provider corrections for
offline implementation; section 1 now names this exact additional exception.
The immutable inventory evidence records the earlier pending state. S3f offline
implementation and compiler/model validation are in progress; no controller
operation is authorized and no S3f runtime acceptance is claimed. The reference window of
16 is an implementation choice; Core requires bounded paging without a full
manifest buffer, rather than mandating that numeric window size.

| Order | Surface | Notes |
|---|---|---|
| 3a | Unit core: `Decision`, `Catalog`, `ModePolicy`, `Supported*Published`, `AvailableModels` | Apply D2 bounds (`ModePolicy`, `SupportedModesPublished`, `SupportedRunStylesPublished` from 0) |
| 3b | CM/EM status, command timing, diagnostics | The PLC publishes `DescriptionKey`/reason codes, never rendered text |
| 3c | Sequence: `SequenceSteps`, `SequenceAnnotations`, `ActiveSteps`, step definitions | `ActiveSteps` from 0 (D2); keep fast-step history PLC-side |
| 3d | `AlarmLog` (Active, Ring, Meta), `StateFlags` | 1,469 AlarmLog + 9 flag paths; 2,125 cumulative. Preserve S0 size/read qualification and measure actual same-scan acquisition |
| 3e | `Access` (`Policy.Required` from 0, D2), audit, data policy | Login stays plain PIN through the mailbox. The gateway's salt pre-hash used declaration data and is dropped; the PLC hashes, with `LoginBusy` covering latency |
| 3f | Configuration pages, `ConfigPersist`, `ConfigSets` listing | Pages come from the PLC on `QUERY_CONFIG` (as TC3), not assembled by a client |
| 3g | `Oee`, `OeeTrend`, `Profiler`, `SystemHealth` | Profiler is 900 paths; derivations are event-driven, not per scan |
| 3h | `Part` (+ genealogy), `HostEvents`, `Nameplate`, `SignalTower`/`MachineState` | Keep the existing single append owners; only the publication form changes |
| 3i | `Line` (calendar, shifts) | Owner-approved offline scope: 16 frozen gaps, two Core Line status members and occupied eight-row V3 history; [S3i publication runtime](Evidence/AB_S3I_CANONICAL_RUNTIME_2026-10-24.md) passed 41+8+31 checks, 88 pairs, 87% Capacity; natural calendar/populated-live-history/target-lifetime/Program-Run gates remain open; parameter keys stay `line.`-prefixed |
| 3j | Fieldbus topology as its own published data product (TC3 `GVL_<Project>Fieldbus.Topology`) | Not a module root |
| 3k | `HmiResponse` / release report, `HmiRequest` mailbox, counters/derived production flags and Features | 126 mailbox/report plus seven Unit fields; full command discovery, secret exclusion and complete 24-reason versioned owner; one dispatch owner, ordering per `OPCUA_TRANSPORT.md` |

**Exit:** full equivalence (4,437 genealogy paths under finite approved
correspondences and complete dynamic/extra Core surfaces), plus the actual press
declaration, on Echo. Each declaration proves ST, SFC and ladder, exact-image
Capacity/scan and all required regressions. Genealogy's three renditions do not
accept the press declaration. Fieldbus has its own product proof even though the
frozen genealogy has zero fieldbus paths. Reconcile the changing consumer census
before S6; the original 22-tool/44-test counts predate canonical/frame additions.

### S4 — Generic Dart `CipSessionClient` and the desktop path

**Corrected dependency and two subgates (owner-approved contract A, 2026-10-25):**
V6.6 has an existing scan counter but no manifest binding to its protected
surfaces. Publish the [V6.7 association](AB_CANONICAL_PUBLICATION_S4_COHERENCE_REVIEW_2026-10-25.md)
before a generic client depends on it; never infer a symbol from a declaration
or naming convention. **S4a** qualifies metadata discovery, counter progress and
bounded small rows on the exact-image Echo session, with Capacity/scan/regression
and genealogy rollback gates. **S4b** completes the client below and qualifies
every consumed row/group and tier under active workloads, then desktop rendering.
Initial Status/product-row measurements do not replace those acceptance gates.

**S4a exit passes at its declared Echo scope:**
[runtime evidence](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md) records
31/31 candidate and restored-baseline cases, 4,428-path/type idle equivalence,
798 Good and two payload-free Uncertain group acquisitions, counter progress,
offline replay and native scan. Its exact-image approval is consumed; S4b and
physical acceptance remain open. The two bounded coherence refusals are retained,
not counted as Good values. Full tiers and active workloads are still gates below.

**S4b latest Echo qualification remains open:**
[Refill attempt](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md) passes 41 cases/87 replays, the busy witness and
3,144 entirely Good samples. Desktop becomes STALE after overview at 1,428.145 ms;
later acquisition/final timing are skipped. TASK maximum 9,003 us /zero overlaps.
Genealogy/31 baseline/all final checks pass; authorization consumed. [Read-only
controls](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md) record Flutter scalar tails above 10 ms without isolating
the prior failure cause. The [MSP preparation](Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md) batches only body/count
reads between separate counters, preserving proofs/freshness/read-only policy.
685 HMI/12 skips and 73 focused tests pass; native qualification needs approval.

- **New** `HMI/packages/fraktal_opcua_client/lib/src/cip_session_client.dart`,
  exported like `ads_session_client.dart`. It covers:
  - EtherNet/IP session handling and a large Forward Open;
  - Symbol list (`0x6B`), Template reads (`0x6C`) and Read Tag Fragmented;
  - template-driven decoding plus the manifest lower bound and logical type;
  - `fraktal.opcua.snapshot.v1`, fast/slow tiers like `WebApiSessionClient`;
  - blocking work in a worker isolate, like `AdsSessionClient`.
- **Coherence** follows Part III §3.13 per published row/group and read tier,
  using PLC-published revision/access metadata. Do not require one same-scan
  live document or use the migration observation frame as a shipping protocol.
  Secret and other command-only values stay outside snapshots and cyclic reads;
  bounded retries must degrade quality rather than accept a torn group.
- **Writes** follow `OPCUA_TRANSPORT.md`, but stay disabled unless the endpoint
  is a commissioned CIP Security session (S7). The repository exposes the
  read-only state so the HMI states it explicitly (Core §11.2). Check the
  existing gateway read-only behaviour first and reuse its mechanism.
- **Factory:** `external_repository_factory_native.dart` routes `cip://` to
  the new client.
- **Delete** the spike `HMI/lib/data/cip/` (`cip_session_client.dart`,
  `eip_cip_client.dart`, `fraktal_manifest.dart`, `libplctag_bridge.dart`).
- **Golden tests** replay recorded Symbol/Template/tag bytes to the expected
  snapshot from S1.
- **Gates:** `flutter analyze`, the full HMI suite with the pinned Flutter
  `--enforce-lockfile`, and desktop acceptance on Echo (render all surfaces,
  writes refused with an explicit read-only state).

### S5 — Dart gateway `cip://` for Web clients and commanding

- `HMI/gateway/bin/fraktal_gateway.dart`: add `cip://` beside `ads://` and
  `s7web://`, using the same session client. Add the deployment switches the
  scheme needs (serial pin, slot) and document them in `DEPLOYMENT.md`.
- Writes reach the PLC through the gateway's existing Core §14 gate (token +
  `wss://`, write roots). For each station, ask and record **read-only or
  write-enabled** (AGENTS §3a).
- Update the Windows installer and tray: an instance may use a `cip://`
  endpoint. Drop the never-exercised Python AB gateway packaging path.
- **Acceptance:** the Web HMI renders and commands Echo through the Dart
  gateway, and recovers after a gateway restart.

### S6 — Retirement and collapse

1. **Migrate the harnesses.** The original 22-tool/44-test estimate is
   superseded by the preliminary syntax census: 54 tools/53 test modules have
   direct legacy references, including oracle/metadata dependencies. Classify
   actual runtime readers before migration. The affected generated contexts
   include `read_unit`, `read_layout`, `*_context_members` and the projection.
   Move every acceptance harness, including the 31-row regressions and the
   Part, tower and genealogy executes, onto canonical reads through the S1
   reader. The equivalence gate must stay green throughout.
2. **Collapse the generator.** Make the canonical structures the working
   storage. Remove the old contexts, the v5 manifest tables they described and
   the copy logic, together with the migration-only S3h observation frame
   (`canonical_observation_period_ms`). Record the memory and scan savings.
3. **Persistence (§3.8b).** Relocate it per the owner decision (see §6). TC3
   and TIA keep documents and sets on a PLC-owned medium, so the coherent
   target is a controller medium behind the existing store seam.
   - Probe Logix file and SD services on the 5580 and on Echo first (v38 audit
     N8).
   - Until it is accepted, the Python live-document keeper and set store
     remain as a standalone adapter reading through the S1 reader, not as a
     gateway.
4. **Host-event sink.** Keep it as a deployment adapter (Core §11.6), reading
   the canonical `HostEvents` through a generic reader. Its durability,
   cursor and dedup behaviour is unchanged.
5. **Delete** `fraktal_ab_projection.py`, `fraktal_ab_gateway.py` and the code
   only they used. Update `check_ab_spec.py` and `check_ab_contracts.py` (V2)
   and `check_consistency`.
6. **Documents:**
   - Part III (final form of the S0 drafts);
   - `OPCUA_TRANSPORT.md` (new "Allen-Bradley CIP transport" section beside
     ADS and S7 Web API);
   - `AGENTS.md` §3a (baseline v37+, L24ER retired, `cip://` no longer a
     spike) and §5;
   - the AB README and `AB_NEW_PROJECT_GUIDE.md`;
   - `HMI_CONTRACT.md` (the five D2 bounds).

### S7 — Physical controller and CIP Security

- Obtain a CIP Security-capable 5380/5580 at v37 or above. Commission a
  FactoryTalk Policy Manager policy. Add a TLS client (port 2221,
  certificate-based) to `CipSessionClient`.
- Enable direct writes per D9.
- Physical acceptance: Capacity/fit, scan, retention across power cycle,
  download and upgrade, and Part III §11.2.1 security evidence.

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scan time grows as Python derivations move into ST | Measure per surface. Compute derivations on change, not every scan. Keep owners single (one append owner per ring) |
| Structure-size or CIP read limits for large roots (AlarmLog, Profiler) | Measure in S0 step 4. If needed, publish a surface as its own data-product tag with the identical canonical path rule, decided once in Part III |
| String memory at Core widths | Budgeted against 3 MB; measured per stage |
| Persistence relocation (Echo may not emulate SD/file services) | Probe first. Keep the standalone adapter until a medium is accepted. Owner decision recorded |
| Harness migration volume (preliminary 54 tools/53 tests with direct references) | Classify runtime readers, then migrate behind the equivalence gate before deleting anything |
| Echo availability after reboot | Elevated start by the owner. Check the service and listener before any guarded step |
| HMI customization bound to the five old AB array paths | Call it out in release notes. The mapper is already base-agnostic |

## 6. Owner decisions pending

1. V2/Part III target approval **recorded 2026-10-20** (D6/D7 included); no longer pending.
2. The §3.8b persistence medium (controller medium versus a standalone
   adapter) after the S6 probe.
3. Read-only or write-enabled for each gateway station (S5, AGENTS §3a).
4. Hardware for S7.
5. Commit and push policy for this work. Nothing is committed yet.

## 7. Relative size (estimate, not a commitment)

| Stage | Estimate |
|---|---|
| S0 | 1–2 days |
| S1 | 2–3 days |
| S2 | about 1 week |
| S3 | 3–6 weeks |
| S4 | 1–2 weeks |
| S5 | about 1 week |
| S6 | 2–3 weeks |
| S7 | hardware-bound |

Native gates (owner Capacity, downloads) set the real pace.

## S3i calendar lifetime follow-up prepared — 2026-10-24

The next natural-calendar/retained-Program-Run fixture is ready offline for
unchanged ACD A5FAFA46…7E36C42 (measured 87% Capacity). It uses a fresh published
Line.LastUpdate, one twelve-hour interval ending three minutes later, target
40 → requested 99, queued original-calendar restoration, two real newest-first
history rows and exact before/after Line value/type equality across one
Program/Run cycle without downloading in that cycle. No private clock access
or clock set is added. Normal path: 38 public Line commits, ceiling 64 including
cleanup; operator-session and exact-target guards remain strict.

All 2,189 AB /74 root tests pass, as do eleven focused emitted-ST lifetime
tests, six negative authorization cases and the guarded helper build. The
170 inherited source bindings and PLC image are unchanged; two fixture/test
sources are added. All 88 prior native pairs replay unchanged. The required
v38 compiler/read-back and Capacity results transfer by exact image hash.

No controller access or change occurred in this preparation. Current owner
approval is still required for the fresh download, public calendar writes and
retained cycle; the earlier session approval is consumed. Proposed session
repeats the 41 candidate checks, adds calendar/retention proof, then rolls back
and restores five documents/31 baseline checks. Fault clears, clock changes,
power operations and hard kills remain excluded. S3i exit and S3j stay open.
See [preparation evidence](Evidence/AB_S3I_CANONICAL_LIFETIME_PREPARATION_2026-10-24.md).
