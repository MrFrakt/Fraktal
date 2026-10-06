# Fraktal/AB — Phase 6 handover prompt

Copy the fenced text below into a fresh coding-agent chat. Open the chat at
the cloned repository root on the AB bench workstation: the PC that reaches
`192.168.100.89`, with the gateway venv at `C:\work\venv_gw`. Written
2026-10-01, at the close of Phase 5.

Phases 0-5 of
[`AB_TC3_PARITY_AUDIT_2026-09-29.md`](../Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md)
are done and on hardware. A new station can now start from a template that
uses all of it. Phase 6 is configuration completeness and access.

**Calendar V3 preparation (2026-10-05).** Current source emits five shift slots
and per-shift good-part production targets. It supports three weekday shifts
plus two special weekend shifts; each row's days/start/duration remain
independent. Targets are zero until configured and follow calendar boundary
application; PLC current/closed target snapshots drive the generic HMI.
Prepared `C:/work/press76.L5X` is an offline artifact, not a loaded/native-fit
claim. A later guarded read sees V3; press75 remains the measured fit baseline. Require owner Capacity Estimate and
Verify/completed-download evidence for the exact file, then restart the
matching gateway. V2 commissioning migration preserves M-101/all models,
current settings and four schedule rows, appending a disabled fifth row and
zero targets; accounts/sessions/history are not commissioning-image data.
Do not rerun old fixed 13-field Line vectors against the new 21-field contract.
See [preparation evidence](Evidence/AB_PRESS76_SHIFT_TARGETS_OFFLINE_2026-10-05.md)
and the V3 migration/target section in the TC3 handoff.

**ST cleanup (2026-10-05).** Prepared `C:/work/press77.L5X` supersedes press76
for the next source-cleanup import. It formats runtime AOI/routine/SFC ST through
one token-preserving policy, groups the ordered scan and configuration mailbox
transactions into complete services, and shares calendar staging once. Expanded
executable tokens and AOI/RLL/SFC structure match press76; public layouts,
initializers and manifest are identical. Declared data delta is zero, terminators
-28. Native memory/timing remain unmeasured; the SDK refuses No valid license.
The guarded controller read now sees the V3 contract matching prepared press76,
without a new Studio Capacity/acceptance record. Keep press75's accepted memory
measurement separate. Require licensed owner Verify/Capacity/completed download
on the exact press77 artifact before advancing controller claims. See
[cleanup evidence](Evidence/AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.md).

**Configuration memory correction (2026-10-05).** The owner press77 download
reaches compilation/linking but fails globally for memory. Offline data/logic
estimate: 799,860 / 786,432 bytes, 13,428 over. Prepared `C:/work/press78.L5X`
supersedes it, SHA-256
`6063EE0B2E15B9E4C162765701D88E24D58340C1D1D83C4B45E469DFC4735168`.
Only ConfigWrite/ConfigSets change: group identical immutable capability facts,
select snapshot kind once, copy the selected fields once and publish count last.
No feature/layout/data reduction; -156 terminators and -12,373 ST source bytes
relative to press77. All 205 baseline/new execution cases preserve every tag.
The owner reports "its good now" and requests commit/push; this is reported
resolution without a new exact-artifact download/Capacity record. Do not turn
source deltas or the unchanged V3 manifest into measured native memory claims.
See [failure](Evidence/AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.md)
and [correction evidence](Evidence/AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.md).

**Cycle-chart detail repair (2026-10-05).** Repeated chart population/vanishing
was reproduced with live station samples and settled mailbox ACKs. Expiring
detail batches were caused by reading closed-tab rings/sequence data and
waiting for a complete-poll boundary between sweeps. Shared HMI now derives
root-scoped demand from the selected tab's visible cards/control bindings and
renews successful bounded sweeps on the declared slow cadence. Child command
timing belongs to the root scope; sets replies remain explicit targeted reads.
Budgeted tiered clients now move visible detail into the slow snapshot tier and
exclude it again on close. This replaces repeated targeted sweeps for those
clients; non-tiered transports keep the bounded fallback. Keep per-batch expiry, station freshness, mutation gates and
generation-based
pending-reply cancellation. Do not retain expired usable chart data or grow PLC
history to hide this failure. See
[cycle-detail evidence](Evidence/AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.md).
Tab scoping alone passed a single-reader check but was insufficient with
concurrent readers. The optional targeted DataValue envelope now permits sharing
Good native records without resetting their source ages/timestamps. That also
passed the separate read-only gateway but still expired in production; the
visible slow-tier promotion is required. Snapshot responseProcessingMs also
removes gateway acquisition from the client transit allowance, with a
one-millisecond resolution allowance and strict validation. Legacy replies
keep full-RPC aging; source timestamps and Good/expiry limits do not change. Budgeted full polls now resume immediately after a period overrun, with one
acquisition in flight; fast reads still respect the declared minimum period.
Skipping to a later timer boundary had spent the remaining freshness margin. Partial native ACKs remain fresh control reads with their own quality, independent of station
health. Scalar-only gateways remain compatible. Press75 remains loaded; no PLC
download/memory growth is required. Restart the existing gateway and hard-refresh
Chrome to load this repair.

