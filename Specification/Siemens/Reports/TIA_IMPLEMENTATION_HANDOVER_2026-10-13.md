You are continuing the Fraktal/TIA Siemens implementation in
`C:\Projects\Fraktal`, branch `main`. Complete the remaining port for TIA V20
on the simulated S7-1500. Continue implementation, compilation and guarded native
testing; do not stop at a plan. The owner requested this fresh-chat handover and
an update to `C:\Projects\SiemensAgent` after the shared sequence-view slice.

Read this entire handover before acting. Earlier chat handovers contain obsolete
target, language, driver and current-project facts; the state below supersedes them.

Read first:

1. `AGENTS.md`, `Specification/README.md`,
   `FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md`.
2. `Specification/Fraktal_Core_Part_I.md`,
   `Specification/Fraktal_TIA_Part_IV.md`,
   `Specification/HMI_CONTRACT.md`, `Specification/OPCUA_TRANSPORT.md`.
   In particular: O1/O4/O9, Core 3.13, 6.8/6.9/6.12, and HMI sequence/read tiers.
3. `Specification/Siemens/SIEMENS_PORT_PLAN.md`, latest progress sections;
   `FraktalCore/PLC/Siemens/README.md`, Framework/Core README and UNIT_SERVICES.md.
4. Latest dated reports:
   `Specification/Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md`,
   `TIA_PERSIST_MEDIUM_2026-10-13.md`, `TIA_LOAD_MEMORY_2026-10-13.md`,
   then the config/access/alarm/recovery/delivery reports they cite.
5. `C:\Projects\SiemensAgent\siemens-kb\tia-automation\INDEX.md`,
   `shared-sequence-view.md`, `shared-load-db-documents.md`,
   `verified-gotchas.md`, `graph-simaticml-and-plcsim.md`.
