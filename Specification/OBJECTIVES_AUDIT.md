# Fraktal — objectives audit & improvement plan

Audit of the whole project (Specification, PLC reference implementation, HMI,
repository hygiene) against the §1.1 objectives **O1–O10**. Each objective gets a
status, the evidence behind it, and any gaps; the gaps are then collected into a
single prioritized plan.

Status legend: ✅ met · 🟡 partial / at-risk · 🔴 gap. Dates are absolute.
Snapshot: **2026-07-26** (previous: 2026-07-22 — see §5 for what changed).

---

## 1. Scorecard

| # | Objective | Status | One-line verdict |
|---|---|---|---|
| O1 | Low development *and maintenance* effort | ✅ | Lifecycle/contract inherited once; base classes carry it. |
| O2 | Easy to learn | ✅ | PLCopen naming, ST/SFC/LD choice, lint-gated names. |
| O3 | Diagnosable by construction | ✅ | First-out walk + reason registry produce root cause automatically. |
| O4 | Reusable, recursive, **scalable** | 🟡 | Structural reuse strong; **runtime scalability** now real (read tiers, config manifest) but only on the native OPC UA path, not the gateway. |
| O5 | Flexible data & connectivity | ✅ | Provider seam + OPC UA / gateway transports proven end-to-end. |
| O6 | Simulatable | ✅ | SimRepository + simulated HAL; virtual commissioning works today. |
| O7 | Safe | ✅ | Safety consumed read-only; press demo keeps the safe filter as final authority. |
| O8 | Portable | ✅ | Core/binding split held; TC3 tags respected. |
| O9 | Good coding and engineering practice | ✅ | CI gate now exists (`.github/workflows/ci.yml`: PLC lint → Dart analyze/test → web build); mbedtls de-duplicated; hygiene rules fixed. |
| O10 | Industrial-grade robustness | 🟡 | Defensive coding + fail-closed present; honest-status docs refreshed; **PLC compile still not in CI** (needs a licensed TwinCAT runner). |

Overall: the **architecture** objectives (O1–O8) are in good shape and demonstrated
end-to-end on real hardware (TwinCAT 4024.75 + native ADS + Flutter HMI). O9 is
now closed: verification is continuous (CI gate on every push) and each dependency
has one representation. O10's single remaining gap is the **PLC compile in CI**,
which is blocked on infrastructure (a self-hosted Windows runner with licensed
TwinCAT XAE), not on code — the job is wired and gated behind a repo variable so
an absent runner cannot masquerade as a passing gate.

---

## 2. Findings by objective

### O4 — Reusable, recursive, scalable  🟡
- ✅ Structural: one module model composes device → EM → Unit → forest; press
  demo adds zero HMI code.
- ✅ Runtime (new): the direct OPC UA transport keeps the published/streamed
  surface proportional to what is consumed — config manifest (§3.10.2) obscures
  activation-static data (`OPC.UA.DA := '0'`, served on demand), and a
  fast/slow/on-demand **read tier** keeps the 2 Hz poll to always-visible data.
  Measured on the press demo: published nodes 33.7k → 17.6k; cyclic fast read
  ~6.9k → ~2.7k; mode-change latency ~1.1 s → ~50 ms.
- ✅ Runtime (ADS): the native path now reads **only requested symbols**, so the
  published-surface bound stops being the scaling limit on that transport.
- 🟡 Gap G1: the tiering + manifest live only in the **native** client. The Web
  **gateway** still publishes/relays everything cyclically. Parity is needed
  before a large forest is served to Web.
- 🟡 Gap G2: the fieldbus topology is a fixed `64 × 16` table declared as Core
  `VAR_GLOBAL CONSTANT` in `PL_Fraktal`. Largely **moot on the ADS path** (only
  requested symbols are read), so this is now a Web-gateway/OPC-UA concern that
  is subsumed by G1. The durable fix is to convert `PL_Fraktal` from a GVL to a
  TwinCAT **Parameter List** object, which lets a consuming project override the
  bound from the Library Manager without touching the library
  ([Object Parameter List](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/3470837515.html)).
  **Deliberately not done in this pass:** it changes the object *type* of a
  shipped library file, and it cannot be verified here (no XAE compile available
  in this environment) — landing an unverifiable schema change to the Core library
  would trade a measured scalability nit for an unmeasured build risk.
- ✅ Related win (measured 2026-07-26): HMI command latency was ~5 s and is now
  **48 ms median**. The cause was not the transport (ADS snapshot 26 ms, commit
  batch 14 ms) but **quadratic key scans in the snapshot mapper** —
  `_arrayElement`/`_indexedPrefix` each did a full 15k-key `startsWith` scan per
  enum value per module (~12M string comparisons/refresh, 1145 ms of UI-isolate
  CPU on a 500 ms timer). Fixed with a precomputed ancestor-path index:
  **1145 ms → 16.6 ms (69×)**. This is O4 *runtime* scalability on the client side,
  which the audit had not previously examined.

