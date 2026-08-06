# fraktal-core — Framework Library (Fraktal Core §2.2)

The Fraktal Core base classes, contract types, `FB_PermIntlk`, the base TcUnit suite, and the test-first scaffold — the "lifecycle written once" of Core §2.2/§6.1. Part I (the platform-neutral normative standard) is `Fraktal_Core_Part_I.md`; this library is its reference implementation on the TwinCAT 3 binding (Part II, `fraktal-tc3`).

> **Baseline (2026-08-02): Core `0.4.0.0` / Modules `0.3.0.0` build clean and their
> TcUnit gates are green.** All three PLC projects returned `LastBuildInfo=0` with an
> empty Error List and regenerated their TMC files, and both isolated-runtime gates
> pass — **92/92 tests across 28 suites** (Core+Modules 84/26, internal Press bench 8/2),
> repeated on a Windows 10 x64 VM. Summaries, runner identities and artifact SHA-256
> hashes are archived in `../../../Specification/Evidence/`.
>
> Separately, an earlier snapshot was deployed to a development runtime and exercised
> end-to-end over TF6100 (Press bench cycling; generic HMI commanding; `QUERY_CONFIG`
> config manifest and `OPC.UA.DA` publication obscuring confirmed). That live result is
> framework-integration evidence on a development runtime — not a machine acceptance,
> safety or production claim, and not re-run against this snapshot. See
> `../../../Specification/OBJECTIVES_AUDIT.md`. Per Core §2 / TC3 §2.1 pin your exact XAE/XAR build; the
> plcproj files target 4024+ (ABSTRACT FBs/methods). The sources are kept **source-compatible with
> TwinCAT 3.1.4024**: no optional/defaulted method inputs (a 4026+ feature) — every method input is
> passed explicitly at every call site (see `IMPLEMENTATION_NOTES.md` §62/§64/§69). File an issue for
> anything a pinned compiler rejects.

## Layout

```
Framework/
  Fraktal_Core/              the Core library (save/install as a versioned library)
  Params/PL_Fraktal.TcGVL      framework constants
  DUTs/                        E_ExecState · E_Reason (§8.8 framework bands) · ST_Diagnostic ·
                               step/condition/decision records (§6.5, §6.9(b), §6.11) ·
                               part context (§3.16) · mode/module enums
  Interfaces/                  I_Module · I_Unit · I_EquipmentModule · I_ControlModule ·
                               I_RecipeProvider (§3.8) · I_DeviceConnector (§3.15) ·
                               I_PartCarrier (§3.16) · I_VerdictProvider
  PermIntlk/FB_PermIntlk       the §7.2 container (Define / SetBypass / ClearBypass / Diagnostic)
  BaseClasses/                 FB_ControlModuleBase · FB_EquipmentModuleBase · FB_UnitBase
                               (template method: a type overrides ONLY _M_Dispatch — §2.2;
                               the Unit base adds modes/cascade, the step chain + stall walk,
                               and the wired-in cycle profiler §6.2/§6.9/§8.11.4)
  Connectivity/                FB_DeviceConnectorBase (§3.15, T7 once) · FB_LocalRecipeProvider (§3.8)
  Platform/F_Now               [TC3] synchronized-clock read (§2.7)
  Platform/F_TimingUpdate      §8.11.4 timing aggregate math (pure, unit-tested)
  BaseClasses/FB_CycleProfiler §8.11.4 cycle waterfall + per-step stats + time-class split
                               (WorkTime = real cycle time; fed by _M_SetStep)
  Fraktal_Modules/           reusable module library
  FraktalCore.tsproj           XAE solution for the Core library alone
  FraktalModules.tsproj        XAE solution for the module library alone
  TwinCAT Fraktal.tsproj       XAE solution loading both libraries together
Examples/                    example applications, one solution folder each
  CoreDemo/Fraktal_Demo/      two-root smoke application (§3.1a; sources only,
                               no .tsproj — add it to a solution to build)
    PressDemo/                 internal Fraktal feature-testing bench
    PressDemo.tsproj           the XAE solution (PressDemoX32 = 32-bit variant)
    Fraktal_Press_Demo/        simulated test-bench PLC project (not a real project)
    PressTests.plcproj         the bench's integration gate (own solution)
    PressTests/                FB_PressDemoUnit_Tests · FB_FaultRecovery_Tests
    _Config/IO/                exported physical I/O configuration
Tests/                       the aggregate Core + Modules gate, self-contained
  Fraktal_Tests.plcproj      its manifest (every Compile path downward)
  FraktalTests.tsproj/.slnx  its XAE solution (ADS port 851)
  Fraktal_Tests/             aggregate TcUnit test sources (§5.7)
    FB_ProbeCM / FB_ProbeEM    minimal concrete probes for the bases
    FB_Base_Tests              T1 · T2 · T4 (+ rollup/T6 at base level) proven ONCE
    FB_PermIntlk_Tests         first-out ordering · bypass rules
    FB_Timing_Tests            §8.11.4: exact math · classified cycle publication · command rows
    PRG_TcUnitRunner           TcUnit.RUN() — driven headless by TcUnit-Runner (TC3 §5.7)
  tools/                     source audits (e.g. Test-OpcUaPublication.ps1)
scaffold/FB_TemplateCM/      "new CM type in 30 minutes" — pre-wired, initially RED (§5.7)
IMPLEMENTATION_NOTES.md      every reconciliation vs. the drafts + proposed Core §3.2 amendments
```

## Bring-up (first compile)

The authoritative interaction and evidence procedure is
`../../../Specification/TWINCAT_XAE_WORKFLOW.md`. It records the exact
Core→Modules save/install order, nested-build versus `CheckAllObjects` boundary,
hidden-XAE automation, isolated-runtime download/run sequence, and the 2026-08-01/02
execution history.

> A `.plcproj` is **not** opened directly like a solution — it is added *into* a TwinCAT
> XAE project. Verified on TwinCAT 3.1 4024.x (TcXaeShell): create/open a TwinCAT solution,
> then right-click the **PLC** node → **Add Existing Item…** → select the `.plcproj`.
> x32 vs x64 XAE does not matter for compiling; it only selects which local runtime
> (TwinCAT System Service) the shell pairs with. 4024.75 is fine — 4024+ is required
> (ABSTRACT FBs/methods).

