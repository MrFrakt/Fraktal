# Fraktal/AB canonical publication — implementation plan

Non-normative plan, 2026-10-20, restructured 2026-10-27. It executes the
decisions in [the design note](AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md)
(D1–D9). Where the two differ, the design note wins and this plan is corrected.
Part III and frozen contracts V1 stay authoritative for the shipping
implementation until S6 activates V2.

This revision states the remaining work (S4b–S7) as work packages: the files,
the change, the tests, the offline gates and the native session for each. It
also settles in advance every choice that can be settled now (§6.2), so that
implementation needs no further design decisions except the open owner
decisions in §6.3. The dated progress narrative to 2026-10-27 is preserved
verbatim in the [status log](AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md).
The sealed records under `Evidence/` are the authority for every result.

## 1. Goal and definition of done

AB reaches the HMI the way TC3 and TIA do. The PLC publishes the canonical Core
module tree. One generic session client discovers it through the controller's
own Symbol and Template objects plus the manifest, with no station declaration
at runtime.

The work is done when all six hold:

1. **Value equivalence.** A generic reader recovers every canonical path the
   Python projection serves, with identical values and types, for genealogy and
   for the press declaration in all three AUTO renditions. The frozen genealogy
   capture (4,437 legacy paths) stays immutable. No general coercion, tolerance
   or ignored path is permitted. The only differences are these finite,
   owner-approved corrections:

   | Correction | Approved | Record |
   |---|---|---|
   | Five D2 array-bound corrections | 2026-10-20 | design note, D2 |
   | 110 Core types, bounded page windows, 12 missing Core fields, PLC-owned revision and timestamps, validated provider responses | 2026-10-22 | [S3f review](AB_CANONICAL_PUBLICATION_S3F_CONTRACT_REVIEW_2026-10-22.md) |
   | 200 numeric corrections, including Core Float32 arithmetic and UInt32 bucket wrap | 2026-10-23 | [S3g review](AB_CANONICAL_PUBLICATION_S3G_CONTRACT_REVIEW_2026-10-23.md) |
   | 224 dependent values: 64 OEE validity flags, 160 profiler rows | 2026-10-23 | [S3g dependent values](AB_CANONICAL_PUBLICATION_S3G_DEPENDENT_VALUES_REVIEW_2026-10-23.md) |
   | 36 type corrections, including the unset Part timestamp from empty string to zero | 2026-10-23 | [S3h review](AB_CANONICAL_PUBLICATION_S3H_CONTRACT_REVIEW_2026-10-23.md) |
   | 122 path spellings, 13 type corrections, command/status/history schema | 2026-10-24 | [remaining-S3 review](AB_CANONICAL_PUBLICATION_REMAINING_S3_CONTRACT_REVIEW_2026-10-24.md) |
   | Read-only configuration view (V6.8), with its own independent oracle | 2026-10-25 | [S4b review](AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md) |

2. **Desktop.** The desktop HMI connects with
   `cip://<controller>?slot=<n>&serial=<hex>` through the generic
   `CipSessionClient` in `fraktal_opcua_client` and renders every surface LIVE.
   It is read-only unless the endpoint is a commissioned CIP Security session
   (D9).
3. **Web.** The Dart gateway serves Web clients from the same client
   (`--plc-endpoint cip://…`), with Core §14 writes over `wss://`.
4. **Retirement.** The Python projection and the Python gateway are deleted.
   The Dart spike `HMI/lib/data/cip/` is already deleted in the working tree.
   §3.8b persistence, configuration sets and the host-event sink have
   declaration-free owners. The legacy generated contexts are gone, and the
   canonical structures are the working storage.
5. **Documents.** Part III, frozen contracts V2 (active), `OPCUA_TRANSPORT.md`,
   `AGENTS.md`, the AB README and the new-station guide describe the final
   behaviour. Every gate is green.
6. **Acceptance.** Echo acceptance passes per stage. Physical and CIP Security
   acceptance pass on a v37+ capable controller (S7).

## 2. Status on 2026-10-27

| Stage | Status | Accepted record (local Echo L81E v38) | Still open |
|---|---|---|---|
| S0 type rules, V2 draft | Done | [types](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md), [supplementary](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md) | — |
| S1 Python reference reader | Done | [S1](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md) | — |
| S2 module tree | Done | [S2](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md) | — |
| S3a–S3k surfaces | Done at genealogy scope | see the list below | — |
| S3 exit: press in ST/SFC/LD, path census | Done | [press S3 exit](Evidence/AB_PRESS_S3_EXIT_RUNTIME_2026-10-25.md), [census](AB_CANONICAL_PUBLICATION_S3_PATH_CENSUS_2026-10-25.json) | Physical-module identity and real I/O move to S7 |
| S4a coherence bindings | Done | [S4a](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md) | — |
| S4b generic Dart client and desktop | **Open** | Best functional result: [reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md). Latest: [body-packet attempt](Evidence/AB_S4B_MSP_ATTEMPT_2026-10-27.md) | Desktop, configuration, idle, generic and final scan, together in one accepted session (§5.1) |
| S5 gateway, Web, installer | Not started | — | §5.2 |
| S6 retirement, collapse, persistence, events | Not started; census taken | [census](Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Continuation/legacy_consumer_inventory_01.json) | §5.3 |
| S7 physical controller, CIP Security | Not started | — | §5.4 |

S3 surface records: [S3a](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md),
[S3b](Evidence/AB_S3B_CANONICAL_RUNTIME_2026-10-21.md),
[S3c](Evidence/AB_S3C_CANONICAL_RUNTIME_2026-10-22.md),
[S3d](Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md),
[S3e](Evidence/AB_S3E_CANONICAL_RUNTIME_2026-10-22.md),
[S3f](Evidence/AB_S3F_CANONICAL_REVISION_RUNTIME_2026-10-23.md),
[S3g](Evidence/AB_S3G_CANONICAL_RUNTIME_2026-10-23.md),
[S3h](Evidence/AB_S3H_CANONICAL_OBSERVATION_FRAME_RUNTIME_2026-10-24.md),
[S3i](Evidence/AB_S3I_CANONICAL_LIFETIME_RUNTIME_2026-10-24.md),
[R1/R2](Evidence/AB_R1_R2_CANONICAL_RUNTIME_2026-10-24.md),
[S3j](Evidence/AB_S3J_CANONICAL_RUNTIME_2026-10-25.md) and
[S3k](Evidence/AB_S3K_CANONICAL_RUNTIME_2026-10-25.md).

The last commit before the decision batch was `f194c3a53` (2026-10-24). O1 was
decided on 2026-10-27: everything since, including about 28,000 evidence files,
was committed and pushed to `main` that day (see the
[status log](AB_CANONICAL_PUBLICATION_STATUS_LOG_2026-10-27.md)). V2 and the Part
III amendment are owner-approved targets, not active.

### 2.1 Baselines the remaining work starts from

