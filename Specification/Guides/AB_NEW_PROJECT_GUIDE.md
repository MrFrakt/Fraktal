# Fraktal/AB - starting a new station

Updated 2026-10-05 through press75 fit, Line verification, shared HMI detail-read repair and press78 configuration memory reduction. This guide
explains how to apply the binding; [Part III](../Fraktal_AB_Part_III.md) is
normative. Read [AGENTS.md](../../AGENTS.md), the
[AB README](../../FraktalCore/PLC/Allen-Bradley/README.md) and the relevant Core
clauses before editing. One committed declaration is the source; the L5X is
output, never hand-edited. This guide replaces superseded build-by-build advice;
historical evidence remains unchanged.

**The port is not complete apart from power.** Main press operation and Phase
0-6 features are verified on the named press68 deployment. Part traceability,
signal-tower/host integration and other optional profiles or probes remain
absent/unclaimed. Line owner/weekly shifts are loaded in press75;
press72 failed linking at LineValidate and press73 failed with a final global
memory error. The owner confirms press75 completed download at 0/0 and Run;
native/browser/retention acceptance is recorded separately. Press69 added model creation/current export and scoped air Start away from
Changeover, but owner Studio Verify refused nested array subscripts. Corrective
press70 has owner-confirmed completed-download fit and eleven restored native
regression suites (159 rows). M-101 export/live repository read pass; Chrome
acceptance and physical model/download retention remain separate.
See section 7 and the [TC3 handoff](../AllenBradley/AB_TO_TC3_HANDOVER_PROMPT_2026-10-04.md).

| Reference | State |
| --- | --- |
| Bench | 1769-L24ER-QB1B, firmware 33.014, 192.168.100.89, serial 7036B510 |
| Successful loaded / memory baseline | C:/work/press75.L5X; SHA-256 82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5 |
| Coherent native manifest | 94E302F650BA1DB5 / revision 9757442, major 4 / binding 2, 65,552 bytes |
| Online data/logic memory | 758,568 / 786,432 bytes; available 27,864, largest free block 27,376 (owner Studio screenshot) |

These are reference measurements, not acceptance for another controller/cabinet.
Never advance the loaded or memory baseline on generation or Verify alone.
The 2026-10-05 guarded read now sees the Calendar V3 contract
`026DC8F584CA2D70 / 159176`, matching prepared press76. It does not identify
private code or supply a new Studio Capacity/download record. Press75 remains
the last owner-accepted memory measurement. Press77 subsequently failed global
linking with a 799,860-byte offline data/logic estimate (13,428 over capacity).
Press78 is the current prepared correction; the owner reports "its good now"
and requests commit/push, without exact-artifact download or new Capacity data.
See [correction evidence](../AllenBradley/Evidence/AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.md).

## 1. Two questions, asked before anything else

Ask the project owner and record both answers in the station binding record:

1. **Read-only or write-enabled?** The gateway defaults to no write root and
   refuses mutations. Complete inert QUERY_CONFIG batches may use the mailbox
   for read pages without granting mutation authority. Enabling writes arms
   Core section 14: authenticated principals, least privilege, no anonymous write.
   Transport authentication and PLC operator authorization are separate layers.
2. **Which controller baseline?** Prefer firmware v37+ on a CIP Security-capable
   family. Measured v33 L24ER uses the legacy zone-and-conduit posture. Repeat
   S2/S4/S11/S12 on another family/revision; do not assume types, security,
   connection sizes or scan/read budgets transfer.

Controller-changing actions require current explicit authorization and an exact
serial/target check immediately before use. Import/Verify/download are the
owner's licensed-desktop steps. An agent does not start a write-enabled gateway
or infer authorization from a previous deployment.

## 2. What every station gets without asking

The generator derives lifecycle, PLCopen handshake/Execute-drop reset, pending
step diagnosis, controller alarm active/history/reset classes, per-step history,
active cursors/annotations, counts, cycle/command timing, OEE buckets,
ConfigPersist reporting, self-description and the closed command mailbox from
one valid declaration. The runtime base owns common behavior once. MachineState
is derived by projection, not latched in a client.

Events, visited steps and completed-command timing belong on the PLC: polls can
miss transitions shorter than their interval. The generic HMI renders the
contract, without per-station screens. ConfigPersist reporting alone does not
establish physical durability for every value or across an upgrade.

## 3. What a station turns on

Copy `fraktal_ab_station_template.py`. It includes Phase 0-6 basics, station
sets, value classes and an empty user provider. Its two-model catalog is static
(`model_capacity=0`); creation is an additional choice, not already on in every
copied template. Remove absent capabilities instead of publishing placeholders.

