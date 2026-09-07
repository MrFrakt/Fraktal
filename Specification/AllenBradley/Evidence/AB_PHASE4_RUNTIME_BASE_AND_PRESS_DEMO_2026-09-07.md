# Fraktal/AB Phase 4 — the runtime base, and the press demo emitted from it

**Phase:** 4 — runtime base, with the press demo as its first emitted application

**Result:** **The runtime base exists as a generator, and the press demo runs on
the bench. One committed declaration emits the contract UDTs, three module AOIs,
the mode owner, the routine and the full-project L5X; it imports at `0/0`,
clears Studio v33 Verify Controller at 0 errors and 0 warnings, round-trips
canonically and passes its census as a registered gate leg. On the controller,
all fifteen matrix rows pass on three consecutive runs with no variance —
including a held two-hand condition that publishes a LOW named reason and no
alarm and then self-resumes, an awaited child whose first-out the unit adopts
verbatim, a reported-not-adopted ram condition, and an operator decision the
chain waits on without faulting.** Two generator defects and two harness faults
were found and fixed on the way, one of them only findable on hardware.

**Date:** 2026-09-07

**Repository revision:** `bd8df12`

**Scope:** two authorized downloads of the press demo to the isolated bench, and
five executions of its fixed matrix. Writes confined to the fifteen declared
input tags, all restored and verified. No fault clear, clock set, firmware,
controller-network, safety, SD-card or physical-I/O operation.

## 1. What the generator emits

The committed sources are the **declaration** and the **generator**. The L5X is
output: reproducible through the gate, never hand-edited. Nothing in this
record was hand-authored Logix.

| Committed source | Role |
|---|---|
| `fraktal_ab_declaration.py` | the declaration types and the rules that refuse a bad one |
| `fraktal_ab_generate.py` | declaration to contract UDTs, AOIs, routine, L5X |
| `fraktal_ab_press_demo.py` | the press demo declaration — the application itself |

From the press demo declaration it emits:

| Emitted | Instance |
|---|---|
| Contract UDTs | 4 — `FRK_T_PressParCfg` (5), `…ModuleCtx` (32), `…UnitCtx` (29), `…Chart` (101 incl. three per-step arrays) |
| Module AOIs | 3 — `FRK_M_PressPressRam`, `FRK_M_PressDoor`, `FRK_M_PressPartSlide`, one per declared module type |
| Mode owner | 1 — `FRK_U_Press`, carrying MANUAL, AUTO and HOME |
| Program / routine / task | 1 / 1 / 1; `FRK_PressTask` PERIODIC **10 ms**, watchdog 500, output updates disabled |
| Controller tags | 28 — contexts, chart, ParCfg, 15 writable inputs, 3 evidence tags, 4 AOI instances |
| Physical I/O references | **0**; embedded `Discrete_IO` inhibited |
| `BOOL` members in public UDTs | **0** |

Census from the gate: `DataTypes 4, AddOnInstructions 4, ControllerTags 28,
Programs 1, Tasks 1`.

### The S16 findings are generator rules, and each one can refuse

A rule that cannot reject anything is a comment. Each of these is enforced by
`validate` or by an emit-time assertion, and each has a test that breaks it
deliberately and requires the refusal:

1. **Ordering is self-checked.** Every emitted mode owner verifies that each
   child module AOI already ran this scan and counts `OrderFail` if not. The
   generator does not merely emit the calls in the right order; the emitted
   logic detects its own violation.
2. **Durations are milliseconds converted from the declared task period**, and
   generation **fails** if the emitted task does not carry that period. A
   timeout that is not a whole number of scans is refused, because the module
   could not count it exactly.
3. **A held command's timeout does not accrue.** The held branch does not
   advance `ElapsedMs`, so a hold never matures into a timeout.
4. **The frozen v33 type map.** Every contract member is a `DINT`; booleans are
   0/1 and durations are range-checked milliseconds. `BOOL` in a public contract
   UDT is refused at emit time — that layout is a recorded S12 hole.
