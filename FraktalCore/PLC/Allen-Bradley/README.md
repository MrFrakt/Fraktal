# Fraktal/AB

This tree is reserved for the Allen-Bradley Logix binding. The authoritative
implementation specification is
[`Specification/Fraktal_AB_Part_III.md`](../../../Specification/Fraktal_AB_Part_III.md).

Current status (2026-10-04): **R0-R6 PASS at their recorded scope; main press
operation and Phase 0-6 features have reference-bench proof on press68.** R6's
original claim remains read-only. The later write-enabled S9 result is qualified
for the named press68 deployment, not every station. Read-only remains a gateway
deployment policy; inert QUERY_CONFIG transactions can read through the mailbox.

**ST organization (2026-10-05):** current source emits consistent four-space
ST layout for runtime AOIs, routines and SFC action/condition bodies. An ordered
scan plan groups startup, restore, modules, Start, Unit dispatch, health,
diagnostics, statistics and forcing into named program services. Configuration
writes/sets have separate mailbox services; calendar candidate copying is shared
once. Existing permissions, scan/ACK order, public layouts and all three
sequence renditions are unchanged. Prepared `C:/work/press77.L5X` adds zero
declared data bytes and removes 28 ST terminators relative to press76; formatted
source grows from whitespace. Native object/call overhead remains unmeasured:
Studio Verify/Capacity/completed download and scan timing remain owner gates.
The SDK attempt refuses **No valid license**. A guarded read now sees the V3
contract matching press76; press75 retains the last accepted memory measurement.
See [cleanup evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS77_ST_CLEANUP_OFFLINE_2026-10-05.md)
and the [routine guidance](../../../Specification/Guides/AB_NEW_PROJECT_GUIDE.md#structured-text-layout-and-routine-ownership).

**Memory correction (2026-10-05):** the owner press77 download subsequently
reaches compilation/linking and fails with a global memory error; its offline
data/logic estimate is 799,860 / 786,432 bytes, 13,428 over capacity.
Prepared `C:/work/press78.L5X` groups identical capability bounds/flags and
copies selected configuration snapshots once per kind. Only ConfigWrite and
ConfigSets change, removing 156 ST terminators and 12,373 ST source bytes with
zero declared-data growth. Formatting, routine ownership, capacities,
permissions and transaction order are preserved. The owner reports "its good
now" and requests commit/push; no new Capacity measurement or exact-artifact
download transcript accompanies that report. Press75 retains the measured
memory baseline. See [failure](../../../Specification/AllenBradley/Evidence/AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.md)
and [correction evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS78_CONFIG_MEMORY_REDUCTION_2026-10-05.md).

**Declared medium and live documents (2026-10-07):** a declaration now picks
where the gateway keeps its documents (`decl.ConfigMedium`, Core
`E_ConfigStore`; the file medium is the only implementation, behind
`fraktal_ab_medium.SetStore`). At the owner's request the press also keeps its
station, line and model data as **live documents** in `live\` beside its sets
and re-applies them after a download through the ordinary staged set path,
under a controller session the set gate permits (`fraktal_ab_live.py`, Part III
AB §3.8b). Restoring is derived controller state: Start names
`std.release.configRestoring` and configuration writes wait until the station
load answers. A read-only gateway never restores. Prepared
`C:/work/press79.L5X` adds 3,132 ST source bytes and 28 statements to press78,
with no new data or tag; the manifest moves to `E5F914E06055CD3B / 15071508`,
and sets saved under press78's revisions still load. A read-only read on
2026-10-07 shows the V3 contract loaded (press76 or press78; the owner must say
which). Capacity Estimate, Verify, the seeded first download and download/power
cycle acceptance are owner gates; until press79 is loaded, run any gateway from a
worktree at `3d77e7a`. See
[offline evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.md).

Shared HMI cycle-chart correction (2026-10-05): detail reads now follow the
selected tab's visible cards rather than loading closed-tab rings and sequence
rows. Tab scoping and timestamp-preserving targeted reads passed isolated
checks but still expired under production load. Budgeted tiered transports now
promote only visible detail to the slow snapshot tier, renewing native records
without repeated leaf batches. Closing the view excludes them again. Original
source age/quality, station freshness and write gates remain enforced. The
optional targeted DataValue envelope retains age for fallback/explicit reads;
partial ACK reads cannot renew station health. The optional snapshot processing
bracket removes duplicate native acquisition time from client transit aging;
source ages/quality/limits remain unchanged. Budgeted full polls now resume immediately after a period overrun, with one
acquisition in flight; fast reads still respect the declared minimum period.
Skipping to a later timer boundary had spent the remaining freshness margin. No PLC download/memory growth is required; load the updated gateway source and hard-refresh Chrome. See
[cycle-detail evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.md).

**Five shifts and production targets (2026-10-05):** the current generator
emits the optional owner calendar V3 with five slots, enough for three weekday
shifts and two weekend shifts, and a good-part target per slot. All existing
weekly/permission/boundary rules remain. The PLC latches the current target
and snapshots it into the same eight-record history before resetting. The
generic HMI shows current progress and historical targets/attainment. An
explicit V2 commissioning bridge preserves the four prior rows and model
catalog, appending an unused fifth row and zero targets. Prepared
`C:/work/press76.L5X` adds 2,756 declared data bytes to press75; Studio Capacity
Estimate, Verify and completed download are still owner gates. The subsequent
guarded V3 read is recorded above; press75 remains the accepted memory baseline.
Restart the existing gateway only after the
matching build is downloaded. See
[offline preparation](../../../Specification/AllenBradley/Evidence/AB_PRESS76_SHIFT_TARGETS_OFFLINE_2026-10-05.md).

The subsequent time-filter report exposed a separate navigation reset: an empty
withdrawn forest cleared the selected unit even if data recovered before a
connection frame was painted. Shared AppState now retains navigation intent
while usable data/permissions still clear; sustained STALE/DOWN still gates
the shell and a populated replacement forest invalidates removed selections.
This follow-up needs only the updated client, with no gateway restart or PLC
download. See [navigation evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_NAVIGATION_2026-10-05.md).

**Painted filter-recovery follow-up (2026-10-05):** the owner subsequently saw
brief Connecting screens with both time and event filters. Rendering-load tests
reproduce expiry and a full detail remount, which the between-frame repair did
not cover. Shared HMI state now retains tab ID and per-view time/severity choices
across that gate; samples and permissions still withdraw. Filter chips change
geometry immediately and cards/controls isolate repainting. This is client-only,
with no PLC storage increase or gateway restart. See
[filter recovery](../../../Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.md).
The owner hard-refreshed and confirms both tab and filter choices stay selected;
see the [acceptance record](../../../Specification/AllenBradley/Evidence/AB_PRESS75_HMI_FILTER_RECOVERY_OWNER_ACCEPTANCE_2026-10-05.json).

Shared HMI correction (2026-10-05): press75's 22-entry configuration page
exceeded a client assumption that every binding used TwinCAT's 16 slots.
The repository now validates freshly read discovered row capacity and the
complete payload before hydration. Typed Boolean read text 0/1 is normalized
to FALSE/TRUE without relaxing write validation. No PLC or gateway source
changes are required. See
[configuration-page evidence](../../../Specification/AllenBradley/Evidence/AB_PRESS75_HMI_CONFIG_PAGE_CAPACITY_2026-10-05.md).

The port is **not complete apart from power**: Part traceability,
signal-tower/host integration and optional profiles/probes remain absent or
unclaimed. The current gap census against TwinCAT (including TC3's
project-chosen retained-data medium) and the next implementation order are in
the [missing-features handover](../../../Specification/AllenBradley/AB_MISSING_FEATURES_HANDOVER_2026-10-06.md). Line owner/calendar V2 is loaded in corrective press75 after
press72 failed linking at LineValidate and press73 failed with a final global
memory error; owner-confirmed fit passes at 0/0 and Run, while native/browser/
retention acceptance has separate scope and
mirror/shared-root transport is unbound. See
[correction evidence](../../../Specification/AllenBradley/Evidence/AB_LINE_V2_ALARM_MEMORY_FIX_2026-10-04.md).
Press75 retains proportional discovery and shared ST/SFC step-entry services,
shares alarm open/close bodies, groups rationalized priority branches and emits
restore defaults once per record. All three renditions,
four users, permissions and PLC chart history remain. Declared data is 107,512
bytes (-1,812 from accepted press70); ST is 260,844 source bytes (-30,972),
4,091 terminators (-447), 5,156 lines (-413), with the same 20 RLL rungs.
These are generation trends, not compiled memory or proof of fit.
The owner's press73 Capacity Estimate is 799,428 / 786,432 data/logic bytes,
12,996 over; I/O is 2,640 / 1,048,576. Press75's online data/logic use is
758,568 / 786,432 bytes, leaving 27,864 available and a 27,376-byte largest
free block. These differing measurement bases do not prove an exact compiled
saving. See [fit evidence](../../../Specification/AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md).
Press69 failed owner Studio Verify on nested array subscripts.
Corrective press70 retains inactive model creation/current export and Changeover
entry-permit scope; owner-confirmed completed-download fit, restored native
regressions and M-101 export/live repository read now pass. The correction
reuses private scratch and adds no data storage over press69. See the
[correction evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SUBSCRIPT_FIX_2026-10-04.md)
and [completion plan](../../../Specification/AllenBradley/AB_PORT_COMPLETION_PLAN_2026-10-04.md).
Press75 is the successful memory baseline; press70's 159 native rows and S3 6/6
remain historical proof at that older artifact's scope.
Press75 supplies 159 successful restored rows across the eleven regression
suites, plus 17 Line rows: calendar permissions/atomicity, saved/current export/
import, a twelve-hour weekend shift and its natural end. All captured config/
four-model banks are restored; actual shift history is preserved. Final S3 is
6/6 with max scan 8,384 us against 10,000 us and no fault/overlap. See
[press75 acceptance](../../../Specification/AllenBradley/Evidence/AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.md).
Chrome controls, physical Line retention and mirror/shared-root transport remain
separate. Three harness defects were corrected without PLC growth: stale direct
sequence counters, watchdog timing excluding acquisition, and a hard-coded V1
set-state expectation. Failed evidence is retained.
Chrome acceptance and physical upgrade retention remain separate. See
[native acceptance](../../../Specification/AllenBradley/Evidence/AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.md) and the
[current project guide](../../../Specification/Guides/AB_NEW_PROJECT_GUIDE.md)
and [TC3 transfer prompt](../../../Specification/AllenBradley/AB_TO_TC3_HANDOVER_PROMPT_2026-10-04.md).
Core source reserves the shared kinds at 0.22.0.0; no TC3 runtime capability is
claimed by that enum extension. S15 still needs the licensed desktop and owner
download; S5's isolated-bench/manual deployment boundary is unchanged.

**Starting a new station:** read
[`Specification/Guides/AB_NEW_PROJECT_GUIDE.md`](../../../Specification/Guides/AB_NEW_PROJECT_GUIDE.md).
Copy [`tools/fraktal_ab_station_template.py`](tools/fraktal_ab_station_template.py),
which includes the Phase 0-6 basics (optional model creation stays off), and select the copy with
`FRAKTAL_AB_DECLARATION`. Every generic tool reads that variable, so a new
station never means editing a tool.

**Historical Phase 4 baseline.** The runtime base exists in its generated form: one
committed Python declaration emits the contract UDTs, the module AOIs, the mode
owner, the routine and the full-project L5X, and the press demo emitted from it
imports at `0/0`, clears Studio v33 Verify at `0/0`, is a registered gate leg,
and runs on the bench with all fifteen matrix rows passing on three consecutive
runs. **Hand-authored L5X remains forbidden** - the declaration and the
generator are the committed sources and the L5X is output.

The press AUTO graph is declared once and **rendered in all three languages** -
ST, native SFC and ladder - each emitted from that one declaration, read back
and machine-checked for graph equality, and walked on the bench with identical
traces. MANUAL and HOME stay single-rendition ST, as the TwinCAT press keeps
them. **Hand-authored ladder is forbidden along with hand-authored L5X**: a
rendition is an emission, never a second maintained source. And the published
contract will describe that graph **once, rendition-agnostic** - the rendition
selector is a harness input, probe-only and never published, because which
language ran is a property of how the application is measured, not of the
machine it describes.

**The module library has started.** Reusable types live in
[`tools/fraktal_ab_library.py`](tools/fraktal_ab_library.py), the counterpart of
TC3's `Fraktal_Modules`, and an application embeds one AOI per *type* it uses —
the same bytes in every application, which `test_fraktal_ab_library.py` proves by
generating two unrelated applications. The cylinder is the first type.
Changeover with per-model stored data, editable configuration, physical I/O with
§10.5.1 forcing and the §3.8a restore gate are built, and Phase 1 of the plan -
the §8.3 alarm log, step conditions, and diagnostics that name their sensor and
onset - Phase 2's §3.13 flow chart, and TC3's registered reason codes with
the §6.9 stall watchdog are built and running on the bench (press33,
2026-09-30). Phase 3's library types - TC3's digital input, two-hand start
and air-pressure monitor - run on the bench too, with TC3's N220 dwell pause
(press38, 2026-10-01). TC3's N180 abandon, its two-hand policy and its
per-step stall time run on the bench too, in all three renditions (press40,
2026-10-01), and so do TC3's per-module manual commands and collision
interlocks (press41). TC3's release reports, with Start gated by its own
report, run on the bench as well (press43, 2026-10-01): Phase 4 of the
parity plan is complete. Phase 5 has begun: TC3's run styles - SINGLE_STEP
and HOLD_TO_RUN beside CONTINUOUS - run on the bench in all three renditions
(press44, 2026-10-01), and press45's manifest, raised to 51,064 bytes to make
room for the rest of Phases 5-6, reads back whole in 142 ms. TC3's OEE, with
its trend and reset, runs on the bench too (press46); TC3's machine state and
rework count as well (press47); TC3's cycle-time profile too (press48); TC3's command timing and degradation
watch as well (press49); TC3's derived state flags too (press50). Spike S3 has measured what this
controller says about its own health and timing (press51; partial: module
connection state is still owed), and TC3's §8.12 system-health publisher runs
on that subset on the bench (press52). The `PartFeed` axis is not built,
by TC3's own rule: it arms only on a real axis, and this controller has no
Integrated Motion. Part traceability and any control-power domain are not;
what remains, and in what order, is the plan in
[`Specification/Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md`](../../../Specification/Reports/AB_TC3_PARITY_AUDIT_2026-09-29.md).

**Phase 6 room is confirmed on hardware (press53, 2026-10-01).**
`C:\work\press53.L5X` raises Fields and Localization from 512 to 768 rows,
bringing the press and template manifests to 79,736 bytes under a 96 KiB
budget. The generator now rejects table or byte-budget overflow before writing
an output. Against press52, only the manifest header and these two array tags
change; the contract hash remains `4FD8961CE0AA3E17`. Capacity is therefore
confirmed by full manifest readback after download, never by the hash alone:
the press's 79,736 bytes read back coherent, with every row equal, in 177.236 ms.
S3 passed 6/6, parity 25/25, and Phases 1-5 passed 7/7, 6/6, 8/8, 11/11 and
25/25; every fixture disarmed and the gateway remained ready. The
[hardware record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ROOM_ON_HARDWARE_2026-10-01.md)
completes the
[offline build record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ROOM_BUILD_2026-10-01.md).

**Phase 6 item 1 is confirmed on hardware (press54, 2026-10-01).**
The press and template register capture of `Profiler.LastWork` into their
editable `BaselineWorkMs`. The controller samples its own source, checks the
capability revision, setup mode, release permissives and ordinary write range
and readiness, then records accepted typed writes and captures in a 16-entry
audit ring. Audit reads are on demand, keeping history out of cyclic HMI polls.
D5 is fixed in both gateways: complete, inert `QUERY_CONFIG` batches
work without a write root, while every mutation retains its gate. AB transactions
are serialized across viewers. The manifest is major 3 and 79,992 bytes under
a 100 KiB bound; an old gateway must refuse it. Controller per-user access and
S9 remain owed. On serial `7036B510`, capture stored and audited the completed
cycle's 970 ms WORK value; every negative passed and the original 950 baseline,
AUTO mode and CONTINUOUS style were restored. The Phase 6 suite passed 10/10,
S3 6/6, parity 25/25 and every Phase 1–5 regression passed. All fixture inputs
cleared and the gateway stayed ready. Full manifest readback was coherent and
equal; the repeat took 180.092 ms. TC3's D5 evidence remains its offline tests.
See the [hardware record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.md)
and [build record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_CAPTURE_BUILD_2026-10-01.md).

**Phase 6 item 2 is confirmed on hardware (press55, 2026-10-02).**
The press and template enable save, load, list, export, import and delete through
the existing generic HMI. The gateway owns four named JSON-line documents; the
controller copies the staged request privately, validates every station record,
and commits all values together. Model save/export is supported; model load
refuses until recipe-store integration, matching TC3. A 16-entry controller audit
records accepted and refused set requests. Save/delete/final import wait up to
five seconds for a host file receipt; failure stays visible in `ConfigPersist`.
This does not establish controller retention across power cycle, download or
upgrade. Controller per-user access and S9 remain owed. The 79,992-byte manifest
uses Fields 526/768 and Localization 514/768 (template: 340 and 425).
The owner downloaded press55 and restarted the gateway. The set fixture passed
17/17, capture 10/10, S3 6/6, parity 25/25 and all Phase 1–5 regressions passed.
All station values, AUTO/CONTINUOUS and ten fixture inputs were restored; the
isolated stores are empty. Full manifest readback was coherent and equal; the
repeat took 171.329 ms. The first attempt exposed mixed direct/gateway commands
in the harness; routing every fixture command through its gateway fixed it
without changing press55. AB 1364 and consistency 32 pass, with 0 errors and
0 warnings; three new harness mutations are killed. The build's HMI and mutation
results remain offline evidence. See the
[hardware record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SETS_ON_HARDWARE_2026-10-02.md)
and [build record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SETS_BUILD_2026-10-02.md).

**Phase 6 item 3 is built offline (press56, 2026-10-02).**
Controller-owned users, salted iterated PIN hashes, LOGIN/LOGOUT, twelve gate
thresholds and idle timeout now share one generated provider with the station
template. The template enables an empty user table and default open policy.
Every mutation is rechecked on the PLC; a native mailbox User claim grants no
role. Secret bytes are wiped before hashing; a bounded background check leaves
the mailbox available, and the generic HMI waits for its result. Accepted
configuration/set audits now use the controller session actor; access audit
messages use the existing 64-slot history ring.
`--access-level` becomes a pre-login display ceiling. The bearer/proxy remains
the transport gate. Press manifest Fields 544/768 and Localization 541/768,
ContentHash `0FC1A37DB998B41C`, revision 1032611, bytes 79,992.
The generated file is `C:\work\press56.L5X`; it and the template reproduce
byte-for-byte. Owner Studio v33 Verify/download and guarded `--access` hardware
verification are pending. The SDK probe refused **No valid license**. Runtime
hash cost, physical retention and the write-enabled S9 claim remain owed.
See the [build record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_BUILD_2026-10-02.md).

**Studio correction (press57, 2026-10-02):** owner Verify of press56 reported
54 undefined-tag errors for `TRUE`. The shared bit-distribution emitter now
assigns `EnableIn := 1`; press57 changes exactly those 54 statements and
reproduces byte-for-byte. The ST model now treats TRUE/FALSE as tag names, and
the platform gate rejects their use across the press and template routines.
Manifest bytes, ContentHash and revision are unchanged. This artifact is
superseded by press58 below. Hardware proof and
S9 remain owed; see the [correction evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_BOOLEAN_FIX_2026-10-02.md).

**Memory correction (press58, 2026-10-02):** owner Verify of press57 reported
**Out of memory in the controller**, one error and zero warnings. Private user
storage now follows the three deployed registrations instead of reserving
sixteen. `AccessAuditV2` packs each 32-byte actor into eight DINTs, preserving
all 64 history slots. Rotates and audit writes use shared generated routines;
SHA finalization uses loops and the round constants use a private constant
table. Declared access storage drops by 10,112 bytes; the empty-user template
saves 10,768 bytes. SHA plus rotate ST drops from 724 to 222 lines. These are
source/storage counts; Studio must establish the compiled project fits.
Fields and localization counts and the 79,992-byte manifest are unchanged;
ContentHash is now `D90151DAB7A1FC1B`, revision 14221649. AB 1404 and root 33
tests pass, consistency reports zero errors/warnings, and 33/33 mutations are
killed. The SDK again refuses **No valid license**. Import
`C:\work\press58.L5X` for the pending owner Verify/download, then restart the
gateway. Authentication rules, physical retention and the S9 claim retain
their pending hardware gates. See the
[memory correction evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_MEMORY_FIX_2026-10-02.md).

**Four-user limit (2026-10-02):** the owner requested a maximum of four users.
The declaration rejects a fifth registration before generating an artifact.
Storage still follows the actual registrations: press58 has three rows, and
the empty template has one inert row. Both L5X files reproduce byte-for-byte
after this limit change. The owner now reports press58 downloaded; guarded
controller proof is next. No replacement download is needed for this ceiling
change. See the
[limit record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_FOUR_USER_LIMIT_2026-10-02.md).

**Press58 controller verification (2026-10-02):** serial 7036B510 has the
coherent 79,992-byte manifest, ContentHash `D90151DAB7A1FC1B`, revision 14221649.
The gateway is ready. The access fixture **failed** because login did not
settle within six seconds. The audit subsequently recorded successful admin
authentication, but hash work raised maximum scan from 1,166 to 31,065 µs,
overlap from zero to 606 and minor fault bits from zero to 64; major bits
remain zero. Press58's SHA block per scan exceeds this controller's 10 ms task
budget. Policy, timeout, station.number, mode/style/baseline and all ten fixture
inputs ended restored; intermediate cleanup acknowledgements failed, so the
fixture is not a pass. No fault or overlap counters were cleared. Further
writing regressions stopped. Item 3 requires a bounded hash workload and a
matching provider wait before re-verification; S9 remains owed. See the
[failed hardware gate](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_HARDWARE_FAILURE_2026-10-02.md).

**Login correction prepared (press62, 2026-10-02):** press61 failed its
scan budget on the controller: maximum 32,136 µs against the 10 ms task,
771 overlaps and minor fault bits 64. No further login writes were issued
after reading that failure. Press62 moves the first 256 SHA-256 hashes to the
gateway; the PLC computes the final hash and compares its own private
registration before assigning its registered level. Stored hashes, salts and
all 257 hashes remain unchanged. The transmitted preimage is a credential;
the PLC wipes it immediately after sampling. Sending the stored hash itself
does not authenticate. Every block advances through ten scans with at most
eight rounds per scan. The accelerated controller work has 100 ms of nominal
scheduling; actual scan cost and end-to-end latency still require hardware proof.
Native PIN clients retain the full bounded path and its 35.7-second budget.
State V3 adds the result sequence so the generic HMI ignores older outcomes.
The subsequent read-only controller/gateway observation matches the press62
public contract and reports a successful admin login with healthy task metrics.
The development HMI server was found serving the old one-read login
implementation and restarted from current source. The owner's actual HTTPS
release was subsequently identified and updated separately, as recorded below.
The subsequent hardware fixture passes the access gate; S9 remains owed. See the
[served-client correction](../../../Specification/AllenBradley/Evidence/AB_PHASE6_HMI_STALE_CLIENT_FIX_2026-10-02.md).
The final release Web folder is `C:\work\press62_hmi_web_final`.
ContentHash is now `10AEDC3FFD6B5DC1`;
manifest capacity remains 79,992 bytes. See the
[split-login evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_SPLIT_FIX_2026-10-02.md).

**Controller access verified (press62, 2026-10-02):** the guarded fixture passes
16/16, including bad PIN handling, logout, roles, native mailbox impersonation
refusal, idle timeout, the accepted write's actual value and the denied actor's
audit. All changed settings are restored and fixture inputs are disarmed.
This run also corrected the gateway's handling of access denials before set
dispatch and the fixture's sequence allocation for native probes. The PLC
artifact remains byte-identical to press62; no new download is required.
The owner must restart the running gateway to load the broker correction.
The next Phase 6 item is data-class permissions; S9 and physical retention
remain owed. See the
[hardware evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_ACCESS_ON_HARDWARE_2026-10-02.md).

**HTTPS HMI release updated (2026-10-02):** the owner's Chrome URL is
`https://press.localhost/`. Caddy served the September 29 release from
`FraktalCore/HMI/build/web`; restarting the development server on port 5555
did not replace it. The tested final release is now deployed into that static
root, with all 42 resources verified by SHA-256 and the old directory retained
at `C:\work\phase6_hmi_https_backup_20261003_024143`. Chrome needs
`Ctrl+Shift+R` to load the corrected login wait and result-sequence handling;
the owner subsequently confirmed that login now works. No controller download
or gateway restart is required for this client deployment. See the
[HTTPS deployment evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_HMI_HTTPS_DEPLOYMENT_FIX_2026-10-02.md).

**HTTPS reboot recovery (2026-10-03):** after Windows restarted, the owner's AB
gateway listened on 127.0.0.1:8099 but Caddy was stopped and nothing listened
on 443. The existing proxy was started without changing its configuration,
credentials or the Web release. A hidden, idempotent launcher at
`C:\work\caddy\Start-WebProxy.ps1` and the current user's
`Fraktal Press HTTPS.lnk` Startup shortcut now start Caddy at Windows sign-in.
The shortcut action is tested; an actual new sign-in is not. Certificate
hostname/trust verification passes and unauthenticated HTTPS returns 401;
all 42 Web resources equal the press64 release. No controller operation or
gateway restart was performed. See the
[recovery evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_HTTPS_REBOOT_RECOVERY_2026-10-03.md).

**Phase 6 item 4 is confirmed on hardware (press64, 2026-10-02).**
The press and station template declare `public` and `commissioning` data classes.
The PLC resolves each value's effective read/write level, applying immutable
minimums and requiring ADMIN for an unknown class or corrupt level. Station
number uses `public`; air-pressure calibration has an ENGINEER write minimum.
Class edits use ACCESS_POLICY. Configuration metadata remains visible while
unreadable values are blank. Writes, captures and every set load/export record
are checked before any value commits or export line returns; save/delete retain
CONFIG_SET alone. The generic HMI receives the PLC's levels and class table.
Policy is a separate retained tag; AccessState V3 and existing registrations
remain unchanged. Manifest major 4 appends class/minimum capability metadata;
AccessAudit V3 appends the refused value and required level. The manifest is
80,760 bytes, Fields 563/768 and Localization 565/768. `C:\work\press64.L5X`
reproduces byte-for-byte. The owner downloaded it and restarted the gateway;
full manifest readback is coherent and equal, with the repeat taking 171.458 ms.
The guarded data-class fixture passes 18/18, access 16/16, capture 10/10,
sets 17/17, S3 6/6, parity 25/25 and Phases 1–5 7/7, 6/6, 8/8, 11/11 and 25/25.
Maximum scan is 5,259 microseconds against the 10,000-microsecond period;
overlaps and fault bits remain zero. Values, class/action policy, timeout and
mode/style are restored, every fixture input is cleared, and the owner's prior
admin session is restored. The tested HMI release is deployed at the actual
HTTPS root. Alarm shelving is next; physical retention and the write-enabled
S9 claim remain owed. See the
[hardware evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_DATA_CLASSES_ON_HARDWARE_2026-10-02.md)
and [build evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_DATA_CLASSES_BUILD_2026-10-02.md).

**Phase 6 item 5 passes on hardware (press67, 2026-10-03).**
The shared alarm log now routes SHELVE_ALARM/UNSHELVE_ALARM when the controller
access provider is enabled, including the station template. The PLC resolves
the HMI's source+description identity uniquely, checks ALARM_SHELVE and the
registry's shelvability/category, and refuses safety, unrationalized or closed
events. Shelves use whole seconds, refuse durations below one second, cap at
eight hours and expire on the binding's periodic task-duration clock. Every
shelf, unshelf and expiry logs to the existing history ring. Control, blocking
and release reports are unchanged. AlarmActive/Ring V2 append the consumed
Shelved flag; the countdown is private. The existing generic HMI consumes it.
Press65 failed owner Verify for memory in `FRK_PressHmiMailbox`. Press66
replaced expanded character comparisons with bounded native manifest lookups,
but its owner download reached linking and then failed **Out of memory in the
controller**, cancelling the download. Press67 also shares configuration audit
and Start release routines, and sizes Fields/Localization reserve to each
declaration in 64-row blocks, with 64 rows of headroom and the same 768-row
ceilings. Compared with press66, declared data drops by 12,288 bytes and total
ST by 235 statement terminators. Both trends are below successful press64.
The four-user ceiling, alarm capacities, command guards and audit data remain.
The generator now reports per-routine code growth and declared data; compare
each remaining implementation with the last successfully downloaded artifact using
`fraktal_ab_generated_size.py --baseline`. These are trends, not compiled bytes.
`C:\work\press67.L5X` reproduces byte-for-byte: ContentHash `832DD0D0F260872B`,
revision 8596944, manifest major 4 / 68,472 bytes, Fields 565/640 and
Localization 570/640. Live readback and changed command behavior now pass on
serial 7036B510: shelving 15/15, data classes 18/18, access 16/16, capture 10/10,
sets 17/17, parity 25/25 and Phases 1–5 7/7 · 6/6 · 8/8 · 11/11 · 25/25.
Final repeat manifest read is coherent and equal in 154.664 ms; S3 passes 6/6
before and after, with maximum scan 5,279 µs against 10,000 µs, zero overlaps
and zero fault bits. The original admin session, policy, timeout, configuration,
mode/style and fixture inputs are restored; no active shelf remains. Exact target
identity was checked before each primitive write. No agent download, gateway
restart, provisioning or counter clear was performed during verification.
Press67 is now the last verified loaded artifact and the baseline for further
memory comparisons. Generated counts do not measure compiled/free memory.
S9 is next; its write-enabled claim and physical retention remain owed. See the
[hardware evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SHELVING_ON_HARDWARE_2026-10-03.md),
[link memory correction evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SHELVING_LINK_MEMORY_FIX_2026-10-03.md),
[previous memory correction](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SHELVING_MEMORY_FIX_2026-10-03.md)
and [initial build evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_SHELVING_BUILD_2026-10-03.md).

**Phase 6 item 6 is prepared offline (press68, 2026-10-03).** The native V3
request adds one bounded 89-DINT frame: one unfragmented write at 500 bytes,
then Sequence last. Its 312-byte aggregate ASCII argument bound is derived
from the native path and pinned serializer; large ConfigSet records stay staged.
CPS sampling, schema/length/sequence checks and frame wiping share one generated
loop. The generic HMI paths and PLC operation ordinals are unchanged. The
versioned native profile now participates in ContentHash so an incompatible
gateway refuses the old build. The new hash is `7A9B9A8B59EEFD16` / revision
8035226; the manifest remains 68,472 bytes, Fields 565/640 and Localization
570/640. Relative to loaded press67: +1,088 declared data bytes, +4,119 ST source
bytes and +63 statement terminators. Four users remain the ceiling; native fit
still requires owner Verify and a completed link/download.

The shared repository suite consumes TC3 contract paths and the production AB
projection/gateway snapshot. New tests cover unsigned wrap, burned interrupted
sequences, cancellation serialization, incomplete native frames, quality and
timestamps, coherent manifest caching and native read tiers. The original S9
coherence fixture remains separate. After the owner's download confirmation,
use `fraktal_ab_s9_write_execute.py --execute-fixture` for the five native replay
boundaries and session/timeout restoration, and `fraktal_ab_s9_read_execute.py`
for current-station read cost and six viewers sharing one reader. Keep the HMI
idle during the exclusive write fixture. The old Phase 0 freshness/budget
numbers do not transfer to this larger station. **S9 and physical retention
remain owed.** See the [offline evidence](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_OFFLINE_2026-10-03.md).

**S9 read-only preflight passes (2026-10-03).** Press68's complete manifest
matches; its fixture is stopped and ready, the current session is restorable,
and no mailbox request is pending. Thirteen live discovery/quality/timestamp/
reconnect checks and S3 6/6 pass. Current-code steady reads have a 192.702 ms
median, fresh mailbox reads about 17 ms, and six viewers share one native read.
The owner reports minimal browser mode-change improvement and asks to move on.
No PLC memory is added. The guarded write fixture still awaits the owner's
completed-download confirmation and an idle HMI; the write-enabled claim,
current freshness/poll declarations and physical retention remain owed. See
the [read-only record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_READ_ONLY_PREFLIGHT_2026-10-03.md).

**S9 native mailbox verification passes (press68, 2026-10-03).** The owner
confirms the completed download. All 17 native replay/frame checks pass on serial
7036B510, including the five replay boundaries, signed/uint32 wrap, premature
commit, reversed segments and public-frame wiping. All eleven regression
suites and independent restoration pass. The original anonymous session,
timeout, configuration, policies, AUTO/CONTINUOUS mode and ten zero fixture
inputs are restored; no pending request or active shelf remains. S3 passes
6/6 before and after, with zero overlaps and fault bits. The Phase 5 downtime
fixture now measures actual native acquisition intervals with the same 250 ms
allowance; slow-read and incorrect-accounting tests and both mutants pass.
The failed attempts and their successful recovery are retained.

Press68 is now the successful memory baseline; this verification adds zero
PLC memory and regenerates byte-identically. No new import/download is needed.
The four-user ceiling remains. Its V3 frame contract is verified on this bench;
the following freshness work supersedes the previously owed software leg.
Physical retention is separately owed. Further mode-latency tuning remains
owner-deferred. See the [native hardware record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_NATIVE_MAILBOX_2026-10-03.md).

**Owner parameter-retention observation and model workflow (2026-10-04).**
The owner confirms that minimum air pressure, edited from 450 to 451 about nine
hours earlier, survives a PLC power cycle; the earlier exact-serial preflight
also reads 451. This confirms that parameter's retention by owner observation,
alongside the earlier admin credential observation. Saved sets, other values/
accounts and download/upgrade retention remain separate checks. The proposed
Station number test was not executed and is redundant for this observation.
On loaded press68, new models require a declaration/catalog change and owner
deployment. Configuration → Model data edits existing models. A Model set names
a snapshot, not a new catalog entry; save/export works and model-set load is
deliberately refused until recipe/changeover integration in both AB and TC3.
See the [owner record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_OWNER_AIR_PRESSURE_RETENTION_2026-10-04.md)
and [model workflow](../../../Specification/Guides/AB_NEW_PROJECT_GUIDE.md#adding-a-model-to-the-current-ab-application).

**Configuration regression repair (2026-10-04).** A slow Parameter sets request
blocked complete snapshots on its own WebSocket, causing the freshness gate to
remount the operator shell. Bounded multiplexing now lets current reads proceed
while existing locks serialize native reads and mailbox transactions. Queued
commands are canceled on disconnect/overload; active native work is drained
without replay. The generic HMI retains published model metadata until its exact
manifest replacements are hydrated. No PLC change, download or memory growth.
Full AB 1,541, HMI 478 (7 expected skips), shared TC3/AB 79 and root 33 tests pass;
analyzer and release Web build pass. The client is deployed and HTTPS-verified.
The owner restarted the gateway; read-only probes verify the concurrent
handler is active and D6 passes on all three health routes. The owner confirms
Parameter sets stays open after the Chrome refresh and ten-second check. See the
[browser acceptance](../../../Specification/AllenBradley/Evidence/AB_PHASE6_CONFIGURATION_OWNER_ACCEPTANCE_2026-10-04.md),
[activation record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_GATEWAY_ACTIVATION_2026-10-04.md)
and the
[configuration record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.md).

**S9 live acceptance passes on press68 (2026-10-03).** After the owner's gateway
restart and Chrome refresh, the corrected repository remains LIVE for 60 seconds
with 121 complete updates and 224 detail batches; maximum update gap is 790 ms.
Three fresh connections, exact-serial 68,472-byte manifest readback and S3 6/6
pass. The owner confirms that the browser loop is gone; HTTPS serves the expected
client hash. This closes S9 for this named write-enabled deployment together with
the prior native 17/17 vector, eleven regressions/restoration and shared contract
75/75. Verification is read-only and adds zero PLC memory. No download is needed.
Physical retention, the separate historical S1 clock probe, TC3 native segmented
transport and D6 remain separate work. Another station still proves its own fit,
budgets and writable deployment. See
[live acceptance](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_LIVE_ACCEPTANCE_2026-10-03.md).

**S9 HMI detail-read loop correction (2026-10-03).** The restarted gateway's
complete samples were current, but the HMI waited for all 2,621 detail leaves
before accepting a sample. Six targeted batches took 1.95–2.42 s and crossed
the 2 s Good deadline. The generic repository now publishes complete samples
independently, reads detail in bounded background batches, and ages each batch
separately. Scope/discovery changes and stale station data discard pending
detail. Freshness limits are unchanged; there is zero PLC growth or download.
The shared suite passes 75/75 and HMI 463 tests (7 expected skips), with analyzer
and release build clean. The previous client fails the new regression test.
The corrected client was HTTPS hash-verified. At that stage S9 remained open:
the gateway had stopped before the live probe. The acceptance above supersedes
that pending state. See the
[loop correction](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_LOOP_FIX_2026-10-03.md).

**S9 freshness source and read-only budget pass (2026-10-03).** `ReadBudget` in
the application owns 500 ms polls, 250 ms cache, 1,000 ms slow heartbeat,
2,000 ms Good / 3,000 ms expiry and a 4,000-byte read connection. The gateway
and generic HMI age samples monotonically even during a blocked read; partial
Ack traffic cannot renew station health, and mutation delivery re-checks it.
The shared suite passes 71/71, full AB discovery 1,535 tests, full HMI 459 tests
(7 expected skips), analyzer clean, five expiry mutants killed. Read-only native
steady/six-viewer maxima are 199.521/224.933 ms; S3 is 6/6. Press68 and template
remain byte-identical, with zero PLC growth. The release Web client is served
and HTTPS hash-verified. Live activation was pending at that stage and now passes
in the acceptance above. No new download is needed. See the
[freshness record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_2026-10-03.md) and [final HMI follow-up](../../../Specification/AllenBradley/Evidence/AB_PHASE6_S9_FRESHNESS_CLEANUP_2026-10-03.md).

**Press67 read-only readiness (2026-10-03):** exact serial 7036B510 serves the
whole 68,472-byte manifest, coherent and equal to the declaration, in 148.642 ms;
Fields/Localization are 565/640 and 570/640. The gateway is ready. S3 passes
6/6 with maximum scan 5,238 µs, zero overlaps and zero fault bits; shelving
preflight passes 4/4 with the press stopped and a restorable level-4 session.
This preceding snapshot performed no fixture write. The subsequent authorized
hardware run above establishes the changed command behavior and restoration.
Manifest identity alone does not prove command logic. See the
[readiness record](../../../Specification/AllenBradley/Evidence/AB_PHASE6_PRESS67_READINESS_2026-10-03.md).

The gateway/repository adapter and the generic HMI are **no longer among them** -
both are built and run against the bench, and on 2026-09-24 the unmodified HMI
commanded the press from a browser (see the gateway section below). What remains
unexercised there is the packaged installer path and anything past loopback.

The current Phase 0 workstation target is `192.168.100.89`, historically from
host adapter `192.168.100.99/24`. FactoryTalk Linx 6.50 browsed it through the
point-to-point alias `Fraktal_AB` on 2026-08-13; **neither still holds on the
2026-09-06 bench workstation**, where the host address is `192.168.100.123` and
`FTLinxCfgIETool.exe /Browse` fails with `status is 2` for every path tried,
including a driver Studio can see. Reachability is unaffected — Studio's Who
Active browses USB and every probe speaks EtherNet/IP directly — see the S16
execution record. Historically, direct CIP identity and symbolic reads also
pass. Studio 5000 v33 positively connected through
`Fraktal_AB\192.168.100.89`, but Studio and SDK read-only uploads over Ethernet
timed out. After USB was reconnected, Studio uploaded successfully through
`Backplane\16` with zero errors and warnings; the upload-derived v33 L5X also
passed a canonical SDK conversion round trip, and Studio's offline
**Verify Controller** completed with zero errors and warnings. The
Ethernet/SDK online issue remains open. With the user's explicit authorization
and all I/O disconnected, a generated memory-only v33 fixture was verified,
downloaded through USB to the serial-matched controller, returned to Remote Run,
and exercised over EtherNet/IP. Controller/program-scoped scalars, arrays
through a fragmented 4 KiB `DINT[1024]`, STRING, UDT, PLC-derived results,
External Access, liveness, and cleanup all passed. Bounded connection-size,
reconnect, timeout-recovery, and concurrent-reader tests also passed. One fixed,
authorized operation corrected the fixture wall clock from 1998 to host UTC;
the fixture reports PTP disabled/unsynchronized and Fraktal preserves that
quality explicitly. No firmware, fault-clear, network-configuration, or
physical-I/O operation occurred. S1 is PASS. S2 then imported, verified,
downloaded and executed a memory-only eight-level nested-AOI fixture: one UDT
`InOut`, STRING `InOut`, atomic Input/Output, private AOI storage, member
External Access, cleanup, and exact target binding all passed. Studio v33 fixed
the platform boundaries at 64 InOut parameters and 16 invocation levels;
Fraktal's generated nesting ceiling is eight. S2 is PASS. A separate
invalid-ST fixture was correctly rejected by Studio Verify with two errors.

S11 then replaced that fixture, under fresh explicit authorization and with all
I/O disconnected, with a memory-only fixture generating **both** AB §3.5
execution forms from one graph declaration: the ST reference-form sequence AOI
nested by an owner AOI, and a program-owned native SFC chart driven by the
generated JSR/SFR wrapper. The generated chart imported cleanly, passed Studio
v33 **Verify Controller** with zero errors and warnings, and round-tripped
canonically. On the controller the two forms walked the identical step trace in
an identical four scans; the root module AOI ran unconditionally and always
ahead of sequence intent; the command/result loop measured exactly one scan; the
simultaneous branch ran one numbered leg per Core branch; and `SFR` reset re-ran
the chain identically. **S11 is PASS and S4's native-SFC family is settled with
it.**

S12 then measured the type map on the same target. `TIME`, `TIME32` and
`LREAL` are unavailable on this controller — the first two abort the import,
the third is rejected by Studio Verify after the SDK had accepted it — and
`LINT` is transport-only, since it declares and round-trips but no arithmetic
form compiles. Duration therefore binds to a range-checked `DINT` of
milliseconds. The public UDT's CIP payload was measured member by member: 24
bytes with a 24-byte array stride, four of them trailing padding forced by the
`LINT`'s alignment. Integer overflow wraps two's-complement, and a NaN bit
pattern transports faithfully while Logix ST's `NaN <> NaN` evaluates false, so
generated code must test NaN by bit pattern. **S12 is PASS.** The S12 fixture
was later replaced: S9 downloaded its coherence fixture on 2026-08-14, and the
controller has held that clean S9 fixture in Remote Run ever since. Its identity
and Remote Run state were re-confirmed read-only on 2026-09-06
([`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md) §7).

A later Studio-only v38 exploration on a disposable `5069-L310ER` revision
38.11 project imported all 28 declaration/use probes and ran Verify on each;
26 were clean, while the two duration cases correctly rejected an untyped
integer operand. It exposed family-specific differences, but the SDK licence,
unchanged v33 regression, and SDK-import evidence are still missing, so it is
explicitly not a second S12 baseline and does not change the frozen v33 contract.

S4 then closed offline with a representative construct matrix: two task types
with their schedules, ST, RLL and SFC routines side by side, nested and tabular
record shapes, a sized `StringFamily` type, a generated `Constant` tag, and an
AOI declaring all three scan flags with their routines. It imports `0/0`,
verifies `0/0`, round-trips canonically, and passes a **generated-vs-exported
construct census** — a check the canonical comparator structurally cannot make,
since it compares two documents that have both already been through Studio. Two
rules came out of it: every generated routine must be reached from its main
routine, or Studio warns about dead code; and every attribute must be stated,
because an omitted one comes back as Studio's default. **S4 is PASS, and with
it R2 closes.** S15 remains open on the unattended-gate and Ethernet questions.

**R3 then closed offline.** The six logical contracts — registry, manifest,
value envelope, mailbox, repository negotiation and the HostEvents ring — are
frozen at version 1 in
[`Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json`](../../../Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json),
the one artifact a generator, a gateway and a gate all read. Part III's prose
stays normative and `tools/check_ab_contracts.py` fails the build when the two
drift, when a field uses a type this controller does not have, or when a
capacity claims a number without evidence.

S7 then measured the manifest itself. A 43,728-byte manifest at candidate
capacities — 4 roots, 128 modules, 512 fields, 256 localization keys and the
rest — read completely and coherently in **293 ms** at S1's conservative
500-byte connection and **62 ms** at 4000 bytes, with a **~32 ms header-only
poll** in steady state. **One bounded manifest fits; no per-root split is
required.** Reading tables as arrays of UDT rows batches into far fewer round
trips than one monolithic tag, so S1's 4 KiB fragmented figure is a worst case
for that access pattern rather than the rate a manifest reader sees. Eight of
the nine `FRK_MAX_*` capacities are now resolved at the sizes actually
measured; `FRK_MAX_MAILBOX_ARGUMENTS` remains S9's.

The default controller communication path is EtherNet/IP explicit messaging
(CIP symbolic access) through the Fraktal gateway. OPC UA is an alternative
projection, not a prerequisite for base Fraktal/AB conformance. S1 selected
hash-pinned pylogix `1.1.5` as the initial private PLC-facing adapter; it shall
sit behind a versioned, allow-listed gateway boundary and shall not expose an
arbitrary CIP `Message()` surface to the HMI.

Start with:

- [`Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`](../../../Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md)
  for the complete status-marked inventory of every Studio 5000, FactoryTalk
  Linx, SDK, EtherNet/IP, Python, UI Automation, and repository tool interface
  used or discovered, plus the unfinished S11 checkpoint;
- [`Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](../../../Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md)
  for the verified fresh-chat paths, tools, commands, and safety boundaries used
  to access Studio 5000, FactoryTalk Linx, and the isolated PLC;
- [`Specification/AllenBradley/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md`](../../../Specification/AllenBradley/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md)
  on the Windows 10 Studio 5000 workstation;
- [`Specification/AllenBradley/Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md)
  for the completed R0 decision record;
- [`Specification/AllenBradley/Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md)
  for the completed platform baseline;
- [`Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md)
  for the completed S1 CIP data/time/transport evidence and initial adapter
  decision;
- [`Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md)
  for the completed nested-AOI, InOut/access, target-limit, and signature
  upgrade evidence;
- [`Specification/AllenBradley/Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md)
  for the completed sequence-execution, scan-ordering, one-scan-latency,
  simultaneous-branch, `SFR` re-entry, and ST/SFC parity evidence, plus the
  native-SFC chart fidelity result;
- [`Specification/AllenBradley/Evidence/AB_S12_TYPE_MAP_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S12_TYPE_MAP_EVIDENCE.md)
  for the completed type-acceptance matrix, the measured CIP UDT layout and
  stride, and the overflow/NaN/string/array/duration rules that bind generated
  code;
- [`Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md`](../../../Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md)
  for the explicitly provisional Studio-only 5380/v38 declaration/use matrix
  and the acceptance work still blocked by the SDK licence;
- [`Specification/AllenBradley/Evidence/AB_S7_MANIFEST_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S7_MANIFEST_EVIDENCE.md)
  for the measured manifest size, per-table read cost at two connection sizes,
  coherence and revision-change results, and the resolved capacities;
- [`Specification/AllenBradley/Evidence/AB_S9_COHERENCE_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S9_COHERENCE_EVIDENCE.md)
  for the snapshot-coherence result: the guard never accepted a torn read at any
  mutation rate, tearing was directly observed unguarded, and retry converges
  only when the mutation interval exceeds the guarded read window;
- [`Specification/AllenBradley/Evidence/AB_S8_SECURITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S8_SECURITY_EVIDENCE.md)
  for the measured absence of CIP Security on this controller and the allow-list
  audit;
- [`Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md`](../../../Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md)
  for the settled security and repository/mailbox decisions — read this before
  starting a new AB project, because it fixes the read-only default, the write
  switch, and the recommended v37+ baseline;
- [`Specification/AllenBradley/Evidence/AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md)
  for the two declarations those decisions deferred: the bench's zone/conduit
  layout with a declared **SL-T 1 / SL-C 0** (and why SL 2 is unreachable on this
  family rather than exceptable), and the reference station's tier poll periods,
  freshness thresholds, reader budget and manifest-mutation convergence limit;
- [`Specification/AllenBradley/Evidence/AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md)
  for the S16 declaration: the Core §6.1 handshake and §6.2 mode chain fit one
  context UDT and two AOIs with no runtime base structure invented, which is the
  finding that lets the spike proceed. It carries the import package and the
  nine-phase execution matrix for the licensed v33 workstation, and it records
  the Core §6.1 ambiguity it had to resolve — whether a HELD command may time
  out — as something Phase 3 must settle rather than let each binding guess;
- [`Specification/AllenBradley/Evidence/AB_S16_EXECUTION_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S16_EXECUTION_EVIDENCE_2026-09-06.md)
  for that package executed on the licensed v33 bench: the real generated L5X
  hash the declaration deliberately withheld, SDK import `0/0`, Studio v33
  Verify `0/0`, an identical canonical round trip, and all nine matrix phases
  passing identically on three consecutive runs. It also records why the first
  runs were not evidence — the executor assembled each observation from 25
  separate reads of a fixture mutating every 10 ms, so phases passed on one run
  and failed on the next until the context was read in a single request — and
  that two automated download attempts crashed Studio v33 with two different
  faults and no root cause, leaving the successful download a manual one;
- [`Specification/AllenBradley/Evidence/AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md)
  for **R4**: a fresh clone regenerating every fixture from an SDK seed and
  clearing import, canonical round trip, census and Studio v33 Verify at `0/0`
  on all nine legs — including the proof that canonical form is stable across
  seeds, which is what makes every hash in every earlier record checkable. It
  itemises what still cannot run unattended rather than rounding up;
- [`Specification/AllenBradley/Evidence/AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md)
  for **R5**: the disposable reference suite — two reference types with the
  module type instantiated twice — executed on the named bench for nine
  machine-readable rows, all passing on three consecutive runs with the
  controller's own cross-talk counter at zero. It records why the CI path is
  named isolated hardware rather than Echo, and why the download step is an
  authorized manual operation;
- [`Specification/AllenBradley/Evidence/AB_R6_SECURITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R6_SECURITY_EVIDENCE.md)
  for **R6**: the zone/conduit layout and declared Security Level, the External
  Access allow-list audit actually run against both downloaded fixtures, the
  three-state client identity model, secret handling, and the update lifecycle
  — with CIP Security, SL 2 and writes each named as **not** claimed;
- [`Specification/AllenBradley/Evidence/AB_LADDER_EXECUTION_PARITY_2026-09-07.md`](../../../Specification/AllenBradley/Evidence/AB_LADDER_EXECUTION_PARITY_2026-09-07.md)
  for the three-form press result and **the first executing ladder sequence on
  this bench** - S4 proved RLL round-trips, never that one runs. It carries the
  trace comparison, the two Logix constraints the graph was *not* bent to fit,
  and the defect only hardware could find: a chart whose JSR/SFR wrapper fired
  on a level its own first step kept true, so it reset itself every scan and
  never advanced. It also records three faults in the measurement itself, and
  why the trace window is now closed by the machine rather than by the observer;
- [`Specification/AllenBradley/Evidence/AB_PHASE4_RUNTIME_BASE_AND_PRESS_DEMO_2026-09-07.md`](../../../Specification/AllenBradley/Evidence/AB_PHASE4_RUNTIME_BASE_AND_PRESS_DEMO_2026-09-07.md)
  for **Phase 4**: what the generator emits, the step-graph comparison against
  the TwinCAT press demo with its two behavioural divergences named rather than
  absorbed, the fifteen-row bench matrix, and the four defects found on the way
  — including the one only hardware could find, where adopting a child's fault
  never released it and pinned the module in a state nothing could clear;
- [`Specification/AllenBradley/Evidence/AB_S9_RECONNECT_QUALITY_TIMESTAMP_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S9_RECONNECT_QUALITY_TIMESTAMP_2026-09-06.md)
  for the measured reconnect budget, the two distinct bad-path quality codes and
  what each obliges a reader to do, and why a value's timestamp is the gateway's
  read time carrying `TimeSynchronized = FALSE`; it also records the wall-clock
  read the S1 fixture guard correctly refused rather than being widened;
- [`Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md)
  for the second engineering PC surveyed on 2026-09-06 — **read it before
  planning any v33 or SDK work on a new machine**, because that PC has Studio
  v37/v38 with no v33, SDK `2.01.974` rather than 2.02, no .NET SDK, and no
  issued `LDSDK.EXE` activation;
- [`Specification/AllenBradley/AB_R3_FROZEN_CONTRACTS.md`](../../../Specification/AllenBradley/AB_R3_FROZEN_CONTRACTS.md)
  and [`Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json`](../../../Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json)
  for the frozen version-1 contracts, what is deliberately still a hole, and
  which spike owns each one;
- [`Specification/AllenBradley/Evidence/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md)
  for the current disposable SDK Build and canonical L5X result;
- [`Specification/AllenBradley/Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md)
  for the authorized v33 fixture generation, Studio Verify/download, physical
  EtherNet/IP execution matrix, access-control results, and rollback state; and
- [`Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md`](../../../Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md)
  plus [`Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md`](../../../Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md)
  for spike and phase order.

Pre-gate tooling:

- [`tools/Fraktal.Ab.OfflineProbe`](tools/Fraktal.Ab.OfflineProbe/README.md)
  opens disposable projects through the installed Logix Designer SDK, reports
  the saved communication path, and can save a new disposable ACD or L5X while
  proving that the input was unchanged. Its `--create-seed` mode creates the
  empty v33 controller skeleton every generator consumes, so the whole chain
  regenerates from a clean checkout. It contains no controller-changing
  operation.
- [`tools/fraktal_ab_eip_probe.py`](tools/fraktal_ab_eip_probe.py) performs a
  targeted read-only EtherNet/IP identity and TCP/IP Interface Object probe. It
  exposes only `ListIdentity` and fixed `Get_Attribute_Single` reads for the
  TCP/IP Interface and Time Sync objects, can require the expected controller
  serial, and reports bounded identity latency.
- [`tools/fraktal_ab_symbolic_read_probe.py`](tools/fraktal_ab_symbolic_read_probe.py)
  performs explicitly named Logix symbolic reads and reports only status, value
  shape, and timing. Values are always redacted; the pinned temporary-client
  dependency is in [`tools/requirements-phase0.txt`](tools/requirements-phase0.txt).
- [`tools/fraktal_ab_phase0_fixture.py`](tools/fraktal_ab_phase0_fixture.py)
  transforms only a fresh empty v33 `1769-L24ER-QB1B` full-project L5X into the
  disposable memory-only execution fixture. It refuses overwrite, inhibits the
  embedded I/O module, disables task output updates, and rejects physical-I/O
  operands.
- [`tools/fraktal_ab_phase0_execute.py`](tools/fraktal_ab_phase0_execute.py)
  is the fixed physical execution vector. It requires the expected serial and an
  explicit arm flag, fingerprints the exact fixture, exposes no arbitrary tag or
  value input, and cleans every writable fixture input before returning.
- [`tools/fraktal_ab_transport_budget_probe.py`](tools/fraktal_ab_transport_budget_probe.py)
  is a fixed, read-only large-array/reconnect/timeout/concurrency probe. It caps
  every workload, requires the expected serial and fixture fingerprint, closes
  every client, and redacts values.
- [`tools/fraktal_ab_time_probe.py`](tools/fraktal_ab_time_probe.py) reads the
  controller wall clock by default. Its only state-changing path requires
  `--set-to-host`, exact serial and fixture checks, and can invoke only
  `SetPLCTime(dst=0)`. It recognizes only the exact Phase 0 data or S2 nested-AOI
  fixture fingerprints.
- [`tools/fraktal_ab_s2_fixture.py`](tools/fraktal_ab_s2_fixture.py) and
  [`tools/fraktal_ab_s2_execute.py`](tools/fraktal_ab_s2_execute.py) generate and
  execute the exact memory-only nested-AOI/access fixture. The execution tool
  exposes no arbitrary tag/value path and cleans its two writable inputs.
- [`tools/fraktal_ab_s2_signature_variant.py`](tools/fraktal_ab_s2_signature_variant.py)
  and [`tools/fraktal_ab_s2_inout_limit_fixture.py`](tools/fraktal_ab_s2_inout_limit_fixture.py)
  generate the offline-only AOI upgrade and 64/65 InOut compiler cases.
- [`tools/fraktal_ab_s11_fixture.py`](tools/fraktal_ab_s11_fixture.py) generates
  the memory-only sequence-execution fixture, emitting the ST reference form and
  the program-owned native SFC chart plus its JSR/SFR wrapper from one graph
  declaration, and declaring the three required controller SFC settings.
- [`tools/fraktal_ab_s11_execute.py`](tools/fraktal_ab_s11_execute.py) is the
  fixed S11 execution vector. It requires the exact serial, fixture fingerprint
  and arm flag, writes only `FRK_S11_Command` and `FRK_S11_ResetRequest`, drives
  one run plus one `SFR` re-entry run, and restores both inputs.
- [`tools/fraktal_ab_s16_fixture.py`](tools/fraktal_ab_s16_fixture.py) generates
  the memory-only command-handshake fixture: one `DINT`-only context UDT and two
  AOIs — a module carrying the Core §6.1 handshake over a simulated plant, and a
  mode owner running an AUTO step chain and a MANUAL behavior over it. A test
  fails the build if the fixture grows a recipe, manifest, registry, mailbox or
  any other runtime-base structure; fixtures stay disposable by construction.
- [`tools/fraktal_ab_s16_execute.py`](tools/fraktal_ab_s16_execute.py) is the
  fixed S16 nine-phase vector. It requires the exact serial, fixture fingerprint
  and arm flag, writes only the five named command tags, restores all five in a
  `finally` block, and fails closed — a held condition that raises `Error`, a
  broken call order, or a command/result latency other than one scan each fail
  the run rather than being reported as a pass. It reads the whole context in
  **one** request and unpacks it against the declared member layout: the fixture
  mutates every 10 ms, so a per-member sweep spans tens of scans and reports a
  state the controller never held — the tearing S9 measured, and the reason a
  phase could pass on one run and fail on the next with nothing changed.
- [`tools/fraktal_ab_declaration.py`](tools/fraktal_ab_declaration.py) is the
  declaration: the committed source an application is emitted from, and the
  rules that refuse a bad one. Each S16 finding is a rule here only because it
  can reject something - unnamed held reasons, timeouts that are not whole task
  scans, a ParCfg record that does not lead with `SchemaVersion`, a condition on
  an undeclared input, a transition to a step that does not exist.
- [`tools/fraktal_ab_generate.py`](tools/fraktal_ab_generate.py) turns a
  declaration into contract UDTs, one module AOI per declared type, the mode
  owner, the routine and the L5X. It asserts at emit time that the task it
  writes carries the declared period the millisecond timeouts were converted
  from, that no public UDT carries a `BOOL`, and that nothing it emitted names a
  physical I/O operand.
- [`tools/fraktal_ab_manifest.py`](tools/fraktal_ab_manifest.py) emits the
  controller-resident manifest from that same declaration, so a client can
  discover the station from the controller rather than from an L5X on disk. It
  describes the declared graph **once, rendition-agnostic**: the field list comes
  from `publishable_tags`, so the rendition selector and any tag that exists only
  because of how one rendition is implemented are absent by construction, and
  declaring AUTO in one language or three produces the identical manifest. Two
  things it learned the hard way are enforced rather than remembered: Logix
  stores an ASCII string only when it is quoted and `$`-escaped, and a key that
  does not fit the published string fails the build instead of being truncated
  into a name it shares with another path.
- [`tools/fraktal_ab_manifest_read.py`](tools/fraktal_ab_manifest_read.py) reads
  the manifest back off a controller and requires every published row to equal
  the declaration it was generated from. It is read-only by construction - there
  is no write path in the file - and its serial guard is required rather than
  optional. It reads array tags with an explicit element count, because an array
  read without one returns row zero and **succeeds**: the first bench run took
  the manifest apart in 526 requests and 1.5 seconds before that was noticed,
  and it was a defect here, not a controller limit. The run records which path
  each table took, so a fallback announces itself rather than costing 500 quiet
  requests.
- [`tools/fraktal_ab_projection.py`](tools/fraktal_ab_projection.py) projects a
  controller into the **transport-neutral snapshot document the HMI's mapper
  already consumes** - a flat `{browsePath: value}` map in which a module is
  anything publishing `Status/Name` and `Status/ModuleType`, with parentage from
  the dotted identity. The generic HMI therefore needs no AB screens and no AB
  repository. It is fail-closed on Core 3.10 grounds: an invalid, truncated or
  disagreeing manifest refuses the whole projection, because a half-drawn plant
  is a worse answer than a refusal. What this binding cannot publish is listed in
  `absent` with a reason rather than left out, since the mapper coerces a missing
  key into a default and silence would render as data.
- [`tools/fraktal_ab_gateway.py`](tools/fraktal_ab_gateway.py) serves that
  projection to the generic HMI over the `fraktal.opcua.gateway.v1` WebSocket
  protocol the HMI already speaks, so it renders a live AB controller with no AB
  screens and no AB repository. It is **read-only**: configured with no write
  root, it refuses mutations before the controller (§11.2.1); only a complete,
  inert `QUERY_CONFIG` page transaction may use the mailbox. It binds
  loopback only, checks the Origin, and holds the discovery revision stable. It
  reports the configured mutation policy as `writeAccess` on all three health
  endpoints; enabling it requires a bearer, write scope, and a wired writer.
  PLC readiness and user permissions remain separate. See the
  [health response contract](../../../Specification/OPCUA_TRANSPORT.md).
  It reuses the projection's shared `read_document`, pins the controller serial and
  re-validates the manifest hash on every poll. Its dependencies are pinned in
  [`tools/requirements-gateway.txt`](tools/requirements-gateway.txt); the live
  HMI run is recorded in
  [`../../../Specification/AllenBradley/Evidence/AB_HMI_GATEWAY_2026-09-21.md`](../../../Specification/AllenBradley/Evidence/AB_HMI_GATEWAY_2026-09-21.md).
- [`tools/fraktal_ab_mailbox_execute.py`](tools/fraktal_ab_mailbox_execute.py) is
  the command mailbox's evidence harness. It speaks the HMI's own gateway
  protocol, commits a request the way the HMI does - arguments first, `Sequence`
  last - and proves each command by reading the controller's `AckSequence` back,
  because a write that returned true is not evidence. It also drives the
  refusals and the three gate negatives, refuses unless the controller publishes
  the expected content hash, and is armed explicitly. It exists because the
  Flutter HMI cannot be the client on a host whose endpoint security intercepts
  TLS; the controller half is identical whoever holds the socket.
- [`tools/fraktal_ab_mailbox_probe.py`](tools/fraktal_ab_mailbox_probe.py)
  measures whether pylogix can write a user `StringFamily` member through `LEN`
  and `DATA`. It writes arguments only and never `Sequence`, so it cannot commit
  a request. The answer is yes, which is a type-map fact about this baseline and
  sits with the S12 findings.
- [`tools/fraktal_ab_press_demo.py`](tools/fraktal_ab_press_demo.py) is the press
  demo declaration - the first application, mirroring the TwinCAT oracle's
  observable behaviour with a simulated plant in tags and no control power.
- [`tools/fraktal_ab_station.py`](tools/fraktal_ab_station.py) selects which
  declaration the generator, the projection, the manifest reader and the
  gateway serve: `FRAKTAL_AB_DECLARATION`, the press when unset. The generator
  also takes `--declaration`.
- [`tools/fraktal_ab_station_template.py`](tools/fraktal_ab_station_template.py)
  is the smallest station that uses everything: a clamp and a part sensor, with
  AUTO, HOME, MANUAL and changeover, run styles, OEE Performance, the
  degradation watch, a state flag, system health, a START permit and an
  interlock. `test_fraktal_ab_station.py` keeps it a working station rather
  than documentation that drifts: it validates, emits, fits the manifest
  budget and projects.
- [`tools/fraktal_ab_press_execute.py`](tools/fraktal_ab_press_execute.py) is its
  fixed fifteen-row harness, reading each structure in one request.
- [`tools/fraktal_ab_rendition_gate.py`](tools/fraktal_ab_rendition_gate.py) reads
  every emitted rendition **back** out of the L5X and recovers its step set and
  transition set in that rendition's own language - a `CASE` for ST, `EQU`
  rung-ins and `MOV`s for ladder, steps and directed links for a chart - then
  requires all of them to equal the declaration. A rendition that cannot be
  parsed back fails the build: silence is not parity.
- [`tools/fraktal_ab_press_parity.py`](tools/fraktal_ab_press_parity.py) walks the
  AUTO graph on the bench in each rendition and requires identical traces. It
  closes its measurement window with the machine rather than the observer -
  withdrawing the start condition once the chain has passed the start step, so
  every rendition parks on the same declared step whatever its speed - because a
  window defined by an observer's reaction time would make a parity claim depend
  on which language happened to be faster.
- [`tools/fraktal_ab_reference_suite.py`](tools/fraktal_ab_reference_suite.py)
  generates the **disposable reference suite** for R5. It is gate tooling, not
  the production module library, and the same scope fence that keeps the S16
  fixture disposable guards it. It promotes the handshake module and the mode
  owner to the binding's first two reference types — importing the declaration
  machinery from the S16 generator rather than copying it — and instantiates the
  module type **twice** over independent contexts, with an on-controller
  cross-talk counter. That second instance is what AB §5.7's G-GENERATED
  argument needs: an extension argument never exercised on a second instance is
  an assertion.
- [`tools/fraktal_ab_reference_execute.py`](tools/fraktal_ab_reference_execute.py)
  is the R5 harness. Same guards as the S16 vector — exact serial, fixture
  fingerprint, explicit arm flag, six-tag write surface restored in a `finally`
  block — and it emits one row per test plus the five summary fields AB §5.7
  names, so the output converts to JUnit the way TC3's does. It reads each
  context in a single request.
- [`tools/fraktal_ab_s12_type_probe.py`](tools/fraktal_ab_s12_type_probe.py)
  emits one minimal project per candidate Logix type, twice — declaration alone
  and declaration plus one operation — so a failure names exactly one type and
  separates an unknown type from an uncompilable expression. Its default
  `v33-5370` profile is the accepted 28-case Phase 0 baseline. The explicit
  `v38-5380-exploratory` profile targets `5069-L310ER` revision 38, remains
  machine-labeled `exploratory-not-accepted`, and adds the four typed-literal and
  matched-operand duration discriminator cases from the Studio-only exploration:
  `python tools/fraktal_ab_s12_type_probe.py <v38-seed.L5X> <output-directory> --profile v38-5380-exploratory`.
- [`tools/fraktal_ab_s12_fixture.py`](tools/fraktal_ab_s12_fixture.py) and
  [`tools/fraktal_ab_s12_execute.py`](tools/fraktal_ab_s12_execute.py) generate
  and execute the memory-only type-map fixture. The controller copies its own
  public UDT, and two adjacent instances of it, into `SINT` arrays so member
  offsets and the padded stride are measured rather than assumed.
- [`tools/fraktal_ab_s9_coherence_fixture.py`](tools/fraktal_ab_s9_coherence_fixture.py)
  and [`tools/fraktal_ab_s9_execute.py`](tools/fraktal_ab_s9_execute.py) provoke
  snapshot tearing and measure whether the coherence guard catches it. The
  vector is ordered so a pass cannot be vacuous: it first shows the guard does
  not reject a frozen controller, then shows unguarded reads genuinely tear, and
  only then sweeps the mutation rate.
- [`tools/fraktal_ab_security_probe.py`](tools/fraktal_ab_security_probe.py)
  asks the controller whether it implements the three CIP Security object
  classes. Fixed classes, read-only, no write path. On the Phase 0 controller
  all three answered `0x05` — a positive absence, which is why that hardware
  runs the legacy zone-and-conduit posture.
- [`tools/fraktal_ab_access_audit.py`](tools/fraktal_ab_access_audit.py) audits
  a project's External Access allow-list offline: declared mailboxes
  `Read/Write`, declared public data `Read Only`, everything else `None`. It
  infers nothing from a tag name and does not treat an omitted attribute as
  `None`, so an incomplete invocation fails loudly instead of approving a
  project by default.
- [`tools/fraktal_ab_s7_manifest_fixture.py`](tools/fraktal_ab_s7_manifest_fixture.py)
  and [`tools/fraktal_ab_s7_execute.py`](tools/fraktal_ab_s7_execute.py)
  materialise the frozen manifest contract as real Logix types at parameterised
  capacities, then measure cold read cost, per-table cost, header-poll cost,
  snapshot coherence and revision-change detection. The generator refuses a
  manifest too large to download, since one that will not download measures
  nothing.
- [`tools/fraktal_ab_s4_matrix_fixture.py`](tools/fraktal_ab_s4_matrix_fixture.py)
  generates the representative construct matrix: both task types with their
  schedules, ST/RLL/SFC in one program, nested and tabular records, a sized
  string type, a generated constant, and the AOI scan routines.
- [`tools/fraktal_ab_l5x_inventory.py`](tools/fraktal_ab_l5x_inventory.py)
  censuses the constructs in a full-project L5X and compares two documents. It
  answers the question the canonical comparator cannot: whether a construct
  survived the *first* import, by comparing the generated declaration against
  the export it produced. An absent attribute is reported rather than treated
  as its default, because Studio writes the default and the difference would
  otherwise resurface later as apparent drift.
- [`tools/fraktal_ab_phase0_gate.py`](tools/fraktal_ab_phase0_gate.py) is the R4
  regeneration gate: it creates the empty v33 seed through the SDK, regenerates
  every fixture from it, and requires a clean import summary, a canonical round
  trip and a construct census for each, plus ID-independent chart equality where
  a chart exists. Studio Verify is opt-in with `--verify` because it needs a
  logged-in desktop session.
- [`tools/fraktal_ab_sfc_roundtrip_compare.py`](tools/fraktal_ab_sfc_roundtrip_compare.py)
  compares the executable SFC content of two L5X documents independently of
  element IDs and sibling order — steps, action qualifiers and bodies,
  transition conditions, branch type/flow, link topology and the controller SFC
  settings — so a generated declaration can be checked against the Studio
  export it produced. It fails closed rather than claiming an unmade comparison.
- [`tools/fraktal_ab_l5x_compare.py`](tools/fraktal_ab_l5x_compare.py) compares
  two full-project L5X exports after excluding only Rockwell's three known
  volatile project/export timestamps, then reports raw and canonical SHA-256
  hashes. Every executable and structural field remains in scope.
- [`tools/fraktal_ab_target_binding_compare.py`](tools/fraktal_ab_target_binding_compare.py)
  separately accepts only the exact serial/firmware-minor stamps introduced by
  a physical download and still requires every other canonical field to match.
- [`tools/fraktal_ab_sdk_log_gate.py`](tools/fraktal_ab_sdk_log_gate.py) turns
  SDK console events into a machine result. It can require named successful
  operations and rejects any SDK error event or non-zero import warning/error
  summary; an SDK process exit code alone is not an import gate.
- [`tools/fraktal_ab_studio_verify.ps1`](tools/fraktal_ab_studio_verify.ps1)
  opens one disposable ACD in the requested Studio revision, invokes offline
  **Verify Controller**, reads Error List counts/details through UI Automation,
  closes without saving, and proves the ACD hash stayed unchanged. It refuses
  repository-contained ACDs and any pre-existing Studio session.

Do not hand-author production L5X. Generated artifacts must be imported,
verified, exported, and compared through Studio 5000, with the exact software,
firmware, controller, and communication baseline recorded as evidence.


### Runtime model creation and file export (2026-10-04)

On the AB press declaration with `model_capacity=8`, Configuration -> Model data
-> **New model** creates an inactive copy of the chosen model. Give it a unique
code, edit it using the Model selector, then use **Changeover** to activate it.
There are eight slots total, including the three declared seed models; users
remain capped at four. In Parameter sets, a Model set offers **Create model
from set**, rather than a load into the running recipe. A complete, typed set is
validated by the PLC before the new catalog entry is published. Existing model
indices remain stable. No model deletion or automatic activation is offered.

**Export current values** exports a PLC snapshot without saving a named set.
Each saved set's **Export** also offers **Download file** (`.jsonl`) and Copy.
The exact pre-catalog configuration revision is recognized when value schemas
are unchanged; unrelated revisions still refuse. TC3 currently exposes neither
optional capability; its shared enum reserves the kinds, without claiming a
runtime recipe-provider implementation.

Press69 is a pending owner deployment; press68 remains the successful memory
baseline. The air-pressure Start permit applies to AUTO/HOME, not CHANGEOVER.
The cylinders' own pressure permits remain in every mode. The prepared image
can include validated commissioning configuration via `--initial-config`;
this carries no sessions, command latches or credential provider data.