1. Open the dedicated 4026 wrapper `Framework/FraktalCore.slnx`, or in TcXaeShell create a
   TwinCAT XAE Project and add `Framework/Fraktal_Core/Fraktal_Core.plcproj` beneath its `PLC` node.
   The referenced Beckhoff
   libraries (`Tc2_Standard`, `Tc2_System`, `Tc2_Utilities`, `Tc3_Module`) resolve from the
   local repository automatically (they are placeholder references, `*` version).
2. Build warning-clean (Core §2), then **Save as library** and install; consumers pin the
   version (§2.2/§5.4). If the compiler rejects a construct, check the watch-item list in
   `IMPLEMENTATION_NOTES.md` §8 — these are known first-compile candidates, fix at source.
3. Close the Core wrapper, then open `Framework/FraktalModules.slnx`, or add
   `Framework/Fraktal_Modules/Fraktal_Modules.plcproj` to another otherwise-empty XAE solution.
   It references the installed `Fraktal_Core`; build it, then save/install it as a library. It
   deliberately has no task or `MAIN`.
4. Add either executable fixture: `Examples/CoreDemo/Fraktal_Demo/Fraktal_Demo.plcproj`, or
   `Examples/PressDemo/Fraktal_Press_Demo/Fraktal_Press_Demo.plcproj` for the pneumatic press.
   The ready-made 4026 system project is `Examples/PressDemo/PressDemo.slnx`
   (`PressDemo.tsproj`); `PressDemoX32.sln` is the legacy XAE-shell wrapper. Open
   one wrapper only—both point at the same Press PLC source project.
5. Open the dedicated `Tests/FraktalTests.slnx`, or
   create a **separate XAE solution** and add `Tests/Fraktal_Tests.plcproj`;
   install **TcUnit** (tcunit.org) first. Then run the press gate too:
   `Examples/PressDemo/PressTests.slnx`. Never load `PressTests` beside the Press
   Demo project: it links the exact Press source objects and duplicate GUIDs make
   TwinCAT rewrite those files. Each `PlcTask.TcTTO` calls its runner. Run only on an isolated
   test runtime/ADS port and leave **Autostart Boot Project disabled**. Start it
   deliberately, harvest the result, and stop it; never make it the machine boot
   application. All suites green is the M1 acceptance bar.
6. Wire TcUnit-Runner into CI so the JUnit results gate the merge alongside lint (Core §6.8, §1.5).

## Writing a sequence: ST, SFC or LD

A chain is a chain: it extends `FB_SequenceBase`, records steps with `M_Step`, and
progresses through the shared result `_retVal`. Only **who evaluates the
transition** differs, and everything else follows from that one fact.

| | **ST** | **SFC** | **LD (integer state machine)** |
|---|---|---|---|
| Owns the transition | `M_Advance` | the SFC runtime | the rungs |
| Body of the POU | `CASE _step OF` | the chart | rungs gated on `_step` |
| Step body lives in | a `CASE` branch | an **ACTION** | an **ACTION** |
| Calls `M_Advance`? | **yes**, ends every branch | **no** | **yes**, from the action |
| Transition condition | (inside `M_Advance`) | `_retVal = E_StepResult.ADVANCE` | (inside `M_Advance`) |
| A jump is | `OnJump1 := <step>` | a branch whose condition is `_retVal = E_StepResult.JUMP1` | `OnJump1 := <step>` |
| Clears `_retVal` | `M_Advance`, on commit | `FB_UnitBase` per scan | `M_Advance`, on commit |
| Overrides `M_ChainRun`? | yes (that is the body) | no — its body *is* the chart | yes |

The per-scan clear is never a project's job: a chain registers itself in
`M_Attach` and `FB_UnitBase._M_BeginSequenceScan` resets every attached chain
before `_M_Dispatch` runs (§1.1 O1). An SFC chart needs **no wiring at all** to be
safe against a stale `ADVANCE`.

`Fraktal_Press_Demo` ships the AUTO chain in ST (`FB_PressDemoAuto`) and SFC
(`FB_SFC_PressDemoAuto`) so the two can be compared side by side. **The `FB_SFC_`
prefix is not a naming convention** — it exists only so two renditions of one
chain can coexist in one project. A real project has one chain per mode and names
it `FB_<Thing><Mode>`.

### Building an SFC chart

The chart graph is drawn in XAE. A `.TcPOU` SFC body is a serialized object graph
(`SFCImplementationObject` → `SFCSegment` → `SFCElementList`), and synthesising
one by hand is not worth attempting — a malformed archive is worse than none
because it still looks like a finished file. Draw the steps and transitions; the
rest is mechanical and can be scripted.

1. **Write the step bodies as ACTIONS.** `MainAction` resolves to an *action* of
   the POU, never a method. Each action is the ST branch **minus** its
   `M_Advance` call: an action only produces `_retVal`.
2. **Name a step `N<StepNo>`, and its action `A<StepNo>_<What>`.** The step carries
   the same number the step record publishes (`M_Step(StepNo := 200)` → step `N200`
   → row `N200` on the §3.13 chart → `200:` in the ST twin), so one step number
   reads identically in the chart, the code, the operator's flow chart and a stall
   message. The action keeps the `A` prefix precisely so the two never blur: in the
   archive a step and its `MainAction` are different objects, and `N200` bound to
   `A200_RamDown` says which is which at a glance. A step's "wait at the join"
   placeholder follows the same rule (`N250` → `_aN250_active`).
3. **Every transition is `_retVal = E_StepResult.ADVANCE`**, except a jump branch,
   which is `_retVal = E_StepResult.JUMP1` (`JUMP2`/`JUMP3` for further branches).
4. **Bind each step's `MainAction`.** The attribute is
   `{700a583f-b4d4-43e4-8c14-629c7cd3bec8}`.

**Read the archive's own descriptor table; never guess an attribute.** Each step
carries ten attributes and *five* of them are empty strings. The archive maps
every GUID to an identifier and a description, so the binding target is a lookup,
not an inference:

| Attribute | GUID |
|---|---|
| `Name` | `{38391c6d-6d4a-42f8-8ee7-9f45e5adafa8}` |
| `Comment` | `{7d894980-aeea-405c-a0f6-e2b26429c58f}` |
| `Exclude` | `{01580b27-6378-448b-8ecb-0e4b795b58d6}` |
| `InitStep` | `{6844a48e-46c2-4cc8-a185-a478f3b99cc0}` |
| `Duplication` | `{62e1754b-7629-4e63-9cec-10ae0c536f1f}` |
| `MinTime` | `{cacf1a68-236e-47c2-b7b1-1cf9199718cb}` |
| `MaxTime` | `{b693554c-1b01-4a8d-afde-9e3a46f7465d}` |
| **`MainAction`** | **`{700a583f-b4d4-43e4-8c14-629c7cd3bec8}`** |
| `EntryAction` | `{a6b08bd8-b696-47e3-9cbf-7408b61c9ff8}` |
| `ExitAction` | `{a2621e18-7de3-4ea6-ae6d-89e9e0b7befd}` |

**`MainAction`, not `EntryAction`.** Step bodies poll child `Done` flags and
timers, so they must run *every scan the step is active*. An entry action runs
once on activation, and a chain wired that way stalls at its first step forever —
which reads as a hung machine, not a wiring mistake.

### Parallel branches (§6.12)

Two work positions that run at the same time and independently. There are two
forms; **prefer the first** unless the chart itself is the clearest documentation.

**Sub-chain fork — every language, including ST.** Each leg is an ordinary chain,
so it brings its own step pointer, transition result and step-scoped latches, and
nothing about it has to know it runs beside another. One step forks and joins:

```iecst
500: M_Step(StepNo := 500, StepName := 'project.step.bothPositions', Awaits := 0,
         AwaitingLabel := '', TimeClass := E_TimeClass.WORK, ExpectedTime := T#0S);
     M_RunPar(Chain := _positionA, BaseStepNo := 600, Branch := 1);
     M_RunPar(Chain := _positionB, BaseStepNo := 700, Branch := 2);
     _retVal := M_ParJoin();
     M_Advance(OnAdvance := 999);
```

`M_ParJoin` commits only when every leg run that scan reports `Done`. The leg list
is the calls themselves — nothing to register, nothing to forget when a leg is
added. Worked example: `FB_ProbeParChain` / `FB_ProbeLeg` / `FB_SequencePar_Tests`.

**Native divergence — drawn in the chart.** In XAE, select the transition after
the forking step and insert a *parallel branch*. In the archive the two shapes are
told apart by what each leg starts with:

| | leg starts with | meaning |
|---|---|---|
| `SFCBranch` whose legs open with `SFCTransition` | a transition | **alternative** (one leg runs) |
| `SFCBranch` whose legs open with `SFCStep` | a step | **parallel** (all legs run) |

Rules for a natively drawn leg:

1. **Every leg step names its leg on its own step record:** `Branch := 1` as the
   last argument of `M_Step`. That is what keeps this leg's issue latch, delay and
   message separate from the main line's, so both can command their own children in
   the same scan. Main-line steps omit it — it defaults to this chain's own leg, so
   a leg written as a sub-chain never mentions a branch either. (Under the legacy
   `FRAKTAL_TC3_4024` profile there are no defaulted method inputs, so a 4024 build
   writes `Branch := 0` at every `M_Step`, as it already does for `M_Advance`.)
2. **A leg's transitions read `_conRetVal[n]`**, not `_retVal`. The main line keeps
   `_retVal`. Both are cleared once per scan by the base.
3. **Every leg needs a terminal step to wait in.** A parallel branch joins only when
   all legs have reached their last step, so the main line needs one too — that is
   what `A250`/`A310` are in `FB_SFC_PressDemoAuto`.
4. **The join transition reads every result**, e.g.
   `_retVal = E_StepResult.ADVANCE AND _conRetVal[1] = E_StepResult.ADVANCE`.
5. **Number every leg; none is "the main line".** A two-leg fork uses legs 1 and 2.
   Leaving one on branch 0 makes the chart draw it unindented, as if the other leg
   were subordinate, and leaves `_retVal` meaning one thing inside the fork and
   another outside it. `_retVal` is the line before and after; between them there
   are only legs.
6. **A composite step inherits its leg.** `M_RunSub` takes no branch argument — the
   sub-chain runs on whatever leg the calling step is on, because `M_Step` already
   set that. Press AUTO `A240` runs the load-position chain from leg 1 and its four
   steps publish as leg 1.
7. **The fork sits on a chain's main line.** Nest by making a leg a sub-chain
   instead — that form nests without limit.

### Writing a Ladder sequence rung by rung

A ladder chain is an **integer state machine**: one rung per state, dispatched on the
inherited `_step`, and the rung writes the next state itself. `FB_LD_PressDemoAuto` is
the worked example; it extends `FB_SequenceBase`, the same base an ST or SFC
chain uses.

**Use `EN`/`ENO`, not a `Run` facade.** A ladder box only executes on power flow, and
XAE already supplies that for **any** method box: enable `EN` and the box gains an
`EN` input and an `ENO` output. The base method is called directly —

```
BOX "M_Step"   params=['EN', 'StepNo', …]  returns=['ENO']          EN=true
BOX "M_StepLd" params=['Run','StepNo', …]  returns=[]               EN=false
```

— so `M_Step`, `M_Await`, `M_RunSub` and **every method on every developer-written FB**
are callable from a rung with no library change at all. This is the only approach that
scales: a project may define or extend module types freely, and adding a hand-written
`…Ld` twin per method per type does not.

> **`FB_SequenceBaseLd` has been deleted.** Its 27 `Run : BOOL` facades were
> reinventing `EN`. They existed because adding an input to an override is
> `C0094: Interface of overridden method doesn't match declaration`, which forced the
> distinct `Ld` names — but `EN`/`ENO` adds no parameter, so the signature never
> changes, so no facade and no renaming was ever needed. A ladder chain now extends
> **`FB_SequenceBase`**, exactly like an ST or SFC chain; `FB_LD_PressDemoAuto` is the
> worked example. `convert_ld_boxes()` in `tools/ld_rung_gen.py` performed the
> migration and is kept for any chain still carrying the old form.
>
> Removing a type from a released library is a breaking change. Core's version was
> **not** stepped for it because no shipped chain outside this repo consumed the
> facade; a downstream project that did must migrate with `convert_ld_boxes()` before
> resolving Core again.