5. **Every ParCfg-shaped record leads with `SchemaVersion : DINT`** (Core §3.8).

A sixth rule the declaration also enforces, because Studio should never be the
first thing to notice: a step whose condition names an input that is not
declared is refused, as is a transition to a step that does not exist.

### One Logix constraint that shaped the design

**An Add-On Instruction may only reference its own parameters and local tags.**
A first cut had the mode owner reaching for controller-scoped context tags
directly, which does not compile. Every child context, the configuration record
and every simulated input is therefore passed in — the mode owner is handed
exactly what it may touch, which is also the more honest shape. A test asserts
that **no AOI body names a controller-scoped tag at all**.

## 2. The press demo, and where it diverges from the oracle

TwinCAT's `Fraktal_Press_Demo` is the behavioural oracle for observable
semantics, never for implementation shape. The step numbers below are the
oracle's, so the two graphs can be compared row by row.

### Step-graph comparison — AUTO

| TC3 step | TC3 behaviour | AB step | AB behaviour | Divergence |
|---|---|---|---|---|
| `0` pressAutoInitialize | clear cycle marker | `0` autoInitialize | same | — |
| `100` pressAwaitTwoHand | await part + air + two-hand | `100` awaitTwoHandStart | same, named stall reason on each | TC3 also opens a traceability record (`M_PartReceived`); AB does not — traceability is out of scope |
| `110` pressRamUp | ram RETRACT | `110` ramUp | same | — |
| `130` pressDoorOpen | door RETRACT | `130` doorOpen | same | — |
| `150` pressSlideInside | slide EXTEND, awaited child | `150` slideInside | same, **and the unit adopts its first-out verbatim** | TC3 also calls `M_PartStarted` |
| `170` pressTransferSettle | delay `TransferSettleTime` | `170` transferSettle | delay `TransferSettleMs` (200 ms) | TC3 carries a `TIME`; AB carries range-checked `DINT` ms (S12) |
| `180` pressDoorClose | two-hand release ⇒ **warning + abort**, jump to 185 | `180` doorClose | two-hand release ⇒ **HELD**: BUSY, LOW reason 6130, no alarm, self-resumes | **named divergence — see below** |
| `185` pressDoorReopen | door back up after abort | — | absent | consequence of the held form |
| `190` pressSlideOutsideAfterAbort | slide out, drop start latch, → 100 | — | absent | consequence of the held form |
| `200` pressRamDown | ram EXTEND; on error **report, not adopt**, jump 210 | `200` ramDown | same | — |
| `210` pressNotReachedConfirm | operator decision, **no timeout** | `210` notReachedConfirm | same, `DecisionId` published, named stall reason | TC3 carries prompt/option strings; AB carries a decision **id** (STRING transport is out of scope here) |
| `215` pressScrapPart | disposition NOK | `215` scrapPart | `ScrapCount` increments | TC3 records a verdict against the part record; AB has no traceability |
| `220` pressDwell | dwell; two-hand release **holds the timer** | `220` pressDwell | plain delay `PressDwellMs` | **named divergence — the held case is carried at 180** |
| `230` pressRecordResult | `M_PartRecord` measured value | `230` recordResult | mark only | traceability out of scope |
| `240` (composite `M_RunSub`) | load position sub-chain at 240/260/280/300 | `240`/`242`/`244` | the same three moves, inlined | **mechanical**: Logix has no sub-chain call in this shape |
| `999` pressAutoComplete | count by verdict, loop to 100 | `999` autoComplete | `CycleCount`/`GoodCount`, loop to 100 | TC3 counts by verdict through the part record |

### Step-graph comparison — HOME

| TC3 | AB | Divergence |
|---|---|---|
| `0` pressHomeInitialize | `0` homeInitialize | — |
| `900` composite load position | `900`/`902`/`904` | inlined, as above |
| `999` pressHomeComplete | `998` homeComplete | AB uses 998 to keep 999 unambiguously the AUTO terminal |

