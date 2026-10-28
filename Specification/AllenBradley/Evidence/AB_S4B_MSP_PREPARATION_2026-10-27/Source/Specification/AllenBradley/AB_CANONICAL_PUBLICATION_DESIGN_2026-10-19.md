# Fraktal/AB canonical publication — one architecture across bindings

Non-normative design note, 2026-10-19, continued through 2026-10-27. Status:
**S3 Echo exit and S4a pass; S4b remains open.** [Refill qualification](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md)
passes 41 cases/87 exact replays, the busy witness and 3,144 entirely Good
samples. Desktop initially LIVE then STALE after overview at 1,428.145 ms.
TASK maximum 9,003 us /zero overlaps; genealogy/31 baseline/final checks pass.
The [read-only controls](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md) establish packet support and long scalar
tails, not the precise failure cause or canonical acceptance. The [prepared
MSP path](Evidence/AB_S4B_MSP_PREPARATION_2026-10-27.md) batches body/count reads between separate counter requests,
with strict read-only/type/extent validation and original proof/freshness limits.
No intra-packet ordering assumption. 685 HMI/12 skips and 73 focused tests pass.
Native improvement remains unproven; fresh approval required. Unchanged PLC
retains 2,339 tests/65% Capacity by hashes. V2/Part III inactive; S5-S7/physical
I/O remain. See the [plan](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).

## Owner decisions

- **Read-only configuration discovery:** the owner selected option A in the
  [S4b review](AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md).
  V6.8 publishes a versioned definition/value view, including occupied model
  banks and access masking, from the existing configuration owner. Direct
  unsecured CIP never uses a mailbox query to select a page or bank. This
  approves the contract and offline work; the exact new image/session requires
  separate current authorization.

- **Coherent architecture** (2026-10-19): *"having a coherent architecture
  along all implementations is important."* Fraktal/AB shall reach the HMI the
  way TC3 and TIA do. The PLC publishes the canonical Core module tree itself,
  and a **generic** session client discovers it through the controller's own
  symbolic services, with no station knowledge.
- **The L24ER is out** (2026-10-19). The 1769-L24ER/v33 is retired as a
  reference target. Its dated evidence stays as history.
- **Delegated:** the owner asked that the remaining choices be narrowed from
  the specification objectives and the other bindings. They are settled below,
  each with its reference.

Rejected this session, with the reason:

- **Finishing the Dart direct-CIP prototype** (`HMI/lib/data/cip/`) as a
  hand-written port of the Python projection. It keeps two copies of one
  contract (O9) and still needs the station declaration.
- **An HMI-owned gateway sidecar.** It keeps the off-PLC projection and its
  declaration, so station knowledge would live outside the PLC, next to the HMI.

## Where each binding keeps the canonical tree today

| | TC3 (Part II) | TIA (Part IV) | AB today (Part III) |
|---|---|---|---|
| Canonical module tree (`Status : ST_ModuleStatus` …) | Published by the PLC (TF6100 / ADS symbols) | Published by the PLC (instance DBs, Web API / OPC UA) | **Reconstructed off the PLC** by `fraktal_ab_projection.py` |
| Client | Generic (`opc.tcp`, `ads://`) | Generic `WebApiSessionClient` (`s7web://`) | Python gateway with the **station declaration** |
| Station knowledge off the PLC | None | None | The declaration module (steps, config pages, policy …) |
| Desktop HMI | Direct | Through the gateway; direct where OPC UA is licensed | Through the gateway; `cip://` is a 45-field spike |

The AB deviation answered the L24ER's 750 KB memory and the v33 type map.
With the L24ER retired, neither constraint remains.

## Measured facts (local Echo L81E v38, image `6DEC4C1DC2F7F78A`)

Captured read-only on 2026-10-19. The raw capture is
`C:/work/fraktal-ab-echo-20261019/projection_capture_01.json`, SHA-256
`5CA907E6076A02833A5670EF3741CD62ACA626F762F9DD557F1E4B9C2C3BBE0C`.

- **One gateway pass is 50 CIP reads, 126,076 bytes.** Ten are manifest
  reads (74 KB) and forty are state reads (51,524 bytes). An offline replay
  reproduces all **4,437** projected values exactly, so the capture is the
  golden vector for value equivalence.
- **The conversion runs about 4,500 lines of Python across 35 modules.**
- **The manifest describes the generated contexts.** It has 670 `Fields` rows,
  and only **36 of the 4,437 canonical paths** correspond to one of them.
