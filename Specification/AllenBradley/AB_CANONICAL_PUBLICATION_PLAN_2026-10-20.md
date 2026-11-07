# Fraktal/AB canonical publication — implementation plan

Non-normative plan, 2026-10-20, restructured 2026-10-27. It executes the
decisions in [the design note](AB_CANONICAL_PUBLICATION_DESIGN_2026-10-19.md)
(D1–D9). Where the two differ, the design note wins and this plan is corrected.
Part III and frozen contracts V1 stay authoritative for the shipping
implementation until S6 activates V2.

This revision retains the completed S4b/S5 checklists and states the remaining
work (S6–S7) as work packages: the files,
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

## 2. Status through 2026-10-30

| Stage | Status | Accepted record (local Echo L81E v38) | Still open |
|---|---|---|---|
| S0 type rules, V2 draft | Done | [types](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md), [supplementary](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md) | — |
| S1 Python reference reader | Done | [S1](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md) | — |
| S2 module tree | Done | [S2](Evidence/AB_S2_CANONICAL_RUNTIME_2026-10-21.md) | — |
| S3a–S3k surfaces | Done at genealogy scope | see the list below | — |
| S3 exit: press in ST/SFC/LD, path census | Done | [press S3 exit](Evidence/AB_PRESS_S3_EXIT_RUNTIME_2026-10-25.md), [census](AB_CANONICAL_PUBLICATION_S3_PATH_CENSUS_2026-10-25.json) | Physical-module identity and real I/O move to S7 |
| S4a coherence bindings | Done | [S4a](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md) | — |
| S4b generic Dart client and desktop | **Done at Echo scope** | [V6.10 runtime](Evidence/AB_S4B_OWNER_REVISION_RUNTIME_2026-10-29.md): all E1–E9 pass together | Physical/security evidence remains S7; V2 activation remains S6 |
| S5 gateway, Web, installer | **Done at Echo/package scope** | [S5 qualification](Evidence/AB_S5_GATEWAY_QUALIFICATION_2026-10-31.md): C1–C13, two-client stability, owner visual check, native gates and verified genealogy recovery | Original baseline START refusal retained; investigate in S6 harness migration. Physical/security acceptance remains S7 |
| S6 retirement, collapse, persistence, events | WP6.1 classified; first offline WP6.2 harness migrated; shared row reader with bounded row-body batching passes offline replay; harness private facts assigned to a WP6.6 acceptance-only structure (O10); gateway command client built (O11); WP6.3 final oracle replay sealed; WP6.4 inventory and V6.11 layouts written, client binding and generic ingress pass offline; V6.11 opt-in emits; its set service (all eight operations) and LiveDocuments keep/restore pass on the emitted code offline; WP6.5 host adapter, ported to Dart and supervised by the tray, answers them offline (HostEvents open); Echo re-baselined onto the genealogy pin after a factory reset (§2.18); the first V6.11 candidate builds on both v38 targets and fits offline; WP6.6 started: context inventory, schema-identity gate with pre-collapse fixtures, collapse increments C0–C7; O12 approved | [S6 consumer review](AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md), [row-reader review](AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md), [current classification](AB_S6_CONSUMER_CLASSIFICATION_2026-11-02_03.json), [host-service inventory](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md), [Echo re-baseline](Evidence/AB_S6_ECHO_REBASELINE_2026-11-04.md), [V6.11 candidate](Evidence/AB_S6_HOST_CANDIDATE_OFFLINE_2026-11-04.md), [collapse review](AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) | Live integration/native proof, remaining harnesses/replays, host-service layouts/implementation, collapse, retirement and activation (§5.3); S6 exit remains open |
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
| S4b accepted image | ACD `84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC`, source `22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06`, manifest `BBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6`. Capacity 2,077,924 used / 1,067,804 available / 3,145,728 Blocks (66%). Older V6.8 pins remain historical |
| S4b write scope | The inherited 41 candidate cases (31 rows, 2 Access, 8 configuration) with exact restoration; 31 baseline cases after rollback |
| S4b accepted scan | TASK median 966 µs, cumulative maximum 8,974 µs, zero overlaps: 1,026 µs margin on the 10 ms period |
| Press candidate | ACD `15E8902551FD6C6D8041727E69D5C2FE917D5BAC0E031D808DB66D8EBFCFD76F`, 53% Capacity, MaxScan 7,246 µs |
| Published surface | Genealogy S4b: 5,940 discovered paths, 4,799–5,407 occupied values, 237–239 guarded groups per full walk, seven modules, three bus nodes. Press: 4,058 paths |
| Toolchain | Flutter 3.47.5 / Dart 3.13.4 at `C:/work/fraktal-toolchains/flutter-3.47.5`, always with `--enforce-lockfile`; Studio v38 two-target build and read-back; the automatic Capacity collector |
| Tests | 759 HMI passed / 12 skipped; 2,356 AB; 74 root; spec, contracts, strict consistency and whitespace clean |
| Bound inputs | 638 product/proof source bindings; 725 prepared runtime inputs in the accepted session |

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
  Every row keeps an equal-even counter proof. Protocol 1 stays under its
  10 ms scan period; approved O9 protocol 2 uses its PLC-owned version and
  separate scan progress inside the declared one-second proof bound.
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

### 2.4 Scheduling continuation, 2026-10-28 — original-tier prerequisite still open

The [scheduling record](Evidence/AB_WP4B5_SCHEDULING_2026-10-28.md) retains
bounded native row batching and count deduplication, phase planning/decoding
outside neighboring proof windows, small coherent discovery headers, separate
slow work, atomic tier installation, fair worker scheduling, and owner-version
configuration caching. Trace timing now applies only to snapshot replies;
polluting configuration descriptors made their equality check always refuse.
The peer's fractional delays meet their monotonic deadline; immutable encoded
replies may be cached, but counter replies and every delay draw remain live.

Current gates: **738 HMI passed /12 skipped**, clean analyzer, locked dependencies,
Windows profile build, root spec/contracts/strict consistency and **74 root tests**.
All **373 PLC/gate bindings** still match, transferring 2,339 AB tests, both v38
builds/read-backs and 65% Capacity. The image is unchanged and is not downloaded.

Three provisional profile runs complete all 31 views with maximum mapped ages
393.105/433.729/423.702 ms. They use a temporary metadata-heartbeat fallback,
which changes a tier rule and was **reverted** under §3. They do not qualify the
current source. Debug reproduces STALE after Overview. Original-tier profiles
26–28 fail LIVE coverage; the overdue-poll experiment is also reverted. All
failures and superseded source copies remain recorded. Current valid consecutive
passes: **zero**. No S4b-Q preparation or native acceptance is claimed.

The [read-tier review](AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md)
and its 230-path inventory request a CIP-only configuration fallback decision
(O8). The original fast policy stays active while it is pending. After the
decision: implement/test the chosen policy, require three fresh exact-source
profile passes plus debug comparison, then WP4b.6/S4b-Q. Echo remains on genealogy,
with passing before/after preflights and zero controller-changing operations.
O1–O7 stand; O7 is not triggered by synthetic results. No commit or push.

### 2.5 O8 approved, 2026-10-28 — implement CIP-only configuration heartbeat

The owner answers the review with “Approve CIP configuration heartbeat
(Recommended)” (`call_a7b096025e8b4393802914b727457fab:0`). This approves its
dependent offline work. Add the optional transport capability, enable it in
CIP only, preserve other transports and require fresh final-source rehearsal
and native gates. The §2.4 provisional passes are still not acceptance of the
new implementation. The source at that checkpoint retains the original tiers.

### 2.6 O8 implemented; final-source rehearsal prerequisite passes, 2026-10-28

The [O8 record](Evidence/AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28.md)
implements the optional CIP-only policy and reconnect delegation, with an
explicit tier-cache signature. Other transports retain their policy. The
existing classifier, exact replacements, live paths, proof/retry rules and
read-only gate remain authoritative.

Three consecutive final-source profile runs (seeds 8/7/9) complete all 31 views,
seven modules and three bus nodes at maxima **392.880/484.124/453.639 ms**.
Debug on the same source reproduces STALE after Overview. Independent verification
matches all 27 bound HMI inputs and confirms the required profile margin.
The earlier provisional broader-policy results are not reused.

**740 HMI passed /12 skipped**, analyzer, locked dependencies, Windows profile
build, 74 root tests and the root gates pass. All 373 PLC/gate bindings still
match, transferring 2,339 AB tests, both v38 builds and 65% Capacity. Echo remains
on genealogy, with no controller changes. WP4b.5 passes; next is WP4b.6/S4b-Q
preparation under standing O3. S4b and native E1–E9 remain open. No commit/push.

### 2.7 O8 native attempt: observer expiry; genealogy restored, 2026-10-29

