# Part I/II Split — Execution Notes (2026-07-02)

*Executes `PART_SPLIT_SPEC.md`. This note records the disposition of sections the spec's table did not explicitly assign, the one editorial rule added, and the audit result. Section numbering is **preserved across the split**: a clause extracted to the binding keeps its Core number there (`TC3 §x.y`), so no reference renumbering was needed.*

## 1. Dispositions beyond the spec table (all follow the table's principle: neutral-normative → Core; platform mechanics → TC3)

| Section | Disposition | Rationale |
|---|---|---|
| §2 | **Split.** Core keeps the platform-neutral requirements (§2.2 library/base-class contract, §2.3 timing, §2.5 source-control principle, §2.6 simulation, §2.7 time sync). TC3 §2 takes toolchain/versions (§2.1), library-distribution mechanics, project settings (§2.4), storage forms, and PTP-over-EtherCAT-DC mechanics. | The spec assigns "§2 environment/library **distribution**" to Part II — honored. But §2.2's base-class requirement, §2.6, and §2.7 are cross-referenced normative Core content (§5.7, §6.9, §8.8, §3.16 depend on them); moving them would make Core reference its own binding. Core §2 notes that §2.1/§2.4 live at TC3 §2.1/§2.4. |
| §10 | **Core**, with fieldbus specifics extracted: EtherCAT clauses (§10.1, §10.5 specifics) → TC3 §10; HAL, drivers/SIM, device wrapping, PLCopen motion model (§10.2–10.4, §10.6) stay — they are the platform-neutral I/O-abstraction and motion contracts. | Same concepts-vs-mechanics principle the table applies to §11.6–11.8. |
| §11.1 | Core keeps the neutral server requirement; TF6100 mechanics → TC3 §11.1. §11.2–§11.5, §11.9–§11.11 stay in Core (OPC UA is a neutral standard; only the TwinCAT server product is binding). | Consistent with "§11.6–11.8 mappings (concepts)" in the table. |
| §13, §14 | **Core.** Change management and IEC 62443 cybersecurity are platform-neutral. | Companion to "§1 objectives/versioning". |

## 2. Editorial rule added (recorded in Core §1.1 tagging convention)

Where a [TC3] fragment is inseparable from an otherwise-neutral Core example (a single line of code, e.g. `__QUERYINTERFACE` in the §3.2/§3.7 walk examples), it **remains in Core carrying the tag and a pointer** to the binding clause; standalone platform-mechanics paragraphs (pragma blocks, `FB_init` code, TF6100/TwinSAFE/EtherCAT/TcUnit specifics) **move to Part II**, each opening with *"Binds Core §x.y."*

## 3. Promotion (per spec)

Annex I §I.9–§I.10 promoted to **Core §10.7 — Declarative routing model (help/nest graph & help affinity)**: position classes, the route graph as data, native multi-help affinity with role-primary resolution, reversal-by-construction rules, and the paid-once/tested-once requirement. Annex I §I.9/§I.10 remain the worked realization and now carry promotion notes; Annex I's Core/TC3 header names the promotion.

## 4. Annex headers (per spec)

Every annex A–I now carries, under its companion line, one line: *"Core concepts demonstrated: … / TC3 mechanics used: …"*. The companion line itself now reads "Companion to Fraktal Core (Part I) exercised through the Fraktal/TC3 binding (Part II); slots under Core §12."

## 5. Audit (spec step 3) — PASS

Two-document scheme: plain `§x.y` resolves in Core (1,032 refs), `Core §x.y` (50) in Core, `TC3 §x.y` (82) in TC3, annex-internal `§X.n` (28) in the owning annex. Indexed: **144 Core §-numbers, 22 TC3 §-numbers**. Unresolved: **0**. E_Reason band collision scan across the whole split set: **no collisions** (Framework 2001–2023 · Sep 10001–05 · Cyl 10101–03 · Axis 10201–04 · Robot 10301–10 · Clamp 11001). Framework companion docs (`Fraktal_Core_BaseClasses.md`, `Fraktal_QuickStart_and_Suite.md`): all refs resolve in Core. Full log: `AUDIT_TWO_DOCUMENT_SCHEME.txt`.

## 6. Repository layout (spec step 4)

```
fraktal-core/   Fraktal_Core_Part_I.md · Fraktal_Core_BaseClasses.md · Fraktal_QuickStart_and_Suite.md
fraktal-tc3/    Fraktal_TC3_Part_II.md · annexes/Annex_A…I (9 files, headers added)
```