- **Census of the canonical values:**

  | Type | Count |
  |---|---|
  | BOOL | 914 |
  | integer | 2,155 |
  | float | 83 |
  | string | 1,284 |

  Of the strings, 613 are empty, 212 are dictionary keys, 145 are names or
  paths and 314 are data. The longest is 54 characters and the mean is 11.6.
- **Echo serves generic symbolic discovery.** The Symbol object listed 61
  controller tags in 48 ms, and the Template object decoded 50 UDTs with member
  names and types. This is the CIP counterpart of TIA's `PlcProgram.Browse`.
- **Five arrays already differ from TC3.** AB publishes `ActiveSteps`,
  `ModePolicy`, `Required`, `SupportedModesPublished` and
  `SupportedRunStylesPublished` from index 1; TC3 declares them from 0. The
  other 22 published arrays match. The HMI mapper tolerates either base, but
  path identity, and with it layouts and customization bundles, differs.
- **CIP Security** objects `0x5D/0x5E/0x5F` are absent on Echo.
- **The 1756-L81E has 3 MB of user memory** (Rockwell 1756 selection guide).

## Target architecture

1. **The PLC publishes the canonical contract.** Each deployed root is one
   controller-scope tag named exactly as the root's browse name (`Press`). Its
   UDT carries the Core members under their canonical leaf names, with child
   modules as members named as the schematic names them.
   - Published values have effective External Access *Read Only*;
     `HmiRequest` alone is effectively *Read/Write*. Private storage is *None*.
     The supplementary probe confirms a Read Only parent blocks its writable
     child. Ancestors of HmiRequest must be Read/Write, other public branches
     Read Only. None storage stays outside whole-read canonical records.
     The manifest supplies effective member access absent from Template data.
     The R6 allow-list audit enforces the effective policy (Core §3.10(a)).
   - Static text stays a dictionary key resolved by the HMI (HMI_CONTRACT §1).
   - The **manifest remains the self-description service** (Core §3.10.2), now
     describing the canonical fields. It supplies only what Logix types cannot
     say themselves: logical type and logical array lower bound/element count
     (D2, D3, D6), plus effective member access absent from Template data.
     S0 found that native BOOL arrays are described as DWORD
     storage; physical word count is not the declared logical element count.
2. **One generic `CipSessionClient`** lives in `fraktal_opcua_client` beside
   `AdsSessionClient` and `WebApiSessionClient`, selected by `cip://`.
   - It discovers through Symbol + Template plus the manifest. A root is any
     controller tag whose type has a top-level `Status` member (TIA §3.10.1).
   - It reads whole structures, decodes them by template, emits
     `fraktal.opcua.snapshot.v1`, and caches discovery by manifest content hash
     and revision.
   - The **desktop HMI uses it directly**, and the **Dart gateway** uses it for
     Web clients, as with ADS and the Web API.
3. **No station declaration is needed at runtime.** The declaration stays the
   one source the generator turns into the L5X. The Python projection, the
   Python gateway and the Dart spike all retire at S6.

## Decisions

