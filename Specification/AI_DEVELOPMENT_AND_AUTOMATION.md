# AI-assisted development and deterministic automation

Two claims, one argument:

1. **If a rule is decidable from source, a human must never be the one checking
   it.** Review attention is the scarcest thing on a project; spending it on
   something a regex settles in 200 ms is a waste that also fails silently,
   because reviewers get tired and linters do not.
2. **If an artifact is derivable, a human must never be the one typing it.** Not
   because typing is slow, but because a hand-typed derivative drifts from its
   source and nothing notices.

Both apply with more force to an AI agent than to a person. An agent typing a
227-line `.plcproj` by hand burns tokens proportional to the file and gets it
subtly wrong; an agent *generating* it burns tokens proportional to the
**decision** — which files belong — and gets it exactly right every time. That
ratio is the whole economic case, and it is also the quality case, because the
two failure modes are the same failure mode.

This document is the survey of where Fraktal already does this, where it does
not, and what an AI-assisted project lifecycle looks like when it does.

> **Status.** Sections 1–2 describe what exists and is running today —
> including `tools/check_consistency.py`, which implements V1, V2 and V4 of the
> Tier 1 list below. The remaining Tier 1–3 items are **proposals with measured
> evidence**, not implemented work. Section 5 is descriptive: it documents the
> lifecycle as currently practised.

---

## 1. What exists today

Twenty-one first-party automation entry points. What each one *guarantees* is
the useful column — several were written after a defect got through, and the
guarantee is the shape of that defect.

### Gates (block a commit or a release)

| Tool | Guarantees |
|---|---|
| `tools/plc_lint.py` | 18 rules, machine-decidable from source (§1.5 makes this a **shall**). Runs both TwinCAT profiles. |
| `tools/check_consistency.py` | Agreement *between* artifacts: every operator-facing key resolves in a catalogue; every test suite is instantiated by a runner and the documented counts match source; a chain carried in two languages has the same steps and transitions in both. |
| `tools/Invoke-TwinCatBuild.ps1` | `CheckAllObjects()` on 5 isolated solutions + the boot-autostart assertion. Captures the DTE2 Error List, which is the only place XAE exposes a compile row. |
| `tools/Invoke-TwinCatLibraryInstall.ps1` | Save-as-library + install for Core then Modules, in dependency order. |
| `tools/Invoke-TwinCatTcUnitGate.ps1` | Activate → download → run → stop on a **named** target. Incomplete: result capture unresolved. |
| `tools/tcunit_to_junit.py` | A TcUnit log is accepted only if runner identity, suite count, test count and failure count all match what was expected. Rejects a log with two summaries. |
| `Tests/tools/Test-OpcUaPublication.ps1` | Rejects definition-level `DA` markers, misplaced GVL markers, and unexcluded pointer/interface storage. |
| `python -m unittest tools.test_*` | 72 tests over the tooling itself. |

### Generators and readers

| Tool | Guarantees |
|---|---|
| `tools/ld_rung_gen.py` | Generates LD rungs by cloning **or** by declaration. A box is derived from the declaration of the method it calls; its gate test regenerates an editor-drawn rung and compares node-for-node. |
| `tools/ld_dump.py` / `tools/sfc_dump.py` | Reads a graphical body back as a graph. This is a **gate, not a convenience** — see §4.1. |
| `HMI/lib/localization/reason_catalog.g.dart` | Generated from PLC reason definitions + `reason_rationalization.json`. The one code generator already in the build. |
| `HMI/gateway/tool/probe_*.dart` (8) | Read live ADS state — sim flags, I/O values, output chain, alarm state, fieldbus, latency, contention. |
| `HMI/gateway/tool/build_gateway.dart`, `build_windows_installer.dart` | Package Web HMI + gateway + signed installer. |
| `scaffold/FB_TemplateCM/` | A **copy**-template (not a generator) with a `SKELETON.md` that states exactly which parameters vary. |