### The two divergences that are behavioural, not mechanical

**1. The two-hand release during door close.** TC3 treats it as an operator
*abort*: it raises a LOW `PROCESS` warning, reopens the door, slides the part
out and returns to the two-hand wait with the start latch dropped. The AB demo
treats it as the **S16 held condition**: the close stands still, reason 6130 is
published at LOW severity, no alarm is raised, nothing times out, and it
resumes on its own when the buttons return.

Both are legitimate readings of §6.1's "progress resumes on its own when the
condition returns", and both refuse to call designed operator behaviour a fault.
They are **not the same machine behaviour**: TC3 ends the cycle and returns the
part; AB pauses and continues the same cycle. This record does not claim the AB
form is the correct one — it is the form the S16 pattern proved, generalised,
and it is recorded here so a reader can see the choice rather than inherit it.

**2. The dwell hold.** TC3 freezes the dwell timer when the two-hand is
released mid-press. AB's dwell is a plain delay, because the held condition is
already carried at 180 and duplicating it would prove nothing new. A production
binding that wants both must declare both.

Everything else above is mechanical: sub-chain inlining, `DINT` milliseconds
instead of `TIME`, a decision id instead of prompt strings, and the absence of
traceability calls that are out of scope.

## 3. Offline gate

Run as a registered leg of the Phase 0 regeneration gate, from a **fresh clone**
with no build output — ten legs, every stage green.

| Check | Result |
|---|---|
| SDK import | `Warnings="0" Errors="0"`, no SDK error event |
| **Studio v33 Verify Controller** | **0 errors, 0 warnings**, input unchanged, closed cleanly |
| Canonical round trip | identical |
| Construct census | `Differences: []` |
| Physical I/O | 0 `Local:`/`Discrete_IO:` operands |
| Public UDTs | all `DINT`, zero `BOOL` |
| Scope fence | all excluded terms absent |

Run from a fresh clone at `bd8df12`: **ten legs, `Passed: true`, `Failed: []`**.
The press demo's canonical export is
`585735535B00ADE830D7F15E0B679AB5587DACE2E84CDD8C3D5B4A034B3184A8`, and the
nine pre-existing legs reproduced the canonical hashes their own records carry —
a third independent confirmation that canonical form is stable across seeds and
across runs.

The generator is also **deterministic**: two runs against the same seed produce
a byte-identical L5X (`867AFA4F38A369BFF011064EC05EA78EAF9976BC6242F40FAEFEB231DB352DC9`),
which is the artifact that was imported, Verified and downloaded.

### Resolved toolchain the gate ran with

The probe's framework and Rockwell client version are MSBuild properties, so the
record keeps them reproducible:

| Item | Resolved value |
|---|---|
| `FraktalProbeTargetFramework` | `net8.0` (built `win-x86`) |
| `FraktalSdkClientVersion` | `2.0.861` |
| CSClient package on disk | `RockwellAutomation.LogixDesigner.CSClient.2.0.861.nupkg` |
| `LdSdkServer.exe` | `2.0.861.0` |
| Studio 5000 Logix Designer | `V33.00.00` |
| .NET SDK | `10.0.400`; x86 runtime `8.0.7` only |
| `pylogix` | `1.1.5`, hash-verified, venv outside the repository |

## 4. Four defects, and which ones hardware found

**Two generator defects.** The second was findable only on the bench.

*Found by reasoning about the emitted logic, before the download:* a `COMPLETE`
step stood the chain down, but the top-level run latch re-armed it on the very
next scan while the run request was held, so `Running` oscillated and a reader
would have got a different answer depending on which scan it sampled. A
completed chain now stays completed until a reset or a mode change.

*Found by the first bench run:* **adopting an awaited child's first-out set
`Running := 0` but never dropped `Execute`.** A module clears a terminal state
only when its Execute falls, so the child stayed faulted permanently and every
later step aiming at it stalled. `ISSUE` had the same hole from the other side —
it re-asserted `Execute` every scan, so a module already in Error could never
reset. **Seven of fifteen rows failed on that one mechanism**: the decision rows
never reached the ram, MANUAL could not jog the slide, and HOME hung on its last
move.