| # | Topic | Decision | Basis |
|---|---|---|---|
| D1 | Target family | A single **reference profile**: CIP Security-capable 5380/5580 class at **v37 or above**. Echo L81E v38 is the development bench. A future smaller family gets a declared reduced profile on **this same** architecture, never a second one. | Owner decision; AGENTS §3a baseline; TIA §1.1 family profiles |
| D2 | Array bounds | The canonical index is the **Core-declared index**, as TC3 and TIA publish it. Logix arrays are physically 0-based, so the manifest states each published array's logical lower bound and element count. The client expands packed BOOL storage before applying canonical index = physical element index + lower bound. The five deviations listed above are corrected. | TC3 Core (21 arrays from 1, 7 from 0); TIA mirrors bounds (`Policy : Array[0..MODE_LAST]`, `Catalog : Array[1..N]`); S0 DWORD storage finding; O9 |
| D3 | BOOL | **Native BOOL members.** The BOOL-free public UDT was a v33 contract rule. | TC3/TIA publish BOOL; v38 exploratory verify 0/0 |
| D4 | Strings | **Core-declared widths** (TC3 uses `STRING(2…255)`, keys 160, set lines 480). One Logix string type per width, `LEN : DINT` + `DATA : SINT[n]`, recognised by shape. UTF-8 bytes with a byte-counted `LEN`. A literal wider than its field is rejected at generation, never truncated at run time. | TIA §3.8.1 reference profile keeps Core widths; O10; S12 byte-counted LEN |
| D5 | Numbers and enums | Enums as `DINT` with generated constants. `INT`/`DINT`/`REAL`/`LREAL`/`LINT` native. 64-bit integers are delivered exactly as Int64, never through a float. LREAL generation retains declared precision: use the qualified `L` suffix in ST or typed Decorated LREAL initial data. Supplementary S0 preserves pi and 1.0000000000000002 exactly; the untyped REAL-rounded control remains a finding. | TIA type map; v38 native build/read-back and S0 runtime bytes |
| D6 | Durations (Core `TIME`) | **DINT milliseconds**, marked DURATION in the manifest; transport **Int32 ms**, wire ordinal 3. It matches Core's width and units directly. Measured TIME32 is 32-bit µs (insufficient range); TIME is 64-bit µs and would require normalization plus wider publication. Native time may remain internal to an owning provider, which converts and range-checks before publishing. | S0 native type codes/units; TC3 `TIME` and TIA `Time` are 32-bit ms; O4/O9 |
| D7 | Timestamps (Core `DT`) | **Native LDT**, 64-bit Unix ns, delivered as **DateTime UTC, zero = unset**. S0 preserved the nanosecond LINT-to-LDT vector exactly; its microsecond LINT-to-DT assignment divided by 1,000. A clock provider converts µs to ns once before assigning LDT. | S0 runtime bytes; TIA S7-1500 `LDT`; Rockwell's LINT-as-LDT conversion rule |
| D8 | Quality and source time | CIP carries no source timestamps; the client stamps read time. | Web API client and current gateway do the same |
| D9 | Writes | **Direct CIP writes only over a commissioned CIP Security policy.** Without it, the direct client is a read-only projection and says so in the HMI. Commands then go through the Dart gateway over `wss://` with an authenticated principal; gateway writes stay a per-deployment recorded decision (Part III §11.2.1). Echo has no CIP Security, so the desktop is read-only direct and commands through the gateway. | Core §11.2 (authenticated principals, integrity, confidentiality; read-only stated explicitly); Core §7.7(d); TC3 OPC UA secure channel; TIA HTTPS web user |

## Cost estimate (to be replaced by Studio Capacity measurements)

- **Published data:** numbers about 12.6 KB, plus strings. Strings take about
  21 KB at their actual maxima, and more at Core widths (D4) because every slot
  is sized. Some existing storage is replaced rather than duplicated: the
  51.5 KB state contexts and the 48.6 KB Localization table.
  - Net growth is estimated at **+20 KB to +150 KB**, against 3 MB.
- **Logic:** derivations move from Python into generated ST, notably OEE
  factors, machine state, condition records, release-report rows and alarm
  presentation. Code size and scan time are **unmeasured** and are gated
  per stage.

## Stages and gates

Each stage carries the same gates:

- generator tests and the AB suite;
- v38 build and read-back on both targets;
- the owner's Studio Capacity Estimate;
- the guarded Echo download;
- the 31 ST/SFC/LD regressions;
- **value equivalence**: the canonical publication read generically equals the
  Python projection for the same controller state, path by path and type by
  type. Allowed differences are the five D2 bound corrections plus the finite
  owner-approved S3f corrections and S3g 200 numeric / 224 dependent value paths
  enumerated in the plan §1. No general coercion, tolerance or ignored path applies.

| Stage | Content | Exit |
|---|---|---|
| S0 | Probe image measuring D2–D7 on Echo over CIP; supplementary size/naming/access questions before S2. First runtime/restore completed; type selections and frozen V2/Part III amendment drafts are recorded. | D6/D7 resolved by measurement and V2 draft approved by the owner |
| S1 | Python reference reader: generic Symbol/Template/manifest discovery into a snapshot (pylogix), compared with the projection | Equal on the published subset |
| S2 | Generator publishes the module tree (`Status` of every module, mode, step) canonically **alongside** the current contexts | Equivalence on Echo for that subset; memory and scan deltas recorded |
| S3 | Remaining surfaces one at a time: Sequence, AlarmLog, Part/HostEvents, Config, OEE/Profiler, Access, Line, Fieldbus | Full 4,437-path equivalence on Echo |
| S4 | Generic Dart `CipSessionClient`; desktop HMI `cip://` uses it, read-only per D9 | Same equivalence from Dart; HMI tests; desktop acceptance on Echo |
| S5 | Dart gateway gains `cip://` for Web clients and commanding | Web and write acceptance through the gateway |
| S6 | Retire the Python projection, the Python gateway and the Dart spike | Docs and gates updated; nothing reads the old contexts |
| S7 | CIP Security on a capable physical controller; direct writes enabled per D9 | Part III §11.2.1 evidence |

