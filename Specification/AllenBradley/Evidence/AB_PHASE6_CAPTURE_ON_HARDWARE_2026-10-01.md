# Fraktal/AB Phase 6 item 1 — capture and read-only configuration on hardware

**Result:** press54's capture stores and audits the machine's published value;
the AB read-only gateway route queries configuration and refuses START. Every
regression harness passes. Phase 6 item 1 is complete on the bench.

**Date:** 2026-10-01, America/Bogota. Fixtures ran from 2026-10-02 02:32:10
to 02:35:37 UTC, from revision `caa2fbf`. The owner replied `done` after the
requested Studio 5000 v33 import, Verify/download and gateway restart. Studio
verification is owner-reported; no Studio transcript was captured here.
The controller measurements below were taken by the guarded harnesses.

This is a new, append-only record following the
[offline build](AB_PHASE6_CAPTURE_BUILD_2026-10-01.md). The
[raw JSON](AB_PHASE6_CAPTURE_ON_HARDWARE_2026-10-01.json) contains every result,
serial check, cleanup report, manifest comparison and gate summary.

## Build readback

| Property | Observed |
|---|---|
| Controller | `1769-L24ER-QB1B/A`, revision `33.14`, serial `7036B510`, `192.168.100.89` |
| Build | `C:\work\press54.L5X` |
| File SHA-256 | `703B896F0A8FED206612D08E44F0A976A5DBF4F4C5AEE5D4ED31E606FF18E6BC` |
| ContentHash / ConfigRevision | `287D251E9DD97551` / `2653477` |
| Manifest major | 3 |
| Fields / Localization | 499/768 and 477/768 |
| Manifest | **79,992 bytes**, coherent, every declared row equal, no findings |
| Read timing | First read 963.434 ms; repeat after fixtures 180.092 ms; 11 requests each |
| Valid / Truncated | 1 / 0 |
| Gateway | `ready`, `plcReady: true`, before fixtures, after fixtures and after gates |

Both reads confirm the versioned capability layout and the published source.
These are measurements of press54, not the 100 KiB generation bound. The
template remains generated and tested offline; it was not downloaded here.

## Capture and D5

The Phase 6 harness passed all ten rows:

| Check | Observed result |
|---|---|
| Published capture capability | `Profiler.LastWork`, CanCapture and CaptureEnabled true |
| Safe starting state | Running 0, Error 0 |
| Read-only query | No bearer or write root; QUERY_CONFIG accepted at sequence 511 |
| Read-only mutation negative | START refused before writing; sequence remains 511 |
| Capture after a completed plant cycle | **970 ms** sampled, stored and audited, ignoring client candidate 999999 |
| Stale revision | Refused: `project.mailbox.refused.config_revision_stale` (441) |
| Editable field without capture | Refused: `project.mailbox.refused.capture_not_registered` (436) |
| Foreign scope | Refused: `project.mailbox.refused.config_key_unknown` (438) |
| AUTO rather than setup | Refused: `project.mailbox.refused.capture_needs_setup` (435) |
| Air permissive absent | Refused: `project.condition.airPressureOk` (469) |

The accepted capture was sequence 525, kind 27. Its audit recorded value 970,
source key 151 (`Profiler.LastWork`) and contract revision 2653477. This proves
stored data against the completed machine cycle, rather than its ack alone.
The identity/revision negatives left configuration and accepted-write audit
unchanged. The air negative also left the captured value unchanged.

D5's hardware test used the actual gateway dispatch and serial-guarded writer,
instantiated with no credential or write root against this controller. No new
gateway listener was started and no deployment credential was read. The owner's
running gateway remained ready. The TC3 gateway's paired query/mutation checks
remain the preceding build's 24/24 offline tests and 4/4 killed mutants; this
record does not claim a TwinCAT hardware deployment.

## Regressions, cleanup and gates

| Harness | Result |
|---|---|
| S3 health/timing, read-only | 6/6 |
| Phase 6 unarmed checks | 2/2 |
| ST/SFC/LD parity | 25/25 |
| Phase 1 | 7/7 |
| Phase 2 | 6/6 |
| Phase 3 | 8/8 |
| Phase 4 | 11/11 |
| Phase 5 | 25/25 |
| Phase 6 capture and read-only query | 10/10 |

S3 sampled 489 scans over 4.893 seconds. Execution time was 587–774 µs,
median 619 µs; maximum scan 1085 µs against the 10,000 µs period. Overlap
count and major/minor fault bits were zero. CPU/memory availability and clock
synchronization remain the recorded S3 limitations.

Each writing harness checked serial `7036B510` and the press fingerprint before
writing, and reported all ten fixture inputs cleared. The Phase 6 finally path
restored and read back the original baseline **950**, mode **AUTO (0)** and run
style **CONTINUOUS (0)**. All restoration operations succeeded. No harness failed
or required a rerun; the repeat manifest read measured the initial slower read
again without any controller-changing action.

- AB tool suite: **1324 tests passed**.
- Consistency: **0 errors, 0 warnings**; its suite **32/32 passed**.

These gates ran before this evidence commit with `-B`, disabled bytecode writes
and fresh cache prefixes. No PLC, generator or gateway source changed in this
verification turn. The offline build retains the HMI/Flutter results, mutation
checks and byte-identical generation evidence.

## Authorization and claim

The owner's current `done` authorized the named verification harnesses' writes
on this exact controller. No download, keyswitch change, firmware/network change,
clock set, or gateway write-enablement was performed by the agent.

The posture remains **v33 legacy zone-and-conduit**, with bench writes enabled
by the owner's recorded 2026-09-29 decision. This item widens that surface with
registered capture; later Phase 6 items add sets, login and shelving. Per-user
controller access and `DATA_WRITE` enforcement remain item 3, and the audit actor
is still the request's claim. **S9 and the write-enabled claim remain owed.**
The next item is parameter sets under the handover's next `go on` / `done` loop.
