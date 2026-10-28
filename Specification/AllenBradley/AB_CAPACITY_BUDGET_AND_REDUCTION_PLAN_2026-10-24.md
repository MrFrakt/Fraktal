# AB canonical publication — capacity budget and memory reduction plan

Non-normative, 2026-10-24. **Rough estimate, not a Studio measurement.** Every
image still has to pass the measured Capacity gate. Figures are Studio
Capacity Blocks on the 1756-L81E v38 reference (3,145,728 total).

## 1. Where the memory goes today

Basis: a least-squares fit of the twelve measured images (genealogy baseline,
S2 to S3i) against modeled data bytes and ST tokens. The result is about 0.97
Blocks per data byte, 8.0 Blocks per ST token, plus about 77 K fixed. Residuals
are within ±40 K (±1.5%) on all twelve. The S3i bench image (2,763,512
measured, 88%) attributes as follows:

| Component | Blocks (fit) | Share |
|---|---:|---:|
| Logic — canonical publishers | 1,246 K | 45% |
| Data — canonical manifest | 384 K | 14% |
| Logic — mailbox, access, sets | 182 K | 7% |
| Data — observation frame (migration only) | 174 K | 6% |
| Data — canonical root (published state) | 136 K | 5% |
| Logic — sequences (ST + SFC; ladder rungs uncounted) | 121 K | 4% |
| Logic — legacy scan services (owners) | 108 K | 4% |
| Logic — module/Unit AOIs | 86 K | 3% |
| Data — legacy V5 manifest tables | 78 K | 3% |
| Data — canonical private work | 72 K | 3% |
| Data — legacy contexts and rings | 47 K | 2% |
| Data — definitions, mailbox, other | 53 K | 2% |
| Fixed | 77 K | 3% |

Four routines hold most of the publisher logic, almost all unrolled:

| Routine | Tokens | Blocks (fit) | Assignments | Loops |
|---|---:|---:|---:|---:|
| `CanonicalConfigPage` | 70,476 | 566 K | 3,154 | 1 |
| `ScanCanonical` | 35,160 | 282 K | 1,768 | 44 |
| `CanonicalAccessAudit` | 22,998 | 185 K | 1,239 | 1 |
| `CanonicalDiagnostic` | 13,028 | 105 K | 923 | 0 |

The bench-only `S3iNativeChecks` acceptance routine adds about 41 K.

**Cost of one more module.** Generating S3i with one extra cylinder CM adds
about 56 K: 29 K data and 27 K logic. Of the data, 21,200 bytes are manifest
rows. The module's own published state is only 2,480 bytes, so describing it
costs about 8.5 times the data. Another 2,832 bytes are the frame copy. Of the
logic, 1,785 tokens are unrolled per-instance publishing, 680 per-module
mailbox dispatch and 335 access audit. With 382 K free, only about six more
modules fit. Three extra modules fail generation before memory even matters:
the legacy V5 manifest is capped at 768 fields.

The manifest has 467 rows. Each carries three `STRING(255)` fields
(CanonicalPath, CountPath, Indices), about 828 bytes per row. Only 181 rows
carry anything beyond the native type, and same-type instances repeat
identical relative rows.

## 2. Estimate of the full implementation

| Image | Estimate | Of 3,145,728 |
|---|---:|---:|
| S3i measured (genealogy migration image) | 2,763,512 | 88% |
| + S3k reports/mailbox (+80 to +200 K) and S3j fixture node (+70 to +140 K), current design | 2.91–3.10 M | 93–99% |
| Press migration image at S3 final, current design | 2.8–3.3 M | 89–105% |
| End state after S6 retirement only (frame, legacy contexts/tables, copy layer removed) | 2.3–2.6 M | 73–83% |
| End state with the reduction plan below | 0.9–1.4 M | 29–45% |

The migration-form figures are the immediate risk: S3k, S3j and the press
probably do not fit as currently generated. Reduction therefore has to start
before S6, not after. The end-state range is judgment-based (±30%): it assumes
the redesigned forms below, which have not been built.

