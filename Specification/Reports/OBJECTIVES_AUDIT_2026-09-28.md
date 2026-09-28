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

**G2 — Runtime evidence stops at Core 0.8.0.0 (O10: honest status).** Core 0.9 to 0.11
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
listed below. Built before that: the overlay container, colour-token and fill-level
bindings, and the budget. Not built:
- the grid container with per-breakpoint variants;
- z-order and named, bindable layers;
- the other bindable properties (`visible`, `enabled`, blink, icon, rotation, opacity);
- a declared per-view budget below 200.
*Plan:* layers and z-order first, because a maintenance picture needs "sensor names"
and "I/O addresses" as show/hide sets. Then `visible`/`blink`, which reuse the same
rule model the state shapes already have. The grid container comes last: the flow
layout plus overlays covers today's screens.

**G5 — The operating-view rules are only partly enforced (§7.4).** *Update, same day:*
option A is implemented - an `ok` token draws neutral on an operating view; contrast at
publish remains open. Enforced: no imagery,
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

**G6 — §7.5 station tile.** The tile's geometry is fixed, but its slot contents are not
type-authored yet. This is planned after G4, because it reuses the same binding and
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