### The shape of the coverage

Strong on **PLC source rules** and **build/compile**. Thin on:

- **cross-artifact consistency** (PLC ↔ HMI ↔ docs ↔ evidence),
- **project creation** — everything before the first compile is hand-typed,
- **runtime and commissioning**, where the probes exist but nothing composes
  them into a gate.

---

## 2. Measured gaps

Every number below was measured against this repository at
`386d83c`. These are findings, not estimates.

### 2.1 Localization keys — 52 unresolved in shipping code

A `DescriptionKey`, `StepName`, `Label` or `Prompt` that has no catalogue entry
renders on the operator HMI as the raw key. Nothing checked this until
`check_consistency.py localization`, which now reports:

```
shipping-code keys referenced (excluding test suites and probe FBs) : 341
resolved (default_catalogs.dart + reason_catalog.g.dart)            : 289
MISSING                                                             :  52
```

**15 of them are `std.*` keys from Core itself** — `FB_UnitBase`
(`std.audit.decision*`, `std.error.partCarrier*`), `FB_SequenceBase`
(`std.error.parallelBranchOutOfRange`), `FB_SystemHealthPublisher` (all eleven
`std.system.*`). Those are not one project's oversight; every station built on
this framework shows them raw. The rest are the press bench's SFC/LD chains and
I/O catalogue.

That they are genuine omissions rather than a family the HMI renders another
way is checkable and was checked: `std.audit.*` and `std.error.*` already have
11 and 71 entries in the catalogue, so the missing siblings are simply missing.
`std.system.*` has none of its eleven — an entire family added to Core after the
catalogue and never carried across.

### 2.2 Rendition parity — was checked by hand, once

The bench carries the same AUTO chain in ST, SFC and LD, and the same release
logic in ST and LD. Nothing proved they agree: the comparison that confirmed the
ladder was correct was a one-off script in a scratchpad.

Carrying N renditions is duplication O9 forbids unless something enforces that
they are the same thing. `check_consistency.py parity` is now that something,
for ST↔LD. **SFC is not covered yet** — its chart archive stores a step's
transition condition as a string in the transition's `Name` attribute, so the
target of a jump is an expression to parse rather than a number to read.
`tools/sfc_dump.py` already reads the attributes; the parity comparison is the
remaining piece.

### 2.3 Test inventory drift — caught only by accident

`TWINCAT_XAE_WORKFLOW.md` §6.3 says a result is accepted only when the counts
match "the intended source inventory". The recorded expectation was 84 tests /
26 suites; the actual source inventory is **94 / 29**. Three suites had been
added since, and two of them **did not compile**, so the gate could not run at
all and the drift stayed invisible for months.

Both halves are mechanical: count `TEST('…')` in the suites the runner's `VAR`
block instantiates. A suite that exists but is not instantiated silently does
not run, and the log's own totals still agree with themselves.

### 2.4 Evidence records are unverified

`.gitattributes` pins `* -text` specifically so evidence SHA-256s stay valid.
The evidence records themselves are hand-written, and nothing recomputes a
single hash. An evidence file whose hashes no longer match its sources is
indistinguishable from one whose hashes do.

### 2.5 Project manifests are hand-maintained

`Fraktal_Press_Demo.plcproj` is 227 lines: 27 `<Compile Include>` + 8
`<Folder Include>` entries, every one of which must mirror the directory tree.
Rules **P1** and **P2** exist *because* this is error-prone — P2 was written the
day a type moved between trees, kept P1 green, and broke only the borrower's
compile. The linter catches the mistake; nothing prevents it.

### 2.6 Rules stated as normative but not machine-checked

Sampled against `plc_lint.py` (0 occurrences of the construct):

