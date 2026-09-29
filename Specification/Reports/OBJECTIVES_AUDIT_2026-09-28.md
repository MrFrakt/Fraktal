# Objectives audit — the week of 2026-09-21 to 2026-09-28

Snapshot: **2026-09-28**. Scope: the 70 commits from `4203407` to `8d1715f`, judged
against Part I §1.1 (objectives O1–O10 and the trimming rule) and the normative
HMI/localization contracts. It extends [`OBJECTIVES_AUDIT.md`](OBJECTIVES_AUDIT.md)
(2026-08-02) for that week only; it is not a release certificate.

Method: each commit was placed against the spec clause it implements. That clause was
then checked in the source, and in the tests or evidence that should prove it. The
Allen-Bradley mailbox and gateway work (2026-09-21 to 2026-09-26) was checked at the
level of its recorded evidence and Part III gates, not re-derived line by line. The
TwinCAT Core work (0.7 to 0.12), the press, and the HMI were checked in the source.

Status: ✅ met · 🟡 gap or unverified claim · 🔴 contradicted.

## 1. What the week delivered

| Area | Commits | Clauses |
|---|---|---|
| AB command mailbox, gateway write path, browser commanding | `4203407`…`e29f09e` | AB §7.7, §11.2, §11.2.1; Core §14 |
| Theme contrast measured as painted; decorative themes | `891e220`, `3cc7023`, `5230064`, `8d1715f` | HMI_CONTRACT theming, §8.1 status colours |
| Type key published | `d14ade8`, `1791f9a` | LOCALIZATION §7.1 |
| Faceplates, containers, bound presentation specified | `5ff457e` | LOCALIZATION §7 |
| Core 0.7→0.12: set delete, data classes, line data, shifts, set listing | `e1c2a1e`…`fa2861a` | Core §3.8b, §3.8d, §3.8e, §8.5.2, §3.10.2 |
| Press: published release conditions, Ladder AUTO fix | `b26ad34` | Core §6.8, §7.2.1 |
| HMI: config tab, sets dialog, shift card, class levels | `74c81a7`…`ef19e56` | HMI_CONTRACT, Core §3.8b/d |
| HMI robustness: image decode, image dedup, keyboard, dialog lifetime, log | `8189167`…`fbcc0d8` | O10 |
| Pictures with placed controls (overlay container) | `1e3011c`, `ac97e9c` | LOCALIZATION §7.2, §7.3 |

## 2. Objective scorecard for the week

| Objective | Status | Verdict |
|---|---:|---|
| O1 Low effort | 🟡→✅ | Most of the week removes work: one mailbox for every command, parameter sets instead of hand copies, and line data held once and mirrored. **The gap:** `Status/TypeKey` was published with no reader, so twenty identical clamps still needed twenty layouts. *Closed in this pass* (§3). |
| O2 Easy to learn | ✅ | The Ladder AUTO fix keeps three renditions equivalent (parity gate). The editor's rule model is bounded and plain: tag, condition, value, state. |
| O3 Diagnosable | ✅ | The release conditions of the running rendition are published. Refused publishes, parameter-set records and dialog refusals name their cause. The durable HMI log located a UI freeze on the first report. |
| O4 Scalable | 🟡→✅ | Sets and shift history sit in the on-demand and slow tiers. **The gap:** a picture view could hold 64 controls × 8 tags with no read budget (§7.3). *Closed:* a 200-read budget is refused at publish. |
| O5 Flexible data | ✅ | Line data mirrors whole revisions from an owner over ADS. Sets export and import as JSON lines. **One limit** is open; see G1. |
| O6 Simulatable | ✅ | Every new HMI feature runs on the simulator; line data's mirror is proved over real ADS in TcUnit. |
| O7 Safe | ✅ | No new write path. Overlay controls use only the existing PLC-validated actions. A visible or enabled binding is presentation, never enforcement. |
| O8 Portable | 🟡 | Core 0.8–0.12 added five clauses that the AB binding does not implement. Part III did not say so, and Annex A still called the gateway and HMI "unbuilt". *The documentation half is closed* (§3); the binding half is G3. |
| O9 Engineering practice | 🟡→✅ | One source per fact held: stored images are deduplicated, the colour tokens reuse the semantic helpers, and theme groups are derived from each theme's finish. **The drift:** a published field with no reader (TypeKey), and stale figures in AGENTS.md and the HMI README (270 and 203 tests; a wrong Flutter pin). *Closed.* |
| O10 Robustness | 🟡 | Real defects were found and fixed: a use-after-dispose that froze the HMI, a keyboard focus loss, and decode on every rebuild. Publish now refuses rather than half-applies. **Open:** runtime evidence for Core 0.9–0.12 is not archived, and 0.12 was not run (G2). An export can produce a line that the mailbox cannot import (G1). |

