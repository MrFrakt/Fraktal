# Fraktal HMI Contract — what a generic client binds (Core §3.10(a′), §3.13)

*The HMI never binds properties or calls methods: everything it renders is **data** in the exposed namespace, published by the framework bases. A station adds zero HMI code (O1); the same structures serve any future binding (O8).*

All displayed strings follow `LOCALIZATION_AND_MODULE_CONTENT.md`: PLC display fields carry stable `std.*`/`project.*` keys, never operator prose. Standard and project catalogs, first-run language selection, CSV administration, module PDF content, and per-section view policy are part of this contract.

In the TwinCAT binding, externally written request/configuration data is `VAR_INPUT` and published result/status data is `VAR_OUTPUT`; implementation `VAR` is private. This IEC access classification is a transport mapping, not authorization: every write listed below is still release-gated and re-checked by the PLC.

## Discovery
Walk the exposed instance tree (§3.10). **A node is a module iff it has a `Status : ST_ModuleStatus` member.** `Status.Name` = tile caption, `Status.ModuleType` = tile kind (Unit / EM / CM), `Status.TileEnable` = render on the parent's child view. Children = nested members that are themselves modules — the parent→child drill path is the namespace itself (§4.8).

## Per-tile bindings (every module)
| UI element | Symbol |
|---|---|
| Caption / kind | instance `Status.Name` identity plus optional `DisplayNameKey`, `Status.ModuleType` |
| State LED | `Status.State` (READY/BUSY/DONE/ERROR/ABORTED) |
| Message line | `Status.Diagnostic.Description` (+ `SourcePath`, `IoTag`, `IoAddress`, `Since`, `TimeSynchronized`) — the §6.9 first-out; `IoTag` is rendered verbatim/monospace and never localized; an unsynchronized stamp is visibly marked untrusted; on a Unit this shows the live stall (`Pending`) whenever no fault is active |
| PLCopen strip | `Busy`, `Done`, `Error`, `Aborted`, `ErrorID` |
| Command timing table (detail) | `Timing.Rows[i]` = {Id, Label, Count, Last, Minimum, Maximum, Avg}, `Timing.LastCmdTime`, `Timing.Truncated` (§8.11.4(a)) |

## Tabbed module detail and administrator customization

Every module detail starts with **Overview** and **Description** tabs. Overview owns
the live operational, diagnostic, configuration, and history facets; Description owns
the localized module information and uploaded documents. The tab strip is omitted when
only one tab is visible. Each tab has an HMI-local minimum `AccessLevel`; only an
authenticated `ADMIN` may change that threshold, title, order, trigger, or content.
Like section policy, tab visibility is defense in depth rather than OPC UA read
authorization.

Typed/category capabilities add reusable detail tabs without station screens:

- a motion facet adds position/target/velocity/error and axis-state presentation;
- `FB_TcpVisionCM`-shaped data adds judgement, result, trigger, and optional-image
  presentation;
- `FB_TcpCodeReaderCM`-shaped data adds decoded value, no-read/match state, link state,
  statistics when published, and a catalog-routed trigger;
- RFID-shaped data adds current UID, tag-present/read-quality, link state, and a
  catalog-routed read action.

These are standard category renderers, not vendor or station pages. Missing optional
values render as unavailable; they are never synthesized. High-performance defaults
use neutral surfaces and reserve strong colour for abnormal/judgement state.

In `ADMIN` edit mode, a custom or guidance tab may contain localized text, scalar value
outputs, Boolean LED indicators, bounded local trend charts, PLC-validated action
buttons, configuration text inputs, and embedded images. The control editor presents
an autocomplete/search selector populated only from scalar OPC UA values owned by the
selected canonical module; it never accepts an invented free-text browse path. Values
below child module nodes belong to that child. `OPC.UA.DA := '0'` therefore removes a
value from custom binding just as it removes it from every OPC UA client. Value, LED,
and configuration-input controls link one compatible value; a chart links up to eight
numeric values and renders them as distinct series. Chart periods are clamped to
250–60000 ms and histories to 20–600 points; these are volatile display samples, not
a historian or a control-time source. A temporarily unavailable imported link is
shown as unavailable and retained for reconnect/change-resistant import rather than
silently discarded.