**Filter-navigation follow-up (2026-10-05).** After the owner's two-minute
idle-view acceptance, changing time-type filters exposed a silent return to
the overview. The shared AppState reset navigation on any empty forest, even
when stale data recovered between painted frames. It now preserves only the
selected path/local scope during withdrawal; current nodes and permissions
remain unavailable and the connection owner still gates STALE/DOWN. A populated
replacement forest still invalidates removed selections. The regression changes
filters in the full bootstrap, withdraws/recovers between frames, and checks
that tab/filter state survives. Sustained loss still removes the shell. See
[navigation evidence](Evidence/AB_PRESS75_HMI_FILTER_NAVIGATION_2026-10-05.md).
This is a client-only repair; press75 and gateway code are unchanged by it.

**Painted filter recovery (2026-10-05).** The subsequent owner report includes
a brief Connecting screen and both time/event filters. Rendering-load browser
tests reproduce expiry and a full detail remount; preserving the module path
alone does not restore its selected tab/filter sets. Shared AppState now owns
only these presentation choices per module/view. STALE/DOWN still clears
usable samples/permissions and removes the operator shell. Recovered detail
uses fresh data with its previous tab/time/severity choices. Chip selection
changes geometry immediately and card/control repainting is isolated. Settings
schema 4 also retains the schema-3 language setup fields instead of reopening
language commissioning. No PLC storage, download or gateway restart is needed.
See [filter recovery](Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.md).
The owner confirms tab/filter retention after a hard refresh; the later
[acceptance record](Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_OWNER_ACCEPTANCE_2026-10-05.json)
closes the pending owner check in that recovery record.

**Configuration-page capacity repair (2026-10-05).** Press75 publishes 22
entries, including thirteen Line settings. The shared HMI had rejected pages
above TwinCAT's 16-slot window, leaving the cards empty and Configuration
hidden. It now validates against freshly read discovered rows and rejects
incomplete rows/duplicate slot aliases. Typed Boolean reads also normalize
0/1 to FALSE/TRUE without relaxing write validation. This is a shared HMI
correction with no PLC memory, download or gateway source change. See the
[capacity record](Evidence/AB_PRESS75_HMI_CONFIG_PAGE_CAPACITY_2026-10-05.md).
The applicable port remains on press75; Chrome/retention acceptance remains
separate from repository and native checks.

**Selected-model HMI correction deployed (2026-10-04).** Owner-created M-101
is present in the four-code native catalog and its schema-4 bank. Read-only
inspection observes manifest 66C4A00ABDB4FCC3; this hash alone does not establish
the exact corrective PLC source. The shared HMI now reads discovered config
paths and captures the matching page before cleanup instead of substituting
cyclic cached data. AB 1,563 and HMI 492 tests pass (seven expected HMI skips),
analyzer/release pass, two assertion mutants are killed and HTTPS assets match.
Owner Chrome acceptance is pending; Ctrl+Shift+R and select M-101. No PLC
import/download or gateway restart is needed for this repair. See the
[model-page record](Evidence/AB_PHASE6_HMI_MODEL_PAGE_READ_2026-10-04.md).
Expanded-catalog commissioning images now support modelCodes plus all banks,
with stable seed ordinals, complete validation and no added PLC storage. Two
serial-guarded captures agree on the four-code catalog; offline boot preserves
M-101. Native download/credential retention is not inferred. See the
[catalog-image record](Evidence/AB_PHASE6_CATALOG_IMAGE_2026-10-04.md). Recapture
commissioned values before the next feature artifact; no download is needed now.
Line data/weekdays are loaded in press75; use the current acceptance below. Update the AB guide and TC3 handoff
again after the applicable port stages are actually accepted.

**Owner confirms completed press70 download (2026-10-04).** The owner
reported eight Studio Verify errors in press69: nested array subscripts in the
shared data-permission check. Press69 did not pass Verify. Press70 resolves the
validated ordinal into existing private scratch before indexing; permission and
bounds rules are preserved, with zero extra data storage over press69. Four
mutations are killed, including the refused compiler shape and permission bypass.
See the [correction record](Evidence/AB_PHASE6_SUBSCRIPT_FIX_2026-10-04.md).

