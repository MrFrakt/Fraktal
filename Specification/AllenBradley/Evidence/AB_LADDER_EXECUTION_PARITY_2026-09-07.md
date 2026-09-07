# Fraktal/AB — ladder execution parity, and the press in three languages

**Spike:** S4/S11 language support — extending the proved execution surface to
the third language

**Result:** **The press AUTO graph is declared once and rendered in ST, native
SFC and ladder, all three emitted from that one declaration, machine-checked
for graph equality, and walked on the bench. All three produce byte-identical
per-step entry-count vectors over one cycle, hold identically at the door-close
step, and stand down identically on abort — seventeen parity rows passing on
three consecutive runs with no variance.** This is the first executing ladder
sequence on this bench: S4 proved RLL round-trips, never that one runs. Two
defects were found on the way, one of them only findable on hardware.

**Date:** 2026-09-07

**Repository revision:** `a6e3aff` plus the parity fixes recorded below

**Scope:** two authorized downloads of the three-rendition press demo to the
isolated bench, and eleven executions of its fixed vectors. Writes confined to
the declared input tags, all restored and verified. No fault clear, clock set,
firmware, controller-network, safety, SD-card or physical-I/O operation.

## 1. What was already proved, and what is new

S11 proved that ST and native SFC walk identical traces on this controller, for
a small generated graph. S4 proved that ladder **round-trips** — 26 ladder
routines imported, exported and compared canonically — and said nothing about
execution, because no ladder sequence had ever run here.

New in this record:

* **an executing ladder sequence on the bench**, walking a real application
  graph rather than a construct matrix;
* **three renditions of one graph**, generated from one declaration, rather
  than the two S11 carried; and
* **a machine gate** that reads every emitted rendition back and requires it to
  equal the declaration, which is the AB analogue of the TC3 three-rendition
  consistency rule.

MANUAL and HOME stay single-rendition ST, exactly as the TwinCAT press keeps
them. Only AUTO is carried in three languages, because only AUTO is the graph
the TwinCAT press renders more than once.

## 2. The declaration grew one field

```python
renditions=(decl.ST, decl.SFC, decl.LD)
```

That is the whole change to the declaration. **The graph is declared once and a
rendition is an emission of it**, never a second maintained source. No new graph
syntax was added — the SFC transition conditions and the ladder rung conditions
are *derived* from the same step records the ST bodies are derived from.

`ST` is required to be first: it is the reference every other rendition is
compared against, and `validate` refuses a chain that omits it or lists it
elsewhere.

## 3. What each rendition is

| Rendition | Form | Size |
|---|---|---|
| ST | program routine, one `CASE` over the step number | 397 lines |
| SFC | program-owned chart plus a generated JSR/SFR wrapper | 16 steps, 18 transitions, 4 branches, 40 directed links |
| LD | RLL integer state machine | 18 rungs — 2 preamble, one per declared step |

### Ladder, and the two rules that make it walk ST's trace

One rung per declared step, `EQU(Step,N)` as the rung-in. Two rules matter:

1. **One step per scan.** Rung order is execution order, so a forward
   transition would otherwise fall straight into the next step's rung in the
   same scan and run a whole chain in one pass. Every transition sets an
   advanced flag; every rung's rung-in requires it clear; the first preamble
   rung clears it once per scan. This is the same ordering rule the TwinCAT
   binding enforces for its own ladder rendition.
2. **Rungs ascend by step number**, asserted on read-back, so the text reads in
   the order it runs.

No instruction's result is fed into another instruction's condition inside a
rung. The step clock needs two operations, so it goes through a named scratch
tag: `SUB(Scan,StepScan,Scratch)` then `MUL(Scratch,period,CurrentStepMs)`.

### SFC, and what makes it a chart rather than ST in disguise

The S11 pattern generalised: program-owned, driven by a generated JSR/SFR
wrapper, with the controller set to `SFCExecutionControl="CurrentActive"` so one
JSR advances one step and the trace stays comparable with ST's.

The split is what makes it a real SFC rendering: **the action does the step's
work and the transition carries its condition**, and both are derived from the
same declared step. An ST body that assigned the next step number inside a chart
action would be an ST chain wearing a chart's clothes.

## 4. A Logix constraint the graph was *not* bent to fit

**Logix accepts exactly one directed link into a step.** The declared AUTO graph
converges twice: the loop back to `N100`, and the three ways of reaching `N240`
(from the scrap step, from the record step, and from the decision's other
answer). The first import said so precisely — three
`RxEXE_S_CANNOT_IMPORT_INVALID_CONNECTION` warnings naming exactly those links.