Two consequences worth knowing before editing an `EN`-gated box:

- **A value-returning box has TWO outputs: `ENO` first, then the return value.**
  `M_Await` reports `returns=['ENO','M_Await']`. Wiring the result into slot 0 puts it
  on `ENO` and leaves the real output dangling; wiring the wrong variable into slot 1
  compiles clean and silently strands the intended one. That is a defect no gate
  catches — see the `_partReady`/`_airReady` trap below.
- **`EN := FALSE` means the box is not executed at all**, so its output variable keeps
  its previous value. A `Run := FALSE` facade call still *ran* and wrote its fail-closed
  default. Inside a rung gated on `EQ(_step, N)` the two are equivalent, because the
  variable is only read by that same rung — but a value read outside the rung differs.

**The two rung shapes.** Everything in a chain is one of these.

*Pure logic* (initialise, wait on conditions, complete):

```
[EQ(_step, 100)]──┬──[M_StepLd  StepNo:=100, StepName:='…', Awaits:=0,
                  │              AwaitingLabel:='', TimeClass:=…, ExpectedTime:=…, Branch:=0]
                  ├──[_partReady := M_AwaitLd(Idx:=1,
                  │              Label:='project.condition.partPresent',
                  │              Ok:=sensor.OutImm.Value AND sensor.OutImm.Quality)]
                  ├──[_airReady := M_AwaitLd(Idx:=2, Label:='…', Ok:=…)]
                  ├──[_twoHandReady := M_AwaitLd(Idx:=3, Label:='…', Ok:=…)]
                  ├──[_startReady := NOT requireTwoHand OR _twoHandReady]
                  └──[_partReady AND _airReady AND _startReady]──[MOVE 110 → _step]
```

*Commanding a child* (most steps — this is the N110 shape):

```
[EQ(_step, 110)]──┬──[M_StepLd  StepNo:=110, …, Awaits:=_pressRam,
                  │              AwaitingLabel:='PressRam.RETRACT']
                  ├──[M_TryIssueLd Steppable:=TRUE]──┬──[_pressRam.Command := E_CylinderCommand.RETRACT]
                  │                                  ├──[_pressRam.Abort   := FALSE]
                  │                                  └──[_pressRam.Execute := TRUE]
                  └──[_pressRam.Done]────────────────┬──[_pressRam.Execute := FALSE]
                                                     └──[MOVE 130 → _step]
```

A **jump** is not a special construct: it is a second `MOVE` under a different contact
in the same rung (`_pressRam.Error` → `MOVE 210 → _step` beside `Done` → `MOVE 220`).
A **terminal** step calls `M_Complete()`/sets `Done` and does not `MOVE`.

**Never nest a value-returning facade box.** Assign each `M_AwaitLd`,
`M_PartReceivedLd`, decision, or other value-returning call to a declared variable of
the exact return type, then combine those variables in a separate logic box. `Run` is
the box's rung-power/execute input; it is not an accumulator for the previous call's
Boolean result. Every active named wait must execute independently on every scan so
the complete diagnostic set remains published.

Why this is a hard rule: XAE lowers a nested graphical output to a temporary named
`ImpVar<BoxId>_<output ordinal>`. In the broken N100 archive,
`ImpVar597_1` is the return of `M_AwaitLd` box ID 597 feeding OR box 612, and
`ImpVar616_1` is the return of `M_AwaitLd` box ID 616 feeding the `Run` pin of outer
`M_AwaitLd` box 614. TwinCAT could not type those nested method temporaries. The
names were editor-generated, but they were not opaque: their box IDs locate the
offending nodes in `<NWL><XmlArchive>`. Flattening the calls also restores the ST/SFC
semantics—three independent result assignments followed by one combined transition.

**Rules that differ from ST.**

1. `M_TryIssueLd` is what re-arms per step — the issue latch is cleared by `M_Step`
   on a step-number change (a chart language never reaches `M_ClearTransition`).
2. No `M_Advance`, no `_retVal`. The rung writes `_step` directly; that is the
   idiomatic ladder transition and rule S1 accepts it (it requires a step record plus
   *some* way to move, not a nominated one).
3. Drop the child's `Execute` in the same rung that leaves the step — §6.1's
   Execute-drop reset is what returns the child to READY.

**Do not synthesise the body from nothing.** A `<NWL>` network is a serialized object
graph of `BoxTreeBox`/`BoxTreeOperand`/`BoxTreeDemux`/`BoxTreeAssign` nodes with `Id`
identities and `VarId` power-rail nodes — roughly 40 kB per rung. Hand-writing one is
not viable and cutting nodes with a regex has produced a file that stayed plausible
while ceasing to be well-formed XML. What *is* viable is **cloning a rung that already
compiles** — see the next section. After any edit, verify with `CheckAllObjects` (see
`Specification/TWINCAT_XAE_WORKFLOW.md`) — the press demo resolves only once Core and
Modules are installed as libraries.

### Generating a rung by cloning a worked example

`tools/ld_rung_gen.py` generates rungs; `tools/test_ld_rung_gen.py` is its gate. The
method is deliberately narrow, and the narrowness is what makes it safe:

1. **Split, never parse.** The archive carries `xml:space="preserve"`, so an
   ElementTree round-trip rewrites indentation that is real content. `split_networks`
   scans `<o>` depth and returns the raw blocks *plus the separator between them* —
   rejoining without it yields `</o><o>` on one line, which is still valid XML and
   therefore fails silently.
2. **Clone a rung of the shape you want** and renumber every `Id`/`VarId` into a fresh
   range above the file's maximum. A duplicated `Id` does not fail to parse; it
   silently shadows a node.
3. **Rewrite only leaf operands.** `subst()` matches the `Operand`+`Type` *pair*, so a
   short name cannot match inside a longer one and the type can never drift away from
   the value — that mismatch is exactly `Cannot convert type 'BOOL' to type 'E_VERDICT'`.
   `subst_string()` additionally derives `STRING(INT#n)` from the new literal, so a
   renamed step cannot keep the previous name's declared length.