## Documents that change when the stages land

- **Part III:** §3.8 type map, §3.10 exposure and §11 transport, plus the
  L24ER retirement.
- **Frozen contracts:** `AB_FROZEN_CONTRACTS_V1.json` becomes V2; the manifest
  major version steps.
- **`OPCUA_TRANSPORT.md`:** a CIP transport section.
- **`AGENTS.md`:** §3a and §5.
- **The AB README and the new-station guide.**
- **`HMI_CONTRACT.md`:** unchanged apart from AB adopting TC3's bounds for
  the five D2 arrays.

## Next step

The owner approved [frozen contracts V2](AB_FROZEN_CONTRACTS_V2.json) and the
[Part III amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md).
The first probe was measured and genealogy restored with 31/31 regressions.
Approval recorded on 2026-10-20: “Approve drafts and proceed to S1”. The
target approval does not activate V2 in the shipping implementation. The S1
reference-oracle exit passes; see [S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md)
for its scope and the S2 physical-manifest/paired-live boundary. The supplementary size/naming/access and full-precision
LREAL cases need a newly prepared/gated probe and separate current download
authorization; they are not covered by the completed first session.

2026-10-21 continuation: the owner authorized the guarded supplementary
session and supplied the exact-artifact Capacity screenshot (69%, in blocks).
The session completed; see [runtime evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md).
A 2 MiB record reads exactly using fragmented reads at 500/4000-byte connection
settings; a root named Press is discoverable; both precise LREAL initializer
forms pass. The effective parent/member access vector passes and all writes
are restored. Symbol attribute 10 distinguishes top-level RO/RW on this Echo,
while the captured Template metadata does not distinguish member permissions.
This requires a PLC-manifest member-access annotation, without station facts
in a client. The target drafts now record these measured implementation rules.
Genealogy is restored with five documents, 31/31 regressions and passing final
checks. S2 is the next implementation stage; its image needs its own compiler,
equivalence, Capacity, scan and current controller-operation gates.

The subsequent owner-approved S2 session completed on 2026-10-21; see
[S2 runtime evidence](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md).
The generic reader discovers seven modules and matches the explicit 46-path
subset, including all types, under an equal-even entire-scan generation.
Both owner Capacity records and native scan deltas are measured. Candidate
and restored genealogy regressions pass 31/31 each, with final readiness and
five-document equality. The interrupted upload and guarded recovery remain
in the evidence; their earlier empty-controller cause is unconfirmed.
S2 exit is satisfied. S3a is next; V2 remains an inactive shipping target.

S3a continuation: the owner selected the oracle's logical path set, with
PLC-published extents/live count references. The V6.1 candidate implements
that view; see [S3a preparation](Evidence/AB_S3A_CANONICAL_PREPARATION_2026-10-21.md).
Its generator, generic reader and paired harness pass offline/native gates,
with unchanged S2 output. The subsequent approved S3a runtime session passes
the 94-path subset, four active-decision pairs and candidate/baseline 31-row
regressions. Capacity is 817,476 used / 3,145,728 total blocks, +72,232 over S2;
native LastScanTime median is 110 us and cumulative MaxScanTime 1,178 us,
with zero overlaps. Genealogy and five documents are restored. See
[runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md), including
the retained acquisition failure and read-harness correction. Reserved
physical slots do not become extra accepted paths. Decision.Timeout/SourcePath
remain an explicit full-Core gap. S3b is next; shipping V2 remains inactive.

The owner requested automatic Capacity estimates. A
[calibrated offline forecast](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md)
predicts held-out S3a usage within +1.0481%. It supplies advisory budgets.
The automatic Studio collector is now qualified on the L81E/v38 English UI:
it reproduced all exact owner S3a Capacity values from the original hash-bound
review copy, then measured S3b at 991,612 used / 3,145,728 total blocks (31%).
It opens only offline copies, preserves source hashes and closes its own
review process. Future stages can obtain the measured gate without repeated
screenshot requests. See the method note for the qualification scope.