The [prepared S4b-Q session](Evidence/AB_S4B_Q_PREPARATION_2026-10-29.md)
runs under standing O3 with unchanged image `30315E6D…`, 65% Capacity and
700 hash-bound inputs. The [attempt record](Evidence/AB_S4B_Q_ATTEMPT_2026-10-29.md)
records **41/41 candidate cases and 87/87 independent raw-read replays**.
The concurrent Dart observer fails E3 after 43 samples: 56 Status leaves expire
at 3,310.162 ms following 20 unsuccessful refresh attempts. The retained
counter/window records show changed revisions; no proof or expiry limit changes.

E4–E7 and final 20-sample timing are skipped: the inherited orchestration exits
when the observer reports failure. This violates P5's intended failure isolation
and must be corrected before the next session. The CPU sampler also stops on a
transient invalid Windows performance-counter sample. No native E7 or O7 fallback
condition is claimed. TASK telemetry retains 6,416 post-download samples,
cumulative maximum **8,994 µs**, zero overlaps; E8 is incomplete without final
timing and desktop coverage.

Genealogy rollback, five exact original documents, **31/31 baseline cases**,
MANUAL/idle/logout, final checks and preflight verification pass. No dumps or
excluded operations. Next: reproduce the observer acquisition failure offline,
correct its tier/coalescing ownership and the two harness gaps, then qualify
the final source before another S4b-Q session. S4b/S5/S6 remain; S7 is deferred.
Nothing is committed or pushed.

### 2.8 Observer policy and harness corrections, 2026-10-29

The [correction record](Evidence/AB_S4B_OBSERVER_POLICY_2026-10-29.md)
applies approved O8 to the independent Dart observer and publishes its slow/
excluded sets atomically. The shared classifier selects exactly the 230 approved
configuration leaves; identity, active alarms, counters and Access remain fast.
The sealed native expiry remains refused by a regression retaining all 56 leaf
diagnostics. No expiry, proof or retry limit changes.

P5 now collects all five read-only outcomes after a writer/observer failure on a
healthy candidate. Eight orchestration scenarios prove rollback and ordering.
The CPU sampler retains invalid process samples and continues valid host/emulator
sampling; injected churn and a live read-only sampler probe pass.

An adaptive-packing experiment is **reverted** after failing its consecutive
profile gate. All four experimental rehearsals and source copies are retained;
their 744/746-test intermediate results are not final-source acceptance. The
restored desktop's 27 inputs match the sealed O8 three-profile/debug proof
exactly, independently verified by hashes. Those unchanged-source proofs transfer;
the two new observer-only files are not imported by the desktop. Separately,
the changed observer passes 100 loopback samples, zero Bad samples and all four
configuration pages, without writes.

Final source: **743 HMI passed /12 skipped**, clean analyzer, locked dependencies,
Windows profile build and 74 root tests. The 373 unchanged PLC inputs retain
2,339 AB tests, both v38 builds/read-backs and 65% Capacity. Native improvement is
unproven. Next is fresh S4b-Q preparation/session under O3 with full P5 collection
and genealogy rollback. No stage exit, commit or push.

### 2.9 Native desktop passes; active observer remains open, 2026-10-29

The [observer retry](Evidence/AB_S4B_Q_OBSERVER_RUNTIME_2026-10-29.md)
runs the unchanged `30315E6D…` image under O3, after its 699 inputs are verified.
**41/41 candidate checks, 87/87 replays, 5,407-path idle equivalence and 5,407
generic values/seven modules pass. Native profile desktop completes all 31 LIVE
views**, seven modules and three bus nodes, with 74 mapped samples and maximum
effective age **446.321 ms**. TASK median in the final 20 samples is 966 µs;
cumulative maximum is **8,994 µs**, zero overlaps across 7,317 monitor samples.

E3 fails after 23 samples: 50 non-header Status leaves expire at 3,285.437 ms.
E4 runs but cannot compare pages because the failed observer produces none.
Its fresh Python oracle succeeds. P5 now collects every read-only stage in order;
the CPU sampler completes with 724 valid host samples, 196 retained invalid
process samples and no missing host samples. E7 passes, so O7 is not triggered.

A separate read-only one-connection timing probe records 24 outcomes without
Bad/Uncertain values; cyclic median is 144.761 ms. This suggests a scheduling/
connection-width investigation, not a proven cause or acceptance result. The
four-connection comparison reaches the restored baseline and correctly refuses
its missing canonical manifest; it is not a valid paired comparison.

Genealogy, five exact original documents, **31/31 baseline checks**, final checks
and preflight pass. No dumps or excluded operations. Next: make E4 acquire its
own Dart pages, reproduce controller communication serialization offline and
qualify a narrower live read schedule before another native session. S4b remains
open; S5/S6 and deferred physical S7 follow. No commit or push.

### 2.10 Read scheduling: prerequisite failed; owner-version proposal pending

The [read-schedule investigation](Evidence/AB_S4B_READ_SCHEDULE_2026-10-29.md)
implements initial one/four-group throughput qualification without publishing
trial caches, and an E4 producer independent of the cyclic observer. Peer checks
pass 100 samples/zero Bad and four pages/1,100 exact scalar values and types.
Fresh final gates pass: 750 HMI/12 skipped, clean analyzer, locked dependencies,
Windows profile build, 74 root tests and unchanged 373-input PLC gate transfer.

The final-source sequence has two 31-view passes (454.987/462.440 ms maximum),
then two refusals; it does not pass the three-consecutive-profile gate. Row reuse,
complete native structure reads, queue pacing, split proofs and separate headers
also fail their rehearsals and are reverted, with every source/output retained.
The restored 31 HMI inputs match the final 750-test source exactly. A debug
comparison refuses after Overview. No new native preparation/session ran.

An isolated root-header peer probe, with no desktop rendering, has 86 Good
reads then a five-field refusal after all 20 attempts: 14 changed counters,
three overlong equal-counter windows and three odd pre-counters. This is a peer
finding; it does not overturn the prior native desktop pass or trigger O7.
Genealogy remains Run/not faulted, MANUAL/idle/logout, with five exact documents
and preflight verified. No controller changes, commit or push.

Next is the [owner-version contract decision](AB_CANONICAL_PUBLICATION_S4B_OWNER_REVISION_REVIEW_2026-10-29.md),
which explicitly revisits Alternative B and plan §3 for a new protocol. It is
unapproved; existing protocol-1 rules stay unchanged. After agreement and offline
qualification, E1–E9 must pass together. S5/S6 remain; physical S7 is deferred.

### 2.11 V6.10 owner revisions: offline prerequisites pass

O9 is implemented and [qualified offline](Evidence/AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29.md).
The actual schema selects 29 existing header leaves/seven modules plus the
read-only configuration view. No Core values/types or new child fields change.
Owner revisions are independent of scan progress; protocol 1 retains its strict
scan-period rule. The wrap proof uses the conservative 2^30−1 recurring tokens.

Final gates: 2,354 AB and 759 HMI tests (12 HMI skips), both v38 builds/read-backs,
effective-access/SDK audits, locked dependencies, analyzer and Windows profile
build. ACD `84EC495F…516FBAC`, source `22DD1C2E…`, exact Capacity 66%
(2,077,924 used / 1,067,804 available / 3,145,728 Blocks). Opt-out V6.8 output
remains byte-identical; regeneration binds the compiled V6.10 image exactly.

Three final-source 31-view profile runs pass with maximum ages
383.054/407.711/420.990 ms, below 700 ms. Debug reproduces STALE after Overview.
The observer has 100 samples/zero Bad; four independent configuration pages
match 1,100 oracle scalars. The synthetic V6.10 discovery fixture preserves
all sealed native V6.8 product bytes and 5,407 values/types. It proves no new
native ABI. Earlier failures remain retained. Unused array routing counts are
skipped only when every descendant is excluded; targeted/live count consumers
and all proof/freshness/retry rules remain intact.

Echo remains on genealogy. Next is fresh sealed native preparation under O3,
then E1–E9 together and genealogy rollback. S4b exit is still open; S5/S6 follow,
physical S7 is deferred. V2 remains inactive and nothing is committed/pushed.

### 2.12 V6.10 native attempt: collector gap; genealogy restored

The [first precheck refusal](Evidence/AB_S4B_OWNER_REVISION_PRECHECK_ATTEMPT_2026-10-29.md)
makes zero controller changes: the template held the previous Capacity figures.
The guard correctly stops before deployment. Fresh preparation derives the
confirmation from the measured image; three new readiness tests pass.