| Item | Value |
|---|---|
| Bench | Echo `601FC87B`, 1756-L81E v38.011, 127.0.0.1 slot 0, Remote keyswitch. The same Windows host (6 logical CPUs, 16 GB) also runs the HMI, gateway, Python and Dart tools |
| Rollback baseline | Genealogy pin `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`, five original host documents, 31 baseline cases. Baseline TASK median 99 µs, maximum 1,166 µs, zero overlaps |
| S4b candidate image | ACD `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`, source `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`, manifest hash `3B765353B71891ED750D331CE11B5DDCE7D1663A06837C4C1EB0FC90FA3346AA`. Capacity 2,066,212 used / 1,079,516 available / 3,145,728 Blocks (65%) |
| S4b write scope | The inherited 41 candidate cases (31 rows, 2 Access, 8 configuration) with exact restoration; 31 baseline cases after rollback |
| S4b candidate scan | TASK maximum 9,002 µs, zero overlaps: 998 µs margin on the 10 ms period |
| Press candidate | ACD `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F`, 53% Capacity, MaxScan 7,246 µs |
| Published surface | Genealogy S4b: 5,940 discovered paths, 4,799–5,407 occupied values, 237–239 guarded groups per full walk, seven modules, three bus nodes. Press: 4,058 paths |
| Toolchain | Flutter 3.47.5 / Dart 3.13.4 at `C:/work/fraktal-toolchains/flutter-3.47.5`, always with `--enforce-lockfile`; Studio v38 two-target build and read-back; the automatic Capacity collector |
| Tests | 685 HMI passed / 12 skipped; 2,339 AB; 74 root; spec, contracts, strict consistency and whitespace clean |
| Bound inputs | 373 PLC/gate source bindings; 1,081 session inputs in the latest run |

### 2.2 Measured facts that constrain the remaining work

Bench:

- The Echo service does not start at Windows boot. The owner starts it from an
  elevated shell: `Start-Service "FactoryTalk Logix Echo Service"`. The
  preflight refuses to download while an HMI session is logged in; ask the owner
  to log out rather than weaken it ([redownload](Evidence/AB_ECHO_REDOWNLOAD_2026-10-19.md)).
- After a forced shutdown, Echo once failed to start with a libComms
  `+0x50C2A4` NULL dereference
  ([diagnostic](Evidence/AB_S3H_CANONICAL_DIAGNOSTIC_RUNTIME_2026-10-24.md)).
  Shut Echo down in order. Every runner refuses to change the controller while a
  dump file exists.

Transport:

- A 4,000- or 4,002-byte connection connects; 8,000, 16,000 and 60,000 are
  refused. Mailbox commands set the shared connection to 500 bytes, so
  observers use their own 4,000-byte connections.
- A Multiple Service Packet is not a whole-scan atomic transaction: 19 of 20
  packets saw equal counters ([host timing](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md)).
  Every row keeps its own equal-even counter proof and a window under 10 ms.
- Per-request latency on this host, median / p95 / maximum: Dart CLI 0.9 / 1.7 /
  4.0 ms; Flutter without widgets 1.1 / 2.8 / 13.1 ms; Flutter while rendering a
  UI 1.3 / 7.0 / 16.3 ms. Rendering on the same host pushes request tails past
  the 10 ms row window.
- The freshness profile is fixed in `CipReadPlan.freshnessBudget`: poll 250 ms;
  fast Good/expiry 1 / 3 s; slow period/Good/expiry 5 / 7.5 / 15 s. The desktop
  row budget is 20 attempts inside one second.