The standing rule continues: all new platform text carries **[TC3]** and lands in Part II.

## 7. Lineage scrub (2026-07-02, post-split)

All references to proprietary source lineages — vendor/framework names, their internal API names, and their object names — were removed across Core, Part II, and the annexes (42 edits, verified zero residuals by scripted scan). Provenance is now grounded exclusively in public standards: **ISA-88 / IEC 61512** (tier model), **PLCopen** (handshake vocabulary, motion & safety FBs), **ISA-TR88.00.02 PackML / OPC 30050**, **ISA-95 / IEC 62264**, **ISA-18.2 / IEC 62682**, **IEC 62443**, and **OPC UA / IEC 62541** companion models. §1.4 was rewritten as the standards-grounding section; the frontmatter "Derives from" became "Grounded in"; the §3.14 hook catalogue dropped its legacy-mapping column; `ModeHandler`/`CommandHandler` are retained as this standard's own handler-role terms (defined in §1.6/§3.1 without attribution); necessary contrasts (e.g. §8.8's bare-numeric-code rationale) now cite "legacy handler frameworks" generically. Reference audit re-run after the scrub: PASS (1,048 plain + 50 Core + 82 TC3 + 28 annex refs, 0 unresolved; reason-band collision scan clean).

## 8. M1 feedback amendments (2026-07-02) — implementation decisions made normative

First compile-driven feedback from the `fraktal-core` implementation, folded into the specification per §13 (each clause names the §1.1 objective it serves):

| Amendment | Where | Objective |
|---|---|---|
| `I_Module`: no `ErrorID` property (number lives only on the PLCopen output); `GetFaultSummary : ST_Diagnostic`; transactional `PrepareRecipe`/`CommitRecipe`/`AbortRecipe` | Core §3.2, §3.8 | O3 one reason record in one place · O4 atomic changeover reaches every child · O8 compiles on any platform |
| Command-bearing tier interfaces use the same `ExecuteCommand(Command : DINT)`/`AbortCommand()` vocabulary; values are validated per §5.6; status is published through `ST_ModuleStatus` | Core §3.2, §2.2 | O4 one interface for every type · O2 no tier-specific synonym or PLCopen-name collision |
| Base-class extension points **are** the §3.14 hooks (`OnAbort`/`OnCyclic`), base-first | Core §2.2 | O2 one hook contract to learn · O1 |
| Inherited conformance rows (T1/T4 + T2/T6 mechanisms) proven once in the base suite; types **shall not** re-test them | Core §5.7 | O1 verification paid once at the owning level |
| `E_Reason` band extensibility: framework enum non-strict, type bands as constants, registry is the collision authority | Core §8.8 | O3/O4 one number space · O8 any enum semantics · O1 no central enum churn |
| `F_Now()` clock helper; pragmas on base classes ⇒ exposure by inheritance; `fraktal-core` named as reference implementation | TC3 §2.7, §3.10, §2.2 | O1 zero exposure/timestamp code per type |
| Annex A generic-getter note aligned with amended §3.2 | Annex A §A.3 | consistency |
| Framework reason numbers pinned (`2001–2006`) + self-test sub-range `2900–2909` (`TEST_FAULT`=2901) | Core §8.8 registry (previous session step) | O3 registry = single truth |

Reference audit re-run after the amendments: see `AUDIT_TWO_DOCUMENT_SCHEME.txt`.

## 9. Amendment: step & command timing capture (2026-07-02)

New **Core §8.11.4** — the cycle-time profile: per-command timing is captured in `FB_ModuleBase` with one inherited `_M_TagCommand` line per type; the cycle profiler consumes the existing §6.5 step record, so the record that powers the stall walk also powers the time chart. Fixed bounded structures drive generic HMI waterfall/Pareto views and the `CYCLE_TIME_DEGRADED` maintenance path. Objectives: O1 (capture once), O3 (time explained like stalls), O4/O8 (neutral structures).

