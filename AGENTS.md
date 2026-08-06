# AGENTS.md — guide for AI coding agents working on Fraktal

Fraktal is a **platform-neutral standard for PLC equipment software**: one recursive three-tier
module model, one data contract, one PLCopen command handshake, one diagnostic model, self-describing
over OPC UA so a generic HMI renders it with zero per-station code. This file is the working briefing
for any agent editing this repo. **Read the spec for anything normative** — every clause below names its
spec section so you can drill in. Spec lives in `Specification/`; the normative core is
`Fraktal_Core_Part_I.md` (Part I), with the TwinCAT binding in `Fraktal_TC3_Part_II.md` (Part II).

> Normative language in the spec: **shall/must** = requirement · **should** = recommendation · **may** = permitted.

**Engineering discipline is objective O9 (§1.1) — apply it to every edit:** one authoritative source per
fact (derive, never duplicate), behaviour written once at the owning level and inherited (overrides add
device logic only), minimum interface surface, additive+versioned changes to released types, and code that
matches the idioms of the code around it. Scalability is both structural *and* runtime (O4): keep a
station's published/discovered/streamed surface proportional to what is actually consumed. The CI/lint gate
(§1.5, §5.5) enforces the machine-checkable half; the rest is on you.

---

## 1. Repository map

```
Specification/        The standard. Part I (Core, platform-neutral) + Part II (Fraktal/TC3 binding)
                      + annexes A–K (worked examples) + HMI_CONTRACT.md + split/audit notes.
FraktalCore/
├── PLC/
│   ├── TwinCAT/                 Fraktal/TC3 reference implementation (IEC 61131-3)
│   │   ├── Framework/Fraktal_Core/       framework library
│   │   ├── Framework/Fraktal_Modules/    reusable module library
│   │   ├── Examples/CoreDemo/Fraktal_Demo/          two-root smoke application
│   │   ├── Examples/PressDemo/Fraktal_Press_Demo/  internal feature-testing bench (not a real project)
│   │   ├── Tests/                       aggregate Core/Modules TcUnit project
│   │   ├── Examples/PressDemo/PressTests/  the internal bench's integration suites
│   │   │                                (separate gate: XAE rejects '..' in a
│   │   │                                Compile path, so Tests/ cannot reach
│   │   │                                Examples/ - run BOTH)
│   │   └── scaffold/FB_TemplateCM/       copy-template (not compiled; born RED)
│   └── Allen-Bradley/            reserved platform binding tree
└── HMI/               Generic operator HMI (Flutter). lib/{data,domain,state,ui}.
```

Two source-of-truth documents beyond the spec:
- `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md` — **every** place the implementation diverged from the
  draft spec, with the reason. Read this before changing PLC code; it records what was decided and why.
- `Specification/HMI_CONTRACT.md` — the exact symbol→widget bind table the HMI implements.
- `Specification/FIRST_PROJECT_AGENT_GUIDE.md` — mandatory phase/evidence workflow when guiding a
  first project, initial target deployment, TF6100 commissioning, or HMI connection troubleshoot.

---

## 2. The mental model (learn this first)

**Three function-block archetypes, recursively nested (§3.1, §3.3):**

| Tier | Type | Role | May contain |
|---|---|---|---|
| Top (recursive) | `FB_Unit` | **ModeHandler** — runs a continuous mode sequence Start→Stop; owns mode | Units, EMs, CMs |
| Middle | `FB_EquipmentModule` | **CommandHandler** — discrete, bounded commands | CMs, nested EMs — **never a Unit** |
| Leaf | `FB_ControlModule` | Hardware-bound device, one HAL channel | nothing (leaf) |

A program hosts **one or more root `FB_Unit`s** (a *forest*, §3.1a) — peers, each with its own
mode/cycle/model identity. There is no shared super-root.

**One contract everywhere (§3.12):** every module exposes `ParCfg` (config/recipe) · `ParCmd`
(command params) · `OutCmd` (command results) · `OutImm` (cyclic status). The PLCopen handshake
(§6.1) — `Execute`/`Busy`/`Done`/`Error`/`ErrorID`/`Abort`/`Aborted` — is the single command vocabulary;
`State` (`E_ExecState`: READY/BUSY/DONE/ERROR/ABORTED) is the derived summary.

**The lifecycle is written ONCE in `FB_ModuleBase` (§2.2).** A concrete module type
`EXTENDS FB_ControlModuleBase` (or the EM/Unit base) and overrides **only `_M_Dispatch`** (its
`CASE _step` device logic, calling `_M_Fault`/`_M_Complete`) plus, optionally, lifecycle hooks (§3.14).
Edge handling, state mapping, Execute-drop reset, `ErrorID`, abort routing, per-command timing, and the
HMI data mirror are all **inherited** — do not re-implement them.

**Diagnosability by construction (§6.9, §8):** when a sequence stalls, the operator gets a precise
root cause produced automatically from the contract — never hand-coded per-step. A stall is a *pending*
diagnostic (Low), not a fault; the fault path is the awaited module's Error, adopted instantly via the
rollup (§8.2).

**Recoverability is part of the contract (§6.1 `Held`, §8.3(b)):** a condition the operator or process
is *expected* to restore — a hold-to-run or two-hand control released mid-motion — is **HELD**, not a
fault: `BUSY`, outputs withdrawn by the same permit, reason published at LOW, no alarm, resumes by
itself (`_M_Hold`/`_M_HoldDiag`, `_M_RollupHold`). Reserve faults for defects. And **one** operator
reset must leave the machine restartable: `OperatorReset` closes a MANUAL_RESET event from ACTIVE as
well as WAIT_RESET *and* releases the latched control state — its own run command plus every child
command the suspended chain issued (`M_ReleaseCommand`) — because §6.1's Execute-drop reset is the only
exit from a latched terminal state and it needs those inputs low. Never make a symptom disappear by
relaxing a release gate; a reset clears the **latch**, never the **condition** (IMPLEMENTATION_NOTES §76).

---

## 3. PLC editing guardrails (the shalls that bite)

**Trim the project, pay in the library (§1.1 O1 — apply this before writing project code):**
- When the same wiring, latch, reset, or per-scan call would be written in **more than one** project
  sequence/module/Unit, that is a *framework* defect. Absorb it into `Fraktal_Core` even if the base
  class gets materially more complex — the cost is paid once, the saving recurs per station.
- **Never leave a project a call it must remember for correctness.** If forgetting it produces a wrong
  or intermittent result, drive it from a path the application already takes: `M_Attach` (registration),
  `OnCyclic` (per scan), `M_ClearTransition` (step change). Worked examples in the base:
  `_M_BeginSequenceScan` (per-scan chain reset — a project calls nothing) and `M_RunSub`
  (composite sub-chain — replaced 8 lines × 4 charts with one call, and removed a latch whose forgotten
  reset left a chain that never restarted).