The chart now emits **selection converges** there, which is the chart's way of
saying what ST says with two transitions writing one step number, and what
ladder says with two `MOV`s to the step tag. **No narrowing was required and the
graph was not altered**: the same 16 steps and 18 transitions are recovered from
all three renditions.

The gate had the mirror-image blind spot and it is worth recording, because it
is the exact failure the gate exists to prevent: a branch and its legs are
joined by XML *containment*, not by a directed link, so the walk treated a
divergence as a dead end and the chart read as having **no transitions at all** —
which would have passed silently as "nothing to disagree about" had the step
sets not also been compared. It now follows that edge, in the direction the
branch flows.

## 5. The machine gate

`fraktal_ab_rendition_gate.py` reads the **emitted L5X back** and recovers, in
each rendition's own language, the step set and the transition set:

* **ST** — `CASE` labels for steps, assignments to the step tag for transitions;
* **LD** — `EQU(Step,N)` rung-ins for steps, `MOV(N,Step)` for transitions, with
  ascending rung order required;
* **SFC** — `Step` elements, walked forward through transitions and branch legs.

All three must equal the declaration. **A rendition that cannot be parsed back
fails the build** — "the parser found nothing, so nothing was wrong" is exactly
the failure mode this removes.

| Rendition | Steps | Transitions | Equals declaration |
|---|---:|---:|---|
| declaration | 16 | 18 | — |
| ST | 16 | 18 | **yes** |
| SFC | 16 | 18 | **yes** |
| LD | 16 | 18 | **yes** |

Six negative tests drop a rung, bend a transition, reverse rung order, blank a
routine, delete a routine and bend a chart link, and require the gate to say so.

One read-back subtlety is handled in the emitted text rather than by guessing:
the `CASE ELSE` assigns a step number but is **not** an edge of the declared
graph, so the generator marks it and the parser stops there.

## 6. Offline gate

| Check | Result |
|---|---|
| SDK import | `Warnings="0" Errors="0"` |
| **Studio v33 Verify Controller** | **0 errors, 0 warnings**, input unchanged, closed cleanly |
| Rendition gate | all three equal the declaration |

## 7. Two defects, and which one hardware found

### Found offline, by reading the emitted logic

Nothing — the offline gates passed all three renditions before the first
download, and they were right to: the graphs genuinely were equal. Which is the
point worth taking from this record.

### Found on the bench

**The SFC chart entered its first step and never advanced.** The generated
JSR/SFR wrapper conditioned `SFR` on a **level** — "the unit is on the entry
step" — and the entry step's own action writes that step number. The chart
therefore reset itself to the initial step every scan and could never leave it.
S11's wrapper fired on a genuine *edge*; mine fired on a condition the chart
itself kept true.

It now fires on `PrevStep < 0`, which the owner sets when it stands the chain
down and which the first step to mark itself clears — a real one-shot restart
marker rather than a self-perpetuating state.

**This is the class of defect a static graph comparison cannot see.** The gate
compared the chart and found it equal to the declaration, and it *was* equal;
the fault was in the wrapper that drives it. Graph equality and execution parity
are different claims, and this record needs both.

### Three faults of mine in the measurement, all in the same place

The first parity harness stopped the chain by hand after detecting the cycle,
then compared absolute chart counts. That was wrong three ways, and each fix
exposed the next:

1. **Absolute counts accumulate.** Nothing clears the chart marks, so ST read 1,
   SFC 2, LD 3 for the same step — the comparison was measuring "how much has
   ever run". Fixed by comparing the delta over each rendition's own window.
2. **A looping chain cannot be stopped at a deterministic point.** A read plus a
   write costs more than one 10 ms period, so each rendition was caught at
   whatever step its own speed had reached — `resting` landed on 110, 999 or 100
   across runs. The window was ragged, not the graph.
3. **Withdrawing the start condition late is itself a race.** Doing it after the
   cycle completed sometimes landed after the loop had re-armed the start step,
   and the chain ran a whole further traversal.

The window is now closed **by the machine, not by the observer**: the start
condition is withdrawn as soon as the chain has passed the start step — nothing
after it reads that condition, so the measured cycle is unaffected — and every
rendition then parks on the same declared step whatever its speed. Only after
that is the chart read.

That is the honest form of the measurement. A trace window defined by the
observer's reaction time would have produced a parity claim that depended on
which language happened to be faster.

## 8. The three-form trace comparison

Three consecutive runs, **seventeen rows, all passing, no variance**.

**Per-step entry counts over one cycle — byte-identical across all three:**

| Step | 0 | 100 | 110 | 130 | 150 | 170 | 180 | 200 | 210 | 215 | 220 | 230 | 240 | 242 | 244 | 999 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ST | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |
| SFC | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |
| LD | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |

`N100` is entered twice because it is where the loop closes and where the chain
parks; `N210`/`N215` are zero because the ram did not fail, which is the correct
path for a clean cycle. `OrderFail` was **0** for every rendition — the module
AOIs ran ahead of sequence intent on every scan in all three languages.

**The held condition at the door-close step — identical in all three:**

| | held step | reason | severity | `Error` | stall reason | resumed to | self-resumed |
|---|---|---|---|---|---|---|---|
| ST | 180 | 6130 | 0 LOW | 0 | 6130 | 200 | yes |
| SFC | 180 | 6130 | 0 LOW | 0 | 6130 | 200 | yes |
| LD | 180 | 6130 | 0 LOW | 0 | 6130 | 200 | yes |

**Abort — identical in all three:** `Aborted` raised, chain stood down to step 0,
`Running` 0, no `Error`, and it did not resume by itself.

### Timings, against the declared 10 ms task period

| Rendition | cycle |
|---|---:|
| ST | 969–982 ms |
| SFC | 747–761 ms |
| LD | 948–961 ms |

**The chart is consistently faster, and that is a real observation rather than
noise** — about 22% below ST across every run. With `CurrentActive` execution
the chart evaluates only the active step and its transition, where the ST `CASE`
and the ladder rung scan reach the whole structure each scan. Ladder sits within
about 2% of ST. **None of this affects the trace**: the same steps ran the same
number of times in the same order, which is what parity claims. Latency is
recorded, not matched — the same position S9's decision record took for
cross-binding parity.

## 9. The full matrix against the ST form

The fifteen-row press matrix was re-run against the ST rendition on the
three-rendition project: **15/15 on three consecutive runs**, disarm clean each
time. The reduced matrix against SFC and LD — normal cycle, held condition,
abort — is §8 above.

## 10. Artifacts and hashes

| Artifact | SHA-256 |
|---|---|
| `press7.L5X` (three renditions, generated) | `47C9E59F0D336E5973965DC7B08CAA51DCB9A0C3217DAAECD2A3815C3835C174` |
| **`press7.ACD`** (Verified `0/0`, downloaded) | **`BF31782402C8522F7B951B4E9D8D9227294708C3D3F65949856E674FEDDC8D51`** |

| Tool | SHA-256 |
|---|---|
| `tools/fraktal_ab_declaration.py` | `562B86ECDB37D7BDF6F646EDFEE93BA59BF25584B04DF1B9CE80178681742DA5` |
| `tools/fraktal_ab_generate.py` | `B003A186297C84D96EE37A024A1736030EEFDA75A8B6921AA3BE22B6AD562BE6` |
| `tools/fraktal_ab_press_demo.py` | `7F51D039462F236D7C3813F388C2EE073C1BC9F7C1065EAB2D5DE71E289AB04E` |
| `tools/fraktal_ab_rendition_gate.py` | `B53B679D497B502247C0C4E980C023F052CFCB0CFE6A03A0667E7703476C61D7` |
| `tools/fraktal_ab_press_parity.py` | `200FDE2216B90203AB9644593D083A52DBC34299C5A4F85B98DE7EC4BA21424E` |
| `tools/test_fraktal_ab_renditions.py` | `0BA007A6621792FE611153424E60242ABC3188712C40FD9E877EA21D77E65AD3` |

Studio saved the project during the download session, so the live ACD now hashes
differently — the expected `controller minor 11 → 14` rebinding. The value above
is the artifact as Verified and downloaded.

## 11. What this does not claim

1. **Only AUTO is multi-rendition.** MANUAL and HOME are ST only, deliberately.
2. **Ladder is not claimed for every mechanic in general** — only for the ones
   this graph uses: commanded children, awaited children with first-out
   adoption, a reported-not-adopted child condition, delays, named waits, a
   held condition and an operator decision. A mechanic outside that set is
   unproven in ladder until it is declared and walked.
3. **Simultaneous branches are not exercised here.** S11 proved those for SFC;
   this graph has selection divergences only.
4. **Latency is recorded, not matched.** The chart is faster; nothing requires
   the three renditions to take the same time, only to walk the same graph.
5. **No sub-chain call.** The load-position composite the TwinCAT press invokes
   as a sub-chain is inlined here in all three renditions, as the Phase 4 record
   already noted for ST.

## 12. Bench handoff state

The controller **retains the clean three-rendition press demo in Remote Run**,
every writable input restored to zero and verified, the rendition selector back
at 0 (ST). Identity at close: `1769-L24ER-QB1B/A LOGIX5324ER`, `33.014`,
`7036B510`, `state` 3, `device_status` 48, PTP disabled and unsynchronized.

Both downloads were performed by the user in Studio under explicit
authorization, with the target identity re-read immediately beforehand and all
I/O disconnected. Automated download remains unavailable on this workstation.