**Marginal module cost.** About 56 K today. About 45 K after S6 alone, which
leaves room for about 12–19 more modules. About 5–8 K with the plan: the type's manifest rows and
logic are paid once, and an instance adds only its state and a call. At that
rate the freed ~1.7–2.2 M holds a station several times larger than the
genealogy fixture, while scan time stays to be measured.

## 3. Reduction plan

Each step keeps the published canonical paths, values and types identical and
is proven the same way: the generic reader's snapshot must not change, then the
exact-image compile/read-back, measured Capacity, scan and native regressions
pass. Plan §3 still binds: no feature cut, truncation or weakened validation.

| # | Step | Objective | Saving (rough) | When |
|---|---|---|---:|---|
| R1 | **Per-type, exception-only manifest.** Annotate a UDT member once per type, not once per instance path. Omit rows the native Template already states. Move CountPath/Indices to a sparse table. Instances inherit their type's facts. V6 minor version; the reader keeps reading older minors | O9 derive once, O4 discovery cost flat in instance count | 330–360 K; manifest marginal per instance ≈ 0 | Before S3k |
| R2 | **Table-driven configuration page and access audit.** Generated constant descriptor rows (ordinal, record, member index, kind, label key) plus one loop routine, replacing 4,393 unrolled assignments. Records are all-DINT, so a single CPS into a DINT scratch array makes members addressable by index | O1 once per mechanism; O10 bounded, deterministic | 500–650 K | Before S3k |
| R3 | **Publish per type, not per instance.** At S6 the canonical leaf becomes the module's working storage: the module AOI (once per type) writes it directly through InOut. `ScanCanonical`/`CanonicalDiagnostic` keep only per-instance calls | O1/O9 behaviour once at the owning level | 250–330 K; logic marginal per module → ~2 K | S6 (prototype earlier) |
| R4 | **Table-driven mailbox dispatch.** Module index tables instead of per-module unrolled branches | O1 | 30–45 K; −680 tokens per module | With S3k |
| R5 | **One AUTO rendition per production image.** The declaration selects ST, SFC or ladder. Acceptance images keep all three for the rendition-parity gate | O2 language choice is the author's | 60–120 K | Production profile |
| R6 | **Acceptance instruments out of production images.** Native-check routines and the observation frame are declaration-gated, like the frame already is | O9 minimum surface; §5.7 test hooks never ship | 40 K now, 174–220 K frame | Now / S6 |
| R7 | **Declared bounds and no duplicate private strings.** Rings and histories sized to the declaration within Core ceilings; private caches hold indices, not second copies of published text | O4 proportional surface; O10 bounded | 20–50 K | Opportunistic |
| R8 | **S6 retirement.** Legacy contexts and V5 tables (with their 768-field cap), the copy layer and the frame | O9 one authoritative source | Included in R3/R6 above, plus 120–130 K data | S6 |

**Scan time is the second budget.** The candidate's cumulative TASK maximum
is already 9,206 µs against a 10 ms period. Table-driven forms trade code size
for indirect addressing. View-specific work (configuration pages, audit text,
on-demand topology identity) should therefore run on request or on change,
never every scan (O4). Each step measures the 20-sample TASK gate alongside
Capacity.

**Order.** Do R1 and R2 first, as generator-internal changes validated by an
unchanged generic snapshot and a native session. They restore about 0.8–1.0 M
of headroom in the migration image, which S3k, S3j and the press need. R4 goes
with S3k. R6's native-check gate is immediate. R3, R5 and R8 belong to S6 and
the production profile. Smaller controller families still need the D1 reduced
profile: even 0.9 M exceeds an L24ER-class 786 KB part.

Analysis inputs (offline, read-only): `C:/work/fraktal-ab-s3j-20261024/capacity_01/`
(`capacity_breakdown.py`, `breakdown_01.json`, the +0/+1/+3 module
generations and their logs).