4. **Every substitution asserts its hit count.** A rewrite that matches nothing reports
   success and changes nothing; `subst()` raises instead. `_pressRam.Execute` occurs
   twice in a command rung (Set coil and Reset coil) — asserting `count=1` there is a
   bug the assertion catches.
5. **Fix `BranchCounter`.** It is the archive's monotonic `VarId` allocator; leaving it
   below a `VarId` that now exists lets XAE hand out a duplicate the next time someone
   opens the chart.
6. **Compile after every rung.** `ImpVar<BoxId>_<n>` in an error message maps directly
   to that node's `<v n="Id">…L</v>`, which locates the fault in seconds — but only if
   you know which rung you just added.

Worked example — the whole of `N130` is `N110` with nine operand substitutions:

```python
rung, next_id, next_var = clone(template_N110, id_base=…, var_base=…)
rung.subst("130", "150", count=1)          # MOVE target FIRST: doing the gate first
rung.subst("110", "130", count=1)          # would collide with the template's MOVE
rung.subst_string("project.step.pressRamUp", "project.step.pressDoorOpen")
rung.subst_string("PressRam.RETRACT", "Door.RETRACT")
rung.subst("_pressRam", "_door", count=1)               # the Awaits operand
rung.subst("_pressRam.Command", "_door.Command", count=1)
rung.subst("_pressRam.Abort",   "_door.Abort",   count=1)
rung.subst("_pressRam.Execute", "_door.Execute", count=2)
rung.subst("_pressRam.Done",    "_door.Done",    count=1)
```

Cloning had one hard limit — **it can only produce box types that already exist
somewhere in the file** — so every rung needing `M_Delay`, `M_AskDecision`, `M_RunSub`,
`M_RaiseWarning`, `M_ReportFromChild` or a child method such as `WithdrawOutputs` used
to stall on "draw one in XAE first". That limit is gone; see the next section. Cloning
is still the shorter route when a rung of the shape you want already exists.

### Declaring a rung instead of cloning one

A `BoxTreeBox` is fully determined by the **declaration of the method it calls**, so
nothing about it has to be copied from anywhere:

| Archive field | Comes from |
|---|---|
| `InputParam.Names` | `EN`, then the `VAR_INPUT` names in declaration order |
| `InputParam.Types` | `BOOL`, then their types |
| `OutputParam` | `ENO : BOOL`, then — only if the method returns a value — the method's own name and return type |
| `OutputItems` | `<n />` when void; otherwise an empty `ENO` slot **then** the return slot |
| `CallType` / `EN` / `ENO` | `Method` / `true` / `true` |

A method on another FB folds the instance into the box type
(`method("_pressRam.WithdrawOutputs", …)`). The operator boxes, the power rails and the
coils are equally mechanical, so `tools/ld_rung_gen.py` provides a small node algebra
and a whole rung is written down:

```python
alloc = Allocator.above(source)                 # Ids above everything in the file
rail  = Rail(alloc.take_var())
items = [
    Wire(rail.var_id, compare("EQ", Term(), Value("_step", "INT"),
                                            Value("215", "INT"))),
    method("M_Step", rail, [("StepNo", "INT", Value("215", "INT")), …]),
    method("M_PartProcessed", rail,
           [("Verdict", "E_Verdict", Value("E_Verdict.NOK", "E_VERDICT")), …],
           returns=("M_PartProcessed", "BOOL"), result="_partProcessed"),
    Coil("_partDispositioned", rail, SET),      # (S)
    Coil("_partInMachine",     rail, RESET),    # (R)
    move(rail, Value("240", "INT"), "_step", "INT"),
]
text = network(items, alloc, comment="N215")
```

- `Term()` is the left power rail; `Wire`/`Rail` are a branch point and its taps, and a
  rung can only branch through them — power flow in the nested `EN` form *is* the
  nesting.
- `Contact` and `Value` are deliberately different types. Both serialize as
  `BoxTreeOperand`, but XAE marks a contact `Boolean`/`Fixed` and a plain BOOL
  *argument* (`Steppable := TRUE`) not, so the type alone cannot tell them apart — and
  in ladder they are not the same thing. `Contact(x, negated=True)` is `--|/|--`.
- `Coil(x, rail, RESET)` is what `x := FALSE` means inside an active step. A *plain*
  coil driven from the step's own rail would write TRUE.
- `result=` on a value-returning `method()` is what makes the ENO trap
  unrepresentable: the return can only land in slot 1.

**The gate for all of it is `tools/test_ld_rung_gen.py`**, which regenerates `N999` —
a rung drawn by hand in the XAE editor — from a declaration and compares it against the
real one node for node, pin for pin and flag for flag. If the emitter can reproduce
what the editor wrote, a rung it emits for a box with no instance to clone is
trustworthy for the same reason.

**Dump the result. A clean compile does not prove a generated node exists.**

```
python tools/ld_dump.py <file.TcPOU>       # every network, as a graph
python tools/sfc_dump.py <file.TcPOU>      # the same for a chart
```

This is not a convenience, it is the verification step. Two failures it catches that
nothing else does:

- an untyped `<o>` — a node lifted out of a `<l2 … cet="BoxTreeBox">` list loses the
  type the list gave it collectively. It parses, it compiles, and the box is simply not
  there. (`network()` writes `NetworkItems` with **no** `cet` so every item states its
  own type.)
- a dead gate. `N215` and `N230` both compiled while reading `EQ(215, 0)` and
  `EQ(230, 0)` — the step number compared against a leftover constant instead of
  against `_step`. Legal IEC, constantly FALSE, no warning from anything.

**Rung order is execution order, and it matters.** A forward transition re-enters any
rung *below* it in the same scan, because the `MOVE` writes `_step` before those rungs
are evaluated. That is normally harmless — the chain simply advances a scan earlier
than the ST twin would — but **not when the two rungs command the same child**: §6.1's
Execute-drop reset needs one scan with `Execute` low, and a Reset coil followed by a Set
coil in the same scan never gives it one. In the press AUTO chain the abort at `N180`
and the reopen at `N185` are the only such pair (both drive the door), which is why
`N185` is placed deliberately **above** `N180` and everything else is in step order.

