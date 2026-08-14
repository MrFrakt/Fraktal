# Fraktal/TC3 — TwinCAT 3 Binding (Part II)
*Unified PLC Programming Standard · **Part II: the TwinCAT 3 binding of Fraktal Core***

**Status:** Draft · Part II of III (Part I: `Fraktal_Core_Part_I.md`; Part III: `Fraktal_AB_Part_III.md`)
**Platform:** Beckhoff TwinCAT 3 · IEC 61131-3 (ST, TwinCAT OOP extensions)

> Every clause in this Part **binds** a Core contract and cites it as **Core §x.y**; a binding clause carries the number of the Core clause it realizes (numbering is preserved across the split). Nothing here introduces new normative model content — tiers, contracts, state machines, diagnostics, and routing live in Part I; this Part maps them onto TwinCAT 3 language extensions and services. A port to another platform re-implements this document only (Core §1.1 O8).
>
> The worked-example annex set A–I (Core §12) belongs to this binding and ships in `fraktal-tc3`.

---

## TC3 §1 — Binding identity & technology baseline

*Binds Core §1.1 (technology baseline), §1.2 (scope), §1.6 (definitions).*

**Fraktal/TC3** is the TwinCAT 3 binding of Fraktal Core. Conformance claims compose as *"Fraktal Core + Fraktal/TC3 (+ profiles)"* (Core §1.1 O8).

**Technology baseline.** TwinCAT 3 (IEC 61131-3 with the TwinCAT OOP extensions) for control; **EtherCAT** for fieldbus and device integration (TC3 §10); **Beckhoff TwinSAFE / FSoE** for functional safety (TC3 §9); the **TF6100** OPC UA server for connectivity and self-description (TC3 §3.10, TC3 §11.1); a generic Flutter operator HMI auto-discovering the module tree (Core §3.13).

**Binding definitions** (extends the Core §1.6 table):

| Term | Meaning |
|------|---------|
| TwinSAFE / FSoE | Beckhoff functional-safety system / Safety-over-EtherCAT protocol (TC3 §9). |
| TF6100 | The TwinCAT OPC UA server product (TC3 §11.1). |
| XAE / XAR | TwinCAT engineering environment / runtime (TC3 §2.1). |
| TMC / ADS | TwinCAT symbol file (server import, TC3 §3.10) / the TwinCAT communication protocol and its runtime ports (TC3 §4.1). |

---

## TC3 §2 — Development & Runtime Environment (TwinCAT 3)

### TC3 §2.1 Toolchain & versions
*Binds Core §2 (pinned-toolchain rule).*
- Engineering is done in TwinCAT 3 (XAE). The **exact** XAE build and the runtime (XAR) build **shall** be pinned per project and recorded in the project documentation; every station on a line uses the same pinned versions.
- The framework requires the TwinCAT OOP extensions (interfaces, methods, inheritance, properties, `FB_init`); these are used only in framework code (Core §5.5).