## 4. Progress

**Latest: R1/R2 native acceptance passes (2026-10-24).** The exact combined
D170F1E3?33FF906C image passed 41 candidate cases, seven calendar rows,
retained Program/Run, 4,010 typed paths and 97 independent replays. Rollback,
31 baseline cases and final state pass; genealogy is restored and approval
consumed. Capacity remains 52% displayed. Steady LastScan median is 874 ?s;
cumulative max is **9,829 ?s**, zero overlaps, only **171 ?s below the 10 ms
period**. This includes startup/retained cycle and does not isolate R2 cost.
Future reductions/stages must retain measured scan gates alongside memory.
Read [runtime evidence](Evidence/AB_R1_R2_CANONICAL_RUNTIME_2026-10-24.md).
The offline history below remains the preparation record; R1/R2 are accepted
only at this genealogy/Echo migration-frame scope. S3j is next.

**R2, offline, measured.** The configuration page and access audit now have
a table-driven form behind the declaration opt-in `canonical_table_driven`:
- every literal stored once in a constant private SINT pool (2,504 bytes);
- the page walks a 30-row definition table;
- the audit reads three slice tables through one shared append routine.

ST tokens fall from 70,476 to 1,456 (page) and from 22,998 to 1,074 (audit).
On the S3i bench declaration:
- **Capacity:** measured 2,014,032 used / 1,131,696 available / 3,145,728
  total Blocks (64%), against 2,763,512 for the accepted S3i image. That is
  **749,480 Blocks freed**; the fit predicted 2.05 M.
- **Compile:** both v38 targets build with import 0/0, and strict read-back is
  equivalent (59 bodies, 46,880 initial values). Effective access passes, with
  all new tables private.
- **Behaviour:** all 9 configuration-page and 7 access/audit executed-ST
  oracle cases pass on the new form, which the tests assert is the code
  under test, plus 6 pool/primitive cases.
- **Regression:** the full AB suite passes 2,213 tests. With the opt-in off,
  all 10 accepted stage images (S2 to S3i) regenerate byte-identically.

The first compile failed with `RxCMP_E_OPERAND_INVALIDDIMSPEC`: Logix refuses
an array reference inside a subscript, which the ST model accepts. Indices
now go through a scalar, and a static test rejects nested subscripts. Native
acceptance (equivalence, scan time, regressions on Echo) still needs a
session. Work and logs: `C:/work/fraktal-ab-s3j-20261024/r2_01/`.

**R1** is drafted for review in the
[V6.4 manifest contract review](AB_CANONICAL_MANIFEST_V64_CONTRACT_REVIEW_2026-10-24.md):
136 type-scoped annotations instead of 467 path rows, about 358 KB.

**Owner decisions, 2026-10-24** (chat reply “all of them approved”). R1 is
approved for offline implementation. The R2 native session (equivalence, scan
and regressions on Echo) is approved in principle. Its exact image still has
to be prepared, sealed and confirmed with the owner immediately before
download (AGENTS.md §3a). S3j D-1 to D-6 are approved, and this work is
committed.

**R1, offline, measured (2026-10-24).** The `canonical_type_manifest` opt-in
emits 137 type-scoped annotations and two exceptions. Its combined R1+R2 S3i
bench measures 1,653,432 used / 1,492,296 available / 3,145,728 total Blocks
(52% displayed), saving 360,600 beyond R2 and 1,110,080 from accepted S3i.
Both v38 compile/read-back/access gates pass. Existing image bytes and generic
snapshot values/types/views are preserved. The estimated 136 annotations missed
the second UDT owning the same logical SequenceSteps path. Native scan and
regressions still require a separately confirmed exact-image session.
Work: `C:/work/fraktal-ab-s3j-20261024/r1_01/`.

The combined image and guarded native apparatus are bound by the
[R1/R2 preparation](Evidence/AB_R1_R2_CANONICAL_PREPARATION_2026-10-24.md).
Current exact-image session confirmation is still required.