The [native attempt](Evidence/AB_S4B_OWNER_REVISION_RUNTIME_ATTEMPT_2026-10-29.md)
downloads `84EC495F…` successfully; SDK/read-back/access audits pass. The Python
collector omits owner-counter Symbols from its capture and correctly fails its
V6.10 validator at the initial comparison, before the 41-case walk. P5 collects
all read-only outcomes. Dart passes four samples/zero Bad and four configuration
page reads; its native desktop stays LIVE/seven modules but fails complete-tab
coverage. Equality/acquisition gates fail on the incomplete Python capture.
TASK maximum is 7,759 µs, zero overlaps (668 monitor + 20 final samples), at
this incomplete workload scope. E1–E9 do not pass together.

Genealogy, five exact original documents, 31 baseline cases and all final checks
pass; Run/not faulted, MANUAL/idle/logout, no dumps or excluded operations.
The collector now derives every revision/progress scalar from both published
binding tables. Twenty-six focused tests pass. The old collector reproduces
the refusal through that acquisition seam; the corrected one returns 5,407
values/types. All 35 HMI proof pins and the PLC image stay unchanged. Fresh
full AB/root gates and a new sealed retry are next, under O3. No commit/push.

### 2.13 S4b exit: E1–E9 pass together

The [accepted V6.10 runtime](Evidence/AB_S4B_OWNER_REVISION_RUNTIME_2026-10-29.md)
passes 41 candidate cases/87 exact raw-read replays, 2,538 observer samples/
zero Bad, four configuration pages/1,100 exact scalars, 5,407-path idle
equivalence/acquisition and all 31 LIVE desktop views (seven modules, three
bus nodes). Maximum mapped effective age 255.856 ms. TASK median 966 µs,
cumulative maximum 8,974 µs/zero overlaps from 7,135 monitor observations plus
20 final samples. Exact image Capacity remains 66%.

Genealogy, five exact original documents, 31 baseline cases, MANUAL/idle/logout,
final checks, preflight and baseline timing pass; no dumps or forbidden
operations. The first Capacity precheck refusal and subsequent collector-gap
attempt remain sealed separately. The corrected collector retains scalar
validation; no proof, freshness, retry, type or value rule is weakened.

S4b is closed at its Echo/software scope. O1 now permits the stage-exit commit
and push, excluding unrelated edits. Next is S5 on this accepted image, then
S6 retirement/host services and inactive-contract activation. Physical S7
remains deferred under O2.

### 2.14 S5 automated runtime: C12 owner witness pending, 2026-10-30

The [sealed runtime](Evidence/AB_S5_GATEWAY_AUTOMATED_RUNTIME_C12_PENDING_2026-10-30.md)
passes all 12 automatic C1–C11/C13 cases through the packaged Dart gateway:
seven-module discovery, login success/refusal, mode and CM commands,
configuration edit/exact restoration, four-page/1,100-scalar oracle comparison,
foreign-root/stale/duplicate and all 39 read-only refusals, and gateway
STALE/DOWN/LIVE recovery without replay. Independent equivalence and raw
capture replay pass on 5,238 occupied values. Capacity is 66%; TASK median
943 µs, cumulative maximum 7,759 µs, zero overlaps. Genealogy, the five original
documents, 31 baseline cases, final checks and preflight pass after rollback.

The owner confirmed availability for C12, but no Chrome checklist arrived
during the sealed 20-minute window. Gateways then closed and rollback ran.
C12 remains unproven; the qualified-session result is false. No S5 commit or
push occurs before that owner check. Next is a freshly guarded owner-browser
follow-up on the same image/source/package, followed by the normal rollback;
S6 starts after S5 exits. O1–O9 stay decided, including standing O3.

The run found and fixed a real publication defect: canonical `WriteRevision`
used the static build hash while typed ingress validates the live configuration
owner. The [correction](AB_CANONICAL_PUBLICATION_S5_WRITE_REVISION_CORRECTION_2026-10-30.md)
changes exactly two generated assignments; layouts and initial Tags stay
identical. Candidate ACD `95E1C514…A586012`, source `979DD73C…105A162` pass both
v38 target builds/read-backs and fresh Studio Capacity. All 2,357 AB, 777 HMI
(12 skipped), 74 root tests, analyzer, locked dependencies, spec/contracts and
strict consistency pass. Earlier precheck, CLI, simulated-air, stale-revision,
startup and monitor-handshake attempts remain separately sealed.

### 2.15 Owner browser observations and idle connections, 2026-10-30

The [owner follow-up](Evidence/AB_S5_GATEWAY_OWNER_CONNECTION_ATTEMPT_2026-10-30.md)
records the four basic checks as reported passed, plus two defects: a brief
disconnect on manual movement and an initial connection error before recovery.
Gateway logs confirm real upstream CIP disconnects. The browser's native
logged-out boundary failed; rollback retained its active-session guard. After
the owner explicitly logged out again, the continuation restored genealogy,
all five documents, 31 baseline cases, final checks and preflight. The original
failed session result remains unchanged. S5 is still open.

A read-only Echo probe reproduced peer closure of an unused connection after
a 100-second idle interval while a periodically read connection stayed usable.
The transport correction opens one fresh serial-pinned command connection per
payload/commit pair and closes it afterward. The read pool renews an observed
idle peer close before starting a whole-row lease. It does not retry an
interrupted row, timeout, malformed reply or command. A second native probe
observed all four idle sockets closed, then successfully renewed/read all four
against the original serial. All 781 HMI tests pass, with 12 existing skips.
Fresh package/browser/delayed-command qualification is required before S5 exit.

The [first corrected-package attempt](Evidence/AB_S5_GATEWAY_IDLE_LOGIN_ATTEMPT_2026-10-30.md)
reached seven-module LIVE and accepted LOGIN acknowledgement 11, then lost the
client LIVE state while waiting for its provider result. No upstream CIP
disconnect appears in that run's gateway log. An old browser had also
reconnected, so the initial idle precondition is unproven. The fixture stopped
at C2; later command/browser cases did not run. Independent read/scan gates
passed at 5,212 occupied paths, and genealogy/five documents/31 baseline cases
were restored after read-only correlation recovered the fixture's own login
proof. A separate one/two-client read-only comparison kept all 80 samples
within the fast Good window. The login-transition cause remains open; next is
the unchanged write scope with existing opt-in frontend timing/freshness traces.

The [trace repeat](Evidence/AB_S5_GATEWAY_BROWSER_ACK_ATTEMPT_2026-10-30.md)
passed all 12 automatic cases, including clean 100-second idle startup and
100-second delayed movement. The owner reported the two-tab check passed with
no flicker. Its native witness nevertheless rejected absent acknowledgement
progress; independent subsequent request/ACK values remained 22. This mismatch
is unresolved, so C12 and S5 remain open. Independent read/scan gates passed on
5,238 occupied paths, with 7,759 µs cumulative TASK maximum and zero overlaps.
After the first baseline run timed out in HOME before the SFC hold case, an
unchanged full retry passed 31/31; final checks/preflight passed and genealogy
is restored. Failed outputs remain sealed. Next is a focused owner-browser
follow-up with read-only RPC/counter observation; unchanged automatic proofs
may be reused only with explicit source/image/package hash verification.

On 2026-10-31 the owner [clarified](Evidence/AB_S5_GATEWAY_BROWSER_WINDOW_CLARIFICATION_2026-10-31.md)
that the reply confirmed an earlier test. This explains the unchanged counter;
it is not evidence of a new command-routing defect. The former failed window
is preserved. The next session opens a fresh Chrome profile for a current,
owner-operated C12 check, retaining all existing native acknowledgement and
logout guards. Additional browser-RPC instrumentation was prepared offline but
is not needed or deployed for this clarification.

The [fresh-window attempt](Evidence/AB_S5_GATEWAY_BROWSER_WINDOW_EXPIRED_2026-10-31.md)
again passed all 12 automatic cases and independent read/scan gates. Its
two-hour owner window expired without a checklist; the automatic rollback
restored genealogy, all five documents, 31/31 baseline cases and final checks.
The later owner reply requests setup/login help, not acceptance. Supply those
details separately and reopen a fresh guarded session with the unchanged
package/image. No product correction, acceptance-rule change or S5 exit follows
from the expiry.

The next [owner two-tab check](Evidence/AB_S5_GATEWAY_TWO_TAB_FAILURE_2026-10-31.md)
failed: second-tab startup showed an error, then repeated connection transitions.
Native ACK advanced 22→33; the PLC stayed healthy and no upstream CIP disconnect
was recorded. All 12 automatic cases and independent read/scan checks passed;
rollback restored genealogy, five documents, 31/31 baseline cases and final
checks. Offline investigation reproduces a shared tier defect: a slow consumer
plus an excluding consumer becomes fast under separate set intersections.
Correct the merge to the highest actual demand (fast > slow > excluded), with
all nine pair combinations covered. This changes no client's selected tier,
freshness/proof/retry limit or write policy. Native browser acceptance remains
open after the offline correction.