- Before adding a "wiring-only" method to a project Unit, ask whether the base can do it from the
  registry it already has. Prefer deleting project glue over documenting it.
- Judge by count, not taste: **more than once is the threshold.**

**Sequences — pick the language, then follow its rule (§6.8):**
- A chain always extends `FB_SequenceBase`, records steps with `M_Step`, and
  progresses through `_retVal`. Only **who evaluates the transition** differs:
  ST → `M_Advance`; SFC → the runtime; LD → the rungs.
- **ST**: every `CASE _step OF` branch ends with `M_Advance(OnAdvance := …)` — and
  that call is the point: it declares the step's COMPLETE set of exits in one place,
  which is what lets S1 prove every non-terminal branch has one. Writing `_step := N`
  by hand works but hides the graph inside conditionals and defeats the check, so ST
  chains **shall** use `M_Advance`. Unused jumps are defaulted: pass `OnJump1 := 185`
  only for jumps the step really has, never `OnJumpN := -1`.
- **SFC naming**: a step is `N<StepNo>`, its action is `A<StepNo>_<What>`. The step
  number is then the same token in the chart, the ST twin's `CASE` label, the §3.13
  row and the stall message; the differing prefix keeps a step distinguishable from
  its action object in the archive.
- **SFC**: step bodies are **ACTIONS** (not methods — `MainAction` resolves to an
  action), each the ST branch **minus** `M_Advance`. Transitions are
  `_retVal = E_StepResult.ADVANCE`, and a jump branch is `… = E_StepResult.JUMP1`.
  A chart POU never overrides `M_ChainRun` — its body *is* the chart.
- **LD**: an integer state machine over the inherited `_step` — one rung per state,
  `[EQ(_step, N)]` dispatching, and the rung `MOVE`s the next state into `_step`. No
  `M_Advance`, no `_retVal`. A chain extends **`FB_SequenceBase`**, the same base ST and
  SFC use: a rung calls the real method through XAE's `EN`/`ENO` pins, so `M_Step`,
  `M_Await` and **every method of every project-defined FB** are rung-callable with no
  library change. That is the only form that scales — a hand-written `…Ld` twin per
  method per developer type does not. (`FB_SequenceBaseLd`, which took `Run : BOOL`
  because adding an input to an override is `C0094`, was exactly that mistake and has
  been **deleted**; `convert_ld_boxes()` in `tools/ld_rung_gen.py` migrates a chain that
  still carries it.) An `EN`-gated value-returning box has **two** outputs, `ENO` first
  and the return value second; wiring the wrong slot compiles clean and strands the
  intended variable. **Never nest a value-returning box or feed its result into another
  box's power pin:** XAE lowers that edge to `ImpVar<BoxId>_<output>` and may fail lazy
  type inference. Assign every return to an explicitly typed local, then combine the
  locals; `Run` is rung power, not Boolean chaining, and independent waits must all be
  called each active scan. Full rung-by-rung procedure, both rung shapes and traps are in
  `FraktalCore/PLC/TwinCAT/README.md` § "Writing a Ladder sequence rung by rung".
- Never add a per-scan `_retVal` clear: `FB_UnitBase._M_BeginSequenceScan` does it
  for every attached chain before `_M_Dispatch` (§1.1 O1).
- The `FB_SFC_` prefix in the press demo is **not a convention** — it only lets two
  renditions of one chain coexist. Name a real chain `FB_<Thing><Mode>`.