Historical press70 artifact: `C:\work\press70.L5X`, SHA-256
`A8CE4B44DA9F09BEE1DCDA1AAC2886F70954C9FA896562D4F3F14D510B9BCF04`,
manifest `66C4A00ABDB4FCC3` / 6735008, binding 2 / 68,472 bytes,
Fields 565/640 and Localization 570/640. Compared with press68: declared data
+2,700 bytes, ST source +5,135 bytes, +59 statement terminators and +54 lines;
RLL stays at 20 rungs. Against refused press69: +50 source bytes, +5 statements
and +5 lines; no data/schema/tag-layout growth. Four users and freshness limits
remain. The source/build hash identifies this logic correction; contract hash
alone cannot distinguish it from press69.

Press70's historical acceptance includes eleven native suites passing
159 rows, S3 passes 6/6 and M-101 current export/live repository read pass. See
[native acceptance](Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md). Exact-serial read-only
capture at 2026-10-04T20:39:15Z confirms serial 7036B510, old manifest and current
commissioned air-pressure minimum 400; press70 seeds that image. The earlier
owner observation of 451 remains historical. No credential-provider upgrade
retention is claimed. Read-only inspection now observes manifest
66C4A00ABDB4FCC3 and owner-created M-101. The owner confirms the exact successful press70 Verify/completed download.
Do not re-download its old three-bank image over the expanded catalog. Any
replacement requires a fresh validated expanded image and separate credential
migration. Owner downloads/restarts; then guard target/fingerprint before native regression,
restoration and browser checks. Do not start a write-enabled gateway yourself.

The owner requests finishing the port beyond the old phase scope. Follow the
[completion sequence](AB_PORT_COMPLETION_PLAN_2026-10-04.md); Line data and weekday/duration shifts are
loaded in corrective press75; Part traceability follows native Line acceptance. The owner also requests per-shift
Monday-Sunday selection, including 12-hour weekend-only shifts, in the line-data
stage. Follow the plan's calendar version/migration and unscheduled-time rules;
the existing daily start-only TC3 calendar cannot express that behavior.
Core 8.5.2 now defines calendar V2. Exact loaded file: `C:/work/press75.L5X`,
SHA 82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5,
manifest 94E302F650BA1DB5 / 9757442, 65,552 bytes. It preserves the fresh expanded
catalog and current Line/config records. Press72 verified/compiled but its
download failed linking at LineValidate. Press73 reduces discovery reserves and
shares ST/SFC step-entry bookkeeping but also fails with a final global memory
error after every named routine links. Owner Capacity Estimate reports
799,428 / 786,432 data/logic bytes (12,996 over) and I/O 2,640 / 1,048,576.
Press75 shares alarm open/close bodies using existing scratch, groups equal
rationalized priorities and emits restore defaults once per record. Data is
-1,812 bytes and ST is -30,972 source bytes/-447 terminators/-413 lines from
accepted press70. All native layouts/tags/AOIs/tasks/other routines compare
equal to press73; all renditions, four users, permissions and chart history
remain. These generation trends do not prove compiled fit. The owner now
confirms press75 completed download at 0/0, followed by Run. Online data/logic
uses 758,568 of 786,432 bytes, leaving 27,864 available (3.54%), largest free
block 27,376. That online use and press73's offline estimate are different
measurement bases. Press75 is the fit baseline. Read-only full manifest,
captured four-model banks/configuration and S3 6/6 pass. Shared HMI assets are
deployed. Native Line behavior, browser controls and physical retention have
separate acceptance scope. The SDK's `No valid license` refusal remains
historical; owner Studio download supplies native fit proof. The six-pair
weekday-mask validator remains. Readers independently refuse old capacities
even with the same logical hash. See the
[fit record](Evidence/AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md).
See [current correction evidence](Evidence/AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md)
and the [earlier allocation correction](Evidence/AB_LINE_V2_LINK_MEMORY_FIX_2026-10-04.md).
Compare every new artifact against accepted press75 fit. Control power remains deliberately excluded; absent
hardware/profile gates stay explicit, not fake success.

**Press75 native acceptance (2026-10-04).** The latest successful suites supply
159 restored rows across eleven suites, plus 17 Line assertions. These
include complete 13-field saved/current export/import, native permissions/
bounds/overlap/partial-set refusal and a twelve-hour weekend shift whose natural
end closes PLC history before applying the restored empty calendar. The unit
returns to unscheduled index 0; two actual closure rows remain. Full captured
configuration/all four banks and admin level 4 are restored. S3 passes 6/6,
max scan 8,384 us, no fault/overlap; fresh complete gateway sample then all
three health routes return 200/plcReady. This is selected successful suites
across three guarded runs, not one uninterrupted all-suite pass. Earlier
cleanup, stale-sequence, stopwatch and schema-preflight failures remain recorded.
The three harness fixes add no PLC memory and need no download. AB 1,607 tests,
21 focused tests, five assertion mutants, root 33 and consistency 0/0 pass.
Chrome controls, physical Line retention and mirror/shared-root transport remain
separate. See [native acceptance](Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md).