The [shared-tier retry](Evidence/AB_S5_GATEWAY_TWO_CLIENT_TIMING_FAILURE_2026-10-31.md)
passed all 12 command cases, but its added read-only two-client prerequisite
caught nine non-LIVE transitions over two 20-second detail/overview phases.
It collected 68 secondary samples; ACK stayed 22. Chrome was not opened.
Snapshot waits of 1.96–2.11 seconds contained native source ages of only
0.18–0.21 seconds. The shared merge correction alone is insufficient. Separate
tier RPCs still expose intermediate profiles, and gateway queue time before
the native call is absent from the declared server-processing bracket.
Offline regressions reproduce both gaps. Install profiles atomically and add
only pre-read gateway waits to the existing processing envelope, preserving
source/leaf ages and post-acquisition transit. No budget/proof/retry/access
limit changes. Independent read/scan gates, genealogy/five-document rollback,
31 baseline cases and all final checks passed. S5 remains open.

The [atomic/queue retry](Evidence/AB_S5_GATEWAY_ATOMIC_QUEUE_RUNTIME_FAILURE_2026-10-31.md)
again passed all 12 command cases but recorded five non-LIVE transitions in
the two-client prerequisite, with 69 secondary samples and unchanged ACK22.
Its previous late-sample refusals did not recur during that probe, but LIVE
cadence remains insufficient. Chrome did not open. Independent reads/scan,
genealogy/five-document rollback, 31 baseline cases and final checks passed.
Test sharing concurrent acquisitions for an unchanged installed profile, with
per-caller processing overlap and no completed-response cache. Do not share
across profile changes, renew source ages, hide a failure or increase a limit.
The probe also retains phase/time details for each rejected link transition.

The [shared-read retry](Evidence/AB_S5_GATEWAY_SHARED_SNAPSHOT_RUNTIME_FAILURE_2026-10-31.md)
again passed all 12 command cases. Its two-client probe collected 115 secondary
samples (69 previously), with five non-LIVE transitions during detail activity
and unchanged ACK22. The phase/time records are retained. This does not meet
acceptance; Chrome did not open. Independent read/scan checks, genealogy/five-
document rollback, 31 baseline cases and final checks passed. Use the existing
native worker trace next, with unchanged implementation sources and a clearly
marked diagnostic executable. Repeat the same command/read vectors, skip the
owner window, preserve all limits and roll back. A diagnostic capture is not
a normal-package qualification or S5 exit.

The [native timing diagnostic](Evidence/AB_S5_GATEWAY_NATIVE_TIMING_DIAGNOSTIC_RUNTIME_2026-10-31.md)
passed all 12 command cases and reproduced three non-LIVE transitions, 117
secondary samples, unchanged ACK22. Post-command native execution maxima were
352 ms for snapshots and 71 ms for slow chunks, with snapshot queue at most
37 ms. Thirteen configuration-assembly operations and repeated configuration
hydration were recorded during the detail workload. Revision invalidation
incorrectly accepts saved-set `/ConfigRev` leaves; configuration-page RPCs
also hold later cyclic requests in their connection queue. Offline tests
reproduce both gaps. Restrict signatures to discovered module revisions and
give read-only configuration pages a separate serial service queue, retaining
prior controls and all write/tier ordering. Tests preserve real root/nested
Unit refetches and verify cyclic/later control progress while a page is held.
No value, quality, freshness, proof or retry limit changes. Independent reads/
scan, genealogy/five-document restore, 31 baseline cases and final checks
passed. Browser C12 was deliberately not attempted; S5 remains open.

### 2.16 Fresh two-tab checklist passes; timing/history defects, 2026-10-31

The [normal-package qualification](Evidence/AB_S5_GATEWAY_CONFIG_OWNER_RUNTIME_DETAIL_FINDINGS_2026-10-31.md)
passes all 12 automatic cases and the two-client prerequisite (121 secondary
samples, zero non-LIVE transitions, ACK22 unchanged). The owner performs the
fresh Chrome checklist without connection flicker; native ACK22 to ACK28 and
MANUAL/idle/logged-out boundaries independently confirm command progress and
logout. All independent native gates pass: 5,264 paths, seven modules, exact
value/type equivalence and replay, four configuration pages/1,100 scalars,
TASK maximum 7,759 microseconds and zero overlaps. Genealogy/five original
documents, 31 baseline cases, final checks and preflight are restored.

The owner also reports a tall blank PartSlide timing card which disappears,
and history rows repeatedly clearing/repopulating. These remain open; the
scoped C12 pass is not S5 exit. Read-only browser observation confirms slow
detail ages near 10 seconds, beyond the unchanged 7.5-second Good limit.
Timing reaches zero Good leaves. Fix the narrow timing-table layout and let
bounded background chunks continue between fast polls, retaining worker
scheduling fences, per-row proofs and all age/freshness limits. Require
regressions and a fresh normal-package native detail-stability qualification.

### 2.17 S5 exit with verified baseline recovery, 2026-10-31

The [corrected normal-package qualification](Evidence/AB_S5_GATEWAY_QUALIFICATION_2026-10-31.md)
passes all 12 automatic cases and owner-operated C12. The owner confirms the
compact scrolling timing table and stable history/timing in two Chrome tabs.
Native ACK22 to ACK26 and logged-out MANUAL/idle boundaries corroborate C12;
automated C5 independently proves movement and return. The extended read-only
probe retains 27 history rows and two timing rows in each client, 120 secondary
samples, zero row/link drops and unchanged ACK22. No freshness, proof, age,
retry or write-policy limit changes.

Independent gates pass: 5,264 occupied paths with exact values/types and raw
capture replay across seven modules; four configuration pages/1,100 scalars;
TASK cumulative maximum 7,759 microseconds, zero overlaps over 6,261 monitored
post-download observations plus 20 final samples. Fresh offline gates include
802 HMI passed/12 existing skips, analyzer, locked dependencies, package and
installer, gateway tests and 74 root tests. Unchanged PLC proofs transfer by
hash, including 2,357 AB tests and both v38 builds/readbacks.

The original session result remains failed: after downloading genealogy and
restoring all five original documents, its baseline fixture stops after 28
rows at START refused and restores its inputs/policy. A guarded MANUAL
normalization and one unchanged 31-case retry pass with a read-only witness;
all final checks/preflight/timing pass. A separate stage-exit record consolidates
native qualification and verified recovery without rewriting either failed
output. The first refusal's cause is not established; investigate the harness
readiness boundary during S6. No re-download, assertion change or added write
vector is used for recovery. Echo ends Run/not faulted, scanning, MANUAL/idle/
logged out, saved documents equal to live; no dumps/clears/clocks/power changes.

S5 exits at Echo/package scope. O1 authorizes its stage commit/push. Next is
WP6.1's current consumer classification, then canonical harness migration and
the final sealed oracle replay before collapse. O4/O5 host-service/persistence
decisions and O6's gated baseline switch remain in force. V2 stays inactive
until S6; S7 remains deferred under O2.

### 2.18 S6 native session ledger

Each session follows §4 under the standing Echo decision O3.

| Date | Record | Reached | Stopped at |
|---|---|---|---|
| 11-04 | [Echo re-baseline](Evidence/AB_S6_ECHO_REBASELINE_2026-11-04.md) | Echo found factory-reset and empty; genealogy pin downloaded, 31/31 baseline cases, preflight equal to the S5 baseline record, final checks and timing pass | — (no candidate; the genealogy baseline is restored) |
| 11-04 | [V6.11 host session](Evidence/AB_S6_HOST_SESSION_ATTEMPT_2026-11-04.md) | Candidate `A4B4FC78…` downloaded and audited; the Dart adapter discovered the host services natively; TASK maximum 7,767 µs, 0 overlaps | First host request refused (CIP 0x0F): the chunk's strings are published Read Only types. Genealogy restored, 31/31 |
| 11-04 | [V6.11 host session 02](Evidence/AB_S6_HOST_SESSION_02_ATTEMPT_2026-11-04.md) | Candidate `902831B4…` downloaded and audited; host requests accepted natively, restore jobs ran | The line document denied to the logged-out session (by design: no adapter login); the procedure now logs in first. Genealogy restored, 31/31 |
| 11-04 | [V6.11 host session 03](Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04.md) | **Pass.** Native restore of all five documents by the Dart adapter under the ENGINEER login; 21 event rows; both host-event rings captured on one state, 220/220 leaves equal; TASK maximum 9,112 µs, 0 overlaps | — (genealogy restored, 31/31) |

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

**O8 amendment, approved 2026-10-28.** The configuration-container fallback
read tier may change only as the approved
[CIP-only review](AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md)
specifies: existing configuration containers without exact hydrated replacements
use the declared 5/7.5/15-second metadata period/Good/expiry. Live identity,
capabilities, active alarms, counters and station freshness stay fast. Other
transports and all proof, retry, access and write rules remain unchanged.
Fresh exact-source rehearsal gates are still required.