Every commanding step now drops `Execute` on its own entry scan and commands
from the next — Core §6.1's Execute-drop reset used as the generator intends,
which also guarantees the rising edge the module latches on. Adopting
additionally releases the child, because pinning it in a state nothing can clear
is a deadlock, not a diagnosis.

**Two harness faults of my own**, both worth naming because they are the same
class of mistake in different clothes:

* a row read the chart the instant it saw a step, catching the **entry scan**
  that zeroes the marks, and so reported a stall reason that was never the
  steady state; and
* a row asserted across a **unit read and a chart read**. Each structure is read
  in one request and is individually coherent — but two requests are two scans.
  **Single-request coherence buys a coherent structure, not a coherent pair.**
  That is the S9 lesson one level up, and it caught me after I had already fixed
  the S16 harness for the simpler version of it.

The adoption row is *stronger* for the fix rather than weaker. The child's live
`ErrorID` is no longer where "verbatim" is checked, because adoption releases
the child by design; the row now requires the parent to republish the child's
own reason, to name which child it came from, **and** the child to be free.

## 5. The executed matrix

Fixed harness, hash-verified `pylogix 1.1.5` in a venv outside the repository.
Values reported as status and shape; `values_redacted: true`.

**Three consecutive runs, fifteen of fifteen rows, no variance.**

| # | Row | Result | What it establishes |
|---|---|---|---|
| 1 | `auto_full_cycle` | **PASS** | the AUTO chain completes a cycle with no adopted fault |
| 2 | `held_two_hand_released_during_door_close` | **PASS** | `Held=1`, reason **6130**, severity **0 LOW**, `Error=0`, still on step 180 |
| 3 | `held_self_resumes_without_reissue` | **PASS** | restoring the two-hand resumes with no fresh command |
| 4 | `awaited_child_fault_adopted_first_out` | **PASS** | `ErrorID=6102` republished, `ErrorSource=3` names PartSlide, stopped on 150, child released |
| 5 | `restart_by_reissue_after_adopted_fault` | **PASS** | clearing and re-issuing restarts the chain |
| 6 | `child_condition_reported_not_adopted` | **PASS** | ram failure reported as a message; the unit does not fault |
| 7 | `decision_step_waits_without_faulting` | **PASS** | `DecisionId` published, stall reason 6112, no fault |
| 8 | `decision_answer_scrap` | **PASS** | the scrap answer dispositions and continues |
| 9 | `decision_answer_return` | **PASS** | the other answer leaves the scrap count alone |
| 10 | `manual_jog` | **PASS** | MANUAL moves one module per request |
| 11 | `home_completes_and_stops` | **PASS** | HOME completes and does not loop |
| 12 | `mode_switch_midcycle_stands_the_chain_down` | **PASS** | back to the init step, no self-resume |
| 13 | `auto_abort_does_not_self_resume` | **PASS** | an aborted AUTO stays down |
| 14 | `blocked_condition_publishes_a_stall_reason` | **PASS** | a missing condition names why (6131) and raises no fault |
| 15 | `chart_marks_and_ordering` | **PASS** | 22 steps visited, 16 with durations, cursor live, `OrderFail = 0` |

Rows 2 and 4 returned byte-identical observations on all three runs.

### Timings, against the declared task period

The declared period is **10 ms**, and the controller published it back
(`FRK_Press_TaskPeriodMs = 10`) — the fingerprint requires that match before any
write, because the timeouts were converted from it.

| Row | run 3 | run 4 | run 5 |
|---|---:|---:|---:|
| `auto_full_cycle` | 971.9 | 971.4 | 969.5 |
| `held_two_hand_released_during_door_close` | 215.9 | 215.3 | 218.3 |
| `held_self_resumes_without_reissue` | 54.3 | 54.4 | 45.8 |
| `awaited_child_fault_adopted_first_out` | 140.0 | 138.6 | 138.4 |
| `child_condition_reported_not_adopted` | 286.3 | 296.3 | 290.8 |
| `home_completes_and_stops` | 166.9 | 173.0 | 170.8 |
| whole matrix | 5190.6 | 5188.5 | 5172.6 |