| Feature | Declaration / requirement |
| --- | --- |
| CONTINUOUS / SINGLE_STEP / HOLD_TO_RUN | `run_styles=decl.RUN_STYLES`; non-safety step pacing |
| OEE Performance | `decl.ideal_cycle_ms(...)`, `ideal_cycle_member`; measure against actual cycles |
| Degradation watch | `decl.baseline_work_ms(...)`, `baseline_work_member`; registered reason; zero disables per model |
| Derived state flags | `state_flags=(decl.StateFlag(...),)`; at most 12; compute every scan |
| System health | `decl.SystemHealth.for_task(period_ms)` and registered reasons |
| Start / direction permits | `start_permits`, module `permits`; one report and action predicate |
| Manual / Changeover | manual mode + actual command catalogue; models/default + CHANGEOVER chain |
| I/O / forcing | `io_modules`; electrical identity once; safety/control-power coils never forceable |
| ST/SFC/LD | one graph, generated renditions; selector is harness-only |
| Capture / named sets | `decl.capture(...)`, `config_sets=True`; typed capabilities and PARAMETER_SETS reasons |
| PLC users / data classes | `access_users`, `data_classes`, `decl.config_access(...)`; provision before tightening policy |
| Shelving | eligible rationalized events; blocking semantics unchanged |
| Runtime model creation | `model_capacity=N`, seeds and sets; seed count <= N <= 8; press70 owner-created M-101/native bank and duplicate refusal verified |
| Current-value export | sets enabled; native read permission checks; no saved slot |
| Line owner / weekly shifts | optional `fraktal_ab_line.Line(...)`, access provider and sets; press75 fit and 17 native calendar/end rows pass; Chrome/physical retention remain separate |
| Freshness/read budget | `read_budget=decl.ReadBudget(...)`; actual target measurements |

The press task is 10 ms. Require synchronization/fieldbus capabilities only
where commissioned; an unavailable required probe must be explained, not faked.

## 4. The workflow

Run commands from `FraktalCore/PLC/Allen-Bradley/tools` unless stated otherwise.

### 4.1 Declare

```powershell
Copy-Item fraktal_ab_station_template.py fraktal_ab_MyStation.py
$env:FRAKTAL_AB_DECLARATION = 'fraktal_ab_MyStation'
```

Edit this copy, never a generic tool. Name modules as the schematics do; reserve
the project reason band; declare records/capabilities, reusable module types,
I/O identity and complete mode graphs. Defaults match ParCfg. SchemaVersion is
first; persistent/published changes need versioning/migration. Pass the same
selection to gateway and harnesses. Fixed press fixtures refuse other stations;
write a bounded fixture for the actual declaration instead of substituting IPs.

### 4.2 Prove it offline

```powershell
python -B -m unittest discover -s . -p 'test_*.py'
python -B ../../../../tools/check_consistency.py
```

From the repository root also run `python -B -m unittest tools.test_check_consistency`.
Adapt TemplateTests from `test_fraktal_ab_station.py`; catalogue every key
(`check_consistency.py --emit` prints missing stubs). Execute generated ST and
semantic mutants, not only source-presence checks. Use `-B` and fresh bytecode
caches: an old same-size mutant `.pyc` once survived restoration. Run shared
HMI/transport checks when those change. Native compile is a separate gate.

### 4.3 Generate

```powershell
python -B fraktal_ab_generate.py <seed.L5X> <stationNN.L5X>
```

Seed controller/type revision must match. Generation refuses existing outputs;
keep named builds and JSON. Record L5X SHA-256, ContentHash, manifest bytes,
capacities and GeneratedSize; regenerate byte-identically. ContentHash covers
contract and native mailbox/catalog profiles, not every logic/private-storage
change. Equal hashes alone do not identify identical builds. Never patch L5X.

For an upgrade, validated `--initial-config <image.json>` carries configuration,
recipe banks and active ordinal. An expanded runtime catalog also requires
`modelCodes`: an ordered list matching every bank, bounded by declared capacity.
The original seed codes must keep their ordinals; added codes are unique,
printable ASCII of 1-80 characters. Complete typed/schema/range and active-bank
validation happens before output. Omit modelCodes only for legacy seed-only
images. The helper seeds the already-declared catalog; it adds no PLC storage.
Capture twice under exact serial/build guards and require identical values;
recapture immediately before generating a later upgrade. Credentials, sessions
and command latches are excluded and need their own migration procedure. See the
[catalog-image proof](../AllenBradley/Evidence/AB_PHASE6_CATALOG_IMAGE_2026-10-04.md).

### 4.4 Import, download, gateway

The owner imports, runs Verify Controller, completes the download, then restarts
the existing gateway with the same declaration and approved security settings:

```powershell
python -B fraktal_ab_gateway.py <ip> --expect-serial <serial> --port <port>
```