S3b's [304-path preparation](AB_CANONICAL_PUBLICATION_S3B_NOTES_2026-10-21.md)
adds existing diagnostics and CM command timing. One generated PLC resolver
owns reason/permit keys, electrical joins and calendar-to-LDT conversion;
generic clients use only discovered Templates and manifest annotations.
Native v38 builds/read-backs pass on both targets, with unchanged S2/S3a
generated outputs. The subsequent approved S3b session passes at 304 paths,
including four decisions, ten held and four Unit first-out fault pairs across
ST/SFC/LD. Candidate/baseline regressions pass 31/31 each. Median native scan
is 123 us, cumulative maximum 1,190 us, zero overlaps. Genealogy is restored.
The retained acquisition and coverage failures led only to observer fixes:
independent read connection and observing the Unit that owns an adopted fault.
See [runtime evidence](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md).
S3c is next; V2 remains inactive for shipping.


S3c preparation (2026-10-22) adds an independently inventoried sequence and
current-step subset, 647 paths total. The PLC still owns visits/durations/marks.
The [V6.2 draft](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md) publishes
bindings from separate native definition records to discovered roots, with a
live fragment revision for cache coherence. Native decoding joins disjoint
leaves under matching containers; no station derivation enters the reader.
The 21-slot annotation view preserves the oracle, above Core's default 16.
Full-Core gaps remain explicit in the [S3c notes](AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md).

A readiness audit found the inherited work scripts' Mode==0 MANUAL label was
wrong: AUTO=0, MANUAL=1. Echo is AUTO/idle, logged out. Earlier readiness prose
is corrected by this finding; sealed evidence remains immutable. The new
guards derive the declaration's manual ordinal. The subsequent S3c session was explicitly approved and completed.


S3c offline gates now pass: 2,052 AB tests, 74 root tests, both v38 builds
and strict read-backs/access, unchanged S2/S3a/S3b generation/replays, automatic
Capacity 1,107,552 / 3,145,728 Blocks (35%, +115,940 over S3b). Prepared ACD
A2559188...0C2286C remains pinned. Runtime and corrected MANUAL readiness now
pass under the completed current approval. See [preparation evidence](Evidence/AB_S3C_CANONICAL_PREPARATION_2026-10-22.md).


S3c runtime now passes at 647 paths/types: four decisions, 14 held/fault pairs
and 21 sequence pairs across ST/SFC/LD; both 31-row fixtures pass on first runs.
Mode clearing, sparse warning notes and retained completed fast steps pass.
Forty paired captures and one generic capture replay identically, with the
same equal-even proof and 1-6 attempts. Candidate native median/max is
200/1,600 us, zero overlaps; these observations have a different workload
from prior stages. Genealogy is restored, actual MANUAL=1/idle, logged out,
five documents equal live and the original preflight unchanged. See
[runtime evidence](Evidence/AB_S3C_CANONICAL_RUNTIME_2026-10-22.md).
S3d is next; this approval is historical for a new image. V2 stays inactive.


S3d offline preparation adds 1,478 paths (1,469 alarms plus nine flags), for
2,125 total, using the same V6.2 reader and a second metadata binding. The PLC
alarm owner alone appends/closes/resets; publication mirrors it. A shared
calendar routine and changed-input caches serve diagnostics, event stamps and
flags. No earlier generated image changes. Both v38 builds/read-backs/access
and 2,062 AB tests pass. Automatic Capacity is 41%, 1,290,016 used of 3,145,728
Blocks, +182,464 over S3c. See the [S3d notes](AB_CANONICAL_PUBLICATION_S3D_NOTES_2026-10-22.md).
The original prepared pin is E5CA9AB3...7CF7C9D. S3d runtime now passes under
the owner's exact-session approval: 31 candidate and 31 restored-baseline rows,
48 paired captures including idle, all 2,125 values/types and generic discovery.
Four decisions, 14 held/fault, 21 sequence and eight reset captures cover all
renditions. Active/closed events, ring wrap, nonzero duration, flag transitions
and Blocking release are observed; WAIT_RESET remains model-only coverage.
Two failed acquisition attempts retain eight and 26 passing rows. The corrected
oracle uses V6.2 revision-cached metadata and two guarded read-only connections,
with both live reads inside the unchanged whole-scan proof (1-8 attempts).
The generic reader and approved PLC image are unchanged. Native root/definition/
metadata sizes are 77,304 / 7,308 / 16,616 bytes. Candidate scan median/max is
437/3,111 us, baseline 99/1,167 us, zero overlaps. These are different workloads,
not an isolated publication-cost measurement. Genealogy, MANUAL=1 readiness,
five documents, policy and original preflight are restored. See
[runtime evidence](Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md).
S3e is next; S3d approval is historical. No full-Core/physical claim or shipping activation.