All milliseconds. The AUTO cycle at ~970 ms is the plant working: three cylinder
strokes at four scans each, a 200 ms transfer settle and a 300 ms dwell, plus
the chain's own steps — not transport cost. A single structure read costs about
3 ms, well inside one 10 ms scan.

### Write surface and cleanup

Every run wrote only the fifteen declared input tags and every run's `disarm`
reported **all fifteen `cleared`**, including the run that failed seven rows.
The fingerprint passed before the first write on every run, and cleanup was
independently re-verified afterwards by read-only probe.

## 6. Artifacts and hashes

| Artifact | SHA-256 |
|---|---|
| generated `press_demo2.L5X` | `867AFA4F38A369BFF011064EC05EA78EAF9976BC6242F40FAEFEB231DB352DC9` |
| **`press_demo2.ACD`** (Verified `0/0`, downloaded) | **`BE831950B95E8F672EC54933E50791DA7619E1FF7AB01A5019C1B45F2CAD1968`** |

Studio saved the project during the download session, so the live file now
hashes differently — the expected `controller minor 11 → 14` rebinding S2
documented. Studio's own pre-save backup preserves the artifact that was
Verified and downloaded, and it hashes to exactly the value above.

| Tool | SHA-256 |
|---|---|
| `tools/fraktal_ab_declaration.py` | `9CCCDF90AEA52F00549BE34CBAA3C38F3980708F236B40FB018DD1768711B525` |
| `tools/fraktal_ab_generate.py` | `69FCA33EA484D34A0A3B995B21BA3035814EF9E3D83BE7412441B214DD0A5E04` |
| `tools/fraktal_ab_press_demo.py` | `37AAF243D77E3F6884A8B336DA47087C5CD248042BCEC85F18D3B6B3DC369CF0` |
| `tools/fraktal_ab_press_execute.py` | `8D1E2697CCE06522E7D858C173F250BB0CD990D04F78C2342ED5AE90CB5D8EDA` |
| `tools/test_fraktal_ab_generate.py` | `D4401FDB540D52B69F39AD4A678E910206A4AE736FFDDD018CEF0CDA732348BD` |
| `tools/fraktal_ab_phase0_gate.py` | `0BDD32EF17D55B5F5E5F7B1F352BED2ED341F124CE0047B7172FBC60C328C6BB` |

43 generator tests, most of them negative. The AB suite is green at **300**.

## 7. Deferrals, recorded rather than forgotten

Out of scope for Phase 4 and deliberately not attempted:

1. **Recipes and changeover** — no recipe record, no changeover chain.
2. **Part traceability** — no part record is opened, started, recorded or
   dispositioned; the demo counts cycles and scrap locally. Several TC3
   divergences in §2 are this deferral showing through.
3. **Release reports.**
4. **The reusable module library.** Module AOIs are generated **per
   application**; the library form is Phase 6. Nothing here is a module library,
   and the generated types carry the application's name for that reason.
5. **The gateway / repository adapter and the generic HMI** — the next session's
   work, deliberately untouched here.
6. **Physical I/O and any control-power domain.** The plant is arithmetic on
   controller tags, the embedded I/O module is inhibited, task output updates
   are disabled, and the generator refuses any `Local:`/`Discrete_IO:` operand.
7. **`BOOL` members in public contract UDTs** — a recorded S12 hole, still
   unmeasured, still refused.

## 7a. What Phase 4 still owes, and the distance to the gateway

The port plan's Phase 4 lists seven elements. **Three are built and proved on
hardware; four are not built at all**, and those four are precisely what the
gateway/HMI vertical needs from the controller side. Recording that here so the
next session starts from the real position rather than from "Phase 4 is done".