Each selected scalar retains its OPC UA `DataValue` status, source/server timestamp,
and runtime type. Only Good-severity values are usable. Bad or Uncertain values are
shown with an explicit quality/status indication; LEDs do not imply an ON/OFF state,
charts do not append a sample, and configuration inputs are disabled until Good data
returns. The flat snapshot value map remains a Good-only compatibility surface.

Controls have portable responsive width presets (quarter, third, half, two-thirds,
full). Narrow displays collapse them to safe full/half-width rows; wide displays use
a wrapping grid. Edit mode supports drag reordering plus keyboard-accessible move
actions. Layouts remain flow-based and responsive rather than persisting fragile
pixel coordinates.

An administrator may select a whitelisted portable icon preset for each custom or
guidance tab. The Overview tab may also carry an embedded background image with
contain/cover/fit-width/fit-height aspect-ratio presets, nine-point alignment, and
independent bounded margins. The image remains presentation-only behind the live
Overview controls; it cannot replace the PLC-owned status contract.

Layout editing cannot create an arbitrary write path. Buttons map only to the existing
manual-command catalog, Unit start/stop/reset, or `DecisionAnswer`; inputs use the
existing acknowledged configuration mailbox. The PLC remains authoritative for
publication, type/range validation, access, releases, interlocks, audit, and acceptance.
Rejected actions follow act-or-explain and no write is queued across reconnect.
Manual-command and decision buttons store only a value selected from the current PLC
catalog and execute against their current canonical module/root; an older imported
free-form target path is ignored. State-changing buttons may require an operator
confirmation and disable while one acknowledged request is in flight. A missing
catalog entry disables the button rather than guessing or sending an obsolete value.

### Configuration write capabilities

The editor is derived only from writable §3.10.2 manifest entries. Each field carries
`Scope`, display/browse `Item`, stable `WriteKey`, non-zero `WriteRevision`, `ConfigKind`,
`ValueType`, optional bounds/exact enum domain, unit/label, and `RequiresReady`. The HMI
shows Apply only when that complete capability is valid, belongs to the current canonical
module, the required root state is satisfied, and the current session permits
`DATA_WRITE`. Missing metadata, duplicate `(Scope, WriteKey)` entries, older manifests,
and arbitrary scalar tags are read-only. A custom configuration-input binding must match
the capability's `Item`; it may not manufacture a field from the final browse segment.

The repository re-resolves the current capability immediately before sending
`WRITE_CONFIG`: `TargetPath=Scope`, `NameValue=WriteKey`, `IntValue=WriteRevision`,
`TextValue=candidate`, then `Sequence` last. Client type/range checks provide immediate
feedback only; the PLC repeats them and remains authoritative. A stale revision or
reconnect never falls back to a browse write and is never queued for replay.

## Sequence-triggered Unit guidance

A Unit may have one or more **guidance** tabs. A guidance tab can match an exact
`CurrentStep.StepNo`, an exact `CurrentStep.StepName`, or `*`; the wildcard opens only
for `WAIT_OPERATOR` steps. On entry to a newly matched step the HMI opens a full-screen
operator guide containing the live step/awaited conditions, any `Decision` prompt, and
the administrator-authored controls. Dismissing it does not complete or acknowledge
the sequence. Completion still comes only from published PLC conditions or the typed
`DecisionAnswer`; the same step is not reopened repeatedly until the step identity
changes. This supports changeover/cleaning/tooling instructions without a
press-specific HMI page or PLC-authored prose.

## Portable HMI customization bundle