## 3. Closed in this pass

1. **Type-scoped layouts (LOCALIZATION §7.1).** The HMI reads `Status/TypeKey`.
   - A module's tabs resolve from its own layout, else its type's layout, else the defaults. An override replaces the type's layout whole.
   - The editor publishes to "this module" or "every module of this type". Dropping an override falls back to the type layout, and the dropped layout is kept as a revision.
   - A type layout is stored under `type:<key>` and is never remapped as a path on import.
   - Because AB modules publish no key yet, the read-surface gate declares the field absent for AB. Those modules keep per-path layouts, the fallback §7.1 defines.
2. **Display class (§7.4).**
   - The Overview and custom views declare operating, maintenance or engineering.
   - The class shows as a badge on the view and is recorded in the export.
   - An operating view is refused a picture at publish.
   - A view stored without a class takes maintenance if it has a picture and operating otherwise, so no stored layout breaks.
3. **Read budget (§7.3).** A view above 200 bound reads is refused at publish, and the refusal names the rule.
4. **Revision history.** When a module's first override is published over a type layout, the "before" revision now records that type layout, not the defaults.
5. **Documentation drift.**
   - Part III Annex A now states that the gateway and HMI are built and proved.
   - It also lists every Core clause added since the Phase 4 base that AB does not bind yet.
   - AGENTS.md and the HMI README carry the current test figures and the real Flutter pin.
6. **Themes.**
   - The picker shows **Industrial standard** first and **Modern** after. The group is derived from each theme's finish, and stored indices are unchanged.
   - Two ANSI/ISA-101 greys, Process Grey and Process Grey Dark, are added, badged, and listed first. The light grey needs a deeper alarm red, because the seed's red fell to 4.4:1 on a tinted alarm banner over grey.

## 4. Ambiguities resolved in the specification

| Clause | Ambiguity | Resolution |
|---|---|---|
| LOCALIZATION §7.2 | "the image's intrinsic aspect ratio is part of the stored layout" — stored where? | The image is embedded in the layout, so its aspect ratio travels with it and is not recorded twice. Positions are fractions of the painted box, including the part a `cover` fit crops. |
| LOCALIZATION §7.3 | "A view declares a binding budget" — and one that declares none? | The standard budget of 200 bound reads applies. A declared budget may lower it, never raise it. |
| LOCALIZATION §7.4 | Which views declare a class, and what does a layout from before §7.4 get? | Views that can carry a picture (the Overview and custom views) declare one. Fixed PLC views are operating. An undeclared view with a picture is maintenance, and without one is operating. |
| HMI_CONTRACT theming | Which themes are "standard"? | Themes without a decorative finish. The ISA-101 claim is declared per theme, never inferred from a palette. |

## 5. Open gaps — plans and options

**G1 — An exported parameter-set line can exceed what import accepts (O5, O10).**
*Update, same day:* option B is implemented in Core 0.13.0.0 (IMPLEMENTATION_NOTES §142).
It is compiled; the runtime run is part of G2.
`ConfigSetDocument` renders lines of up to 480 characters, but `ST_HmiRequest.TextValue`
is `STRING(255)`. An export that holds a long record therefore cannot come back through
the HMI. The HMI refuses it by name and does not truncate it, but the round trip is
broken for that record.
- *A. Widen `TextValue` to 480.* The simplest change for TC3. It changes the mailbox
  layout that AB pins byte for byte, so it needs a Core contract version step, an AB
  regeneration, and a new R-gate run.