| Rule (AGENTS.md) | Checkable how |
|---|---|
| `_M_State` shall never sit behind an `IF` | structural: assignment inside a conditional |
| `M_Advance` shall not pass `OnJumpN := -1` | literal scan |
| `OutImm` shall be derived, never latched | an `OutImm.*` write inside a sequence chain — the `Homed` defect exactly |
| a local browse name may not contain `.` | literal scan on `Setup(Name := …)` |
| every reusable type ships a suite (§5.7) | type inventory vs suite inventory vs runner `VAR` block |
| T1/T4 not re-tested per type | test-name scan |

Correctly **already** enforced, and worth stating so nobody re-implements them:
`SchemaVersion : UINT` first (**D1**), `SUPER^` first in hooks (**H1**), reason
bands ≥10000 and collision-free repository-wide (**R1**), enum ordinal parity
with the HMI (**E1**), `{attribute 'qualified_only'}` on all 40 framework enums
(compliant, though unenforced).

---

## 3. Proposed automation, ranked

Ranked by (defects prevented × frequency) ÷ effort. Effort is calibrated against
`ld_rung_gen.py`, which was ~470 lines + 24 tests and took roughly one session.

### Tier 1 — validations. Cheap, and each one has live findings.

| # | What | Prevents | Status |
|---|---|---|---|
| V1 | **Localization coverage** — every key in shipping PLC source resolves in a shipped catalogue | 52 live misses, 15 of them framework-wide | **built** — `check_consistency.py localization` |
| V2 | **Test inventory** — derive runner ↔ suite ↔ `TEST()` counts from source; fail if the workflow doc disagrees | §2.3 drift, and a suite that exists but never runs | **built** — `check_consistency.py inventory` |
| V3 | **Evidence integrity** — recompute every SHA-256 in `Specification/Evidence/*.md` | an evidence record that quietly stopped being true | ~50 lines |
| V4 | **Rendition parity** — the ST/LD comparison as a check | the whole justification for carrying more than one rendition | **built** — `check_consistency.py parity` |
| V5 | **The §2.6 rule set** — new lint rules | classes of defect the spec calls *shall* | ~150 lines |

V1 lands as a **warning**, not an error: it fires 52 times today, and a check
that turns the gate red on the day it ships teaches everyone to skip the gate.
`--emit` prints pasteable Dart for every missing key, so clearing the backlog is
mechanical; `--strict` promotes warnings to failures once it is clear.

V2 and V4 are **errors** and pass today, so they can block immediately.

V4's value is not theoretical. Re-introducing the exact defect that shipped —
a rung gate reading `EQ(215, 0)` instead of `EQ(_step, 215)` — makes the ladder
report 15 rungs against the twin's 16 steps, and the check names the missing
one. That defect previously passed lint, five compiles and a runtime gate.

**On V5, a caution learned while writing this.** Two of the six candidate rules
(`_M_State` behind an `IF`, and `OutImm` latched inside a chain) need real
statement-level structure, not line-oriented scanning: a first attempt reported
`FB_PressDemoUnit.OnCyclic` as a violation when the call is plainly at the top
level. A rule with false positives is worse than no rule, because it teaches
people to override the gate. These two want a small ST block parser first.

### Tier 2 — generators. Larger, and they change how a project starts.

| # | What | Input | Replaces |
|---|---|---|---|
| G1 | **Manifest generator** — emit `.plcproj` `Compile`/`Folder` lists from the tree | the directory | 227 hand-maintained lines per project; makes P1/P2 unfailable rather than merely checked |
| G2 | **Module-type generator** — `FB_TemplateCM` as a generator, not a copy | type name, reason band, command enum, HAL fields | the copy-and-rename ritual `SKELETON.md` documents; guarantees the band is reserved and the RED suite is shaped right |
| G3 | **ST chain generator** — a chain from a step table | `(StepNo, name, awaits, command, next, jumps)` | the most repetitive authoring in a project. **Strictly easier than the LD generator that already exists** — ST is text |
| G4 | **Project scaffold** — forest description → `MAIN`, the four DUTs per Unit, reasons GVL, I/O GVL/catalog/driver skeletons, manifests, test project | a forest YAML | everything before the first compile |
| G5 | **Evidence generator** — log + git + hashes → an evidence record | a raw TcUnit log | the record hand-written in this session; fully mechanical |