- **Do not synthesise an SFC/LD body from nothing — clone one that compiles.**
  It is a serialized object graph. For **LD**, `tools/ld_rung_gen.py` generates a rung
  by cloning an existing network, renumbering every `Id`/`VarId` into a fresh range,
  and rewriting only leaf operands; `tools/test_ld_rung_gen.py` proves the split/rebuild
  is byte-identical before it touches a file. Every substitution asserts its hit count,
  because a rewrite that matches nothing reports success and changes nothing. Compile
  after **every** rung: `ImpVar<BoxId>_<n>` maps straight to that node's
  `<v n="Id">…L</v>`. **The limit is absolute: it can only produce box types that
  already exist somewhere in the file** — a rung needing a box with no instance to
  clone from (`M_DelayLd`, `M_AskDecisionLd`, `M_PartRecordLd`, `M_RunSubLd`,
  `M_RaiseWarningLd`, `M_ReportFromChildLd`, a child's `WithdrawOutputs`) needs **one**
  instance drawn in XAE first; then clone it. Full procedure in
  `FraktalCore/PLC/TwinCAT/README.md` § "Generating a rung by cloning a worked example".
  For **SFC** the archive is flat attribute records, not a wired graph, so a chart is
  materially easier to clone than a rung — no `Id`/`VarId` renumbering, no power rails.
  Read the archive's own descriptor table (`<d2 n="Attributes" ckt="Guid"
  cvt="SFCAttributeDescription">`) for the attribute GUIDs rather than guessing: a step
  has ten attributes, four normally empty, and **a transition stores its condition
  expression in `Name`**. `MainAction` is `{700a583f-b4d4-43e4-8c14-629c7cd3bec8}`;
  using `EntryAction` by mistake stalls the chain at its first step forever. The full
  GUID table and the step/action naming rule are in the README section above.
- **To own a child's failure, stop awaiting it.** An awaited child fault is adopted
  by `FB_UnitBase.OnCyclic` (`_exec := ERROR`, `_step := 0`) *before* `_M_Dispatch`
  runs, so a chart can never jump on it. Pass `Awaits := 0` and name the wait with
  `M_Await` (press AUTO `N200` does this to offer a scrap/return decision).
- **A command behind an `IF`/`CASE` has no rollup — raise it (§6.9(d)).**
  `M_RaiseFromChild(Source := _child)` adopts the child's own first-out verbatim;
  `M_RaiseCustom(Reason, DescriptionKey, Severity, Category, LinkPath)` states a rule
  the framework cannot see. Both return TRUE only when they actually faulted, so the
  shape is `IF M_Raise…(…) THEN <drop the child's Execute>; RETURN; END_IF` and it is
  safe to call every scan. The reaction is fixed: the chain stops **on** the step, that
  §3.13 row gets the error and its drill-down link, and when the error clears the step's
  latches are re-armed so the command is **re-issued and re-tested**, never resumed
  mid-handshake. Restart-vs-resume of the whole chain is the project's call in
  `OnCommandStart`. `Severity`/`Category` are a proposal — §8.8 rationalization wins for a
  registered reason, so they only survive for a project band code (10000+).
- **A handled condition is a message, not a fault (§6.9(e)).** `M_RaiseWarning(Reason,
  DescriptionKey, Severity, Category)` states a rule the step owns;
  `M_ReportFromChild(Source)` publishes a child's first-out **verbatim without adopting
  it**. Neither touches `_exec`, so the chain keeps its own recovery branch; the ring
  entry is AUTO_RESET come+gone and can never block a restart; and the base raises each
  at most **once per step visit**, so call them unconditionally every scan. Press AUTO
  `N180` (two-hand released while the door closes) and `N200` (ram did not reach) are
  the shipped examples. Choose (d) `M_Raise…` only when the machine must actually stop.
- **Parallel branches (§6.12) — prefer the sub-chain fork.** `M_RunPar(Chain, BaseStepNo,
  Branch)` once per leg then `_retVal := M_ParJoin();` works in **every** language, and
  each leg is an ordinary chain, so it already owns its step pointer, its `_retVal` and
  its step-scoped latches (§1.1 O4: make the work position a type, do not duplicate its
  steps in a picture). A natively drawn SFC/LD divergence is also supported: a leg step
  passes `Branch := n` to `M_Step` (there is no separate declaring call — the leg is an
  argument of the step record, so it cannot be set without recording a step), and that
  leg's transitions read `_conRetVal[n]`. **Number every leg (1, 2, …); none of them is
  "the main line"** — `_retVal` is the line before and after the fork, and the join reads
  every `_conRetVal[n]`. `M_RunSub` takes no branch: a composite step inherits the leg of
  the step that runs it. In the archive, a branch whose legs open with a **step** is parallel;
  one whose legs open with a **transition** is alternative.
- **A flow-chart row is assembled from four tables** (§3.13), split by how often each
  part changes: `SequenceStepDef` (static, served once through the §3.10.2 manifest under
  the live browse paths), `ActiveSteps` (a cursor per concurrent leg — live, ~10 entries),
  `SequenceSteps` (7 B/row: `Visited`, `LastDuration`, and the error/message marks), and
  the sparse `SequenceAnnotations` for their text. A project writes none of it — `M_Step`
  still takes the same arguments and the base files them.
- **Never move `Visited`/`LastDuration`/the marks to client-side accumulation.** An HMI
  polls at a few Hz against a task at kHz, so it cannot see a step shorter than its poll
  interval: it would skip fast steps and lose transient faults. Liveness is safe to derive
  from the cursor; history is not. The row FLAG is likewise authoritative — if the note
  table fills, the mark survives and only the text is lost.
- **The §3.13 chart is scoped to the running mode.** `FB_UnitBase.OnModeChanged` clears
  the published rows, so each mode builds its own chart; a project writes nothing, it
  inherits through the `SUPER^` call every override already makes. Rows are discovered
  by visit and discovery never ends, so without that boundary the table is the union of
  every chain run since boot — and `MAX_SEQUENCE_STEPS` bounds it silently.
- **`CurrentStep`, the §6.9 walk and the profiler are main-line only.** A first-out must
  name one step. A leg is timed and guarded on its own §3.13 row (`Active`, `Elapsed`,
  `TimedOut`); a leg that must fault uses §6.9(d) and stops the whole chain.
- Full comparison table, the SFC build procedure and the trap list live in
  `FraktalCore/PLC/TwinCAT/README.md` § "Writing a sequence: ST, SFC or LD".

**Editing `.TcPOU` files by script:**
- A method's **declaration and implementation are separate CDATA blocks**. A
  replacement written against the two concatenated matches nothing and *reports
  success* — a silent no-op. Target one CDATA section, then re-read and assert.
- `FUNCTION_BLOCK INTERNAL FB_X EXTENDS FB_Y` is legal; qualifiers may precede the
  name in any combination.
- IEC standard function names (`SUB`, `ADD`, `DIV`, `LEN`, `SEL`, …) are reserved as
  identifiers — rule **C2** rejects them. A *qualified* enum member is fine.

**Command result vs. derived state (§3.12):**
- Ask what makes the value change. A command produced it and it stays until another
  command replaces it → `OutCmd`. It is simply true *right now*, recomputed from the
  modules underneath → `OutImm`, and it **shall** be derived, never latched.
- `Homed` is the canonical mistake: latched by a HOME sequence, it keeps claiming
  "homed" after an operator jogs an axis off position in MANUAL, because only a
  sequence can clear a latch and no sequence is running.
- Publish derived state with `OutImm.X := _M_State(Idx := n, Key := '...', Ok := <expr>);`
  — it returns the value, so it reads as a plain assignment, and adds the name, the
  moment it last changed (§2.7), and a bounded generic table the HMI renders without
  knowing the module type. Same shape as `_M_Await` on purpose.
- **Call it unconditionally, every scan.** A flag that stops being published goes
  `Stale` and is forced FALSE: state nobody computes is not a claim. Never put
  `_M_State` behind an `IF`.

**Compile before you claim.** There IS a TwinCAT compiler on the dev host:
`tools/Invoke-TwinCatBuild.ps1` runs `CheckAllObjects()` on the two libraries and the two
test solutions. Read `Specification/TWINCAT_XAE_WORKFLOW.md` §5.1 before concluding a
failure is undiagnosable — the Error List is reachable **only** through the `DTE2`
interface (`envdte80.dll` from the same IDE), and base `EnvDTE.DTE` returns an empty or
missing property that looks like a tooling dead end.
- **A ladder facade is not an override.** Adding `Run : BOOL` for rung power flow changes
  the signature, which is `C0094`. Give it its own name (`M_StepLd`), and remember a
  method returns through **its own** name — renaming the method without retargeting
  `<name> :=` in the body silently rebinds it to the inherited method.

**Where a type lives, and when to declare a flag (lint rule L1):**
- **A library declares only what a library object owns.** The test is not "who uses
  it" — a reusable type is *meant* to be used from outside. It is: does any object in
  the Framework tree declare a member of it (plain, `REFERENCE TO`, `ARRAY … OF`, or
  `EXTENDS`)? If only an application instantiates it, it is that application's
  contract and belongs in that project. `ST_PneumaticPress*` sat in `Fraktal_Modules`
  with no library FB owning them, so every consumer carried four structs for a machine
  they do not have (§1.1 O4/O9). Cross-library ownership is fine — `ST_IoPointIdentity`
  lives in Core and is owned by Modules.
- **Moving a type between trees is a two-manifest edit (lint rule P2).** A project that
  compiles *another* project's authored sources — `PressTests` links the shipping Press
  Unit/sequences rather than copying them — must borrow every object of that tree it
  references. P1 only proves each manifest lists its **own** root completely, so a type
  that moves *into* a lender's tree is added to the lender's manifest, keeps P1 green,
  and breaks only the borrower's compile. That is exactly how the `ST_PneumaticPress*`
  move broke `PressTests` while the bench stayed green.
- **Declare a flag when something needs it, not before.** A published field with no
  consumer is not "ready for the future", it is surface everyone pays for and nobody
  reads. `OutCmd`/`OutImm` are the exception *only* because the generic HMI tree
  renders whatever is published — but a field no PLC code, no HMI code and no MES
  reads is an orphan, and the honest fix is to delete it and add it back the day it
  has a reader.

**Lifecycle & hooks (§2.2, §3.14):**
- New module types **shall extend the base classes** — never re-implement the lifecycle.
- Every overridden hook **shall call `SUPER^.OnX(...)` first** and propagate its return — **except
  `OnModeExit`**, where calling the base *is* the cancel, so it is staged to the end of a graceful stop (§3.14.4).
- A module FB body contains only the inherited `Cyclic()` call; concrete types put no application logic
  there. Per-scan extension work goes in `OnCyclic`, one-shot command wiring/reset in
  `OnCommandStart`, and device logic in `_M_Dispatch` (IMPLEMENTATION_NOTES §5).
- **No `FB_Unit` inside an `FB_EquipmentModule`** (§3.3) — structurally enforced; a CI check walks the tree.

**Naming (§4.3–§4.6) — a lint gate checks this:**
- Prefixes: `F_` function · `FB_` function block · `M_`/`_M_` public/protected method · `ST_` struct ·
  `E_` enum · `I_` interface · `GVL_`/`PL_` GVL/param-list · `PRG_` program (except `MAIN`).
- **No Hungarian** on variables/instances (`Clamp1 : FB_ControlModule`, not `fbClamp1`). Retained
  access markers only: `p` pointer, `r` reference, `i` interface, leading `_` for `%I/%Q/%M`-mapped (HAL boundary).
- Enums carry `{attribute 'qualified_only'}` and are referenced `E_X.MEMBER`. Constants `UPPER_SNAKE_CASE`.
- TwinCAT keywords are case-insensitive and forbidden as identifiers (`Action`, `Class`, `Log`, `Min`, `Max`, `R`,
  `S`, `DT`, `Time`, etc.). Use semantic alternatives (`Gate`, `TimeClass`, `AuditSlot`, `Minimum`, `Maximum`, `DeltaMs`).
- Status = *adj·noun·num·past-verb* (`ClampClosed`); Command = *verb·adj·noun·num* (`CloseClamp`) (§4.5).
- A module's local OPC UA browse segment **shall equal** its local PLC instance/schematic name.
  `Status.Name` is the qualified dotted Fraktal identity (`Root.Child`); its final segment shall equal
  that local browse name. `.` is reserved as the path separator and is forbidden inside a local name.
  Reference/owner aliases are not additional modules (§4.7, §4.8).
- In TwinCAT TF6100 **TMC-Filtered** mode, place `{attribute 'OPC.UA.DA' := '1'}` immediately before every deployed root Unit instance in `MAIN`/the forest-owning GVL. The explicit instance marker inherits to that root's children. Do not place `DA=1` on reusable FB type definitions: definition-level publication exposes undeployed instances and reference aliases as extra browse roots. Place standalone-data markers immediately before the published variable (for example `GVL_<Project>Fieldbus.Topology`), never before `VAR_GLOBAL` (Part II §3.10).
- Exclude implementation-only pointer/interface/reference storage inherited into a published subtree with `{attribute 'OPC.UA.DA' := '0'}`. Never hide the published child-module instances. An application-owned `Unsupported datatype ... UXINT` path is an exclusion defect; Beckhoff's `TwinCAT_SystemInfoVarList._AppInfo.TComSrvPtr` is a skippable system leaf, not a Fraktal compile or discovery failure.

**Data & recipe (§3.8):**
- `SchemaVersion : UINT` **shall be the first member** of every `ParCfg`/record — a generic provider
  validates by comparing the stored first-UINT to the target's. Adding a member = a schema change.
- Recipe load is **migrate-or-fault** (`RECIPE_INVALID`), never partially applied. External payloads are
  validate-before-load (§5.6).

**Traceability (§3.16):**
- Every `FB_Unit` publishes `Part : ST_PartContext`. Traceability is OFF until the composition root
  injects a carrier via `SetPartCarrier` (shipped default: `FB_LocalPartCarrier`, BY_POSITION serials;
  RFID/DataMatrix/host substitute behind `I_PartCarrier` — the recipe-provider pattern).
- A Unit's mode chain raises the four canonical events through the inherited helpers:
  `_M_PartReceived` (identity confirmed at entry) → `_M_PartStarted` → optional `_M_PartRecord`
  (measured values) → `_M_PartProcessed(Verdict, Reason)` — the carrier write precedes the event.
  ERROR entry auto-raises `EVENT_PART_PROCESSING_ABORTED`; also call `_M_PartAborted()` in `OnAbort`.
- Carrier failures are never silent: `CARRIER_READ_FAILED` / `CARRIER_WRITE_FAILED` faults (§8.8
  band 2020–2029; the four `EVENT_PART_*` codes live there too).

**I/O code placement (§10.2.1):**
- `GVL_<Project>IO` declares raw mapped symbols only; exactly one project Hardware Driver POU may access it.
- Project I/O catalogs own tag/address/description/module-role data only. They do not copy live values or
  reimplement bounds, duplicate, health, or diagnostic-join algorithms.
- `FB_IoTopologyPublisher` owns those reusable algorithms; CMs consume HAL semantics and injected identity.
- `MAIN` is a composition root: setup, real/simulation selection, and scan ordering—not channel assignments.
- An electrical tag/address has one project source of truth; do not repeat the literal in `MAIN`, a CM, and
  a fieldbus publisher.
- Changeover uses fallible `PrepareRecipe(Model)` → recursive readiness → infallible bounded
  `CommitRecipe()`; prepare rejection calls `AbortRecipe()`. Commit performs no validation or I/O.
  Providers address records by `(ModelCode, RecipeKey)`, never one ambiguous string.

**Reason codes (§8.8) — one number space, the registry is the collision authority:**
- Framework band `2001–2008` (TIMEOUT/PERMISSIVE_NOT_MET/INTERLOCK_DROPPED/RECIPE_INVALID/STEP_STALLED/
  RETRY_EXHAUSTED/CYCLE_TIME_DEGRADED/UNSUPPORTED_COMMAND); self-test `2900–2909`. Type bands are `DINT` constants ≥10000 in
  the type's own `PL_<Type>Reasons`. **Reserve a band before writing a type**; record it; the audit scans
  for duplicates and band squats. `E_Reason` is deliberately non-strict so bands compose across libraries.

**Defensive coding (§5.6):** validate commands against the supported set (reject out-of-range with a
reason, never a silent default); bounds-check indices; validate motion targets against limits. Every
behaviour-selection path shall have a safe fallback. A fail-closed initialized result plus a terminating
guard `RETURN` is an explicit fallback; optional bounded updates/diagnostic appends need no empty `ELSE`.
Every `CASE` dispatcher still has an `ELSE` — never a silent no-op that stalls a chain.

**Safety and control power (§9.8, `SAFETY_AND_CONTROL_POWER_PROFILE.md`):** the standard PLC may
send untrusted enable/stop/unlock requests, but TwinSAFE/certified safety alone grants safe enable,
unlock, reset, muting, bridging, and safe valve/drive outputs. `ControlOn` is control-domain orchestration;
`PowerOn` targets one named group. Neither may self-resume after safety or communication recovery.
Key bridging and muting are read-only, conspicuous HMI status—never `PermIntlk` bypasses or forces.
Safety/control-power ownership is an optional **control domain** orthogonal to the Unit forest: a Unit
references zero or one domain, and one domain may serve several peer root Units. Never invent a
super-root Unit or duplicate the coordinator per Unit; `Present=FALSE` means no profile Start gate.

**Language policy (§5.5, §6.2, §6.8):** framework/base types are **ST only**. A multi-step Unit/EM
sequence is a separate POU that **extends `FB_SequenceBase`**; the shipped reference form is the Core
§6.8 **ST `CASE _step OF` skeleton** (native graphical SFC is a permitted §6.8 alternative but only if
authored in the XAE SFC editor — a hand-emitted chart XML fails with an `SFCStepType` cascade; never
commit one). Each `_step` branch contains that step's `M_Step`/condition record, child command or wait,
decision/timer/result logic, and sets the shared `_retVal`, ending with `M_Advance(OnAdvance := <next>)`.
The owner adapter may only run the sequence or bridge protected framework services; use
`OnCommandStart` for its one-shot reset edge. A token-only
body plus `CASE ActiveStep OF` application logic in the Unit is forbidden. The project-owned
`FB_PressDemoHome`, `FB_PressDemoChangeover`, `FB_PressDemoAuto`, and shared `FB_PressDemoLoadPosition`
are the reference; their `FB_PressDemoUnit._M_Sequence*` methods are lifecycle-only adapters.

**Release ownership and act-or-explain (§7.2.1, §7.6, §7.8):**
- Define a condition at the lowest module with enough semantic context. Reusable release logic consumes
  HAL/child/domain contracts, never project raw-I/O GVLs or unrelated application globals. Parents append
  child records; they do not copy the Boolean under a new description.
- `CommonManRelease`/`AllOk` are convenience summaries, never the only diagnostic source. Preserve every
  condition record and qualified owning `SourcePath` so common + active-mode/function-specific failures
  remain individually visible and same-text child conditions are distinguishable.
- A Unit's `Start()` **consumes the BOOL returned by `ReleaseReportStart(Report := HmiResponse.Report)`**
  after the audited access check. Never code
  a second execution predicate beside the report. Compose one common Start set plus optional active-mode
  entry/frontier records; later part/operator/downstream waits stay in the §6.5 pending step record.
- Manual release is common Unit manual conditions AND only the selected target+direction's specific
  conditions. Safety/muting/bridging may be explained read-only but never granted or bypassed here.
- Cross-module, mode-entry, and application-policy conditions **shall be visibly project-owned** under the
  affected Unit branch (normally `Release`/`Permissives`), not hidden in a reusable library. Expose named
  condition state and feed the one authoritative Unit release report. Device-intrinsic conditions stay in
  the reusable CM/EM that has the semantic context to own them.

**Code grouping & sequence distribution (§4.2, §6.7):**
- Application project folders follow the **instance tree**, not artifact types: `00_System` (MAIN,
  raw I/O GVLs, safety aliases, hardware driver, domain coordinator, sim plant) then one
  `0N_<UnitName>` folder per root Unit holding that Unit's application engineering data
  grouped into owner-local roles (`Sequences/Mode|Sub`, `Release`, `Recipes`, and `Io`).
  Never create application-wide POU/DUT/sequence buckets. `Fraktal_Press_Demo` is the model.
- Reusable libraries are type—not instance—collections: keep the type/owner relationship obvious, but do
  not copy a reusable implementation into each application branch. TwinCAT methods stay under their owner
  FB; do not add forwarding POUs merely to manufacture a folder.
- A deployed Unit's concrete mode chains and cross-module release policy belong to its application branch.
  A library may offer an abstract helper, reusable sub-sequence, or opt-in generic default, but it shall be
  explicitly selected and extendable/replaceable; a library shall not silently make AUTO/HOME/CHANGEOVER
final for the project. In the internal Press test bench, `FB_PressDemoUnit`, `Sequences/`, and `Release/` all live
  under `Fraktal_Press_Demo/01_PneumaticPress` while `Fraktal_Modules` supplies the reusable device modules.
- Every chain has one owner and one step-state writer: an ST chain with application logic inside its
  `CASE _step OF` step branches plus a lifecycle-only `_M_Sequence<Mode>` adapter = continuous Unit mode
  (default form on `FB_SequenceBase`);
  EM/CM command dispatch = finite public command through §6.1; `_M_Seq<Name>` = owner-private finite
  sub-sequence with no module/OPC UA identity. The call graph is acyclic and two chains never command the
  same child in one scan. Promote a sub-sequence to an EM when it needs independent commandability,
  concurrency, recipe/lifecycle/diagnostic identity, or reuse by unrelated owners.
- A sequence POU **extends `FB_SequenceBase`** (§6.8(a)): it supplies the `_step` token,
  `M_Step`/`M_Await`/`M_Gate`/`M_TryIssue`/`M_Delay`, the part/decision/completion forwards, the shared
  `_retVal : E_StepResult`, and `M_Advance`. Each `_step` branch is `_retVal`'s only writer and ends with
  `M_Advance(OnAdvance := <next>)` (optional `OnJump<n>` for §6.10 branches), which advances and clears
  the step-scoped latches. The owning Unit already implements `I_SequenceHost` (base) — pass `THIS^` at
  the sequence's `Setup`; do not create per-project host interfaces or per-step transition Booleans.
- Extract a coherent chain when reused, branch/cleanup-heavy, or materially clearer—not every step. The
  caller supplies a `BaseStepNo` window and publishes the private progress through the normal step record.
  In the press, AUTO/HOME/CHANGEOVER embed the shared `FB_PressDemoLoadPosition`; never copy that motion chain.
- Cross-standard orientation (Bosch **Nexeed** reference, `NexeedReferenceOnly/`; decisions documented in
  `Specification/NEXEED_REFERENCE_INSIGHTS.md`): `SqM` ≈ mode sequence, `SqC` ≈ module command, `SqS` ≈
  private sub-sequence, location folders ≈ §4.2 ownership. Do **not** import Unit+Extension duplication,
  per-step wrappers, opaque summed releases, PLC-authored HMI visibility, direct raw-global coupling, or
  ordinary-PLC safety bridging. Fraktal base classes, hooks, condition records, and safety boundary own those.

**Testing (§5.7):** every reusable module **type** ships a TcUnit suite run against the sim HAL in CI.
Rows **T1** (handshake + Execute-drop reset) and **T4** (abort, no self-resume) are proven **once** in
`FB_Base_Tests` for every inheriting type — **do not re-test them per type**. A type earns T2 (first-out
reason + SourcePath), T3 (interlock withholds output), T5 (recipe migrate-or-fault). T10 proves once that
the Unit base consumes its release report; any Unit adding mode-entry conditions exercises one of them.
`Fraktal_Tests` and `PressTests` run only on an isolated test runtime/ADS port with Autostart Boot Project disabled;
never deploy either as the machine boot application. On TC3, fill large bounded records such as
`ST_ReleaseReport` through caller-owned `VAR_IN_OUT` storage—nested by-value returns can overflow the
bounded task stack.
SIM-only force hooks compile out of release builds.

---

## 4. HMI editing guardrails

**The HMI is generic and data-driven (§3.10(a′), §3.13, `HMI_CONTRACT.md`):**
- It binds **published data, never properties/methods** (those are invisible to OPC UA). A node is a module
  iff it has a `Status : ST_ModuleStatus` member. Adding a module type adds HMI automatically — **do not
  write per-station/per-type screens.**
- The UI binds only `PlcRepository` (`lib/data/plc_repository.dart`). `SimRepository` is the shipped live
  demo; OPC UA (FFI) and a WebSocket/REST gateway (for Web) are swap-in adapters behind the same interface.
- **Enum ordinals in `lib/domain/types.dart` are the PLC contract** — they must match the Core DUTs
  (`E_Mode`, `E_ExecState`, `E_NodeState`, `E_ChannelDir`, `E_ChannelKind`, `E_GatedAction`, …). Verify
  them first when changing either side.
- Dependencies are deliberately narrow: Flutter SDK localization, `file_picker`,
  `pdfrx`, `cupertino_icons`, and the Dart-team `ffi` package for the normative
  native OPC UA adapter. Native code must remain behind conditional imports;
  Web uses the versioned gateway protocol. Do not add further packages without
  a spec-backed need and a cross-platform review.
- A packaged gateway may serve the exact compiled Web HMI with `--web-root` as
  well as `/fraktal`. Keep both on one origin: a release Web build derives
  `ws://`/`wss://<page-origin>/fraktal` automatically, while Chrome debug keeps
  the explicit loopback development endpoint. The gateway remains loopback-only;
  remote Web access belongs behind an authenticated same-host HTTPS/WSS proxy.
- Connection ownership precedes the operator shell: `ConnectionBootstrap` opens the wizard until an endpoint has reached `LIVE`, removes the interactive HMI immediately on `STALE`/`DOWN`, and exposes connection editing only after 30 s without `LIVE`. Never bypass this gate or queue writes across reconnect.
- Module details are tabbed and data-driven. Overview/Description are standard; typed category data may add Motion/Vision/Code Reader/RFID tabs. ADMIN-authored custom/guidance controls select compatible current-module scalar tags through autocomplete and use only the existing PLC-validated repository actions—never add arbitrary OPC UA writes or station screens. Scalar/LED/input controls bind one tag; charts bind at most eight numeric tags. Custom tab icons and an optional fitted/aligned/margined Overview background are portable presentation data. Guidance is triggered by `CurrentStep` but never advances a PLC step by dismissal. The portable customization bundle includes layouts, bindings, access policy, images/PDFs, and localization overrides; it deliberately excludes connection settings and session/credentials. Import remaps only deterministic module-path changes and preserves ambiguous paths as deferred content—never discard profiles merely because the live project structure changed (`HMI_CONTRACT.md`, `LOCALIZATION_AND_MODULE_CONTENT.md`).
- Custom controls preserve OPC UA DataValue quality/type/timestamps: Bad/Uncertain values remain linkable but render unavailable, do not feed trends, and cannot enable inputs. Use responsive width presets and flow layout, not persisted pixel coordinates. ADMIN edits stay in a local undoable draft until explicit Publish; publish/rollback retains at most 20 revisions per module and exports them in customization schema 4. Manual/decision buttons come from live PLC catalogs, target the current canonical module/root, optionally confirm, and wait for acknowledgement; ignore imported legacy free-form target paths.
- Wizard step 2 assigns one or more discovered root Unit paths to this HMI. `ScopedPlcRepository` enforces that scope for reads and writes; only an authenticated ADMIN may edit it later.
- The write surface is deliberately narrow: `Command`+`Execute`/`Abort`, `DecisionAnswer`, Unit
  mode/start/stop, manual commands, channel force — all release-gated (§7.6/§7.7) and re-checked by the PLC.
  **Hold-to-run over HMI is non-safety** (no dead-man).
- I/O identity is structured data: `ST_IoChannel.Name` and `ST_Diagnostic.IoTag` **shall equal the
  approved electrical/I/O-list tag verbatim**. Localize only `DescriptionKey`/`Diagnostic`; preserve
  `Address`, unique `Path`, and owning `ModulePath` so alarms cross-link to fieldbus channels.

---

## 5. Build, run, test

For a first project or first deployment, read and follow
`Specification/FIRST_PROJECT_AGENT_GUIDE.md` completely. Keep compile, target,
runtime, OPC UA channel/session, namespace authorization, Fraktal discovery,
mailbox acknowledgement, and PLC acceptance as separate checkpoints. Once the
module tree is live, diagnose failed controls from the `HmiRequest` write/commit
and `HmiResponse` acknowledgement/diagnostic path—do not restart from ping.

**Initial setup on a fresh machine or PLC** — condensed ordered checklists are in
`FIRST_PROJECT_AGENT_GUIDE.md` §11 (11.1 single-PC development bring-up; 11.2
brand-new Beckhoff CX/IPC). The one non-obvious blocker they name: TF6100 5.x
(TwinCAT 4026) publishes **no** Data Access namespace until a one-time
**Trust-On-First-Use initialization** is completed from the OPC UA Configurator
over a *secured* endpoint (`Basic256Sha256`/`SignAndEncrypt` + `UserName`); an
uninitialized server looks exactly like a symbol/port fault (`Objects` shows only
`Server` + `Initialization`, HMI sees 0 root Units). Initialization disables the
Anonymous token, so re-add Anonymous for the commissioning HMI; and on a
usermode/standalone runtime pre-create the admin OS user (`net user … /add`)
before initializing because the restricted server cannot create it itself
(§7.0). Dev-PC extras: Windows Developer Mode for `flutter run -d windows`; a
TF6100 7-day trial license (else `DEMO mode`); enable the PLC project **TMC File**
so `Port_<ADS port>.tmc` is generated.

**PLC (TwinCAT 3, 4024+):** a `.plcproj` is added *into* a TwinCAT XAE solution, not opened directly:
create a TwinCAT XAE Project in TcXaeShell/VS, right-click **PLC → Add Existing Item…** → the `.plcproj`.
Before any XAE work, read `Specification/TWINCAT_XAE_WORKFLOW.md`; it is the
authoritative interaction/evidence procedure. Its mandatory distinctions are:

- nested IEC **Build/Rebuild** proves the selected PLC/platform and may regenerate
  TMC; **Check all objects** compiles every object but is not a full system build;
- `tools/Invoke-TwinCatBuild.ps1` performs only isolated hidden-XAE
  `CheckAllObjects()` plus the boot-autostart assertion—it never selects a target,
  activates, downloads, runs tests, or installs a library;
- `CheckAllObjects()` itself exposes only its Boolean. For diagnostics, use the
  matching `EnvDTE80.DTE2` interface—not the base DTE wrapper—and capture both
  `ToolWindows.ErrorList.ErrorItems` and the DTE Build Output pane. The maintained
  script does this and, on the pinned 4026/VS18 host, captures the PLC rows and
  coded compile transcript headlessly. Zero captured rows never override
  `FALSE`; use the cleared visible PLC Error List UTF-8/TSV export as fallback.
  See workflow §5.1–5.3;
- build/install in dependency order: open only `Framework/FraktalCore.slnx`, build
  and **Save as library and install**, close it; then do the same with
  `Framework/FraktalModules.slnx`; verify the exact versions in **PLC → Library
  Repository**, then close/reopen every consumer so placeholders reload;
- source-library projects shall never coexist in a solution with consumers of the
  installed versions, and PressTests shall never coexist with the Press bench;
- runtime tests are a separate manual/runner-owned gate on an isolated target:
  verify target/ADS/autostart, Activate Configuration, PLC Login/download, PLC
  Start, capture the event log, match runner+counts+zero failures, then stop/Config;
- archive revision, XAE/XAR/platform/target/ADS identity, raw log, JUnit, TMC and
  source hashes. A wrong-runner green summary is a failed gate-selection check.

There are **two** TcUnit gates and both must be run: `Tests/Fraktal_Tests.plcproj`
(Core + Modules) and `Examples/PressDemo/PressTests.plcproj` (the internal Press integration bench).
They are separate because XAE rejects a `..` segment in a `Compile Include`, so a
manifest in `Tests/` cannot reach `Examples/`. Every Compile path is downward from
its own manifest; the press gate links (never copies) the same Unit/sequences that
ship. A `<Folder Include>` list must mirror the Include directories, not the `<Link>`
paths — XAE creates those folders on disk.
Build order: `Fraktal_Core` first (use `Framework/FraktalCore.slnx`, save/install as library), then
`Fraktal_Modules` (close Core, use `Framework/FraktalModules.slnx`, save/install as library), then the
`Fraktal_Demo`, `Fraktal_Press_Demo`, `PressTests`, and `Fraktal_Tests` applications
(`Fraktal_Tests` needs TcUnit).
Do not leave the Core/Modules source-library projects loaded beside applications that consume their
installed libraries: XAE sees the same source object GUIDs twice and rewrites them in the solution.
Use separate library/application solutions, or unload/remove the library-source projects after install
and before adding the applications. The press sequences are plain ST on `FB_SequenceBase` and need no SFC
library reference. (If you ever add a genuine graphical SFC drawn in the XAE editor, it also needs no
`IecSfc` `.plcproj` reference — the compiler provides `SFCStepType`; an `SFCStepType` cascade means a
machine-generated/malformed chart XML, which is prohibited — author charts in the editor only.) Close
and reopen XAE after changing a `.plcproj` library reference so the in-memory project reloads it.
For the same GUID-ownership reason, never load `Fraktal_Press_Demo.plcproj` and
`PressTests.plcproj` in one XAE solution: the press gate links the exact Press
Unit/sequence/release source files. Use its dedicated isolated test solution,
or unload/remove the Press application before adding the press tests.
The current Core is `0.4.0.0` and Modules is `0.3.0.0`; downstream placeholders are pinned accordingly. Core's minor-version steps include the append-only decision/configuration capability contract and the generated rationalization/host-event contract, while TwinCAT's fourth revision component is reserved for contract-neutral rebuilds (Part II §2.2). They also include the deployed-root-only TF6100 publication change, so regenerate TMC files. Core and Modules must be rebuilt and reinstalled before any application resolves.
If every Modules-owned type is reported
unknown in an application, stop: this is an unresolved/stale `Fraktal_Modules` reference, not a
reason to edit each affected POU. Install Core `0.4.0.0`, resolve/build/install Modules `0.3.0.0`,
then reload the application placeholders and rebuild.
Build warning-clean (§2). The source is a **draft not
yet compiled against a pinned TwinCAT** — see "watch items" below.

**HMI (Flutter):** from `FraktalCore/HMI/` (windows/web platform folders are committed; SDK on this
machine: `C:\Apps\FlutterSdk\flutter` — `flutter` is on `PATH`, so prefer resolving it there rather
than hard-coding a path):
```
flutter pub get
flutter analyze                 # clean as of 2026-08-02 (Flutter 3.44.6, the CI pin)
flutter test                    # 166 passing, 4 intentional live-environment skips
flutter run -d windows|chrome
```
`analysis_options.yaml` is self-contained (no flutter_lints include) per the zero-package policy.

**Gateway + Web HMI deployment:** follow
`Specification/WEB_HMI_GATEWAY_DEPLOYMENT.md`. The platform package command
builds Flutter Web first and includes the exact output beside the gateway:
```
cd FraktalCore/HMI
flutter pub get
cd gateway
dart pub get
dart run tool/build_gateway.dart --clean
```
On Windows this also creates
`build/gateway/installer/FraktalSetup.exe` — a combined installer (PowerShell
WinForms wizard) for the native HMI app and/or the gateway + Web HMI. It queries
the local TwinCAT router for the AMS Net ID and shares that ADS endpoint with
the Gateway by default; clear the checked share option for separate endpoints.
The Windows gateway option can also deploy a pinned,
checksum-verified Caddy HTTPS/WSS proxy, collect/hash browser credentials, write
the exact `--allow-origin`, generate/export an internal LAN-CA root, optionally
trust it for the installing Windows user, add a local-subnet firewall rule, and
supervise both processes from the tray. Local trust never propagates: every
remote browser device must trust the exported public root (or site PKI). Leave
the new-password fields blank on upgrade to preserve site proxy security.
Linux output includes `web/`, the systemd unit, and protected environment
example; its reverse proxy remains site-managed. Build on the target OS.
Production distribution
shall sign binaries
and record hashes. Prove `/livez`, `/readyz`, static `/`, `/fraktal`, Fraktal
discovery, mailbox acknowledgement, and link-loss recovery as separate gates;
never infer PLC readiness from the process or page alone.

---

## 6. Known deferred / watch items — do NOT "fix" blindly

### 6.0 Commissioning gates — read these BEFORE debugging "nothing works"

Two gates in the `VAR CONSTANT` block of `PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo/00_System/MAIN.TcPOU` can make a perfectly
healthy test bench look completely broken. **Read them off the live PLC first**; they have cost multiple
wasted debugging sessions chasing control logic:

| Gate (`VAR CONSTANT`) | When wrong | Symptom |
| --- | --- | --- |
| `CONTROL_CIRCUIT_MAPPING_CONFIRMED` | `FALSE` | `M_WriteOutputs` **forces `_000K951_A1` and `_000K911_A1` FALSE every cycle**. Control On can never energize, so the hardwired N54 D2 relay chain never closes and K985/K986 never enable the valves — **no output moves anywhere**, even though the valve coils are written unconditionally. |
| `USE_SIMULATION` | `TRUE` | `MAIN` calls `IoDriver.M_ClearOutputs()` every cycle, so all physical outputs are held FALSE while the simulation driver still animates the plant — the HMI shows movement, the terminals stay dark. |

They are **`VAR CONSTANT` on purpose: they cannot be changed online.** Defeating a gate requires a
source edit plus a download — a reviewable, auditable act, not a live write from an HMI or ADS client.
Do not "helpfully" convert them back to writable variables.

`MAIN` also publishes inert read-only mirrors named `UseSimulation` / `ControlCircuitMappingConfirmed`,
reassigned from the constants every cycle purely so the gate state stays visible over ADS (the compiler
inlines constants and may publish no symbol). **Nothing reads the mirrors** — writing one online has no
effect, and adding a consumer that reads a mirror would silently re-open the online-write hole.

Diagnose in seconds instead of hours:

```bash
cd FraktalCore/HMI/gateway
dart run tool/probe_sim_flag.dart <amsNetId> [port]   # prints both flags live
```

The tell that separates these from a logic bug: **forcing the output in TwinCAT XAE works.** That proves
the terminal, wiring and process image are fine and the PLC simply is not driving the coil.

`CONTROL_CIRCUIT_MAPPING_CONFIRMED` is a **safety interlock, not a nuisance flag**. It holds the control
coils off until someone verifies the K951/K911 electrical semantics on the real cabinet (per N54 D2,
`SwitchControlOn` and `EnableControlOn` are *distinct* signals, yet both currently receive
`PowerHal.EnableRequestOut`). **An agent must never set it to TRUE** — that is an electrical
verification on live equipment and belongs to the commissioning engineer. Report it and stop.

### 6.1 Deferrals and first-compile caveats

These are recorded honestly in `IMPLEMENTATION_NOTES.md` and the spec. They are **first-compile watch
items or deliberate deferrals**, not bugs to silently change without a compiler or a spec reason:
- Compile-plausibility caveats pending a pinned TwinCAT: `SEL` on STRING, `DINT_TO_TIME`/`TIME_TO_DINT`,
  `TIME_TO_UDINT`, interface `= 0` comparisons, `MID()` arg
  order, `'$R'` terminator escape, `FIND/DELETE` string semantics, `TIME * INT` backoff doubling,
  `AssertEquals_REAL` delta signature in TcUnit.
- The pinned 4024 compiler requires every method input at every call. Optional method inputs are a
  4026+ feature; do not use default-valued method `VAR_INPUT` in this binding.
- A child FB published as a parent's `VAR_OUTPUT` is readable to external ST, but its inputs cannot be
  assigned through that parent output. Route such writes through an explicit method on the child or
  owner; keep direct request-symbol writes for OPC UA clients at the published module node.
- `FB_TemplateCM` (`scaffold/`) is a **copy-template, not compiled** — it is intentionally absent from
  every `.plcproj`. Its tests are born RED on purpose (§5.7).
- `I_EventSink` historian adapters, automated PKI enrollment, Linux/site SSO or
  mTLS reverse-proxy policy, and a shared production document store remain
  deployment adapters. Native OPC UA, the gateway protocol, loopback Web
  hosting, the bundled authenticated Windows HTTPS/WSS proxy, Windows tray
  installer, and Linux systemd packaging are implemented; do not describe them
  as deferred.
- Annexes B/D/G/I predate the base classes and show the *expanded* lifecycle form for pedagogy; a
  conforming type keeps only their `CASE` bodies (§2.2).

When you change code, prefer **anchored edits with a post-assertion** over "if X not in file" idempotency
guards — the latter silently no-op when an old artifact already carries the name (this caused real
compile-blocking regressions; see IMPLEMENTATION_NOTES §24).

---

## 7. Where things live (quick lookup)

| You need… | Look at… |
|---|---|
| The common lifecycle | `PLC/TwinCAT/Framework/Fraktal_Core/BaseClasses/FB_ModuleBase.TcPOU`; tier wrappers are `FB_ControlModuleBase`, `FB_EquipmentModuleBase`, and `FB_UnitBase`; spec §2.2, §6.1 |
| The public module interface | `PLC/TwinCAT/Framework/Fraktal_Core/Interfaces/I_Module.TcIO` (+ `I_Unit`/`I_EquipmentModule`/`I_ControlModule`); spec §3.2 |
| Framework reason codes / constants | `PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL`; spec §8.8 |
| A reusable CM/EM implementation | `PLC/TwinCAT/Framework/Fraktal_Modules/` (cylinder CM, clamp EM); Annexes A/B/C |
| Internal Press test-bench Unit, mode chains, and releases | `PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo/01_PneumaticPress/{FB_PressDemoUnit,Sequences,Release}` |
| CX2030 press I/O and commissioning gaps | `Specification/CX2030_PRESS_IO_MAPPING.md`; physical XTI under `PLC/TwinCAT/Examples/PressDemo/_Config/IO/` and linked symbols in `PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo/00_System/Hardware/` |
| First project / deployment / OPC UA commissioning | `Specification/FIRST_PROJECT_AGENT_GUIDE.md` |
| Web HMI + Windows/Linux gateway installation | `Specification/WEB_HMI_GATEWAY_DEPLOYMENT.md`; detailed switches in `HMI/gateway/DEPLOYMENT.md` |
| Part traceability (§3.16) | `PLC/TwinCAT/Framework/Fraktal_Core/Connectivity/FB_LocalPartCarrier.TcPOU`, `Interfaces/I_PartCarrier.TcIO`, UnitBase `_M_Part*` helpers; Annex E |
| Start a new module type | Copy `PLC/TwinCAT/scaffold/FB_TemplateCM/`, read its `SKELETON.md` |
| HMI↔PLC bind table | `Specification/HMI_CONTRACT.md` |
| HMI domain model (the contract types) | `HMI/lib/domain/types.dart` |
| HMI transport seam | `HMI/lib/data/plc_repository.dart` (+ `sim_repository.dart`) |
| Nexeed comparison decisions (grouping/sequences/releases) | `Specification/NEXEED_REFERENCE_INSIGHTS.md` |
| Why the code differs from the draft spec | `PLC/TwinCAT/IMPLEMENTATION_NOTES.md` |