- *B. Additive continuation (recommended).* A new request kind carries the second part
  of a line; the PLC joins the two parts before it validates the record. The mailbox
  layout does not change, and AB may refuse the new kind until it binds it, as it does
  for set delete today.
- *C. Cap export at 255.* Records that do not fit would be refused at export instead.
  This is fail-closed, but a station's own data could then not leave it. Not recommended.

**G2 — Runtime evidence stops at Core 0.8.0.0 (O10: honest status).** *Update, same day:*
step 1 is done. Both gates are green on Core 0.13.0.0 (Core/Modules 187/187, Press 8/8),
archived in `Evidence/2026-09-28_Core_Press_TcUnit.md`. The run found a real defect:
set lines longer than 255 characters had been exported truncated, because `CONCAT`
and `LEN` stop at 255. It is fixed and proven (IMPLEMENTATION_NOTES §143). Steps 2–4,
the live OPC UA pass, remain. Core 0.9 to 0.11
passed on the local runtime: 174, 180 and 186 tests of 186, and PressTests 8/8.
The results are recorded only in commit messages; the raw logs and JUnit were not
archived under `Specification/Evidence/`. Core 0.12 was compiled (`CheckAllObjects` 0/0)
but not run. None of the week's HMI features has run against a live PLC over OPC UA.
*Plan:*
1. Re-run both TcUnit gates on 0.12 on the local UmRT (someone must be at XAE to
   approve its prompts). Archive the raw logs, the JUnit files and a dated record.
2. Download the press demo.
3. Run one live acceptance pass over OPC UA covering: the sets dialog (save, load,
   delete, export, import), the shift card, class levels, a type-scoped layout on the
   three press cylinders, and a maintenance picture view.
4. Record each item as passed or failed.

**G3 — AB does not bind the Core 0.8–0.12 clauses (O8).** *Update, same day:* option A
is done. The AB declaration names type keys, and the gateway projects them; they are
kept out of the controller manifest, whose hash is unchanged. The press publishes
the TwinCAT press's keys, so one faceplate serves both. B and C remain. The unbound
clauses were:
set delete (§3.8b), data classes (§3.8d), line data (§3.8e), shifts (§8.5.2) and the
type key (§7.1). All are now recorded as not claimed.
- *A. Bind the type key first (recommended as the next step).* The AB declaration names
  each module's type once, and the generator emits the key. This is the cheapest of the
  five, and it makes one faceplate serve a TwinCAT press and an AB press alike, as
  §7.1 promises.
- *B. Bind §3.8d and §3.8b delete.* These need the AB mailbox to enforce access, which
  AB §11.2.1 ties to the write decision. They belong to the write-enabled profile, not
  the read-only claim.
- *C. Declare §3.8e/§8.5.2 an optional Core profile* ("Line"), claimed per binding, the
  same way Robot is. This matches their nature, since a single-station line has no
  mirror. It is a Core decision.

**G4 — §7.2/§7.3 are only partly built.** *Update, same day:* layers (show/hide chips),
z-order (front/back), a bound `visible` and blink are now built; what stays open is
listed below, less a bound `enabled` for buttons and inputs (added later the same day).
Built before that: the overlay container, colour-token and fill-level bindings, and
the budget. Not built:
- the grid container with per-breakpoint variants;
- z-order and named, bindable layers;
- the other bindable properties (`visible`, `enabled`, blink, icon, rotation, opacity);
- a declared per-view budget below 200.
*Plan:* layers and z-order first, because a maintenance picture needs "sensor names"
and "I/O addresses" as show/hide sets. Then `visible`/`blink`, which reuse the same
rule model the state shapes already have. The grid container comes last: the flow
layout plus overlays covers today's screens.

**G5 — The operating-view rules are only partly enforced (§7.4).** *Update, same day:*
option A is implemented - an `ok` token draws neutral on an operating view. Contrast at
publish is closed structurally: authored colour can only be a token, and every token
(`off` now mapped to `outline`) is measured at 3:1 on a card in every theme by the
contrast suite, so no layout can publish an illegible state. Enforced: no imagery,
and semantic tokens only (structurally, since the model holds no literal colours).
Not enforced:
- "Colour reserved for abnormal conditions." A state shape's OK token draws green in
  any class.
