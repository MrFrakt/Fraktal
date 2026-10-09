# Fraktal/TIA — S11 GRAPH leg: generated S7-GRAPH chain on a simulated S7-1500 (2026-10-09)

**What this records.** The S7-GRAPH rendition of the S2 AUTO chain, **generated** from a
declaration (never drawn or hand-written), compiled by TIA V20, downloaded to an
S7-PLCSIM Advanced S7-1500 and run against the same two cylinder CMs as the SCL
chain. It walks the SCL chain's step trace, and the restart edge works mid-run.
It also records what GRAPH accepts from a generator and what it refuses. Raw material:
[`TIA_S11_GRAPH_PLCSIM_2026-10-09/`](TIA_S11_GRAPH_PLCSIM_2026-10-09/)
(numbered in order, failures included).

| Item | Value |
|---|---|
| Target | **simulated** CPU 1516-3 PN/DP `6ES7 516-3AP03-0AB0` FW V3.0, instance `FrkS11` on S7-PLCSIM Advanced (API 5.0, runtime 50.42.10.00), softbus only, `192.168.252.1` on the `PLCSIM` PG/PC interface. No physical controller was addressed. |
| Authorization | simulator only. The bench 1214C was not touched. |
| Toolchain | TIA Portal V20 / Openness V20, `Fraktal.Tia.Cli` build `VQkeYU2l…` (whitelisted). Nothing was rebuilt. |
| Image | the S2 sources (`Spikes/S2_Shape`, unchanged), plus the S11 sources (`Spikes/S11_Graph`), plus the generated chart `FB_SpkAutoGraph` |
| Generator | `tools/fraktal_tia_graph.py` from `S11_Graph/chain_auto.json`, with TIA's own export `S11_Graph/reference/FB_GraphSample.xml` as the template |
| Result | **19/19** self-test rows. These are S2's 17 plus **18** (GRAPH trace = SCL trace) and **19** (restart edge mid-run), over three downloads (`14`, `16`, `18`). |

Source hashes: every one equals the `sha256` that the import logged (`05`).

| File | sha256 |
|---|---|
| `S11_Graph/chain_auto.json` | `ff5f149661390ffdafa3344372d6b736ebcde308503dacb2007be9bad5a995d8` |
| `S11_Graph/reference/FB_GraphSample.xml` | `9dfd43265b38aa06cd9410c02d6a080a4bcd6304be592fb262f60893d9c03240` |
| generated `FB_SpkAutoGraph.xml` (`03`) | `433de41e98e4cb4ed75fa1b7f23ed3c7bdaf62ca71d0f34af25561c6be011b29` |
| `S11_Graph/10_GraphServices.scl` | `aec2886008e71f3fe1afaaa8796dc3efa342d36e0c46f3c9b3820e0850101c0f` |
| `S11_Graph/15_GraphInstance.db` | `6d3b00cfae747a305bb783f1020ed734f29dd7006de466a4d08ef407a71fdb30` |
| `S11_Graph/18_GraphOwner.scl` | `85bb1bff44b7028c49ad235d8c2bf5e195396cef324c355ac6e6ceea320565c1` |
| `S11_Graph/20_GraphRig.scl` | `903a987d5ba4ff6a1b9ff291b17c7a20a0f379c802dc59b71febd39d661a2365` |
| `S11_Graph/25_GraphRigInstance.db` | `f88632af2dae0cb4d52033ac880441de4f2ed36005ee6e213a0412ff98db465a` |
| `S11_Graph/30_GraphCycle.scl` | `2a311b8a55a982195ab9c5594575ea78bf6117596c7000d59098efec91832ba0` |
| `S2_Shape/40_AutoSeq.scl` (the SCL rendition) | `df7d48e3b1a67a3f825b0203198a6f44d6ab5d7522b5c77f65b4fe425b0035cd` |
| `tools/fraktal_tia_graph.py` (as committed; regenerates `03` byte-identically. The run used a revision that differed only in a docstring and in creating the output folder) | `6e152c924619dbaa4af89910ba6239d9646821e098c9630b95d4a3ca04370f85` |
| `tools/Invoke-PlcSimInstance.ps1` | `9c6f6258044df41fff939838e502d195206af2ab9c0a8fed89d167800324cca0` |

