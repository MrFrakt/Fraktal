# Press75 restored native regression and Line acceptance

Client date: 2026-10-04, America/Bogota. The owner confirms exact press75
completed download at 0/0 and Run, then closes HMI tabs for the direct native
apparatus. The invoked Phase 6 workflow authorizes these fixed fixture writes
on serial 7036B510; every primitive write rechecks that target. No agent
download, keyswitch, clock, firmware/network or write-gateway restart occurs.

## Scope and artifact

`C:/work/press75.L5X`, SHA-256
`82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5`,
generator commit `1528eab`, manifest 94E302F650BA1DB5 / 9757442, 65,552 bytes.
The [fit record](AB_LINE_V2_PRESS75_NATIVE_FIT_2026-10-04.md) records online
data/logic 758,568 / 786,432 bytes, 27,864 available, largest block 27,376.
Harness fixes add no PLC data/code and require no new download.

## Failures preserved and apparatus corrected

The first shelving run passes its 15 assertions but times out restoring its own
login-result sequence. Independent restoration succeeds. Sequence 109's earlier
trace has no matching result; its cause remains unproved. Twenty later diagnostic
logins each match their own result. No failed evidence is promoted to acceptance.

With HMI tabs closed, a commit guard catches two consumed sequences. Gateway
fixture commands advance the controller cursor but not the direct helper's
cached counter. The owning direct helper now reads a settled request/ACK for
every command and refuses a changed cursor before commit. Missing reads and
outstanding requests fail before writes. This does not create a cross-process
mailbox lock: direct fixtures still require isolation from other writers.

The next run records a false-negative watchdog timing row: remaining wait
28.970 s, controller StallMs 30,000, non-fault STEP_STALLED and no early timeout.
The stopwatch had excluded command/setup/snapshot reads while the watchdog ran.
It now starts before those operations and checks the controller elapsed value;
the native rerun measures 30.204 s and passes. The controller watchdog is unchanged.

The set preflight then refuses before any write because it hard-codes V1,
while optional Line correctly expands the released state to V2. It now derives
the expected version from the declaration and still refuses mismatches. Both
with-Line and without-Line paths are tested. The last set retry passes 17 rows.

Two Line apparatus attempts are also retained with full restoration: one omitted
the current-export document name and was correctly refused; another attempted
to read private clock tags and got no value. The final fixture uses the required
name and a fresh, public controller export timestamp. No private tag access was
changed and no clock write was made.

## Accepted native regression

Eleven suites supply 159 successful rows: shelving 15, data classes 18, access
16, capture 10, rendition parity 25, phase1 7, phase2 6, phase3 8, phase4 12,
phase5 25 and sets 17. These are selected successful suites across three runs,
each with independent final restoration; this is not one uninterrupted all-suite
pass. The interrupted runs remain overall failures in the machine record.

Catalog/all four recipe banks, model ordinal, station data, baseline, Line
calendar, class/access policy, timeout, mode/style and all fixture inputs return
to their captured values. No disposable model is created. Admin level 4 is
restored through a matching result; shelves are cleared and the unit is idle.

## Accepted Line vectors

Seventeen rows prove complete 13-field saved/current export and JSONL import,
operator/technician minimum-write refusal even with a spoofed admin actor,
whole-calendar overlap/partial-set/range refusal without partial application,
a complete twelve-hour Saturday/Sunday calendar, and per-field validation
against the whole calendar. Effective write minima remain controller-owned.

The fixture positions the twelve-hour interval to end three minutes after a
fresh controller timestamp, without changing that clock. Restoring the original
empty calendar remains pending while the existing shift runs, then applies at
its real minute boundary. The PLC closes the history row before resetting its
profile-owned counters, then returns to unscheduled index 0 with no next boundary
and matching applied/declared revisions. Two actual history closures remain;
cleanup never deletes or rewrites controller history. Time quality remains
unsynchronized. Host set files are isolated and do not touch production sets.

Final independent readback passes the full manifest, captured configuration/
four-model banks and S3 6/6, with no major/minor fault or task overlap. A fresh
complete gateway sample precedes final healthz/livez/readyz checks; all return
200 with plcReady true. Idle-cache degradation is not hidden by a deadline change.

## Validation and remaining gates

The full AB suite passes 1,607 tests; focused harness tests pass 21, five
semantic mutants fail assertions without interpreter errors, root tests pass
33 and consistency reports 0 errors/0 warnings. PLC generation is unchanged.

This proves one weekend-only shift and its natural end, not a hardware sweep of
every weekday/overnight/overflow boundary. Offline calendar/closure tests retain
their separate scope. Chrome controls and physical Line retention remain owner
checks; mirror/shared-root transport, Part traceability and later port stages
remain unclaimed. Keep future memory growth within this measured baseline.

The [machine record](AB_LINE_V2_PRESS75_NATIVE_ACCEPTANCE_2026-10-04.json) contains
selected assertion rows, guarded restoration, preserved failures, final S3/health
and source/artifact hashes. Earlier evidence is unchanged.