- "Contrast enforced at publish."
*Options:*
- *A (recommended).* In an operating view, render the `ok` token as neutral grey and keep
  colour for warning, fault and info. The author's rule is unchanged, only its
  rendering follows the class.
- *B.* Refuse an `ok` token in operating views at publish.

A deliberately green "all clear" would then need a maintenance or engineering view.

**G6 — §7.5 station tile.** *Update, same day: closed.* Slot contents are type-authored:
three metric and two badge slots in fixed columns, OK neutral, authored per station or
per type, exported with the profile.
The tile's geometry is fixed, but its slot contents were not type-authored. This is planned after G4, because it reuses the same binding and
token vocabulary.

**G7 — Default theme.** The shipped default is still Light Blue (index 0). ISA-101
practice would default a new panel to Process Grey.
- *Option:* change the default for new installations only; stored selections are
  untouched. This is a product decision, so it is left to the project.

## 6. Verification of this pass

- `flutter analyze` clean.
- `flutter test`: 373 passing, 6 intentional live-environment skips.
- New tests cover:
  - type layout reach and whole-override replacement;
  - the before-revision recording the type layout;
  - import keeping the type scope;
  - publishing through the "Every <type>" chip;
  - class derivation, refusal, and its export;
  - budget refusal at 201 reads;
  - the picker order and ISA-101 leading;
  - every theme gate, including the two new greys.
- `check_consistency --strict` 0/0, including the read-surface gate's new
  `Status/TypeKey` entry.
- No PLC source changed in this pass, so neither the TwinCAT build nor the runtime gate
  applies to it.

## 7. Status at the end of 2026-09-28, and what needs the project owner

Closed today without anyone at the machine:
- **G1**: Core 0.13, set lines in pieces.
- **G2 step 1**: both runtime gates green on 0.13 and archived. It also found and fixed
  the 255-character truncation (IMPLEMENTATION_NOTES §143), and lint rule C9 now guards
  against it.
- **G3 A**: AB type keys.
- **G4 in part**: layers, z-order, bound `visible` and `enabled`, blink.
- **G5**: neutral OK on operating views; token contrast proved in every theme.
- **G6**: station tile slots.

**Still open, and why:**

| Gap | Needs | Why it cannot be done unattended |
|---|---|---|
| G2 steps 2–4 | the owner at XAE, then at the HMI | Downloading the press demo replaces the test application on the runtime, XAE asks for confirmation, and the acceptance pass is judged at the screen |
| G3 B | a decision: read-only or write-enabled AB | Enabling writes arms Core §14 in full (AGENTS.md §3a); the answer must be recorded, never assumed |
| G3 C | a decision: make line data + shifts an optional Core profile, or bind them in AB | It changes what a conformance claim covers |
| G7 | a decision: default new installs to Process Grey | A product choice; stored selections are unaffected either way |
| G4 rest | nothing; planned work | Bindable icon, rotation and opacity, bound layer visibility, the grid container, and a declared budget below 200 are buildable at any time; they are sequenced after the live pass so they are shaped by it |

## 8. Principles sweep of the libraries and examples (after Core 0.15.0.0)

The line fix (§145) showed the week's audit had checked each clause against its own
spec text, but had not checked the libraries and examples for violations of the
model's *standing* principles. This pass did that. Scope: `Fraktal_Core`, `Fraktal_Modules`,
the press bench, CoreDemo, and the HMI's catalogues. Allen-Bradley is excluded
because its code is generated from one declaration and is audited through its R/S gates.

Checked and clean:
- Every module FB body is only `Cyclic();`.
- Every overridden hook calls `SUPER^` first.
- No `OutImm` flag is latched as a literal.
- The raw I/O GVL is read only by the hardware driver.
- No `OPC.UA.DA := 1` sits on a type definition.
- No EM holds a Unit.
- The HMI has no station- or type-specific code.
- The lint gates (naming, L1 placement, C8 sim hooks, S1 chain exits) are green.

The findings are below, most severe first.