**§9 addendum — time classification (same date):** Core §8.11.4 gained clause **(f)**: every profiled step carries an `E_TimeClass` (`WORK` default; `WAIT_UPSTREAM`/`WAIT_DOWNSTREAM`/`WAIT_OPERATOR`/`WAIT_EXTERNAL`), declared with one enum argument on wait steps only. The profiler publishes per-class totals plus **`WorkTime` — the real cycle time** — and `WaitTime`; wait classes are the per-step attribution of §8.11.3 Starved/Blocked (auto-attribution is a *may*; explicit class wins; wait classes shall not mask process slowness). §3.13 waterfall coloured by class with a Total/Work/waits header. Implemented: `E_TimeClass` DUT, `Class` fields on `ST_StepTiming`/`ST_TimingRow`, `ByClass`/`WorkTime`/`WaitTime` on `ST_CycleProfile`, classified `FB_CycleProfiler`, extended `FB_Timing_Tests`. Objectives: O1 (zero cost on non-wait steps), O3 (slow vs starved distinguishable by construction), O4/O8 (fixed neutral structures).

## 10. M2–M4 amendments (2026-07-02) — the lifecycle family completed

Eight Core amendments accompany the final implementation milestones (objectives in brackets): §3.8 **SchemaVersion is the first `UINT`** of every ParCfg/record, enabling one generic provider [O1,O4]; §6 intro: **the Unit's run is a §6.1 command** (Start/Stop = issue/complete) [O2,O4]; §6.9: **a stall is a pending reason, never a fault** — the fault path is the awaited module's Error, adopted instantly via §8.2 [O3]; §3.14.4: **`OnModeExit` return semantics** fixed (0 = consent to E-stop cancel, >0 = graceful hold; commit on leaving BUSY) [O2]; §8.11.4(f): **Starved/Blocked derived from the step's wait class** — one declaration, two views [O3]; §6.5: the step record carries `E_TimeClass`; §5.7: **T7 proven once** in `FB_DeviceConnectorBase`; §2.2: the base-class clause now names the full lifecycle family (`FB_UnitBase`, connector base, local provider). Implementation delivered: `fraktal-core` library (Unit/connector/provider), `Fraktal_Modules` (cylinder CM, clamp EM, sim plant model, band constants per §8.8), seven TcUnit suites in one gate. Reference audit re-run: PASS.

## 11. Pre-HMI amendment (2026-07-02): the HMI contract is data

New **Core §3.10(a′)**: properties/methods are invisible to the exposed namespace, so everything a generic client renders **shall** be published as data — the framework `ST_ModuleStatus` mirror (name, tier, state, live §6.9(a) diagnostic, tile flag), refreshed by the bases [O1: zero exposure code per type; O3: the tile message is always the best available sentence; O8: rebindable structures]. New §3.13 **discovery & binding** bullet: module marker = the `Status` member; Unit extras (Pending, CurrentStep, History ring, counters, Decision, profiler); write surface deliberately narrow with §7.6 release gating declared a precondition for HMI manual functions. Implemented (mirror, §6.9(a) ring, §8.11 counters) and proven in `FB_Hmi_Tests`; bind table in `fraktal-core/HMI_CONTRACT.md`. Reference audit re-run: PASS.

## 12. §8.3 alarm & event history (2026-07-04)