Preserve write-root/origin/authentication; never echo tokens. Do not bypass
hash/capacity mismatch. A gateway needed before download must run from a
worktree at the loaded build's commit. A canceled download proves no new state.

On the reference Windows bench, gateway 127.0.0.1:8099 and Caddy HTTPS/WSS are
separate processes. Starting only the gateway does not start press.localhost.
The owner's hidden sign-in launcher uses the existing config/certificate store:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\work\caddy\Start-WebProxy.ps1
```

HTTPS 401 proves reachability/authentication, not PLC readiness. The plaintext
loopback-upstream warning is expected behind this same-host TLS proxy. Verify
served asset hashes; Ctrl+Shift+R reloads Chrome. See
[reboot recovery](../AllenBradley/Evidence/AB_PHASE6_HTTPS_REBOOT_RECOVERY_2026-10-03.md).

If Configuration disappears, inspect manifest hydration before changing tab
visibility or access rules. Press75 publishes 22 configuration entries (four
model, five station, thirteen Line); the shared client previously rejected
anything over TwinCAT's 16-entry window. Page capacity belongs to the binding:
validate the count against the freshly read discovered rows, require complete
Scope/Item/ValueText and reject duplicate slot aliases. Do not raise a global
constant or allocate a larger PLC buffer to repair this client assumption.
Typed Boolean read text 0/1 is normalized to FALSE/TRUE by the shared manifest
mapper; write validation remains unchanged. This correction is HMI-only;
no PLC download or gateway source change is needed. See
[configuration-page evidence](../AllenBradley/Evidence/AB_PRESS75_HMI_CONFIG_PAGE_CAPACITY_2026-10-05.md).

### 4.5 Verify on the controller, and record it

Read manifest with `fraktal_ab_manifest_read.py <ip> --expect-serial <serial>`,
then healthz/livez/readyz and read-only S3. Compare coherent full readback,
hash/capacities. Authorized write fixtures need exact guards, an explicit arm,
bounded waits, finally restoration, independent final readback and disarm.
Cancel/disconnect never authorizes replay. Prove actions with actual command
counts/end positions: ACKs or step traces can pass while a stroke was skipped.
Wait on stable levels/counters instead of short-lived flags. Preserve failures.
Isolate direct native fixtures from HMI tabs: a separate process is outside the
production gateway's mailbox lock. Each direct command reads the settled
request/ACK cursor afresh, stages arguments, then refuses a changed cursor
before committing. An old ACK is not proof of a new command. Login must settle
with its own LoginResultSequence. Program mode leaves the task stopped and can
cause a login timeout. Start a watchdog stopwatch before its command/setup reads,
and also verify the controller's elapsed timer; those reads consume real time.
Append `.md`/`.json` evidence; never edit an old result to match a new build.

## 5. Rules and feature recipes

Logix v33 contract members are DINT (including 0/1 flags). Do not use unmeasured
BOOL layouts or TRUE/FALSE tag references. ST string literals are replaced by
numeric keys at projection. AOIs cannot reach controller scope. Mode ordinals
are AUTO 0, MANUAL 1, HOME 2, CHANGEOVER 3. Durations respect task period.
Scalable checks use bounded loops/one term per statement within operator limits.
Resolve an indirect array index into existing scalar scratch before indexing:
Studio v33 rejected `Levels[Staged.Ordinal[Index] - 1]` in press69. Keep the
ordinal bounds and data permissions; do not unroll the checks to avoid syntax.
Read structures via dimension-aware `read_layout`, not member-by-name shortcuts
that break when arrays move offsets. Chart steps <=32 and state flags <=12.

Start consumes the release report the HMI explains. Project entry permits may
use `decl.Permit(..., modes=(MODE_AUTO, MODE_HOME))`. Press70 removes air only
from Changeover's Start set; cylinders retain pressure/directional permits.

### Capacity

Fields/Localization reserve follows rows plus eight rows of headroom in eight-row blocks,
with 768 ceilings and a 102,400-byte whole budget. Generation refuses truncation.
Empty reserve costs memory. Press57/65 exhausted Verify memory; press66 passed
Verify but failed link/download. Share routines/scratch instead of unrolled
copies. The press ceiling stays four users; TC3 need not inherit that limit.

On divided-memory controllers, record both areas using Controller Properties →
Capacity → Estimate after importing and verifying the exact offline artifact.
See Rockwell's [offline memory procedure](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/controller-properties/estimate-memory-requirements-offline-for-controlle.html).
The owner reports press73 at 799,428 maximum estimated data/logic bytes against
786,432 total: 12,996 over. I/O uses only 2,640 / 1,048,576; spare I/O capacity
does not resolve this data/logic limit. Press75's completed download passes;
online used/max is 758,568 / 786,432 with 27,864 available and largest free
block 27,376. The estimate and online use have different measurement bases.
Record a new Estimate before the next larger artifact, then require completed
linking and native timing. A source reduction does not predict compiled saving.

From the repository root:

```powershell
python -B FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_generated_size.py C:\work\press75.L5X --baseline C:\work\press70.L5X
```

Press70 adds 2,700 declared bytes, 5,135 ST source bytes, 59 terminators and
54 lines over press68; RLL remains 20. The subscript correction adds zero data
bytes, 50 ST source bytes and five statements/lines over refused press69. These trends exclude compiled code, AOI storage,
metadata/reserve/unsupported layouts. Fit requires Verify **and completed link**;
Press75 reduces declared data by 1,812 bytes, ST source by 30,972 bytes,
terminators by 447 and lines by 413 over press70, preserving all three renditions.
Owner-confirmed completed download establishes press75 as the current baseline.
See [native acceptance](../AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md).

| Table | Static template rows/capacity | Historical press68/70 | Press75 rows/capacity |
| --- | --- | --- | --- |
| Fields | 379/392 | 565/640 | 616/624 |
| Localization | 481/496 | 570/640 | 652/664 |

The current template also sizes other discovery tables from their rows, keeping
one spare rounded to small blocks within each frozen ceiling. Modules/Nameplates
share their capacity. Its manifest is 46,080 bytes (offline-tested); earlier
16/32 and 64-row policies measured 53,112 and 58,232 bytes. Press is 68,472 (press68
and press70 read back); press75 reads 65,552. The template needs its own native fit/live gates.

### Structured Text layout and routine ownership

`fraktal_ab_st_format.py` owns emitted ST layout. The generator applies it at
the serialization boundary to runtime AOIs, program routines and SFC actions/
conditions: four spaces per block, spaced operators/arguments, one instruction
per line, separated CASE arms and advisory 120-column wrapping. Literals,
operands and executable token order are preserved and checked. Fix the source
or this formatter; never edit generated L5X or duplicate formatting rules in
each feature. Frozen Phase 0 fixtures remain historical inputs.

`scan_sections()` owns the ordered scan plan and emits complete services once:
access startup; mailbox frame/handler; restore before the scan increment;
passive/commanded modules; Start; Unit and sequence dispatch; health; diagnostics
and alarms; Line/statistics; then forcing under this scan's permission verdict.
The main routine calls each section once. `ConfigWrite` and `ConfigSets` run
inside the mailbox's existing authorized CASE arms; acknowledgement and secret
wipe stay in the caller. `LineStage` shares calendar copying across individual
writes, complete sets and calendar application, using the existing scratch.

Keep the AOI lifecycle at its owning level. Program services may use controller
scope; AOIs cannot call those services. Extract whole blocks rather than moving
RETURN/RTN/EXIT across boundaries. Share repeated behavior; do not split every
small conditional into a new routine or add scratch solely for organization.
Keep released names/layouts/ordinals and all three sequence renditions intact.
The inline scan/mailbox views are derived from the same plan for test execution;
they are not a second authored implementation.

Press77 preserves every pre-existing executable token after expanding only the
new service calls, plus AOI/RLL/SFC structure and all declared data/initializers.
It adds zero declared data bytes and removes 28 ST terminators relative to
press76. Formatting adds source whitespace; neither source size nor terminator
count measures compiled memory. Additional routine metadata/JSR costs still
need exact-artifact Studio Verify, Capacity Estimate, completed linking and
native scan timing. The SDK attempt reports **No valid license**; the owner's
licensed desktop is the remaining native gate. See the linked cleanup evidence.

The subsequent press77 native download reaches compilation/linking but exceeds
the controller's data/logic area. Press78 preserves the organization while
grouping identical immutable bounds/type/flag facts into multi-label CASE arms.
Configuration snapshot SAVE/EXPORT selects the kind once and copies its fields
once, including the selected inactive model; count is published after the copy.
Commit addresses, access checks, staging, audit, ACK and secret wipe remain at
their existing owners. No tags, types or reserves are added or removed.
The emitted delta is -156 ST terminators and -12,373 ST source bytes versus
press77. Boundary, address-isolation and snapshot tests plus 205 old/new
execution comparisons check behavior. The owner reports resolution, but no
new measured compiled-memory margin. Require that margin before further growth.

Treat source documentation as part of the target budget: Rockwell documents
that embedded ST comments are downloaded into controller memory
([SFC programming manual, page 67](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm006_-en-p.pdf)).
This does not attribute the press77 excess to whitespace or quantify its cost.
Share repeated executable behavior and fact selection; retain useful ownership
comments without repeating every capability label. Record source, statements,
data and native Capacity separately. See [failure](../AllenBradley/Evidence/AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.md)
and [correction](../AllenBradley/Evidence/AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.md).

### Registering controller users

The template has zero accounts, open thresholds and zero timeout. Register up
to four before tightening policy. Use one PowerShell command:

```powershell
& C:\work\venv_gw\Scripts\python.exe -B .\fraktal_ab_access_provision.py station_admin --level 4
```

Hidden prompts create a salted hash registration for the declaration, not a
live PIN write. Replacing a user's PIN row requires controlled deployment; no
online SET_PIN exists. Never put PINs in argv/commits or copy bench accounts.
Plan credential upgrades separately from physical-cycle retention.

PLC session/roles own every permission. Login ACK means consumed, not success;
the HMI waits for the matching outcome/session, not old LoginFailed. Logout
cancels pending work; read/list/export/release polling does not extend timeout.
AB accelerates login using 256 gateway prefix hashes plus final PLC verification,
retaining 257 iterations, role authority and eight SHA rounds per scan. Full
native PIN clients remain supported. Protect/wipe prefixes like PINs. Measure
before considering this platform optimization on TC3. See
[16/16 access proof](../AllenBradley/Evidence/AB_PHASE6_ACCESS_ON_HARDWARE_2026-10-02.md).

### Registering data classes

Use `data_classes=(decl.DataClass('calibration', 'project.dataClass.calibration',
read_level=0, write_level=3),)` and
`decl.config_access(member, 'calibration', min_write_level=3)`. Up to eight stable
class IDs; PLC combines class level with immutable value minimum. Corrupt/unknown
policy requires ADMIN; SET_CLASS_LEVEL needs ACCESS_POLICY. Blank ClassId follows
DATA_READ/DATA_WRITE. QUERY_CONFIG gives metadata but blanks unreadable ValueText.
Loads validate all before commit; exports check all read permissions. SAVE/DELETE
require CONFIG_SET alone, not permission to read fields of an opaque snapshot.
The gateway never grants privilege. See
[18/18 proof](../AllenBradley/Evidence/AB_PHASE6_DATA_CLASSES_ON_HARDWARE_2026-10-02.md).

### Alarm shelving

Resolve SourcePath + Description to exactly one live eligible event, not a
recycled slot. Require permission/rationalization; reject foreign, duplicate,
safety/unshelvable requests. Positive whole seconds <=8 hours; task-time expiry
survives logout/calendar changes. Shelved blocking events still block Start;
slot reuse clears state. Press67 15/15 and later regressions pass. See
[proof](../AllenBradley/Evidence/AB_PHASE6_SHELVING_ON_HARDWARE_2026-10-03.md).

### Write-enabled S9 verification

Press68 V3 native writes pass 17/17, all eleven regressions/restoration and S3
6/6 before/after. Frame arguments fit one connected 500-byte write (89 DINTs,
312 aggregate ASCII bytes), then Sequence last. Use `mailbox.command_writes`,
not decoded scalar/string writes. Large sets retain separate staging. See
[native proof](../AllenBradley/Evidence/AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md).

The press budget is 500 ms polling, 250 ms cache, 1,000 ms slow heartbeat,
2,000 ms Good / 3,000 ms expiry and 4,000-byte reads. Monotonic expiry advances
during stalled RPC; partial ACK/detail cannot renew complete station health.
Commands recheck freshness. Owner restart/browser acceptance and the 60-second
production reader yielded 121 complete updates, no STALE/DOWN, max gap 790 ms.
This qualifies S9 on press68 only, not press70/new targets. See
[live proof](../AllenBradley/Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md).

If cycle charts repeatedly fill then disappear while the link and mailbox ACK
remain healthy, inspect detail-batch ages separately. On press75, reading all
closed-tab history/sequence data plus an extra poll gap let chart batches leave
the Good window. The shared HMI now requests only the selected tab's visible,
access-permitted cards/control bindings and renews bounded sweeps on their slow
cadence. Child command timing belongs to its root scope; parameter-set replies
are explicit reads, never periodic chart work. Per-batch expiry remains enforced.
Tab scoping alone passed a single-reader check but was insufficient with
concurrent readers. The gateway now shares Good native records through an
optional targeted DataValue envelope, preserving source age/quality/timestamps;
the HMI ages them further across the RPC and local processing. Production still
exposed expiry across leaf sweeps. Budgeted tiered transports now promote only
the visible detail to the slow snapshot tier and exclude it again on close.
Native records refresh once for shared viewers, with their original source
quality/age; non-tiered transports retain bounded targeted fallback. Partial
ACKs carry their own quality without renewing station health. Repeat multi-viewer
checks on new targets. The optional snapshot processing bracket prevents
counting native acquisition twice in the client transit allowance; source
ages/limits remain unchanged, malformed brackets fail closed, and older
gateways keep conservative full-RPC aging. Budgeted full polls now resume immediately after a period overrun, with one
acquisition in flight; fast reads still respect the declared minimum period.
Skipping to a later timer boundary had spent the remaining freshness margin. No PLC memory growth/download is needed. Restart the
existing
gateway and hard-refresh Chrome to load both source changes. See
[cycle-detail record](../AllenBradley/Evidence/AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.md).

Measure cold/steady reads, tier promotion and shared viewers per target. Keep
guards, freshness and locks. The concurrent handler permits bounded RPC work
without starving complete reads or parallelizing native writes. D6 writeAccess
and Parameter sets browser acceptance are active. See
[activation](../AllenBradley/Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md).

### Registering a capture

`decl.capture(member, 'Profiler.LastWork')` targets an editable scalar. PLC samples
the owning-root source and ignores the client candidate, applying normal setup,
release/schema/range/value checks. ConfigAudit is shared. See
[capture proof](../AllenBradley/Evidence/AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.md).

### Adding a model to the current AB application

After press70 deployment: Configuration -> Model data -> **New model** clones
an existing model to a unique code. Edit it using Model selection, then activate
via ordinary **Changeover**. A saved Model set offers **Create model from set**.
Creation is inactive; all code/capacity/schema/typed values/read/write permissions
are validated before publishing. Eight slots include three seeds; indices never
move; no delete/automatic activation. Creation may run while BUSY; later editing
keeps normal gates. Use an owner-selected code/source for native acceptance,
never a disposable test model that cannot be removed.

Missing/zero capacity hides creation; the template grows statically by controlled
declaration deployment. TC3 only reserves the kinds and exposes neither new
capability. Physical created-model retention and native download/upgrade
retention are unverified; expanded-catalog image generation/boot tests now pass.
See
[press69 record](../AllenBradley/Evidence/AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.md).

The shared HMI model-page read correction is deployed on the bench. The owner
created M-101; serial-guarded readback confirms its catalog entry and native
schema-4 bank. The corrected HMI queries only discovered response paths and
captures the selected page before cleanup. Hard-refresh Chrome; no PLC download
is needed for that UI repair. Live production repository read returns all four
M-101 fields; Chrome browser acceptance is pending. See the
[read/deployment record](../AllenBradley/Evidence/AB_PHASE6_HMI_MODEL_PAGE_READ_2026-10-04.md).
A later generated image must include the expanded commissioned catalog and all
banks via modelCodes; the tested helper now supports that. Native upgrade and
credential retention still require separate acceptance.

### Registering parameter sets

Enable sets/reasons and typed capabilities. PLC owns values/validation; gateway
owns documents/medium. Station load stages <=64 records and commits all-or-none.
Import stores without applying. Direct Model-set load still refuses in AB/TC3
pending recipe/Changeover integration; inactive creation from a set is distinct.
Exact pre-catalog and pre-Line revisions are recognized when value schemas are unchanged;
unrelated/foreign/schema-invalid payloads refuse. Names are not ModelCodes.

Current values export without a saved-set slot; current/saved exports offer
**Download file** (`.jsonl`, UTF-8) and Copy. All lines use one immutable
connection-scoped snapshot; missing/refused lines abort. Receipt Pending/Failed
correlates to store transactions but does not prove all physical durability.
See [station-set proof](../AllenBradley/Evidence/AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.md).

### Line owner and weekly shifts

Select `application(line=Line('LINE-1', 'PLC-1', utc_offset_min=-300))` when
using the new-station template, importing `Line` from `fraktal_ab_line`. Leave
it absent for a station without a line. The owner sits beside the root, never
in its child tree. This binding currently accepts owners only; no mirror
transport or multi-root sharing is proved by the single-root Press bench.

The current generator uses Calendar V3 with five unused rows and five zero
production targets, so enabling Line does not immediately reset existing
counts. Press75 remains the loaded V2 fit baseline; prepared press76 needs
owner Capacity Estimate, Verify and completed download. Use Configuration → Line data:
UTC offset applies to the whole line; each row has start minutes, duration
minutes and weekday checkboxes. For a weekend-only 12-hour shift, set start
480 (08:00), duration 720 and select Saturday/Sunday (mask 96). Enable the days
last when editing an unused row. A start of -1 or no selected days disables it.
Sunday overnight intervals belong to Sunday even when they end on Monday.

Every proposed edit validates the complete weekly calendar. Overlaps refuse;
adjacent endpoints are allowed. A V3 Line parameter set contains all 21 fields and
loads atomically. Save/export/import use the existing generic set dialog, and
current-value export consumes no saved slot. The minimum Line write level is
ENGINEER, raised further by the controller's effective policy. A weekday
checkbox does not grant a write or bypass Save validation.

For three regular weekday shifts plus two special weekend shifts, configure
rows 1–3 with Monday–Friday selected (mask 31), and rows 4–5 with
Saturday–Sunday selected (mask 96). For example, weekday starts 0/480/960 with
480-minute duration, weekend starts 0/720 with 720-minute duration cover each
day without overlap. Other start times/durations are valid when intervals do
not intersect, including across the Sunday/Monday boundary. Enable days last,
or atomically import a complete Line set. This example is not applied to the
live controller automatically.

Each row also has Production target: a non-negative good-part count, with
0 unset. Targets are reporting goals, separate from recipe stop counts. The
PLC latches the interval's target at its start; an edit is pending until the
calendar boundary. Statistics shows current good/target and percentage, then
the target/attainment captured with each closed shift. No NOK/rework is added
to the numerator; zero and unscheduled targets have no attainment calculation.
Existing manual-reset/clock-quality flags still mark partial/unverified totals.

Prepared file `C:/work/press76.L5X`, SHA-256
`806BB78A1D8B6A932AA826373C0F59F2C2D9848E6F6AA2004A11D2D5EF876C35`,
manifest `026DC8F584CA2D70` / 159176, 68,048 bytes. The explicit commissioning
image bridge preserves the twice-read four-model catalog (including M-101)
and every V2 schedule/current configuration value, adds an unused fifth row
and zero targets. Credentials/session/history are excluded; existing access
initializers remain byte-identical to press75. The source has 2,756 additional
declared data bytes, 9,535 additional ST source bytes and 153 additional
terminators; those are not compiled memory estimates. Record both Studio
Capacity areas before downloading and completed-link/Run evidence afterwards,
then restart the existing gateway and hard-refresh Chrome. See
[offline preparation](../AllenBradley/Evidence/AB_PRESS76_SHIFT_TARGETS_OFFLINE_2026-10-05.md).

Calendar edits wait for the current finite boundary. An empty-calendar edit
applies next scan, preserving accrued unscheduled production unless an active
shift starts. Unscheduled intervals are index 0 and close at the next enabled
start. The controller owns eight newest records, counts, raw OEE inputs,
quality and manual-reset flags; it snapshots before resetting. A manual OEE
reset preserves full production counts but its OEE factors use the matching
reset window. No client accumulates history. Clock quality is marked, never
set by a gateway or inferred from the PC clock.

Loaded file: `C:/work/press75.L5X`, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`.
Manifest `94E302F650BA1DB5` / 9757442, 65,552 bytes, Fields 616/624,
Localization 652/664. It preserves the fresh captured four-model catalog,
all banks/current records and ordinals, including M-101. New Line defaults are
explicitly added; credentials/sessions and runtime history are not captured.
Trends over accepted press70: data -1,812 bytes, ST -30,972 source bytes,
-447 terminators and -413 lines; RLL is unchanged. These do not prove compiled fit.
Press72 verified/compiled but failed during download linking. Press73 frees
4,968 declared data bytes through proportional discovery reserves and removes
452 ST terminators through shared step-entry bookkeeping at the same execution
point. AOIs, released UDTs, other tag initializers, tasks and LD remain identical
to press72. PLC chart visits/history/timing, all renditions, four users and all
permissions remain. The six-pair validator is unchanged: 2,020 calendars match
an independent interval oracle. Press73 also fails with a final global memory
error. Press75 shares native alarm allocation/close services using existing
scratch, groups equal rationalized priorities and emits startup defaults once.
It removes 19,863 source bytes, 240 terminators and 245 lines from press73;
all layouts/tags/AOIs/tasks/other routines compare equal. Read the
[earlier allocation correction](../AllenBradley/Evidence/AB_LINE_V2_LINK_MEMORY_FIX_2026-10-04.md)
and [current correction](../AllenBradley/Evidence/AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md).