| # | Status | Where | Principle | Finding |
|---|---|---|---|---|
| P1 | ✅ closed | `FB_LineData`, press | §3.8e(a), §3.3 | The line was a CM registered under one root. *Closed in `21d3e08`, IMPLEMENTATION_NOTES §145.* Follow-ups: the line's `Revision`/`Stale`/`Owner` are no longer visible anywhere except the stale event; and `FB_LineData` still sets a type key it never publishes. |
| P2 | 🔴 | `FB_PressDemoUnit.OnCyclic` | §7.2.1 "never code a second execution predicate beside the report", §7.8 act-or-explain | A two-hand pulse calls `Start()` only when `PartPresent AND PressureOk`. Otherwise it silently drops the pulse. So the Start release report is not the whole predicate, and a refused start explains nothing. |
| P3 | 🔴 | `Fraktal_Modules/FB_ClampStationUnit` | §6.7 (a library shall not make a mode chain final), §6.8, LOCALIZATION §1/§7.1, O9 | A concrete application Unit with its continuous cycle sits in the reusable library. The cycle is a `CASE _step` inside the Unit's `_M_Dispatch` with hand-written `_step :=`, not a chain on `FB_SequenceBase` with `M_Advance`. It publishes `project.*` keys and type key, and copies `Clamp.OutImm` into its own `OutImm`. Used by CoreDemo, `FB_ClampStationUnit_Tests` and Annex H. |
| P4 | 🟡 | `FB_ClampEM`, `FB_TwoHandStartCM` | LOCALIZATION §1 key ownership | Library types raise project keys (`project.error.clampNotConfirmedAfterSettle`, `project.safety.twoHandControl`). Every consuming project must therefore supply the library's text. |
| P5 | 🟡 | 7 library module types | LOCALIZATION §7.1, O1 | `FB_AsciiDeviceCM`, `FB_TcpVisionCM`, `FB_TcpCodeReaderCM`, `FB_Iv3VisionCM`, `FB_Matrix220CM`, `FB_RobotCM` and `FB_StaubliVal3Connector` publish no type key. A faceplate therefore cannot be authored once for "every vision camera" or "every robot". |
| P6 | 🟡 | `FB_PressDemoUnit` `OutImm` | O9 one source; AGENTS "parents append child records, they do not copy the Boolean"; O4 orphan surface | The Unit republishes nine child facts under new names (`PressRetracted`, `DoorOpen`, `DoorClosed`, `SlideInside`, `SlideOutside`, `TwoHandArmed`, `TwoHandActive`, `PartPresent`, `AirPressureOk`). It also carries `ReadyForLoad` (= `Homed`), `ActiveSettleTime` (= `ParCfg`) and `Diagnostic` (= `Status.Diagnostic`, written twice per scan). The only reader of any of them is `MAIN`'s lamp (P7). |
| P7 | 🟡 | press `MAIN` | §10.2.1 (`MAIN` is a composition root), signal-tower clause "never station-specific IF logic" | `MAIN` computes `LampsOn` from Unit, child and domain state, although Core ships `FB_SignalTower`/`ST_SignalTowerParCfg` for exactly this. |
| P8 | 🟡 | `FB_PressDemoUnit.OnCyclic` | §7.2.1 lowest owning module; §6.1 `Held`; §6.9(d) | On air-pressure loss while BUSY, the Unit withdraws three children's outputs itself and faults with `PERMISSIVE_NOT_MET`. The condition belongs in the cylinders' interlock records, where a drop while busy rolls up as `INTERLOCK_DROPPED`. It is also a condition the process is expected to restore, so `Held` may be the right reaction. Separately, a `PneumaticPower` error is adopted with `_M_RollupFault()` on a child nobody awaits; §6.9(d) says `M_RaiseFromChild`. |
| P9 | 🟡 | `FB_PressDemoUnit` hooks | O1 "more than once is the threshold" | The same `_M_ResetModeSequences`/`_M_ClearModeTransitionState`/`_M_WithdrawSequenceOutputs` calls are repeated in six hooks. The base already knows every attached chain, so resetting them on init, command start, mode change, abort and operator reset is framework work. The power-group request edge (`ControlOn/OffRequest` → `PneumaticPower.Execute`) is likewise hand-wired glue for inputs the base itself defines. |
| P10 | 🟡 | press recipe (added today) | O9 one source | `PrepareRecipe` hard-codes `T#30S`/`T#5S`, and today's PAR_CFG registration repeats them as `30000`/`5000`. Also watch: the active-model write-back to the catalog is project code. A second project with an editable local catalog makes it a framework item (§3.8b intends the provider to read the `I_ConfigStore`). |
| P11 | 🟡 | HMI `default_catalogs.dart` | LOCALIZATION §1 | Six `project.config.press*` keys (two older, four added today) sit in the **standard** English map instead of the project map, and have no Spanish. |
| P12 | 🟡 verify | robot connectors | Annex I I.5, O9 | `FB_SimRobotConnector` extends `FB_DeviceConnectorBase`, but `FB_StaubliVal3Connector` extends a CM (`FB_AsciiDeviceCM`). Two bases serve one role, and swapping connectors may change whether a module appears in the tree, which I.5 says it must not. How each is instanced still needs checking. |
| P13 | 🟢 low | `FB_PressDemoUnit.M_AppendConfig` | O9, O1 | The Unit reads `GVL_PressFieldbus.Topology` directly, although its injected I/O catalog already owns the topology publisher. There are two routes to one datum, and every project with a bus must remember this override. |
| P14 | 🟢 low | CoreDemo | §4.2 | A flat `MAIN`, with no `00_System`/`0N_<Unit>` folders. |

