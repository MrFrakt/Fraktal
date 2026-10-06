# Fraktal/AB Phase 6 item 5 — shelving on hardware

**Date:** 2026-10-03, America/Bogota. **Parent:** `50a1b9b`.
**Result:** press67 shelving passes **15/15**; all final hardware regressions
and restoration pass. After the read-only readiness snapshot and an explicit
fixture request citing AGENTS.md §3a, the owner authorized the shelving and
regression fixtures with **“go ahead.”** Authorization covers the declared
fixture operations and session setup/restoration on serial **7036B510**.
The companion [JSON](AB_PHASE6_SHELVING_ON_HARDWARE_2026-10-03.json) preserves
every final suite, the initial failed Phase 5 run, restoration, identity-guard
counts, timings, reproduction and source hashes. Historical evidence is unchanged.

## Loaded reference profile and memory baseline

Target is `192.168.100.89`, `1769-L24ER-QB1B/A`, firmware **33.014**, task
**10 ms**. The entire **68,472-byte** major-4 manifest reads coherently and all
rows equal the declaration: ContentHash `832DD0D0F260872B`, ConfigRevision
**8596944**, Fields **565/640**, Localization **570/640**, Rationalization
**23/32** and write capabilities **9/64**. The final read takes
142.020 ms and the repeat **154.664 ms**.
The owner artifact `C:\work\press67.L5X` remains SHA-256
`C07886CC6C490B46A2DDCD90B5F6AF494CF2722D611020C1295DC728522ACD2F`.

Press67 is the verified loaded baseline for future growth comparisons.
Compared with failed press66, its supported declared data is **12,288 bytes
smaller**, total ST has **235 fewer statement terminators** and **18,455 fewer
source bytes**. Relative to successful press64 the deltas are −11,864 declared
bytes, −107 terminators and −8,847 source bytes. These are source/data trends,
not native compiled/free controller-memory measurements. No fresh Studio Verify
log or native free-memory value is supplied by this verification run. The live
dimensions and changed command regressions agree with the owner artifact;
manifest identity alone is not a logic hash.

Both press67 and the station template regenerate byte-identically after the
fixture correction. The template SHA-256 remains
`632900553C7E7AA368BBE853574F27AA131E605C3EB57DA0F1B6B98FF4C57A98`;
its 58,232-byte manifest and smaller declarations remain offline evidence.
The four-user ceiling, alarm/history capacities and writable tag set are unchanged.
No new download is required for this fixture-only correction.

## Shelving hardware proof

The fixture verifies AlarmActive/Ring V2, the standing registry-shelvable
metrics event, stopped/error-free state and a restorable known session, then:

- Shelf and manual unshelf change the published annunciation flag and log
  lifecycle history. Shelf identity is source plus description, never a slot.
- Native requests claiming admin remain refused under the operator's actual
  session for both shelf and unshelf. Foreign source, wrong description and
  zero duration refuse without creating a shelf.
- An above-cap request is accepted as a bounded shelf, then removed. The exact
  eight-hour cap is proved offline; an eight-hour hardware wait is not claimed.
- A requested three-second shelf expires after logout in **3.833 seconds**, and
  the controller logs expiry independently of the session and calendar time.
- The registry-unshelvable cylinder defect **10101** refuses shelving and still
  refuses Start with a release report. Shelved blocking events, duplicate
  identities, safety/unrationalized refusal, exact cap and slot reuse retain the
  additional offline proof. The hardware defect row tests an unshelvable fault.

All six successful shelving authentications settle in **1,108.469–1,195.155 ms**,
including its in-process gateway, guarded CIP staging and correlated result.
LoginFailed is false for each success. This does not measure Chrome rendering
or the full native-PIN fallback. Shelving cleanup restores the original admin
session, policy and timeout and leaves no shelf active.

## Regression timing correction and final results

The first Phase 5 run passes **21/25**. All three hold-to-run rows release at
step 240 after five commands, instead of during the brief slide motion; the
runtime row measures wall time 2,704.9 ms against controller RunMs 2,060 ms.
The immediate identity check before each primitive Write increases argument
staging latency. The fixture assumed staging was shorter than a motion and
counted pre-START staging as running time. Its original output and successful
restoration are retained, not replaced by the retry.

The corrected fixture uses the already-declared recoverable PartSlide hold to
keep the issued motion in progress while staging the release. It requires the
module to be BUSY/HELD, releases that fixture input in `finally`, then proves the
existing motion completes while the next door command remains unissued. After
holding again, exactly eight commands complete the cycle, in ST/SFC/LD alike.
Runtime is compared between START and STOP acknowledgements with the unchanged
**250 ms** tolerance. The retry observes wall time
**2098.3 ms** and RunMs
**2210 ms**. PLC/gateway/HMI behavior and
generated artifacts are unchanged. The two slow-client/cleanup tests pass;
both in-memory mutations removing the motion barrier or leaving it active
are killed. No mutant is written to disk or run on the controller.

| Suite | Final result |
|---|---|
| Shelving | 15/15 |
| Data classes | 18/18 |
| Controller access | 16/16 |
| Capture / read-only query | 10/10 |
| Parameter sets | 17/17 |
| Principles parity, ST/SFC/LD | 25/25 |
| Phases 1, 2, 3, 4, 5 | 7/7, 6/6, 8/8, 11/11, 25/25 |
| S3 health/timing before and after | 6/6 each |

Across the successful suite invocations, **10,367**
primitive Writes have the same number of immediate exact target checks and
zero identity blocks. The initial failed timing invocation has its own complete
guard record. All invocations total **13,965**
guarded fixture Writes; separate setup/restoration session writes use
`GuardedPLC` and are outside these CLI counts. Guard tests also refuse a changed
serial and a wrong IP before delivery. No Write payloads or private credentials
are recorded by the guard.

Final independent readback confirms AUTO/CONTINUOUS, stopped without Error,
baseline 950, station number 1, ram limit 2,000 ms, pressure minimum 450,
pressure conflict time 500 ms and two-hand requirement enabled. Both class
read/write policies and all twelve action thresholds are NONE; timeout is
zero. All ten fixture inputs are zero. The original `phase6_admin` session is
level 4, with LoginBusy/LoginFailed zero, and no active shelf remains. The set
fixture uses an isolated store and restores its values. Gateway status is
`ready`, `plcReady=true`.

Maximum task scan is **5,279 µs** against **10,000 µs**, overlap count
**zero**, and major/minor fault bits **zero**. S3 passes before and after.
No fault or timing counter was cleared. The offline AB suite passes
**1,486 tests**, the consistency suite **33**, and consistency reports
**0 errors / 0 warnings**. The generated build's 21 killed mutations remain
historical offline evidence; HMI source/build are unchanged and browser
rendering was not newly measured during this run.

No agent download, gateway launch/restart, provisioning/PIN change, native
fault/counter clear, clock set or firmware/network change was performed during
verification. Fixture commands, sensor/fault injections and policy/session
changes were within the current authorization and restored.

Item 5's runtime gate is accepted. **Item 6, the write-enabled S9 contract
suite, is next.** The v33 legacy zone-and-conduit bench remains write-enabled
by the 2026-09-29 decision; these shelving routes widen that surface but do not
establish the full S9 claim. Physical retention across power-cycle/download/
upgrade also remains owed.