**G3 deserves emphasis.** The hard version of chain generation is done: a
graphical LD body is a serialized object graph with `Id`/`VarId` identity and
power rails, and it is generated today from a declaration. An ST chain is a
`CASE` statement. If the ladder can be generated, the ST skeleton is a
strictly smaller problem, and it is the form §5.5 calls the shipped reference.

### Tier 3 — runtime and commissioning

| # | What | Notes |
|---|---|---|
| R1 | Finish the TcUnit result capture | the one blocker on a fully automated runtime gate |
| R2 | Compose the eight ADS probes into a **commissioning checklist runner** | §6.0's commissioning gates cost multiple debugging sessions each; the probes exist, the composition does not |
| R3 | Publication/discovery assertion | the guide's OPC UA phase is entirely manual today |

---

## 4. The rules that make generated code trustworthy

These are not style preferences. Each was paid for.

### 4.1 A clean compile does not prove a generated node exists

Two things compile perfectly and do nothing:

- **an untyped `<o>`.** A node lifted out of a `<l2 … cet="BoxTreeBox">` list
  loses the type the list gave it collectively. It parses, it compiles, the box
  is absent.
- **a dead gate.** `EQ(215, 0)` instead of `EQ(_step, 215)` — legal IEC,
  constantly FALSE. Two committed rungs shipped this way and passed every gate.

So: **generate, then read the graph back.** `ld_dump.py` exists for this. The
same applies to any generated artifact — the check is not "did the tool exit 0",
it is "does the artifact say what it should".

### 4.2 Every substitution asserts its hit count

A rewrite that matches nothing reports success and changes nothing. That is the
default failure mode of text manipulation and it is silent. `subst()` raises
instead. Apply the same rule to every generator: assert what you expected to
match, and fail when the count differs.

### 4.3 Prefer positional identity over text identity

`"0"` is simultaneously the gate constant, the `Awaits` argument and the
`Branch` argument of one rung. Text substitution cannot address that rung;
`set_input(box, pin, value)` can, because pins match the declaration one-for-one.

### 4.4 Byte fidelity

`.gitattributes` pins `* -text`. Line endings are mixed *on purpose* and
evidence hashes depend on them. Edit repository files as **bytes**: on Windows,
`write_text` rewrites every line ending and `utf-8-sig` invents a BOM, and the
resulting whole-file diff hides the four lines that actually changed.

### 4.5 Derive expectations from source, never from a document

The workflow doc said 84/26. Source said 94/29. A number copied into prose is a
number that will be wrong later — so a gate should *compute* what it expects and
use the document only as a cross-check.

### 4.6 Never claim a runtime result without the runtime gate

A compiled artifact is evidence of compilation. This session's ladder is
compiled, graph-verified and cross-checked against its ST twin — and has never
executed. The evidence record says so.

---

## 5. AI-assisted development across the lifecycle

This is descriptive: it is how the work is actually done here, mapped onto the
`FIRST_PROJECT_AGENT_GUIDE.md` phases. The division that makes it work is
constant:

> **The agent proposes and generates. The machine proves. The human decides
> anything that is a judgement about the physical world.**