The owner confirms exact press75 completed download at 0/0 and Run. Online
data/logic uses 758,568 / 786,432 bytes, leaving 27,864 available (3.54%) and
a largest free block of 27,376. This differs from press73's offline estimate;
do not claim the subtraction as measured compiled saving. Fresh native reads
confirm the complete manifest/capacities and all four captured model banks.
See [fit evidence](../AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md).
The shared Web HMI is deployed and HTTPS assets verified. Native Line behavior,
Chrome controls and physical retention have separate acceptance records.
Press75 now supplies 159 successful restored regression rows across eleven
suites and 17 native Line rows. The Line vector verifies complete 13-field
export/import, permission/range/overlap/partial-set refusal, a twelve-hour
weekend-only interval and its natural end. The original calendar is declared
pending during the active shift, then applies at that boundary; history is
closed before the profile resets counters. Two actual closure rows remain,
never erased for fixture cleanup. Final config/all four banks are restored,
S3 passes 6/6 (max 8,384 us; no faults/overlap) and all health routes are ready.
This is one weekend/end vector, not a hardware sweep of every weekday/history
overflow. Chrome controls and physical Line retention remain owner gates. See
[native acceptance](../AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md).

## 6. What a healthy station looks like on this baseline

One LOW CONTROLLER_METRICS_UNAVAILABLE event is expected: no CPU/free-memory
GSV source. It occupies a slot but does not block Start; find faults via FaultEvt,
not Active[1]. Required unavailable probes make SystemHealth unhealthy by contract.
Fieldbus/DC/fan/storage figures remain unavailable. Time-unsynchronized status
authorizes neither a clock write nor weakened freshness. State is derived.