An `ADMIN` can export/import one versioned UTF-8 JSON customization bundle. It includes
all persistent administrator-owned presentation state: module tabs and controls,
per-tab and per-section access policy, tab icon choices, guidance triggers, embedded
control and Overview background images with layout settings, module PDF
documents/metadata, OPC UA control bindings, and both standard/project localization
overrides for every language. Import validates the complete bundle and explicitly
confirms a merge:
imported IDs/keys update matching items while target-only customization is preserved.
It reconciles module identities conservatively: exact paths first, then a mapped
parent plus unchanged local name, then a unique longest dotted-path suffix. A uniquely
remapped descendant may establish a root-rename hint. Ambiguous or absent modules do
not fail the import and are not discarded; their profiles remain stored under the
original path as **deferred**, and the administrator receives an exact/remapped/deferred
report. Malformed schemas or payloads still fail closed.

Administrator edits are drafts: add/edit/delete/reorder operations update only an
in-memory working copy with undo/redo. Operators continue to see the last published
layout until `Publish` succeeds. Publishing records the previous layout, UTC time,
administrator identity, and optional change note. At most 20 revisions per module are
retained; restoring a revision first records the layout being replaced. Revision
history is part of customization schema 4 and follows the same deterministic module
path reconciliation during import.
Connection endpoint/transport, proven-connection state, selected Unit scope,
credentials/session state, and language selection are connection/bootstrap settings
and are deliberately excluded. The shipped native and Web stores remain device-local;
the bundle is the portable commissioning/backup path. Native storage replaces files
through a flushed temporary generation and retains a last-known-good backup; Web uses
IndexedDB and migrates the older local-storage record when encountered.

## Unit detail view (additional)
| UI element | Symbol |
|---|---|
| Current step | `CurrentStep` (StepNo, StepName, AwaitingLabel, TimeClass, ExpectedTime, Conds[] with per-condition Label/Ok — §6.5/§6.9(b)) |
| Model catalog | optional `AvailableModelCount` + `AvailableModels[]/ModelCode`; render a selector when present, otherwise validated free text (§3.8) |
| Live stall reason | `Pending` (Low; distinct from a fault) |
| Cycle waterfall | `Profiler.LastCycle` — ordered `Steps[]` {StepNo, StepName, **TimeClass** (color), Started, Duration}; header: `Total`, **`WorkTime` (real cycle time)**, `WaitTime`, `ByClass[0..4]` (§8.11.4(b)/(f)) |
| Step Pareto | `Profiler.StepStats[]` (Avg/Max per StepNo, class-tagged), `Profiler.Current` for the live bar |
| Counters | `GoodCount`, `NokCount`, `Starved`, `Blocked` (§8.11) |
| Fault history | `History[1..MAX_DIAG_RING]`, newest at `HistoryHead` (§6.9(a) ring — shift post-mortem) |
| Operator decision | read `Decision` (Prompt/Options/Default/Timeout); **write** `DecisionAnswer` (1-based option; 0 = none) (§6.11) |
| Alarm/event list | sparse `AlarmLog.Active[1..MAX_ALARM_ACTIVE]` slots whose State is ACTIVE/WAIT_RESET (Severity, Reason, Source, optional exact `IoTag`/`IoAddress`, ComeAt + time-quality flag, ResetClass) — WAIT_RESET rows render as "cleared, awaiting reset" (§8.3(b)) |
| Event history | `AlarmLog.Ring[]`, newest at `AlarmLog.RingHead` — each closed event with optional exact `IoTag`/`IoAddress`, **`Duration`**, ComeAt/GoneAt/ResetAt and their time-quality flags (§8.3(a)/(d)); unsynchronized records are marked untrusted, never discarded; full history via an `I_EventSink` historian adapter (deferred by design) |
| Blocked banner | `AlarmLog.Blocking` — Unit will refuse `Start` until **OperatorReset** (write, release-gated §7.6/§14) |

## Safety and control-power facets (§9.8)