| Phase | Agent generates | Machine proves | Human decides |
|---|---|---|---|
| **0 · Inputs** | the question list; marks unknowns explicitly | — | I/O list, safety concept, target identity, security ownership |
| **A · Model** | forest and tier decomposition; reason-band proposal; DUT skeletons | `A1` (no Unit in an EM), `R1` (band ≥10000, collision-free), `D1` (`SchemaVersion` first), `N1`/`N2` | the decomposition itself; which existing module type to reuse |
| **B · Composition + I/O** | `MAIN`, GVLs, catalog, driver skeleton, manifests *(G1, G4)* | `P1`/`P2` (manifests), `Test-OpcUaPublication.ps1` (markers), `L1` (type ownership) | electrical tags, addresses, polarity, fail-closed defaults |
| **C · Sequences + release** | chains from a step table *(G3)*; LD/SFC bodies *(exists)*; release condition skeletons | `S1` (chain contract), `C5`–`C7`, `H1`, rendition parity *(V4)*, graph dump | the process — what the machine actually does, and in what order |
| **D · Test** | the RED suite from the §5.7 row map *(G2)* | TcUnit + `tcunit_to_junit.py` (runner identity + counts), inventory check *(V2)* | which behaviours are worth proving beyond the inherited rows |
| **E · Build** | — | `Invoke-TwinCatBuild.ps1` on 5 solutions; `Invoke-TwinCatLibraryInstall.ps1` | version steps on released types |
| **F · Deploy + runtime** | the activation sequence with a **named** target | `Invoke-TwinCatTcUnitGate.ps1`; evidence integrity *(V3)* | which runtime, and whether it may be taken | 
| **G · Commission** | probe composition *(R2)* | the §6.0 gates read live | `CONTROL_CIRCUIT_MAPPING_CONFIRMED` — an electrical verification on live equipment, **never** an agent's to set |
| **H · Online debug** | hypotheses, ranked; the probe to falsify each | the probe result | what to change on a running machine |

### What makes it *tested* rather than merely *assisted*

Three properties, all present today:

1. **Every claim has a gate behind it.** The tooling's own 72 tests, the lint's
   282-file sweep, the 5-solution compile, the runner-identity check on a TcUnit
   log. An agent's assertion that something works is worth exactly the gate it
   cites.
2. **Failures are designed to be loud.** Hit-count assertions, `ValidIds`,
   duplicate-`Id` detection, the "more than one summary" rejection. The
   engineering effort goes into making silent failure impossible, because a
   silent failure is the only kind an agent cannot self-correct.
3. **The irreversible steps are gated on a human naming the target.**
   `-ExpectedNetId` is mandatory and has no default. That single parameter is
   what separates "activate the test application" from "activate it on the wrong
   machine", and it is deliberately not inferable.

### The known failure modes

Stated so they are designed against, not discovered again:

- **A green gate that graded the wrong thing.** A Press run once reported
  `PRG_TcUnitRunner` and 84/26, proving the *Core* application was still
  selected. Hence runner identity in the validator.
- **A right-looking action on the wrong target.** An activation with no
  `TargetNetId` silently went to the local runtime. It activated, restarted,
  logged in and started without one error, and produced nothing — for an hour it
  looked like a capture bug.
- **A tool that reports success and changes nothing.** The reason every
  substitution asserts its count.
- **Documentation drifting from source.** §2.3.

---

## 6. Suggested order

1. ~~**V1, V2, V4**~~ — done, `tools/check_consistency.py`, 9 tests.
   Next on that tool: **V3** (evidence hashes), which fits the same shape.
2. **Clear the V1 backlog** — 52 keys, `--emit` generates the stubs; then turn
   `--strict` on in the gate so it can never grow again. The 15 `std.*` ones are
   Core's own and should go first: `std.audit.*` and `std.error.*` already have
   11 and 71 siblings in the catalogue, so those omissions are simply misses,
   and all eleven `std.system.*` keys are absent as a family.
3. **G1** — manifests. Turns two lint rules from *checks* into *impossibilities*.
4. **G3** — the ST chain generator. Largest recurring authoring cost, and the
   harder graphical version is already proven.
5. **V5** — the remaining rule set, after the ST block parser it needs.
6. **G2, G4** — the scaffold generators, once G1 and G3 have settled the shape.
7. **R1** — finish the runtime capture, then **R2**.

Nothing here requires a new framework concept. Every item is a derivation of
something the repository already states, and the measure of success is the same
in each case: **the number of things a reviewer has to remember goes down.**
