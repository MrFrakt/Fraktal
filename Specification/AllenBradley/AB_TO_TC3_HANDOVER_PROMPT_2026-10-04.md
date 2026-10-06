# AB implementation lessons — TC3 handoff

Date: 2026-10-04. Source baseline: press75 generator (`1528eab`) with completed
fit and scoped native regression/Line acceptance. This is a working handoff, not a claim
that TC3 has these capabilities or that the AB port is complete. Copy the fenced
prompt into a fresh coding-agent chat opened at the repository root on the
licensed TwinCAT workstation. Linked history is evidence; the specification is
the authority. The project distribution now uses AGPL-3.0-only; see
[LICENSING.md](../../LICENSING.md), preserving historical MIT and third-party rights.

```text
Execute the AB-to-TC3 transfer described here. Audit what TC3 already does, then
implement missing portable behavior at its owning framework/provider level.
Do not blindly copy Logix representations, claim complete AB parity, or duplicate
the generic HMI fixes. Commit reviewable changes on main unless the current
workspace requires isolation; never discard unrelated changes or push unasked.

READ FIRST
1. AGENTS.md, Specification/README.md, FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md.
2. Core Part I: §1.1 O1/O4/O7/O9/O10, §2.2, §3.8a–e, §3.10/3.12/3.13,
   §6.1/6.8/6.9, §7.6/7.7, §8.3/8.5/8.10/8.11/8.12, §14.
3. Part II, HMI_CONTRACT.md, OPCUA_TRANSPORT.md, FIRST_PROJECT_AGENT_GUIDE.md,
   TWINCAT_XAE_WORKFLOW.md. Use the first-project phase/evidence workflow for any
   target deployment or HMI-connection troubleshooting.
4. AB_NEW_PROJECT_GUIDE.md, AB_TC3_PARITY_AUDIT_2026-09-29.md and the evidence links
   following this prompt. Audit historical claims against their dated acceptance.

ST organization follow-up (2026-10-05): prepared press77 centralizes runtime
ST layout at serialization and replaces the long program scan with named
responsibility services from one ordered plan. Configuration write/capture and
set transactions remain inside their authorized mailbox arms, with ACK/wipe
owned by the caller. Repeated calendar candidate copying is shared once with
existing scratch. Expanding only the new zero-argument services reproduces
every pre-existing executable token; AOI/RLL/SFC structure, contract identity,
public data and initializers are unchanged. Declared data delta versus press76
is zero, ST terminators -28. Source whitespace grows; routine metadata/call
overhead and native timing are unmeasured. The SDK refuses No valid license;
licensed Studio Verify/Capacity/completed download remain owner gates. A guarded
read now sees press76's V3 contract, but no new memory/acceptance record.
Transfer clear ownership, consistent layout, shared behavior and execution-order
proof to TC3's existing FB methods/hooks. Do not recreate Logix program services
or a string formatter in TwinCAT, split the inherited lifecycle, rename released
contracts for style, or assume a source reduction proves compiled savings.
See Specification/AllenBradley/Evidence/AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.md.

Configuration memory follow-up (2026-10-05): press77's native download reaches
compilation/linking but fails globally; offline data/logic is 799,860 / 786,432
bytes (13,428 over). Press78 retains the organized services and formatting,
groups immutable capability facts with equal bounds/flags/type, and selects a
snapshot kind once before copying its fields. Each field retains its own commit
address and access policy; inactive-model selection, validation-before-commit,
audit, ACK/wipe and all capacities/features stay unchanged. Only ConfigWrite
and ConfigSets differ; declared-data delta is zero, ST terminators -156 and
ST source bytes -12,373 versus press77. All 205 old/new execution cases preserve
every tag. The owner reports "its good now" and requests commit/push, without
new exact-artifact Capacity/download evidence. Press75 remains the last measured
memory baseline. Transfer shared fact selection and bounded snapshot ownership
where TC3 has duplication; preserve provider methods and released contracts.
Do not infer compiled savings from source counts or relax permissions to save
code. The embedded source is also a target budget item on Logix; native memory
and timing must still be measured after structural refactoring.
See Specification/AllenBradley/Evidence/AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.md.

Shared HMI cycle-chart follow-up (2026-10-05): detail reads now follow the
selected tab's visible/access-permitted cards and authored tag bindings;
closed-tab history and sequence tables must not crowd cycle-chart refreshes.
Child timing scopes to the owning root, not a child browse alias. Successful
bounded sweeps renew on the slow cadence without adding a complete-poll gap
after a long sweep; old batches still expire independently and cannot renew
station health. Tab scoping alone was insufficient with concurrent AB readers:
the gateway now shares Good native records through an optional targeted
DataValue envelope, preserving source quality/timestamps/age. The shared web,
IO and reconnect clients preserve that age rather than renewing cached values.
Production still exposed expiry across leaf sweeps. Budgeted tiered transports
now promote only visible detail to the slow snapshot tier; closing the view
excludes it again. Native record refresh is shared across viewers, while the
non-tiered fallback retains bounded targeted reads. Source freshness is unchanged.
An optional snapshot processing bracket removes duplicate acquisition time from
the client transit allowance, with strict bounds and legacy compatibility.
Implement that bracket at the age-calculation boundary if a TC3 gateway offers
it; do not infer source UTC or widen deadlines to hide delivery cost.
Budgeted full polls now resume immediately after a period overrun, with one
acquisition in flight; fast reads still respect the declared minimum period.
Skipping to a later timer boundary had spent the remaining freshness margin.
Partial native ACKs keep their own quality and cannot renew station health;
legacy scalar readValues remains compatible. Reuse the shared HMI repair for TC3, do not duplicate it or
relax freshness. Repeat representative large-forest measurements on TC3;
press75 evidence is a named-bench check, not a TC3 latency claim. See
Specification/AllenBradley/Evidence/AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.md.

Shared filter-navigation follow-up (2026-10-05): an empty withdrawn forest
must not erase the selected module path or local tree scope. A sub-frame
STALE/LIVE recovery previously opened the plant overview without painting the
connection screen. The shared AppState now preserves navigation intent while
current module data/session permissions still disappear. The connection owner
continues to gate sustained STALE/DOWN; a populated replacement forest still
invalidates removed selections. Regression coverage exercises filters through
the full bootstrap and checks mounted tab/filter retention between frames.
Reuse this shared fix; do not cache usable PLC data or relax quality deadlines.
See Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_NAVIGATION_2026-10-05.md.

Painted filter recovery supersedes the between-frame scope above: actual
time/event filter use can delay samples under rendering load and paint the
connection gate. Detail remounts now restore the tab ID and per-view filter
choices from shared HMI-only state. Usable PLC samples, permissions and commands
are never retained there; expiry and the connection gate remain unchanged.
Selection geometry updates immediately and card/control repainting is isolated.
Tests paint both STALE and DOWN gates, verify the shell/data/session withdrawal,
then check the remounted Statistics and Events views and choices. Reuse this
shared fix and repeat active-filter stress on TC3. Schema-4 settings now preserve
the earlier language setup fields on reload. This adds no PLC/gateway storage.
See Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.md.
Owner hard-refresh acceptance of tab/filter retention is recorded separately in
Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_OWNER_ACCEPTANCE_2026-10-05.json.

Shared HMI follow-up (2026-10-05): QUERY_CONFIG capacity is binding-owned,
not a universal 16-entry limit. Press75's 22-entry page was refused by the
client, leaving all config cards empty and hiding Configuration. The generic
repository now bounds counts by the freshly read discovered rows and refuses
missing fields/duplicate slot aliases; flat AB and container TC3 names are
covered at 16, 22 and 35 entries. Typed Boolean read text 0/1 is normalized to
FALSE/TRUE at the shared manifest mapper; write validation is unchanged.
Reuse these repairs; do not enlarge the TC3 PLC window or duplicate them in a
station view. See
Specification/AllenBradley/Evidence/AB_PRESS75_HMI_CONFIG_PAGE_CAPACITY_2026-10-05.md.

KNOWN STATE / LIMITS
- AB's last accepted loaded/memory baseline is press75 on 1769-L24ER-QB1B fw33.014,
  serial 7036B510 at 192.168.100.89. File SHA-256:
  82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5.
  Manifest 94E302F650BA1DB5 / 9757442, major 4 / binding 2, 65,552 bytes.
  Owner confirmed full download at 0/0 and Run. Online data/logic is 758568 /
  786432 bytes, with 27864 available (3.54%) and largest free block 27376.
  Native full manifest/captured banks and S3 6/6 pass; press70's historical
  159 restored regression rows retain their earlier scope. Live M-101 HMI
  repository read passes; Chrome/upgrade retention
  are separate. Do not overwrite its expanded catalog with an old seed image.
  Press75 now supplies 159 successful restored rows across eleven suites and
  17 Line assertions: complete calendar transactions/export/import, effective
  permissions, twelve-hour weekend activation and its natural end/restoration.
  Final S3 is 6/6, max scan 8384 us against 10000 us, no faults/overlap and
  fresh gateway health is ready. Selected successful suites span three runs;
  interrupted runs remain failures. Two real Line history closures are kept.
  Chrome controls, physical Line retention and mirror/shared-root transport
  remain separate; this is not a full hardware calendar/overflow matrix.
- Main modes, recoverable holds, three AUTO renditions, diagnostics/reports,
  profiler/OEE/state, capture/station sets, controller users/classes/shelving and
  qualified write-enabled S9 have reference-bench proof. That is not every TC3
  press feature: Part carrier traceability, tower/host, nameplate/
  optional safety profiles and some platform probes remain absent/unclaimed.
  Power/control-domain behavior was deliberately excluded. Do not port those
  omissions back into TC3 or weaken its safety/control-power commissioning gates.
- Press69 failed Studio Verify on nested array subscripts. Corrective press70
  is accepted at the scope above. It adds inactive model creation, current
  export and the press-demo Changeover air-entry scope. Data +2700 bytes,
  ST +5135 bytes/+59 terminators/+54 lines over press68; these are not compiled fit.
  Dynamic permission lookup samples the validated ordinal into existing scratch
  before indexing; no extra data storage. This is a Logix compiler constraint,
  not a reason to change TC3's indexing or relax either binding's permissions.
- Press75 loads optional Line owner/calendar V2: weekday masks,
  explicit start/duration, overnight/week-wrap validation, unscheduled index 0,
  bounded PLC history and complete calendar transactions. Core 8.5.2 defines
  the additive V2 contract and exact daily-calendar migration. The generic
  editor/history changes are already shared; do not duplicate the UI on TC3.
  File C:/work/press75.L5X SHA
  82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5,
  manifest 94E302F650BA1DB5 / 9757442. Native fit passes; boundaries/browser/
  retention have separate acceptance. Mirror/shared-root composition is unbound in AB. Do not
  treat offline source tests as a full Line conformance claim.
  Press71 hit LineValidate memory exhaustion. The correction checks six row
  pairs with weekday-mask intersection/rotation instead of four nested loops
  and day lookup CASEs. A <=24-hour duration bounds possible overlap to same
  or adjacent days. 2020 calendars match an independent interval oracle.
  Press72 verified/compiled but failed during controller linking at LineValidate.
  Press73 reduces discovery reserves and shares ST/SFC step-entry bookkeeping
  at the original call point; PLC visits, timings/history, all three renditions,
  permissions and four users remain. Press73 also fails with a final global
  memory error after named routine linking. Owner Capacity Estimate reports
  data/logic 799428 / 786432 bytes (12996 over), I/O 2640 / 1048576. Press75
  shares native alarm open/close bodies with existing scratch, groups equal
  rationalized priorities and emits restore defaults once per record. It removes
  240 ST terminators from press73 without data/layout growth. Over accepted
  press70: data -1812, ST -30972 source bytes/-447 terminators/-413 lines.
  Owner-confirmed full download and online Capacity now prove press75 fit.
  The press73 estimate and press75 online use have different measurement bases;
  their subtraction is not claimed as a directly measured compiled saving.
  Source/data trends do not measure compiled saving. Capacities changed in
  press73 but released UDTs/AOIs/LD and logical manifest identity did not;
  readers separately refuse old capacities. Exact artifact confirmation remains required.
  Transfer the ownership/proportional-allocation lessons, not these Logix limits
  or this representation, to TC3. Preserve failed-build evidence.
- TC3 Core source is 0.22.0.0, Modules 0.10.0.0. Shared enum reserves CREATE_MODEL 37
  and EXPORT_CURRENT_CONFIG 38 only. TC3 currently publishes neither positive
  ModelCapacity nor Features/ExportCurrentConfig, and its dispatcher refuses
  unsupported kinds. Do not expose a button before its provider/PLC path exists.
- The AB host could not reach TC3 compilation: DTE18 configuration selection
  failed at SolutionContexts.Item(1) with System.ArgumentException (Index);
  DTE17 COM startup failed 80040154/REGDB_E_CLASSNOTREG. Resolve the compiler gate
  on the licensed TC3 host before treating the shared enum release as validated.
  These are host failures, not proof that the source compiles.

PRIORITY A — MISSING TC3 CAPABILITIES
1. Runtime model creation through the existing root/provider ownership.
   New model = unique code plus an inactive copy of an existing model or a
   complete saved Model set. It must never switch active ModelCode/ParCfg, move
   existing ordinals or skip normal PrepareRecipe/readiness/CommitRecipe.
   Validate code/capacity/schema/complete field coverage/type/range and every
   effective read/write permission before committing; Count/publication last.
   Refuse full/duplicate/missing/foreign/stale/incompatible requests atomically.
   AB's eight slots/80 printable-ASCII bytes are reference bounds, not a reason
   to invent incompatible TC3 types. Follow the shared contract and declare any
   narrower binding policy. Creation may run BUSY only when existing/active
   storage and indices are untouched; editing/activation keep their normal gates.
   Keep stable provider-owned record addresses, not pointers into temporary
   buffers. Declare retention and migration across boot/download separately.
   Generated upgrades must preserve the expanded catalog and every recipe bank,
   not only source-declared seeds. AB initial-config images now validate optional
   modelCodes with stable seed ordinals, capacity, unique codes and complete banks;
   generated boot tests pass without layout growth. Native upgrade/credential
   retention is separate. Apply the same ownership/validation principle to the
   TC3 provider; do not copy Logix XML serialization or assume its retention.
   Source to compare: fraktal_ab_models.py, fraktal_ab_sets.py, fraktal_ab_initial_config.py,
   test_fraktal_ab_models.py, test_fraktal_ab_initial_config.py;
   TC3: FB_UnitBase, FB_LocalRecipeProvider, I_RecipeProvider/I_RecipeStore,
   FB_ConfigSetJson and the existing model page/capability registration.
   Do not add application-specific clone wiring to each Unit or mutate a recipe
   by direct HMI writes. No disposable native creations without an owner plan:
   AB creation has no delete and cannot be restored by ordinary fixture cleanup.
2. EXPORT_CURRENT_CONFIG 38: permission-checked immutable snapshot of current
   configuration or selected inactive model, without consuming a saved-set slot.
   Return the header/continuation lines in the declared protocol; reject an
   incomplete document. Isolate connection/session exports and interruptions;
   recheck per-value read permissions before disclosing a line. No replay.
   Current/saved file-download UI is already shared. Implement provider/backend
   support and publish Features/ExportCurrentConfig only after it passes tests.
   Do not overwrite a named saved set as an export scratchpad.
3. Model-set workflow: distinguish a stored snapshot name from ModelCode.
   CREATE_MODEL from set appends inactive storage; it is not LOAD into the running
   model. Both bindings deliberately refuse running-model load until atomic
   provider/Changeover integration. Do not remove that refusal to satisfy the UI.
   AB recognizes only its exact pre-catalog revision when value schemas agree.
   TC3 migration needs its own explicit compatibility check, not accept-all
   ConfigRev or partial application. SchemaVersion is first and versioned.
4. Press-demo Start policy: review TC3's FB_PressDemoRelease/state owner. Remove
   only the compressed-air entry condition from Changeover's Start set as the
   owner requested for AB; retain it in AUTO/HOME and retain every cylinder/
   directional pressure permit. The action consumes the same report the HMI
   shows. Never hide a condition only in UI or bypass motion/safety permits.

PRIORITY B — PORTABLE DEFECTS / REGRESSIONS TO AUDIT
- Stale Done on reissue: AB native SFC visited steps while skipping door close,
  press and slide commands. Require the Execute-low reset boundary and fresh
  command lifecycle before accepting old Done. Verify actual command counts,
  end positions and repeated cycles in ST/SFC/LD, not just equal step traces.
  Rung order is execution order; Reset then Set in the same scan is no low scan.
- Hold/recovery/time: two-hand/hold-to-run release is HELD, outputs withdrawn,
  low pending reason, auto resume. A paused dwell must not consume its remaining
  delay. Faults are defects. One operator reset releases all issued child command
  latches and leaves restart possible; do not loosen release conditions instead.
- Diagnostic first-out: stamp onset and record transient warnings/history on
  PLC. A handled report must not latch the Unit diagnostic forever. Capture
  adoption while the child still owns its cause; join I/O identity by role, not
  similar description text. Publish one authoritative Diagnostic per module.
- Profiler/OEE: keep completed steps/commands on PLC; scope visited/chart rows
  to mode, preserve raw time classes. RESET_OEE retires its own timing/trend epoch
  without silently clearing part counts. Trend slots use their own bucket/count
  snapshot. Bracket real acquisition time in fixtures instead of widening budgets.
- Config sets/access: preserve a matching PLC permission refusal even if the
  previous set-state Sequence differs. Only accepted operations require their
  matching set snapshot. Stale reject indices/results cannot authorize mutation.
  PLC owns role and effective value access. Capture ignores client candidate;
  loads validate every value before commit; exports check all read access;
  SAVE/DELETE use CONFIG_SET alone for opaque storage. Audit identity is the PLC
  session, never a claimed User field. Read queries do not renew idle timeout.
- Shelving: resolve unique event identity, preserve blocking/safety behavior,
  clear shelf state on slot reuse and expire by monotonic/task time even after
  logout. An alarm is not granted a bypass merely because it was shelved.
- Login/result race: ACK means request consumed, not authentication complete.
  HMI waits for its correlated result/session; old LoginFailed cannot paint a
  failure ahead of success. LoginBusy/outcome sequence are optional metadata,
  with correct fallback for TC3's synchronous path. Logout cancels pending work.
  Test delayed completion, refusal, stale outcome, disconnected read and successful
  modal closure. AB's costly v33 hashing motivated its gateway prefix/final-PLC
  hash path. Keep TC3 native authentication until timing/security measurement
  justifies a change; do not move role authority into the gateway.

PRIORITY C — ALREADY SHARED; VERIFY TC3, DO NOT REIMPLEMENT
- Calendar V2 weekday editor and shift table: use a new TC3 calendar type and
  schema, not extra members silently added to released ST_ShiftCalendar.
  Retain UTC-offset policy; derive V1 duration from the next start with all
  days selected, including sole 24-hour shifts. Validate whole half-open weekly
  intervals before commit; Sunday overnight belongs to Sunday. Add the portable
  duration/day write keys only after the PLC/provider path exists. Unscheduled
  intervals keep production; edits wait for the finite boundary, and empty
  calendar edits preserve accrued counts unless an active shift begins.
  Closed history stays immutable; forward jumps close once with unverified
  quality, backward jumps never rewrite it. Snapshot before reset, preserve
  trends, and keep manual OEE reset baselines aligned with factors. TC3 already
  stores computed factors; do not copy AB's DINT raw-input representation.
  Sources: fraktal_ab_line.py/test_fraktal_ab_line.py and Core 8.5.2/HMI contract.
  Run the actual TC3 compiler and both runtime gates after the PLC implementation.
- Five-slot schedule/production targets (2026-10-05): AB now emits calendar
  V3 with three weekday-capable and two weekend-capable slots, each independently
  configured; it does not enable a new schedule during migration. Add new TC3
  calendar and shift-record types and explicitly migrate V1/V2 persistent
  images. Raise the declared row capacity to at least five for this bench;
  preserve existing indices, append an unused fifth row and zero targets.
  Per-row `ProductionTarget` counts good parts per root, 0 unset, with portable
  `line.shift.<index>.productionTarget` keys and PIECE units. Whole Line sets
  include every calendar/target field, and effective ENGINEER-or-higher policy
  still applies. Latch `ShiftProductionTarget` at interval start, close its
  immutable target into history before resetting, and defer target edits to
  the same boundary as the calendar. Unscheduled target is zero. The shared
  HMI already maps/renders these optional fields, supports fifth-row weekdays,
  and derives current/history attainment from existing good counts, including
  overachievement; goals never stop production. Preserve reset/clock flags.
  AB's 21-field Line set, 30 total capabilities, schema-3 expanded arrays and
  raw DINT history are binding details, not TC3 layout prescriptions. Sources:
  `fraktal_ab_line.py`, `fraktal_ab_initial_config.migrate_line_v2`,
  `test_fraktal_ab_line_targets.py`, Core §8.5.2 and HMI_CONTRACT.
  Offline press76 is prepared; press75 remains the loaded/native-fit baseline
  until owner Capacity Estimate, Verify and completed download are recorded.
  Run TC3 library installation, actual compilation and both runtime gates;
  add generated/runtime tests for all five boundaries, Sunday wrap,
  target edits during a shift, unset goals and immutable history.
- HMI time-type filters for cycle trend, Pareto and Gantt; visible Gantt durations
  concatenate on a linear axis with hidden time excluded, full-cycle header and
  original starts in tooltips preserved. No irregular/nonlinear timescale.
- Shared 8 px inline spacing, equal Show-all/legend height, control presets covering
  interactive filters/checkboxes/buttons/switches and editor actions; compact
  read-only badges retained; time-quality indicator first in health metrics.
- Generic configuration selector and dialogs: retain static published paths
  until exact manifest replacements are hydrated; exclude only unconsumed data.
  Parameter sets stays open during live detail traffic. File exports are JSONL.
- Selected model pages now read the discovered response subtree, including AB
  flat Entries[i] and TC3 container names; optional absent fields are not queried.
  Capture each config reply before awaited cleanup/polling can replace shared
  values. Failed page reads cannot substitute another model's cached recipe.
  This repair is already in the shared HMI; verify on TC3 rather than copying it.
- Complete-sample freshness: independent monotonic expiry during stalled RPC,
  detail/ACK reads cannot renew whole-station health, commands recheck immediately
  before delivery. Do not extend deadlines to hide starvation or reconnect loops.
- Shared transport watchdog and bounded detail scheduling landed in both client
  paths. AB concurrent request handling retains native read/mailbox locks; audit
  TC3 gateway scheduling before proposing the same change. Cancel queued commands,
  drain active work and never replay on disconnect. TC3 native segmented transport
  has separate unfinished evidence: AB's packed CIP frame is not an OPC UA fix.
- D6 health writeAccess reporting exists in both gateways; AB healthz/livez/readyz
  readback is active, TC3 remains offline-checked. Verify scope/allow-all/read-only
  diagnostics without exposing bearer credentials. Health 200/static page loaded
  is not proof of writable PLC readiness.
- Check exact served asset SHA, HTTPS origin/proxy/certificate/startup and the
  actual running client before debugging PLC state. Reboot lost the AB proxy,
  not the gateway code. The owner restarts approved write gateways; do not start
  one yourself or change firewall/authentication to work around a stale client.

ENGINEERING / MEMORY LESSONS
- One source per fact and common behavior once at its owner. Reuse bounded
  provider/capability tables and framework lifecycle; remove repeated project
  wiring rather than documenting a required extra cyclic call.
- Qualify configuration ownership by its record as well as member name. A Line
  field may share a name with a recipe field; model-bank routing, export,
  creation permissions and audit attribution must still stay at the right owner.
  The generated Press bytes are unchanged by this generic ownership repair.
- Track compiled task stack, scan cost, overlaps and object/data/code footprint
  on TC3. AB Verify/link OOM proved source/data trends are not native fit. Do not
  import its four-user limit or DINT-only/string/numeric-key/operator restrictions
  into IEC/TwinCAT; TRUE and native strings/types remain valid there.
- Follow TC3 by-reference rules for large reports, no property-member chaining,
  no reserved names, no standard string calls beyond255. FB_ConfigSetJson's byte
  routines are the reference for long JSON lines. Pointer/interface storage is
  implementation-only; root-only OPC UA instance publication must remain clean.
- Generate SFC/LD and dump the graph after edits. Native compile is mandatory;
  install Core first, then Modules, before dependent solutions resolve placeholders.
  Keep additive/versioned released contracts and update both lender/borrower
  manifests, versions and consumer pins. Do not fake optional capabilities.
- Native fixture commands reread settled request/ACK state every time, compare
  uint32 bit patterns across wrap and refuse a changed cursor before commit.
  Alternating gateway/direct helpers must not reuse a cached process counter.
  Isolate direct fixtures from HMI tabs: a different process is outside the
  gateway's serialized writer. Require the login's own result sequence and a
  running task. Restore in finally and read independently. Wait on counters/
  stable states. Start watchdog timing before command/setup/snapshot acquisition;
  also inspect the PLC elapsed value. Derive expected record version from the
  declaration; optional features can require a versioned state type. Preserve
  failed evidence rather than widening deadlines or editing old results.
- Owner observed admin and one air-threshold value surviving physical cycles
  on press68. That is not the full persistence matrix, saved/model survival,
  upgrade retention or measured durability window. Preserve commissioned values
  through a validated schema-aware plan, never reset defaults silently.
- Write shared native behavior once at its owner: alarm slot allocation,
  initialization and close-to-ring need one body each, with event-specific
  identity left to the caller. Preserve full-list refusal, reset classes,
  timestamps, counts, shelving and wrap; never move history to client polling.
  AB compares 384 mixed alarm scans and 512 startup images against the previous
  emitted ST and kills eight service mutants. Group equal rationalized priorities
  without changing unknown-reason HIGH fallback. Default installation can be
  shared by never-written and rejected images while only rejection raises loss;
  valid images and later scans must remain untouched. Audit TC3 ownership and
  compiler/runtime behavior before adopting a comparable change; do not copy
  Logix global scratch or its platform memory limits.

GATES / DELIVERY
1. Baseline checks, then meaningful tests for each portable behavior and semantic
   mutants that remove bounds/permission/atomicity/reset/freshness guards.
2. TC3 lint in modern and 4024, tool discovery, root consistency/root tests.
3. Library changes: Invoke-TwinCatLibraryInstall.ps1 (Core before Modules), then
   Invoke-TwinCatBuild.ps1/CheckAllObjects for the configured solutions. Resolve
   DTE host selection issues rather than reporting an empty Error List.
4. Run aggregate Core/Modules TcUnit and separate PressTests on an isolated test
   runtime with boot Autostart off. Never deploy tests as a machine application.
5. Shared HMI/client/gateway changes: tests, analyzer, pinned Flutter build;
   prove targeted reads, complete freshness, cancellation, dialogue stability and
   current/saved exports with TC3. Do not assume AB native proof transfers.
6. Before target actions use the first-project guide, current authorization,
   exact target checks and restoration plan. Power/control safety gates remain
   commissioning-engineer decisions. No download, clock/fault/network change or
   native write based on this handoff alone.
7. Append dated evidence.md/json, update implementation notes/claims/guides and
   report implemented/offline/native/browser/retention states separately. Preserve
   press69 Verify failure, press70 acceptance boundaries and old MIT history. Commit with
   Co-Authored-By: Codex <noreply@openai.com>. Do not push unless requested.
```