### Reading and generating an SFC chart

An `<SFC>` body is a different archive from `<NWL>`, and simpler. The skeleton is

```
SFCImplementationObject
└── o n="Root" t="SFCSegment"
    └── o n="ElementList" t="SFCElementList"
        └── l2 n="InnerList"          ← the chart, in order
            ├── o t="SFCStep"         ← EmbeddedMain/Entry/ExitAction, nested
            │                            ElementList, and l2 n="Attributes"
            ├── o t="SFCTransition"
            ├── o t="SFCJump"
            └── o t="SFCBranch"       ← l2 of SFCSegment legs
```

**Everything meaningful is a GUID-keyed attribute**, and the archive ships its own
descriptor table — `<d2 n="Attributes" ckt="Guid" cvt="SFCAttributeDescription">` maps
each GUID to an `Identifier`. Read it from the file rather than trusting this list;
these are the 14 it currently defines:

| Identifier | GUID | Notes |
|---|---|---|
| `Name` | `38391c6d-6d4a-42f8-8ee7-9f45e5adafa8` | step name (`N200`); **on a transition this holds the CONDITION expression** |
| `MainAction` | `700a583f-b4d4-43e4-8c14-629c7cd3bec8` | action run while the step is active |
| `EntryAction` | `a6b08bd8-b696-47e3-9cbf-7408b61c9ff8` | runs once on activation |
| `ExitAction` | `a2621e18-7de3-4ea6-ae6d-89e9e0b7befd` | runs once on deactivation |
| `InitStep` | `6844a48e-46c2-4cc8-a185-a478f3b99cc0` | exactly one step per chart |
| `Parallel` | `23bdaa98-72ec-41f7-817b-9dede5697086` | on a **branch**: parallel vs alternative |
| `Qualifier` | `e174fc0d-80b0-4a9e-a530-ca239c249a50` | action association qualifier |
| `MinTime` / `MaxTime` | `cacf1a68-…` / `b693554c-…` | step active-time bounds |
| `Monitoring` | `8294df19-5962-4dee-a874-1051dabb0e3e` | transition monitoring |
| `Comment` | `7d894980-aeea-405c-a0f6-e2b26429c58f` | |
| `Duplication` | `62e1754b-7629-4e63-9cec-10ae0c536f1f` | copy implementation vs reference |
| `Symbol` | `bc882c11-1e91-4dd8-a6b8-2075724ed18b` | `EnumValue`, not a string |
| `Exclude` | `01580b27-6378-448b-8ecb-0e4b795b58d6` | hidden; excludes from build |

A real step carries **ten** of these — `Name`, `Comment`, `Exclude`, `InitStep`,
`Duplication`, `MinTime`, `MaxTime`, `MainAction`, `EntryAction`, `ExitAction` — and
four are normally empty strings. A transition carries only `Name`, `Comment`, `Exclude`.
Values are typed wrappers: `StringValue`, `BoolValue`, or `EnumValue` (which carries a
`TemplateGuid` before its `Value`, so a regex written for the string form silently
skips it).

Two traps that cost real time:

- **`MainAction` vs `EntryAction`.** Putting the body on `EntryAction` runs it once and
  the chart stalls at its first step forever. `MainAction` is the one you want.
- **The action is a separate POU object.** `<Action Name="A200_RamDown">` is a sibling
  of `<Method>` under `<POU>`; the step attribute only holds its *name* as a string, so
  a renamed action and a step still naming the old one both parse and neither warns.

Fraktal's naming makes the step number the same token everywhere: step `N<StepNo>`,
action `A<StepNo>_<What>` (`N200` → `A200_RamDown`), matching the ST twin's `CASE`
label and the §3.13 row. The differing prefix is what keeps a step distinguishable from
its action object inside the archive.

Because steps and transitions are flat attribute records rather than a wired graph,
an SFC chart is **materially easier to clone than a ladder rung** — retargeting a step
is two `StringValue` edits (`Name`, `MainAction`) with no `Id`/`VarId` renumbering and
no power rails. The same discipline still applies: assert every substitution's hit
count, keep `Id`/`IdParent` consistent, and compile after each step.

Reading an archive is far easier than writing one: dump a body's structure before
touching it (`python tools/sfc_dump.py <file>`, `python tools/ld_dump.py <file>`). Note
that the descriptor `<d2>` is a **dictionary** — alternating `<v>` key and `<o>` value
children, and the values are typed collectively by `cvt`, so none of them carries a
`t=`. A dumper that filtered on `t="SFCAttributeDescription"` printed an empty table and
an empty chart, and looked like a file with nothing in it. The `<NWL>` node grammar
`ld_dump` prints is

```
DEMUX var=N (DEF)  ← defines a power node; its <o n="Input"> is what drives it
DEMUX var=N (ref)  ← every later use of that same rail
OPERAND "x" : "T"  ← Flags 1 = negated contact, 0 = plain
ASSIGN -> "x"{flags=N}   ← 2 = Set coil (S), 3 = Reset coil (R), 0 = plain
BOX "M_Step" params=[EN, StepNo, …]   ← InputItems positionally match params
```

### Traps that cost real time here

- **A `.TcPOU` edit must target one CDATA section.** A method's declaration and
  implementation are separate CDATA blocks. A replacement written against the two
  concatenated matches nothing and reports success — a silent no-op. This bit
  `M_Reset` twice.
- **`_retVal` is a one-scan signal.** In a chart the runtime evaluates the
  transition *after* the step action, so the value must survive the scan and be
  gone before the next one. The framework does this; do not add a manual clear.
- **A chart POU must not override `M_ChainRun`.** Its body is the chart. Only a
  chain used as a composite sub-step (`M_RunSub`) overrides it, and such a
  sub-chain must therefore be ST.
- **`FUNCTION_BLOCK INTERNAL FB_X EXTENDS FB_Y`** is legal; any combination of
  `ABSTRACT`/`FINAL`/`INTERNAL`/`PUBLIC`/`PRIVATE`/`PROTECTED` may precede the
  name.