### O9 — Good coding and engineering practice  ✅
- ✅ One-source-of-truth idioms are real: reason registry (§8.8), inherited
  lifecycle (§2.2), single read-tier classifier, single config-manifest walk.
- ✅ Additive/versioned contract changes observed (E_HmiRequestKind append-only;
  ConnectionSettings schemaVersion; ConfigRev protocol degrades on old servers).
- ✅ Gap G3 **CLOSED** (2026-07-26): `.github/workflows/ci.yml` runs on every push
  and PR, in the Annex H order *lint → test → build*: `tools/plc_lint.py` over the
  TwinCAT sources; `flutter analyze` + `flutter test` for the HMI; `dart analyze`
  for `gateway/` and `packages/fraktal_opcua_client`; `flutter build web`. The
  Flutter version is pinned (3.44.6) so a green is reproducible. Every job was
  verified locally before wiring: 232 PLC files clean, three trees analyze clean,
  115 tests pass, web build succeeds.
  - The lint enforces what is decidable from source: object/filename agreement and
    §4.4 prefixes (N1/N2); **no defaulted METHOD inputs** (C1 — a 4026-only
    feature that breaks the 4024 target); no reserved word as an identifier (C2 —
    these desync the parser and cascade misleading errors); balanced `<Method>`
    tags (C3); unique GUIDs per file (C4). C1/C2 codify defects that have each
    cost real compile cycles.
  - It found a live regression on its first run: `FB_SequenceBase.M_Advance` had
    reacquired defaulted inputs (`OnJump1..3 : INT := -1`). Fixed — all 22 call
    sites already passed the arguments explicitly, so removing the defaults is
    behaviour-preserving.
- ✅ Gap G4 **CLOSED** (2026-07-22 pass): the root `.gitignore` no longer excludes
  authored content, and machine-local artifacts are untracked.
- ✅ Gap G5 **CLOSED** (2026-07-26): `mbedtls` now has one representation — the
  upstream 5.3 MB tarball, which the native OPC UA build extracts. The 51 MB /
  2,043-file extracted tree is build output, so it is ignored and was unstaged.
- ✅ Ignore-rule holes found while closing G5 and fixed, since they would have
  committed machine-local state on the next `git add`: per-package `.dart_tool/`
  (only the HMI root was matched), Flutter's `windows/flutter/ephemeral/`
  (**absolute paths + pub-cache symlinks** — 51 entries were already staged, incl.
  4 symlinks that would break on any other machine), and compiled `*.dll`/`*.pdb`.

### O10 — Industrial-grade robustness  🟡
- ✅ Defensive coding (§5.6): validated commands, bounded rings, fail-closed
  `ELSE` branches; the HMI never queues writes across reconnect; the OPC UA
  client recovers from online-change session loss deliberately.