**Plan, in order:**
1. **P2** — Move part-present and air-pressure into the press release component as Start entry conditions, in both the ST and LD renditions. The pulse then calls `Start()` unconditionally, and its refusal is reported. PressTests gains one case.
2. **Quick one-source cleanups**:
   - **P4, P5, P11** — key and catalogue fixes, no behaviour change.
   - **P10** — one constant pair.
   - **P6** — delete the copies; P7 then reads the children.
3. **P7** — drive the lamp through the signal tower.
4. **P9** — have the base reset attached chains on its own lifecycle transitions. This is a Core minor version; the press drops five hook bodies.
5. **P3** — move the clamp-cell Unit into CoreDemo as its application Unit, with a proper chain. Keep a probe Unit in `Tests/` for the library EM tests. Removing a released library type is a Modules major version.
6. **P12** — check how each connector is instanced, then keep one connector base.
7. **P13, P14** — when next touched.

**Needs the project owner:**

| Finding | Decision |
|---|---|
| P8 | Air loss while running: **HELD** (outputs withdrawn, resumes when pressure returns, no alarm) or **fault** (manual reset)? The standard leans to HELD for a condition the process restores; the press currently faults. |
| P3 | Remove `FB_ClampStationUnit` from `Fraktal_Modules` (Modules major step, Annex H example updated), or keep it deprecated for one release? |
| All | Runtime gates after each PLC step, as for G2. |

### 8.1 Status after closing (same day)

The owner decided P8 (**hold**) and P3 (**remove the Unit entirely**).

| # | Status | How it was closed |
|---|---|---|
| P1 | ✅ | `21d3e08`. Follow-ups: `FB_LineData` no longer carries a module presentation it never published. The four shift starts now have their own labels (English and Spanish). The line's `Revision`/`Stale`/`Owner` are deliberately **not** republished on the root, because nothing reads them (O4); staleness reaches the operator as its LOW event. |
| P2 | ✅ | `9b6a09a`. `Start()` is asked unconditionally, and only the two-hand latch is qualified. |
| P3 | ✅ | `9b6a09a`. The Unit and its structs left `Fraktal_Modules` (0.8.0.0). CoreDemo owns `FB_ClampCellUnit` with a proper chain. The Unit-tier rows moved to `FB_UnitTier_Tests`. |
| P4, P5, P11 | ✅ | `9b6a09a`. Library types raise `std.*` keys only. The vision, code-reader and robot types publish type keys. Press text moved to the project catalogue. |
| P6, P7 | ✅ | `9b6a09a`. The press `OutImm` holds only derived facts, and the pushbutton lamp is `TwoHandStartReady`, which `MAIN` only maps. |
| P8 | ✅ | `9b6a09a`. Air is each cylinder's own condition, so air loss holds and resumes. A new PressTests case proves it (9 tests / 2 suites). |
| P9 | ✅ | `9b6a09a`, Core 0.16.0.0. The base restarts attached chains on first scan, mode change and abort. Restart-vs-resume stays project policy. |
| P10 | ✅ | `9b6a09a`. One `RECIPE_MAX_*` pair. |
| P12 | ✅ | Core 0.17.0.0 / Modules 0.9.0.0 (IMPLEMENTATION_NOTES §147). The Stäubli connector now sits on the connector base, and the ASCII framing is shared through `FB_AsciiLink`. The robot CM services its connector and offers `RECONNECT`. Two latent defects went with it: no heartbeat or `LinkTimeout`, and a `LinkReason` that always said "link down". |
| P13 | ✅ | The press reaches the topology through the I/O catalogue that owns it. |
| P14 | ✅ | `9b6a09a`. CoreDemo has `00_System`/`01_ClampCell` folders **and an XAE solution**: until now no gate compiled it at all. |