| Port-plan Phase 4 element | State |
|---|---|
| The §6.1 handshake | **built, proved** — generated composition, no base structure invented |
| Lifecycle composition (`Begin`/`End` equivalent) | **built as generated call order**, with the ordering self-check S11/S16 established |
| Diagnostic surface, in miniature | **built** — first-out adoption, reported-not-adopted, named stall reasons, the §3.13 chart |
| **Manifest publication** | **not built** — nothing self-describes; the repository protocol has nothing to read |
| **The registry** | **not built** |
| **Diagnostic/event core** (the HostEvents ring) | **not built** — conditions are published as current state, not as an event history |
| **Release / access enforcement** | **not built** |
| **One provider seam** | **not built** |

So the honest distance to the gateway/generic-HMI session is:

0. **A constraint that binds it, decided before it is built:** the manifest
   describes the declared graph **once, rendition-agnostic**. A chain rendered
   in several languages still has one graph, and the rendition selector is a
   harness input - probe-only, never published. Recorded in
   [`AB_LADDER_EXECUTION_PARITY_2026-09-07.md`](AB_LADDER_EXECUTION_PARITY_2026-09-07.md)
   §11a and enforced in the generator's `publishable_tags`.
1. **Manifest publication is the blocking one.** Core §3.10 and AB §11.2 have the
   HMI discover a station by reading its manifest; S7 already measured what one
   costs to read (43,728 bytes in 293 ms at a 500-byte connection, 62 ms at
   4000, ~32 ms header-only steady state) and R3 froze the schema. What does not
   exist is a generator that **emits** one from the declaration. Everything the
   manifest would describe — modules, commands, reason codes, chains, step
   numbers, the chart layout — is already in the declaration, so this is
   emission work, not design work.
2. **The registry** and **release/access enforcement** are needed before the HMI
   can command anything rather than only render it. The initial claim is
   read-only, so the gateway can be built and proved against reads first, and
   R6 §7 already records that enabling writes re-arms Core §14 in full.
3. **The event core** is needed for the HMI's alarm and event surface. Present
   state is not an event history, and nothing here should be mistaken for one.
4. **A provider seam** is needed for values that do not come from the module
   tree.

What the gateway can already rely on today: contract structures that read
coherently in **one CIP request each** (unit 116 B, chart 404 B, ParCfg 20 B,
module 128 B, all inside the 500-byte S1 ceiling and each about 3 ms), declared
reason codes, a live step cursor with per-step visited marks and durations, a
named stall reason, and the S9 freshness and reader budgets already declared for
the reference station.

## 8. Bench handoff state

The controller **retains the clean press demo in Remote Run**, all fifteen
writable inputs restored to zero and verified. Identity at close:
`1769-L24ER-QB1B/A LOGIX5324ER`, `33.014`, `7036B510`, `state` 3,
`device_status` 48, PTP disabled and `is_synchronized` false.

The S16 fixture's rollback path remains recorded and reproducible from the gate:
regenerate it from a seed, import and Verify it as §3, and download it over the
same USB `Backplane\16` route under fresh authorization. The reference suite and
every spike fixture are reproducible the same way.

Automated download remains unavailable on this workstation; both downloads here
were performed by the user in Studio under explicit authorization, with the
target identity re-read immediately beforehand and all I/O disconnected.

## 9. Status

| Item | State |
|---|---|
| Declaration and generator | **committed; the L5X is output, never hand-edited** |
| S16 findings as generator rules | **five enforced, each with a refusing test** |
| Press demo | **emitted, imported `0/0`, Verified `0/0`, gate leg green** |
| Bench execution | **15/15 rows, three consecutive runs, no variance** |
| Step-graph comparison against TC3 | **recorded, with two behavioural divergences named** |
| Phase 4 | **the runtime base runs, in its generated form** |
| Gateway / generic-HMI vertical | **not started, by instruction** |

No conformance claim is made. The reusable module library, the gateway adapter
and the generic HMI remain unbuilt.