## 1. What GRAPH accepts from a generator (TIA V20, GraphVersion 6.0)

Openness V20 creates blocks only in ProDiag. The owner therefore drew one reference
chart in the editor, `FB_GraphSample`. Its export is the template, and every form below
was compiled by TIA before the generator used it:

- **Actions** are token streams: `<Action [Event="S1|S0"] Qualifier="N">` with one
  `<Token Text=…/>` per lexeme and a trailing newline token. `S1` runs once when
  the step activates, `S0` once when it deactivates, and a plain `N` runs every active scan.
- **A CALL** has newline-separated parameters, as TIA itself writes them
  (`CALL "FC" ⏎ (P1 := v ⏎ P2 := v ⏎ )`). With commas it was refused ("invalid
  characters"). The writer's tokens equal the tokens of TIA's own export
  (`test_writer_tokens_equal_tias_own`).
- **InOut struct and InOut FB-instance members** can be read and written in actions
  (`#Seq.Issued`, `#CylA.Execute := …`) and in transitions (`01`, `02`).
- **An action is `operand := operand` or a CALL, nothing else.** `IF … THEN … END_IF`
  is refused with "Tag IF not defined". `#Seq.Issued := #CylA.Done AND NOT #CylB.Done`
  is refused with "The operand is missing or has an incorrect data type" (`19`).
- **Transitions** are FBD networks without a power rail: operands, an `A` (AND) box
  with `Card` = n (including n = 1), and a `TrCoil`. A Bool literal `TRUE` is a valid
  operand. A transition with no condition is refused: the owner's first drawing failed
  with "Trans4 missing / no conditions".
- Each step carries the empty supervision (`SvCoil`) and interlock (`IlCoil`) networks
  exactly as TIA writes them, plus the template's `MaximumStepTime T#10S` /
  `WarningTime T#7S`. Connections are `Direct` to the step drawn next and `Jump`
  otherwise.
- **The round trip is exact.** The canonical dump of the generated file and of TIA's
  re-export after import and compile are identical (`07`, `08`). Parity with the SCL
  `CASE` holds on both. The 2-step reference chart, used as a negative control,
  fails parity (`09`).

## 2. A GRAPH FB is not a multi-instance — it is a parameter instance

- Declaring the chart as a static (multi-instance) of an owner FB is refused:
  "The data type '"FB_SpkAutoGraph"' is not supported as a multiple instance". It
  fails the same way with the chart's alarm handling on and off (`04`).
- Declaring it as an owner's **`VAR_IN_OUT Chart : "FB_SpkAutoGraph"`** is accepted
  and runs (`18_GraphOwner.scl`, `20`). The owner adapter calls `#Chart(INIT_SQ := …,
  Seq := …, CylA := #CylA, CylB := #CylB)` and passes its own InOut children
  through. The composition root declares **one single-instance DB per deployed
  chain** (`"S11Graph"`) and hands it in. This is the TIA counterpart of AB's
  per-owner SFC routine/tag set.

## 3. Run results (S7-PLCSIM, cycle ≈ 1.0 ms)

The rig (`20_GraphRig.scl`) runs in a second program-cycle OB, OB123, that executes
after Main. The scan order is therefore the Unit adapter's: children first, then the
chain. The rig starts after the S2 harness has finished.

| Run | Download | Rows | Case 18 trace | Case 19 | Notes |
|---|---|---|---|---|---|
| 1 | `11` (`--trust-plc`, see §5) | 18/18 (`12`) | `0,100,110,120,100,110` | — | 607 chart calls to six steps |
| 2 | `13` | 19/19 (`14`) | same | `0,100,110` | restart on N110's entry scan |
| 3 | `15` | 19/19 (`16`) | same | same | restart once CylB was commanded |
| 4 | `17` | 19/19 (`18`) | same | same | `ExecBBeforeInit` recorded |

The per-scan log decodes as `Log[k] = StepNo·100 + A.Execute·8 + A.Done·4 + B.Execute·2 + B.Done`
(`12`, `18`):

```
0 · 10000 · 10008 · 10008 · 11004 · 11002 · 11002 · 12001 · 12010 …
```

- **The step switch and the new step's actions happen in one call.** The scan on which
  CylA reports `Done` (child called first) is the scan on which T2 fires, N110's actions
  run and N100's `S0` drops `CylA.Execute` (`11004`).
- **Execute is low on a step's first active scan and high from the second**
  (`10000 → 10008`, `11004 → 11002`, `12001 → 12010`). That is the generated pattern:
  `S1 #Seq.Issued := FALSE`, `N #<child>.Execute := #Seq.Issued`, `N #Seq.Issued := TRUE`,
  `S0 #<child>.Execute := FALSE`. It is necessary because GRAPH runs the old step's
  `S0` and the new step's actions in the same call. A child commanded by consecutive
  steps (CylB in N110 then N120) would otherwise never see Execute low, and the
  Core §6.1 Execute-drop reset would never happen. **Cost:** one scan per issuing step
  compared with the SCL chain, where the advance and the issue fall in different scans.
- **Restart edge (`INIT_SQ`).** On the call with `INIT_SQ = TRUE` the chart
  returns to the initial step and runs its actions in that same call. Run 4:
  `StepAfterInit = 0` and `Log2[0] = 0`. It also runs the **active step's `S0`
  actions**: `CylB.Execute` was TRUE before the call (`ExecBBeforeInit = TRUE`) and
  FALSE after it (`ExecBAfterInit = FALSE`). The chain then walks `0,100,110` again.
  On the first call, `INIT_SQ` likewise starts the chart at N000.
- Timing: 607 chart calls (614 ms) for six steps. Most of that is the 300 ms sim
  travel of the retract. Mean cycle 1.01 ms, max 3.97 ms, including the GRAPH runtime.
- Download asks a GRAPH-specific question, `TurnOffSequence` ("Turn off the sequence
  (FB_SpkAutoGraph, DB S11Graph) before loading?"). The driver leaves it at its
  default, `True` (`13`, `17`).

## 4. Tool facts measured on the way

- **PLCSIM power-on race.** The first `PowerOn` after the Runtime Manager cold-starts
  failed with `InstanceNotRunning (-14)` (`00`); seconds later the same call succeeds.
  `Invoke-PlcSimInstance.ps1` now retries up to three times.
- **PLCSIM tag reads.** `UpdateTagList(DB, false, filter)` wants every block name in
  double quotes (`"A","B"`); bare names give `WrongArgument (-8)`. `Read` of a
  `String` leaf returns `NotSupported (-19)`. Both are handled by the new `read`
  action, which is read-only.
- A program-cycle OB written in an SCL source with only a name and a TITLE is created
  as a program-cycle OB and auto-numbered 123. Program-cycle OBs run in number order,
  so the rig follows Main without touching S2's sources.

## 5. Trust on first use, once (simulator)

Registering a new PLCSIM instance gives the simulated CPU a new certificate. The
committed download plan was refused ("certificate not matching", then "Connect to
module PLC_1 failed", `10`). The one-off recovery was the logged `--trust-plc PLC_1`
on the command line, never in a plan (`11`). Every later download used the committed
`download_plcsim.plan` unchanged, with no TLS question (`13`, `15`, `17`). Part IV
§14 is applied as written; the act was on a simulator only.

## 6. What this does not settle

- GRAPH's own **supervision** (`MaximumStepTime`, the V/C networks) and the
  **acknowledge/skip** modes. The template's defaults are kept, and no step reached
  10 s. Whether a GRAPH supervision error must be disabled or mapped to the Core
  §6.9 stall walk is still open.
- **STOP→RUN, download with reinitialization while RUN, and error-OB behaviour** — the
  remaining S11 items. Also the GRAPH form on a **physical** S7-1500: the bench CPU is
  an S7-1200, which has no GRAPH.
- Alternative and parallel GRAPH branches (`Branches` stayed empty) and decisions/jumps
  beyond the one `Jump` back to N100.