S3e offline preparation now adds 29 Access/data-policy paths (2,154 total),
and enriches the existing ring's MESSAGE slots from its Access audit owner.
Changed-input caches preserve slot replacement and avoid formatting unchanged
rows. The provider alone grants authority; private registrations/secrets stay
private. A generic BITSTRING32 correction exposes the masked sequence word as
UInt32, with high-bit tests and unchanged S2/S3a/S3b/S3c/S3d images/replays.
Both v38 builds/read-back/access, 2,078 AB tests and automatic Capacity pass:
1,568,852 / 3,145,728 Blocks (49%, +278,836 over S3d). The prepared pin is
95E85B50...A1B240B. See the [S3e notes](AB_CANONICAL_PUBLICATION_S3E_NOTES_2026-10-22.md).
Its new approval must explicitly include the two additional fixed Access
checks. That exact session is now completed: all 2,154 values/types match, with
31 inherited candidate rows, two Access checks, 54 replayed paired captures
including idle and 31 restored-baseline rows. Access Busy/failure/success/logout,
manual/class policy changes and shared-ring audit text pass. The first audit
mistakenly checked MANUAL at Required[1]; its owner uses gate 2. A retained
partial repeat added three recorded rows before the observer expectation
stopped it. The corrected owner-derived audit accepts the original complete
captures. Temporary source edits were restored; all 76 prepared sources match.
The PLC/image and unchanged proof did not change. Accepted attempts range 1-41.
Native root/bindings total 101,780 bytes; candidate median/max is 817/4,033 us,
baseline 99/1,167 us, zero overlaps. Different workloads preclude an isolated
cost claim. Genealogy, five documents, policy and MANUAL=1 readiness are restored.
See [runtime evidence](Evidence/AB_S3E_CANONICAL_RUNTIME_2026-10-22.md).
S3f preparation is next; S3e approval is historical for future controller work.

S3f's independent inventory now identifies 801 additional legacy paths
(2,955 cumulative). The [contract review](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md)
enumerates 110 Core type mismatches, 12 missing Core fields, unbounded host page
assembly, a time-of-day PendingSince, boot-insensitive revisions and host-only
set/document overlays. The owner approved the scoped correction in question
`call_eead11c567404709986d61b2907a3d61:0`; the plan's acceptance clause now
names it explicitly. The immutable inventory retains its pending state at seal
time. S3f offline preparation now has both v38 compiler/read-back/access gates
and a prepared ACD, pin A05695F1...E3EB66. Automatic Studio Capacity passes at
73% (2,298,412 used / 847,316 available / 3,145,728 total Blocks). See the
[S3f notes](AB_CANONICAL_PUBLICATION_S3F_NOTES_2026-10-23.md) and V6.3 wire draft.
The owner subsequently authorized the exact session; its recorded scope now
passes with 31 inherited candidate rows, two Access/eight configuration cases,
88 paired replays and 31 restored-baseline rows. The PLC image and generic
reader are unchanged. Read-only packet balancing and explicit MANUAL policy
observations fix the acquisition/audit findings without weakening proof.
Closing gates pass 2,108 AB tests and 74 root tests; 140 current sources are
bound. Genealogy, five documents, policy and MANUAL=1 readiness are restored.
See [runtime evidence](Evidence/AB_S3F_CANONICAL_RUNTIME_2026-10-23.md).
That session approval is consumed. Retained restart and active-model native
revision vectors remain open before full S3f acceptance. V2 stays inactive;
no commit/push is authorized.


## Current S3g preparation (2026-10-23)

**S3g complete offline preparation, 2026-10-23:** both approved amendments
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



## S3g Echo acceptance (2026-10-23)

**Latest, 2026-10-23: S3g exit passes on Echo.** All 83 planned checks
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
S3h inventory is next; further controller changes need separate current approval.