§8.3 expanded to the full event contract: record with **duration** and synchronized stamps; **AUTO_RESET vs MANUAL_RESET** classes (manual blocks the Unit's `Start` until a deliberate, release-gated operator reset — the §9.3 no-self-re-enable principle at the event layer); automatic fault capture from the §8.2 rollup (event = diagnostic + lifecycle, one authoring); per-Unit active list + closed ring browsable over OPC UA; **`I_EventSink`** for historian/DB adapters (interface normative, implementations deployment-deferred); ISA-18.2 mapping. Objectives: O1 (auto-captured, one call for manual events), O3 (durations + same §8.8 vocabulary), O7 (blocking class never self-clears). Implemented + tested in fraktal-core; audit PASS.

## 13. §7.7 user access levels (2026-07-04)

Access = the *who* release dimension, ANDed with §7.2–§7.6. Levels/actions enums; per-station policy as persistent station config with **fully-open shipped default** (locking down is a deliberate commissioning decision, §14 checklist) [O1/O6]; per-function manual override via §7.6 [granularity]; `I_AccessProvider` + local default, data-driven login (§3.10(a′)), secret hygiene, idle logout, §8.3 audit events [O3]; PLC re-checks every gated entry — client never trusted [O7/§14]; §8.9 shelving roles now reference §7.7. Implemented + tested in fraktal-core (95 files, gates PASS, audit PASS).

## 14. Fieldbus topology & I/O diagnostics view (2026-07-04)

New Core **§10.5.1** (platform-neutral) + TC3 **§10.6** (EtherCAT/ADS binding): a physical bus tree — nodes (master→slaves→terminals) with a neutral `E_NodeState` (OFFLINE/INIT/PREOP/SAFEOP/OPERATIONAL/FAULT) and I/O channels (digital on/off, analog value+unit, direction, quality/forced) — **auto-detected from the fieldbus master's own diagnostics** at runtime (not hand-authored), published over §3.10 and rendered as a second HMI tree (§3.13) with node/channel status colouring. Forcing a channel is gated by §7.6+§7.7 and logged (§8.3). Maps to the logical HAL (§3.6): the module first-out and the bus-node view are two lenses on one fault. Objectives: O3 (diagnose at the wiring, one vocabulary), O4/O8 (neutral node-state so non-EtherCAT buses map on), O1 (auto-detected, no per-node HMI code). HMI: fieldbus repository interface + sim + topology tree widget (Flutter).

## 15. §7.6.1 manual command surface (2026-07-04)

Manual commands = a module concern surfaced on the module detail view (contrast §10.5.1 channel force = fieldbus concern). Self-describing catalog per module (O1); single gated path — MANUAL mode + §7.6 release + §7.7 MANUAL access — routed through the command surface so interlocks defend it; §8.3 audited; no mode-bypass override (whole Unit goes to a known-safe state first). Base classes carry the catalog + gate; concrete modules publish + consume. Tested. HMI panel visually distinct from force.

## 16. Annex J — MTP / IEC 63280 interoperability mapping (2026-07-10)

Benchmark against current standards (MTP 2.0 released 2026 by PI; IEC 63280 track) showed MTP is the industry standardization of Fraktal's own thesis (self-describing modules + orchestration over OPC UA). Annex J maps the concepts: root Unit ↔ PEA, external DCS ↔ POL, mode-selected sequences ↔ service procedures, §6.1 handshake ↔ 2658-4 service state machine (via the Annex F PackML projection), §3.10 Status mirror ↔ IndicatorElement DataAssemblies, §3.8 config ↔ ServParams, §8.3 alarms ↔ MTP alarm aspect. Honest mismatches recorded: flat PEA set vs Fraktal's recursive forest (export roots only), process-vs-discrete orientation, 2658-2 P&ID-style HMI vs Fraktal's data-driven tree, Fraktal-only surfaces (§7.8 release reports, §7.6.1 manual catalog, §10.5.1 topology) stay on Fraktal's own OPC UA surface. Export is engineering-time projection of the existing self-description — no runtime instrumentation added. Element names flagged for verification against the licensed 2658/MTP 2.0 sheets. Core §11.7 + TC3 §11.1 cross-reference the annex; audit extended to annex letters A–J. Objectives: O1 (one description, many consumers), O4/O8 (any MTP POL can orchestrate a Fraktal station).

## 17. §8.5.1 OEE model & trend samples (2026-07-11)

OEE as derivation, not instrumentation: time buckets (run/down/idle) + existing counters -> A×P×Q with per-factor validity; invalid factors omitted from the product, never assumed 100% (O7 — the UI must not flatter). Idle excluded from A by default with buckets published for re-derivation (deployment scheduling differs). Bounded PLC-side trend ring for the sparkline; historian owns long horizons. Reset gated (§7.7 DATA_WRITE) + audited (§8.3). HMI: exception-based colouring per ISA-101 practice.

## 18. §8.10 shelving hard rule + §8.8 registry enforcement (2026-07-12)

§8.10 amended: shelving = annunciation only, never control (Blocking/interlocks/release reports unaffected); SAFETY never shelvable; no rationalization record -> not shelvable. Implementation surfaced two latent §8.8 registry violations (duplicate constant; band squat on the axis CM range) — fixed, renumbered (basic cylinder 10110–10116), registered in the table, and the audit now scans GVL constants for duplicates and band squats so the registry is machine-enforced, not just prose.

## 19. §3.15.1a byte-transport abstraction + TC3 §3.15 (2026-07-12)

One platform-neutral `I_ByteChannel` under §3.15's connector archetype so TCP/serial device modules are written once and ported by swapping only the transport (O4/O8) — TC3 = Tc2_TcpIp, CODESYS = SysSocket/NBS, Siemens = TSEND_C. `FB_AsciiDeviceCM` pattern (framing, one-request, timeout⇒fault band 10401–10406, reconnect) + scripted sim channel makes device CMs hardware-free-testable. Protocol strings are Setup parameters verified against vendor manuals, never hard-coded folklore. Registry row added.