- The HMI computes effective age as:
  - the source age of the oldest fast row;
  - plus transit (the RPC time minus the server's processing bracket);
  - plus local processing.

  The code is `HMI/lib/data/opcua_freshness.dart` and
  `HMI/lib/data/opcua_repository.dart:286-337`. Worker queue time is inside the
  bracket and is not charged.

Logix generation rules. These bind the S6 generator work:

- A member named after a type (`Time`, `DT`, …) fails with
  `RxSTX_E_UNEXPECTED_TOKEN`.
- Time literals are normalised: `T#1s500ms`, never `T#1500ms`, and never a
  `TIME#` prefix.
- ST has no `MOV`.
- An array reference inside a subscript fails with
  `RxCMP_E_OPERAND_INVALIDDIMSPEC`; index through a scalar.
- Long operands can exceed the compiler's operand-length limit (S3k); keep
  generated operands short.
- An untyped decimal rounds to REAL before an LREAL assignment. Use the `L`
  suffix or typed initial data (D5).
- A Read Only parent blocks a writable child, so the ancestors of `HmiRequest`
  are Read/Write. A None member breaks whole-structure reads.
- Template metadata does not distinguish member RO/RW/None, so the manifest
  publishes effective access.

### 2.3 S4b attempt ledger

Each attempt was separately authorized. Each ended with genealogy restored and
31/31 baseline cases, except the preflight attempt, which stopped before
download with genealogy untouched. The 2026-10-26 runs used ACD `7D75E86E…DEF056BF`; the
2026-10-27 runs used `30315E6D…3049A5`, which differs only in deferring cold
first-scan view formatting.

| Date | Record | Reached | Stopped at |
|---|---|---|---|
| 10-26 | [canonical attempt](Evidence/AB_S4B_CANONICAL_ATTEMPT_2026-10-26.md) | Download, audits | `Unterminated Template name` before readiness; 0/41 cases |
| 10-26 | [Template retry](Evidence/AB_S4B_TEMPLATE_RETRY_ATTEMPT_2026-10-26.md) | Template and manifest discovery | First root sample refused |
| 10-26 | [root diagnostic](Evidence/AB_S4B_ROOT_DIAGNOSTIC_ATTEMPT_2026-10-26.md) | Readiness | Root age 2,065.752 ms after 2,495.609 ms of processing |
| 10-26 | [lookup retry](Evidence/AB_S4B_LOOKUP_RETRY_ATTEMPT_2026-10-26.md) | 41/41, 140 snapshots | Root Status Uncertain (`coherence-unavailable`) |
| 10-26 | [coherence retry](Evidence/AB_S4B_COHERENCE_RETRY_ATTEMPT_2026-10-26.md) | 41/41, 587 rows | Bad value: 10 s slow expiry against the declared 15 s |
| 10-26 | [freshness retry](Evidence/AB_S4B_FRESHNESS_RETRY_ATTEMPT_2026-10-26.md) | 41/41, 884 samples | Root Status retries exhausted (three attempts in 6,237 µs) |
| 10-26 | [reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md) | 41/41, 87 replays, 902 samples, configuration (1,100 values), idle and generic (5,407) | TASK maximum 10,033 µs with one startup overlap |
| 10-26 | [desktop/scan preflight](Evidence/AB_S4B_DESKTOP_SCAN_PREFLIGHT_ATTEMPT_2026-10-26.md) | Backup | Ready-file race, before download |
| 10-26 | [desktop/scan run](Evidence/AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26.md) | All reader gates | Desktop helper false positive (zero modules); startup overlap |
| 10-27 | [cold desktop](Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27.md) | 41 cases | Observer incomplete after 68 samples; later stages skipped |
| 10-27 | [Status order](Evidence/AB_S4B_STATUS_ORDER_ATTEMPT_2026-10-27.md) | 41/41, 910 samples | Desktop startup null check |
| 10-27 | [startup diagnostic](Evidence/AB_S4B_STARTUP_DIAGNOSTIC_ATTEMPT_2026-10-27.md) | 41/41, 906 samples | Desktop startup sample late or expired |
| 10-27 | [parallel reader](Evidence/AB_S4B_PARALLEL_READER_ATTEMPT_2026-10-27.md) | 25/41 | Legacy Part reader: snapshot changed during every bounded read |
| 10-27 | [Part-read diagnostic](Evidence/AB_S4B_PART_READ_DIAGNOSTIC_ATTEMPT_2026-10-27.md) | 41/41, 1,991 samples | Desktop STALE after overview |
| 10-27 | [desktop timing](Evidence/AB_S4B_DESKTOP_TIMING_ATTEMPT_2026-10-27.md) | 41/41, 2,035 samples | Desktop STALE after overview |
| 10-27 | [tier/queue](Evidence/AB_S4B_TIER_QUEUE_ATTEMPT_2026-10-27.md) | 49 samples | Login busy state not observed |
| 10-27 | [busy witness](Evidence/AB_S4B_BUSY_WITNESS_ATTEMPT_2026-10-27.md) | 41/41, 2,805 samples | Desktop STALE after overview, 1,310.560 ms |
| 10-27 | [row refill](Evidence/AB_S4B_REFILL_ATTEMPT_2026-10-27.md) | 41/41, 3,144 samples | Desktop STALE after overview, 1,428.145 ms |
| 10-27 | [body packets](Evidence/AB_S4B_MSP_ATTEMPT_2026-10-27.md) | 41/41, 87 replays, 2,851 samples, median age 209.959 ms | Desktop STALE after overview, 1,051.723 ms |

### 2.3 Offline continuation, 2026-10-28 — WP4b.5 gate remains open

The [rehearsal record](Evidence/AB_WP4B5_REHEARSAL_2026-10-28.md) implements the loopback peer and tests wire
discovery against both golden and hash-pinned sealed bytes. Seven peer tests
pass. The peer serves symbolic/fragmented reads and read-only MSPs, refuses
the Echo port, echoes the transport identity/context, preserves native type
codes and handles, and shuts down explicitly. Synthetic counters retain the
10 ms/equal-even model. Latency is piecewise interpolation of the recorded
minimum/median/p95/maximum, not an invented empirical sample set.

The profile target has an explicit rehearsal flag and separate native/result
labels. Its in-memory acceptance panel is configured for public read visibility
through the existing content API; live mode remains logged out and read-only,
without changing PLC policy, data or session identity. Every original view,
refusal and freshness condition stays required. Trace-only successful mapped
ages and worker operation boundaries supplement the existing phase traces.

**The prerequisite does not pass:** the final-source profile model run takes
3,397.686 ms awaiting its first snapshot and refuses at effective age
1,001.601 ms; debug takes 4,135.311 ms and refuses at 1,027.650 ms. Neither
accepts a view. UI reply waits are 1.076/0.679 ms; this does not isolate a host
or controller cause. These are synthetic-server results, never native E7.

A separately labelled zero-injected-delay diagnostic maps seven snapshots
(maximum age 261.606 ms) and captures Overview plus three root tabs, then
becomes STALE after Statistics demand. That demand promotes 2,280 leaves into
slow snapshots (excluded count 3,660 → 1,380); a snapshot starts but does not
finish before the fast window expires. The secondary finder exception is kept;
later test guards diagnose loss of LIVE before further tab lookups. This run
is apparatus-only and cannot satisfy the latency-model gate.

All launches verify the genealogy preflight before and after, make no controller
changes and stop only their local peer. The three-consecutive-profile/700 ms
prerequisite remains **0 passing runs**. No new native session is prepared.
The O7 fallback is not triggered: no native E7/host-CPU threshold is claimed.

Current unit gates: **697 HMI passed /12 skipped**, analyzer, locked
dependencies and Windows profile build. All 373 PLC/gate bindings remain
unchanged, transferring 2,339 AB tests, both v38 builds and 65% Capacity.
Root spec/contracts/strict consistency/74 tests/whitespace are checked after
this status edit. No stage exit or commit/push is claimed.

Next: measure requested versus realized rehearsal delay at the socket boundary
and implement/test bounded slow-detail scheduling that preserves cyclic
freshness, row proofs, source ages and every demanded value/type. Address the
initial fast acquisition cost as its own constraint. Then require all three
profile rehearsals at ≤700 ms before WP4b.6/S4b-Q. S5/S6 remain; S7 physical
gates stay deferred/excluded as O2 states. The owner decisions in §6.3 stand.

## 3. Invariants for every stage

- **One source.** The declaration is the only source, and the generator emits
  the L5X. Hand-authored L5X is forbidden. No station knowledge enters a client.
- **Canonical paths.** Paths, leaf names, enum ordinals and logical types equal
  TC3's (`HMI_CONTRACT.md`, `HMI/lib/domain/types.dart`). Array indices follow
  each array's Core-declared bound (D2).
- **Published versus private.** Published members are External Access *Read
  Only*. Only `HmiRequest` and the typed command endpoints are *Read/Write*.
  Private storage is *None*. The R6 allow-list audit runs on every generated
  image.
- **Native types per D3–D7**, and the generation rules in §2.2.
- **Language parity.** ST/SFC/LD parity holds; the rendition gate and the 31
  regressions stay green.
- **No gate is passed by relaxing it.** No freshness limit, proof window,
  attempt budget, tier rule, coherence rule, access policy or read-only rule
  changes to make a gate pass. No feature is cut and no validation weakened to
  make an image fit.
- **Budget.** Memory and scan time are measured per image. Memory uses the
  automatic Studio Capacity collector on a hash-checked review copy. Scan time
  uses native `TASK` `MaxScanTime` and the overlap count. The
  [forecast](AB_CAPACITY_FORECAST_METHOD_2026-10-21.md) and the
  [capacity plan](AB_CAPACITY_BUDGET_AND_REDUCTION_PLAN_2026-10-24.md) are
  advisory.
- **Controller changes** follow §4. Evidence is append-only under
  `Specification/AllenBradley/Evidence/`, failed runs included.

## 4. Native session protocol

Every controller-changing session follows these five steps. The stage sections
list only what differs.

1. **Prepare offline.**
   - Record exact ACD and source hashes.
   - Both v38 targets build and read back; the effective access audit passes;
     automatic Capacity is recorded.
   - Every offline gate for the stage is green.
   - Create a fresh workspace `C:/work/fraktal-ab-<stage>-<yyyymmdd>/session_NN/`.
     Its runner verifies every bound input's hash before the first controller
     call.
   - The approval template is set to false, and a sealed preparation record is
     written.
2. **Ask once.** The owner approves one sentence naming the session and its
   image, for example "Approve guarded S4b profile-desktop session". The
   approval covers that image, that write scope and its rollback, once.
   **Echo standing authorization (2026-10-27).** The owner states the Echo
   instance exists exclusively for this work, so a session whose guard
   confirms identity `601FC87B` at 127.0.0.1 slot 0 needs no per-session
   approval. Every other rule of this section is unchanged — guards, dump
   check, exact-target check, rollback, sealing — and any controller other
   than Echo still needs its own approval.
3. **Run.**
   - Guard: service, listener, identity `601FC87B`, v38.011, slot 0, Remote, not
     faulted, no HMI session logged in.
   - Dump check, MANUAL normalization, preflight, backup upload.
   - Start the read-only TASK monitor (100 ms).
   - Program/download/Run; SDK log audits; read-back; access audit; candidate
     guard.
   - Then the stage gates. A writer stage stops the session at its first
     failure. Read-only stages after the writer stages still run and record
     (P5). Then the session rolls back.
4. **Roll back.**
   - Guarded MANUAL; download a hash-checked copy of the genealogy pin (the
     original file is never opened); SDK and access audits.
   - Restore the five original host documents; run the 31/31 baseline cases;
     restore MANUAL, idle and logged out.
   - Final checks, preflight verify-only, baseline timing.
5. **Seal.**
   - Whitelisted artifacts only: no ACD/BAK, binaries or credentials.
   - Record payload hashes and never overwrite. Failed runs are sealed exactly
     like passing ones.
   - Update the stage's §2 row and add one §2.3-style ledger line. Nothing else
     in this plan changes for a session.

Never in any session: fault clears, TASK-counter clears, clock changes, power or
vendor-state operations, Echo hard kills, or archiving a credential or Secret.

## 5. Remaining work

### 5.1 S4b — close the desktop gate

**What the evidence establishes.**

1. The reader is functionally complete. The [reader run](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md)
   passed all of these on 5,407 paths:
   - 41/41 cases and 87/87 replays;
   - four configuration pages (1,100 values);
   - idle equivalence and generic acquisition.

   The desktop gate has never passed. The final scan gate passed only in runs
   that ended before the desktop stage could run.
2. Every desktop failure since the Part-read diagnostic is the same. The first
   snapshot is LIVE; the second is refused at `after-overview`. The last three
   sessions' refused snapshots:

   | Session | Source age | Acquisition | Transit | Effective age |
   |---|---:|---:|---:|---:|
   | busy witness | 995.5 ms | 1,012.0 ms | 311.6 ms | 1,310.6 ms |
   | row refill | 996.6 ms | 1,125.7 ms | 428.6 ms | 1,428.1 ms |
   | body packets | 738.0 ms | 745.6 ms | 309.7 ms | 1,051.7 ms |

   The limit is 1,000 ms.
3. The refused walk is no larger than the observer's. It read 237 groups over
   5,940 discovered paths. The observer's slowest walks read the same 237–239
   groups in at most 364.5 ms, and its median acquisition is 209.5 ms. The
   refused walk's slowest groups needed 4–6 coherence attempts of 35–58 ms each.
   The first desktop walk's slowest groups needed 2–3 attempts of about 19 ms.
4. The desktop runs under `flutter test`, on the same six-CPU host as the Echo
   emulator:
   - the debug-mode (JIT) `flutter_tester` engine with software rendering;
   - `LiveTestWidgetsFlutterBindingFramePolicy.fullyLive`, at 1600×1000.

   Rendering on this host raises request tails from 4 ms to 16 ms, above the
   10 ms row window (§2.2). Debug-mode timing is not the shipped product's
   timing; Flutter's guidance is to measure performance in profile mode.
5. Two client inefficiencies add cost:
   - On every snapshot, `CipSessionEngine.snapshot` re-expands and sends the full
     discovered path vector (`cip_session_client.dart:274-278`; 10–19 ms on the
     desktop). `OPCUA_TRANSPORT.md:385-387` and the repository
     (`opcua_repository.dart:300-307`) expect it once per discovery, and the Web
     API client sends it only when it changes (`webapi_session_client.dart:364`).
   - On a slow-due walk (the first walk, then every 5 s), `CipReadPlan.acquire`
     interleaves slow rows with fast rows in schema order
     (`cip_read_plan.dart:706`). Fast rows read early keep ageing while the slow
     reads that follow complete.

So the desktop gate measures debug-mode rendering contention on a shared host
as much as it measures the client. The packages below:

- remove the client's own excess;
- make acceptance run the shipped build;
- let one session show where the remaining time goes.

None changes a limit, budget, rule or policy (§3).

**WP4b.1 — Send the path vector once per discovery.**

- `HMI/packages/fraktal_opcua_client/lib/src/cip_session_client.dart`:
  - `CipSessionEngine` gains `bool _pathsSent = false`.
  - `snapshot()` calls `plan.publication.discoverPaths()` and fills `'paths'`
    only while `_pathsSent` is false, then sets it true. Afterwards it sends
    `'paths': const <String>[]`.
  - `discover()` builds a new engine, so every reconnect sends the vector again.
  - The trace records `pathExpansionUs` and `pathCount` only on the sending
    snapshot.
- Tests:
  - the first snapshot carries exactly `discoverPaths()` and the second
    carries `[]`;
  - after a new `connect` the vector is sent again;
  - the repository keeps the last non-empty vector
    (`opcua_repository.dart:304-307`), and its tier classification is unchanged.

**WP4b.2 — Read slow-due rows before fast rows.**

- `cip_read_plan.dart`, `acquire()`, when `paths == null && due`, walks the
  records in two phases with `flush()` between them:
  1. `slowOnly` visits only groups whose consumed leaves are all slow (the
     existing test at line 706);
  2. `fast` visits only groups with at least one fast leaf.

  The Status phase stays last. `seenCounts` persists across phases, so each
  count is read once per walk, as today. Non-due walks and targeted reads
  (`paths != null`) are unchanged.
- Every walk reads the same request multiset as today. Only the order changes,
  and only on due walks.
- Tests use recorded-wire replay from `test/fixtures/cip_publication_goldens.json.gz`
  and a synthetic clock advancing 1 ms per request:
  1. For due and non-due walks, the sorted wire-request list is identical to
     the current order.
  2. Values and types are identical.
  3. On a due walk, the maximum fast `ageMs` is bounded by the fast and Status
     phases, and is lower than the interleaved order's by at least the slow
     phase's duration.
  4. A non-due walk's request order is byte-identical.

**WP4b.3 — Measure the remaining time.** These run under
`--dart-define=fraktal.cip.trace=true` only; default builds are unchanged.

- **Worker.** Per walk: `due`; group count and duration per phase (`slowOnly`,
  `fast`, `status`); the number of groups needing more than two attempts.
- **Delivery.**
  - The worker adds `sentTimelineUs` to each reply, taken from `Timeline.now`
    (`dart:developer`). It is one monotonic clock across all isolates.
  - The repository logs `replyWaitUs` (`Timeline.now - sentTimelineUs`) and
    `requestDelayUs` (UI send to worker receipt) beside the existing
    `stage=complete-sample-rejected` line.
- **Session.** A read-only host monitor samples `\Process(*)\% Processor Time`
  for the Echo emulator, the HMI process, Python and Dart every second, from
  download to rollback (`Get-Counter`).

**WP4b.4 — Run desktop acceptance on the shipped build.**

- Add `integration_test: sdk: flutter` to `HMI/pubspec.yaml`
  `dev_dependencies`. It is an SDK package, dev only, and nothing extra ships.
- Move the session's `desktop_diagnostic_qualification_test.dart` into
  `HMI/integration_test/ab_desktop_acceptance_test.dart`, with driver
  `HMI/test_driver/integration_test.dart`. Coverage stays the same:
  - production factory and repository;
  - an in-memory public-read acceptance-panel policy, using existing content
    configuration, while live mode stays logged out and PLC access is unchanged;
  - LIVE and the expected seven modules at every capture;
  - every tab of every module, the fieldbus page and its three nodes (31 views);
  - two refused actions per root, the read-only icon present, zero client
    writes.

  It uses `IntegrationTestWidgetsFlutterBinding`; screenshots stay on the
  existing `RepaintBoundary.toImage` path.
- Run it as:

  ```
  flutter drive --profile -d windows \
    --driver=test_driver/integration_test.dart \
    --target=integration_test/ab_desktop_acceptance_test.dart \
    --dart-define=fraktal.cip.trace=true \
    "--dart-define=fraktal.ab.desktop.endpoint=cip://127.0.0.1?slot=0&serial=601FC87B" \
    --dart-define=fraktal.ab.desktop.output=<session>/desktop_profile
  ```

- The debug `flutter test` form keeps only its captured-fixture mode, as
  rendering proof with no freshness claim. That is its existing role.

**WP4b.5 — Rehearse without Echo.**

- Promote the socket `Peer` in `HMI/test/cip_transport_test.dart` into
  `HMI/tool/cip_rehearsal_peer.dart`, a loopback EtherNet/IP server that serves:
  - the Symbol, Template and record bytes of the sealed S4b generic capture
    `Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime/generic_capture.json.gz`,
    hash-pinned (its image differs from `30315E6D…` only in first-scan
    behaviour);
  - the recorded identity serial;
  - Read Tag Fragmented and Multiple Service Packet;
  - synthetic coherence counters: +2 every 10 ms, odd for 1 ms;
  - per-request delay interpolated between measured Flutter quantiles in the
    [host-timing record](Evidence/AB_S4B_HOST_TIMING_2026-10-27.md).

  It records the hash of the capture it serves.
- It is rehearsal apparatus, never acceptance evidence. No shipped endpoint
  default points at it.
- **Gate before any further S4b native preparation.** With Echo running
  genealogy, untouched, in the background:
  1. The profile-mode acceptance (WP4b.4) passes against the peer three runs in
     a row, with maximum effective age ≤ 700 ms.
  2. The debug `flutter test` live form, run against the same peer, either
     reproduces a STALE refusal or the record states why it does not.

  Record both in an offline evidence note.

**WP4b.6 — Session order.** The next runner runs these after
`candidate_regressions`, in this order:

1. the independent four-page configuration comparison (1,100 values against the
   post-fixture oracle);
2. `idle_equivalence`;
3. `generic_acquire`;
4. `desktop_profile`;
5. `candidate_timing`.

All five are read-only, so each runs and records even if an earlier one fails.
The session passes only if all pass.

**Offline gates before preparation.**

- WP4b.1–4b.5 tests pass, including the rehearsal gate.
- The full HMI suite passes on the pinned SDK with `--enforce-lockfile` (685
  plus the new tests, 12 skips), with `flutter analyze` and
  `flutter build windows --profile`.
- The PLC image is unchanged. Its 373 bindings, 2,339 AB tests, both v38 targets
  and 65% Capacity transfer by hash.
- 74 root tests; spec, contracts, strict consistency and whitespace.

**Native session S4b-Q** follows §4 with image `30315E6D…` and the unchanged
write scope.

| Gate | Pass criterion |
|---|---|
| E1 candidate cases | 41/41 (31 rows, 2 Access, 8 configuration) with exact restoration |
| E2 replays | 87/87 independent raw-read pairs; exact values and types |
| E3 observer | Zero Bad samples; every Good value younger than the fast Good limit; Uncertain rows payload-free |
| E4 configuration | Four pages, 1,100 exact values and types against the post-fixture oracle |
| E5 idle equivalence | 5,407 paths, zero differences |
| E6 generic acquisition | 5,407 values, seven modules |
| E7 desktop | Profile build LIVE at all 31 captures; seven modules, three bus nodes; refusals recorded; zero client writes; maximum effective age recorded |
| E8 scan | TASK cumulative maximum < 10,000 µs and zero overlaps from download to the end of E7; 20-sample timing recorded |
| E9 rollback | §4 step 4 complete |

**Failure responses, decided now.**

| Signature | Next step |
|---|---|
| E7 fails and the refused sample's fast-phase source age is > 400 ms | Move the slow refresh into its own worker operation between snapshots, so that a snapshot never contains slow rows: `refreshSlow` becomes a scheduled `acquireSlow` call, and snapshot walks are never due. Offline proof as in WP4b.2 |
| E7 fails and `replyWaitUs` is > 400 ms | Record a profile-mode DevTools timeline against the rehearsal peer. Fix the UI-isolate hotspot in its owning widget or in `OpcUaSnapshotMapper`. No freshness change |
| E7 fails in two consecutive profile sessions, and more than 10% of desktop groups need more than two attempts while host CPU is above 85% | Apply the pre-selected O7 fallback: the second bench PC (leg 1), or the recorded bench limit if no second host exists (leg 2) |
| Any of E1–E6 fails | Stop. Reproduce offline from the sealed bytes and fix the owning code. Never retry unchanged |
| E8 records an overlap or ≥ 10,000 µs | Stop. Locate it with the TASK trace; make the PLC-side fix in the generator, with its own image and Capacity. Never clear counters |

**Exit:** E1–E9 pass in one session.

### 5.2 S5 — Dart gateway `cip://` for Web clients and commanding

S5 changes only HMI and gateway code. The PLC image stays `30315E6D…`; its
V6.6 `CommandBindings` already publish the typed command ingress
([wire draft](AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md)).

**WP5.1 — Typed command writer in the client.**

- New `HMI/packages/fraktal_opcua_client/lib/src/cip_command_writer.dart`, used
  only when `CipSessionClient.connect(…, commandWrites: true)`. The desktop
  factory never sets it (D9). The gateway sets it when the instance has at least
  one `--write-root`.
- It uses one dedicated, serial-pinned 4,000-byte connection (the binding's
  `ConnectionBytes`), separate from the four read-only connections.
- `writeBatch(List<OpcUaWrite>)`:
  - It accepts only one root's `<root>/HmiRequest/<field>` writes with
    `Sequence` last. The gateway already enforces this; the writer re-checks it.
  - It maps the root to its `CommandBindings` row.
  - It encodes the `PayloadSymbol` record from its Template:
    - `SchemaVersion` = the row's `Version` (1);
    - `ManifestRevision` = the discovered `ConfigRevision`;
    - `StagedSequence` = `Sequence`;
    - `Arguments` = the nine Core fields. An absent field takes its Core zero
      value.
    - Strings are UTF-8 with a byte-counted `LEN`; `BoolValue` is native BOOL;
      `DurationMs` keeps UInt32 bits.
  - It refuses before any I/O on an unknown field, a type mismatch, a string
    longer than its Template capacity, or a payload over `MaximumPayloadBytes`
    (1,024).
- On the wire:
  1. one unfragmented Write Tag (`0x4D`) of the payload record;
  2. one Write Tag of the DINT `CommitSymbol` = `Sequence`.

  It returns true only if both replies are status 0. It never retries, splits or
  replays after a reconnect. Any transport error closes the writer connection
  and requires rediscovery.
- `write()` for a single path returns false for every path on CIP.
- Tests (offline, socket peer):
  - exact payload bytes for each of the 39 command kinds against the Template;
  - a refusal for each malformed case above;
  - ordering (payload, then commit), and no commit after a failed payload;
  - no write from a read-only client;
  - a reconnect discards the in-flight batch.

**WP5.2 — `cip://` in the gateway.**

- `HMI/gateway/bin/fraktal_gateway.dart`:
  - Accepts `cip://<host>[:44818]?slot=<0-255>&serial=<8 hex digits>`, using the
    same query validation as `external_repository_factory_native.dart:56-66`.
    `serial` is mandatory for the gateway, because it pins the controller the
    gateway may write to.
  - Connects through `ReconnectingOpcUaSessionClient` to
    `CipSessionClient.connect(commandWrites: writeRoots.isNotEmpty)`.
  - Logs `stage=cip-connect` and `stage=connected transport=cip`, and reports
    the OPC UA security profile as ignored, as for ADS.
  - The usage text and the scheme error message add `cip://`.
- `HMI/gateway/lib/src/fraktal_gateway_server.dart`: write validation and the
  global serializer are unchanged. The `QUERY_CONFIG` viewer exception
  (`_isConfigQuery`) is never used on CIP: a read-only instance's client refuses
  writes, and configuration is read through WP5.3.

**WP5.3 — Configuration pages over the gateway.**

- Add the method `readConfigurationPage` (`params: {root, model}`) to
  `fraktal.opcua.gateway.v1`. The gateway answers it from the session client's
  `OpcUaReadOnlyConfigurationClient` after `config.permitsRead('<root>/…')`.
- An older gateway answers `Unsupported gateway method.`, and the client
  reports configuration as unavailable. It never falls back to a mailbox query.
- `HMI/lib/data/opcua_gateway_client_io.dart` and `opcua_gateway_client_web.dart`
  implement `OpcUaReadOnlyConfigurationClient` with the new method. The WebSocket
  gateway protocol section of `OPCUA_TRANSPORT.md` documents it.

**WP5.4 — Installer, tray and documents.**

- `HMI/gateway/deploy/windows/fraktal_instances.ps1`, `Test-FraktalEndpoint`:
  accept `cip` with a non-empty host, only the `slot` and `serial` query keys,
  and a serial of 8 hex digits. It also lacks `s7web` (found 2026-10-27): the
  scheme set is `ws/wss/http/https/opc.tcp/ads`, so a `s7web://` instance — a
  transport the gateway already serves — is rejected by the installer today.
  Add the scheme in the same change.
- `fraktal_wizard.ps1`: the endpoint labels and invalid-endpoint messages
  (lines 505 and 575) name `cip://<host>?slot=0&serial=<serial>`.
- `HMI/gateway/DEPLOYMENT.md` and `Specification/Guides/WEB_HMI_GATEWAY_DEPLOYMENT.md`:
  a `cip://` row and an example instance. The per-instance write-root question
  is unchanged.
- Remove the Python AB gateway instructions from the AB README and
  `AB_NEW_PROJECT_GUIDE.md`. The code itself is deleted in WP6.7.

**Offline gates:**

- the WP5.1–5.4 tests;
- `dart test` in `HMI/gateway`;
- the full HMI suite and analyzer;
- `dart run tool/build_gateway.dart --clean`, including the Windows installer;
- the AB and root gates, unchanged.

**Owner decision before the session:** O3, the bench gateway posture.

**Native session S5-Q** follows §4 with the same image and rollback. The
controller writes come only from these cases. The automated cases use the Dart
WebSocket client, which speaks the same protocol as the Web HMI.

| Case | Instance | Pass |
|---|---|---|
| C1 discovery | `echo` | LIVE with seven modules; `/readyz` 200; `writeAccess.enabled` true |
| C2 login, valid PIN | `echo` | Accepted with a matching typed acknowledgement; no Secret in any snapshot, log or evidence |
| C3 login, wrong PIN | `echo` | Refused with the owner's reason |
| C4 mode MANUAL → AUTO → MANUAL | `echo` | Each step acknowledged; `Mode` follows |
| C5 one manual command on one CM | `echo` | Acknowledged; the CM state follows |
| C6 configuration edit, then exact restore | `echo` | The value changes, then equals the original; `ConfigRev` advances |
| C7 configuration page | `echo` | `readConfigurationPage` equals the S4b oracle page |
| C8 write outside the write root | `echo` | Refused by the gateway; the PLC acknowledgement is unchanged |
| C9 duplicate or stale sequence | `echo` | Refused by the gateway; the acknowledgement is unchanged |
| C10 read-only instance | `echo-view` | Every command refused before the PLC; the acknowledgement is unchanged; `writeAccess.enabled` false |
| C11 gateway restart | stop, then start `echo` | Client STALE, DOWN after 5 s, LIVE after the restart; nothing replayed (acknowledgement unchanged across the restart) |
| C12 browser | owner, Chrome, the packaged Web HMI on `echo`'s origin | LIVE overview, login, an acknowledged mode change, logout; the owner records the checklist, as on [2026-09-24](Evidence/AB_BROWSER_COMMAND_2026-09-24.md) |
| C13 final state | `echo` | Logged out, MANUAL, idle |

**Exit:** C1–C13 pass, and `/healthz` `writeAccess` matches each instance's
configuration.

### 5.3 S6 — Retirement, collapse, persistence and events

Order: WP6.1 → 6.2 → 6.3, with 6.4 (owner approval) in parallel; then 6.5 → 6.6
→ 6.7 → 6.8 → the native session.

**WP6.1 — Classify every legacy consumer.** Re-run the census script
(`Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Continuation/inventory_legacy_consumers_01.py`)
on the current tree. It found 107 direct consumers (54 tools, 53 tests) and 284
transitive ones. Extend it to assign each module one class by these rules; the
first match wins, and an unclassified module stops the step.

| Class | Rule | Action |
|---|---|---|
| RT runtime projection and gateway | `fraktal_ab_projection`, `fraktal_ab_projection_replay`, `fraktal_ab_gateway`, `fraktal_ab_mailbox_probe`, their `test_` modules, `requirements-gateway.txt`, `HMI/test/live_ab_gateway_test.dart`, `HMI/test/live_ab_command_test.dart` | Delete in WP6.7 |
| MO migration oracle | `fraktal_ab_s<N><x>_{equivalence,reference,fixture_execute,revision_execute,lifetime_execute,io_execute}`, `fraktal_ab_s4b_equivalence`, `fraktal_ab_canonical_equivalence`, `fraktal_ab_canonical_observation`, `fraktal_ab_paired_observation`, `fraktal_ab_mailbox_frame`, and their tests | Final sealed replay (WP6.3), then delete in WP6.7 |
| GN generator | `fraktal_ab_generate`, `fraktal_ab_resources` | Collapse in WP6.6 |
| AD host adapter | `fraktal_ab_host_events`, `fraktal_ab_sets`, `fraktal_ab_set_broker`, `fraktal_ab_medium` | Re-home in WP6.5 |
| HX acceptance harness | Every other `*_execute`, `fraktal_ab_press_parity`, `fraktal_ab_s9_*` | Migrate to canonical reads in WP6.2 |
| UT unit test | Every other `test_fraktal_ab_*` that uses `*_context_members` or the projection | Rewrite against the canonical structures in WP6.6 |
| HL helper | Any other direct consumer | Replace the legacy import with its canonical owner; a helper that serves only RT or MO follows them |

The output is `Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_<date>.json`.
WP6.7's deletion step reads it.

**WP6.2 — Phase A: harnesses on canonical reads, legacy still present.**

- Every HX module reads through `fraktal_ab_canonical_reader.py` (S1) instead of
  `read_unit`, `read_layout` or `*_context_members`. Assertions are unchanged.
  `fraktal_ab_press_execute.py` loses its `read_layout` and `read_unit`
  definitions.
- Until the baseline switch (O6), a harness chooses its reader by discovery: a
  controller that publishes exactly one canonical manifest is read
  canonically, and any other is read through the legacy reader. The rollback
  baseline is the legacy genealogy image, which has no canonical tree. This
  temporary dual path ends in WP6.7.
- Offline gate: every migrated harness replays its sealed captures with
  unchanged verdicts.

**WP6.3 — Final sealed replay, before any generator change.** On the
pre-collapse tree, run once more:

- every MO test;
- all accepted image pins (byte-identical regeneration);
- every sealed capture replay.

Seal the result as `Evidence/AB_S6_MIGRATION_ORACLE_FINAL_REPLAY_<date>`, with
hashes. From then on, sealed evidence stays readable data, and its executable
replay ends by design.

**WP6.4 — Host-service contract (owner approval, O4).** The staged ConfigSet and
ConfigProvider inputs, the live-document keeper and the host-event sink are the
last consumers that need the station declaration and the legacy endpoints. For
example, `fraktal_ab_set_broker.py` maps keys through `gen.editable_values(app)`.
The recommended contract is V6.9, additive like V6.6:

- a `HostServiceBindings` manifest table with one row per root and service
  (`ConfigSets`, `ConfigProvider`, `LiveDocuments`, `HostEvents`). Each row gives
  the version, request, commit and reply symbols, the chunk record and maximum
  chunk bytes, and the required access gate;
- documents move in bounded chunks addressed by (scope, key). The PLC resolves
  keys to its own ordinals, as the typed command ingress does;
- every chunk and receipt uses the typed ingress's commit/acknowledge state
  table: serial arithmetic, collision refusal, no replay;
- the legacy staged endpoints and the legacy Frame ingress are removed in WP6.6.

Write it as `AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_<date>.md`, with
its inventory, then ask. WP6.5 and the host-service part of WP6.6 wait for the
approval.

**WP6.5 — Declaration-free host adapter.**

- One process per controller instance:
  `FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_host_adapter.py`, built from
  the AD modules. It discovers through the S1 reader and the V6.9 bindings, and
  serves three things:
  - configuration sets and the provider, with `FileStore` unchanged at
    `%LOCALAPPDATA%\Fraktal\ConfigSets\<serial>-<root>`;
  - live documents re-applied after a download, through `FileMedium`;
  - HostEvents delivery, with durability, cursor and deduplication unchanged.
- It writes only through the V6.9 endpoints and imports nothing from
  `fraktal_ab_declaration` or `fraktal_ab_generate`; a test asserts that.
- It runs beside each gateway instance from an optional
  `instances\<name>\host_adapter.args`, and the tray supervises it as a second
  process of that instance. Instance discovery is unchanged (every folder with a
  `gateway.args`), so no third index is added. The generic gateway stays
  binding-neutral.
- The persistence medium is decided (O5, 2026-10-27): the host `FileMedium`
  is the AB reference medium — what the press bench implements — behind the
  same seam a controller medium could later use (WP7.5 cannot run under O2,
  so the seam stays open without a date). A project may declare PLC memory
  only: it runs no host adapter, publishes no `ConfigPersist` subtree and
  claims no durability.

**WP6.6 — Phase B: collapse the generator.** In `fraktal_ab_generate.py`:

- **R8.** The canonical structures become the working storage. Remove
  `common_/module_/type_/unit_context_members`, the legacy contexts, the V5
  manifest tables (with their 768-field cap), the copy layer and the S3h
  observation frame (`canonical_observation_period_ms`).
- **R3.** Each module AOI writes its canonical leaf directly through InOut;
  `ScanCanonical` and `CanonicalDiagnostic` keep only per-instance calls.
- **R6.** Acceptance-only routines (native check vectors, first-scan bench
  vectors) are emitted only when a declaration enables them. Production
  declarations never do.
- **R5.** A production declaration selects one AUTO rendition (ST, SFC or LD).
  Acceptance declarations keep all three for the parity gate.
- The legacy staged service and Frame endpoints are removed. V6.9 is the only
  host-service path, and the typed ingress is the only command path.
- UT modules assert on the canonical structures in the executed-ST model.

Offline gates:

- **Schema identity.** The collapsed genealogy-S4b image's discovered path set
  and logical types equal those of `30315E6D…` exactly (5,940 paths). The
  collapsed press image's equal the press S3 exit image's.
- Executed-ST model cases are unchanged.
- Both v38 targets build and read back; the access audit passes.
- Capacity is recorded against the capacity plan's ranges: 2.3–2.6 M Blocks
  with R8 alone, 0.9–1.4 M with R3.
- The scan-risk proxy (ST token count) is recorded.

**WP6.7 — Delete and update the gates.**

- Delete RT and MO per the classification file. After the baseline switch,
  delete the harnesses' legacy reader branch and the legacy baseline fixture.
- Re-run the census; it must report zero direct legacy references.
- Switch `tools/check_ab_spec.py` and `tools/check_ab_contracts.py` to V2.
  Update `tools/check_consistency.py` wherever it names a deleted file, and the
  AB README's test counts.

**WP6.8 — Documents and activation.**

- **Part III.** Apply the [amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md):
  - §1, §2.1 and §4.1: reference profile and L24ER retirement;
  - §3.8 type map V2; §3.10 exposure; §3.10.2 read-only configuration;
  - §3.13 coherence; §11.1 topology.

  Add V6.9.
- **Frozen contracts.** `AB_FROZEN_CONTRACTS_V2.json` gets `active: true`, and
  V1 is marked superseded.
- **`OPCUA_TRANSPORT.md`.** A new "Allen-Bradley CIP transport" section beside
  ADS and the S7 Web API: discovery, row coherence, the freshness profile, the
  command writer and `readConfigurationPage`.
- **`AGENTS.md`.** §3a: the v37+ baseline, the L24ER retired, `cip://` no
  longer spike scope, the Python gateway gone. §5: `cip://` among the gateway
  transports.
- The AB README, `AB_NEW_PROJECT_GUIDE.md`, and `HMI_CONTRACT.md` (AB adopts
  TC3's bounds for the five D2 arrays).

**Native session S6-Q** follows §4. One approval covers two candidate images in
sequence: the collapsed genealogy-S4b image, then the collapsed press image.

- **Genealogy gates:**
  - the 41 candidate cases on canonical harnesses;
  - E7 desktop;
  - gateway cases C1, C4, C6 and C11;
  - native schema identity (path set and types equal to S4b);
  - Capacity and scan (< 10,000 µs, zero overlaps).
- **Press gates:** the 47 rows, with the seven core cases in each of ST, SFC and
  LD; schema identity; Capacity and scan.
- **Baseline switch (O6, approved 2026-10-27).** The collapsed genealogy image
  becomes the Echo rollback baseline, with its own 31 canonical baseline cases
  recorded in this session. The legacy genealogy pin stays archived and is no
  longer downloaded.

**Exit:** definition-of-done items 1, 4 and 5, and the census reports zero
direct legacy references.

### 5.4 S7 — Physical controller and CIP Security

**WP7.0 — Hardware (owner decision O2).** Recommended:

- a ControlLogix 5580 (1756-L81E or larger) at firmware v37 or later, CIP
  Security–capable on the port the HMI uses;
- one digital input and one digital output module matching a declared
  station's I/O catalog;
- an isolated network.

Staying in Echo's family keeps the 3 MB memory basis. Confirm CIP Security
support for the exact catalog number and firmware against Rockwell's current
compatibility data before purchase.

**O2 decided 2026-10-27: no physical controller will be bought.** S7 is
therefore deferred without a date, not cancelled: every hardware-only gate
(WP7.4 physical acceptance, WP7.5 controller-medium probe, and
definition-of-done item 6) becomes a declared exclusion in the binding record
for as long as no hardware exists — the press81 `require_controller_metrics`
pattern, never a standing event. WP7.5 never runs, so O5's "revisit after
WP7.5" clause is void. Whether WP7.1–7.3 (`cips://`, direct writes, policy
commissioning) are worth implementing with no controller that can accept them
is revisited only after S4b–S6 exit; Echo cannot terminate TLS on port 2221,
so nothing in S7 is provable on the bench.

**WP7.1 — CIP Security client.**

- Endpoint: `cips://<host>[:2221]?slot=<n>&serial=<hex>`, EtherNet/IP over TLS.
- Certificate-based device identity; Dart's TLS stack has no PSK.
- Credentials come from `FRAKTAL_CIP_CLIENT_CERTIFICATE`,
  `FRAKTAL_CIP_CLIENT_PRIVATE_KEY`, `FRAKTAL_CIP_CLIENT_KEY_PASSWORD` and
  `FRAKTAL_CIP_TRUSTED_CA`, following the WSS pattern in
  `external_repository_factory_native.dart:36-45`.
- TLS 1.2 or later. The server certificate is validated against the trusted CA,
  and the identity against the pinned serial.
- The same `CipReadPool` and `CipSessionEngine` run above the TLS socket.

**WP7.2 — Direct writes.** `cips://` sets `commandWrites: true`, so `readOnly`
is false; `cip://` stays read-only. The writer is WP5.1's. The operator still
authenticates through the PLC login (Core §14).

**WP7.3 — Policy commissioning.**

- A FactoryTalk Policy Manager policy: controller and HMI-host certificates,
  integrity and confidentiality required.
- Record the policy export as evidence, without private keys.
- Record the Part III §11.2.1 evidence: authenticated principal, least
  privilege, no anonymous write.

**WP7.4 — Physical acceptance.** Every session needs its own owner
authorization, and the owner performs any power cycle. Gates:

- Capacity on the physical controller;
- scan maximum and overlaps under the workload;
- the 41 + 31 cases and the press's 47 rows;
- the desktop over `cips://` with writes: login, mode, a manual command,
  configuration edit and restore;
- the gateway over `cip://` and `cips://`;
- retention across a power cycle;
- download and firmware/project upgrade, with live documents re-applied by the
  host adapter;
- physical-module identity and offline I/O proof (the S3 residual): every
  catalog channel's address, tag and identity match the declaration and the
  fieldbus product;
- unsecured CIP writes refused.

**WP7.5 — Controller medium probe (v38 audit N8).** A read-only probe of the
Logix file and SD services on the 5580. Its result decides whether O5 can move
§3.8b to a controller medium. Until then, the host `FileMedium` stays.

**Exit:** definition-of-done items 2, 3 and 6 on the physical controller.

## 6. Decisions

### 6.1 Already decided

- D1–D9 in the design note.
- The V2 and Part III targets (2026-10-20).
- The finite corrections in §1.
- S3j D-1 to D-6, R1 and R2 (2026-10-24).
- S4 coherence contract A, the S4b read-only configuration option A and the S3k
  command ABI option A (2026-10-25).

### 6.2 Decided in this plan

| # | Decision | Basis |
|---|---|---|
| P1 | The path vector is sent once per discovery | `OPCUA_TRANSPORT.md:385-387`; the repository contract; the Web API client |
| P2 | Slow-due rows are read before fast rows; counts once per walk | The request multiset is unchanged; fast age is bounded by fast work; slow Good is 7.5 s |
| P3 | Desktop freshness acceptance runs the profile build on the Windows embedder (`flutter drive --profile`), adding the SDK `integration_test` dev dependency. The debug harness stays fixture-only | The shipped product is AOT, and debug timing is not representative. Rendering contention is measured (§2.2) |
| P4 | The Echo-free rehearsal peer passes before any further S4b native preparation | Nineteen sessions, none of them accepted; every iteration costs an owner approval and a download |
| P5 | Read-only stages run after a failure; writer stages stop at their first failure | Each session yields all of its read-only results |
| P6 | Timing instruments are trace-only: phases, delivery via `Timeline.now`, host CPU | Measure before the next correction |
| P7 | CIP command writes: the payload record, then the commit DINT, on one dedicated connection; no retry, split or replay; single writes refused | V6.6 wire draft; Part III §7.7; the `OPCUA_TRANSPORT.md` mailbox rules |
| P8 | Gateway `cip://` requires `serial`; writes only with a write root | The gateway writes to the PLC; AGENTS.md §3a |
| P9 | Configuration over the gateway goes through `readConfigurationPage`; no mailbox fallback on CIP | S4b option A; one mechanism (O9) |
| P10 | Browser acceptance is an owner-operated checklist; the automated cases use the Dart WebSocket client | No browser automation exists in the repository; precedent of 2026-09-24 |
| P11 | The S6 classification rules and actions in WP6.1 | The census |
| P12 | A final sealed replay precedes deleting the oracles; executable replay of old evidence then ends | One source (O9); evidence stays immutable |
| P13 | Harnesses choose their reader by discovery until the baseline switch | No declaration at runtime; the legacy baseline must stay testable |
| P14 | Host services run in one declaration-free Python adapter per instance, supervised beside the gateway | Design note S6; Core §11.6; the generic gateway stays binding-neutral |
| P15 | `cips://` with certificate identity and WSS-style environment credentials | D9; Dart TLS has no PSK; the existing environment-variable idiom |

### 6.3 Owner decisions

Each native session also needs its own exact authorization (§4) — waived for
Echo by the standing authorization of 2026-10-27. That is an operation
approval, not a design decision.

**Decided 2026-10-27:**

- **O1 — commit and push.** Everything since `f194c3a53` was committed and
  pushed to `main` on 2026-10-27, excluding the `.dart_tool` caches inside
  sealed evidence snapshots (the modified Siemens ones restored to HEAD; a
  `.gitignore` rule keeps future ones out). From here on, one commit per
  stage exit.
- **O2 — no S7 hardware purchase.** See WP7.0 for the recorded consequences:
  hardware-only gates become declared exclusions; S7 is deferred without a
  date; WP7.5 never runs.
- **O3 — Echo posture and standing use.** The owner states Echo exists
  exclusively for this work, so Echo sessions need no per-session approval
  (§4 step 2 records the standing authorization; guards and rollback stay).
  The S5 bench runs the recommended pair: a write-enabled `echo`
  (`--write-root Press`, port 8080) and a read-only `echo-view` (port 8081),
  recorded in the binding record (AGENTS.md §3a).
- **O4 — V6.9 host-service contract approved** as the WP6.4 shape. The review
  document with its inventory is still written before WP6.5, but no further
  approval gates WP6.5 or the host-service part of WP6.6.
- **O5 — §3.8b persistence medium** (decided in the second batch, same day).
  The host `FileMedium` through the WP6.5 host adapter is the AB reference
  medium and what the press bench implements. A project may declare PLC
  memory only: it runs no host adapter, publishes no `ConfigPersist`
  subtree and claims no durability — the HMI reads that as "nothing
  pending, nothing lost", never a permanent alarm. The declaration's
  `ConfigMedium` selects per project; the controller-medium seam stays open
  without a date.
- **O6 — baseline switch approved.** The collapsed genealogy image becomes
  the Echo rollback baseline at S6-Q, after it passes its gates in that
  session; the legacy pin stays archived with its hash.
- **O7 — fallback pre-selected, leg 1.** If the trigger fires (two profile
  sessions failing only E7 under host CPU above 85%), the desktop
  acceptance moves to a second bench Windows PC running the same profile
  drive against `cip://<echo-host>`. The bench-limit leg (E7 in fixture
  mode, recorded as a declared exclusion) applies only if no second host
  exists. No limit, budget or rule changes in either leg.

No owner decisions remain open. The next owner touchpoints are the ones
that cannot be delegated: the C12 browser checklist (owner-operated by
design, P10) and any controller other than Echo.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A shared host cannot demonstrate the 1 s desktop budget | P3 profile build, P4 rehearsal, P6 measurement; O7 as the recorded contingency |
| The scan margin is 998 µs; R3's indirect addressing can raise scan time | Measure per image (E8); the TASK monitor runs from download; a generator fix gets its own image |
| The collapse moves code and data | Schema identity, executed-ST model cases and native rows gate WP6.6; the capacity ranges are ±30% estimates |
| Harness migration volume (107 direct and 284 transitive modules) | WP6.1 rules; Phase A before the collapse; the final sealed replay before deletion |
| Unsecured CIP writes from the gateway host carry the PIN in clear on the controller network | Part III §11.2.1 zone-and-conduit posture until S7; the bench uses loopback only; `cips://` at S7 |
| Persistence on hardware | WP7.4 download/upgrade retention; WP7.5 probe; the host `FileMedium` stays until a medium is accepted |
| Echo availability | Elevated start by the owner; service and listener checks before every guarded step; orderly shutdown |
| HMI customizations bound to the five old AB array paths | Release notes; the mapper is already base-agnostic |

## 8. Sequence and effort (estimates, not commitments)

| Step | Offline work | Native sessions |
|---|---|---|
| S4b: WP4b.1–4b.6 | 3–4 days | 1 (S4b-Q) |
| S5: WP5.1–5.4 | 4–5 days | 1 (S5-Q) |
| S6: WP6.1–6.8 | 3–4 weeks, plus the O4 review | 1 (S6-Q, two images) |
| S7: WP7.1–7.5 | 1–2 weeks after hardware | 1–2 on hardware |

Owner approvals and native sessions set the real pace. The plan avoids the
S4b pattern of one session per hypothesis: each session above runs only after
its offline gates, and the rehearsal peer where one applies, have passed.