**O9 amendment, approved 2026-10-29.** The
[owner-version contract](AB_CANONICAL_PUBLICATION_S4B_OWNER_REVISION_REVIEW_2026-10-29.md)
adds V6.10 protocol-2 owner rows for module discovery headers and the read-only
configuration view, with independent scan progress. Only those owner-protected
rows gain the declared proof bound within the existing one-second acquisition
deadline; protocol 1 retains its strict scan-period bound. Core values/types,
tiers, freshness, retries, access and write policy stay unchanged. All offline,
image, Capacity, rehearsal and E1–E9 gates still apply.

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

### 5.1 S4b — desktop gate closed (2026-10-29); checklist retained

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
- **O9 bootstrap:** before the first V6.10 download, the peer uses generated
  V6.10 manifest/owner-counter metadata over the hash-pinned native V6.8
  product bytes above. It records both hashes and marks the new metadata and
  Template handles as synthetic apparatus. Every existing product byte and all
  5,407 projected values/types must match. Scan progress stays dynamic; owner
  revisions are stable until their protected values change. This proves the
  client path, never the new controller ABI. The new-image native gates prove
  the actual Symbol/Template layout and PLC ownership.
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
- O9 changes the PLC generator and image. Fresh full AB discovery, both v38
  builds/read-backs and exact-image automatic Studio Capacity replace the old
  373-binding/2,339-test/65% transfer. The old result remains historical.
- 74 root tests; spec, contracts, strict consistency and whitespace.

**Native session S4b-Q** follows §4 with the sealed, freshly qualified V6.10
image and the unchanged write scope. `30315E6D…` remains the pre-O9 candidate.

| Gate | Pass criterion |
|---|---|
| E1 candidate cases | 41/41 (31 rows, 2 Access, 8 configuration) with exact restoration |
| E2 replays | 87/87 independent raw-read pairs; exact values and types |
| E3 observer | Zero Bad samples; Good values within their declared tier's Good limit (fast 1 s, slow 7.5 s, including O8); Uncertain rows payload-free |
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

S5 implements HMI and gateway code against the S4b V6.10 publication. Native
qualification also required the two documented write-revision assignment
corrections (§2.14), producing exact image `95E1C514…A586012` with the same
wire layout and both v38 build/read-back and Capacity gates. Its
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

C2/C3 distinguish command consumption from authentication. The existing native
access provider acknowledges LOGIN before its bounded hash work completes.
Both cases correlate `Access/LoginResultSequence` and wait for `LoginBusy` to
clear. C2 requires the expected user/level and no failure; C3 requires
`LoginFailed` and level zero; the owner also publishes its audit result. Its initial
mailbox acknowledgement can be Accepted. This clarifies the existing Core
login behavior (`OpcUaRepository.login`), without changing the PLC contract.

**Exit:** C1–C13 pass, and `/healthz` `writeAccess` matches each instance's
configuration.

### 5.3 S6 — Retirement, collapse, persistence and events

Order: WP6.1 → 6.2 → 6.3, with 6.4 (contract inventory under approved O4) in parallel; then 6.5 → 6.6
→ 6.7 → 6.8 → the native session.

**WP6.1 — Classify every legacy consumer.** Re-run the census script
(`Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Continuation/inventory_legacy_consumers_01.py`)
on the current tree. It found 107 direct consumers (54 tools, 53 tests) and 284
transitive ones. Extend it to assign each module one class by these rules; the
first match wins, and an unclassified module stops the step.

Implemented 2026-11-02 by `tools/fraktal_ab_legacy_consumers.py` in the AB
binding. The [review](AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md)
records the current counts and scope corrections: classify explicit retirement
owners/importers even without a direct legacy call, include the existing press
S3k oracle, and review standalone engineering probes without rewriting their
fixture-specific ABI checks. Import closure is conservative; dynamic imports
and external callers still need review before deletion.

| Class | Rule | Action |
|---|---|---|
| RT runtime projection and gateway | `fraktal_ab_projection`, `fraktal_ab_projection_replay`, `fraktal_ab_gateway`, `fraktal_ab_mailbox_probe`, their `test_` modules, `requirements-gateway.txt`, `HMI/test/live_ab_gateway_test.dart`, `HMI/test/live_ab_command_test.dart` | Delete in WP6.7 |
| MO migration oracle | `fraktal_ab_s<N><x>_{equivalence,reference,fixture_execute,revision_execute,lifetime_execute,io_execute}`, the press-prefixed S3k equivalent, `fraktal_ab_s4b_equivalence`, `fraktal_ab_canonical_equivalence`, `fraktal_ab_canonical_observation`, `fraktal_ab_paired_observation`, `fraktal_ab_mailbox_frame`, and their tests | Final sealed replay (WP6.3), then delete in WP6.7 |
| GN generator | `fraktal_ab_generate`, `fraktal_ab_resources` | Collapse in WP6.6 |
| AD host adapter | `fraktal_ab_host_events`, `fraktal_ab_sets`, `fraktal_ab_set_broker`, `fraktal_ab_medium` | Re-home in WP6.5 |
| HX acceptance harness | Every other tool `*_execute`, `fraktal_ab_press_parity`, `fraktal_ab_s9_*` | Migrate station reads in WP6.2; verify standalone engineering probes with no legacy station-read dependency |
| UT unit test | Every other affected `test_fraktal_ab_*`, including indirect imports of an affected owner | Review/rewrite canonical-structure assertions in WP6.6 |
| HL helper | Any other affected helper, including indirect consumers | Replace the legacy dependency with its canonical owner; a helper that serves only RT or MO follows them |

The output is `Specification/AllenBradley/AB_S6_CONSUMER_CLASSIFICATION_<date>.json`.
WP6.7's deletion step reads it.

**WP6.2 — Phase A: harnesses on canonical reads, legacy still present.**

The first migration is the offline S9 repository-contract runner. It uses the
S1 decoder on sealed native captures and no longer imports the declaration,
projection, gateway or their synthetic fixture builder. The shared Dart
contract preserves all 124 case verdicts. Other HX owners remain open; this
offline runner needs no live-controller fallback.

- Every HX module reads through `fraktal_ab_canonical_reader.py` (S1) instead of
  `read_unit`, `read_layout` or `*_context_members`. Assertions are unchanged.
  `fraktal_ab_press_execute.py` loses its `read_layout` and `read_unit`
  definitions.
- Until the baseline switch (O6), a harness chooses its reader by discovery: a
  controller that publishes exactly one valid canonical manifest is read
  canonically; absence alone permits the legacy reader. A present malformed,
  unsupported or ambiguous manifest refuses rather than falling back. The rollback
  baseline is the legacy genealogy image, which has no canonical tree. This
  temporary dual path ends in WP6.7.
- Offline gate: every migrated harness replays its sealed captures with
  unchanged verdicts.

The shared `open_row_reader` entry point and row acquisition now pass offline
replay of all 5,264 occupied S5 leaves under their published owner/count guards;
see the [reader review](AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md).
This is infrastructure, not another completed HX migration. The press lifecycle,
private fixture observations and unchanged-assertion replays remain to integrate;
the stopped Echo service prevents native checks at this checkpoint.

On 2026-11-03, row bodies became bounded packets: at most 64 read services and
4,000 bytes. They are planned before the first proof and validated after it
closes; see the [evidence](Evidence/AB_S6_ROW_BODY_BATCHING_OFFLINE_2026-11-03.md).
The press accounting in the reader review finds that only 6 of the harness's 33
legacy facts have a canonical correspondence. The other 27 have no source after
R8, and 11 of its 15 rows mix both kinds in one read. Owner decision O10 (§6.3)
resolves this. The private facts move to an acceptance-only observation structure
in WP6.6. The press harness keeps its legacy reads until then, and loses
`read_unit`/`read_layout` when it migrates with the collapse.

The same accounting over all 24 HX migration modules
([evidence](Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03.md)) finds 15 with
private context facts. None of them can move onto canonical reads alone, so all
follow O10. Sixteen harnesses also command through the legacy Frame ingress,
which WP6.6 removes. Under O11 (§6.3) they command through the gateway's
`writeBatch` instead, using the shared harness command client. Legacy images
keep the Frame path until WP6.7 removes the legacy branch. The client
`fraktal_ab_harness_commands.py` passes offline, including against the real
Dart gateway server
([evidence](Evidence/AB_S6_HARNESS_COMMAND_CLIENT_OFFLINE_2026-11-04.md)).

**WP6.3 — Final sealed replay, before any generator change.** On the
pre-collapse tree, run once more:

- every MO test;
- all accepted image pins (byte-identical regeneration);
- every sealed capture replay.