- **IEC standard function names are reserved as identifiers** — `SUB`, `ADD`,
  `DIV`, `LEN`, `SEL` and the rest. A method input named `Sub` parses as the
  subtraction operator and yields ~40 cascading errors on innocent lines. Rule
  **C2** now rejects them; a *qualified* enum member (`E_CylinderPosition.MID`) is
  still fine.
- **`M_TryIssue` used to fire once per chart RUN in SFC/LD.** A chart language never
  calls `M_ClearTransition` — its engine owns the transition, so there is no commit
  point to hang it on — and nothing else re-armed the issue latch. The re-arm now
  lives in `M_Step`, the one call every step of every language makes. If you are
  reading an older chart that only ever commanded its first child, this was why.
- **A parallel leg is not a place to fault quietly.** `CurrentStep`, the §6.9 stall
  walk and the profiler follow the **main line** only: a first-out has to name one
  step. A leg is timed and guarded on its own §3.13 row instead, and a leg that must
  fault does it through §6.9(d), which stops the whole chain — one leg failing is a
  failure of the step.
- **Owning a child's failure is not the same as hiding it.** A step that drops
  `Awaits` to disposition the failure itself (below) is one case; a step whose
  command sits behind an `IF`/`CASE` is the other, and that one has no rollup at
  all. Raise it explicitly (Core §6.9(d)):

  ```iecst
  IF M_RaiseFromChild(Source := _gauge) THEN
      _gauge.Execute := FALSE;      // §6.1 drop-reset frees the child to recover
      RETURN;
  END_IF
  ```

  `M_RaiseCustom` does the same for a condition no module reports — an
  application rule, an out-of-band measurement — with the step choosing the text,
  severity, category and drill-down link. Both stop the chain **on** the step,
  mark that row of the §3.13 flow chart, and re-arm the step's latches when the
  error clears, so the command is re-issued and re-tested rather than resumed
  mid-handshake. Both are one call in ST, an action line in SFC, and a
  power-flow-gated box in LD. Worked example: `FB_ProbeRaiseChain`.

- **Do not fault a condition the step already handles.** `M_RaiseWarning` (a rule the
  step states) and `M_ReportFromChild` (a child's first-out, published but not
  adopted) record the occurrence and leave the chain running — press AUTO `N180`
  and `N200`. They are AUTO_RESET come+gone events, so they can never block the
  next `Start`, and the base emits each once per step visit so an unguarded call in
  a step body is correct. Reach for the raising pair only when the machine must
  stop.

- **Owning a child's failure means not awaiting it.** An awaited child fault is
  adopted by `FB_UnitBase.OnCyclic` — `_exec := ERROR`, `_step := 0` — *before*
  `_M_Dispatch` runs, so a chart can never jump on it. A step that wants to
  disposition the failure itself passes `Awaits := 0` and names the wait with
  `M_Await` instead (`N200` in the press AUTO chain does exactly this).

Rule **S1** knows the difference: for an `<SFC>`/`<LD>`/`<FBD>` body it requires
the chart contract (`_retVal`, `M_Step(`) rather than the ST skeleton, so a
correct chart is not forced to pretend it is ST.

### Building an LD chain (integer-based state machine)

This section used to describe a second, incompatible ladder form: a
`FB_SequenceBaseLd` base whose methods took `Run : BOOL`, and rungs that ended in
`M_Advance` with an `OnJump1..3` mapping. **Neither is how the ladder works.** The
facade has been deleted (`EN`/`ENO` replaces it) and a rung has always written `_step`
directly. The authoritative description is § "Writing a Ladder sequence rung by rung"
above; this heading is kept only so an old link still lands somewhere truthful.

Rule **S1** knows the difference between the three faces: an `<SFC>` chart must not
need `M_Advance`, a `<NWL>`/`<LADDER>` chain must carry *some* way to move (writing
`_step` counts), and an ST chain needs the full `CASE _step OF` skeleton.

### Two TcUnit gates, and why they are separate

There are **two** test projects and you must run both:

| Gate | Covers | Solution |
|---|---|---|
| `Tests/Fraktal_Tests.plcproj` | Core + Modules (26 suites / 84 tests, simulated HAL) | `Tests/FraktalTests.slnx` |
| `Examples/PressDemo/PressTests.plcproj` | Internal Press feature bench (2 suites / 8 integration tests: `FB_PressDemoUnit_Tests`, `FB_FaultRecovery_Tests`) | `Examples/PressDemo/PressTests.slnx` |

Accept a runtime result only when both its count and runner identity match the
selected gate: Core/Modules output is rooted at `PRG_TcUnitRunner` and reports
84 tests/26 suites; Press output is rooted at `PRG_PressTestRunner` and reports
8 tests/2 suites. If a Press attempt reports the Core identity, either the wrong
solution was downloaded or a previously created Core boot project restarted on
that target. Source `BootProjectAutostart="false"` prevents creating a new
autostart configuration; it does not erase boot data that already exists on a
runtime.

They are split because of a hard TwinCAT constraint: PLC Control inspects a raw
`Compile Include` path **before** it evaluates `<Link>` metadata, so a path
containing `..` makes the importer try to create a project-tree folder literally
named `..` and stop with *"'..' is not a valid folder name."* Every Compile path
must run **downward** from its manifest.

A single aggregate would therefore have to sit at `TwinCAT/` to reach both
`Tests/` and `Examples/` — cluttering the root that holds the platform's
projects. Keeping each manifest beside the sources it owns is what lets `Tests/`
stay self-contained. The press suites still link the **same** physical objects
that deploy (`Fraktal_Press_Demo/01_PneumaticPress/...`), never copies.

Two rules keep this working, both enforced by `plc_lint.py` **P1**:
- no `..` in any Compile path, and every include must resolve;
- a `<Folder Include>` list mirrors the **Include** directories, never the
  `<Link>` paths — XAE materialises those entries as real directories on disk,
  so a mismatch litters the tree with phantom empty folders.

Never load `PressTests` in the same solution as `Fraktal_Press_Demo`: both link
the same source objects and duplicate in-solution GUIDs make PLC Control rewrite
the shared files.