Configuration -> Model data -> New model clones an inactive recipe; Model sets
offer Create model from set; ordinary Changeover alone activates it. Eight total
slots include three seeds. Current/saved exports offer Download file and Copy.
Air Start applies to AUTO/HOME, not Changeover; module pressure permits remain.
Do not append disposable native test models: creation is retained and has no
delete action. Obtain an owner-selected model code/source for live creation,
then verify readback and physical retention. The initial
[feature record](Evidence/AB_PHASE6_MODEL_CATALOG_EXPORT_2026-10-04.md) is history,
not evidence that press69 passed native compilation.

**Progress as of 2026-10-03:** Phase 6 items 0–5 are verified on the reference
bench. The owner confirms that press68 was already downloaded. Its native S9
write vector passes **17/17**, all eleven regressions and independent restoration
pass, and S3 passes 6/6 before/after. **Press68 is the current successful loaded
memory baseline**, SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`,
manifest `7A9B9A8B59EEFD16` / 8035226, binding 2 / 68,472 bytes,
Fields 565/640 and Localization 570/640. The four-user ceiling is retained.
This verification adds zero PLC memory and regenerates byte-identically;
**no new import/download is needed**. See the
[native hardware evidence](Evidence/AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md).

The first Phase 5 attempt stopped on an uncommitted frame-write failure; no
automatic replay occurred, and guarded restoration/readback passed. A fresh
run completed 24/25 because the OEE downtime fixture ignored native read time.
The corrected fixture brackets actual acquisition and keeps the 250 ms timing
allowance; the retry passes 25/25, focused tests and both in-memory mutants pass.
PLC/gateway/HMI source is unchanged. Failed outputs are retained in the evidence.

**Item 6 passes on the press68 reference bench.** The owner restarted the
gateway, hard-refreshed Chrome, and reports that the reconnect loop is gone.
The corrected repository passed a 60-second read-only live run: 121 complete
updates, 224 detail batches, no STALE/DOWN transition or empty forest, and a
maximum update gap of 790 ms. Three fresh connections, exact-serial manifest
readback and S3 6/6 also pass. The served Web client remains HTTPS hash-verified.
The probe omitted only ConfigRev-triggered mailbox hydration to remain read-only;
no controller write or armed regression occurred. See the
[live acceptance](Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md).

The owner subsequently reports physically powering the PLC off/on and logging
in successfully with the existing admin credential. Admin credential retention
is owner-confirmed on press68. On 2026-10-04 the owner also confirms that minimum
air pressure, edited from 450 to 451 about nine hours earlier, survives a PLC
power cycle; prior exact-serial readback also shows 451. This establishes the
reported parameter's retention, not every configuration value or saved set.
Saved-set survival, other accounts, download/upgrade retention and the physical
durability window remain unverified. See the
[admin observation](Evidence/AB_PHASE6_OWNER_CREDENTIAL_RETENTION_2026-10-03.md)
and [air-pressure observation](Evidence/AB_PHASE6_OWNER_AIR_PRESSURE_RETENTION_2026-10-04.md).

At the owner's request, the generic HMI cycle trend and step Pareto now filter by
time class using the same selectable legend behavior as Gantt. The release is
served at press.localhost with HTTPS asset hashes verified; no PLC change or
gateway restart was needed. See the
[time-filter delivery](Evidence/AB_PHASE6_HMI_TIME_FILTERS_2026-10-03.md).

The owner then requested a linear Gantt axis that excludes hidden durations
entirely. That adjustment is tested and deployed: visible steps concatenate from
zero, original starts remain in tooltips, and the full-cycle header is preserved.
See the [Gantt follow-up](Evidence/AB_PHASE6_HMI_GANTT_VISIBLE_TIME_2026-10-03.md).

Show all now uses the same chip sizing as the time-type legend, keeping its row
height stable when it appears. The updated Web client is deployed; see the
[legend sizing evidence](Evidence/AB_PHASE6_HMI_LEGEND_SIZE_2026-10-03.md).

D6 health reporting is implemented in both gateways without changing PLC code
or memory. All three health endpoints expose `writeAccess` mutation policy and
scope without credentials. Offline checks pass. After the owner's restart,
all three AB health routes return HTTP 200, `plcReady: true`, and the expected
Press write scope: **D6 live readback passes on press68 (2026-10-04)**. TC3 keeps
its prior offline evidence. No import/download or Web HMI rebuild is needed. See
the [D6 implementation](Evidence/AB_PHASE6_D6_HEALTH_WRITE_ACCESS_2026-10-03.md)
and [live activation](Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md).

**Configuration regression repair (2026-10-04): software checks pass; the
concurrent AB handler is active; browser acceptance passes by owner report.** Opening
Parameter sets could starve complete snapshots on
the same AB WebSocket and make the freshness gate remount the operator shell.
The gateway now multiplexes bounded requests while keeping native reads and
mailbox transactions serialized by their existing locks. Disconnect/overload
cancels queued commands and drains active native work without replay. The
generic HMI excludes published static paths only once their exact manifest
replacements are hydrated, restoring the model list when a binding publishes
it outside configuration pages. Unconsumed SequenceStepDef storage remains
excluded. Full AB 1,541, HMI 478 (7 expected skips), shared TC3/AB 79 and root 33
tests pass; analyzer and release build pass. The Web client is deployed and
HTTPS hash-verified. The owner restarted the existing gateway. A read-only
probe confirms the concurrent request loop is active: inert replies now arrive
in 1.02–1.95 ms while native snapshots continue, rather than waiting behind
them. D6 readback passes. The owner hard-refreshed Chrome and confirms Parameter
sets stays open after at least ten seconds. See the
[activation record](Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md) and
[browser acceptance](Evidence/AB_PHASE6_CONFIGURATION_OWNER_ACCEPTANCE_2026-10-04.md).
The proposed [Station number check](AB_PHASE6_RETENTION_CHECK_PLAN_2026-10-04.md)
was not authorized or executed. The owner's subsequent air-pressure power-cycle
observation makes it redundant for a representative parameter-retention check.
Loaded press68 has no runtime Add model action: edit existing models in Model
data; adding a catalog entry requires a declaration change and owner deployment.
Model set save/export is supported, but model-set load remains deliberately
refused in AB and TC3 until recipe/changeover integration. See the
[current workflow](../Guides/AB_NEW_PROJECT_GUIDE.md#adding-a-model-to-the-current-ab-application).
No PLC download, declaration change or memory growth;
four users and freshness limits remain unchanged. See the
[configuration evidence](Evidence/AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.md).

Inline groups now use the unit card's 8 px spacing in both directions, through
one shared visual token. All 26 similar wraps use it, including health, power,
device status, counters, legends and compact action groups. The unit card keeps
its geometry. The presentation update is built, tested and HTTPS-deployed;
Chrome hard refresh loads it. It needs no gateway or PLC change; the separate
configuration and D6 checks are recorded above. See the
[shared spacing evidence](Evidence/AB_PHASE6_HMI_INLINE_SPACING_2026-10-04.md).

The control-size preset now covers all interactive chip families, time/event
filters, checkbox/radio glyphs, switches and editor icon actions. Shared sizing
keeps Show all level with timing filters and reserves the larger toggle bounds;
read-only badges keep their compact layout. Time quality is first in the health
metrics row. The tested release is HTTPS-deployed; hard-refresh Chrome to load
it. This presentation change needs no PLC download or gateway restart; the
separate configuration/D6 activation results are recorded above. See the
[interactive sizing evidence](Evidence/AB_PHASE6_HMI_INTERACTIVE_SCALE_2026-10-04.md).

Item 6's freshness/poll source and tests pass: press68 declares 500 ms
polling, 250 ms cache, 1,000 ms slow heartbeat, 2,000 ms Good / 3,000 ms expiry,
and a 4,000-byte read connection. Monotonic expiry runs during a stalled RPC;
partial Ack reads cannot renew complete-station health. Commands re-check it
before delivery. The shared TC3/AB suite passes 75/75, AB discovery 1,535 tests,
HMI 463 tests (7 expected skips), analyzer clean, five semantic mutants killed.
Read-only hardware confirms steady maximum 199.521 ms and six shared viewers
224.933 ms; S3 remains 6/6. Press68 and template regenerate byte-identically.
The release Web client is served and HTTPS hash-verified at press.localhost.

**Write-enabled S9 passes for this named press68 deployment.** This combines
the prior authorized native 17/17 vector and eleven regressions/restoration with
the shared contract, declared freshness/expiry enforcement and corrected live
verification. It is not a writable claim for an undeployed template or another
station. No further PLC download is needed. Historical Phase 0 100/300 ms limits
do not transfer. Configuration/set physical retention, the separate historical
S1 clock probe and TC3's native segmented-transport leg remain separate work. D6's AB live
readback passes as recorded above; TC3 health reporting remains offline-tested.
No power cycle, download, clock write or native regression is
authorized by the owner's latest gateway-restart confirmation. See the
[freshness evidence](Evidence/AB_PHASE6_S9_FRESHNESS_2026-10-03.md),
[loop correction](Evidence/AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md), and
[live acceptance](Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md).
The owner has deferred further mode-latency tuning. Do not ask for the press68
download again or restart/start a write-enabled gateway yourself. Existing
[offline evidence](Evidence/AB_PHASE6_S9_OFFLINE_2026-10-03.md),
[read-only preflight](Evidence/AB_PHASE6_S9_READ_ONLY_PREFLIGHT_2026-10-03.md)
and [command-latency evidence](Evidence/AB_PHASE6_COMMAND_LATENCY_2026-10-03.md)
remain append-only history.

The table and initial commands below describe the original handover.

## State at handover

| | |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`, `192.168.100.89:44818` |
| Loaded build | `press52.L5X`: `ContentHash 4FD8961CE0AA3E17`, `ConfigRevision 5232790`, manifest 55,160 bytes. File SHA-256 begins `c4c4158b10df978a`. Repository logic `75c288c`; [evidence](Evidence/AB_PHASE5H_SYSTEM_HEALTH_ON_HARDWARE_2026-10-02.md) |
| Repository | `main` at `00faf8b` or later: the new-station template, the selector and the guide. The press still emits byte-identical to press52, so **no download is pending** |
| AB tool suite | 1282 tests. `check_consistency` 0 errors, 0 warnings |
| Last bench run | Phase 5 25/25, S3 6/6, §146 parity 25/25, Phases 1-4 7/7 · 6/6 · 8/8 · 11/11 |
| Manifest room | budget 57,344 bytes; Fields 485/512, Localization 460/512, Rationalization 20/32 |
| Decisions on record | Baseline **v33 legacy zone-and-conduit**. **Writes enabled on the bench by explicit decision 2026-09-29.** S9, the suite that would back that decision, is **owed**. Q1: per-user principals on the controller, as TC3 |