## 7. Remaining gaps and deployment boundaries

| Capability | Current state |
| --- | --- |
| Operating modes, holds, ST/SFC/LD, alarms/reports, timing/OEE/state | feature gates and press68 regressions pass |
| Capture, station sets, users, classes, shelving, qualified S9 | named press68 verified; new targets rerun gates |
| Model creation/current export/Changeover air scope | press70 completed-download fit; owner-created M-101 native bank/export/duplicate refusal and mode-scoped air reports pass; Chrome/physical retention remain separate |
| Direct running-model set load | refused in AB/TC3; needs provider/atomic Changeover integration |
| Part traceability (Core 3.16) | absent in AB; TC3 press injects a local carrier |
| Line data/shifts (Core 3.8e, 8.5.2) | press75 fit and 17 native calendar/weekend-end rows pass; Chrome/physical retention remain separate; mirror/shared-root composition remains unbound |
| SignalTower/LAMP_TEST and HostEvents | absent/no bench hardware or host projection |
| Control-power/safety profiles | power deliberately excluded; process/two-hand logic is not certified-safety conformance |
| Nameplate/IDTA, I/O connection state in health | absent/unclaimed; schema and S3 probe work remain |
| MANUAL_HELD / Integrated Motion | no manual-held route; L24ER has no motion/S14 proof |
| Retention | owner confirms one admin and one air-threshold edit across cycles; full values/accounts/sets/models, durability and upgrade matrix remain unverified |
| S1 clock probe, other targets and packaged AB installer | separate acceptance; not implied by press68 S9 |