Seal the result as `Evidence/AB_S6_MIGRATION_ORACLE_FINAL_REPLAY_<date>`, with
hashes. From then on, sealed evidence stays readable data, and its executable
replay ends by design.

Sealed 2026-11-04 as
[`AB_S6_MIGRATION_ORACLE_FINAL_REPLAY_2026-11-04`](Evidence/AB_S6_MIGRATION_ORACLE_FINAL_REPLAY_2026-11-04.md):

- All 494 tests in the 38 MO test modules pass.
- Of 17 accepted pins, 13 regenerate byte-identically. Four typed-ingress pins
  (S3k, S4a, press S3 exit, S4b V6.8) are superseded by the recorded S5
  write-revision correction. Each differs from its sealed source only in its one
  or two `WriteRevision` assignments, so they are not claimed byte-identical.
- Of 51 sealed capture replays, 40 reproduce as recorded. The other 11 are each
  explained by a recorded change, verified over its whole extent: grown glob
  scope with every sealed row present, the S5 `WriteRevision` field over 226
  pairs, the S3j reference correction, and an in-session S3D re-run.

No unexplained difference remains. The generator may now change.

**WP6.4 — Host-service contract inventory (approved O4).** The staged ConfigSet and
ConfigProvider inputs, the live-document keeper and the host-event sink are the
last consumers that need the station declaration and the legacy endpoints. For
example, `fraktal_ab_set_broker.py` maps keys through `gen.editable_values(app)`.
The approved host-service shape was reserved as V6.9, additive like V6.6.
O9 now introduces V6.10 first. Implement the host-service addition at the next
unused additive minor (V6.11 if no intervening version), retaining V6.10 owner
bindings. Do not downgrade the manifest or silently extend its existing type.
The O4 shape remains:

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
its inventory before WP6.5. O4 in §6.3 already approves the shape; no further
approval gates WP6.5 or the host-service part of WP6.6.

The [2026-11-02 inventory](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
now records the four services and their additional helper owners, current
endpoints, limits and preservation gates. Native descriptor/chunk layouts and
state vectors remain engineering work before emission; no V6.11 code or adapter
implementation is claimed by that inventory.

The [V6.11 wire draft](AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md)
(2026-11-04) fixes the layouts and the state table. Without the Python broker,
the operator's set command reaches the PLC first. The PLC opens a job and asks
a declaration-free host for its I/O, through one shared ingress per root. The
draft adds `ConnectionBytes` to the O4 row, so the PLC still publishes every
connection bound. The client binding, the generic ingress ST and V6.11 manifest
normalization pass offline
([evidence](Evidence/AB_S6_HOST_SERVICE_LAYOUT_OFFLINE_2026-11-04.md)). The Dart
decoder accepts V6.11 and agrees with Python on its content hash.

The generator now emits V6.11 under the `canonical_host_services` opt-in,
which no accepted declaration sets. It emits the table, the ingress, and the
HostEvents ring on its own owner revision. The ConfigSets service carries all
eight set operations. The owner parks the operator's command without an
answer, asks the host for exactly its input, and resumes the unchanged set
transaction within 1.8 s or refuses it. A load or export is fetched by key; a
list's catalog is published whole; a current export's line is rendered by the
host. These paths run on the emitted routines and tag initializers in the
executed-ST model ([evidence](Evidence/AB_S6_HOST_SET_SERVICE_OFFLINE_2026-11-04.md)
for five operations, [then all eight](Evidence/AB_S6_HOST_SET_OPERATIONS_OFFLINE_2026-11-04.md)).
The LiveDocuments jobs follow. A host keeps each document through a snapshot
job, which an operator's set command preempts. It restores each after a
download through a job that resumes as a silent owner pass: the access check
and the set transaction run, with no operator acknowledgement, and the
verdict returns on the job ([evidence](Evidence/AB_S6_HOST_LIVE_DOCUMENTS_OFFLINE_2026-11-04.md)).
The PLC side of every V6.11 host service is now in place offline, and the
adapter (WP6.5) comes next.

**WP6.5 — Declaration-free host adapter.**

- One process per controller instance: `fraktal_host_adapter.exe`, from
  `FraktalCore/HMI/gateway/bin/fraktal_host_adapter.dart`. It was first built
  in Python from the AD modules, then ported (see the status below). It
  discovers through the S1 reader and the host-service bindings, and serves
  three things:
  - configuration sets and the provider, with `FileStore` unchanged at
    `%LOCALAPPDATA%\Fraktal\ConfigSets\<serial>-<root>`;
  - live documents re-applied after a download, through `FileMedium`;
  - HostEvents delivery, with durability, cursor and deduplication unchanged.
- It writes only through the versioned host-service endpoints and uses nothing
  from `fraktal_ab_declaration` or `fraktal_ab_generate`. The Python adapter
  had a test that asserted this. The Dart executable cannot import them at
  all; only its tests drive the Python bench.
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

Status, 2026-11-04 ([evidence](Evidence/AB_S6_HOST_ADAPTER_OFFLINE_2026-11-04.md)):
- **Done offline.** The adapter answers every set job and keeps and restores
  every live document, against the emitted controller code with real store
  and medium folders. What it renders from published facts equals the
  engineering code's rendering. It imports neither the declaration nor the
  generator, and the declaration-free host parts moved out of the engineering
  modules. Its pylogix port is tested against synthetic Templates.
- **Ported to Dart** (owner decision, 2026-11-04;
  [evidence](Evidence/AB_S6_HOST_ADAPTER_DART_OFFLINE_2026-11-04.md)). The
  adapter now ships like the gateway, as `fraktal_host_adapter.exe` beside
  it. The tray supervises it from an instance's optional `host_adapter.args`.
  The Python adapter is retired. The Dart one answers the same scenarios
  against the emitted controller code, through its real CIP port over
  synthetic Templates as well as through plain values. Its request bytes
  equal the engineering encoder's, and its store and medium files equal the
  Python ones, in both directions.
- **Candidate prepared** (2026-11-04;
  [evidence](Evidence/AB_S6_HOST_CANDIDATE_OFFLINE_2026-11-04.md)). The
  pre-collapse V6.11 profile `fraktal_ab_genealogy_s6_host_demo` builds on
  both v38 targets, passes the access audit and fits (70%). Its first v38
  builds found two defects the offline gates passed:
  - a BOOL comparison operand, now caught offline by
    `fraktal_ab_st_bool_operands`;
  - a revision guard too long to compile once it accepts the documents V6.10
    saved. Without those predecessors it would refuse them.
  The first native session then found a third: the host request's strings
  were Read Only types, so the controller refused the whole write (CIP
  0x0F). The request now has its own Read/Write string family, and the
  access audit checks every member nested inside a writable ingress
  ([evidence](Evidence/AB_S6_HOST_WRITABLE_STRINGS_OFFLINE_2026-11-04.md)).
- **Native** (2026-11-04,
  [evidence](Evidence/AB_S6_HOST_SESSION_03_RUNTIME_2026-11-04.md)). On Echo:
  - the Dart adapter discovered the V6.11 host services and restored the
    candidate's live documents natively, under the ENGINEER login;
  - the canonical HostEvents ring equals the legacy ring's projection, 220
    of 220 leaves on one coherent, wrapped state.

  The raw capture is sealed.
- **HostEvents delivered** (2026-11-05;
  [evidence](Evidence/AB_S6_HOST_EVENTS_DART_OFFLINE_2026-11-05.md)). The
  adapter reads each canonical ring under its owner revision. Its batch from
  the sealed native capture equals the legacy batch read natively. Its
  cursor and JSONL sink write the engineering collector's bytes. The work
  also found the gateway's projection refusing every V6.11 image (the ring's
  owner row), now fixed.