For a compiler-only local/CI check that does not activate or download a target,
run `tools/Invoke-TwinCatBuild.ps1` from the repository root. It opens each test
solution in a separate hidden XAE host, selects x64, asserts Autostart Boot Project
is false, and runs the nested IEC project's `CheckAllObjects`. Runtime CI supplies
the separate isolated-target hook and validates its raw TcUnit summaries with
`tools/tcunit_to_junit.py`, including expected runner identity as well as counts.


**Build order matters:** save/install `Fraktal_Core`, then save/install `Fraktal_Modules`.
`Fraktal_Demo`, `Fraktal_Press_Demo`, `PressTests`, and `Fraktal_Tests` are executable applications, not libraries;
Tests additionally needs `Fraktal_Modules` and `TcUnit` installed.

Each manifest sits with the sources it owns, so every compile input is a downward
path. Keep it that way: do not reintroduce escaping `..` compile paths, and do not
merge the two gates back into one manifest — that would force it up to `TwinCAT/`.

If a test runtime is accidentally saved as a boot project and reports a PLC
stack overflow during TwinCAT startup, keep outputs safe, return TwinCAT to
Config mode, remove/disable the `Fraktal_Tests` boot project for that ADS port,
and restart. The following PREOP→OP / ADS 1804 messages are consequences of the
crashed PLC runtime, not separate I/O mapping faults.

## Commissioning gates (first power-up of a real machine)

Two gates in the `VAR CONSTANT` block of `Examples/Fraktal_Press_Demo/00_System/MAIN.TcPOU` deliberately hold
physical outputs off until the corresponding check is done. Until then the machine looks broken while
the software is healthy:

- **`CONTROL_CIRCUIT_MAPPING_CONFIRMED`** (default `FALSE`) — `FB_PressIoDriver.M_WriteOutputs` forces
  `_000K951_A1` (`SwitchControlOn`) and `_000K911_A1` (`EnableControlOn`) FALSE every cycle. Control On
  cannot energize, so the hardwired N54 D2 relay chain never closes and K985/K986 never enable the
  valves — **nothing moves at all**, even though the cylinder coils are written unconditionally.
  Set it only after verifying the K951/K911 electrical semantics on the cabinet. Per the N54 D2 signal
  table these are *distinct* signals (momentary button coil vs. bus/air-OK enable), yet both currently
  receive `PowerHal.EnableRequestOut`; confirm that is correct for your wiring before enabling.
- **`USE_SIMULATION`** (default `FALSE`) — when TRUE, `MAIN` calls `IoDriver.M_ClearOutputs()` every
  cycle so no physical output is ever energized during virtual commissioning.

### Demo-rig deviation: the E-stop mirror is NOT fail-safe

`_000K910A` (`=000+S1-K910A:14`, "Emergency Switch 1 Pressed") is wired **normally open** on the demo
rig — confirmed on hardware — so `FB_PressIoDriver` inverts it to produce the healthy mirror. A
normally-open E-stop contact cannot distinguish "not pressed" from a broken wire, a pulled terminal or a
dead input card: all read FALSE, and the mirror would report **healthy**. ISO 13850 / EN 60204-1 require
a normally-**closed** contact so any break forces the stop.

This is tolerable *only* because the mirror is diagnostic and the hardwired N54 D2 relay chain remains
the safety authority (Core §9). **A production machine must rewire to NC and delete the inversion.**

These are **constants, so they cannot be written online.** Changing one is a source edit in `MAIN` plus
a download — deliberate and reviewable, rather than a live write from an HMI, XAE watch window or ADS
client. The trade-off is intentional: switching to virtual commissioning now costs a download.

`MAIN` still publishes read-only mirrors (`UseSimulation`, `ControlCircuitMappingConfirmed`) so the gate
state remains visible to diagnostics; they are reassigned from the constants every cycle and no logic
reads them, so writing a mirror online changes nothing.

Read both off a running PLC before suspecting the control logic:

```bash
cd FraktalCore/HMI/gateway
dart run tool/probe_sim_flag.dart <amsNetId> [port]
```

**If forcing the output in TwinCAT XAE works but the PLC never drives it, it is one of these gates** —
the terminal, wiring and process image are already proven good by that test.

## Writing your first type (Quick-start, Core §1.1)

1. Copy `scaffold/FB_TemplateCM/`, rename `Template` → your type, **reserve a reason band** (Core §8.8) and record it in the registry.
2. Declare your `E_<Type>Command`, `ST_<Type>Hal`, `ST_<Type>ParCfg` (keep `SchemaVersion` — §3.8).
3. Write `_M_Dispatch` only (~15 lines): drive output → await sensor → `_M_Complete()` / `_M_Fault(<band code>, …)`. Interlocks via `FB_PermIntlk`; the lifecycle is inherited.
4. Turn the RED suite GREEN: fill the T2/T3/T5 expected values and run against the sim HAL (§2.6) — no rig. T1/T4 are already proven by `FB_Base_Tests` for every inheriting type.
5. Wire once in the parent's `Setup` (§3.11); the tile renders itself (§3.13).

## Conformance mapping (Core §5.7)

| Row | Where proven |
|---|---|
| T1 handshake + Execute-drop reset | `FB_Base_Tests` (once, for every inheriting type) |
| T2 first-out reason **and** SourcePath | base mechanism in `FB_Base_Tests`; each type re-proves with **its** reasons (scaffold) |
| T3 interlock withholds output | per type (scaffold, RED) |
| T4 abort, no self-resume | `FB_Base_Tests` (once) |
| T5 recipe migrate-or-fault | per type (scaffold, RED) |
| T6 rollup adopts child verbatim | base mechanism in `FB_Base_Tests` (`FB_ProbeEM`); composites re-prove per Annex H §H.5 |
| T7 link supervision | `FB_Connector_Tests` (once, in the connector base) |
| T8/T9 tier rows | per composite/Unit type (worked: `FB_ClampEM_Tests` rollup, `FB_Unit_Tests`) |

`Fraktal_Modules/` ships reusable module types (including Annex A/B's `FB_CylinderCM` and `FB_ClampEM`) with their §8.8 band constants, simulation models, and configured device presets; their suites run in the same gate.