---

```text
You are continuing the Fraktal/AB (Allen-Bradley Logix) implementation. Objective:
Phase 6 of Specification/Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md - configuration
completeness and access - so Fraktal/AB behaves as the TwinCAT (TC3) build does.
TC3 is the behavioural oracle for semantics, never for implementation shape.

HOW THE USER WORKS (follow it)
* "should be same as tc3 build, why do you asking for a choice?" - do not offer menus.
  Decide what TC3 does, explain the implications of the decision, and recommend
  per Fraktal's principles and objectives (Core §1.1, O1-O10). Ask only the
  questions AGENTS.md §3a requires, plus controller-changing authorization.
* The loop:
  - The user says "go on". You build one item offline: declaration and
    generator change, tests, mutation checks, and the L5X written to
    C:\work\pressNN.L5X (next is press53). Commit it.
  - Then tell the user exactly what to import and download.
  - The user imports and downloads in Studio 5000 v33, restarts the gateway, and
    replies "done".
  - You verify on the controller, write dated evidence, update the audit and
    README, commit, and report.
* "done" after a download is the user's authorization for the verification
  harnesses' tag writes on serial 7036B510. It covers nothing else.
* Keep replies short. Report failures plainly, with the output.
* Remaining implementations must track controller memory growth. Owner Verify
  exhausted memory in press57 and press65; press66 compiled but exhausted memory
  at link/download, which was cancelled. Keep the four-user ceiling; reuse bounded
  native loops and existing tables. Generation now includes GeneratedSize.
  Compare per-routine/total source and statement counts plus declared data with
  the last successfully downloaded L5X using fraktal_ab_generated_size.py --baseline.
  These are trends, not compiled memory: fit needs owner Studio Verify AND a
  completed link/download. Do not advance the baseline on Verify alone or assume
  controller state after a cancelled download. Size Fields/Localization reserve
  to the declaration with the existing 768-row ceilings, not the ceiling itself.

READ FIRST, IN THIS ORDER
1. AGENTS.md (§3a is the AB rules) and FraktalCore/PLC/Allen-Bradley/README.md.
2. Specification/Guides/AB_NEW_PROJECT_GUIDE.md: what the binding already does,
   the Logix rules, capacity, what a healthy station looks like.
3. Specification/Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md:
   - §4: open defects D5 and D6;
   - §6.5 and §6.6: the Phase 6 gaps;
   - §7: decision Q1;
   - §8: the Phase 6 plan;
   - §9: the platform rules.
4. Specification/Fraktal_AB_Part_III.md: the claim table, §11.2.1, and S9.
5. Core (Specification/Fraktal_Core_Part_I.md): §3.8b persistence and parameter
   sets; §3.8c teach capture (CAPTURE_CONFIG); §3.8d data classes; §7.7 access;
   §8.10 shelving; §14 security.
6. FraktalCore/PLC/TwinCAT/IMPLEMENTATION_NOTES.md, how TC3 did each:
   - §22 shelving;
   - §77 PLC-authoritative permissions;
   - §78 capability-driven configuration writes;
   - §80 Web read tiers;
   - §89 access-policy mailbox fixture;
   - §133 durability;
   - §137 set delete;
   - §138 data classes;
   - §141-§143 the set listing and lines;
   - §149 model data;
   - §150 salted PIN hashes;
   - §151 a model's data as one page.
   The TC3 code is FB_UnitBase (CAPTURE_CONFIG, the access methods) and
   FB_ConfigSetJson.
7. Specification/HMI_CONTRACT.md: the sets dialog, login and the access level the
   HMI expects. The HMI is generic: never add AB screens.

STANDING RULES (NOT NEGOTIABLE)
* One committed declaration is the source and the L5X is output. Never hand-edit
  L5X or ladder. Regenerate.
* Never download, change mode or keyswitch, write a tag, clear a fault, set the
  clock, or touch firmware or network configuration without CURRENT explicit
  authorization from the user in this session. Check serial 7036B510 at
  192.168.100.89 immediately before the operation. Prior authorization is
  historical. Compile and download are the owner's, on the licensed desktop: the
  SDK probe on this workstation refuses "No valid license".
* Controller reads are allowed with the serial guard every tool already applies.
* Never start a gateway with a write root yourself; the user (re)starts it. The
  write token lives in C:\work\caddy\Caddyfile. Never echo it, and prefer the env
  var FRAKTAL_GATEWAY_WRITE_TOKEN over argv. Credentials are in C:\work\creds.txt;
  never print them.
* Evidence is append-only: new dated files under Specification/AllenBradley/Evidence/
  (.md plus the harness .json), never edits to old ones.
* Never bypass the gateway's build-hash check. If the repository is ahead of the
  controller, the fix is a download. If a gateway must run before the download,
  run it from a worktree at the commit that produced the loaded build.
* Do not push unless asked. Commit with the attribution trailer the session gives you.
* AGENTS.md §3a, question 1 (read-only or write-enabled) is answered for this
  bench: write-enabled by the 2026-09-29 decision. Phase 6 widens what a
  write can do (sets, login, shelving). Say so in each item's evidence, and
  do not record the write-enabled claim as met until S9 passes.

THE GATES (run before every commit)
  cd FraktalCore/PLC/Allen-Bradley/tools
  # clear __pycache__ first; mutations always with -B
  C:\work\venv_gw\Scripts\python.exe -B -m unittest discover -s . -p "test_*.py"
  cd ../../../..
  C:\work\venv_gw\Scripts\python.exe -B tools/check_consistency.py
  C:\work\venv_gw\Scripts\python.exe -B -m unittest tools.test_check_consistency
Generate:
  python -B fraktal_ab_generate.py C:\work\seed_v33.L5X C:\work\press53.L5X
  - It refuses an existing output.
  - Record the file SHA-256 and the manifest bytes. ContentHash covers the
    published contract and versioned native mailbox profile, not logic or
    manifest-table reserve capacity.

THE VERIFY SET, after the user's "done" (all from the AB tools directory)
  python -B fraktal_ab_manifest_read.py 192.168.100.89 --expect-serial 7036B510
      "passed": true (coherent, every row equal); bytesRead identifies the build
  curl http://127.0.0.1:8099/healthz                (status "ready", plcReady true)
  python -B fraktal_ab_s3_execute.py 192.168.100.89 --expect-serial 7036B510     (read-only)
  python -B fraktal_ab_press_parity.py 192.168.100.89 --expect-serial 7036B510 --execute-fixture
  python -B fraktal_ab_phase1_execute.py ... --execute-fixture   and phase2 .. phase5
Add a Phase 6 harness (fraktal_ab_phase6_execute.py) on phase5's pattern:
  - serial and fingerprint first;
  - read-only rows before writes;
  - an explicit --execute-fixture arm;
  - restore everything it writes in a finally;
  - command through the mailbox the way the HMI does: arguments first,
    Sequence last, then AckSequence read back.

LESSONS THAT COST TIME (do not relearn them)
* Prove a command by what the PLANT did (module command counts, end positions),
  never by its acknowledgement.
* Isolate direct native fixtures from HMI tabs; their process is outside the
  production gateway's mailbox lock. Read a settled request/ACK cursor for each
  direct command and refuse a changed cursor before commit. Gateway and direct
  helpers advancing the same mailbox cannot share a cached local counter.
  Require the login's own LoginResultSequence; Program mode stops its task.
* Start a watchdog stopwatch before command/setup reads; reads consume time while
  the PLC timer runs. Verify the PLC elapsed value too. Derive set-state schema
  from the declaration (Line enabled means V2), never assume every station is V1.
* Never await a flag that lives a couple of scans: a CIP poll misses it and the row
  times out silently. Await a level or a counter.
* Read every structure with read_layout (dimension-aware), never by member names
  (D9: the first array a type gained shifted every member read by name after it).
* One standing LOW event, CONTROLLER_METRICS_UNAVAILABLE (21), is EXPECTED: CPU
  and memory have no GSV source. It occupies an active-alarm slot. Find a fault
  by FaultEvt, never Active[1].
* ContentHash ignores capacity and logic.
  - Two builds can share a hash, so identify a build by file hash and manifest
    bytes.
  - The gateway refuses a capacity mismatch by name ("Fields holds N rows on
    the controller..."). That message means the controller is behind:
    download.
* After every download the gateway must be restarted. "Not allowing mode change"
  right after a download has meant exactly that, four times.
* Logix v33 rules:
  - DINT only in contract UDTs; no string literal assignment in ST.
  - At most 5 operators of one kind per expression; anything that scales is
    one IF per term (test_fraktal_ab_platform_limits).
  - An AOI cannot reach controller scope.
  - No shift operator and no UDINT, so a hash's rotates are BTD plus DINT
    wraparound (audit Q1).
  - Studio import is the arbiter for GSV attribute names.
* A stale same-size mutant .pyc once survived its restore. Use -B and clear
  __pycache__.
* The press masks generator assumptions: it registers every reason and uses every
  feature. Build each Phase 6 feature into fraktal_ab_station_template.py too;
  test_fraktal_ab_station.py keeps the template a working station. Three defects
  were found exactly that way on 2026-10-01.

PHASE 6 SCOPE - recommended order, each one download unless noted
0. ROOM FIRST (one download, no feature).
   - Phase 6 adds mailbox kinds, set rows, a user table and localization keys,
     and Localization (460/512) and Fields (485/512) are nearly full.
   - Raise them, and the manifest budget, by the S7 cost-curve rule.
   - Confirm the raise by reading the manifest back from the controller. Never
     assume it.
1. CAPTURE_CONFIG (Core §3.8c teach capture, TC3 FB_UnitBase).
   - Small, and it exercises the configuration write path that sets also use.
   - Close D5 in the same item: QUERY_CONFIG only reads but travels as a
     mailbox write, so a read-only viewer cannot see configuration at all. Fix
     it in both gateways.
2. Parameter sets: save, load, list, export, import, delete, and
   ACK_CONFIG_RESTORE (§3.8b; TC3 §137, §141-§143).
   - Part III decides the split: "the controller owns the values and every
     validation, the gateway owns the document and the medium". Most of this
     is gateway work.
   - The controller stages and validates. A load is migrate-or-fault, never
     partially applied.
3. Per-user access on the controller (Q1; §7.7; TC3 §77, §89, §150).
   - A user table with PINs as salted, iterated SHA-256.
   - LOGIN and LOGOUT, levels, and a session timeout.
   - Every mutation re-checked on the controller.
   - Why on the controller: FRK_Press_HmiRequest is externally writable, so
     anything enforced only in the gateway can be bypassed.
   - `--access-level` becomes the pre-login level.
   - The Secret is cleared immediately after sampling.
4. Data classes with per-value access (§3.8d, TC3 §138), once access is enforced.
5. Alarm shelving (§8.10, TC3 §22), on the existing alarm log. Registry
   rationalization decides what is shelvable.
6. S9, the write-enabled contract suite. Only once it passes may Part III record
   the write-enabled claim as met.
Close D6 when convenient (S): /healthz, /livez and /readyz do not say whether the
write gate is on.

THE MAILBOX TODAY (fraktal_ab_mailbox.py)
* It routes SET_MODE, START, STOP, OPERATOR_RESET, DECISION_ANSWER,
  MANUAL_COMMAND, FORCE_CHANNEL, SET_MODEL, RELEASE_START, RELEASE_MANUAL,
  RELEASE_ACTION and RESET_OEE.
* It also routes the run-style kinds, and WRITE_CONFIG for a station with
  editable values.
* It refuses the rest BY NAME, each with a localization key that names the owed
  work. Phase 6 turns these refusals into routes:
  - access_not_enforced: LOGIN, LOGOUT, SET_ACCESS_LEVEL, SET_SESSION_TIMEOUT,
    SET_CLASS_LEVEL;
  - no_config_manifest: QUERY_CONFIG, CAPTURE_CONFIG;
  - no_config_sets: the seven set kinds;
  - no_shelving: SHELVE_ALARM, UNSHELVE_ALARM.
* Never route a kind to the nearest similarly named tag. A kind is routed only
  where the declaration has the mechanism.

LEFTOVERS, NOT PHASE 6 (keep them visible)
* S3's MODULE connection state (INT attributes) is still owed in system health.
* Nameplate is class N. The frozen v1 Nameplates table cannot carry the IDTA
  fields, so it needs a contract decision first. Recommend one before building.

FIRST STEP
Read the documents above, then run the gates and the read-only half of the
verify set:
- manifest_read: expect "passed": true and bytesRead 55,160;
- /healthz;
- s3_execute.
That confirms the controller still carries press52 and the gateway is ready.
Then report, and on "go on" build item 0 (room), then item 1.
```
