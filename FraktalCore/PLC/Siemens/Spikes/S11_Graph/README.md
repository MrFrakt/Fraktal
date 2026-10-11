# S11 — S7-GRAPH rendition on a simulated S7-1500

Part IV §3.5 / §12 S11: the S2 AUTO chain as an S7-GRAPH FB, **generated** from a
declaration, run on S7-PLCSIM Advanced. Its step trace must match the SCL
rendition's (`../S2_Shape/40_AutoSeq.scl`). Result 2026-10-09: 19/19, see
[`TIA_S11_GRAPH_PLCSIM_2026-10-09.md`](../../../../../Specification/Siemens/Evidence/TIA_S11_GRAPH_PLCSIM_2026-10-09.md).

Continuation: [`TIA_S11_SEMANTICS_2026-10-09.md`](../../../../../Specification/Siemens/Evidence/TIA_S11_SEMANTICS_2026-10-09.md)
records 28/28 after download and a direct STOP→RUN. `Semantics/make_charts.py`
generates four probes (empty networks, acknowledge, auto-release, skip), with
100 ms maximum time and 50 ms warning time. `Semantics/build.plan` imports them;
`Errors/build.plan` adds the local-error and OB121 tests. Both reuse `FrkS11`.
After generation, pass the export directory as a second argument to
`make_charts.py` to compare settings, times, V/C wiring, actions and transitions.

For a direct simulated warm restart, `Invoke-PlcSimInstance.ps1 -Action halt`
then `-Action run`, both with `-ConfirmTarget 192.168.252.1`, retain registration
and the downloaded image. `off` releases the virtual CPU's memory during offline
TIA builds. `stop` powers off **and unregisters**; a new registration needs the
logged TLS trust step again. Use `status` first: mode changes are restricted to
Softbus and an IP it reports. Validate a full numeric result read with
`tools/plcsim_results.py read.log --cases 1-28 --junit result.xml`.

`Recovery/` adds an independent Unit, a generated three-step GRAPH chart and
host-controlled simulated feedback. `make_fixture.py <new-directory>` generates
the complete build input; `build.plan` rebuilds the existing station's program
without replacing its certificates. `run_probe.py` records one guarded read,
typed write, delta download or mode change to a new log file. Use the approved
`candidate_s11_enumeration` executable; it is never rebuilt by these scripts.
`verify.py <raw-directory>` validates the recorded case sets and recovery
observations. These are test-owner mechanisms, not the full Unit lifecycle.

Results 2026-10-10: 16 checks passed; GRAPH state-preserving RUN delta **unpassed**
([evidence](../../../../../Specification/Siemens/Evidence/TIA_S11_GRAPH_RECOVERY_2026-10-10.md)).
The FC delta preserved observed BUSY/step/DB state. The GRAPH label-only delta
requested TurnOffSequence and DataBlockReinitialization with unchanged exported
interfaces. Do not infer preservation from `--changes-only`. The corrected CM
applies the same interlock to its coils outside the idle guard, so the owner can
withdraw them after a completed command as well as while BUSY. The final image
passed an active restart and stayed idle awaiting a fresh Arm.

| File | Role |
|---|---|
| `reference/FB_GraphSample.xml` | the one chart drawn in the TIA editor, exported verbatim (BOM, CRLF). It is the writer's template, not a source |
| `chain_auto.json` | the AUTO chain declared once: steps, labels, commands, waits, exit conditions |
| `10_GraphServices.scl` | `FRK_Seq_AwaitPending`: a GRAPH action cannot hold an `IF`, so a conditional wait takes its condition as an operand |
| `15_GraphInstance.db` | `"S11Graph"`, the chart's single-instance DB (a GRAPH FB cannot be a multi-instance) |
| `18_GraphOwner.scl` | the owner's lifecycle-only adapter, with the chart as a **parameter instance** |
| `20_GraphRig.scl`, `25_GraphRigInstance.db`, `30_GraphCycle.scl` | test image only: after the S2 harness, run the chart and record cases 18 (trace) and 19 (`INIT_SQ` restart mid-run); OB123 runs after Main |
| `station_1516_plcsim.plan` | one-time S7-1500 station project `FrkS11` (CPU 1516-3 PN/DP V3.0), simulation support on, the S2 sources imported |
| `build_plcsim.plan` | import the services, the generated chart and the rig; compile; save; export |
| `download_plcsim.plan` | download over the `PLCSIM` PG/PC interface only (softbus — nothing on the network) |

## Run

```powershell
$repo = 'C:\Projects\Fraktal'; $s11 = "$repo\FraktalCore\PLC\Siemens\Spikes\S11_Graph"
$work = "$env:LOCALAPPDATA\Fraktal\TiaStations"; $gen = "$env:TEMP\frk_s11"
$cli  = "$repo\FraktalCore\PLC\Siemens\tools\TiaCli\bin\Release\net48\Fraktal.Tia.Cli.exe"
$sim  = "$repo\FraktalCore\PLC\Siemens\tools\Invoke-PlcSimInstance.ps1"

# 1. generate the chart, then check it against the SCL rendition (also run on the export in 3)
python "$repo\FraktalCore\PLC\Siemens\tools\fraktal_tia_graph.py" generate "$s11\chain_auto.json" "$s11\reference\FB_GraphSample.xml" "$gen\FB_SpkAutoGraph.xml"
# 2. build (offline); 3. parity on what TIA stored
& $cli plan "$s11\build_plcsim.plan" --set "work=$work" --set "s11=$s11" --set "gen=$gen"
python "$repo\FraktalCore\PLC\Siemens\tools\fraktal_tia_graph.py" parity "$work\FrkS11_export\xml\FB_SpkAutoGraph.xml" "$s11\..\S2_Shape\40_AutoSeq.scl"
# 4. the virtual CPU lives as long as its host process: start it in the background
Start-Process powershell -WindowStyle Hidden -ArgumentList "-File `"$sim`" -Action host -Name FrkS11"
# 5. download (simulator only), then about 30 s later read the rows
& $cli plan "$s11\download_plcsim.plan" --set "work=$work"
powershell -File $sim -Action read -DataBlocks 'SpkResults,S11Rig' -Match '^SpkResults\.T\.(Passed|Failed|RowCount)$'
# 6. done: New-Item "$env:TEMP\plcsim_FrkS11.stop"   (the host powers off and unregisters)
```

A newly registered instance presents a new certificate. Its first download is
refused, and the recovery is one logged `--trust-plc PLC_1` on the command line,
never in a plan (Part IV §14). The download asks `TurnOffSequence` for the GRAPH
DB; the driver leaves it at its default (`True`).

## The reference chart (drawn once)

Openness V20 creates blocks only in ProDiag, and no GRAPH SimaticML sample is
published. The writer is therefore built against one chart that TIA itself produced:
`FB_GraphSample` in `FrkS11` has two steps (N000 with a `CALL "FRK_Seq_Step"`, N100
with `N` actions), LAD comparison transitions and a jump back. Redraw it only if a new
TIA version changes the export. Then re-run `test_fraktal_tia_graph.py`: it checks
the reader against that export, and the writer's tokens against TIA's own.