Any module may publish `Safety : ST_SafetyStatus` and `ControlPower : ST_ControlPowerStatus`; `Present=FALSE` hides the card. A root Unit additionally publishes read-only `Domain : ST_ControlDomainStatus` and `Status.ControlDomainId` (`''` = no arrangement). Its application-fed `ControlDomain` input is excluded from OPC UA; clients bind only `Domain`. One domain may serve several root Units; mirrored cards with the same ID are one shared domain, not independent power controls. Safety rows are read-only and include device kind/state, demand, safe-state feedback, reset-required, fault, muting, keyed bridge, fieldbus health, and affected power groups. Muting/bridge are conspicuous and never rendered as normal bypass controls. Control power shows domain Control On/Off state, affected member Units, and each named power group's request, feedback, safety permit, fieldbus health, reaction, and rearm requirement. `Start` is unavailable when an assigned domain is not `ReadyForStart`; an unassigned Unit adds no gate. The ordinary HMI never writes safety reset, bridge, muting, or guard unlock.

Control On/Off is data-driven through the selected root Unit's `HmiRequest` mailbox (`CONTROL_ON` / `CONTROL_OFF`). The base acknowledges only after applying the `POWER_CONTROL` access gate, then emits one-scan `ControlOnRequest` / `ControlOffRequest` outputs. A one-Unit application may consume those pulses locally; a shared-domain application shall route every member request to the single domain coordinator. Reconnection never replays either request.

## System health, clock quality, and signal tower (§2.7/§8.12/§8.13)

A Unit with `SystemHealth.Present=TRUE` renders the bounded live health card from
task cycle/jitter/overrun, explicit controller/IPC/fieldbus/DC availability and
values, and `SystemHealth.TimeQuality`. Unavailable is distinct from zero and a
clock that is unavailable, unsynchronized, or outside the configured tolerance is
conspicuous. `SignalTower` renders the semantic Red/Amber/Green/Blue/White/Horn and
`TestActive` state beside it; no HMI code knows electrical output addresses.

Lamp test writes only append-only mailbox request `LAMP_TEST := 26`. The control is
shown through the existing act-or-explain path, requires the Unit's `MANUAL` access
gate and an idle Unit, waits for acknowledgement, and is disabled while
`TestActive`. The PLC owns the bounded timeout, so disconnect never leaves the test
latched. Health/tower fields are generic Unit facets and shall not create a
station-specific page.

## Connector sub-tile
`Status` as any module; link detail: LastSeen/Reaction are on the connector's mirror/diag (`Status.Diagnostic` = link first-out when unlinked).

## Fieldbus and I/O identity

The physical topology binds `Topology : ST_FieldbusTopology`: `NodeCount`, `Nodes[] : ST_BusNode`, `MappingValid`, and `MappingDiagnostic`. An invalid mapping is a commissioning fault and shall be displayed rather than treated as an empty/healthy bus. Discovery reads `NodeCount` and each active node's `ChannelCount` before traversing the bounded arrays; unused fixed-array elements are not part of an HMI snapshot. For every `ST_IoChannel`, the client maps `Name`, `DescriptionKey`, `Address`, `Path`, `ModulePath`, `Dir`, `Kind`, values, `Unit`, `Forced`, `Quality`, `FaultActive`, `Diagnostic`, and `Forceable`. `Name` is the exact approved electrical/I/O-list tag and is shown verbatim in monospace; `DescriptionKey` and `Diagnostic` are localized by the project catalog. `Address` shows the terminal/channel locator. `Path` remains the unique forcing/audit identity, while `ModulePath` opens the owning module and defines the HMI assignment boundary. `Forceable` is an explicit PLC capability and defaults false when absent; output direction by itself never creates a force control. A snapshot marked `truncated=true` is rejected before mapping and shall never produce a `LIVE` repository or an empty-but-healthy fieldbus view.

When `FaultActive` is true the channel and its diagnostic are highlighted. A module alarm simultaneously shows `ST_Diagnostic.IoTag`/`IoAddress`, so a cylinder timeout can read, for example, “press did not reach DOWN” plus `_101B202A · EL1809 Ch5`; the same exact tag is highlighted in the fieldbus tree. Transport adapters shall copy these fields without normalizing case, stripping the leading mapping marker, translating, or substituting a friendly label.

