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
   exceptions are the five D2 array-bound corrections, listed one by one. This
   holds for the genealogy fixture (4,437 paths) and the press declaration, in
   all three AUTO renditions.
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
+174,136 blocks over S3a. Runtime equivalence, active-condition coverage, native
scan measurements and candidate/rollback regressions remain open and require
a new current owner authorization. S3a's authorization is historical.
The owner's no-commit instruction remains active.

| Order | Surface | Notes |
|---|---|---|
| 3a | Unit core: `Decision`, `Catalog`, `ModePolicy`, `Supported*Published`, `AvailableModels` | Apply D2 bounds (`ModePolicy`, `SupportedModesPublished`, `SupportedRunStylesPublished` from 0) |
| 3b | CM/EM status, command timing, diagnostics | The PLC publishes `DescriptionKey`/reason codes, never rendered text |
| 3c | Sequence: `SequenceSteps`, `SequenceAnnotations`, `ActiveSteps`, step definitions | `ActiveSteps` from 0 (D2); keep fast-step history PLC-side |
| 3d | `AlarmLog` (Active, Ring, Meta), `StateFlags` | 1,469 paths, the largest surface; check structure-size limits from S0 |
| 3e | `Access` (`Policy.Required` from 0, D2), audit, data policy | Login stays plain PIN through the mailbox. The gateway's salt pre-hash used declaration data and is dropped; the PLC hashes, with `LoginBusy` covering latency |
| 3f | Configuration pages, `ConfigPersist`, `ConfigSets` listing | Pages come from the PLC on `QUERY_CONFIG` (as TC3), not assembled by a client |
| 3g | `Oee`, `OeeTrend`, `Profiler`, `SystemHealth` | Profiler is 900 paths; derivations are event-driven, not per scan |
| 3h | `Part` (+ genealogy), `HostEvents`, `Nameplate`, `SignalTower`/`MachineState` | Keep the existing single append owners; only the publication form changes |
| 3i | `Line` (calendar, shifts) | Line keys stay `line.`-prefixed |
| 3j | Fieldbus topology as its own published data product (TC3 `GVL_<Project>Fieldbus.Topology`) | Not a module root |
| 3k | `HmiResponse` / release report, `HmiRequest` mailbox | The mailbox stays the single write surface, with ordering per `OPCUA_TRANSPORT.md` |

**Exit:** full equivalence (4,437 genealogy paths, plus the press) on Echo;
31/31 regressions; rendition gate green.

### S4 — Generic Dart `CipSessionClient` and the desktop path

- **New** `HMI/packages/fraktal_opcua_client/lib/src/cip_session_client.dart`,
  exported like `ads_session_client.dart`. It covers:
  - EtherNet/IP session handling and a large Forward Open;
  - Symbol list (`0x6B`), Template reads (`0x6C`) and Read Tag Fragmented;
  - template-driven decoding plus the manifest lower bound and logical type;
  - `fraktal.opcua.snapshot.v1`, fast/slow tiers like `WebApiSessionClient`;
  - blocking work in a worker isolate, like `AdsSessionClient`.
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

1. **Migrate the harnesses.** 22 tools and 44 test modules read the generated
   contexts (`read_unit`, `read_layout`, `*_context_members`, the projection).
   Move every acceptance harness, including the 31-row regressions and the
   Part, tower and genealogy executes, onto canonical reads through the S1
   reader. The equivalence gate must stay green throughout.
2. **Collapse the generator.** Make the canonical structures the working
   storage. Remove the old contexts, the v5 manifest tables they described and
   the copy logic. Record the memory and scan savings.
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
| Harness migration volume (22 tools, 44 tests) | Migrate behind the equivalence gate before deleting anything |
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