### TC3 §2.2 Library distribution
*Binds Core §2.2.*
- Libraries are referenced as versioned TwinCAT library references with their dependencies; local or relative library references are not permitted (Core §5.4). The framework library ships as a versioned TwinCAT library; projects consume a pinned release, never a copy.
- **Reference implementation:** repository `fraktal-core` — `PLC/TwinCAT/Framework/Fraktal_Core` (framework library), `PLC/TwinCAT/Framework/Fraktal_Modules` (reusable module library), `PLC/TwinCAT/Examples/CoreDemo/Fraktal_Demo` (executable root-Unit forest), `PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo` (internal feature-testing bench, not a real project), `PLC/TwinCAT/Tests` (aggregate Core + Modules TcUnit gate) and `PLC/TwinCAT/Examples/PressDemo/PressTests` (the bench's integration gate) — both test applications are excluded from deployed runtimes, and `PLC/TwinCAT/scaffold`.
- TwinCAT library metadata uses four components (`major.minor.patch.revision`, e.g. `0.1.0.0`). Fraktal compatibility follows the first three semantic-version components; `revision` identifies a binding rebuild that does not change the observable contract.
- The reproducible XAE build order, full-build/object-check distinction, local
  library save/install procedure, isolated-runtime interaction, and retained
  evidence are defined in `TWINCAT_XAE_WORKFLOW.md`. A `CheckAllObjects()` result
  shall not be reported as target activation, download, or runtime evidence. Its
  Boolean is the all-object pass/fail authority; failure detail shall be retained
  from the matching DTE2 ErrorItems/Build Output capture (or the visible PLC Error
  List fallback) as defined by workflow §5.1–5.3. Zero captured rows shall not
  override `CheckAllObjects()=FALSE`.

### TC3 §2.4 Project & solution settings
*Binds Core §2 note; baseline defined in TC3 §4.1 (project name, autostart boot project, symbolic mapping, TMC symbol download, ADS ports, documentation format).*

### TC3 §2.5 Source-control form
*Binds Core §2.5.* Text-diffable storage is TwinCAT source / PLCopen-XML export or the IDE's text storage.

When one `.plcproj` compiles linked sources from sibling project directories, its owning XAE project
shall establish their nearest common ancestor as the PLC source base and every `Compile Include`
shall be a downward relative path from that base. TwinCAT's **Add Existing Item** importer validates
the raw source path before applying `Link` metadata and may reject escaping `..` segments. The
Hoisting a manifest to a common ancestor is therefore always sound, but it is the
*fallback*: it drags the manifest away from the sources it owns and clutters the
binding root. **Prefer instead to give each body of sources its own manifest**, so
no cross-sibling linking is needed at all.

The reference implementation does this with two gates. `PLC/TwinCAT/Tests/` holds
the aggregate Core + Modules gate, whose every compile input is downward from
`Tests/`; the press example's suites live in
`PLC/TwinCAT/Examples/PressDemo/PressTests.plcproj`, downward from `PressDemo/`.
Both gates shall be run. A project's suites may live beside the example they
exercise, but shall remain a separate `.plcproj` so no test object reaches the
deployed runtime (Core §5.7), and shall link — never copy — the objects under test.

A `<Folder Include>` list shall mirror the manifest's `Compile Include` directories,
not its `Link` paths: XAE materializes those entries as real directories relative to
the manifest, so any other list leaves empty phantom folders in the source tree.

### TC3 §2.7 Time-synchronization mechanics
*Binds Core §2.7.* PTP discipline is realized over **EtherCAT distributed clocks** for the fieldbus and network PTP (IEEE 1588) for the IPC; NTP fallback where PTP is unavailable.

The framework library exposes the station clock as **`F_Now() : DT`** (wrapping `Tc2_Utilities.F_GetSystemTime`, UTC). Every framework timestamp — `ST_Diagnostic.Since` (Core §8.8), the `FB_PermIntlk` first-out (Core §7.2), alarm edges, part results and cycle profiles — reads it, so "one clock feeds all timestamps" (Core §2.7) holds by construction rather than by convention.

`GVL_FraktalTime.Current : ST_TimeQuality` is the one PLC-wide quality authority
and is excluded from OPC UA; each configured root republishes its validated copy
inside `SystemHealth`. `F_TimeSynchronized()` supplies the quality Boolean stamped
alongside every framework wall-clock field. `FB_TcSystemHealthProbe` measures the
primary task from the monotonic `TIME()` source and accepts the remaining target
metrics, DC state, and documented time-source quality as explicit inputs. A target
adapter shall source those inputs from the licensed/runtime APIs available on that
controller. Missing metrics remain `Available=FALSE`; an application shall not
inject healthy zeros. `F_Now()` does not discipline the operating-system clock;
the target's PTP/NTP/DC commissioning still owns that prerequisite.

---

## TC3 §3 — Language & wiring mechanics (TwinCAT 3)

### TC3 §3.2 Capability query
*Binds Core §3.2/§3.7/§3.9.* The Core's runtime capability query (interface upcast on a child held as `I_Module`) is realized with the TwinCAT operator `__QUERYINTERFACE(iChild, iRicher)`, returning TRUE and filling the richer interface reference when the instance implements it. `I_Module` **shall extend `__System.IQueryInterface`**, so every richer tier interface inherits the capability-query prerequisite. Used in the parent walk (Core §3.2), the mode cascade (Core §3.7), and client-side feature checks (Core §3.9).

### TC3 §3.3 Public contract variable classes
*Binds Core §3.10(a′)/(a″), §3.12 and §6.1.* TwinCAT permits external ST access only to a function block's inputs and outputs. Therefore contract/configuration request data (`Command`, `Execute`, `Abort`, `ParCfg`, `ParCmd`, and root-Unit `HmiRequest`) **shall** be declared `VAR_INPUT`; published result/status data (`Busy`, `Done`, `Error`, `Aborted`, `ErrorID`, `Status`, `Timing`, `OutCmd`, `OutImm`, and `HmiResponse`) **shall** be `VAR_OUTPUT`. Published child-module instances used for recursive traversal are `VAR_OUTPUT`. A caller may read such a child and call its public methods, but **shall not** assign a nested child input through the parent's output; TwinCAT rejects that write. PLC composition code shall route the request through an explicit public method on the child or owning parent. OPC UA clients commit requests through the root Unit mailbox, where the base independently release-gates them and acknowledges the sampled sequence. Implementation state remains `VAR` and is never accessed from another FB. This mapping makes the PLC composition API, TMC symbols, and OPC UA contract agree instead of relying on non-standard access to FB locals.

For the pinned 3.1.4024 binding, every method input **shall be supplied explicitly** at each call. Optional method inputs with declaration initializers are a 3.1.4026+ feature and shall not be used by the 4024 reference implementation.

### TC3 §3.5 Sequence binding — the `FB_SequenceBase` ST skeleton

*Binds Core §5.5, §6.2 and §6.8.* A multi-step application sequence is a separately compiled POU that
**shall extend the Core `FB_SequenceBase`**. The reference (shipped) form is the Core §6.8 ST
`CASE _step OF` skeleton: each step branch owns the corresponding step's real application behavior —
`M_Step`/`M_Await` publication, the child `Execute`/`Done` handshake, timer or decision evaluation,
result work — and sets the shared transition result `_retVal`. A native graphical TwinCAT SFC is a
permitted alternative under Core §6.8, but only when authored in the XAE SFC editor (its proprietary
chart `XmlArchive` is not reliably machine-generatable — a hand-emitted chart missing the connection
graph fails with an `Unknown type: 'SFCStepType'` cascade and shall not be committed). The ST skeleton
is preferred here precisely because it is plain reviewable text with no editor-generated blob.

`FB_SequenceBase` owns the framework bridge and shared flow mechanics once: the `_step` token, `M_Step`,
`M_Await`, `M_Gate`, one-shot `M_TryIssue`, `M_Delay`, the part/decision/completion forwards, the shared
`_retVal : E_StepResult`, and `M_Advance`. A step branch is `_retVal`'s only writer; it ends with
`M_Advance(OnAdvance := <next>)` (plus optional `OnJump<n>` for §6.10 branches), which commits the
transition — advancing to the mapped step and clearing the step-scoped latches (drive-issue, delay) so
the next step re-arms, or holding on `NONE`. The owning `FB_UnitBase` already implements `I_SequenceHost`
and is attached during sequence `Setup`. Projects shall not introduce another host interface, a per-step
transition Boolean set, or a forwarding wrapper for each step.

Direct child input writes shall use owner-bound `REFERENCE TO` aliases established during `Setup`,
avoiding the prohibited write through a parent's published `VAR_OUTPUT` (TC3 §3.3). Reference/interface
members are implementation state and shall be excluded from TF6100 publication (`{attribute 'OPC.UA.DA'
:= '0'}`). The step branch still names the child, command, wait predicate, decision, and transition; the
base is plumbing, not hidden behavior.

The reference press uses `FB_PressDemoHome`, `FB_PressDemoChangeover`, `FB_PressDemoAuto`, and the shared
`FB_PressDemoLoadPosition` under the application branch `Fraktal_Press_Demo/01_PneumaticPress/Sequences`,
called by `FB_PressDemoUnit._M_SequenceHome`, `_M_SequenceChangeover`, and `_M_SequenceAuto`. Those Unit
methods only perform the reset-then-run lifecycle call; they contain no active-step selector or
production state machine. All four extend `FB_SequenceBase`; issue and await remain in one reviewable
drive step. The shared `FB_PressDemoLoadPosition` is one private nested chain invoked as a composite
parent step; its own ram-up, door-open, and slide-outside branches contain the real child handshakes and
publish detailed private progress through the Unit's normal step record via a caller-supplied
`BaseStepNo` window. No sequence helper is a Fraktal module or OPC UA node.

The same Unit branch owns `Release/FB_PressDemoRelease`: its `ModeStart` condition container and named
live condition outputs are published beneath the Unit, while `M_AppendStart`/`M_AppendManual` fill the
same authoritative reports consumed by the Unit gates. TwinCAT method-scoped `REFERENCE TO` inputs
connect the release evaluator to child modules without storing/publishing pointer-like alias state.

### TC3 §3.8 Configuration value-type binding
*Binds Core §3.8a and §3.10.2.*

Core configuration value type `TIME` is represented by
`E_ConfigValueType.DURATION` in Structured Text because `TIME` is a reserved
TwinCAT identifier. Its wire ordinal remains **3** and the generic HMI continues
to name that transport value `time`; this is a binding spelling only, not a
contract or schema change.

### TC3 §3.10 OPC UA exposure mechanics
*Binds Core §3.10(a) and Core §11.1.* Publication begins at every deployed root Unit **instance**, making the intended forest explicit and independently auditable when TF6100 imports a TMC in **Filtered** mode. Reusable FB type definitions do not carry `OPC.UA.DA := 1`:

```iecst
FUNCTION_BLOCK FB_Unit IMPLEMENTS I_Unit
...

PROGRAM MAIN
VAR
    {attribute 'OPC.UA.DA' := '1'}
    CellA : FB_CellUnit;
END_VAR

{attribute 'qualified_only'}
VAR_GLOBAL
    {attribute 'OPC.UA.DA' := '1'}
    Topology : ST_FieldbusTopology;
END_VAR
```

With the symbol file (TMC) download enabled in project settings (TC3 §4.1), the TF6100 server builds its namespace from the symbol file at server startup. Use **Filtered** mode in production so only pragma-enabled symbols are published. Although TwinCAT supports markers on type definitions, Fraktal/TC3 shall not use definition-level `DA=1`: it publishes undeployed instances and makes reference aliases eligible as browse roots. Place an instance marker immediately before every deployed root-Unit declaration in `MAIN` (or the application GVL that owns the forest); its children inherit it. Place the marker immediately before each separately published GVL variable, not before `VAR_GLOBAL` or the GVL declaration. A conforming server browse shall contain the direct root path (for example `PLC1/MAIN/CellA/Status`); aliases reached through a driver, coordinator, HAL, provider, or `REFERENCE TO` member are not additional roots.

An inherited publication marker shall not expose implementation-only pointer,
interface-reference, or `REFERENCE TO` storage. Such a field shall carry
`{attribute 'OPC.UA.DA' := '0'}` or live outside the published subtree; it is not
part of the Fraktal wire contract. This exclusion shall not be applied to the
published child-module instances that form the recursive module tree. A TF6100
TMC-import message naming an application-owned `PVOID`/`UXINT` path indicates a
missing exclusion, even though skipping that unsupported leaf does not by itself
invalidate the remaining namespace.

The framework base classes and reusable concrete types carry no `DA=1` marker. A new module *type* still needs no exposure code because the deployed root marker recursively publishes its contract and legitimate child-module instances. The application adds the one standard marker per root when composing its forest (Core §1.1 O1). A static source/TMC audit shall reject definition-level enable markers and unexcluded persistent pointer/interface/reference members.

`FB_UnitBase` additionally publishes `HmiRequest : ST_HmiRequest` and
`HmiResponse : ST_HmiResponse`. TF6100 clients write all argument leaves before
the `UDINT Sequence` leaf. The base writes `AckSequence` after invoking the
existing gated IEC method. The sequence fields, request-kind enum ordinals, and
mailbox member names are wire-contract data and are append-only.

> **Open verification item — write-fragmentation atomicity (TC3 and AB).**
> This commit-marker design assumes the argument leaves are all visible to the
> PLC before the `Sequence` write becomes visible. The assumption is sound for
> ordered, individually-committed leaf writes, but it has **never been tested
> against a fragmented or reordered transport write** in either binding. If a
> large `ST_HmiRequest` is written as a batched or segmented transfer — an ADS
> sum-write, a TF6100 multi-node write, or in Fraktal/AB a CIP payload larger
> than the negotiated connection size — a scan could in principle observe a new
> `Sequence` alongside partially-written arguments.
>
> Fraktal/AB removes the question by construction: AB §7.7 bounds the request
> payload to a single unfragmented connected write. **TC3 has no equivalent
> bound and therefore still carries the risk.** Both bindings shall test this
> explicitly — batched/segmented request writes, argument leaves committed out
> of order, and a scan deliberately interleaved between argument and sequence
> writes — before either claims a writable deployment. A defect here is a
> defect in the shared design, not in one transport, and the fix (a two-slot or
> seqlock mailbox) would likewise apply to both.

### TC3 §3.11 Constructor injection: `FB_init`, `REF=`, and member ordering
*Binds Core §3.11.* Top-level identity/HAL injection uses `FB_init`:

```iecst
FUNCTION_BLOCK FB_ControlModule IMPLEMENTS I_ControlModule
VAR_INPUT CONSTANT
    // FB_init parameters: set once at instantiation
END_VAR
METHOD FB_init : BOOL
VAR_INPUT
    bInitRetains : BOOL;
    bInCopyCode  : BOOL;
    Name         : STRING;            // root identity; nested Setup receives qualified path (Core §4.8)
    HalRef       : REFERENCE TO ST_Hal; // HAL channel mapping
END_VAR
THIS^._name := Name;
THIS^._hal  REF= HalRef;
```

```iecst
// Two clamps, same type, different name + mapping — full logic reused:
Clamp1 : FB_ControlModule(Name := 'Clamp1', HalRef := Hal.Clamp1);
Clamp2 : FB_ControlModule(Name := 'Clamp2', HalRef := Hal.Clamp2);
```

**Member ordering (the reason for Core §3.11's `Setup` rule):** TwinCAT runs a member's `FB_init` *before* the enclosing FB's, so a parent cannot forward its own `FB_init` parameters into a child's `FB_init`. Composite types therefore wire children through the Core-mandated one-shot `Setup(...)` called from the parent's `FB_init`/`Setup` (worked example: Annex B).

### TC3 §3.14 Lifecycle-extension binding
*Binds Core §2.2 and Core §3.14.*

TwinCAT realizes Core's authoritative lifecycle through inheritance. Every module
extends the base function block for its tier, and `FB_ModuleBase.Cyclic()` owns the
non-optional scan path. Concrete module bodies call that inherited entry point;
their application behavior is confined to `_M_Dispatch` and declared lifecycle
extensions. The base owns command-edge/reset semantics, initialization,
accepted-command start, cyclic/child rollup, abort routing, BUSY-only dispatch,
HELD/timing/terminal resolution, diagnostics/status publication, and release of
framework one-shot requests in the Core §2.2 order.

Core lifecycle extensions bind to `PROTECTED` virtual methods on the relevant
base FB. Except for `OnModeExit`, every override shall call `SUPER^.OnX(...)`
first and propagate its return unless it deliberately changes it. `OnModeExit`
is the specified exception: the base call performs cancellation, so a graceful
override stages `SUPER^.OnModeExit(...)` until its application reaction consents.
An omitted override uses the base default. The source lint and base/type suites
prove these ordering rules; a project does not reproduce the lifecycle.

This is a binding mechanism, not a Core requirement for inheritance. The R0
authority audit in `AB_R0_CORE_AUTHORITY_EVIDENCE.md` confirms that the existing
TC3 implementation remains the reference behavior while Fraktal/AB realizes the
same Core order through generated composition.

### TC3 §10.2.1 I/O integration placement

The Core responsibility table binds to TwinCAT as follows:

- a project `GVL_<Project>IO` contains only leading-underscore `AT %I*`/`AT %Q*` symbols;
- an `FB_<Project>IoDriver` is the sole POU that reads or writes that GVL and maps it to typed HAL structures;
- an `FB_<Project>IoCatalog` contains the approved tag/address/description/module-role join and configures `FB_IoTopologyPublisher` plus module identity records;
- `FB_IoTopologyPublisher` in `Fraktal_Core` owns validation, health propagation and diagnostic joining against `ST_FieldbusTopology`;
- `MAIN` calls setup and the driver methods in scan order but contains no individual raw channel assignments.

The catalog and driver are application infrastructure, not `FB_Unit`/`FB_EquipmentModule`/`FB_ControlModule` objects and therefore do not create a fourth tier. `GVL_<Project>Fieldbus.Topology : ST_FieldbusTopology` is the published HMI data. `FB_EcBusHealth` supplies runtime slave count/order, state/link data, and configured-identity mismatch flags from the EtherCAT master; the catalog supplies reviewed node/channel identity and project semantics; `FB_IoTopologyPublisher` validates and joins them. Either authority failing validation keeps `MappingValid=FALSE`.

---

## TC3 §4 — Project settings (TwinCAT 3)

### TC3 §4.1 TwinCAT project settings
*Binds Core §4.1 and Core §2 (environment baseline).*
- **Autostart Boot Project** is enabled for the deployed machine application—not
  the aggregate Tests application (TC3 §5.7). **Symbolic Mapping** and **TMC
  symbol download** are enabled where required for TC3 §3.10 / Core §3.10.
- One default ADS port per runtime (e.g. 851 for project 1); deviations approved by Controls Engineering.

### TC3 §4.8 Browse-name source
*Binds Core §4.8.* The `Name` "passed at instantiation" is the `FB_init` `Name` parameter (TC3 §3.11).

---

## TC3 §5 — Quality tooling (TwinCAT 3)

### TC3 §5.7 Unit-test framework & CI runner
*Binds Core §5.7.* Tests are written with the TwinCAT 3 xUnit framework **TcUnit** and executed in CI by **TcUnit-Runner**, which drives the suites headless on the build agent and emits JUnit-format results for the merge gate (Core §6.8). Worked example: Annex H.

The `Fraktal_Tests` and `PressTests` applications shall run only on an isolated
test runtime/ADS port or CI worker. Neither shall be selected as the machine boot
project, and both repository wrappers shall serialize Autostart Boot Project as
disabled. A test runtime is started deliberately, its result is harvested, and
it is then stopped or replaced by the machine application.

The exact XAE sequence and evidence identity are specified in
`TWINCAT_XAE_WORKFLOW.md` §6. Runner identity, expected suite/test inventory, and
zero failures shall all match; a green summary from the wrong runner is not the
selected gate's result.

TwinCAT task stacks are bounded. Large bounded contract records such as
`ST_ReleaseReport` shall be filled in caller-owned storage through `VAR_IN_OUT`;
they shall not be returned and reassigned by value through nested calls. The
reference `ReleaseReportStart`, `ReleaseReportManual`, and
`ReleaseReportAction` methods return the `Released` Boolean and fill their
report argument in place.

---

## TC3 §8 — Diagnostics & performance binding (TwinCAT 3)

### TC3 §8.11 Timing sources for the cycle-time profile
*Binds Core §8.11.4(e).* Durations are measured with the monotonic millisecond clock (`TIME()`), differenced as `DWORD` so the ~49-day wrap subtracts correctly; wall-clock `Started`/`Since` stamps come from `F_Now()` (TC3 §2.7). The profiler and timing structures are plain framework DUTs exposed through the §3.10 pragmas on the base classes, so the HMI reads them with no per-type wiring. Core's semantic time-class field is spelled `TimeClass` in the TwinCAT DUTs and method inputs because `CLASS` is a reserved TwinCAT identifier. The HMI binds `TimeClass`; its reader may accept legacy draft snapshots containing `Class` during migration.

### TC3 §8.12 System-health binding
*Binds Core §8.12.* `FB_TcSystemHealthProbe` is the TC3 adapter seam;
`FB_SystemHealthPublisher` remains platform-neutral evaluation/alarm ownership.
The composition root calls the probe once per scan, injects its bounded
`ST_SystemHealthInput` plus schema-first thresholds through `SetSystemHealth`, and
the Unit base publishes `SystemHealth`. Task cycle/jitter use `TIME()`; controller,
IPC, EtherCAT/DC and clock-source inputs shall come from target-specific diagnostic
APIs or remain explicitly unavailable. The Press Demo's synthetic values are an
internal simulation profile, not live target evidence.

### TC3 §8.13 Signal-tower binding
*Binds Core §8.13.* `FB_SignalTower` produces only semantic lamp/horn outputs.
`FB_UnitBase` calls it from the Unit's machine state, active-alarm maximum severity,
and decision slot, publishes `SignalTower`, and handles append-only mailbox kind
`LAMP_TEST := 26`. The project Hardware Driver is the only code permitted to map
those outputs to `%Q` channels. The standard mapper never writes a project raw-I/O
GVL and the internal Press fixture may leave the semantic output unwired when no
reviewed physical stack-light mapping exists.

### TC3 §8.9 Generated alarm-rationalization binding
*Binds Core §8.8/§8.9.* `Specification/reason_rationalization.json` is the
symbol-keyed rationalization authority; numeric authority remains `E_Reason` and
the registered `PL_*Reasons` lists. `HMI/tool/generate_reason_catalog.dart`
validates exact coverage and generates `PL_ReasonCatalog`,
`F_ReasonMetaByIndex`, `F_ReasonMeta`, and the Dart localization/metadata lookup.
`FB_AlarmLog` resolves generated priority/category/shelvability by `ReasonCode`,
rejects standard-record overrides, and exposes the complete static catalog
through the paged configuration manifest. Static metadata is not a cyclic array.

---

## TC3 §9 — Safety binding (TwinCAT 3)

*Binds Core §9.1, §9.7.* The certified safety system is **Beckhoff TwinSAFE**: TwinSAFE Logic plus safe I/O over **FSoE** (Safety-over-EtherCAT). The PLCopen Safety `SF_*` function-block set of Core §9.7 is available on TwinSAFE Logic and **should** be used for standard safety functions. The safety project's version/identity is tracked separately from the standard application's (Core §13, §14.2).

*Binds Core §9.8.* Guard monitoring/locking, ESPE/light-curtain evaluation and muting, enabling switches, safe requests, external-device monitoring, and safe valve/drive outputs are implemented in TwinSAFE with certified blocks and safe I/O. Standard TwinCAT PLC code maps TwinSAFE group/device status into `ST_SafetyStatus` and `ST_ControlPowerStatus`; standard-to-safety values are requests only. A cell-scope coordinator publishes `ST_ControlDomainStatus`, and each root `FB_UnitBase.ControlDomain` input is assigned either the relevant shared record or the absent default. Multiple peer Units may consume the same record; this does not change the Unit call tree. EtherCAT/FSoE loss, terminal watchdog behavior, and each valve-island/drive power zone shall have a validated safe-state configuration independent of the standard PLC reaction. A keyed bridge is a physical TwinSAFE mode/input and is read-only to the HMI.

---

## TC3 §10 — Fieldbus binding (TwinCAT 3)

### TC3 §10.1 EtherCAT
*Binds Core §10.1.* **EtherCAT** is the primary fieldbus. The EtherCAT master(s), topology, and distributed-clock settings **shall** be documented; distributed clocks feed the station time base (TC3 §2.7). Drives, robots, scanners, and sub-buses are integrated as EtherCAT devices or through documented gateways.

### TC3 §3.15 Byte-transport binding (TCP/IP)
*Binds Core §3.15.1a.* `I_ByteChannel` is implemented over **`Tc2_TcpIp` (TF6310)**: `FB_SocketConnect`/`FB_SocketClose` for `Open`/`Close`, `FB_SocketSend`/`FB_SocketReceive` for `Send`/`Poll`, all driven non-blocking from the channel's cyclic state machine. A skeleton (`FB_TcpChannelTc3`) names these FBs with TODO bodies — **verify FB signatures, the TF6310 license requirement, and the local server (`TcpIpServer.exe`) prerequisite against Beckhoff InfoSys for the pinned TwinCAT version** before first use. Serial devices bind the same interface over `Tc2_SerialCom` analogously.

### TC3 §10.5 EtherCAT & IPC diagnostics
*Binds Core §10.5.* EtherCAT master state, lost frames, slave errors, distributed-clock sync loss, and watchdog surface as System alarms per Core §10.5/§8.6.

### TC3 §10.6 Fieldbus topology & I/O diagnostics (EtherCAT/ADS)
*Binds Core §10.5.1.* The conforming base profile is a three-authority composition: `FB_EcBusHealth` reads the EtherCAT master's reported slave count/order plus each slave's `deviceState`/`linkState`; `FB_<Project>IoCatalog` imports the reviewed XAE/ESI/TMC/electrical channel identity, scaling, address, and owning-module data; and `FB_IoTopologyPublisher` validates the bounded join and publishes `ST_FieldbusTopology`. The `deviceState` mismatch flags make configured vendor/product/revision/serial disagreement fail visible; `E_NodeState.FAULT` covers those flags and lost/no-response conditions. Channel values are copied by the sole project Hardware Driver from the same linked process-image/HAL variables used by control logic, not re-read through CoE. A runtime force, when a project explicitly enables one, resolves only a reviewed `Forceable` output and writes through that application's output authority behind the Core §7.6/§7.7 gates; it is never a raw master/process-image or input force, and every accepted request is logged as a §8.3 event. `I_FieldbusScanner`/`FB_EcFieldbusScanner` remain an optional compatibility seam for deployments needing richer vendor-specific runtime discovery; the fail-closed skeleton is not the default profile and is not required for base conformance. Master/slave state changes continue to raise the System alarms of TC3 §10.5 — the topology view and alarm list are two views of one source. The implementation and acceptance guide is **`FIELDBUS_ADS_ADAPTER.md`**.

---

## TC3 §11 — Connectivity binding (TwinCAT 3)

### TC3 §11.1 TF6100 OPC UA server

> **MTP note.** TwinCAT ships MTP engineering/runtime support (TE8400/TF8400) which can expose a module structure over OPC UA per VDI/VDE/NAMUR 2658. Mapping a Fraktal root Unit onto an MTP PEA (services, DataAssemblies, alarms) is specified in **Annex J**; verify the TwinCAT MTP product path against the pinned TwinCAT version.
*Binds Core §11.1 and Core §3.10.* The **TwinCAT OPC UA server (TF6100)** publishes the module tree from a DA pragma on every deployed root instance plus explicit standalone data variables (TC3 §3.10), TMC symbol download (TC3 §4.1), filtered/marked symbols, implementation-reference exclusions, structured types, and type-aware browsing. Browse identity follows Core §4.8: a local TF6100 browse segment equals the local PLC/schematic member name, while published `Status.Name` is the complete dotted Fraktal identity.

TF6100 shall run on the host that owns the PLC runtime (the CX/IPC for a remote
runtime); the Flutter HMI is the OPC UA client and does not require a second
TF6100 server. First deployment shall be accepted in layers: TCP listener,
SecureChannel, activated session, `Server/NamespaceArray` containing the
configured PLC Data Access namespace, an authorized `Objects` browse exposing
`PLC1/MAIN/<Root>/Status`, writable root `HmiRequest` leaves, and a matching
`HmiResponse.AckSequence`. A PLC namespace present in `NamespaceArray` while
`Objects` returns only namespace-zero `Server` is an authorization failure, not
a missing TMC or network failure.

TF6100 namespace permissions shall keep the Data Access device and the ancestors
of each permitted root browsable. Node-specific rights may then narrow writes to
the root `HmiRequest` subtree. Configuration shall be written to the target and
TF6100 restarted/reloaded after security or TMC changes. Anonymous membership in
the built-in Users group with `SecurityPolicy=None` is permitted only for a
controlled commissioning activity; the production requirement remains Core
§11.2/§14 authenticated sign-and-encrypt with least privilege. The complete
first-deployment and fault-isolation procedure is
`FIRST_PROJECT_AGENT_GUIDE.md`.

### TC3 §11.6 Host-event binding
*Binds Core §11.6.* Each published root inherits
`HostEvents : FB_HostEventPublisher`; TF6100 exposes its bounded 32-record ring,
head, count, and wrapped flag through the root's deployed-instance DA marker.
Implementation-only `I_HostEventSink` storage is explicitly excluded from OPC UA.
`FB_UnitBase` owns part, mode, changeover, and NOK projection; application
composition calls the named tool/material seams. Optional north-bound delivery
implements `I_HostEventSink` and is injected at the composition root. The HMI and
PLC `E_HostEventKind` ordinals are a checked append-only transport contract.

---


*End of Fraktal/TC3 — Part II (draft). Core: `Fraktal_Core_Part_I.md`.*
