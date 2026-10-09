# S11 — S7-GRAPH rendition on a simulated S7-1500

Part IV §3.5 / §12 S11: the AUTO chain as an S7-GRAPH FB, run on S7-PLCSIM, with
the same step trace as the SCL rendition (`../S2_Shape/40_AutoSeq.scl`).

| File | Role |
|---|---|
| `station_1516_plcsim.plan` | one-time S7-1500 station project `FrkS11` (CPU 1516-3 PN/DP V3.0), simulation support on, the S2 sources imported |
| `download_plcsim.plan` | download over the `PLCSIM` PG/PC interface only (softbus — nothing on the network) |
| `../../tools/Invoke-PlcSimInstance.ps1` | hosts the virtual controller (`-Action host`, background); `status`, `stop` |

## The reference chart (drawn once, then never hand-written again)

Openness V20 creates blocks only in ProDiag, and no GRAPH SimaticML sample is
published, so the generator is written against one chart that TIA itself
produced. Draw it once in the TIA editor, in `%LOCALAPPDATA%\Fraktal\TiaStations\FrkS11\FrkS11.ap20`
(close every Openness run first):

1. **Program blocks → Add new block → Function block**, name `FB_GraphSample`,
   language **GRAPH**.
2. **Interface:** `InOut` → `Seq` : `"FRK_SeqCtx"` and `CylA` : `"FB_SpkCylinderCM"`.
3. **Chart:**
   - Step 1 (initial) — rename `N000`. Action: qualifier `N`, a call of
     `"FRK_Seq_Step"` (StepNo `0`, StepName `'s.start'`, Seq `#Seq`) if the action
     editor offers calls; otherwise `#CylA.Execute := FALSE`.
   - Transition `T1` — FBD comparison `#Seq.RetVal == 1`.
   - Step 2 — rename `N100`. Actions: `N` `#CylA.Execute`, and `#CylA.Command := 1`.
   - Transition `T2` — FBD comparison `#Seq.RetVal == 1`, then **jump** to `N000`.
4. **Save the project and close TIA Portal.**

The export of that block (`export --plc PLC_1 --out …`) is the reference the GRAPH
writer (`fraktal_tia_graph.py`) and its reader are built and tested against.