**Found while closing, and still open:**

| # | Finding | Needs |
|---|---|---|
| P15 | ✅ **Closed:** `Status.Diagnostic` is the one published diagnostic (O9 one source, O1 no per-type copy, O4 half the live reads, O2/O8 the structure every binding already reads). Removed from 13 `OutImm` structs and 13 types; Core §6.1/§6.9 and Annexes A/B/C/H updated; lint rule D2 enforces it (IMPLEMENTATION_NOTES §148, Core 0.18.0.0 / Modules 0.10.0.0). | — |
| — | ✅ **Ran:** both runtime gates green on Core 0.18.0.0 (189/42, 9/2; `Evidence/2026-09-28b_Core018_Press_TcUnit.md`) and again on 0.19.0.0 (193/43, 9/2; `Evidence/2026-09-28c_Core019_Press_TcUnit.md`). | — |
| P10 watch | ✅ **Closed:** the active-model write-back left the press. The root saves model data through the provider's `I_RecipeStore`, for every model, not only the running one (IMPLEMENTATION_NOTES §149, Core 0.19.0.0). | — |

## 9. The owner's decisions, and their closing (2026-09-28, evening)

The owner decided every open decision in one pass. All four follow the recommendation.

| Item | Decision | How it was closed |
|---|---|---|
| **PIN storage** (§14; found by a read-only ADS probe) | Hash and hide | `b0e2be4`, Core 0.20.0.0, IMPLEMENTATION_NOTES §150. A PIN is kept only as a salted, iterated SHA-256 (`F_Sha256`, plain ST, checked against the FIPS vectors). The table is hidden from ADS symbols and OPC UA. The press hashes a commissioning PIN in the scan it is written and clears it. Core §7.7(c) now forbids a provider from retaining a secret it can read back. |
| **G3 B** (§3.8d, §3.8b delete on AB) | AB stays **read-only** | AB Part III records both as belonging to the write-enabled profile (§11.2.1). They are not claimed and the mailbox refuses both. They are bound only if a project enables writes and records that answer. |
| **G3 C** (§3.8e, §8.5.2) | An optional Core profile | Core §1.5 defines the **Line** profile, claimed per binding like Robot; §3.8e and §8.5.2 are marked with it. A binding without it publishes no partial line data, and a client reads absence as "no line". AB does not claim it. |
| **G7** (default theme) | Process Grey for new installations | `kDefaultThemeIndex` (27). A stored selection is never changed, and a settings file older than the UI preferences keeps Light Blue. A test pins the index to the Process Grey entry. |

**Still open:**

| Gap | Needs |
|---|---|
| Runtime gates on Core 0.20.0.0 (Core/Modules 197/44, Press 9/2) | The owner at XAE |
| G2 steps 2–4: the live OPC UA acceptance pass | The owner at the HMI, after downloading the press |
| ~~G4 rest~~ | ✅ **Closed.** The bound icon, rotation and opacity, bound layer visibility and the declared per-view budget are built; the tab dialog also stopped dropping a tab's default flag and card arrangement on save. The grid container followed: column/row cells as fractions of the tab, variants per control-scale preset, and in-place editing (HMI_CONTRACT, 412 tests). |
