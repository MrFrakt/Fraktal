# Native task windows and durable publisher restart — 2026-10-18

Four bounded native TASK windows pass on local Echo, and the existing host
collector recovers across a same-manifest download without duplicate SQLite
rows, including replay from its pre-download cursor. All 31 tower/Part/resource
regressions and 23 final restoration checks pass. The port is **not complete**;
production health-provider promotion and clock-replay identity remain open.

Payload, exact source bindings, native artifact hashes and validation logs:
[`AB_NATIVE_WINDOWS_RESTART_2026-10-18/manifest.json`](AB_NATIVE_WINDOWS_RESTART_2026-10-18/manifest.json).
Baseline commit: `23912ff5171021fc533b73ea510d564752be91cb`.
Earlier [read-only timing evidence](AB_NATIVE_TIMING_2026-10-18.md),
[collector crash recovery](AB_HOST_RECOVERY_2026-10-18.md) and
[resource-event acceptance](AB_RESOURCE_EVENTS_2026-10-18.md) retain their scope.

## Target and authorization

The owner's standing statement, **“simulated plc is available for you to download
anytime”**, authorizes this local simulated-controller download. Exact guards
run immediately before each mode change/download: `127.0.0.1`, slot 0,
Emulate 5580 product 288, firmware 38.011, serial `601FC87B`, and the expected
local Echo listener. The final Echo inspection also identifies controller
`FraktalPhase0`, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`.
No physical controller is authorized by that statement.

The running resource image was uploaded and saved before replacement. All five
live configuration documents equalled their saved medium, and the original
access policy and logged-out/idle state were checked. The saved cursor and
17 existing sink rows were captured before download. Credentials remain local.
No fault clear, clock/PTP change, Echo scaling, scheduling change or electrical
I/O operation occurred.

The generated source is `C:/work/fraktal-ab-task-windows-20261018/windows_01.L5X`,
SHA-256 `2A14A3CC12E46AAA04EB56FD99ED214128181968A5549576C21CE82E76BB9525`.
The manifest remains major 5, `EBF1887B15E96453`, configuration revision
15462792, declaration `fraktal_ab_resource_demo`. Native ACD/large L5X artifacts
remain local; their hashes, read-back comparisons and logs are archived.

## Native reuse and ownership

[Rockwell's v38 TASK reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-task-object.html)
supports GSV/SSV MaxInterval and MinInterval as two-DINT interval values. These
are task-wide extrema, rather than the spacing of clocks sampled after variable
application work. The reference does not establish the reset seed needed for
Fraktal's short windows; this experiment measures it on the exact target.

`fraktal_ab_task_window_probe.py` generates the ordinary resource fixture and
uses the shared guarded augmentation owner. Every existing executable body,
initializer, alarm record and task setting is preserved apart from a final
main-routine JSR. The private 224-byte native record has read-only external
access and revision-bracketed acquisition. Four reset pairs write only
TASK MaxInterval/MinInterval. After 401 scans, the experiment freezes both its
record and its SSV path; the regression matrix and final checks confirm the
completed record remains unchanged.

The first scan resets the extrema; each subsequent window contains 100 task
intervals. MaxInterval is seeded with zero throughout. MinInterval alternates
zero and the full-width sentinel `0x7fffffff7fffffff`. Immediate GSV read-back
captures the actual reset value before the next task execution. Native COP
preserves all eight bytes when recording the two-DINT values as LINTs.

| Window | MinInterval seed | Immediate reset read-back | Native minimum..maximum, us |
| --- | --- | --- | --- |
| 0 | 0 | exact | 9,998..10,002 |
| 1 | 9,223,372,034,707,292,159 | exact | 9,999..10,001 |
| 2 | 0 | exact | 9,999..10,001 |
| 3 | 9,223,372,034,707,292,159 | exact | 9,999..10,001 |

Configured period is 10,000 us; no major/minor fault or changed overlap count
was observed. Zero is a working reset method for both extrema on this Echo;
the larger sentinel is unnecessary here. This is steady-state reset/window
qualification, not clock-adjustment, missed-scan, scaling or physical acceptance.

**Production decision:** keep the existing health provider pending an adapter
review. Resetting these extrema also changes what engineering tools and other
programs see. A production adapter must own that shared statistic and preserve
both the current per-scan overrun/jitter event behavior and the settled published
window. Native window results alone do not supply the latest individual interval.
Do not silently replace either contract with lifetime or window extrema.

Private growth is 3,084 ST source bytes, 44 terminators, 53 lines and no RLL
rungs/AOIs, plus the 224-byte native record. The generic DINT/SINT estimator
excludes this LINT-containing record. These measurements exclude compiled
instructions, AOI storage, metadata and reserve; they do not prove physical fit.

## Host delivery through the actual download

The same declaration/manifest is used on both sides of the download. The
publisher sequence restarts while its wall-clock-derived epoch changes:

- Before: epoch `[299754595, 205878]`, acknowledged sequence 157, 17 sink rows.
- After download: epoch `[-1736657026, 205878]`, empty ring/sequence 0. The
  collector commits one `publisherEpochChanged` notice naming the complete old
  cursor before acknowledging the new epoch. The sink now has 18 rows.
- After the regression matrix: sequence 157 again. Both epochs' retained events
  coexist with distinct stable keys. The new ring's overwritten interval is
  explicitly reported; the sink has 35 rows, including the original records.
- Reopening the collector, restoring the old pre-download cursor and replaying,
  then reopening again all leave those same 35 rows unchanged. Acknowledgement
  recovers to the new epoch/sequence 157; SQLite integrity remains `ok`.

All 11 immediate restart checks and 17 post-regression/replay checks pass.
The collectors perform zero controller writes. Cursor acknowledgement and
deduplication use the existing collector and SQLite transaction implementation;
this batch adds no second delivery engine. The epoch-change notice reports an
unknown restart interval, not a promise that no events were lost at replacement.

This proves ordinary same-manifest Echo download/restart delivery with the
existing clock progression. Startup identity still derives from WallClockTime;
clock replay, physical power/download retention, gateway service restart and
network delivery remain unqualified.

## Validation and final state

- **1,863 AB tests pass**, 319.797 seconds, including eight new probe tests.
  The generated-control-flow model proves bounds and shutdown; its native
  instruction stubs are not evidence for controller reset semantics.
- **74 root tests pass**. AB specification, frozen-contract and strict
  cross-artifact consistency gates pass.
- Studio 38 / SDK 2.1.974 EchoController and PhysicalController builds pass;
  the prepared ACD reopens and builds. Import summaries have zero warnings and
  errors, and backup/download operation logs pass their required-operation gate.
- Echo, physical, prepared and downloaded read-back match **43 executable
  bodies, 20,446 authored initials and 21 SFC steps**. PhysicalController is an
  offline compiler target only. The opt-out tower source remains byte-identical.
- **31/31 live regressions pass**, including 21 resource/Part ST/SFC/LD rows.
  Configuration restore, lamp-test expiry without a client, adopted fault,
  handled NOK, HELD/resume, abort, mode change and one-reset recovery pass.
- **23 final checks pass**. All five documents equal pre-download values and
  reopened saved documents; original policy, simulation inputs and session
  restore. Regeneration equals the exact compiled-source hash.

Echo remains **Run, fault-free, MANUAL/idle**, with no active lamp test or Part,
and logged out under the original policy. The resource fixture with the completed
private window probe remains loaded. Its native task-wide interval statistics
now describe execution since the final experimental reset, not since download.
No ordinary production health calculation or public manifest layout changed.