- ✅ Determinism: fixed-size published structures; no per-scan allocation.
- ✅ Gap G6 **CLOSED**: the PLC/Core READMEs now state what is proven (compiles
  under TwinCAT 3.1.4024.75, deployed and exercised on a runtime) versus pending.
  One stale line remained in `PLC/IMPLEMENTATION_NOTES.md` ("not yet compiled
  against a pinned TwinCAT") and is corrected in this pass.
- 🟡 Gap G7 **PARTIALLY CLOSED**: the TwinCAT *source* rules now run on every
  commit (see G3), which catches the naming/4024/contract drift class. A real
  **compile + TcUnit run** still does not: it needs a self-hosted Windows runner
  with licensed TwinCAT XAE. The `plc-compile` job exists in the workflow but is
  gated behind `vars.HAS_TWINCAT_RUNNER` so an unavailable runner cannot look like
  a passing gate — a deliberate honest-status choice (O10). **Remaining work is
  infrastructure provisioning, not code.**
- ✅ Gap G8 **CLOSED by the ADS migration** (plan item 3, now shipped): the native
  transport is ADS, so TF6100 is out of the native path entirely and its
  `0x00000710` handle-pool bursts cannot occur there. A distinct ADS handle-pool
  exhaustion was found and fixed separately (batched `SYM_HNDBYNAME`, chunked
  handle acquisition under a time budget, bulk release via `SUMUP_WRITE`).

### O9/O10 — per-type test depth (§5.7)  🟡  *newly assessed 2026-07-26*
§1.5 makes this a **shall**: "Each reusable module **type shall** ship an automated
test suite (§5.7) … the suite **shall** be green before the type is released or
changed", and §5.7 sets the bar as the **T1–T10 checklist, applicable rows per
tier** — not the mere existence of a suite. Previous passes checked that suites
exist; they did not check the rows against the checklist. Result of doing so:

- ✅ **67 TcUnit tests across 24 suites**, with a real `TcUnit` library reference
  and a working `PRG_TcUnitRunner` (`TcUnit.RUN();`) — the harness is sound.
- ✅ Annex H's caveat is **stale and should be corrected**: it says T4/T5 are
  "left as the reader's exercise", but `FB_CylinderCM_Tests` covers
  **T1–T5** explicitly (`T5_recipe_schema_mismatch_faults` etc.). The CM tier is
  the strongest evidence in the repo.
- ⚠️ **Correction to the first reading of this gap.** §5.7 is explicit that
  **T1/T4 and the T2/T6/T7/T10 *mechanisms* are proven once in the base suite**
  and that types "**shall not** re-test inherited rows" — verification is paid at
  the level that owns the behaviour (O1). `FB_Base_Tests` does exactly that
  (`T1_Handshake_and_execute_drop_reset`, `T2_First_out_reason_and_source_path`,
  `T4_Abort_reports_and_no_auto_resume`, `T6_Rollup_adopts_child_first_out`), so
  the shortfall was **narrower than "eight rows missing"**: what a type owes is
  the applicable rows re-proven with **its own** reasons, paths, modes and actions.
- ✅ Gap **G9 CLOSED** (2026-07-26) for the two tier representatives:
  - `FB_ClampEM_Tests` 1 → **3 tests**: added **T3** (a dropped child permissive
    withholds the output and the EM surfaces `INTERLOCK_DROPPED` naming
    `ClampIntlk.CylA` — the composite tier's own path/reason pairing) and **T5**
    (stored `ST_ClampParCfg.SchemaVersion` = 2 vs expected 1 →
    `RECIPE_INVALID`, and the actuator must not mis-run).
  - `FB_ClampStationUnit_Tests` 1 → **4 tests**: added **T8** (the type's mode set
    is the baseline AUTO+MANUAL, so `SetMode(CALIBRATION)` returns FALSE, leaves
    `ModeActive` unchanged and raises no error — a rejection is not a fault),
    **T10** (Start accepts **iff** `ReleaseReportStart` says `Released`, asserted
    in both directions so the report cannot drift from the gate), and **T6+T9**
    (the root adopts the deepest child's first-out verbatim across *two* tiers —
    `Stall.Station.Clamp.CylB` — which is what the Unit adds over the EM's single
    hop, and must not name itself).
- 🟡 Residual: `FB_PowerGroupCM_Tests`, `FB_TwoHandStartCM_Tests` and
  `FB_MultiRoot_Tests` remain single-test. They are CM/no-tier types whose
  inherited rows are covered by the base suite, so this is thin-but-conformant
  rather than a blocking gap; deepen opportunistically.
- ⏳ **Unverified:** these tests are written against the real APIs (every
  identifier and member visibility checked statically) but **have not been
  compiled or run** — no XAE in this environment. They are a conformance *claim*
  only once green in a run; that is item **B**.

### O1–O3, O5–O8  ✅
No new gaps. These are demonstrated by the shipped base classes, the two
worked-example applications, the generic HMI rendering a real press demo over
OPC UA, and the annex set. Keep them green via the CI gate once it exists (G3).

---

## 3. Improvement plan (prioritized)

Ordered by value ÷ effort. Each item names the objective it closes and a concrete
first step.

| P | Item | Closes | Status / next step |
|---|---|---|---|
| ~~1~~ ✅ | **CI gate** — `.github/workflows/ci.yml`: PLC lint → HMI analyze+test → Dart package analyze → web build. Flutter pinned to 3.44.6. | O9 G3 | **DONE** 2026-07-26. Every job verified locally first. Found and fixed a live 4024 regression on its first run. |
| ~~2~~ ✅ | **Refresh honest-status docs** — READMEs, plus the last stale line in `PLC/IMPLEMENTATION_NOTES.md`. | O10 G6 | **DONE**. |
| ~~3~~ ✅ | **Migrate the native PLC transport to ADS** (OPC UA stays the multi-brand option) — see [`ADS_TRANSPORT_MIGRATION.md`](ADS_TRANSPORT_MIGRATION.md). | O4/O10 G8, O5 | **DONE**. TF6100 is out of the native path; command latency 48 ms median (target was <100 ms). |
| ~~6~~ ✅ | **De-duplicate mbedtls vendoring**. | O9 G5 | **DONE** — tarball is the single representation; extracted tree ignored + unstaged. |
| **A** | **Commit the untracked HMI source.** `FraktalCore/HMI/lib/` and siblings are present on disk but have **0 tracked files** — the app source is outside version control. The ignore rules are now correct, so this is a review-and-stage step. | O9 G4 | **HIGHEST RISK REMAINING.** `git status` shows ~110 untracked paths; stage `lib/`, `gateway/`, `packages/`, `native/`, `test/`, `tool/`, then confirm no `.dart_tool`/`ephemeral`/`*.dll`/mbedtls tree is included. Left to the user: committing is theirs to authorize. |
| **B** | **PLC compile + TcUnit in CI.** Job is written and gated behind `vars.HAS_TWINCAT_RUNNER`. | O10 G7 | Provision a self-hosted Windows runner with licensed TwinCAT XAE + TcUnit; fill in the automation-interface build; publish JUnit XML (Annex H). Infrastructure, not code. |
| ~~B2~~ ✅ | **EM/Unit tier test rows** (§5.7) — EM +T3/T5, Unit +T8/T10/T6+T9, written against the real APIs and auto-run by the existing `PRG_TcUnitRunner`. | O9/O10 G9 | **DONE** 2026-07-26 (67 → 72 tests). Needs one green run to become a conformance claim — folded into item **B**. |
| **C** | **Gateway read-tier / manifest parity** so Web scales like native. Now also subsumes G2. | O4 G1, G2 | Teach the gateway the config-manifest + tier protocol, or document Web as full-publish and cap forest size. |
| **D** | **Per-deployment fieldbus topology sizing** — convert `PL_Fraktal` to a TwinCAT Parameter List so a project can override `MAX_BUS_NODES`/`MAX_NODE_CHANNELS`. | O4 G2 | Low priority: moot on ADS, and it changes a shipped library object's type, so it needs an XAE compile to land safely. |

Items 1, 2, 3 and 6 are complete. **Item A is now the highest-risk open item** — not
because it is hard, but because unversioned source is the one gap that can lose
work outright. Items B–D are infrastructure and Web-path scalability.

---

## 4. What the 2026-07-22 pass changed
- Added objectives **O9** (good coding & engineering practice) and **O10** (industrial-grade
  robustness) to §1.1, with accurate cross-references; strengthened O1
  (maintenance effort) and O4 (runtime scalability) in place.
- Centralized `.gitignore` at the root; corrected the inverted rules; untracked
  ~1,859 machine-local artifacts; the HMI source the old rules hid is now
  visible to git.
- Recorded this audit + plan (this file) as the single reference for the
  remaining work (G1–G8).

---

## 5. What the 2026-07-26 pass changed

Closed **G3, G5, G6, G8** and partially closed **G7**; O9 moves 🟡 → ✅.

- **CI gate added** (`.github/workflows/ci.yml`) — G3. Runs on every push/PR in the
  Annex H order lint → test → build. Toolchain pinned. All five jobs were run
  locally before being wired, so the gate reflects a real green, not an intention.
- **PLC lint written** (`tools/plc_lint.py`, 232 files clean) — the §1.5 **shall**
  now has an implementation. Encodes five rule families; C1 (no defaulted METHOD
  inputs) and C2 (no reserved-word identifiers) exist because both have already
  cost real compile cycles on the 4024 target.
- **Live regression caught and fixed** — `FB_SequenceBase.M_Advance` had regained
  defaulted inputs, which breaks every call site on 4024. Verified all 22 call
  sites pass the arguments explicitly, then removed the defaults.
- **mbedtls de-duplicated** — G5. One representation (the upstream tarball).
- **Ignore-rule holes closed** — per-package `.dart_tool/`, Flutter
  `windows/flutter/ephemeral/` (absolute paths + 4 pub-cache symlinks that were
  already staged and would break on any other machine), compiled `*.dll`/`*.pdb`.
  Staging set under `HMI/` went from 2,220 paths to 172 authored files.
- **Honest status corrected** — G6: the last stale "not yet compiled" claim.
- **Client-side O4 scalability** — HMI command latency 5 s → **48 ms median** by
  removing quadratic key scans from the snapshot mapper (1145 ms → 16.6 ms of
  UI-isolate CPU per refresh). Measured against a live PLC, not inferred.
- **Fieldbus state now read from hardware** — `FB_EcBusHealth` decodes real
  EtherCAT AL states and auto-detects the master's AmsNetId
  (`FB_GetLocalAmsNetId` + the `.2.1` master convention), so a deployment needs
  **no** hand-typed fieldbus address and no XAE checkbox — the O4 "detect the most
  from hardware with the least manual wiring" goal. Publishes `ReadOk`,
  `LastErrorId`, `SlavesReported`, `NetIdMissing` so a failure is visible rather
  than silently showing every node faulted.

### Deliberately not done
- **G2 / item D** (`PL_Fraktal` → Parameter List): changes the object type of a
  shipped library file and cannot be compile-verified in this environment. Moot on
  the ADS path. Landing it unverified would trade a measured nit for build risk.
- **Item A** (committing the untracked HMI source): the ignore rules are fixed and
  the staging set is clean, but the commit itself is the user's call.