6. Memory under
   `C:\Users\Siemens\.claude\projects\c--Projects-Fraktal\memory\`:
   MEMORY.md, project-siemens-port.md and naming/language feedback files.
   The latest sections supersede older memory entries.

Standing owner instructions:

- Primary target is the simulated S7-1500 CPU1516, PLCSIM Advanced V7, TIA V20.
  There is no 150KB reference limit. The physical 1214C/192.168.0.10 is secondary
  and is not the current target. Never silently switch to it.
- GRAPH AUTO/HOME and ST permissives are wired into the press demo. The owner
  explicitly added ST and LD examples, initially unwired, and later explicitly
  requested wiring GRAPH/ST. Optional ST/LAD renditions remain uninstantiated.
  Do not re-ask the language/wiring question or restore the old no-Ladder rule.
- Use GRAPH terminology for Siemens charts. Preserve TC3 press jumps and parallel
  examples. No power-control feature and no actual physical press bench available.
  Qualify shared framework behavior synthetically and move on with the port;
  physical wiring/process testing belongs to the owner when a bench exists.
- Use consistent station config / line config / model config names.
- Keep code/raw evidence outside Specification/Siemens (Markdown only there).
  Follow Fraktal groups in both disk and TIA. MAIN is a root calling routine;
  the wired press MAIN remains three calls.
- Shared algorithms own lifecycle, reset, latches, timing, diagnostics and
  publication. Generated typed edges supply device wiring. No application call
  that must be remembered for correctness. Allocate/stream only consumed surfaces.
  Read Core types/ordinals/constants rather than inventing copies. Released Core
  layouts/enums require additive/versioned handling, not silent edits.
- Simulator downloads/testing and SiemensAgent KB updates are authorized. Preserve
  existing user work. Do not stage/commit/push without a request. No subagents
  unless an applicable explicit instruction authorizes delegation.

Current verified state:

- Generator version **0.16**. Shared view uses unchanged Core
  ST_SequenceStepDef/ST_SequenceStep/ST_SequenceCursor/ST_SequenceAnnotation and
  ST_StepRecord. `sequence_view` is an optional Unit declaration with bounded
  capacity/branches/annotations. Private consumed-size work belongs to
  FRK_Views.Vnnn; the owning Unit frame publishes readonly mirrors. This avoids
  a GRAPH/root-FB compile cycle. Definitions travel through the config manifest.
- Frame begin/end controls scan and committed-mode boundaries. Shared sequence
  helpers record visits/waits/notes. PLC history catches fast steps. Deeper
  sub-chain cursors win over parent composites. Warning notes clear on a new
  visit; error notes on authorized reset; full note tables retain row flags.
  Static discovery/guard changes use the Core manifest quiet interval.
- Wired press: **168 sources**, **19 AUTO + 4 HOME GRAPH steps**, native LAD
  **161 networks / 155 calls**, MAIN **3 calls**. Profile: 23 rows, two parallel
  legs, four annotation slots. Load-position local 240/260/280/300 projects to
  **600/620/640/660** through one `view_offset:360`; `view_depth:1` preserves
  leaf cursor priority. Main GRAPH step numbers/transitions are unchanged.
- Native synthetic sequence fixture: **122/122 checks** including actual helpers,
  privacy/readonly access, fast history, guards/config updates, sparse notes,
  row bounds, reset/mode boundary, isolation and STOP/RUN. Runtime compile **0/0**;
  press both compile stages **0/0**, native readback/parity matches. Tool suite
  **183 tests**, cross-artifact suite **35**, shipped lint/consistency pass.
- A Python-only refactor shares the published-member map with lint. Compiled PLC
  source bytes remain identical; the archive binds that comparison. Checked-in
  default structural generation replays 24 sources; press replays 168.
- Current loaded runtime:
  `%LOCALAPPDATA%\Fraktal\TiaStations\Sequence_View_Runtime_20261013\FrkS12\FrkS12.ap20`.
  This is the synthetic sequence/config fixture and uses **LOCAL_RETAIN config**.
  It does not select LOAD_DB and does not represent a combined persistence gate.
- Current separately compiled press:
  `%LOCALAPPDATA%\Fraktal\TiaStations\Sequence_View_Press_Offline_20261013\FrkS12\FrkS12.ap20`.
  This selects **both sequence view and LOAD_DB**, but is compiled offline.
- Prior generator0.15 persistence qualification remains intact:
  **340 consumer + 122 access + 100 state/alarm + 341 recovery = 903 native checks**;
  two UNLINKED banks/key, CRC/generations, bounded FIFO/leases/write rate,
  read-back durability, restore barrier/quiescence and typed fallback/repair.
  Prior runtime/press are Persist_Medium_Runtime_20261013 and
  Persist_Medium_Press_Offline_20261013. Fixture17 docs, press7 docs. Do not say
  those 903 checks were rerun on 0.16's currently loaded sequence fixture.
- Current owner read: Fraktal RUN, both roots MANUAL/READY, logged out, charts empty,
  no blocking alarm and no pending/failed config commit. The keeper is preserved.

Files that own the latest change:

- `tools/fraktal_tia_sequence_view.py` and
  `Framework/Core/sequence_view.scl.in` under `FraktalCore/PLC/Siemens`:
  sizing, private pool/dispatch, frame publication, row/cursor/note algorithms,
  Core-derived manifest facets and revision interval.
- `tools/fraktal_tia_declaration.py`: optional profile validation and reserved
  frame members; `fraktal_tia_generate.py`: version, authoritative type requests,
  generated frame boundary; `fraktal_tia_config.py`: manifest owner components.
- `Framework/Core/sequence_services.scl.in`, `sequence_branches.scl.in`:
  actual helper hooks. `tools/fraktal_tia_examples.py` and
  `Examples/PressDemo/01_PneumaticPress/press.json`: language-shared metadata,
  typed zero guard operand, declared projection, wired press/profile.
- `Tests/SequenceView/{make_fixture.py,probe_web.py,README.md}`,
  `tools/test_fraktal_tia_sequence_view.py`, `tools/tia_lint.py`.
- Checked-in generated packages:
  `Tests/Generator/generated`, `Examples/PressDemo/generated`.
  Generated packages are replayable; edit owners/templates, then regenerate.

Owner/tool facts that must be preserved:

- Simulator instance **Fraktal**, CPU1516, TCPIP, addresses
  **169.254.212.49 and 192.168.1.1**, `ie1/ie2/ie3 = 0` (no physical mappings).
  Keeper PowerShell **PID12728**, no expiry. Never terminate it, unregister the
  instance, create its stop-file or register a replacement. The VM now has16GB;
  obsolete advice to power it off for each build does not apply to this owner.
- Explicit approved driver:
  `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli\bin\candidate_structure_examples\Fraktal.Tia.Cli.exe`
  SHA256 **ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74**.
  Pass `--driver` every time. Do not rebuild/overwrite it. Existing whitelist
  approval persists. Only if a driver rebuild is necessary: finish/review the
  candidate first, preserve the approved binary, then explain the per-hash rule
  and request owner whitelisting. Entry names collide by executable basename.
- Set `FRAKTAL_TIA_SIM_INSTANCE=Fraktal`. Use `tools/tia_target_guard.py` before
  writes/restarts. Reuse `tools/tia_mailbox.py` for complete request arguments,
  sequence-last commit/ack and no replay. API batches are not single-scan snapshots.
- Native Web API user fraktal, host169.254.212.49, pinned certificate:
  `%LOCALAPPDATA%\Fraktal\TiaStations\FrkS12.webapi.pin`.
  Credentials come from DPAPI via `Tests/Access/with_credentials.ps1` into process
  environment only. Never print secrets/hash buffers or put a PIN/password in a
  command, report or handover. Close API connections/logout after work.
- Runtime read helper: `Spikes/S12_TypeMap/simulator.ps1 -Action read
  -DataBlocks 'A,B' -Match 'narrow-regex'`. This can inspect private runtime tags;
  keep filters narrow and exclude credentials. Web private reads return200;
  readonly writes return205.
- Restart only the existing guarded instance: simulator.ps1 halt then run;
  `Tests/Config/cycle_simulator.ps1` for a deliberate simulated power-cycle gate.
  Do not recreate projects/certificates or change adapters as a routine workaround.

Native workflow and evidence:

```powershell
$env:FRAKTAL_TIA_SIM_INSTANCE = 'Fraktal'
$driver = 'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\TiaCli\bin\candidate_structure_examples\Fraktal.Tia.Cli.exe'
python FraktalCore/PLC/Siemens/Spikes/S12_TypeMap/run_plan.py COMPILE_ONLY_PLAN NEW_LOG --driver $driver --require-clean-compile
```

Inspect 0 errors/0 warnings, then run a **separate guarded download-only plan**
with `${download}` and `--download`. `--require-clean-compile` validates after the
entire plan; embedding download can load a warning image before that validation.
Use new output names and keep failed attempts. Use existing source organization
and GRAPH/LAD generators/readers; never handwrite serialized chart networks.

Working directory:
`%LOCALAPPDATA%\Fraktal\TiaSpikes\Sequence_View_20261013`.
Final compile inputs: `candidate_06`, `frames_06`, `runtime_grouped_06`,
`press_07`, `press_grouped_07`; exports: `runtime_export_06`, `press_export_07`.
Final logs: 11_runtime_compile, 13_download, 15_press_compile,
19_native_view.jsonl, 18_press_parity.json, final tool/consistency and owner logs.
The checked-in press manifest reflects the byte-identical generator/lint refactor;
older raw trial manifests preserve their historical authority hashes.
Snapshots, final gate summary/JUnit and SHA256SUMS are sealed in
`FraktalCore/PLC/Siemens/Evidence/Archives/TIA_SEQUENCE_VIEW_2026-10-13`.
Older persistence archive TIA_PERSIST_MEDIUM_2026-10-13 has17,782 files/328,181,297
bytes and was fully verified. Do not rewrite either archive or dated report.

Cheap gates:

```powershell
python -m unittest discover -s FraktalCore/PLC/Siemens/tools -t FraktalCore/PLC/Siemens/tools
python FraktalCore/PLC/Siemens/tools/tia_lint.py FraktalCore/PLC/Siemens/Tests/Generator/generated FraktalCore/PLC/Siemens/Examples/PressDemo/generated
python tools/check_consistency.py
python -m unittest tools.test_check_consistency
```

Broad older fixture lint has eight pre-existing missing-ELSE findings in test-only
stimuli. Shipped source lint is clean. Do not confuse those gates. Capture native
Python test stdout via subprocess binary output rather than PowerShell `>` (UTF16
and NativeCommandError formatting). Author LF/ASCII SCL via write_bytes; check
paths before recursive moves and retain the previous generated package.

Measured pitfalls:

- SCL UPPER_BOUND accepts open arrays here, not CurrentStep.Conds' fixed Core
  array. Bind MAX_STEP_CONDS from Core; do not hardcode a divergent limit.
- The tested LAD importer rejected T#0ms and 0ms for this Time parameter. A private
  typed `Seq.NoTimeGuard` is the qualified workaround, shared by all renditions.
  Do not generalize this to every TIME literal/form.
- ST_Diagnostic has **SourcePath**, not LinkPath. Annotation Key is the
  description key, and SourcePath is the drill-down source.
- Frame/root-DB references from early sequence FCs create a compile cycle before
  GRAPH owner adapters exist. Private typed per-consumer work breaks the cycle;
  the same Unit frame owns publication. No new application scheduling glue.
- Reset spelling is OPERATOR_RESET; the release gate rejects it without a real
  blocking occurrence. A presentation-only error mark is insufficient. Do not
  relax that gate to make a test pass. Login/authority remains real.
- Revision checks must wait for the **latest** metadata mutation, not an earlier
  discovery revision that has already committed.
- E_Mode.MANUAL is1 in current Core; derive ordinals. Avoid guessed constants.
- LOAD_DB restore is asynchronous. Wait FRK_PersistStatus.Restoring=false plus
  expected restored state before login/alarms. StartupCount advances before the
  loader completes. Historical RestoreLost=true with RestoreAcknowledged=true is
  not a newly unacknowledged loss. Normalize timeouts/publisher stimuli between
  old regression suites. Quiesce runs before registry clear.

Finish the remaining port in measured slices:

1. Audit Core/PartIV/plan into a clause-to-source/evidence gap matrix. Preserve
   completed gates; distinguish implemented, native-qualified and open scope.
   Do not infer full conformance from type translation or the growing test count.
2. First close the new view's integration boundaries: native generic HMI manifest
   hydration + deferred rows/notes + live cursors/rendering, with zero station
   code. Existing mapper supports these tables and zero-based array normalization;
   it was not exercised against 0.16's new live table in this slice. Combine the
   synthetic view fixture with selected LOAD_DB and qualify cold restore/quiesce
   publication and relevant regressions. Audit whether the cold barrier can leave
   a stale cursor/mirror; withdraw publication through owning framework paths.
3. Complete shared diagnostic walks, pending/stall reasons, fault/hold adoption,
   annotation lifetime and main/per-leg timing/profiling. Audit complete condition
   recording on command success as well as pending waits, inactive branch fault
   attribution, nested/sub-chain identity/projection and bounded overflow handling.
   The table slice alone does not qualify all Core6.9/8.11 semantics. Keep
   recoverable conditions HELD, precise first-out and one-reset restartability.
4. Complete provider selection/dispatch and remaining line-config/station/model
   contracts, complete validation/migration and generic publication. Use consistent
   naming and one authoritative source for metadata and behavior. Do not add a
   shared super-root to the independent Unit forest.
5. Expand reusable modules/HAL according to the normative port scope and TC3
   ownership idioms. Keep raw I/O in the one hardware driver, encapsulate device
   commands and absorb repeated glue into shared Core. Test no-bench behavior
   synthetically and compile press offline without claiming process acceptance.
6. Complete generic transport/HMI/deployment/provider acceptance and documentation,
   versioning/schema/migration and cross-artifact gates. Reconcile the clause gap
   matrix and final reports; update SiemensAgent with every measured fact and scope.

Still separate/unqualified: arbitrary physical torn writes/endurance, changed
layout/full-download preservation, CARD_FILE/external medium adapters, independent
unattended historian service authentication, S7-1200 fit and physical press safety/
process acceptance. Do not block simulator port progress waiting for a press bench,
and do not declare these passed by inference.

The repository has a large existing dirty working tree spanning Siemens, HMI,
specification and relocated evidence. Those changes are intentional ongoing work;
do not reset/clean them. Continue from current files and preserved evidence, keep
the owner running, communicate meaningful progress, and complete each authorized
slice before yielding.

Post-seal storage note: the archive verifies6,748 files/637,012,841 logical bytes (excluding SHA256SUMS). Copying engineering caches briefly exhausted C:; compression preserved bytes and allowed the complete project copies and checksum seal. The existing projects/keeper were preserved. C: still has less than1GB free at handover: check Get-PSDrive C before another project clone/build series and arrange sufficient workspace capacity. Do not delete sealed archives or user projects. Working trial packages and the new archive use transparent NTFS compression; their logical contents are unchanged. The archive contains the pre-seal handover snapshot; this current prompt adds the measured post-seal storage state.