- **Session findings fixed** (2026-11-05; [evidence](Evidence/AB_S6_HOST_PERMITS_OFFLINE_2026-11-05.md)).
  - `SessionPermits` now means the session could load every document (the
    set gate and each value's write level), and a restore job is refused
    `ACCESS` on exactly that.
  - The adapter no longer retries a denied restore under the permission it
    was denied under.

  Both v38 targets build the change.
- **Open.** The native run of the ring reader and of the new predicate
  (S6-Q).

**WP6.6 — Phase B: collapse the generator.** In `fraktal_ab_generate.py`:

- **R8.** The canonical structures become the working storage. Remove
  `common_/module_/type_/unit_context_members`, the legacy contexts, the V5
  manifest tables (with their 768-field cap), the copy layer and the S3h
  observation frame (`canonical_observation_period_ms`).
- **R3.** Each module AOI writes its canonical leaf directly through InOut;
  `ScanCanonical` and `CanonicalDiagnostic` keep only per-instance calls.
- **R6.** Acceptance-only routines (native check vectors, first-scan bench
  vectors) are emitted only when a declaration enables them. Production
  declarations never do. Under O10 these include the fixture observation
  structure. The press harness migrates onto it and the canonical rows in this
  step. Its offline gate shows each of the 15 rows' predicates gives the same
  result over the new sources as over the legacy contexts.
- Under O11, harness commands move to the gateway command client in the same
  step that removes the Frame ingress. Every harness listed in the HX
  accounting as commanding through it switches; none keeps a Frame writer.
- **R5.** A production declaration selects one AUTO rendition (ST, SFC or LD).
  Acceptance declarations keep all three for the parity gate.
- The legacy staged service and Frame endpoints are removed. The new versioned host-service binding is the only
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

**C0 done, 2026-11-05.** The [collapse review](AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) splits WP6.6 into
increments C0–C7. Each is proven before the next starts
([evidence](Evidence/AB_S6_COLLAPSE_INVENTORY_OFFLINE_2026-11-05.md)).

- **Inventory.** The 320 context members are classified by their data flow in
  both S6-Q declarations: 108 private, 80 input, 62 output, 30 shared, 24
  published and 16 unused in the genealogy.
- **Gate.** `fraktal_ab_schema_identity.py` records each image's external
  surface from the L5X itself. Every difference must be declared, with the plan
  item that makes it.
- **Baseline.** The S4b image `30315E6D…` predates the V6.10 and V6.11 header
  additions, so no collapsed V6.11 image can equal it. The gate therefore
  compares each collapsed image with the pre-collapse image of the same
  declaration, recorded from `6898dfb87`: V6.11 genealogy, 94 published tags,
  and the press, 78. The native path-set comparison stays S6-Q's.
- **Findings the wording above does not show.**
  - The header's V6.3 `Services` rows name the staged request, so removing the
    staged endpoints is a new minor, V6.12.
  - Two V5 tables are named by the canonical command binding and stay.
  - The configuration revision is a hash of legacy content. Decision O12
    (§6.3, approved) redefines it, as increment C0b before C1: every later
    increment changes the declarations that today's revision hashes.

**C1 done offline, 2026-11-05** ([evidence](Evidence/AB_S6_COLLAPSE_R3_OFFLINE_2026-11-05.md)). Behind the S6-Q
opt-in `canonical_collapse`, each type AOI writes its own canonical leaf:
its state, `FaultActive` and command timing rows. The copy lines are gone.
The legacy branch every other declaration uses is unchanged byte for byte.

**C2 done offline, 2026-11-05** ([evidence](Evidence/AB_S6_COLLAPSE_C2_OFFLINE_2026-11-05.md)). Eight Unit and chart
members the publication copied unconditionally are stored at their canonical
paths. Every reader and writer names those paths, and the copies are gone.

**C3 done offline, 2026-11-05** ([evidence](Evidence/AB_S6_COLLAPSE_C3_OFFLINE_2026-11-05.md)). Each module's
context is its AOI instance: its members are the type AOI's parameters, and
the instance tag carries its initial values. The context tags and types are
gone. Narrowing to locals waits for C4's O10 structure.

**C4a done offline, 2026-11-05** ([evidence](Evidence/AB_S6_COLLAPSE_C4A_OFFLINE_2026-11-05.md)). O10's fixture
observation is declared per surface and emitted as one Read Only structure,
copied inside the canonical generation's odd window, so one generation proof
covers it with the canonical rows. The press collapse observes the 29
private facts its harnesses assert. Both collapse declarations drop the S3h
frame. **C4b is done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C4B_OFFLINE_2026-11-06.md)):
the press readers use O10 plus exact canonical aliases under the same scan
proof; 86 accepted native-state replays preserve all accounted facts and the
unchanged row predicates. All 2,574 AB tests pass, both v38 targets build/read
back, and fresh Capacity remains 61%. Other HX profiles must account their
extra facts before activation; their command/launcher migration remains with
C5/O11 and S6-Q. **C4c is done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06.md)):
a code-derived plan keeps external/fixture facts as parameters, moves private
module state to locals and removes unused fields. Defaults and instance
initialization survive compiled read-back; distinct signatures name distinct
AOI layouts. All 2,584 AB/85 root tests and both v38 preparations pass; Capacity
is 60% (1,914,768/3,145,728 Blocks). The C4a?c press/offline scope is complete;
remaining HX/O11 migrations and integrated native S6-Q stay open.

**C5a done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06.md),
[working notes](AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)). Collapsed press
commands use O11 writeBatch through an owned, package/serial/root-pinned Dart
gateway; their ACK and numeric refusal key are independently read over CIP.
O10 V2 permits native member selection under the unchanged strict scan proof.
The press gains the approved V6.7 counter bindings: its frozen S3 parent is
V6.6, and C4b's earlier replay supplied those bindings synthetically. This
closes a metadata prerequisite, not a native acceptance gate. All 2,612 AB and
85 root tests pass, both profiles build/read back on both v38 targets, and the
schema/token/default/access proofs pass. Capacity is 60% genealogy
(1,915,620/3,145,728 Blocks), 46% press (1,447,072/3,145,728). No controller
operations were performed; the legacy declarations remain byte-identical.

**C5b1 done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B1_OFFLINE_2026-11-06.md)).
The capture/configuration slice uses typed Core requests, live revisions and
PLC-published refusal keys, with independent O10 value/audit checks. The
read-only viewer uses the existing Dart `readConfigurationPage` RPC and proves
START cannot commit. The S6-Q press gains the approved V6.8/V6.10 publications;
its fixture gains ten facts (40 total). All 2,629 AB and 85 root tests pass,
both v38 builds/read-backs/access/defaults pass, and schema/token proofs pass.
Press Capacity is 49% (1,554,428 used / 1,591,300 available / 3,145,728 Blocks).
Genealogy is byte-identical to C5a and retains its hash-bound 60% qualification.
No controller operations or scan measurement ran. The six native audit fields
are absent from old captures; their native acceptance remains S6-Q. The
remaining set/host lifecycle is C5b2; this does not qualify other HX consumers.

**C5b2 done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B2_OFFLINE_2026-11-06.md)).
The set fixture and shared collapsed restore branch use the Dart V6.11
adapter, an owned pinned child and an isolated copy of original documents.
Operator commands use O11; canonical reads and raw O10 records independently
verify results, store receipts and restoration. All 2,664 AB / 85 root tests,
75 focused checks, 25 replay/writer/storage checks and 44 Dart tests pass.
The press enables the approved V6.11 host jobs (75 O10 facts), passes both v38
builds/read-backs/access/defaults and fits at 54% (1,703,672 used / 1,442,056
available / 3,145,728 Blocks). A frozen flag-only reference has 65 unchanged
other routines and the fixture's exact 35 fact copies. Genealogy remains
byte-identical and retains its hash-bound 60% qualification. No controller
operations or scan measurements ran. Remaining HX migrations are C5b3;
Frame/staged retirement and V6.12 remain C5c. C6/C7 and native S6-Q still follow.

**C5b3 policy slice done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B3_POLICY_OFFLINE_2026-11-06.md)).
The Phase 6 access/data-class/shelving fixtures use O11, independent canonical
policy/configuration/text reads and 27 additional exact O10 fields (102 total).
The original 43 case-site predicates retain all value, no-change and timing
conditions after acquisition/lookup normalization. Native serials/extents and
all 27 additions replay from the 86 accepted captures; annotation/annunciation
replay also passes. All 2,681 AB, 85 root and 63 focused tests pass, as do both
v38 builds/read-backs/default/access/SDK audits. Studio Capacity is 54%
(1,713,204 used / 1,432,524 available / 3,145,728 Blocks), +9,532 used. Exactly
27 fixture copies add 411 ST tokens; 65 other routines are unchanged.
Genealogy remains byte-identical with its hash-bound 60% qualification; the
unchanged shipping Dart packages retain C5b2's hash-bound 44-test qualification.
No controller operation or scan measurement ran. This completes the policy
slice only: Phase 5 metrics/reports, Part/genealogy/inherited runners and the
standalone canonical press launcher still need C5b3 accounting/migration.
Frame/staged removal remains C5c, then C6/C7 and native S6-Q. The base press
excludes controller metrics, so the original/migrated shelving preflight both
refuse its required reason-21 event. A dedicated shelving acceptance profile
remains before positive native shelving acceptance; no guard is relaxed.

**C5b3 shelving acceptance profile, offline follow-up.**
`fraktal_ab_press_s6_shelving_echo38` inherits the collapsed press and changes
only `SystemHealth.require_controller_metrics` to true. This is an
acceptance-only requirement: the existing health/alarm owner opens reason 21
after its first-sample guard. The normal press retains its exclusion. The
original shelving eligibility and restoration guards remain unchanged. See
the [offline qualification](Evidence/AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06.md).
Positive native shelving remains S6-Q after C7; this profile is not a native
acceptance result. Its exact image must be regenerated and qualified after
the remaining collapse increments.