## Tree & theming (client behaviour)
**Tree highlighting (§3.13):** per node, effective severity = max(own active events, children's) with HIGH > MED > LOW; tint every ancestor down to the source, strongest at the source. Derived purely from `Status`/`AlarmLog` — no extra PLC symbols. **Themes:** Material 3, selectable (light/dark/high-contrast); theme *changing* is an HMI-local setting gated by a configurable minimum `Access.CurrentLevel` (default `NONE` = open) — it is client config, not a PLC gated action. **Transports:** desktop/mobile bind OPC UA directly (FFI client); **Web requires a WebSocket/REST gateway** (browsers cannot open raw TCP) — the client is written against an abstract repository so Sim/OPC UA/gateway swap without UI changes.

## Connection bootstrap (fail-closed)

Connection ownership precedes the operator shell. On first use—or whenever settings exist but have never produced a `LIVE` repository state—the HMI **shall open a connection wizard**. Step 1 configures and proves the endpoint. After `LIVE` discovery, step 2 lists root Unit browse paths and requires at least one Unit assignment for this HMI. The selected paths are saved locally and form both a display filter and a repository write boundary, including fieldbus branches through their channel-to-module paths; global connection status remains visible. `EverConnected` becomes true only after the repository is live and Unit assignment is complete; saving an endpoint alone is not proof.

When settings have previously connected, startup goes directly to a full-screen **Connecting to PLC** view. The interactive HMI is not built while the repository is `CONNECTING`, `STALE`, or `DOWN`. A transition away from `LIVE` removes operator interaction immediately; commands are never queued or replayed across reconnection. After 30 seconds without `LIVE`, and not before, the view exposes **Edit connection settings**. A successful `LIVE` transition cancels that timer and opens the shell only if every saved Unit path is rediscovered; missing/renamed assignments return to step 2 fail-closed. An authenticated `ADMIN` may edit the Unit assignment later from the shell. Native settings use a local JSON file; Web uses browser local storage. Both are HMI-local connection configuration, not PLC recipe/station data.

## Access levels (§7.7) — how the Flutter client behaves
Per root Unit: read `Access.CurrentLevel` / `Access.CurrentUser` / `Access.LoginFailed`, `Access.Policy.Required[0..10]` (index = `E_GatedAction`, including append-only `ALARM_SHELVE` at 9 and `POWER_CONTROL` at 10), and `Access.Policy.SessionTimeout`. A blocked control remains pressable only to open its release explanation; it never issues the mutation. Login is **data-driven** through the root mailbox; the PLC clears the transported secret after each attempt. Idle auto-logout (`T#0S` = never) is rearmed by successful login and accepted authenticated operator mutations, never by snapshot/manifest/release polling. A mailbox `Accepted` acknowledgement means the login request was consumed, **not** that credentials were accepted; login succeeds only when the resulting access snapshot has `LoginFailed = FALSE`, `CurrentUser` equal to the requested user, and `CurrentLevel > NONE`. On failure the dialog stays open, clears the secret field, and shows a localized generic user/PIN error (never reveals which credential was wrong). **Shipped default policy is fully open** (all thresholds `NONE`) — a station may require no login at all. The settings view edits the selected root's persistent policy through append-only mailbox kinds `SET_ACCESS_LEVEL=24` and `SET_SESSION_TIMEOUT=25`, serially; both are PLC-rechecked against `ACCESS_POLICY`, and the PLC rejects raising that threshold above the active session level to prevent retained self-lockout. The PLC re-checks all mutations, including decisions, power, shelving, force, and configuration writes. Accepted privileged mutations and denied attempts land in the §8.3 ring without secrets.

## Alarm shelving & rationalization (§8.9/§8.10)
Units publish the generated rationalization catalog (`Meta`: per-ReasonCode priority, category, operator action, consequence, and shelvable flag) which the HMI joins onto events by `reasonCode` — the alarm row shows *what to do*. The HMI carries the same generated catalog as a deterministic fallback for a partial/older manifest, while the PLC remains authoritative for alarm behavior. A record with no operator action is an event and is not rendered as an actionable alarm. Active alarms carry `Shelved`; a shelved alarm is **de-emphasized (never hidden) in lists and excluded from the banner** — annunciation only: **Blocking, interlocks, and release reports are untouched**. Shelve/unshelve via `shelveAlarm`/`unshelveAlarm` (ALARM_SHELVE-gated §7.7, act-or-explain §7.8, PLC re-checks: SAFETY never shelvable, unrationalized reasons refuse). Shelves auto-expire in the PLC (time-bounded); every shelve/unshelve/expiry is a §8.3 event.

## OEE (§8.5.1)
Units publish `Oee` (run/down/idle ms buckets + Availability/Performance/Quality/OEE, each with a validity flag) and `OeeTrend` (bounded sample ring). The HMI renders an OEE facet: factors + OEE% with **exception-based colouring** (muted at/above target, amber/red below) and a **sparkline** from the ring. **Invalid factors render as '—' and are omitted from the product — never assumed 100%** (O7). `resetOee` is DATA_WRITE-gated (§7.7), audited (§8.3), and follows act-or-explain (§7.8). Long-horizon trending is the historian's job, not the ring's.

## Digital nameplate (§3.10.1)
A module with a non-empty `Nameplate` (`ST_Nameplate`: product URI, manufacturer, designation, serial, year, HW/FW/SW versions, order code, documentation URL) renders a **nameplate facet card** on its detail view — identity, versions, and a tappable documentation link. Read-only by contract: identity, not configuration (outside §3.8/§7.7 entirely). Empty nameplate = no card. Root Units always publish one; any module may (a purchased CM keeps its own identity). Projection to AAS/IEC 63278 (IDTA 02006 Digital Nameplate et al.) is Annex K.

## Release panel (§7.8) — "why is this blocked?"
Pressing a blocked control (Start, or a manual command) never silently no-ops: it opens a **persistent bottom panel immediately** in a localized “checking release conditions” state, then calls the pure query `releaseReportStart(unitPath)` or `releaseReportManual(unitPath,targetPath,value)` and renders the FULL rollup — every unmet precondition at once (mode, access, active alarm, and each failed interlock), each with its localized description, kind icon, numeric reason, and qualified owning `SourcePath`. The manual query includes the selected command value because directional interlocks may differ. The panel stays while blocked and can be dismissed; while open it refreshes at a controlled, non-overlapping interval, and when the action releases it shows a brief 'now released'. A repository snapshot emitted by a query acknowledgement **shall not itself trigger another query** (that feedback loop can flood the PLC mailbox). The query computes the same predicate the gate uses (no drift). Interlock reasons reuse the §7.2 PermIntlk descriptions. **Every** gated control follows act-or-explain — Start/Stop/step/reset/changeover/manual open the release panel when blocked; channel force (fieldbus-scoped) explains inline. No gated control is ever a silent dead button. If a rejected action yields no reasons, the panel explicitly reports the contract/publication defect rather than rendering an empty area.

## Mode bar (§3.4.1/§3.4.2)
Right-side vertical bar controlling the selected module's owning Unit: **mode selector** (current-mode icon on top, menu of `supportedModes`), **play/stop** at the bottom (play = `start`; while running it becomes a red stop = graceful `stop`, finishing the sequence — reads `running`), and an optional **step toggle** cycling CONTINUOUS→SINGLE_STEP→HOLD_TO_RUN for modes whose `supportedRunStyles` allow it (`setRunStyle`; SINGLE_STEP shows a step button → `stepRequest`; HOLD_TO_RUN shows a press-and-hold → `setHoldRun`). **MANUAL shows no play/stop/step** (no sequence). The stop button **blinks** while `stopPending` (stop requested, sequence still finishing) and is non-interactive during that window. Per-step `steppable` (default true) means some steps run through even in step mode (published on `CurrentStep`). Mode changes honour the per-mode `modePolicy` (§3.4.1): `blockedWhileRunning` refuses with a hint, `confirm` prompts (graceful "finish & switch" vs immediate "interrupt & switch"), `interruptible` proceeds. **Hold-to-run is NON-SAFETY** (§3.4.2/§9) — never a dead-man. All gated by MODE_CHANGE/START_STOP (§7.7).

## Show-why-blocked (§7.6.0)
## Manual commands (§7.6.1)
Each CM/EM publishes a **command catalog** (`{value,label}` list); the HMI renders a button per entry — no per-type code. A command is issued via `manualCommand(unitPath, targetPath, value)` and accepted **only** when the owning Unit is in `MANUAL` mode (§3.4) **and** the user holds `MANUAL` access (§7.7); it routes *through* the module (interlocks/first-out/timing still apply — the opposite of a fieldbus force). Every accept/reject is a §8.3 event. The panel is visually distinct from the fieldbus force (bordered 'Manual commands' card on the module) so the two risk levels are never confused. Single path only — no mode-bypass override.

## Write surface (deliberately narrow, §14)
Writes are limited to module `Command` + `Execute`/`Abort`, `DecisionAnswer`, Unit mode/run-style/start/stop/step/hold, release-gated manual commands and bounded lamp test, alarm reset/shelving, model/configuration changes, and explicitly authorized channel force. Every path is gated and re-checked by the PLC; commands are never queued across connection loss.

For a guided model change, the HMI writes `CHANGEOVER` mode, submits the selected model through the
transactional model request, then starts the Unit sequence. The live `CurrentStep` and `Decision`
records drive the instructions and confirmation buttons; no press- or station-specific page is used.

OPC UA clients shall issue those operations through the root Unit's generic
`HmiRequest : ST_HmiRequest` / `HmiResponse : ST_HmiResponse` mailbox; they do
not call IEC methods. Arguments are written first and `Sequence` last. The Unit
samples a new sequence once, routes it through the same methods and release
gates used internally, clears transported secrets, and writes `AckSequence`
only after processing. See `OPCUA_TRANSPORT.md`.

The repository shall serialize each mailbox transaction, shall not allow a
periodic refresh to starve its writes, and shall wait for any already-running
refresh before evaluating acknowledgement data. Control success means the exact
`Sequence` was acknowledged and `Accepted=TRUE`; rejection and timeout are
different results, and the PLC's localizable `Diagnostic` is logged/displayed
for a rejection. Static browse discovery should be cached for the session;
cyclic updates use subscriptions or bounded batch reads rather than recursively
re-browsing the complete server namespace every refresh interval.

The Web gateway exposes the same tier capability as direct clients through
versioned path discovery, compact tier indices, and bounded targeted reads. The
gateway intersects every connected browser's slow/on-demand sets before changing
its one shared PLC session, so one client can never reduce another client's live
surface. Optional deployment `read-root` subtrees filter snapshots, discovery,
tier setup, and targeted reads consistently; PLC/OPC-UA authorization remains the
primary confidentiality boundary when no additional gateway read scope is set.

Discovery shall canonicalize module identity before rendering. `Status.Name` is
the qualified dotted identity (`Root.Child`); a real module's final OPC UA
browse-name segment equals the final segment of that identity. Candidates are
deduplicated by the complete `Status.Name`, parentage comes from its dotted
prefix, and the shallowest matching OPC UA path is canonical. A `REFERENCE TO`
or owner alias whose local browse name differs from the final identity segment
is not a module instance. Duplicate root identities are a contract/deployment
diagnostic and shall never be passed unchanged into station selectors.

## Known deferred (tracked)
§8.3(d) `I_EventSink` historian implementations (OPC UA A&C / SQL / MES
adapters — interface is normative and shipped; adapters are deployment work) and
external §11.6 `I_HostEventSink` deliveries. The fixed bounded `HostEvents` OPC UA
projection, HMI hydration, and §8.8/§8.9 generated catalog are shipped and
freshness-checked; historian/MES/REST/MQTT delivery adapters remain deployment
profiles. Core §8.10's optional Alarm-performance profile (long-window
rate/standing/stale/chatter/flood analytics) is likewise owned once by the chosen
station/line aggregator or historian, not duplicated in every root HMI. Unknown external/application reasons still fall back to the PLC
diagnostic description and require a complete runtime rationalization before
they may be shelved.