The sources below bound the claims in that prompt. They do not grant new target
authorization or transfer a hardware PASS to TC3:

| Topic | Source / evidence |
| --- | --- |
| Current AB status and remaining scope | [parity audit](../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md), [new-project guide](../Guides/AB_NEW_PROJECT_GUIDE.md), `tools/check_consistency.py:AB_ABSENT` |
| Skipped SFC strokes and physical-action tests | [press39 failure](Evidence/AB_PRESS39_SFC_STALE_DONE_ON_HARDWARE_2026-10-01.md), [press40 acceptance](Evidence/AB_PRESS40_ON_HARDWARE_2026-10-01.md) |
| OEE/command timing | [OEE](Evidence/AB_PHASE5C_OEE_ON_HARDWARE_2026-10-01.md), [timing](Evidence/AB_PHASE5F_COMMAND_TIMING_ON_HARDWARE_2026-10-01.md) |
| Access performance/result sequencing | [split hash](Evidence/AB_PHASE6_ACCESS_SPLIT_FIX_2026-10-02.md), [native access](Evidence/AB_PHASE6_ACCESS_ON_HARDWARE_2026-10-02.md), [served-client correction](Evidence/AB_PHASE6_HMI_HTTPS_DEPLOYMENT_FIX_2026-10-02.md) |
| Value/set permissions | [sets](Evidence/AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.md), [data classes](Evidence/AB_PHASE6_DATA_CLASSES_ON_HARDWARE_2026-10-02.md) |
| Code/data/reserve, linking and shelving | [link-memory fix](Evidence/AB_PHASE6_SHELVING_LINK_MEMORY_FIX_2026-10-03.md), [shelving proof](Evidence/AB_PHASE6_SHELVING_ON_HARDWARE_2026-10-03.md) |
| Coherence/freshness, native frame and live scope | [native S9](Evidence/AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md), [freshness](Evidence/AB_PHASE6_S9_FRESHNESS_2026-10-03.md), [detail-loop correction](Evidence/AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md), [live proof](Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md) |
| Configuration and D6 | [regression fix](Evidence/AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.md), [gateway activation](Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md), [owner dialog acceptance](Evidence/AB_PHASE6_CONFIGURATION_OWNER_ACCEPTANCE_2026-10-04.md) |
| Shared HMI filters/layout | [time filters](Evidence/AB_PHASE6_HMI_TIME_FILTERS_2026-10-03.md), [visible Gantt time](Evidence/AB_PHASE6_HMI_GANTT_VISIBLE_TIME_2026-10-03.md), [inline spacing](Evidence/AB_PHASE6_HMI_INLINE_SPACING_2026-10-04.md), [control presets](Evidence/AB_PHASE6_HMI_INTERACTIVE_SCALE_2026-10-04.md) |
| Retention / current extension | [admin observation](Evidence/AB_PHASE6_OWNER_CREDENTIAL_RETENTION_2026-10-03.md), [air parameter observation](Evidence/AB_PHASE6_OWNER_AIR_PRESSURE_RETENTION_2026-10-04.md), [press69 offline record](Evidence/AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.md) |
| Accepted catalog and prepared weekly Line extension | [press70 native acceptance](Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md), [Line preparation](Evidence/AB_LINE_V2_PREPARED_2026-10-04.md), [ownership regression](Evidence/AB_LINE_V2_OWNERSHIP_CHECK_2026-10-04.md) |
| Line validator memory correction | [press71 failure and press72 preparation](Evidence/AB_LINE_V2_VALIDATE_MEMORY_FIX_2026-10-04.md) |
| Line link budget and shared step-entry service | [press72 link failure and press73 preparation](Evidence/AB_LINE_V2_LINK_MEMORY_FIX_2026-10-04.md) |
| Divided memory estimate, shared alarm services and startup defaults | [press73 failure and press75 preparation](Evidence/AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md) |
| Press75 fit, harness ownership/timing/schema and native Line scope | [completed fit](Evidence/AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md), [159 regression + 17 Line rows](Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md) |