**C5b3 Phase 5 metrics and reports done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B3_PHASE5_OFFLINE_2026-11-06.md)).
`fraktal_ab_phase5_execute.py` reads OEE, machine state, run styles, profiler,
command timing, state flags and system health from canonical CIP rows and O10
observations (141 facts total, +39 in `FRK_T_PressFixtureV2_2A276D94`), with zero
direct legacy projection or layout calls and all 21 row predicates and 16 wait
predicates preserved. Cylinder `TimCount`/`TimLast` read from canonical
`Timing/Rows[1..2]` aliases; all 39 added private facts and all Phase 5
canonical metric/report views replay identically across all 86 accepted press
captures. Both v38 press profiles (`fraktal_ab_press_s6_collapse_echo38` and
`fraktal_ab_press_s6_shelving_echo38`) build/read back on both targets, pass
SDK/access/default/schema/token proofs, and fit at 54% Studio Capacity
(1,726,208 and 1,726,244 Blocks, +13,004). Phase 5's `health_rows` reason-21
precondition is proven offline on the shelving profile while the normal press
retains its metrics exclusion. Part, genealogy/inherited runners and the
canonical press launcher remain in C5b3 before C5c/V6.12, C6/C7 and native S6-Q.

C5 continues in two dependent increments without changing its exit gate:
remaining HX fact/read/command migrations and the public host-adapter/set
lifecycle first, then Frame/staged endpoint removal and V6.12 readers. The
press's capture client now has the read-view and owner-revision publications;
its Phase 6 set client and shared restore branch now use the host-service publication
and Dart adapter lifecycle. Other HX consumers still need migration. A shared
command facade alone does not qualify a whole legacy harness. C6/C7 and
integrated native S6-Q remain after C5.

**WP6.7 — Delete and update the gates.**

- Delete RT and MO per the classification file. After the baseline switch,
  delete the harnesses' legacy reader branch and the legacy baseline fixture.
  The `websockets` pin in `requirements-gateway.txt` moves to a harness
  apparatus requirements file first, because the O11 command client needs it.
- Re-run the census; it must report zero direct legacy references.
- Switch `tools/check_ab_spec.py` and `tools/check_ab_contracts.py` to V2.
  Update `tools/check_consistency.py` wherever it names a deleted file, and the
  AB README's test counts.

**WP6.8 — Documents and activation.**

- **Part III.** Apply the [amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md):
  - §1, §2.1 and §4.1: reference profile and L24ER retirement;
  - §3.8 type map V2; §3.10 exposure; §3.10.2 read-only configuration;
  - §3.13 coherence; §11.1 topology.

  Add the host-service minor following V6.10.
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

**Native session S6-Q** follows §4 under standing Echo authorization O3. The
candidate sequence is the collapsed genealogy-S4b image, a dedicated shelving
acceptance image, then the normal collapsed press image. The added shelving
image supplies a real warning through the existing optional health requirement;
it preserves the normal press's platform exclusion. Each image retains fresh
guards, backup, Capacity, build/read-back, scan and rollback gates.

- **Genealogy gates:**
  - the 41 candidate cases on canonical harnesses;
  - E7 desktop;
  - gateway cases C1, C4, C6 and C11;
  - native schema identity (path set and types equal to S4b);
  - Capacity and scan (< 10,000 µs, zero overlaps).
- **Press gates:** the 47 rows, with the seven core cases in each of ST, SFC and
  LD; schema identity; Capacity and scan.
- **Shelving phase:** run the unchanged Phase 6 shelving cases with
  `FRAKTAL_AB_DECLARATION=fraktal_ab_press_s6_shelving_echo38`, independent
  canonical/O10 observation, O11 commands and complete document/session
  restoration. Require the actual standing reason-21 event in preflight;
  never inject an alarm slot or weaken eligibility. Finish this phase before
  the normal press validation; end the session on the qualified genealogy
  baseline. The additional download is acceptance apparatus, not a production
  health-policy change.
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

- **O8 — configuration fallback tier, approved (2026-10-28).** The
  [230-path review](AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md)
  authorizes a CIP-only metadata heartbeat for published activation-static
  containers without exact hydrated replacements. Owner reply:
  “Approve CIP configuration heartbeat (Recommended)”
  (`call_a7b096025e8b4393802914b727457fab:0`). The broader temporary implementation
  remains reverted. Implement the optional capability and require fresh
  final-source rehearsal gates before native preparation.

**O9 — owner-versioned publication, approved 2026-10-29.** The owner answered
“Approve owner revisions (Recommended)” to
`call_440bb9c9544b4ea78c5cfdde3f44d706:0`, approving the
[V6.10 contract](AB_CANONICAL_PUBLICATION_S4B_OWNER_REVISION_REVIEW_2026-10-29.md)
and dependent offline work, including its explicit protocol-2 proof-bound
amendment and separate scan progress. O4's host-service shape carries forward
without a future schema downgrade. No acceptance or stage exit is implied.

**O10 — acceptance-only fixture observation, approved 2026-11-03.** The owner
chose “Acceptance-only vector (Recommended)” for the press harness's 27 private
facts. The [reader review](AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md)
accounts for them. In WP6.6, under R6, an acceptance declaration emits one Read
Only fixture observation structure. It carries exactly the private facts its
harnesses assert. The publication routine writes it under the same generation
counter, so one row proof covers canonical and private facts together. It has
no TC3 path, never enters the manifest, and no production declaration emits it.
Assertions stay unchanged. The press harness keeps its legacy reads through
WP6.2 and migrates with WP6.6; S6-Q proves it. Each further harness's private
facts are accounted the same way before they join the structure.

**O11 — harness commands through the gateway protocol, decided 2026-11-04.**
The [HX accounting](Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03.md)
found 16 harnesses commanding through the legacy Frame ingress that WP6.6
removes. The owner delegated the choice: “i leave the desision to you, decide
based on specification objectives and multi plc brand coherence”. Harnesses
command through the gateway's brand-neutral `writeBatch`. They send the nine
Core `HmiRequest` arguments, then `Sequence`, exactly as the HMI repository
does, through a loopback write-enabled instance (O3's `echo`). They observe
the acknowledgement and the machine through their own CIP reader.

- *Multi-PLC coherence:* the same command client serves TwinCAT, Siemens and
  AB gateways.
- *O9:* each brand keeps exactly one command encoder, in its gateway transport.
  There is no Python twin of the WP5.1 writer.
- *Acceptance:* commands take the operator's path, while observation stays
  independent of it.

Plant stimulus and fault-injection writes remain direct, declared test-build
writes. They are the simulated world, not commands.

**O12 — the configuration revision after the collapse, approved 2026-11-05.**
The owner chose option A (“ok lets do A”) after both options were explained.
Set documents carry `configRev`, which is
`LegacyContentHash[:6]`: a hash of the V5 tables, which are built from the
context member declarations that R8 deletes. Recommended, per the
[collapse review](AB_CANONICAL_PUBLICATION_S6_COLLAPSE_REVIEW_2026-11-05.md) §5:

- the revision becomes a hash of what gives a stored value its meaning: each
  editable value's record, scope, key and kind or type, plus the set schema and
  the model and line layout. Ranges, write levels and ordinals stay out,
  because the controller checks the first two at load and resolves keys
  itself;
- `LegacyContentHash` becomes that hash. Its path and the reader's
  `configRev = LegacyContentHash[:6]` rule are unchanged;
- the collapsed image also accepts every revision its pre-collapse build
  accepts, recorded once as constants by the generator at `6898dfb87`;
- a station declared outside this tree records its own with the pre-collapse
  tools before it upgrades, and carries them in its declaration.

The alternative, not chosen, keeps a frozen, unemitted V5 content function
solely to feed the hash. O12 lands as increment C0b, before C1.

C0b is implemented offline ([evidence](Evidence/AB_S6_O12_DOCUMENT_REVISION_OFFLINE_2026-11-05.md)). Each declaration accepts
exactly its own recorded revisions, bound to the document identity they were
saved under. A declaration whose values change meaning but still claims them
does not validate. The V5 header keeps its content revision until C6.

O1–O12 are decided. The later owner touchpoints include the C12 browser
checklist (owner-operated by design, P10) and any controller other than Echo.

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
| S6: WP6.1–6.8 | 3–4 weeks, plus the O4 review | 1 (S6-Q, three images including shelving acceptance) |
| S7: WP7.1–7.5 | 1–2 weeks after hardware | 1–2 on hardware |

Owner approvals and native sessions set the real pace. The plan avoids the
S4b pattern of one session per hypothesis: each session above runs only after
its offline gates, and the rehearsal peer where one applies, have passed.