The owner requested completion beyond the earlier Phase 6 boundary. Follow the
[staged completion plan](../AllenBradley/AB_PORT_COMPLETION_PLAN_2026-10-04.md),
continuing with Chrome/physical Line checks after
[press75 native acceptance](../AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md), preserving
[press70 native acceptance](../AllenBradley/Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md).

The [parity audit](../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md) preserves history.
No earlier PASS is broadened by this guide. The
[TC3 prompt](../AllenBradley/AB_TO_TC3_HANDOVER_PROMPT_2026-10-04.md) separates
needed binding work from improvements already shared by the HMI.

## 8. When something looks wrong

| Symptom | First check / lesson |
| --- | --- |
| Hash/capacity mismatch | loaded build/declaration; never bypass discovery |
| Mode/Start refused after download | gateway restart and declaration selection |
| HTTPS fails after reboot | proxy startup/certificates separately; 401 is not readiness |
| Login fault then eventual success | request/result/session correlation, pending state, served asset hashes |
| Parameter sets reloads home | complete snapshots starved by RPC/detail work; retain locks and multiplex bounded requests |
| Model selector vanishes | static replacement not hydrated; retain published metadata until complete |
| Reconnect loop/stale UI | partial detail never renews whole health; independent monotonic expiry |
| Filters followed by a return to overview, possibly with a brief Connecting screen | distinguish sample expiry from a browser refresh. Root-path retention alone covers recovery between frames; a painted connection gate remounts the detail. Retain tab ID and per-view time/severity choices in HMI-only state, never samples or permissions. Disable chip drawer-width animation and isolate card/control repainting; stress actual filters, not only an idle view. See [filter recovery](../AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.md). |
| Steps visited but no stroke | stale Done/missing Execute-low scan; count commands/end positions |
| Healthy fixture timeout | fleeting flag or read cost; bracket acquisition, wait on counters |
| Out of memory | code/data/reserve; Verify and successful linking, not source size alone |
| One value survives cycle | evidence for that value only, not all persistence/upgrades |
| Gantt filter leaves blank time | shared HMI concatenates visible durations linearly; retain full-cycle header/original tooltip starts |
| Raw key / inconsistent control size | catalogue/shared tokens, not per-screen overrides |

## 9. Licensing a station built from Fraktal

Current distribution is AGPL-3.0-only; older MIT grants remain. Read
[LICENSING.md](../../LICENSING.md) before distributing derived PLC/HMI/gateway
work. Preserve notices and provide exact Corresponding Source as required;
modified network programs need section 13's source offer. Ordinary parameter
exports are not automatically relicensed. Assess proprietary station code and
vendor dependencies under actual combined-work/System-Libraries rules; no blanket
linking exception is granted. License changes do not replace engineering gates.
